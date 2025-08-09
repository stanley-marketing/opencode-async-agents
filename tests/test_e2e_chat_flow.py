# pyright: reportGeneralTypeIssues=false
"""E2E-style test: send a chat message that mentions the agent and
verify that
1. AgentManager processes it
2. A task file is created (progress tracking begun)
3. A response is queued via TelegramManager stub
"""

from datetime import datetime
from pathlib import Path

from types import SimpleNamespace

import os
import time

import pytest

from src.chat.message_parser import ParsedMessage
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge
from src.trackers.task_progress import TaskProgressTracker


class DummyTelegramManager:
    def __init__(self):
        self.sent: list[str] = []
        self._handlers = []

    # AgentManager registers itself via add_message_handler – we fake that API
    def add_message_handler(self, fn):
        self._handlers.append(fn)

    def send_message(self, text: str, _employee: str):
        self.sent.append(text)
        return True

    # helper for test – invoke handlers
    def inject_message(self, parsed):
        for h in self._handlers:
            h(parsed)


class DummySessionManager:
    def __init__(self, sessions_dir):
        self.sessions_dir = sessions_dir
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self._active = {}

    def start_employee_task(self, employee_name, task_description, model=None, mode="build"):
        self._active[employee_name] = {"is_running": True}
        return "sess_1"

    def get_active_sessions(self):
        return self._active

    def finish(self, employee):
        if employee in self._active:
            self._active[employee]["is_running"] = False


class DummyFileManager:
    def list_employees(self):
        return [{"name": "alice", "role": "python-developer"}]


@pytest.fixture()
def setup_env(tmp_path: Path):
    sessions_dir = tmp_path / "sessions"
    tel = DummyTelegramManager()
    fm = DummyFileManager()
    mgr = AgentManager(fm, tel)  # type: ignore[arg-type]
    sess_mgr = DummySessionManager(str(sessions_dir))
    bridge = AgentBridge(sess_mgr, mgr)  # type: ignore[arg-type]
    return SimpleNamespace(tel=tel, mgr=mgr, bridge=bridge, sess=sess_mgr, sessions_dir=sessions_dir)


def test_chat_triggers_task(setup_env):
    env = setup_env

    # Create parsed message that mentions agent @alice
    parsed = ParsedMessage(
        message_id=1,
        text="@alice please calculate coverage",
        sender="tester",
        timestamp=datetime.now(),
        mentions=["alice"],
        is_command=False,
    )

    # Inject message into the telegram -> agent manager handler
    env.tel.inject_message(parsed)

    # Task file should now exist (bridge called)
    progress_file = env.sessions_dir / "alice" / "current_task.md"

    assert progress_file.exists(), "Task file not created via chat flow"

    # Response should be sent back
    assert env.tel.sent, "No chat response sent back"
