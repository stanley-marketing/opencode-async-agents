"""
Chat module for Telegram integration with AI employees.
Handles group chat communication, @mentions, and agent coordination.
"""

from .telegram_manager import TelegramManager
from .message_parser import MessageParser
from .chat_config import ChatConfig

__all__ = ['TelegramManager', 'MessageParser', 'ChatConfig']