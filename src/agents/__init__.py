"""
Agent module for communication agents.
Handles chat-based communication between users and AI employees.
"""

from .agent_manager import AgentManager
from .base_communication_agent import BaseCommunicationAgent
from .communication_agent import CommunicationAgent

__all__ = ['BaseCommunicationAgent', 'CommunicationAgent', 'AgentManager']