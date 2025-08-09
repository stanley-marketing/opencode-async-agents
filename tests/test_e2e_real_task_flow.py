# pyright: reportGeneralTypeIssues=false
"""E2E test for the real task-assignment flow.

This spins up the *real* FileOwnershipManager, TaskProgressTracker,
OpencodeSessionManager, AgentManager, and AgentBridge.  External side
effects that would reach the network (Telegram HTTP calls, `opencode`
sub-process) are monkey-patched so the test can run fully offline while
 exercising the real code paths.
"""

from __future__ import annotations

import os
import time
import types
from pathlib import Path
from datetime import datetime

import pytest

from src.managers.file_ownership import FileOwnershipManager
from src.utils.opencode_wrapper import OpencodeSessionManager, OpencodeSession
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge
from src.chat.message_parser import MessageParser
from src.config import config as cfg


@pytest.fixture()
def tmp_sessions_dir(tmp_path: Path):
    """Provide an isolated sessions/ directory for the test run."""
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    # Ensure Config.SESSIONS_DIR points at the temp dir so that any code
    # which falls back to Config continues to use the isolated area.
    os.environ["SESSIONS_DIR"] = str(sessions)
    # Reload the Config module so the class attributes pick up env var.
    import importlib
    import src.config.config as config_mod  # type: ignore
    importlib.reload(config_mod)
    return sessions


@pytest.fixture()
def patched_telegram_manager(monkeypatch: pytest.MonkeyPatch) -> TelegramManager:  # noqa: D401
    """Return a TelegramManager with network calls disabled.

    The real *implementation* class is kept – only its `send_message`
    method is replaced so that we can assert on messages later without
    hitting Telegram HTTP endpoints.
    """

    sent_messages: list[str] = []

    def fake_send(self: TelegramManager, text: str, sender_name: str = "system", reply_to: int | None = None):  # noqa: D401,E501
        sent_messages.append(text)
        # Pretend rate-limiting etc. all passed
        return True

    monkeypatch.setattr(TelegramManager, "send_message", fake_send, raising=True)

    mgr = TelegramManager()
    # expose captured list on the instance for assertions
    mgr._sent_messages = sent_messages  # type: ignore[attr-defined]
    return mgr


@pytest.fixture()
def patched_opencode(monkeypatch: pytest.MonkeyPatch):
    """Patch heavy parts of the OpencodeSession so it completes instantly."""

    def _instant_execute(self: OpencodeSession):  # noqa: D401
        """Return a dummy successful result containing coverage text."""
        return {
            "success": True,
            "stdout": "Overall coverage: 83 %\nAll tests passed.",
            "stderr": "",
            "return_code": 0,
        }

    monkeypatch.setattr(OpencodeSession, "_execute_opencode_command", _instant_execute, raising=True)

    # Speed up analyse-task step – skip walking the filesystem.
    monkeypatch.setattr(OpencodeSession, "_analyze_task_for_files", lambda self: ["src/sample.py"], raising=True)

    # Nothing to return – patching is in place for the test duration.
    return None


def wait_until(condition, timeout: float = 10.0, interval: float = 0.1):
    """Utility helper – block until *condition()* is True or timeout expires."""
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return True
        time.sleep(interval)
    return False


def test_real_e2e_task_flow(tmp_sessions_dir: Path, patched_telegram_manager: TelegramManager, patched_opencode):  # noqa: D401,E501
    """Full end-to-end test exercising the real task flow."""

    # 1.  Core components -------------------------------------------------
    db_path = tmp_sessions_dir / "employees.db"
    file_manager = FileOwnershipManager(str(db_path))
    # Hire an employee so AgentManager will create an agent for them.
    employee_name = "elad"
    assert file_manager.hire_employee(employee_name, "developer")

    # Session manager (quiet so console spam is suppressed)
    session_mgr = OpencodeSessionManager(file_manager, sessions_dir=str(tmp_sessions_dir), quiet_mode=True)

    # Telegram (patched)
    telegram_mgr = patched_telegram_manager

    # Agent manager & bridge – these are the real production classes
    agent_manager = AgentManager(file_manager, telegram_mgr)
    # Hook monitoring system so agents get the shared task tracker
    agent_manager.setup_monitoring_system(session_mgr.task_tracker, session_mgr)

    # Disable expensive LLM reasoning inside CommunicationAgent summaries
    # by null-ing the ReAct agent reference later.
    # Patch CommunicationAgent._handle_task_assignment so it assigns the task even without the heavy ReAct reasoning.
    from src.agents.communication_agent import CommunicationAgent
    def _quick_assign(self, message):  # type: ignore[overwrite-attr]
        task_description = self.message_parser.extract_task_description(message.text, self.employee_name)
        if self.on_task_assigned and task_description:
            self.on_task_assigned(task_description)
            self.current_task = task_description
            self.worker_status = "working"
            self.active_tasks.add(task_description)
        self._record_response()
        return f"Sure, I will work on: {task_description}"
    CommunicationAgent._handle_task_assignment = _quick_assign
    # Null out react agents to avoid external LLM calls during analysis/summary
    for ag in agent_manager.agents.values():
        ag.react_agent = None  # type: ignore[attr-defined]

    bridge = AgentBridge(session_mgr, agent_manager)

    # 2.  Send a real chat message ---------------------------------------
    parser = MessageParser()
    message_data = {
        "message_id": 1,
        "text": f"@{employee_name} please calculate test coverage",
        "from": {"username": "boss"},
        "date": int(time.time()),
    }
    parsed = parser.parse_message(message_data)

    # Route through the AgentManager handler (as TelegramManager would do)
    agent_manager.handle_message(parsed)

    # 3.  Expect a current_task.md file to exist soon --------------------
    task_file_path = tmp_sessions_dir / employee_name / "current_task.md"
    assert wait_until(task_file_path.exists, timeout=5), "task file was not created"

    # 4.  Wait for OpencodeSession to finish & bridge to record completion
    def completed():
        # First ensure all sessions finished running
        sessions = session_mgr.get_active_sessions()
        if sessions and any(info.get("is_running", False) for info in sessions.values()):
            return False
        # Trigger bridge check once sessions appear done
        bridge.check_task_completion()
        return employee_name not in bridge.active_tasks

    assert wait_until(completed, timeout=8), "session did not complete in time"

    # Manually invoke completion check once more to be sure (covers race)
    bridge.check_task_completion()

    # 5.  Verify completed task file archived & contains coverage --------
    completed_output = session_mgr.task_tracker.get_last_completed_task_output(employee_name)
    assert completed_output is not None
    assert "coverage" in completed_output.lower(), "coverage figure missing from task output"

    # 6.  Verify a message was sent via Telegram containing coverage ------
    sent_texts: list[str] = telegram_mgr._sent_messages  # type: ignore[attr-defined]
    assert sent_texts, "no telegram messages sent"
    joined = "\n".join(sent_texts).lower()
    assert "coverage" in joined, "coverage summary not included in telegram output"
