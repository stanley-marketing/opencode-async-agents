# pyright: reportGeneralTypeIssues=false
"""Integration test: full task flow through AgentBridge → AgentManager
ensuring that a task file is created, archived, and that a completion
message is pushed through the TelegramManager stub containing a summary.
"""

from pathlib import Path
import os
import shutil

from types import SimpleNamespace

from src.bridge.agent_bridge import AgentBridge
from src.trackers.task_progress import TaskProgressTracker


class DummySessionManager:
    """Mimic start/stop of worker sessions."""
    def __init__(self, sessions_dir: str, file_manager=None):
        self.sessions_dir = sessions_dir
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self.file_manager = file_manager or DummyFileManager()
        self._active_sessions: dict[str, dict] = {}
        self._counter = 0

    # --- methods AgentBridge relies on ---
    def start_employee_task(self, employee_name: str, task_description: str, model=None, mode="build"):
        self._counter += 1
        sess_id = f"sess_{self._counter}"
        self._active_sessions[employee_name] = {"session_id": sess_id, "is_running": True}
        
        # Create task file like the real session manager does
        self.task_tracker.create_task_file(employee_name, task_description, ["dummy_file.py"])
        
        return sess_id

    def get_active_sessions(self):
        # return dict { employee: {is_running: bool}}
        return {emp: info for emp, info in self._active_sessions.items() if info["is_running"]}

    # helper for test – mark worker finished
    def finish_task(self, employee_name: str):
        if employee_name in self._active_sessions:
            self._active_sessions[employee_name]["is_running"] = False


class DummyTelegramManager:
    """Capture messages that would be sent to chat."""
    def __init__(self):
        self.sent: list[str] = []

    def send_message(self, text: str, _employee: str = "system", reply_to: int = None):
        self.sent.append(text)
        return True
    
    def add_message_handler(self, handler):
        """Dummy method to satisfy AgentManager initialization"""
        pass
    
    def is_connected(self):
        """Dummy method to satisfy AgentManager"""
        return True


class DummyFileManager:
    def list_employees(self):
        return [{"name": "alice", "role": "developer"}]


class DummyAgent:
    """Minimal agent that just returns a canned completion message including task_output."""
    def __init__(self):
        self.worker_status = "idle"
        self.current_task = None
        self.active_tasks = set()
    
    def notify_worker_completed(self, task: str, task_output: str = ""):
        summary = "SUMMARY:" + (task_output[:50] if task_output else "no output")
        return f"✅ Completed {task}\n\n{summary}"


def test_full_task_flow(tmp_path: Path):
    sessions_dir = tmp_path / "sessions"
    telegram = DummyTelegramManager()
    file_manager = DummyFileManager()
    # Build minimal AgentManager
    from src.agents.agent_manager import AgentManager
    agent_manager = AgentManager(file_manager, telegram)  # type: ignore[arg-type]
    # Replace the real agent with dummy agent for alice
    agent_manager.agents["alice"] = DummyAgent()  # type: ignore[index]

    session_mgr = DummySessionManager(str(sessions_dir), file_manager)  # type: ignore[arg-type]

    # bridge uses task_tracker from session_mgr
    bridge = AgentBridge(session_mgr, agent_manager)  # type: ignore[arg-type]

    # Assign task
    ok = bridge.assign_task_to_worker("alice", "Calculate coverage")
    assert ok

    current_task = sessions_dir / "alice" / "current_task.md"
    assert current_task.exists(), "Task file must be created"

    # Simulate worker writing some coverage value then marking complete
    with current_task.open("a", encoding="utf-8") as f:
        f.write("\nOverall coverage: 82%\n")

    # archive file to completed_tasks via task_tracker
    session_mgr.task_tracker.mark_task_complete("alice")

    # mark worker session finished
    session_mgr.finish_task("alice")

    # Bridge detects completion directly
    bridge._handle_task_completion("alice")  # protected, but OK for test

    # A message should be sent via telegram manager containing coverage summary
    assert telegram.sent, "No message sent through TelegramManager"
    last_msg = telegram.sent[-1]
    assert "coverage" in last_msg.lower() or "summary" in last_msg.lower()
