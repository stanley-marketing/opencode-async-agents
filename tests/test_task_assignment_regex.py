import pytest
from datetime import datetime

from src.agents.communication_agent import CommunicationAgent
from src.chat.message_parser import ParsedMessage


def test_react_response_triggers_task_assignment(monkeypatch):
    """If the ReAct agent response contains a 'Started coding task:' line
    the communication agent should still trigger `on_task_assigned` even
    when the original user message cannot be parsed into a task description.
    """

    # Collect the task description passed to the callback
    captured_task_descriptions = []

    def dummy_on_task_assigned(task_description: str):
        captured_task_descriptions.append(task_description)
        return True  # Simulate successful assignment via AgentBridge

    # Instantiate a communication agent
    comm_agent = CommunicationAgent(employee_name="elad", role="python-developer")
    comm_agent.on_task_assigned = dummy_on_task_assigned

    # Patch the agent's message parser so it fails to find a description in the user text
    monkeypatch.setattr(
        comm_agent.message_parser,
        "extract_task_description",
        lambda text, employee: "",
    )

    # Stub ReAct agent that returns a response including the task start line
    class DummyReActAgent:
        def handle_message(self, text, context=None, mode="forward"):
            return (
                "✅ Started coding task: Run test coverage analysis and report coverage percentage\n"
                "Task ID: task_1234\nPriority: high"
            )

    comm_agent.react_agent = DummyReActAgent()

    # Create a parsed message that mentions the agent but lacks a clear task description
    parsed_msg = ParsedMessage(
        message_id=1,
        text="@elad could you handle this for me?",
        sender="tester",
        timestamp=datetime.utcnow(),
        mentions=["elad"],
        is_command=False,
        command=None,
        command_args=[],
        reply_to=None,
    )

    # Act – process the mention
    _ = comm_agent.handle_mention(parsed_msg)

    # Assert – the fallback regex captured the task description and triggered the callback
    assert captured_task_descriptions, "on_task_assigned was not called"
    assert (
        captured_task_descriptions[0]
        == "Run test coverage analysis and report coverage percentage"
    ), "Incorrect task description extracted from ReAct response"
    # The agent's internal state should reflect the new task
    assert comm_agent.current_task == captured_task_descriptions[0]
