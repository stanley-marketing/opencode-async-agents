"""
E2E Agent Interaction Tests
Tests agent-to-agent communication, help cycles, and task delegation.
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
    manager = WebSocketManager(host="localhost", port=8768)
    
    # Start server in background
    server_thread = threading.Thread(target=manager.start_polling, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(1)
    
    yield manager
    
    # Cleanup
    manager.stop_polling()


@pytest.fixture
async def specialized_agent_system(websocket_server):
    """Set up specialized agent system for interaction testing"""
    # Create file manager (in-memory for testing)
    file_manager = FileOwnershipManager(":memory:")
    
    # Create agent manager with WebSocket
    agent_manager = AgentManager(file_manager, websocket_server)
    
    # Create specialized agents with distinct expertise
    agent_manager.create_agent("backend_alice", "backend_developer", 
                              ["python", "django", "api", "database", "security"])
    agent_manager.create_agent("frontend_bob", "frontend_developer", 
                              ["react", "typescript", "css", "ui", "responsive"])
    agent_manager.create_agent("devops_charlie", "devops_engineer", 
                              ["docker", "kubernetes", "aws", "monitoring", "deployment"])
    agent_manager.create_agent("qa_diana", "qa_engineer", 
                              ["testing", "automation", "selenium", "quality", "bugs"])
    agent_manager.create_agent("security_eve", "security_specialist", 
                              ["security", "penetration", "encryption", "compliance", "audit"])
    
    yield agent_manager


@pytest.fixture
async def test_scenario(websocket_server):
    """Create test scenario helper"""
    scenario = WebSocketTestScenario("ws://localhost:8768")
    yield scenario
    await scenario.cleanup_clients()


class TestAgentToAgentCommunication:
    """Test direct agent-to-agent communication patterns"""
    
    async def test_agent_consultation_flow(self, test_scenario, specialized_agent_system):
        """Test: Agent consults another agent for expertise"""
        
        user = await test_scenario.create_client("tech_lead", "tech_lead")
        
        # Step 1: Assign task requiring multiple expertise areas
        await user.send_message("@backend_alice create a secure user authentication API with proper testing")
        
        # Step 2: Wait for initial response from backend agent
        alice_response = await user.wait_for_agent_response("backend_alice", timeout=10)
        assert alice_response is not None
        WebSocketTestAssertions.assert_agent_response(alice_response, "backend_alice")
        
        # Step 3: Backend agent should consult security specialist
        # Wait for potential consultation messages
        consultation_messages = await user.wait_for_messages(5, timeout=15)
        
        # Look for agent-to-agent communication
        agent_messages = [msg for msg in consultation_messages 
                         if msg.get('type') == 'chat_message' 
                         and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        # Verify agents are collaborating
        if len(agent_messages) >= 2:
            # Check for security consultation
            security_mentions = [msg for msg in agent_messages 
                               if 'security_eve' in msg.get('data', {}).get('mentions', [])]
            
            if security_mentions:
                # Verify security agent responds with expertise
                security_response = await user.wait_for_agent_response("security_eve", timeout=10)
                if security_response:
                    security_text = security_response['data']['text'].lower()
                    security_keywords = ['security', 'authentication', 'encryption', 'jwt', 'oauth']
                    assert any(keyword in security_text for keyword in security_keywords)
        
        # Step 4: Backend agent should also consult QA for testing
        qa_consultation = [msg for msg in agent_messages 
                          if 'qa_diana' in msg.get('data', {}).get('mentions', [])]
        
        if qa_consultation:
            qa_response = await user.wait_for_agent_response("qa_diana", timeout=10)
            if qa_response:
                qa_text = qa_response['data']['text'].lower()
                testing_keywords = ['test', 'testing', 'automation', 'unit', 'integration']
                assert any(keyword in testing_keywords for keyword in testing_keywords)
    
    async def test_cross_functional_collaboration(self, test_scenario, specialized_agent_system):
        """Test: Multiple agents collaborate on cross-functional task"""
        
        user = await test_scenario.create_client("product_owner", "product_owner")
        
        # Step 1: Assign complex feature requiring all teams
        feature_request = ("Create a user dashboard with real-time data, responsive design, "
                          "secure authentication, automated testing, and production deployment")
        await user.send_message(f"Team, we need to build: {feature_request}")
        
        # Step 2: Mention all relevant agents
        await user.send_message("@backend_alice @frontend_bob @devops_charlie @qa_diana @security_eve "
                               "please coordinate on this dashboard feature")
        
        # Step 3: Wait for agent responses and coordination
        coordination_messages = await user.wait_for_messages(8, timeout=20)
        
        # Step 4: Verify each agent type responded
        agent_responses = [msg for msg in coordination_messages 
                          if msg.get('type') == 'chat_message' 
                          and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        responding_agents = {msg['data']['sender'].replace('-bot', '') for msg in agent_responses}
        
        # At least 3 agents should respond to coordinate
        assert len(responding_agents) >= 3, f"Expected multiple agents to respond, got: {responding_agents}"
        
        # Step 5: Verify coordination keywords in responses
        response_texts = [msg['data']['text'].lower() for msg in agent_responses]
        coordination_keywords = ['coordinate', 'work together', 'collaborate', 'team', 'dashboard']
        
        coordination_found = any(any(keyword in text for keyword in coordination_keywords) 
                               for text in response_texts)
        assert coordination_found, "Agents should show coordination intent"
        
        # Step 6: Verify technical expertise is mentioned
        technical_keywords = {
            'backend': ['api', 'database', 'server', 'backend'],
            'frontend': ['ui', 'react', 'frontend', 'responsive'],
            'devops': ['deploy', 'docker', 'production', 'infrastructure'],
            'qa': ['test', 'quality', 'automation', 'testing'],
            'security': ['secure', 'authentication', 'security', 'encryption']
        }
        
        expertise_mentioned = 0
        for text in response_texts:
            for expertise, keywords in technical_keywords.items():
                if any(keyword in text for keyword in keywords):
                    expertise_mentioned += 1
                    break
        
        assert expertise_mentioned >= 2, "Agents should mention their technical expertise"
    
    async def test_agent_knowledge_sharing(self, test_scenario, specialized_agent_system):
        """Test: Agents share knowledge and best practices"""
        
        user = await test_scenario.create_client("junior_dev", "junior_developer")
        
        # Step 1: Junior developer asks for general advice
        await user.send_message("I'm new to web development. What are the best practices for building secure, scalable applications?")
        
        # Step 2: Wait for multiple agents to offer advice
        advice_messages = await user.wait_for_messages(6, timeout=15)
        
        # Step 3: Verify multiple agents provided advice
        agent_advice = [msg for msg in advice_messages 
                       if msg.get('type') == 'chat_message' 
                       and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        assert len(agent_advice) >= 2, "Multiple agents should offer advice to junior developer"
        
        # Step 4: Verify each agent provides domain-specific advice
        advice_texts = [msg['data']['text'].lower() for msg in agent_advice]
        
        # Check for domain-specific advice
        backend_advice = any(any(keyword in text for keyword in ['api', 'database', 'server', 'backend']) 
                           for text in advice_texts)
        frontend_advice = any(any(keyword in text for keyword in ['ui', 'frontend', 'user experience']) 
                            for text in advice_texts)
        security_advice = any(any(keyword in text for keyword in ['security', 'authentication', 'encryption']) 
                            for text in advice_texts)
        
        # At least two domains should be covered
        domains_covered = sum([backend_advice, frontend_advice, security_advice])
        assert domains_covered >= 2, "Multiple domains should be covered in advice"
        
        # Step 5: Follow up with specific question
        await user.send_message("@security_eve specifically, how should I handle user passwords securely?")
        
        # Step 6: Verify security specialist provides detailed advice
        security_response = await user.wait_for_agent_response("security_eve", timeout=10)
        assert security_response is not None
        
        security_text = security_response['data']['text'].lower()
        password_keywords = ['password', 'hash', 'bcrypt', 'salt', 'secure', 'encryption']
        assert any(keyword in security_text for keyword in password_keywords)


class TestHelpRequestAndResponseCycles:
    """Test help request and response cycles between agents"""
    
    async def test_agent_requests_help_from_specialist(self, test_scenario, specialized_agent_system):
        """Test: Agent requests help from specialist when stuck"""
        
        user = await test_scenario.create_client("developer", "developer")
        
        # Step 1: Assign task to frontend agent that requires backend knowledge
        await user.send_message("@frontend_bob create a user profile page that displays data from our REST API")
        
        # Step 2: Wait for initial response
        bob_response = await user.wait_for_agent_response("frontend_bob", timeout=10)
        assert bob_response is not None
        
        # Step 3: Frontend agent encounters API integration challenge
        await user.send_message("@frontend_bob the API is returning 401 errors. What should I check?")
        
        # Step 4: Frontend agent should seek help from backend specialist
        help_messages = await user.wait_for_messages(4, timeout=15)
        
        # Look for help request to backend agent
        backend_mentions = [msg for msg in help_messages 
                           if msg.get('type') == 'chat_message' 
                           and 'backend_alice' in msg.get('data', {}).get('mentions', [])]
        
        if backend_mentions:
            # Step 5: Backend agent should provide API troubleshooting help
            alice_help = await user.wait_for_agent_response("backend_alice", timeout=10)
            if alice_help:
                help_text = alice_help['data']['text'].lower()
                api_keywords = ['401', 'authentication', 'token', 'api', 'authorization', 'header']
                assert any(keyword in help_text for keyword in api_keywords)
        
        # Alternative: Frontend agent provides general troubleshooting
        else:
            bob_help = await user.wait_for_agent_response("frontend_bob", timeout=10)
            assert bob_help is not None
            help_text = bob_help['data']['text'].lower()
            assert any(keyword in help_text for keyword in ['401', 'api', 'authentication', 'check'])
    
    async def test_escalating_help_requests(self, test_scenario, specialized_agent_system):
        """Test: Help requests escalate through team hierarchy"""
        
        user = await test_scenario.create_client("intern", "intern")
        
        # Step 1: Intern asks for help with complex deployment issue
        await user.send_message("I'm trying to deploy our app but getting SSL certificate errors in production")
        
        # Step 2: Wait for initial help offers
        initial_help = await user.wait_for_messages(3, timeout=10)
        
        # Step 3: Escalate to DevOps specialist
        await user.send_message("@devops_charlie I'm still stuck with SSL certificate errors. Can you help?")
        
        # Step 4: DevOps agent should provide specialized help
        devops_help = await user.wait_for_agent_response("devops_charlie", timeout=10)
        assert devops_help is not None
        
        help_text = devops_help['data']['text'].lower()
        ssl_keywords = ['ssl', 'certificate', 'tls', 'https', 'domain', 'ca', 'cert']
        assert any(keyword in help_text for keyword in ssl_keywords)
        
        # Step 5: If still complex, should involve security specialist
        await user.send_message("@devops_charlie the certificates are valid but still failing. Security issue?")
        
        # Step 6: DevOps might consult security specialist
        security_consultation = await user.wait_for_messages(3, timeout=10)
        
        security_mentions = [msg for msg in security_consultation 
                           if msg.get('type') == 'chat_message' 
                           and 'security_eve' in msg.get('data', {}).get('mentions', [])]
        
        if security_mentions:
            security_help = await user.wait_for_agent_response("security_eve", timeout=10)
            if security_help:
                security_text = security_help['data']['text'].lower()
                security_ssl_keywords = ['certificate', 'security', 'validation', 'chain', 'trust']
                assert any(keyword in security_text for keyword in security_ssl_keywords)
    
    async def test_peer_to_peer_help_network(self, test_scenario, specialized_agent_system):
        """Test: Agents form peer-to-peer help network"""
        
        user = await test_scenario.create_client("team_lead", "team_lead")
        
        # Step 1: Create scenario where multiple agents need to help each other
        await user.send_message("We're building a microservices architecture with React frontend, "
                               "Python backend, Docker deployment, comprehensive testing, and security audit")
        
        # Step 2: Assign initial task that will require collaboration
        await user.send_message("@backend_alice start with the user service API")
        
        # Step 3: Backend agent should coordinate with others
        alice_response = await user.wait_for_agent_response("backend_alice", timeout=10)
        assert alice_response is not None
        
        # Step 4: Simulate need for frontend coordination
        await user.send_message("@backend_alice what API endpoints will frontend need?")
        
        # Step 5: Backend should coordinate with frontend
        coordination_messages = await user.wait_for_messages(4, timeout=15)
        
        # Look for cross-agent coordination
        agent_messages = [msg for msg in coordination_messages 
                         if msg.get('type') == 'chat_message' 
                         and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        # Step 6: Verify agents are coordinating
        if len(agent_messages) >= 2:
            coordination_found = False
            for msg in agent_messages:
                mentions = msg.get('data', {}).get('mentions', [])
                if any(agent in mentions for agent in ['frontend_bob', 'backend_alice']):
                    coordination_found = True
                    break
            
            # If coordination found, verify it's meaningful
            if coordination_found:
                coordination_texts = [msg['data']['text'].lower() for msg in agent_messages]
                api_coordination = any(any(keyword in text for keyword in ['api', 'endpoint', 'interface']) 
                                     for text in coordination_texts)
                assert api_coordination, "API coordination should be discussed"


class TestTaskDelegationPatterns:
    """Test task delegation between agents"""
    
    async def test_hierarchical_task_delegation(self, test_scenario, specialized_agent_system):
        """Test: Senior agent delegates subtasks to specialists"""
        
        user = await test_scenario.create_client("architect", "solution_architect")
        
        # Step 1: Assign complex system design task
        system_design = ("Design and implement a complete e-commerce platform with user management, "
                        "product catalog, shopping cart, payment processing, and admin dashboard")
        await user.send_message(f"@backend_alice please lead the development of: {system_design}")
        
        # Step 2: Backend lead should acknowledge and start delegation
        alice_response = await user.wait_for_agent_response("backend_alice", timeout=10)
        assert alice_response is not None
        
        # Step 3: Look for delegation to other specialists
        delegation_messages = await user.wait_for_messages(6, timeout=20)
        
        # Step 4: Verify delegation to appropriate specialists
        agent_messages = [msg for msg in delegation_messages 
                         if msg.get('type') == 'chat_message' 
                         and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        # Look for mentions of other agents (delegation)
        delegated_agents = set()
        for msg in agent_messages:
            mentions = msg.get('data', {}).get('mentions', [])
            for mention in mentions:
                if mention.endswith('_bob') or mention.endswith('_charlie') or mention.endswith('_diana'):
                    delegated_agents.add(mention)
        
        # Step 5: Verify appropriate delegation occurred
        if delegated_agents:
            # Frontend should be involved for UI
            frontend_involved = any('frontend' in agent or 'bob' in agent for agent in delegated_agents)
            # DevOps should be involved for deployment
            devops_involved = any('devops' in agent or 'charlie' in agent for agent in delegated_agents)
            
            assert frontend_involved or devops_involved, "Appropriate specialists should be delegated to"
        
        # Step 6: Verify delegation includes clear task breakdown
        delegation_texts = [msg['data']['text'].lower() for msg in agent_messages]
        task_keywords = ['task', 'component', 'module', 'feature', 'implement', 'develop']
        
        task_breakdown = any(any(keyword in text for keyword in task_keywords) 
                           for text in delegation_texts)
        assert task_breakdown, "Delegation should include task breakdown"
    
    async def test_parallel_task_execution(self, test_scenario, specialized_agent_system):
        """Test: Multiple agents work on parallel tasks"""
        
        user = await test_scenario.create_client("project_manager", "project_manager")
        
        # Step 1: Assign parallel tasks to different agents
        await user.send_message("Sprint planning: @backend_alice work on user API, "
                               "@frontend_bob create user interface, "
                               "@qa_diana prepare test cases, "
                               "@devops_charlie set up staging environment")
        
        # Step 2: Wait for all agents to acknowledge their tasks
        acknowledgments = await user.wait_for_messages(6, timeout=15)
        
        # Step 3: Verify each agent acknowledged their specific task
        agent_responses = [msg for msg in acknowledgments 
                          if msg.get('type') == 'chat_message' 
                          and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        responding_agents = {msg['data']['sender'].replace('-bot', '') for msg in agent_responses}
        
        # At least 3 agents should respond
        assert len(responding_agents) >= 3, f"Expected multiple agents to respond, got: {responding_agents}"
        
        # Step 4: Verify task-specific acknowledgments
        response_texts = [msg['data']['text'].lower() for msg in agent_responses]
        
        # Check for task-specific keywords
        api_mentioned = any('api' in text or 'backend' in text for text in response_texts)
        ui_mentioned = any('ui' in text or 'interface' in text or 'frontend' in text for text in response_texts)
        test_mentioned = any('test' in text or 'qa' in text for text in response_texts)
        deploy_mentioned = any('staging' in text or 'environment' in text or 'deploy' in text for text in response_texts)
        
        # At least 2 task areas should be acknowledged
        task_areas = sum([api_mentioned, ui_mentioned, test_mentioned, deploy_mentioned])
        assert task_areas >= 2, "Multiple task areas should be acknowledged"
        
        # Step 5: Check for coordination between parallel tasks
        await user.send_message("How are the parallel tasks progressing? Any dependencies?")
        
        # Step 6: Wait for status updates
        status_updates = await user.wait_for_messages(4, timeout=10)
        
        status_responses = [msg for msg in status_updates 
                           if msg.get('type') == 'chat_message' 
                           and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        # Verify agents provide status updates
        assert len(status_responses) >= 1, "Agents should provide status updates"
    
    async def test_dynamic_task_reallocation(self, test_scenario, specialized_agent_system):
        """Test: Tasks are reallocated when agents are unavailable"""
        
        user = await test_scenario.create_client("scrum_master", "scrum_master")
        
        # Step 1: Assign task to specific agent
        await user.send_message("@frontend_bob create the user registration form with validation")
        
        # Step 2: Wait for initial response
        bob_response = await user.wait_for_agent_response("frontend_bob", timeout=10)
        assert bob_response is not None
        
        # Step 3: Simulate agent becoming unavailable/stuck
        await user.send_message("@frontend_bob are you stuck on the validation logic?")
        
        # Step 4: Wait for response or timeout
        stuck_response = await user.wait_for_agent_response("frontend_bob", timeout=8)
        
        # Step 5: If agent is stuck, reallocate or get help
        await user.send_message("Team, frontend_bob needs help with form validation. Who can assist?")
        
        # Step 6: Wait for other agents to offer help
        help_offers = await user.wait_for_messages(4, timeout=10)
        
        # Step 7: Verify other agents offer assistance
        help_responses = [msg for msg in help_offers 
                         if msg.get('type') == 'chat_message' 
                         and msg.get('data', {}).get('sender', '').endswith('-bot')
                         and msg.get('data', {}).get('sender') != 'frontend_bob-bot']
        
        if help_responses:
            help_texts = [msg['data']['text'].lower() for msg in help_responses]
            help_keywords = ['help', 'assist', 'validation', 'form', 'can help', 'support']
            
            help_offered = any(any(keyword in text for keyword in help_keywords) 
                             for text in help_texts)
            assert help_offered, "Other agents should offer help when colleague is stuck"


class TestAgentStatusAndPresence:
    """Test agent status updates and presence indicators"""
    
    async def test_agent_status_updates(self, test_scenario, specialized_agent_system):
        """Test: Agents provide status updates during work"""
        
        user = await test_scenario.create_client("manager", "manager")
        
        # Step 1: Assign long-running task
        await user.send_message("@devops_charlie set up the complete CI/CD pipeline for our microservices")
        
        # Step 2: Wait for initial acknowledgment
        initial_response = await user.wait_for_agent_response("devops_charlie", timeout=10)
        assert initial_response is not None
        
        # Step 3: Check status during work
        await asyncio.sleep(2)  # Simulate some work time
        await user.send_message("@devops_charlie what's your progress on the CI/CD pipeline?")
        
        # Step 4: Verify status update
        status_response = await user.wait_for_agent_response("devops_charlie", timeout=10)
        assert status_response is not None
        
        status_text = status_response['data']['text'].lower()
        progress_keywords = ['progress', 'working', 'setting up', 'configuring', 'pipeline', 'ci/cd']
        assert any(keyword in status_text for keyword in progress_keywords)
        
        # Step 5: Request detailed status
        await user.send_message("@devops_charlie can you give me a detailed status update?")
        
        # Step 6: Verify detailed response
        detailed_response = await user.wait_for_agent_response("devops_charlie", timeout=10)
        assert detailed_response is not None
        
        # Detailed response should be longer and more specific
        detailed_text = detailed_response['data']['text']
        assert len(detailed_text) > len(status_text), "Detailed status should be more comprehensive"
    
    async def test_agent_availability_coordination(self, test_scenario, specialized_agent_system):
        """Test: Agents coordinate availability for collaborative tasks"""
        
        user = await test_scenario.create_client("coordinator", "project_coordinator")
        
        # Step 1: Request team availability for urgent task
        await user.send_message("Urgent: We need to fix a critical security vulnerability. "
                               "@security_eve @backend_alice @devops_charlie are you available?")
        
        # Step 2: Wait for availability responses
        availability_responses = await user.wait_for_messages(5, timeout=15)
        
        # Step 3: Verify agents respond about availability
        agent_responses = [msg for msg in availability_responses 
                          if msg.get('type') == 'chat_message' 
                          and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        assert len(agent_responses) >= 2, "Multiple agents should respond to availability check"
        
        # Step 4: Verify availability keywords
        response_texts = [msg['data']['text'].lower() for msg in agent_responses]
        availability_keywords = ['available', 'ready', 'can help', 'on it', 'here', 'urgent']
        
        availability_confirmed = any(any(keyword in text for keyword in availability_keywords) 
                                   for text in response_texts)
        assert availability_confirmed, "Agents should confirm availability for urgent tasks"
        
        # Step 5: Coordinate the urgent response
        await user.send_message("Great! @security_eve please lead the vulnerability assessment, "
                               "@backend_alice check the API endpoints, "
                               "@devops_charlie prepare for emergency deployment")
        
        # Step 6: Verify coordinated response
        coordination_responses = await user.wait_for_messages(4, timeout=10)
        
        coordinated_agents = [msg for msg in coordination_responses 
                             if msg.get('type') == 'chat_message' 
                             and msg.get('data', {}).get('sender', '').endswith('-bot')]
        
        # At least 2 agents should acknowledge their specific roles
        assert len(coordinated_agents) >= 2, "Agents should acknowledge their roles in urgent response"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])