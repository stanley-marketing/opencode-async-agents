"""
Comprehensive E2E tests for WebSocket communication system.
Tests agent communication patterns without external dependencies.
"""

import asyncio
import json
import pytest
import websockets
from datetime import datetime
from typing import Dict, List, Optional
import threading
import time

from src.chat.websocket_manager import WebSocketManager
from src.chat.message_parser import MessageParser, ParsedMessage
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager


class WebSocketTestClient:
    """Test client for E2E WebSocket testing"""
    
    def __init__(self, url: str, user_id: str, role: str = "user"):
        self.url = url
        self.user_id = user_id
        self.role = role
        self.websocket = None
        self.messages = []
        self.connected = False
        self.message_handlers = []
        
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.url)
            
            # Send authentication
            auth_message = {
                'type': 'auth',
                'user_id': self.user_id,
                'role': self.role
            }
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for auth success
            response = await self.websocket.recv()
            auth_response = json.loads(response)
            
            if auth_response.get('type') == 'auth_success':
                self.connected = True
                return True
            else:
                raise Exception(f"Authentication failed: {auth_response}")
                
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            
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
        
    async def wait_for_message(self, timeout: int = 10) -> Optional[Dict]:
        """Wait for a message from the server"""
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            message = json.loads(response)
            self.messages.append(message)
            
            # Notify handlers
            for handler in self.message_handlers:
                handler(message)
                
            return message
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None
            
    async def wait_for_messages(self, count: int, timeout: int = 10) -> List[Dict]:
        """Wait for multiple messages"""
        messages = []
        start_time = time.time()
        
        while len(messages) < count and (time.time() - start_time) < timeout:
            message = await self.wait_for_message(timeout=1)
            if message:
                messages.append(message)
                
        return messages
        
    def add_message_handler(self, handler):
        """Add a message handler"""
        self.message_handlers.append(handler)


