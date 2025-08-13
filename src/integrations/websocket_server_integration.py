# SPDX-License-Identifier: MIT
"""
WebSocket Server Integration Module
Provides seamless WebSocket integration for all existing servers.
"""

import asyncio
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from ..chat.websocket_manager import WebSocketManager
from ..chat.communication_manager import CommunicationManager

logger = logging.getLogger(__name__)


class WebSocketServerIntegration:
    """
    Integration layer that adds WebSocket support to existing servers.
    Provides backward compatibility while enabling real-time communication.
    """
    
    def __init__(self, host: str = "localhost", websocket_port: int = 8765, 
                 transport_type: str = None):
        """
        Initialize WebSocket integration.
        
        Args:
            host: WebSocket server host
            websocket_port: WebSocket server port
            transport_type: Preferred transport ('websocket', 'telegram', or None for auto)
        """
        self.host = host
        self.websocket_port = websocket_port
        self.transport_type = transport_type
        
        # Communication manager with WebSocket support
        self.communication_manager = CommunicationManager(
            transport_type=transport_type,
            host=host,
            port=websocket_port
        )
        
        # Integration state
        self.is_integrated = False
        self.server_instance = None
        self.agent_manager = None
        self.session_manager = None
        
        # Real-time features
        self.status_broadcasters: List[Callable] = []
        self.task_listeners: List[Callable] = []
        
        logger.info(f"WebSocket integration initialized on {host}:{websocket_port}")
        
    def integrate_with_server(self, server_instance, agent_manager=None, session_manager=None):
        """
        Integrate WebSocket functionality with an existing server.
        
        Args:
            server_instance: The server instance to integrate with
            agent_manager: Agent manager for real-time agent communication
            session_manager: Session manager for task notifications
        """
        try:
            self.server_instance = server_instance
            self.agent_manager = agent_manager
            self.session_manager = session_manager
            
            # Replace the server's communication manager
            if hasattr(server_instance, 'telegram_manager'):
                server_instance.telegram_manager = self.communication_manager
                logger.info("Replaced TelegramManager with CommunicationManager")
                
            if hasattr(server_instance, 'communication_manager'):
                server_instance.communication_manager = self.communication_manager
                logger.info("Updated server's communication manager")
                
            # Set up real-time features
            self._setup_real_time_features()
            
            # Set up agent communication enhancement
            if agent_manager:
                self._setup_agent_communication(agent_manager)
                
            # Set up session management integration
            if session_manager:
                self._setup_session_integration(session_manager)
                
            self.is_integrated = True
            logger.info("WebSocket integration completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to integrate WebSocket with server: {e}")
            raise
            
    def _setup_real_time_features(self):
        """Set up real-time broadcasting features"""
        try:
            # Add status broadcasting
            self.add_status_broadcaster(self._broadcast_server_status)
            
            # Add task progress broadcasting
            self.add_task_listener(self._broadcast_task_progress)
            
            # Set up periodic status updates
            self._start_periodic_broadcasts()
            
            logger.info("Real-time features configured")
            
        except Exception as e:
            logger.error(f"Failed to setup real-time features: {e}")
            
    def _setup_agent_communication(self, agent_manager):
        """Enhance agent communication with WebSocket support"""
        try:
            # Store original methods for fallback
            original_handle_message = agent_manager.handle_message
            original_request_help = agent_manager.request_help_for_agent
            original_notify_completion = agent_manager.notify_task_completion
            
            # Enhance message handling with real-time broadcasting
            def enhanced_handle_message(message):
                result = original_handle_message(message)
                
                # Broadcast agent activity
                self._broadcast_agent_activity({
                    'type': 'message_processed',
                    'sender': message.sender,
                    'mentions': message.mentions,
                    'timestamp': datetime.now().isoformat()
                })
                
                return result
                
            # Enhance help requests with real-time notifications
            def enhanced_request_help(employee_name, task, progress, issue=""):
                result = original_request_help(employee_name, task, progress, issue)
                
                if result:
                    self._broadcast_agent_activity({
                        'type': 'help_requested',
                        'employee': employee_name,
                        'task': task[:100],
                        'progress': progress,
                        'issue': issue,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                return result
                
            # Enhance completion notifications
            def enhanced_notify_completion(employee_name, task, task_output=None):
                result = original_notify_completion(employee_name, task, task_output)
                
                if result:
                    self._broadcast_agent_activity({
                        'type': 'task_completed',
                        'employee': employee_name,
                        'task': task[:100],
                        'timestamp': datetime.now().isoformat()
                    })
                    
                return result
                
            # Replace methods
            agent_manager.handle_message = enhanced_handle_message
            agent_manager.request_help_for_agent = enhanced_request_help
            agent_manager.notify_task_completion = enhanced_notify_completion
            
            logger.info("Agent communication enhanced with WebSocket support")
            
        except Exception as e:
            logger.error(f"Failed to setup agent communication: {e}")
            
    def _setup_session_integration(self, session_manager):
        """Integrate with session manager for task notifications"""
        try:
            # Store original methods
            original_start_task = session_manager.start_employee_task
            original_stop_task = session_manager.stop_employee_task
            
            # Enhance task starting with real-time notifications
            def enhanced_start_task(employee_name, task_description, model=None, mode="build"):
                session_id = original_start_task(employee_name, task_description, model, mode)
                
                if session_id:
                    self._broadcast_task_update({
                        'type': 'task_started',
                        'employee': employee_name,
                        'session_id': session_id,
                        'task': task_description[:100],
                        'model': model,
                        'mode': mode,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                return session_id
                
            # Enhance task stopping
            def enhanced_stop_task(employee_name):
                result = original_stop_task(employee_name)
                
                self._broadcast_task_update({
                    'type': 'task_stopped',
                    'employee': employee_name,
                    'timestamp': datetime.now().isoformat()
                })
                
                return result
                
            # Replace methods
            session_manager.start_employee_task = enhanced_start_task
            session_manager.stop_employee_task = enhanced_stop_task
            
            logger.info("Session management enhanced with WebSocket support")
            
        except Exception as e:
            logger.error(f"Failed to setup session integration: {e}")
            
    def add_status_broadcaster(self, broadcaster: Callable):
        """Add a status broadcaster function"""
        self.status_broadcasters.append(broadcaster)
        
    def add_task_listener(self, listener: Callable):
        """Add a task listener function"""
        self.task_listeners.append(listener)
        
    def _broadcast_server_status(self):
        """Broadcast server status to connected clients"""
        try:
            if not self.server_instance:
                return
                
            status = {
                'type': 'server_status',
                'data': {
                    'timestamp': datetime.now().isoformat(),
                    'active_sessions': len(self.session_manager.get_active_sessions()) if self.session_manager else 0,
                    'total_agents': len(self.agent_manager.agents) if self.agent_manager else 0,
                    'chat_enabled': getattr(self.server_instance, 'chat_enabled', False),
                    'transport_type': self.communication_manager.get_transport_type()
                }
            }
            
            self._send_broadcast(status)
            
        except Exception as e:
            logger.error(f"Failed to broadcast server status: {e}")
            
    def _broadcast_task_progress(self, task_data: Dict[str, Any]):
        """Broadcast task progress updates"""
        try:
            message = {
                'type': 'task_progress',
                'data': task_data
            }
            
            self._send_broadcast(message)
            
        except Exception as e:
            logger.error(f"Failed to broadcast task progress: {e}")
            
    def _broadcast_agent_activity(self, activity_data: Dict[str, Any]):
        """Broadcast agent activity updates"""
        try:
            message = {
                'type': 'agent_activity',
                'data': activity_data
            }
            
            self._send_broadcast(message)
            
        except Exception as e:
            logger.error(f"Failed to broadcast agent activity: {e}")
            
    def _broadcast_task_update(self, task_data: Dict[str, Any]):
        """Broadcast task updates"""
        try:
            message = {
                'type': 'task_update',
                'data': task_data
            }
            
            self._send_broadcast(message)
            
        except Exception as e:
            logger.error(f"Failed to broadcast task update: {e}")
            
    def _send_broadcast(self, message: Dict[str, Any]):
        """Send broadcast message to all connected WebSocket clients"""
        try:
            if (self.communication_manager.get_transport_type() == 'websocket' and 
                hasattr(self.communication_manager.transport, '_broadcast_message')):
                
                # Use asyncio to send the broadcast
                if hasattr(self.communication_manager.transport, 'loop') and self.communication_manager.transport.loop:
                    asyncio.run_coroutine_threadsafe(
                        self.communication_manager.transport._broadcast_message(message),
                        self.communication_manager.transport.loop
                    )
                    
        except Exception as e:
            logger.error(f"Failed to send broadcast: {e}")
            
    def _start_periodic_broadcasts(self):
        """Start periodic status broadcasts"""
        def periodic_broadcast():
            while self.is_integrated:
                try:
                    for broadcaster in self.status_broadcasters:
                        broadcaster()
                        
                    # Wait 30 seconds before next broadcast
                    for _ in range(30):
                        if not self.is_integrated:
                            break
                        threading.Event().wait(1)
                        
                except Exception as e:
                    logger.error(f"Error in periodic broadcast: {e}")
                    
        # Start in background thread
        broadcast_thread = threading.Thread(target=periodic_broadcast, daemon=True)
        broadcast_thread.start()
        
        logger.info("Periodic broadcasts started")
        
    def start_communication(self):
        """Start the communication system"""
        try:
            self.communication_manager.start_polling()
            logger.info(f"Communication system started with {self.communication_manager.get_transport_type()} transport")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start communication system: {e}")
            return False
            
    def stop_communication(self):
        """Stop the communication system"""
        try:
            self.communication_manager.stop_polling()
            self.is_integrated = False
            logger.info("Communication system stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop communication system: {e}")
            
    def switch_transport(self, transport_type: str, **kwargs) -> bool:
        """Switch communication transport"""
        try:
            success = self.communication_manager.switch_transport(transport_type, **kwargs)
            
            if success:
                logger.info(f"Successfully switched to {transport_type} transport")
                
                # Broadcast transport change
                self._broadcast_server_status()
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to switch transport: {e}")
            return False
            
    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration status information"""
        return {
            'integrated': self.is_integrated,
            'transport_type': self.communication_manager.get_transport_type(),
            'transport_info': self.communication_manager.get_transport_info(),
            'connected': self.communication_manager.is_connected(),
            'host': self.host,
            'websocket_port': self.websocket_port,
            'status_broadcasters': len(self.status_broadcasters),
            'task_listeners': len(self.task_listeners)
        }
        
    def get_connected_users(self) -> List[Dict[str, Any]]:
        """Get list of connected WebSocket users"""
        try:
            if (self.communication_manager.get_transport_type() == 'websocket' and 
                hasattr(self.communication_manager.transport, 'get_connected_users')):
                return self.communication_manager.transport.get_connected_users()
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get connected users: {e}")
            return []


# Factory function for easy integration
def create_websocket_integration(host: str = "localhost", websocket_port: int = 8765, 
                                transport_type: str = None) -> WebSocketServerIntegration:
    """
    Factory function to create WebSocket integration.
    
    Args:
        host: WebSocket server host
        websocket_port: WebSocket server port  
        transport_type: Preferred transport type
        
    Returns:
        WebSocketServerIntegration instance
    """
    return WebSocketServerIntegration(host, websocket_port, transport_type)