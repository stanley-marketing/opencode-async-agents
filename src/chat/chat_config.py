"""
Configuration for Telegram chat integration.
Handles bot tokens, chat IDs, and other settings.
"""

import os
from typing import Optional
from dataclasses import dataclass

@dataclass
class ChatConfig:
    """Configuration for Telegram chat system"""
    
    # Telegram Bot Configuration
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    webhook_url: Optional[str] = None
    
    # Agent Behavior Configuration
    stuck_timeout_minutes: int = 10
    max_messages_per_hour: int = 20
    response_delay_seconds: int = 2
    help_offer_probability: float = 0.3  # 30% chance to offer help
    
    # Message Configuration
    bot_name_suffix: str = "-bot"
    max_message_length: int = 4096  # Telegram limit
    
    def __post_init__(self):
        """Load configuration from environment variables"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', self.bot_token)
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', self.chat_id)
        self.webhook_url = os.getenv('TELEGRAM_WEBHOOK_URL', self.webhook_url)
    
    def is_configured(self) -> bool:
        """Check if minimum configuration is available"""
        return bool(self.bot_token and self.chat_id)
    
    def get_bot_name(self, employee_name: str) -> str:
        """Get the bot name for an employee"""
        return f"{employee_name}{self.bot_name_suffix}"

# Global configuration instance
config = ChatConfig()