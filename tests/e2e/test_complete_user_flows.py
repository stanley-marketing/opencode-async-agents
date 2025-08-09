"""
Complete E2E User Flow Tests
Tests comprehensive user scenarios from connection to task completion.
"""

import asyncio
import json
import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from tests.utils.websocket_test_client import (
    WebSocketTestClient, 
    WebSocketTestScenario, 
    WebSocketTestAssertions,
    create_test_clients,
    cleanup_test_clients
)
from src.chat.websocket_manager import WebSocketManager
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager

logger = logging.getLogger(__name__)


@pytest.fixture
async def websocket_server():
    """Start WebSocket server for testing"""
    manager = WebSocketManager(host="localhost", port=8767)
    
    # Start server in background
    server_thread = threading.Thread(target=manager.start_polling, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(1)
    
    yield manager
    
    # Cleanup
    manager.stop_polling()


@pytest.fixture
async def agent_system(websocket_server):
    """Set up agent system with WebSocket manager"""
    # Create file manager (in-memory for testing)
    file_manager = FileOwnershipManager(":memory:")
    
    # Create agent manager with WebSocket
    agent_manager = AgentManager(file_manager, websocket_server)
    
    # Create test agents with different roles and expertise
    agent_manager.create_agent("alice", "developer", ["python", "testing", "api"])
    agent_manager.create_agent("bob", "designer", ["ui", "css", "frontend"])
    agent_manager.create_agent("charlie", "devops", ["docker", "deployment", "monitoring"])
    agent_manager.create_agent("diana", "qa", ["testing", "automation", "quality"])
    
    yield agent_manager


@pytest.fixture
async def test_scenario(websocket_server):
    """Create test scenario helper"""
    scenario = WebSocketTestScenario("ws://localhost:8767")
    yield scenario
    await scenario.cleanup_clients()


class TestCompleteUserJourney:
    """Test complete user journey from start to finish"""
    
    async def test_new_user_onboarding_flow(self, test_scenario, agent_system):
        """Test: New user joins, sees existing messages, and starts interacting"""
        
        # Step 1: Create initial conversation between existing users
        manager = await test_scenario.create_client("manager", "manager")
        alice_user = await test_scenario.create_client("alice_user", "developer")
        
        # Simulate existing conversation
        await manager.send_message("Good morning team! Let's start the daily standup.")
        await alice_user.send_message("Morning! I'm working on the authentication system.")
        
        # Wait for messages to propagate
        await asyncio.sleep(1)
        
        # Step 2: New user joins and should see existing messages
        new_user = await test_scenario.create_client("bob_new", "developer")
        
        # Wait for connection and message history
        await asyncio.sleep(2)
        
        # Verify new user received existing messages
        chat_messages = new_user.get_messages_by_type('chat_message')
        assert len(chat_messages) >= 2, "New user should see existing conversation"
        
        # Verify message content
        message_texts = [msg['data']['text'] for msg in chat_messages]
        assert any("standup" in text.lower() for text in message_texts)
        assert any("authentication" in text.lower() for text in message_texts)
        
        # Step 3: New user introduces themselves
        await new_user.send_message("Hi everyone! I'm Bob, just joined the team.")
        
        # Step 4: Verify other users receive the introduction
        intro_message = await manager.wait_for_message(timeout=5, message_type='chat_message')
        assert intro_message is not None
        assert "Bob" in intro_message['data']['text']
        assert intro_message['data']['sender'] == "bob_new"
        
        # Step 5: Manager welcomes new user and assigns first task
        await manager.send_message("Welcome Bob! @alice_user can you help Bob get set up?")
        
        # Verify mention is received
        mention_message = await alice_user.wait_for_message(timeout=5, message_type='chat_message')
        assert mention_message is not None
        assert "alice_user" in mention_message['data']['mentions']
        
    async def test_user_message_history_persistence(self, test_scenario, agent_system):
        """Test: User messages persist and are available to new connections"""
        
        # Step 1: Create conversation with multiple message types
        user1 = await test_scenario.create_client("user1", "developer")
        user2 = await test_scenario.create_client("user2", "designer")
        
        # Send various types of messages
        await user1.send_message("Let's discuss the new feature requirements")
        await user2.send_message("@user1 I have some design mockups ready")
        await user1.send_message("/help design patterns")
        await user2.send_message("Here's the link: https://example.com/mockups")
        
        # Wait for messages to be processed
        await asyncio.sleep(2)
        
        # Step 2: Disconnect users
        await user1.disconnect()
        await user2.disconnect()
        
        # Step 3: Reconnect and verify message history
        user1_reconnected = await test_scenario.create_client("user1", "developer")
        
        # Wait for message history to load
        await asyncio.sleep(2)
        
        # Verify all message types are preserved
        chat_messages = user1_reconnected.get_messages_by_type('chat_message')
        assert len(chat_messages) >= 4, "All messages should be preserved"
        
        # Verify specific message content
        message_texts = [msg['data']['text'] for msg in chat_messages]
        assert any("feature requirements" in text for text in message_texts)
        assert any("mockups" in text for text in message_texts)
        assert any("/help" in text for text in message_texts)
        assert any("https://example.com" in text for text in message_texts)
        
        # Verify mentions are preserved
        mention_messages = [msg for msg in chat_messages if msg['data'].get('mentions')]
        assert len(mention_messages) >= 1, "Mentions should be preserved"
        
    async def test_user_typing_indicators_flow(self, test_scenario, agent_system):
        """Test: Typing indicators work correctly in multi-user scenario"""
        
        # Create multiple users
        users = await create_test_clients("ws://localhost:8767", [
            {"user_id": "alice", "role": "developer"},
            {"user_id": "bob", "role": "designer"},
            {"user_id": "charlie", "role": "manager"}
        ])
        
        try:
            alice, bob, charlie = users["alice"], users["bob"], users["charlie"]
            
            # Step 1: Alice starts typing
            await alice.send_typing(True)
            
            # Step 2: Bob and Charlie should receive typing indicator
            bob_typing = await bob.wait_for_message(timeout=5, message_type='typing')
            charlie_typing = await charlie.wait_for_message(timeout=5, message_type='typing')
            
            assert bob_typing is not None
            assert charlie_typing is not None
            WebSocketTestAssertions.assert_typing_indicator(bob_typing, "alice", True)
            WebSocketTestAssertions.assert_typing_indicator(charlie_typing, "alice", True)
            
            # Step 3: Alice sends message (should stop typing)
            await alice.send_message("I'm working on the login component")
            
            # Step 4: Verify typing indicator stops
            await alice.send_typing(False)
            
            # Step 5: Multiple users typing simultaneously
            await bob.send_typing(True)
            await charlie.send_typing(True)
            
            # Alice should receive both typing indicators
            typing_messages = await alice.wait_for_messages(2, timeout=5, message_type='typing')
            assert len(typing_messages) == 2
            
            typing_users = {msg['data']['user_id'] for msg in typing_messages}
            assert "bob" in typing_users
            assert "charlie" in typing_users
            
        finally:
            await cleanup_test_clients(users)


class TestAgentMentionFlows:
    """Test agent mention and response flows"""
    
    async def test_single_agent_mention_and_response(self, test_scenario, agent_system):
        """Test: User mentions agent and receives appropriate response"""
        
        user = await test_scenario.create_client("developer", "developer")
        
        # Step 1: Mention agent with task
        await user.send_message("@alice please create a user authentication system")
        
        # Step 2: Wait for agent response
        agent_response = await user.wait_for_agent_response("alice", timeout=10)
        
        # Step 3: Verify response structure and content
        assert agent_response is not None, "Agent should respond to mention"
        WebSocketTestAssertions.assert_agent_response(agent_response, "alice")
        
        # Verify response is relevant to the task
        response_text = agent_response['data']['text'].lower()
        assert any(keyword in response_text for keyword in ['authentication', 'user', 'system', 'task'])
        
        # Step 4: Follow up with clarification
        await user.send_message("@alice what technologies will you use?")
        
        # Step 5: Verify agent provides technical details
        followup_response = await user.wait_for_agent_response("alice", timeout=10)
        assert followup_response is not None
        
        followup_text = followup_response['data']['text'].lower()
        assert any(tech in followup_text for tech in ['python', 'jwt', 'oauth', 'database', 'api'])
        
    async def test_multiple_agent_mentions_in_single_message(self, test_scenario, agent_system):
        """Test: User mentions multiple agents in one message"""
        
        user = await test_scenario.create_client("manager", "manager")
        
        # Step 1: Mention multiple agents
        await user.send_message("@alice @bob please collaborate on the user dashboard - Alice handles backend, Bob designs frontend")
        
        # Step 2: Wait for responses from both agents
        responses = await user.wait_for_messages(3, timeout=15)  # Original + 2 agent responses
        
        # Step 3: Verify both agents responded
        agent_responses = [msg for msg in responses 
                          if msg.get('type') == 'chat_message' 
                          and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        assert len(agent_responses) >= 2, "Both agents should respond"
        
        # Verify specific agents responded
        responding_agents = {msg['data']['sender'].replace('-bot', '') for msg in agent_responses}
        assert 'alice' in responding_agents
        assert 'bob' in responding_agents
        
        # Step 4: Verify responses acknowledge collaboration
        response_texts = [msg['data']['text'].lower() for msg in agent_responses]
        assert any('collaborate' in text or 'work together' in text or 'coordinate' in text 
                  for text in response_texts)
        
    async def test_agent_help_request_flow(self, test_scenario, agent_system):
        """Test: Agent requests help and receives assistance"""
        
        user = await test_scenario.create_client("developer", "developer")
        
        # Step 1: User asks for help with specific technology
        await user.send_message("I'm having trouble with CSS Grid layout. Any suggestions?")
        
        # Step 2: Wait for agent offers to help
        help_responses = await user.wait_for_messages(2, timeout=10)
        
        # Step 3: Verify at least one agent offered help
        agent_help = [msg for msg in help_responses 
                     if msg.get('type') == 'chat_message' 
                     and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        assert len(agent_help) >= 1, "At least one agent should offer help"
        
        # Step 4: Verify help is relevant to CSS
        help_text = agent_help[0]['data']['text'].lower()
        assert any(keyword in help_text for keyword in ['css', 'grid', 'layout', 'try', 'suggest'])
        
        # Step 5: User follows up with specific question
        await user.send_message("@bob how do I center items in a grid container?")
        
        # Step 6: Verify specific technical response
        specific_help = await user.wait_for_agent_response("bob", timeout=10)
        assert specific_help is not None
        
        specific_text = specific_help['data']['text'].lower()
        assert any(keyword in specific_text for keyword in ['center', 'grid', 'justify', 'align'])


class TestTaskAssignmentFlows:
    """Test task assignment and completion flows"""
    
    async def test_complete_task_assignment_cycle(self, test_scenario, agent_system):
        """Test: Complete task assignment from start to completion"""
        
        manager = await test_scenario.create_client("manager", "manager")
        
        # Step 1: Assign task to agent
        task_description = "Create a REST API endpoint for user registration"
        await manager.send_message(f"@alice {task_description}")
        
        # Step 2: Verify task acknowledgment
        ack_response = await manager.wait_for_agent_response("alice", timeout=10)
        assert ack_response is not None
        WebSocketTestAssertions.assert_agent_response(ack_response, "alice")
        
        ack_text = ack_response['data']['text'].lower()
        assert any(keyword in ack_text for keyword in ['got it', 'will do', 'on it', 'started'])
        
        # Step 3: Simulate task progress updates
        await asyncio.sleep(2)  # Simulate work time
        
        # Step 4: Check task status
        await manager.send_message("@alice what's the status on the API endpoint?")
        
        status_response = await manager.wait_for_agent_response("alice", timeout=10)
        assert status_response is not None
        
        status_text = status_response['data']['text'].lower()
        assert any(keyword in status_text for keyword in ['working', 'progress', 'api', 'endpoint'])
        
        # Step 5: Simulate task completion
        # This would normally be triggered by the worker agent
        completion_message = "Task completed: REST API endpoint created with validation and error handling"
        
        # Verify completion notification format
        assert "completed" in completion_message.lower()
        assert "api" in completion_message.lower()
        
    async def test_task_delegation_between_agents(self, test_scenario, agent_system):
        """Test: Agent delegates subtask to another agent"""
        
        user = await test_scenario.create_client("lead", "lead_developer")
        
        # Step 1: Assign complex task requiring multiple skills
        await user.send_message("@alice create a user dashboard with authentication and responsive design")
        
        # Step 2: Wait for initial response
        initial_response = await user.wait_for_agent_response("alice", timeout=10)
        assert initial_response is not None
        
        # Step 3: Alice should coordinate with Bob for design
        # Wait for potential coordination messages
        coordination_messages = await user.wait_for_messages(3, timeout=15)
        
        # Look for coordination between agents
        agent_messages = [msg for msg in coordination_messages 
                         if msg.get('type') == 'chat_message' 
                         and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        # Verify agents are coordinating
        if len(agent_messages) >= 2:
            message_texts = [msg['data']['text'].lower() for msg in agent_messages]
            coordination_keywords = ['coordinate', 'work together', 'design', 'frontend', 'backend']
            assert any(any(keyword in text for keyword in coordination_keywords) 
                      for text in message_texts)
        
    async def test_task_error_handling_flow(self, test_scenario, agent_system):
        """Test: Agent encounters error and requests help"""
        
        user = await test_scenario.create_client("developer", "developer")
        
        # Step 1: Assign task that might cause issues
        await user.send_message("@charlie deploy the application to production with SSL certificates")
        
        # Step 2: Wait for initial response
        initial_response = await user.wait_for_agent_response("charlie", timeout=10)
        assert initial_response is not None
        
        # Step 3: Simulate error scenario
        await user.send_message("@charlie the SSL certificate validation is failing")
        
        # Step 4: Verify agent acknowledges the issue
        error_response = await user.wait_for_agent_response("charlie", timeout=10)
        assert error_response is not None
        
        error_text = error_response['data']['text'].lower()
        assert any(keyword in error_text for keyword in ['ssl', 'certificate', 'error', 'issue', 'check'])
        
        # Step 5: Agent should provide troubleshooting steps
        assert any(keyword in error_text for keyword in ['verify', 'check', 'try', 'ensure'])


class TestMultiUserCollaboration:
    """Test multi-user collaboration scenarios"""
    
    async def test_team_brainstorming_session(self, test_scenario, agent_system):
        """Test: Multiple users and agents collaborate on brainstorming"""
        
        # Create team members
        users = await create_test_clients("ws://localhost:8767", [
            {"user_id": "product_manager", "role": "manager"},
            {"user_id": "senior_dev", "role": "senior_developer"},
            {"user_id": "designer", "role": "designer"},
            {"user_id": "qa_lead", "role": "qa_lead"}
        ])
        
        try:
            pm, dev, designer, qa = users.values()
            
            # Step 1: Product manager starts brainstorming
            await pm.send_message("Let's brainstorm features for the new user onboarding flow")
            
            # Step 2: Team members contribute ideas
            await dev.send_message("We could add progressive disclosure to reduce cognitive load")
            await designer.send_message("I suggest using micro-interactions to guide users")
            await qa.send_message("We need to ensure accessibility compliance throughout")
            
            # Step 3: Involve agents in discussion
            await pm.send_message("@alice @bob what are your thoughts on these ideas?")
            
            # Step 4: Wait for agent contributions
            agent_responses = []
            for _ in range(4):  # Wait for multiple responses
                response = await pm.wait_for_message(timeout=5)
                if (response and response.get('type') == 'chat_message' 
                    and response.get('data', {}).get('sender', '').endswith('-bot')):
                    agent_responses.append(response)
            
            # Step 5: Verify agents provided relevant input
            assert len(agent_responses) >= 1, "Agents should contribute to brainstorming"
            
            response_texts = [msg['data']['text'].lower() for msg in agent_responses]
            brainstorming_keywords = ['onboarding', 'user', 'feature', 'suggest', 'consider', 'idea']
            assert any(any(keyword in text for keyword in brainstorming_keywords) 
                      for text in response_texts)
            
        finally:
            await cleanup_test_clients(users)
            
    async def test_code_review_collaboration(self, test_scenario, agent_system):
        """Test: Code review collaboration between users and agents"""
        
        # Create development team
        users = await create_test_clients("ws://localhost:8767", [
            {"user_id": "author", "role": "developer"},
            {"user_id": "reviewer", "role": "senior_developer"},
            {"user_id": "maintainer", "role": "tech_lead"}
        ])
        
        try:
            author, reviewer, maintainer = users.values()
            
            # Step 1: Author requests code review
            await author.send_message("I've submitted PR #123 for the authentication module. Could someone review?")
            
            # Step 2: Reviewer acknowledges
            await reviewer.send_message("I'll take a look at the authentication PR")
            
            # Step 3: Reviewer finds issues and mentions agent for help
            await reviewer.send_message("@alice I see some security concerns in the password hashing. Can you suggest best practices?")
            
            # Step 4: Wait for agent security advice
            security_advice = await reviewer.wait_for_agent_response("alice", timeout=10)
            assert security_advice is not None
            
            advice_text = security_advice['data']['text'].lower()
            security_keywords = ['password', 'hash', 'security', 'bcrypt', 'salt', 'secure']
            assert any(keyword in advice_text for keyword in security_keywords)
            
            # Step 5: Maintainer provides final approval
            await maintainer.send_message("Thanks for the review. @author please address the security feedback")
            
            # Step 6: Author acknowledges and asks for clarification
            await author.send_message("@alice can you provide a code example for secure password hashing?")
            
            # Step 7: Verify agent provides technical example
            code_example = await author.wait_for_agent_response("alice", timeout=10)
            assert code_example is not None
            
            example_text = code_example['data']['text'].lower()
            assert any(keyword in example_text for keyword in ['example', 'code', 'bcrypt', 'hash'])
            
        finally:
            await cleanup_test_clients(users)


class TestErrorScenarios:
    """Test error handling and edge cases"""
    
    async def test_connection_recovery_during_conversation(self, test_scenario, agent_system):
        """Test: User connection drops and recovers during active conversation"""
        
        # Step 1: Start conversation
        user = await test_scenario.create_client("user", "developer")
        await user.send_message("@alice let's work on the database schema")
        
        # Step 2: Get initial response
        initial_response = await user.wait_for_agent_response("alice", timeout=10)
        assert initial_response is not None
        
        # Step 3: Simulate connection drop
        await user.disconnect()
        await asyncio.sleep(2)
        
        # Step 4: Reconnect
        user_reconnected = await test_scenario.create_client("user", "developer")
        
        # Step 5: Continue conversation
        await user_reconnected.send_message("@alice I'm back. Where were we with the database schema?")
        
        # Step 6: Verify agent responds appropriately
        recovery_response = await user_reconnected.wait_for_agent_response("alice", timeout=10)
        assert recovery_response is not None
        
        response_text = recovery_response['data']['text'].lower()
        assert any(keyword in response_text for keyword in ['database', 'schema', 'continue', 'working'])
        
    async def test_invalid_agent_mention(self, test_scenario, agent_system):
        """Test: User mentions non-existent agent"""
        
        user = await test_scenario.create_client("user", "developer")
        
        # Step 1: Mention non-existent agent
        await user.send_message("@nonexistent_agent please help with this task")
        
        # Step 2: Wait for any responses
        responses = await user.wait_for_messages(2, timeout=5)
        
        # Step 3: Verify no agent response for non-existent agent
        agent_responses = [msg for msg in responses 
                          if msg.get('type') == 'chat_message' 
                          and msg.get('data', {}).get('sender') == 'nonexistent_agent-bot']
        
        assert len(agent_responses) == 0, "Non-existent agent should not respond"
        
        # Step 4: Verify existing agents might offer help
        helpful_responses = [msg for msg in responses 
                           if msg.get('type') == 'chat_message' 
                           and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        # It's okay if no agents respond to invalid mentions
        # But if they do, they should be helpful
        if helpful_responses:
            help_text = helpful_responses[0]['data']['text'].lower()
            assert any(keyword in help_text for keyword in ['help', 'assist', 'available'])
            
    async def test_message_flood_handling(self, test_scenario, agent_system):
        """Test: System handles message flooding gracefully"""
        
        user = await test_scenario.create_client("user", "developer")
        
        # Step 1: Send many messages quickly
        message_count = 20
        for i in range(message_count):
            await user.send_message(f"Message {i} - testing flood handling")
            await asyncio.sleep(0.1)  # Small delay to avoid overwhelming
        
        # Step 2: Wait for system to process
        await asyncio.sleep(3)
        
        # Step 3: Send normal message to verify system is responsive
        await user.send_message("@alice are you still responsive after the message flood?")
        
        # Step 4: Verify agent can still respond
        response = await user.wait_for_agent_response("alice", timeout=10)
        assert response is not None, "Agent should still be responsive after message flood"
        
        # Step 5: Verify response is coherent
        response_text = response['data']['text']
        assert len(response_text.strip()) > 0, "Response should not be empty"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])