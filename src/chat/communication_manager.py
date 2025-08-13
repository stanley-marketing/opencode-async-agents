# SPDX-License-Identifier: MIT
"""
Unified communication manager supporting both Telegram and WebSocket transports.
Provides seamless switching between communication backends.
"""

import logging
import os
from typing import Callable, Optional, Dict, Any, List
from .message_parser import ParsedMessage

logger = logging.getLogger(__name__)


class CommunicationManager:
    """
    Unified interface for communication that supports multiple transport layers.
    Provides the same interface as TelegramManager for backward compatibility.
    """
    
    def __init__(self, transport_type: str = None, **kwargs):
        """
        Initialize communication manager with specified transport.
        
        Args:
            transport_type: 'telegram', 'websocket', or 'auto' (default)
            **kwargs: Transport-specific configuration
        """
        self.transport_type = transport_type or self._detect_transport_type()
        self.transport = None
        self._initialize_transport(**kwargs)
        
    def _detect_transport_type(self) -> str:
        """Auto-detect which transport to use based on environment"""
        # Check environment variable first
        env_transport = os.environ.get('OPENCODE_TRANSPORT', '').lower()
        if env_transport in ['telegram', 'websocket']:
            return env_transport
            
        # Check if in safe mode (prefer WebSocket)
        safe_mode = os.environ.get('OPENCODE_SAFE_MODE', '').lower() in ['true', '1', 'yes']
        if safe_mode:
            return 'websocket'
            
        # Check if Telegram is configured
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if telegram_token and telegram_chat_id:
            return 'telegram'
        else:
            return 'websocket'
            
    def _initialize_transport(self, **kwargs):
        """Initialize the selected transport"""
        try:
            if self.transport_type == 'telegram':
                from .telegram_manager import TelegramManager
                self.transport = TelegramManager()
                logger.info("Initialized Telegram transport")
                
            elif self.transport_type == 'websocket':
                from .websocket_manager import WebSocketManager
                
                # Extract WebSocket-specific config
                host = kwargs.get('host', os.environ.get('WEBSOCKET_HOST', 'localhost'))
                port = int(kwargs.get('port', os.environ.get('WEBSOCKET_PORT', 8765)))
                
                self.transport = WebSocketManager(host=host, port=port)
                logger.info(f"Initialized WebSocket transport on {host}:{port}")
                
            else:
                raise ValueError(f"Unsupported transport type: {self.transport_type}")
                
        except ImportError as e:
            logger.error(f"Failed to import transport {self.transport_type}: {e}")
            # Fallback to the other transport
            self._fallback_transport(**kwargs)
        except Exception as e:
            logger.error(f"Failed to initialize {self.transport_type} transport: {e}")
            self._fallback_transport(**kwargs)
            
    def _fallback_transport(self, **kwargs):
        """Fallback to alternative transport if primary fails"""
        try:
            if self.transport_type == 'telegram':
                logger.warning("Falling back to WebSocket transport")
                from .websocket_manager import WebSocketManager
                host = kwargs.get('host', 'localhost')
                port = int(kwargs.get('port', 8765))
                self.transport = WebSocketManager(host=host, port=port)
                self.transport_type = 'websocket'
                
            elif self.transport_type == 'websocket':
                logger.warning("Falling back to Telegram transport")
                from .telegram_manager import TelegramManager
                self.transport = TelegramManager()
                self.transport_type = 'telegram'
                
        except Exception as e:
            logger.error(f"Fallback transport also failed: {e}")
            raise RuntimeError("No communication transport available")
            
    # Delegate all TelegramManager interface methods to the transport
    
    def add_message_handler(self, handler: Callable[[ParsedMessage], None]):
        """Add a message handler function"""
        return self.transport.add_message_handler(handler)
        
    def start_polling(self):
        """Start message polling/server"""
        return self.transport.start_polling()
        
    def stop_polling(self):
        """Stop message polling/server"""
        return self.transport.stop_polling()
        
    def send_message(self, text: str, sender_name: str = "system", 
                    reply_to: Optional[int] = None) -> bool:
        """Send a message"""
        return self.transport.send_message(text, sender_name, reply_to)
        
    def is_connected(self) -> bool:
        """Check if transport is connected and working"""
        return self.transport.is_connected()
        
    # Transport-specific methods
    
    def get_transport_type(self) -> str:
        """Get the current transport type"""
        return self.transport_type
        
    def get_transport_info(self) -> Dict[str, Any]:
        """Get information about the current transport"""
        info = {
            'type': self.transport_type,
            'connected': self.is_connected()
        }
        
        # Add transport-specific information
        if self.transport_type == 'websocket' and hasattr(self.transport, 'get_server_stats'):
            info.update(self.transport.get_server_stats())
            info['connected_users'] = self.transport.get_connected_users()
            
        elif self.transport_type == 'telegram' and hasattr(self.transport, 'get_webhook_info'):
            info['webhook_info'] = self.transport.get_webhook_info()
            info['chat_info'] = self.transport.get_chat_info()
            
        return info
        
    def switch_transport(self, new_transport_type: str, **kwargs) -> bool:
        """
        Switch to a different transport type.
        
        Args:
            new_transport_type: 'telegram' or 'websocket'
            **kwargs: Transport-specific configuration
            
        Returns:
            bool: True if switch was successful
        """
        if new_transport_type == self.transport_type:
            logger.info(f"Already using {new_transport_type} transport")
            return True
            
        try:
            # Stop current transport
            if self.transport:
                self.transport.stop_polling()
                
            # Initialize new transport
            old_transport_type = self.transport_type
            self.transport_type = new_transport_type
            self._initialize_transport(**kwargs)
            
            logger.info(f"Successfully switched from {old_transport_type} to {new_transport_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch to {new_transport_type}: {e}")
            return False
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get communication statistics"""
        stats = {
            'transport_type': self.transport_type,
            'connected': self.is_connected()
        }
        
        # Add transport-specific stats
        if hasattr(self.transport, 'get_server_stats'):
            stats.update(self.transport.get_server_stats())
        elif hasattr(self.transport, 'last_message_time'):
            stats['rate_limiting'] = {
                'last_message_times': len(self.transport.last_message_time),
                'message_counts': len(self.transport.message_count)
            }
            
        return stats


# Factory function for easy instantiation
def create_communication_manager(transport_type: str = None, **kwargs) -> CommunicationManager:
    """
    Factory function to create a communication manager.
    
    Args:
        transport_type: 'telegram', 'websocket', or None for auto-detection
        **kwargs: Transport-specific configuration
        
    Returns:
        CommunicationManager instance
    """
    return CommunicationManager(transport_type=transport_type, **kwargs)


# Backward compatibility alias
TelegramManager = CommunicationManager