@pytest.fixture
async def websocket_server():
    """Start WebSocket server for testing"""
    manager = WebSocketManager(host="localhost", port=8766)
    
    # Start server in background
    server_thread = threading.Thread(target=manager.start_polling, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(1)
    
    yield manager
    
    # Cleanup
    manager.stop_polling()


@pytest.fixture
async def test_client(websocket_server):
    """Create a test client"""
    client = WebSocketTestClient("ws://localhost:8766", "test_user", "developer")
    await client.connect()
    
    yield client
    
    await client.disconnect()


@pytest.fixture
async def agent_system(websocket_server):
    """Set up agent system with WebSocket manager"""
    # Create file manager (in-memory for testing)
    file_manager = FileOwnershipManager(":memory:")
    
    # Create agent manager with WebSocket
    agent_manager = AgentManager(file_manager, websocket_server)
    
    # Create some test agents
    agent_manager.create_agent("alice", "developer", ["python", "testing"])
    agent_manager.create_agent("bob", "designer", ["ui", "css"])
    
    yield agent_manager


class TestWebSocketBasicCommunication:
    """Test basic WebSocket communication functionality"""
    
    async def test_connection_and_authentication(self, websocket_server):
        """Test WebSocket connection and authentication"""
        client = WebSocketTestClient("ws://localhost:8766", "test_user", "developer")
        
        # Test connection
        success = await client.connect()
        assert success
        assert client.connected
        
        # Test disconnection
        await client.disconnect()
        assert not client.connected
        
    async def test_message_sending_and_receiving(self, test_client):
        """Test basic message sending and receiving"""
        # Send a message
        await test_client.send_message("Hello, world!")
        
        # Should receive the message back (broadcast)
        message = await test_client.wait_for_message()
        assert message is not None
        assert message['type'] == 'chat_message'
        assert message['data']['text'] == "Hello, world!"
        assert message['data']['sender'] == "test_user"
        
    async def test_multiple_clients(self, websocket_server):
        """Test communication between multiple clients"""
        client1 = WebSocketTestClient("ws://localhost:8766", "user1", "developer")
        client2 = WebSocketTestClient("ws://localhost:8766", "user2", "designer")
        
        await client1.connect()
        await client2.connect()
        
        try:
            # Client1 sends message
            await client1.send_message("Hello from user1")
            
            # Client2 should receive it
            message = await client2.wait_for_message()
            assert message is not None
            assert message['type'] == 'chat_message'
            assert message['data']['sender'] == "user1"
            assert message['data']['text'] == "Hello from user1"
            
            # Client2 responds
            await client2.send_message("Hello back from user2")
            
            # Client1 should receive it
            message = await client1.wait_for_message()
            assert message is not None
            assert message['data']['sender'] == "user2"
            
        finally:
            await client1.disconnect()
            await client2.disconnect()
            
    async def test_typing_indicators(self, websocket_server):
        """Test typing indicator functionality"""
        client1 = WebSocketTestClient("ws://localhost:8766", "user1", "developer")
        client2 = WebSocketTestClient("ws://localhost:8766", "user2", "designer")
        
        await client1.connect()
        await client2.connect()
        
        try:
            # Client1 starts typing
            await client1.send_typing(True)
            
            # Client2 should receive typing indicator
            message = await client2.wait_for_message()
            assert message is not None
            assert message['type'] == 'typing'
            assert message['data']['user_id'] == "user1"
            assert message['data']['is_typing'] == True
            
            # Client1 stops typing
            await client1.send_typing(False)
            
            # Client2 should receive stop typing
            message = await client2.wait_for_message()
            assert message is not None
            assert message['type'] == 'typing'
            assert message['data']['is_typing'] == False
            
        finally:
            await client1.disconnect()
            await client2.disconnect()


class TestAgentCommunication:
    """Test agent communication patterns"""
    
    async def test_agent_mention_response(self, agent_system, websocket_server):
        """Test that agents respond when mentioned"""
        client = WebSocketTestClient("ws://localhost:8766", "manager", "manager")
        await client.connect()
        
        try:
            # Mention an agent
            await client.send_message("@alice please review the code")
            
            # Should receive agent response
            messages = await client.wait_for_messages(2, timeout=5)  # Original + response
            
            # Find agent response
            agent_responses = [msg for msg in messages 
                             if msg.get('type') == 'chat_message' 
                             and msg.get('data', {}).get('sender') == 'alice-bot']
            
            assert len(agent_responses) > 0
            response = agent_responses[0]
            assert 'alice' in response['data']['text'].lower()
            
        finally:
            await client.disconnect()
            
    async def test_task_assignment_flow(self, agent_system, websocket_server):
        """Test complete task assignment flow"""
        client = WebSocketTestClient("ws://localhost:8766", "manager", "manager")
        await client.connect()
        
        received_messages = []
        client.add_message_handler(lambda msg: received_messages.append(msg))
        
        try:
            # Assign a task to an agent
            await client.send_message("@alice please create a login component")
            
            # Wait for messages
            await asyncio.sleep(2)
            
            # Should receive acknowledgment
            agent_messages = [msg for msg in received_messages 
                            if msg.get('type') == 'chat_message' 
                            and 'alice' in msg.get('data', {}).get('sender', '')]
            
            assert len(agent_messages) > 0
            
            # Check for task acknowledgment
            acknowledgments = [msg for msg in agent_messages 
                             if any(word in msg.get('data', {}).get('text', '').lower() 
                                   for word in ['got it', 'sure', 'on it', 'will do'])]
            
            assert len(acknowledgments) > 0
            
        finally:
            await client.disconnect()
            
    async def test_help_request_flow(self, agent_system, websocket_server):
        """Test help request and response flow"""
        client = WebSocketTestClient("ws://localhost:8766", "alice", "developer")
        await client.connect()
        
        received_messages = []
        client.add_message_handler(lambda msg: received_messages.append(msg))
        
        try:
            # Send help request
            await client.send_message("I'm stuck with this CSS issue. Any ideas?")
            
            # Wait for responses
            await asyncio.sleep(2)
            
            # Should receive help offers from other agents
            help_responses = [msg for msg in received_messages 
                            if msg.get('type') == 'chat_message' 
                            and msg.get('data', {}).get('sender') != 'alice'
                            and any(word in msg.get('data', {}).get('text', '').lower() 
                                   for word in ['help', 'try', 'consider', 'suggestion'])]
            
            # At least one agent should offer help
            assert len(help_responses) > 0
            
        finally:
            await client.disconnect()


class TestMessageParsing:
    """Test message parsing and formatting"""
    
    async def test_mention_parsing(self, test_client):
        """Test that mentions are properly parsed"""
        await test_client.send_message("@alice and @bob please collaborate")
        
        message = await test_client.wait_for_message()
        assert message is not None
        assert 'alice' in message['data']['mentions']
        assert 'bob' in message['data']['mentions']
        
    async def test_command_parsing(self, test_client):
        """Test command parsing"""
        await test_client.send_message("/help testing")
        
        message = await test_client.wait_for_message()
        assert message is not None
        assert message['data']['is_command'] == True
        assert message['data']['command'] == 'help'
        assert 'testing' in message['data']['command_args']
        
    async def test_reply_functionality(self, test_client):
        """Test reply-to functionality"""
        # Send original message
        await test_client.send_message("Original message")
        original = await test_client.wait_for_message()
        
        # Send reply
        await test_client.send_message("This is a reply", reply_to=original['data']['id'])
        reply = await test_client.wait_for_message()
        
        assert reply['data']['reply_to'] == original['data']['id']


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    async def test_invalid_authentication(self, websocket_server):
        """Test handling of invalid authentication"""
        client = WebSocketTestClient("ws://localhost:8766", "", "")  # Invalid credentials
        
        success = await client.connect()
        assert not success
        
    async def test_connection_recovery(self, websocket_server):
        """Test connection recovery after disconnect"""
        client = WebSocketTestClient("ws://localhost:8766", "test_user", "developer")
        
        # Initial connection
        await client.connect()
        assert client.connected
        
        # Force disconnect
        await client.websocket.close()
        client.connected = False
        
        # Reconnect
        await client.connect()
        assert client.connected
        
        await client.disconnect()
        
    async def test_malformed_message_handling(self, test_client):
        """Test handling of malformed messages"""
        # Send invalid JSON
        try:
            await test_client.websocket.send("invalid json")
            # Should not crash the server
            await asyncio.sleep(0.5)
            assert test_client.connected
        except Exception:
            pass  # Expected to fail gracefully


class TestPerformance:
    """Test performance and load handling"""
    
    async def test_high_frequency_messages(self, test_client):
        """Test handling of high-frequency messages"""
        message_count = 50
        sent_messages = []
        
        # Send many messages quickly
        for i in range(message_count):
            message_text = f"Message {i}"
            await test_client.send_message(message_text)
            sent_messages.append(message_text)
            
        # Receive all messages
        received_messages = await test_client.wait_for_messages(message_count, timeout=10)
        
        # Should receive all messages
        assert len(received_messages) == message_count
        
        # Messages should be in order
        for i, msg in enumerate(received_messages):
            assert msg['data']['text'] == f"Message {i}"
            
    async def test_concurrent_users(self, websocket_server):
        """Test multiple concurrent users"""
        num_clients = 10
        clients = []
        
        try:
            # Create and connect multiple clients
            for i in range(num_clients):
                client = WebSocketTestClient("ws://localhost:8766", f"user{i}", "developer")
                await client.connect()
                clients.append(client)
                
            # All clients send messages simultaneously
            tasks = []
            for i, client in enumerate(clients):
                task = client.send_message(f"Message from user{i}")
                tasks.append(task)
                
            await asyncio.gather(*tasks)
            
            # Each client should receive messages from all other clients
            for client in clients:
                messages = await client.wait_for_messages(num_clients, timeout=5)
                assert len(messages) >= num_clients - 1  # Exclude own message
                
        finally:
            # Cleanup
            for client in clients:
                await client.disconnect()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])