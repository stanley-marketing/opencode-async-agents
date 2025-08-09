"""
Chat module for Telegram integration with AI employees.
Handles group chat communication, @mentions, and agent coordination.
"""

from .chat_config import ChatConfig
from .message_parser import MessageParser
from .telegram_manager import TelegramManager

__all__ = ['TelegramManager', 'MessageParser', 'ChatConfig']