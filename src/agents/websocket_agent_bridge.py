# SPDX-License-Identifier: MIT
"""
WebSocket Agent Bridge
Enhances agent communication with real-time WebSocket capabilities.
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict

from ..chat.message_parser import ParsedMessage
from ..chat.message_persistence import get_message_persistence, MessagePersistence
from ..auth.websocket_auth import get_authenticator, WebSocketAuthenticator

logger = logging.getLogger(__name__)


@dataclass
class AgentStatus:
    """Real-time agent status information"""
    agent_name: str
    role: str
    status: str  # 'idle', 'working', 'stuck', 'completed'
    current_task: Optional[str]
    progress: float
    last_activity: datetime
    session_id: Optional[str]
    connected_users: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['last_activity'] = self.last_activity.isoformat()
        return data


@dataclass
class TaskNotification:
    """Task-related notification"""
    type: str  # 'assigned', 'started', 'progress', 'completed', 'failed'
    agent_name: str
    task_id: str
    task_description: str
    progress: float
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class WebSocketAgentBridge:
    """
    Bridge between agents and WebSocket communication.
    Provides real-time agent status updates, task notifications, and enhanced communication.
    """
    
    def __init__(self, agent_manager, session_manager, websocket_manager):
        """
        Initialize WebSocket agent bridge.
        
        Args:
            agent_manager: AgentManager instance
            session_manager: Session manager for task tracking
            websocket_manager: WebSocket manager for real-time communication
        """
        self.agent_manager = agent_manager
        self.session_manager = session_manager
        self.websocket_manager = websocket_manager
        
        # Message persistence for chat history
        self.message_persistence = get_message_persistence()
        
        # Authentication for secure connections
        self.authenticator = get_authenticator()
        
        # Real-time state tracking
        self.agent_statuses: Dict[str, AgentStatus] = {}
        self.active_tasks: Dict[str, TaskNotification] = {}
        self.user_subscriptions: Dict[str, Set[str]] = {}  # user_id -> set of agent_names
        
        # Event handlers
        self.status_handlers: List[Callable] = []
        self.task_handlers: List[Callable] = []
        self.message_handlers: List[Callable] = []
        
        # Background monitoring
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Set up message handling
        self._setup_message_handling()
        
        logger.info("WebSocket agent bridge initialized")
        
    def _setup_message_handling(self):
        """Set up message handling for WebSocket communication"""
        try:
            # Add message handler to WebSocket manager
            if hasattr(self.websocket_manager, 'add_message_handler'):
                self.websocket_manager.add_message_handler(self._handle_websocket_message)
                
            # Enhance agent manager with real-time capabilities
            self._enhance_agent_manager()
            
            # Enhance session manager with real-time notifications
            self._enhance_session_manager()
            
            logger.info("Message handling configured")
            
        except Exception as e:
            logger.error(f"Failed to setup message handling: {e}")
            
    def _enhance_agent_manager(self):
        """Enhance agent manager with real-time WebSocket capabilities"""
        try:
            # Store original methods
            original_handle_message = self.agent_manager.handle_message
            original_request_help = self.agent_manager.request_help_for_agent
            original_notify_completion = self.agent_manager.notify_task_completion
            
            # Enhanced message handling
            def enhanced_handle_message(message: ParsedMessage):
                # Store message in persistence
                asyncio.create_task(self._store_message(message))
                
                # Call original handler
                result = original_handle_message(message)
                
                # Broadcast message to WebSocket clients
                self._broadcast_message_update(message)
                
                # Update agent statuses
                self._update_agent_statuses_from_message(message)
                
                return result
                
            # Enhanced help requests
            def enhanced_request_help(employee_name: str, task: str, progress: str, issue: str = ""):
                result = original_request_help(employee_name, task, progress, issue)
                
                if result:
                    # Broadcast help request
                    self._broadcast_help_request(employee_name, task, progress, issue)
                    
                    # Update agent status
                    self._update_agent_status(employee_name, 'stuck', task, 0.0)
                    
                return result
                
            # Enhanced completion notifications
            def enhanced_notify_completion(employee_name: str, task: str, task_output: str = None):
                result = original_notify_completion(employee_name, task, task_output)
                
                if result:
                    # Broadcast completion
                    self._broadcast_task_completion(employee_name, task, task_output)
                    
                    # Update agent status
                    self._update_agent_status(employee_name, 'completed', task, 100.0)
                    
                return result
                
            # Replace methods
            self.agent_manager.handle_message = enhanced_handle_message
            self.agent_manager.request_help_for_agent = enhanced_request_help
            self.agent_manager.notify_task_completion = enhanced_notify_completion
            
            logger.info("Agent manager enhanced with WebSocket capabilities")
            
        except Exception as e:
            logger.error(f"Failed to enhance agent manager: {e}")
            
    def _enhance_session_manager(self):
        """Enhance session manager with real-time task notifications"""
        try:
            # Store original methods
            original_start_task = self.session_manager.start_employee_task
            original_stop_task = self.session_manager.stop_employee_task
            
            # Enhanced task starting
            def enhanced_start_task(employee_name: str, task_description: str, model: str = None, mode: str = "build"):
                session_id = original_start_task(employee_name, task_description, model, mode)
                
                if session_id:
                    # Create task notification
                    task_notification = TaskNotification(
                        type='started',
                        agent_name=employee_name,
                        task_id=session_id,
                        task_description=task_description,
                        progress=0.0,
                        timestamp=datetime.now(),
                        metadata={'model': model, 'mode': mode}
                    )
                    
                    # Store and broadcast
                    self.active_tasks[session_id] = task_notification
                    self._broadcast_task_notification(task_notification)
                    
                    # Update agent status
                    self._update_agent_status(employee_name, 'working', task_description, 0.0, session_id)
                    
                return session_id
                
            # Enhanced task stopping
            def enhanced_stop_task(employee_name: str):
                # Get session info before stopping
                active_sessions = self.session_manager.get_active_sessions()
                session_info = active_sessions.get(employee_name)
                
                result = original_stop_task(employee_name)
                
                if session_info:
                    # Create stop notification
                    task_notification = TaskNotification(
                        type='stopped',
                        agent_name=employee_name,
                        task_id=session_info.get('session_id', ''),
                        task_description=session_info.get('task', ''),
                        progress=0.0,
                        timestamp=datetime.now(),
                        metadata={}
                    )
                    
                    # Broadcast and clean up
                    self._broadcast_task_notification(task_notification)
                    
                    # Remove from active tasks
                    session_id = session_info.get('session_id')
                    if session_id and session_id in self.active_tasks:
                        del self.active_tasks[session_id]
                        
                    # Update agent status
                    self._update_agent_status(employee_name, 'idle', None, 0.0)
                    
                return result
                
            # Replace methods
            self.session_manager.start_employee_task = enhanced_start_task
            self.session_manager.stop_employee_task = enhanced_stop_task
            
            logger.info("Session manager enhanced with WebSocket capabilities")
            
        except Exception as e:
            logger.error(f"Failed to enhance session manager: {e}")
            
    async def _handle_websocket_message(self, connection, message_data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        try:
            message_type = message_data.get('type')
            
            if message_type == 'subscribe_agent':
                await self._handle_agent_subscription(connection, message_data)
            elif message_type == 'unsubscribe_agent':
                await self._handle_agent_unsubscription(connection, message_data)
            elif message_type == 'get_agent_status':
                await self._handle_get_agent_status(connection, message_data)
            elif message_type == 'get_active_tasks':
                await self._handle_get_active_tasks(connection, message_data)
            elif message_type == 'send_agent_message':
                await self._handle_send_agent_message(connection, message_data)
            elif message_type == 'get_chat_history':
                await self._handle_get_chat_history(connection, message_data)
            else:
                logger.warning(f"Unknown WebSocket message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            
    async def _handle_agent_subscription(self, connection, message_data: Dict[str, Any]):
        """Handle agent subscription requests"""
        try:
            user_id = getattr(connection, 'user_id', 'unknown')
            agent_name = message_data.get('agent_name')
            
            if not agent_name:
                await connection.send_message({
                    'type': 'error',
                    'message': 'Agent name required for subscription'
                })
                return
                
            # Add subscription
            if user_id not in self.user_subscriptions:
                self.user_subscriptions[user_id] = set()
            self.user_subscriptions[user_id].add(agent_name)
            
            # Send current status
            if agent_name in self.agent_statuses:
                await connection.send_message({
                    'type': 'agent_status',
                    'data': self.agent_statuses[agent_name].to_dict()
                })
                
            logger.info(f"User {user_id} subscribed to agent {agent_name}")
            
        except Exception as e:
            logger.error(f"Error handling agent subscription: {e}")
            
    async def _handle_agent_unsubscription(self, connection, message_data: Dict[str, Any]):
        """Handle agent unsubscription requests"""
        try:
            user_id = getattr(connection, 'user_id', 'unknown')
            agent_name = message_data.get('agent_name')
            
            if user_id in self.user_subscriptions and agent_name:
                self.user_subscriptions[user_id].discard(agent_name)
                
            logger.info(f"User {user_id} unsubscribed from agent {agent_name}")
            
        except Exception as e:
            logger.error(f"Error handling agent unsubscription: {e}")
            
    async def _handle_get_agent_status(self, connection, message_data: Dict[str, Any]):
        """Handle get agent status requests"""
        try:
            agent_name = message_data.get('agent_name')
            
            if agent_name and agent_name in self.agent_statuses:
                await connection.send_message({
                    'type': 'agent_status',
                    'data': self.agent_statuses[agent_name].to_dict()
                })
            else:
                # Get all agent statuses
                all_statuses = {name: status.to_dict() for name, status in self.agent_statuses.items()}
                await connection.send_message({
                    'type': 'all_agent_statuses',
                    'data': all_statuses
                })
                
        except Exception as e:
            logger.error(f"Error handling get agent status: {e}")
            
    async def _handle_get_active_tasks(self, connection, message_data: Dict[str, Any]):
        """Handle get active tasks requests"""
        try:
            active_tasks = {task_id: task.to_dict() for task_id, task in self.active_tasks.items()}
            
            await connection.send_message({
                'type': 'active_tasks',
                'data': active_tasks
            })
            
        except Exception as e:
            logger.error(f"Error handling get active tasks: {e}")
            
    async def _handle_send_agent_message(self, connection, message_data: Dict[str, Any]):
        """Handle sending messages to agents"""
        try:
            user_id = getattr(connection, 'user_id', 'unknown')
            agent_name = message_data.get('agent_name')
            message_text = message_data.get('message')
            
            if not agent_name or not message_text:
                await connection.send_message({
                    'type': 'error',
                    'message': 'Agent name and message required'
                })
                return
                
            # Create parsed message
            parsed_message = ParsedMessage(
                message_id=int(time.time() * 1000),
                text=message_text,
                sender=user_id,
                mentions=[agent_name],
                is_command=False,
                command=None,
                command_args=[],
                reply_to=None,
                timestamp=datetime.now()
            )
            
            # Send to agent manager
            self.agent_manager.handle_message(parsed_message)
            
            await connection.send_message({
                'type': 'message_sent',
                'message': f'Message sent to {agent_name}'
            })
            
        except Exception as e:
            logger.error(f"Error handling send agent message: {e}")
            
    async def _handle_get_chat_history(self, connection, message_data: Dict[str, Any]):
        """Handle get chat history requests"""
        try:
            conversation_id = message_data.get('conversation_id', 'main')
            limit = message_data.get('limit', 50)
            
            # Get messages from persistence
            messages = await self.message_persistence.get_conversation_messages(
                conversation_id, limit=limit
            )
            
            # Convert to dict format
            message_data = [msg.to_dict() for msg in messages]
            
            await connection.send_message({
                'type': 'chat_history',
                'data': {
                    'conversation_id': conversation_id,
                    'messages': message_data
                }
            })
            
        except Exception as e:
            logger.error(f"Error handling get chat history: {e}")
            
    async def _store_message(self, message: ParsedMessage):
        """Store message in persistence"""
        try:
            await self.message_persistence.store_message(
                message_id=str(message.message_id),
                conversation_id='main',  # Default conversation
                sender=message.sender,
                text=message.text,
                message_type='chat_message',
                mentions=message.mentions,
                metadata={
                    'is_command': message.is_command,
                    'command': message.command,
                    'command_args': message.command_args
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            
    def _broadcast_message_update(self, message: ParsedMessage):
        """Broadcast message update to WebSocket clients"""
        try:
            broadcast_data = {
                'type': 'message_update',
                'data': {
                    'message_id': message.message_id,
                    'sender': message.sender,
                    'text': message.text,
                    'mentions': message.mentions,
                    'timestamp': message.timestamp.isoformat(),
                    'is_command': message.is_command
                }
            }
            
            self._send_websocket_broadcast(broadcast_data)
            
        except Exception as e:
            logger.error(f"Failed to broadcast message update: {e}")
            
    def _broadcast_help_request(self, employee_name: str, task: str, progress: str, issue: str):
        """Broadcast help request to WebSocket clients"""
        try:
            broadcast_data = {
                'type': 'help_request',
                'data': {
                    'agent_name': employee_name,
                    'task': task,
                    'progress': progress,
                    'issue': issue,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            self._send_websocket_broadcast(broadcast_data)
            
        except Exception as e:
            logger.error(f"Failed to broadcast help request: {e}")
            
    def _broadcast_task_completion(self, employee_name: str, task: str, task_output: str = None):
        """Broadcast task completion to WebSocket clients"""
        try:
            broadcast_data = {
                'type': 'task_completion',
                'data': {
                    'agent_name': employee_name,
                    'task': task,
                    'output': task_output,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            self._send_websocket_broadcast(broadcast_data)
            
        except Exception as e:
            logger.error(f"Failed to broadcast task completion: {e}")
            
    def _broadcast_task_notification(self, task_notification: TaskNotification):
        """Broadcast task notification to WebSocket clients"""
        try:
            broadcast_data = {
                'type': 'task_notification',
                'data': task_notification.to_dict()
            }
            
            self._send_websocket_broadcast(broadcast_data)
            
        except Exception as e:
            logger.error(f"Failed to broadcast task notification: {e}")
            
    def _update_agent_status(self, agent_name: str, status: str, current_task: str = None, 
                           progress: float = 0.0, session_id: str = None):
        """Update agent status and broadcast to subscribers"""
        try:
            # Get agent info
            agent_info = self.agent_manager.get_agent_status(agent_name)
            role = agent_info.get('role', 'unknown') if agent_info else 'unknown'
            
            # Create or update status
            agent_status = AgentStatus(
                agent_name=agent_name,
                role=role,
                status=status,
                current_task=current_task,
                progress=progress,
                last_activity=datetime.now(),
                session_id=session_id,
                connected_users=self._get_subscribed_users(agent_name)
            )
            
            self.agent_statuses[agent_name] = agent_status
            
            # Broadcast to subscribers
            self._broadcast_agent_status(agent_status)
            
        except Exception as e:
            logger.error(f"Failed to update agent status: {e}")
            
    def _update_agent_statuses_from_message(self, message: ParsedMessage):
        """Update agent statuses based on message activity"""
        try:
            # Update status for mentioned agents
            for agent_name in message.mentions:
                if agent_name in self.agent_statuses:
                    self.agent_statuses[agent_name].last_activity = datetime.now()
                    self._broadcast_agent_status(self.agent_statuses[agent_name])
                    
        except Exception as e:
            logger.error(f"Failed to update agent statuses from message: {e}")
            
    def _broadcast_agent_status(self, agent_status: AgentStatus):
        """Broadcast agent status to subscribed users"""
        try:
            broadcast_data = {
                'type': 'agent_status_update',
                'data': agent_status.to_dict()
            }
            
            # Send to subscribed users only
            subscribed_users = self._get_subscribed_users(agent_status.agent_name)
            self._send_websocket_broadcast(broadcast_data, target_users=subscribed_users)
            
        except Exception as e:
            logger.error(f"Failed to broadcast agent status: {e}")
            
    def _get_subscribed_users(self, agent_name: str) -> List[str]:
        """Get list of users subscribed to an agent"""
        subscribed_users = []
        
        for user_id, subscriptions in self.user_subscriptions.items():
            if agent_name in subscriptions:
                subscribed_users.append(user_id)
                
        return subscribed_users
        
    def _send_websocket_broadcast(self, message: Dict[str, Any], target_users: List[str] = None):
        """Send broadcast message via WebSocket"""
        try:
            if hasattr(self.websocket_manager, '_broadcast_message'):
                # Use WebSocket manager's broadcast method
                if hasattr(self.websocket_manager, 'loop') and self.websocket_manager.loop:
                    asyncio.run_coroutine_threadsafe(
                        self.websocket_manager._broadcast_message(message),
                        self.websocket_manager.loop
                    )
            elif hasattr(self.websocket_manager, 'send_message'):
                # Fallback to send_message
                self.websocket_manager.send_message(
                    json.dumps(message), 
                    sender_name='system'
                )
                
        except Exception as e:
            logger.error(f"Failed to send WebSocket broadcast: {e}")
            
    def start_monitoring(self):
        """Start background monitoring of agent statuses"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("WebSocket agent bridge monitoring started")
        
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
            
        logger.info("WebSocket agent bridge monitoring stopped")
        
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Update agent statuses from session manager
                self._sync_agent_statuses()
                
                # Clean up old subscriptions
                self._cleanup_subscriptions()
                
                # Sleep for monitoring interval
                time.sleep(30)  # 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Short sleep on error
                
    def _sync_agent_statuses(self):
        """Sync agent statuses with session manager"""
        try:
            active_sessions = self.session_manager.get_active_sessions()
            
            # Update statuses for active sessions
            for employee_name, session_info in active_sessions.items():
                status = 'working' if session_info.get('is_running') else 'idle'
                task = session_info.get('task', '')
                session_id = session_info.get('session_id')
                
                self._update_agent_status(employee_name, status, task, 0.0, session_id)
                
            # Mark inactive agents as idle
            all_agents = self.agent_manager.list_active_agents()
            for agent_name in all_agents:
                if agent_name not in active_sessions and agent_name in self.agent_statuses:
                    if self.agent_statuses[agent_name].status != 'idle':
                        self._update_agent_status(agent_name, 'idle')
                        
        except Exception as e:
            logger.error(f"Failed to sync agent statuses: {e}")
            
    def _cleanup_subscriptions(self):
        """Clean up old subscriptions"""
        try:
            # Remove empty subscription sets
            empty_users = [user_id for user_id, subs in self.user_subscriptions.items() if not subs]
            for user_id in empty_users:
                del self.user_subscriptions[user_id]
                
        except Exception as e:
            logger.error(f"Failed to cleanup subscriptions: {e}")
            
    def get_bridge_status(self) -> Dict[str, Any]:
        """Get bridge status information"""
        return {
            'monitoring_active': self.monitoring_active,
            'agent_statuses': len(self.agent_statuses),
            'active_tasks': len(self.active_tasks),
            'user_subscriptions': len(self.user_subscriptions),
            'total_subscriptions': sum(len(subs) for subs in self.user_subscriptions.values()),
            'message_handlers': len(self.message_handlers),
            'status_handlers': len(self.status_handlers),
            'task_handlers': len(self.task_handlers)
        }
        
    def get_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get all agent statuses"""
        return {name: status.to_dict() for name, status in self.agent_statuses.items()}
        
    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all active tasks"""
        return {task_id: task.to_dict() for task_id, task in self.active_tasks.items()}


# Factory function for easy creation
def create_websocket_agent_bridge(agent_manager, session_manager, websocket_manager) -> WebSocketAgentBridge:
    """
    Factory function to create WebSocket agent bridge.
    
    Args:
        agent_manager: AgentManager instance
        session_manager: Session manager instance
        websocket_manager: WebSocket manager instance
        
    Returns:
        WebSocketAgentBridge instance
    """
    return WebSocketAgentBridge(agent_manager, session_manager, websocket_manager)