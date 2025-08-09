# pyright: reportGeneralTypeIssues=false
"""Tests that a task file is automatically created when a task is assigned via AgentBridge.

The test uses lightweight stub classes instead of the full SessionManager / AgentManager
implementations.  We only need the subset of behaviour exercised by
`AgentBridge.assign_task_to_worker`.
"""

import os
from pathlib import Path

from types import SimpleNamespace

import pytest

from src.bridge.agent_bridge import AgentBridge
from src.trackers.task_progress import TaskProgressTracker


class DummySessionManager:
    """Minimal stand-in for OpencodeSessionManager used by AgentBridge."""

    def __init__(self, sessions_dir: str):
        self.sessions_dir = sessions_dir
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self._counter = 0

    # AgentBridge calls this to spin up a worker session
    def start_employee_task(self, employee_name: str, task_description: str, model=None, mode="build"):
        self._counter += 1
        # Return a dummy session id – anything truthy is accepted by AgentBridge
        return f"sess_{self._counter}"

    # AgentBridge later inspects session status in check_task_completion, but we don't
    # run that part in this unit-test.
    def get_active_sessions(self):
        return {}


class DummyTelegramManager:
    def send_message(self, text: str, _employee: str):
        # Pretend the message always sends OK
        return True


@pytest.fixture()
def tmp_sessions(tmp_path: Path):
    """Provide a temporary sessions directory for the test run."""
    return tmp_path / "sessions"


@pytest.fixture()
def bridge(tmp_sessions):
    # Minimal AgentManager stub – only the pieces AgentBridge touches
    dummy_agent_manager = SimpleNamespace(
        agents={},
        is_agent_available=lambda _name: True,  # always available
        notify_task_completion=lambda *_args, **_kwargs: True,  # no-op
    )

    session_mgr = DummySessionManager(str(tmp_sessions))
    return AgentBridge(session_mgr, dummy_agent_manager)  # type: ignore[arg-type,call-arg]


def test_assign_task_creates_progress_file(bridge, tmp_sessions):
    employee = "alice"
    task_desc = "Calculate test coverage"

    # Sanity – no file before assignment
    progress_file = tmp_sessions / employee / "current_task.md"
    assert not progress_file.exists()

    # Assign the task – should internally create the task file via TaskProgressTracker
    ok = bridge.assign_task_to_worker(employee, task_desc)
    assert ok, "assign_task_to_worker should return True"

    # Now the task progress file should exist
    assert progress_file.exists(), "current_task.md must be created for the worker"

    # Content sanity – task description should appear in the file
    content = progress_file.read_text("utf-8")
    assert task_desc in content
