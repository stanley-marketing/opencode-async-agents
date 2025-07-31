"""
Telegram manager for handling bot communication.
Manages message sending, receiving, and webhook/polling setup.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import aiohttp
import threading
from queue import Queue, Empty

from .chat_config import config
from .message_parser import MessageParser, ParsedMessage

logger = logging.getLogger(__name__)

class TelegramManager:
    """Manages Telegram bot communication and message handling"""
    
    def __init__(self):
        self.bot_token = config.bot_token
        self.chat_id = config.chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        self.message_parser = MessageParser()
        self.message_queue = Queue()
        self.message_handlers: List[Callable[[ParsedMessage], None]] = []
        
        # Rate limiting
        self.last_message_time = {}
        self.message_count = {}
        
        # Polling state
        self.is_polling = False
        self.polling_thread = None
        self.last_update_id = 0
        
    def add_message_handler(self, handler: Callable[[ParsedMessage], None]):
        """Add a message handler function"""
        self.message_handlers.append(handler)
    
    def start_polling(self):
        """Start polling for messages in a background thread"""
        if self.is_polling:
            logger.warning("Polling is already running")
            return
        
        if not config.is_configured():
            logger.error("Telegram bot not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            return
        
        self.is_polling = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        logger.info("Started Telegram polling")
    
    def stop_polling(self):
        """Stop polling for messages"""
        self.is_polling = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        logger.info("Stopped Telegram polling")
    
    def _polling_loop(self):
        """Main polling loop running in background thread"""
        while self.is_polling:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._process_update(update)
                time.sleep(1)  # Poll every second
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _get_updates(self) -> List[Dict]:
        """Get updates from Telegram API"""
        try:
            import requests
            
            url = f"{self.base_url}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 10,
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('ok'):
                logger.error(f"Telegram API error: {data}")
                return []
            
            updates = data.get('result', [])
            if updates:
                self.last_update_id = updates[-1]['update_id']
            
            return updates
            
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []
    
    def _process_update(self, update: Dict):
        """Process a single update from Telegram"""
        message_data = update.get('message')
        if not message_data:
            return
        
        # Only process messages from our chat
        chat_id = str(message_data.get('chat', {}).get('id', ''))
        if chat_id != self.chat_id:
            return
        
        # Parse the message
        parsed_message = self.message_parser.parse_message(message_data)
        
        # Add to queue for processing
        self.message_queue.put(parsed_message)
        
        # Notify handlers
        for handler in self.message_handlers:
            try:
                handler(parsed_message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    def send_message(self, text: str, sender_name: str = "system", 
                    reply_to: Optional[int] = None) -> bool:
        """Send a message to the chat"""
        
        # Rate limiting check
        if not self._can_send_message(sender_name):
            logger.warning(f"Rate limit exceeded for {sender_name}")
            return False
        
        # Format message with sender
        if sender_name != "system":
            formatted_text = f"{config.get_bot_name(sender_name)}: {text}"
        else:
            formatted_text = text
        
        # Truncate if too long
        if len(formatted_text) > config.max_message_length:
            formatted_text = formatted_text[:config.max_message_length-3] + "..."
        
        try:
            import requests
            
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': formatted_text,
                'parse_mode': 'Markdown'
            }
            
            if reply_to:
                data['reply_to_message_id'] = reply_to
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                self._record_message_sent(sender_name)
                logger.info(f"Message sent by {sender_name}")
                return True
            else:
                logger.error(f"Failed to send message: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def _can_send_message(self, sender_name: str) -> bool:
        """Check if sender can send a message (rate limiting)"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old message counts
        if sender_name in self.message_count:
            self.message_count[sender_name] = [
                timestamp for timestamp in self.message_count[sender_name]
                if timestamp > hour_ago
            ]
        else:
            self.message_count[sender_name] = []
        
        # Check rate limit
        if len(self.message_count[sender_name]) >= config.max_messages_per_hour:
            return False
        
        # Check minimum delay between messages
        if sender_name in self.last_message_time:
            time_since_last = now - self.last_message_time[sender_name]
            if time_since_last.total_seconds() < config.response_delay_seconds:
                return False
        
        return True
    
    def _record_message_sent(self, sender_name: str):
        """Record that a message was sent for rate limiting"""
        now = datetime.now()
        self.last_message_time[sender_name] = now
        
        if sender_name not in self.message_count:
            self.message_count[sender_name] = []
        self.message_count[sender_name].append(now)
    
    def get_chat_info(self) -> Dict:
        """Get information about the chat"""
        try:
            import requests
            
            url = f"{self.base_url}/getChat"
            params = {'chat_id': self.chat_id}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('ok'):
                return data.get('result', {})
            else:
                logger.error(f"Failed to get chat info: {data}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting chat info: {e}")
            return {}
    
    def is_connected(self) -> bool:
        """Check if bot is connected and working"""
        try:
            import requests
            
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return data.get('ok', False)
            
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False