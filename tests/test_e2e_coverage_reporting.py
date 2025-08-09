# pyright: reportGeneralTypeIssues=false
"""End-to-end test that verifies the *chat → worker → analysis → summary* flow
includes the coverage percentage in the final Telegram message.

The real system is used, but heavy external calls are monkey-patched:
• ReActAgent.analyze_task_results → deterministic summary containing
  a coverage figure ("Overall coverage: 81 %").
• TelegramManager.send_message → capture text locally.
• OpencodeSession._execute_opencode_command → dummy successful run.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from src.managers.file_ownership import FileOwnershipManager
from src.utils.opencode_wrapper import OpencodeSessionManager, OpencodeSession
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge
from src.chat.message_parser import MessageParser
from src.agents.react_agent import ReActAgent


@pytest.fixture()
def tmp_sessions(tmp_path: Path):
    sess = tmp_path / "sessions"
    sess.mkdir()
    os.environ["SESSIONS_DIR"] = str(sess)
    return sess


@pytest.fixture()
def patch_network(monkeypatch: pytest.MonkeyPatch):
    """Patch Telegram send + Opencode execution for offline deterministic run."""

    sent: list[str] = []

    def fake_send(self: TelegramManager, text: str, sender_name: str = "system", reply_to=None):  # type: ignore[override]
        sent.append(text)
        return True

    monkeypatch.setattr(TelegramManager, "send_message", fake_send, raising=True)

    def instant_exec(self: OpencodeSession, *a, **kw):  # type: ignore[override]
        return {
            "success": True,
            "stdout": "Overall coverage: 81 %\nDone.",
            "stderr": "",
            "return_code": 0,
        }

    monkeypatch.setattr(OpencodeSession, "_execute_opencode_command", instant_exec, raising=True)

    # Patch analysis so it returns explanation incl. coverage
    def fake_analysis(self: ReActAgent, task_output: str, task_description: str | None = None):  # type: ignore[override]
        return (
            "Here is the coverage analysis:\n"
            "• Overall line coverage is 81 %.\n"
            "No major gaps detected. Nice work!"
        )

    monkeypatch.setattr(ReActAgent, "analyze_task_results", fake_analysis, raising=True)

    return sent


def wait_until(cond, timeout=6, interval=0.1):
    import time
    start = time.time()
    while time.time() - start < timeout:
        if cond():
            return True
        time.sleep(interval)
    return False


def test_coverage_number_reported(tmp_sessions: Path, patch_network):
    # core components
    db_path = tmp_sessions / "employees.db"
    fm = FileOwnershipManager(str(db_path))
    fm.hire_employee("elad", "developer")

    sess_mgr = OpencodeSessionManager(fm, sessions_dir=str(tmp_sessions), quiet_mode=True)
    tel = TelegramManager()  # patched send
    mgr = AgentManager(fm, tel)
    mgr.setup_monitoring_system(sess_mgr.task_tracker, sess_mgr)
    bridge = AgentBridge(sess_mgr, mgr)

    # send chat message
    parser = MessageParser()
    message = parser.parse_message({
        "message_id": 1,
        "text": "@elad please calculate coverage",
        "from": {"username": "boss"},
        "date": int(time.time()),
    })
    mgr.handle_message(message)

    # wait until bridge cleans up
    assert wait_until(lambda: not sess_mgr.get_active_sessions()), "session still running"
    bridge.check_task_completion()

    # ensure a telegram message with the coverage percent was sent
    joined = "\n".join(patch_network).lower()
    assert "81 %" in joined or "81%" in joined, f"coverage percent missing in telegram output: {joined}"