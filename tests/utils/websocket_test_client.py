"""
WebSocket test client utilities for E2E testing.
Provides reusable test client and helper functions.
"""

import asyncio
import json
import websockets
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import time


class WebSocketTestClient:
    """Enhanced test client for WebSocket E2E testing"""
    
    def __init__(self, url: str, user_id: str, role: str = "user"):
        self.url = url
        self.user_id = user_id
        self.role = role
        self.websocket = None
        self.messages = []
        self.connected = False
        self.message_handlers = []
        self.connection_handlers = []
        self.error_handlers = []
        
    async def connect(self, timeout: int = 10) -> bool:
        """Connect to WebSocket server with timeout"""
        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.url), 
                timeout=timeout
            )
            
            # Send authentication
            auth_message = {
                'type': 'auth',
                'user_id': self.user_id,
                'role': self.role
            }
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for auth success
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=timeout
            )
            auth_response = json.loads(response)
            
            if auth_response.get('type') == 'auth_success':
                self.connected = True
                
                # Notify connection handlers
                for handler in self.connection_handlers:
                    handler('connected')
                    
                return True
            else:
                raise Exception(f"Authentication failed: {auth_response}")
                
        except Exception as e:
            for handler in self.error_handlers:
                handler(f"Connection failed: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            
            # Notify connection handlers
            for handler in self.connection_handlers:
                handler('disconnected')
                
    async def send_message(self, text: str, reply_to: Optional[int] = None):
        """Send a chat message"""
        if not self.connected:
            raise Exception("Not connected")
            
        message = {
            'type': 'chat_message',
            'data': {
                'text': text,
                'reply_to': reply_to
            }
        }
        
        await self.websocket.send(json.dumps(message))
        
    async def send_typing(self, is_typing: bool):
        """Send typing indicator"""
        if not self.connected:
            return
            
        message = {
            'type': 'typing',
            'data': {
                'is_typing': is_typing
            }
        }
        
        await self.websocket.send(json.dumps(message))
        
    async def send_custom_message(self, message: Dict[str, Any]):
        """Send custom message for testing edge cases"""
        if not self.connected:
            raise Exception("Not connected")
            
        await self.websocket.send(json.dumps(message))
        
    async def wait_for_message(self, timeout: int = 10, message_type: Optional[str] = None) -> Optional[Dict]:
        """Wait for a message from the server, optionally filtering by type"""
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            message = json.loads(response)
            self.messages.append(message)
            
            # Notify handlers
            for handler in self.message_handlers:
                handler(message)
            
            # Filter by type if specified
            if message_type and message.get('type') != message_type:
                return await self.wait_for_message(timeout, message_type)
                
            return message
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            for handler in self.error_handlers:
                handler(f"Error receiving message: {e}")
            return None
            
    async def wait_for_messages(self, count: int, timeout: int = 10, 
                               message_type: Optional[str] = None) -> List[Dict]:
        """Wait for multiple messages"""
        messages = []
        start_time = time.time()
        
        while len(messages) < count and (time.time() - start_time) < timeout:
            message = await self.wait_for_message(timeout=1, message_type=message_type)
            if message:
                messages.append(message)
                
        return messages
        
    async def wait_for_agent_response(self, agent_name: str, timeout: int = 10) -> Optional[Dict]:
        """Wait for a response from a specific agent"""
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            message = await self.wait_for_message(timeout=1, message_type='chat_message')
            if message and message.get('data', {}).get('sender') == f"{agent_name}-bot":
                return message
                
        return None
        
    async def expect_message_sequence(self, expected_types: List[str], timeout: int = 10) -> List[Dict]:
        """Wait for a sequence of message types in order"""
        messages = []
        
        for expected_type in expected_types:
            message = await self.wait_for_message(timeout, expected_type)
            if not message:
                raise AssertionError(f"Expected message type '{expected_type}' not received")
            messages.append(message)
            
        return messages
        
    def add_message_handler(self, handler: Callable[[Dict], None]):
        """Add a message handler"""
        self.message_handlers.append(handler)
        
    def add_connection_handler(self, handler: Callable[[str], None]):
        """Add a connection status handler"""
        self.connection_handlers.append(handler)
        
    def add_error_handler(self, handler: Callable[[str], None]):
        """Add an error handler"""
        self.error_handlers.append(handler)
        
    def get_messages_by_type(self, message_type: str) -> List[Dict]:
        """Get all received messages of a specific type"""
        return [msg for msg in self.messages if msg.get('type') == message_type]
        
    def get_messages_by_sender(self, sender: str) -> List[Dict]:
        """Get all messages from a specific sender"""
        return [msg for msg in self.messages 
                if msg.get('type') == 'chat_message' 
                and msg.get('data', {}).get('sender') == sender]
        
    def clear_messages(self):
        """Clear message history"""
        self.messages.clear()


class WebSocketTestScenario:
    """Helper class for running complex test scenarios"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.clients = {}
        self.scenario_data = {}
        
    async def create_client(self, user_id: str, role: str = "user") -> WebSocketTestClient:
        """Create and connect a test client"""
        client = WebSocketTestClient(self.server_url, user_id, role)
        success = await client.connect()
        
        if not success:
            raise Exception(f"Failed to connect client {user_id}")
            
        self.clients[user_id] = client
        return client
        
    async def cleanup_clients(self):
        """Disconnect all clients"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
        
    async def simulate_conversation(self, conversation: List[Dict[str, str]], delay: float = 0.5):
        """Simulate a conversation between multiple users"""
        for message_data in conversation:
            user_id = message_data['user']
            text = message_data['text']
            
            if user_id not in self.clients:
                raise Exception(f"Client {user_id} not found")
                
            await self.clients[user_id].send_message(text)
            await asyncio.sleep(delay)
            
    async def test_agent_mention_flow(self, user_id: str, agent_name: str, task: str) -> Dict:
        """Test complete agent mention and response flow"""
        if user_id not in self.clients:
            raise Exception(f"Client {user_id} not found")
            
        client = self.clients[user_id]
        
        # Send mention
        mention_text = f"@{agent_name} {task}"
        await client.send_message(mention_text)
        
        # Wait for agent response
        agent_response = await client.wait_for_agent_response(agent_name, timeout=10)
        
        return {
            'mention_sent': mention_text,
            'agent_response': agent_response,
            'success': agent_response is not None
        }
        
    async def test_multi_user_collaboration(self, users: List[str], topic: str) -> Dict:
        """Test collaboration between multiple users"""
        results = {
            'messages_sent': 0,
            'messages_received': {},
            'typing_indicators': 0
        }
        
        # Each user sends a message about the topic
        for user_id in users:
            if user_id not in self.clients:
                continue
                
            client = self.clients[user_id]
            await client.send_message(f"Working on {topic} - {user_id}")
            results['messages_sent'] += 1
            
            # Send typing indicator
            await client.send_typing(True)
            await asyncio.sleep(0.5)
            await client.send_typing(False)
            results['typing_indicators'] += 1
            
        # Wait for all messages to be received by all clients
        await asyncio.sleep(2)
        
        # Count messages received by each client
        for user_id, client in self.clients.items():
            if user_id in users:
                chat_messages = client.get_messages_by_type('chat_message')
                results['messages_received'][user_id] = len(chat_messages)
                
        return results
        
    def store_scenario_data(self, key: str, value: Any):
        """Store data for the scenario"""
        self.scenario_data[key] = value
        
    def get_scenario_data(self, key: str) -> Any:
        """Get stored scenario data"""
        return self.scenario_data.get(key)


class WebSocketTestAssertions:
    """Helper class for common WebSocket test assertions"""
    
    @staticmethod
    def assert_message_structure(message: Dict, expected_type: str):
        """Assert message has correct structure"""
        assert message is not None, "Message should not be None"
        assert 'type' in message, "Message should have 'type' field"
        assert message['type'] == expected_type, f"Expected type '{expected_type}', got '{message['type']}'"
        
    @staticmethod
    def assert_chat_message(message: Dict, expected_sender: Optional[str] = None, 
                           expected_text: Optional[str] = None):
        """Assert chat message structure and content"""
        WebSocketTestAssertions.assert_message_structure(message, 'chat_message')
        assert 'data' in message, "Chat message should have 'data' field"
        
        data = message['data']
        assert 'text' in data, "Chat message data should have 'text' field"
        assert 'sender' in data, "Chat message data should have 'sender' field"
        assert 'timestamp' in data, "Chat message data should have 'timestamp' field"
        
        if expected_sender:
            assert data['sender'] == expected_sender, f"Expected sender '{expected_sender}', got '{data['sender']}'"
            
        if expected_text:
            assert expected_text in data['text'], f"Expected text '{expected_text}' not found in '{data['text']}'"
            
    @staticmethod
    def assert_agent_response(message: Dict, agent_name: str):
        """Assert message is a valid agent response"""
        WebSocketTestAssertions.assert_chat_message(message, f"{agent_name}-bot")
        
        # Agent responses should contain acknowledgment or helpful content
        text = message['data']['text'].lower()
        helpful_indicators = ['got it', 'sure', 'on it', 'will do', 'help', 'try', 'consider']
        assert any(indicator in text for indicator in helpful_indicators), \
            f"Agent response doesn't seem helpful: {text}"
            
    @staticmethod
    def assert_typing_indicator(message: Dict, expected_user: str, expected_typing: bool):
        """Assert typing indicator message"""
        WebSocketTestAssertions.assert_message_structure(message, 'typing')
        assert 'data' in message, "Typing message should have 'data' field"
        
        data = message['data']
        assert data['user_id'] == expected_user, f"Expected user '{expected_user}', got '{data['user_id']}'"
        assert data['is_typing'] == expected_typing, f"Expected typing '{expected_typing}', got '{data['is_typing']}'"
        
    @staticmethod
    def assert_user_status(message: Dict, expected_user: str, expected_status: str):
        """Assert user status message"""
        WebSocketTestAssertions.assert_message_structure(message, 'user_status')
        assert 'data' in message, "User status message should have 'data' field"
        
        data = message['data']
        assert data['user_id'] == expected_user, f"Expected user '{expected_user}', got '{data['user_id']}'"
        assert data['status'] == expected_status, f"Expected status '{expected_status}', got '{data['status']}'"


# Utility functions for common test patterns

async def create_test_clients(server_url: str, users: List[Dict[str, str]]) -> Dict[str, WebSocketTestClient]:
    """Create multiple test clients"""
    clients = {}
    
    for user_data in users:
        user_id = user_data['user_id']
        role = user_data.get('role', 'user')
        
        client = WebSocketTestClient(server_url, user_id, role)
        success = await client.connect()
        
        if not success:
            # Cleanup already connected clients
            for existing_client in clients.values():
                await existing_client.disconnect()
            raise Exception(f"Failed to connect client {user_id}")
            
        clients[user_id] = client
        
    return clients


async def cleanup_test_clients(clients: Dict[str, WebSocketTestClient]):
    """Cleanup multiple test clients"""
    for client in clients.values():
        await client.disconnect()


def create_test_conversation() -> List[Dict[str, str]]:
    """Create a sample conversation for testing"""
    return [
        {'user': 'manager', 'text': '@alice please create a login component'},
        {'user': 'alice', 'text': 'Got it! I\'ll create the login component.'},
        {'user': 'manager', 'text': '@bob can you design the UI for the login?'},
        {'user': 'bob', 'text': 'Sure thing! I\'ll work on the login UI design.'},
        {'user': 'alice', 'text': '@bob what colors should I use for the buttons?'},
        {'user': 'bob', 'text': 'Use primary blue #007bff for the main button.'}
    ]


def create_performance_test_messages(count: int, prefix: str = "Test message") -> List[str]:
    """Create a list of test messages for performance testing"""
    return [f"{prefix} {i}" for i in range(count)]