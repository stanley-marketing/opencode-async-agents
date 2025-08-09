"""
Real-World Usage Scenario Tests
Tests realistic usage patterns and complex workflows.
"""

import asyncio
import json
import pytest
import time
import threading
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from tests.utils.websocket_test_client import (
    WebSocketTestClient, 
    WebSocketTestScenario, 
    WebSocketTestAssertions,
    create_test_clients,
    cleanup_test_clients,
    create_test_conversation
)
from src.chat.websocket_manager import WebSocketManager
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager

logger = logging.getLogger(__name__)


@pytest.fixture
async def websocket_server():
    """Start WebSocket server for testing"""
    manager = WebSocketManager(host="localhost", port=8771)
    
    # Start server in background
    server_thread = threading.Thread(target=manager.start_polling, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(1)
    
    yield manager
    
    # Cleanup
    manager.stop_polling()


@pytest.fixture
async def production_agent_system(websocket_server):
    """Set up production-like agent system"""
    file_manager = FileOwnershipManager(":memory:")
    agent_manager = AgentManager(file_manager, websocket_server)
    
    # Create realistic development team
    agents = [
        ("sarah_lead", "tech_lead", ["architecture", "python", "leadership", "code_review"]),
        ("mike_backend", "backend_developer", ["python", "django", "postgresql", "api", "microservices"]),
        ("emma_frontend", "frontend_developer", ["react", "typescript", "css", "webpack", "testing"]),
        ("alex_devops", "devops_engineer", ["docker", "kubernetes", "aws", "terraform", "monitoring"]),
        ("lisa_qa", "qa_engineer", ["testing", "automation", "selenium", "performance", "security"]),
        ("david_security", "security_specialist", ["security", "penetration", "compliance", "encryption"]),
        ("anna_designer", "ux_designer", ["design", "figma", "user_research", "prototyping", "accessibility"]),
        ("tom_data", "data_engineer", ["python", "sql", "spark", "airflow", "analytics"])
    ]
    
    for name, role, expertise in agents:
        agent_manager.create_agent(name, role, expertise)
    
    yield agent_manager


@pytest.fixture
async def test_scenario(websocket_server):
    """Create test scenario helper"""
    scenario = WebSocketTestScenario("ws://localhost:8771")
    yield scenario
    await scenario.cleanup_clients()


class TestDailyStandupScenario:
    """Test daily standup meeting scenario"""
    
    async def test_complete_standup_meeting(self, test_scenario, production_agent_system):
        """Test: Complete daily standup with team updates"""
        
        # Create team members
        team_members = await create_test_clients("ws://localhost:8771", [
            {"user_id": "scrum_master", "role": "scrum_master"},
            {"user_id": "product_owner", "role": "product_owner"},
            {"user_id": "dev_john", "role": "developer"},
            {"user_id": "dev_jane", "role": "developer"},
            {"user_id": "qa_bob", "role": "qa_engineer"}
        ])
        
        try:
            scrum_master = team_members["scrum_master"]
            product_owner = team_members["product_owner"]
            dev_john = team_members["dev_john"]
            dev_jane = team_members["dev_jane"]
            qa_bob = team_members["qa_bob"]
            
            # Step 1: Scrum master starts standup
            await scrum_master.send_message("Good morning team! Time for our daily standup. Let's go around and share updates.")
            
            # Step 2: Each team member provides updates
            await dev_john.send_message("Yesterday: Completed user authentication API. Today: Working on password reset functionality. Blockers: None.")
            
            await dev_jane.send_message("Yesterday: Fixed responsive design issues. Today: Implementing dark mode. Blockers: Waiting for design assets from Anna.")
            
            await qa_bob.send_message("Yesterday: Automated login tests. Today: Performance testing. Blockers: Need staging environment from DevOps.")
            
            # Step 3: Product owner asks for clarification
            await product_owner.send_message("@dev_john how long do you estimate for the password reset feature?")
            
            # Step 4: Developer responds with estimate
            await dev_john.send_message("@product_owner I estimate 2-3 days including testing and documentation.")
            
            # Step 5: Scrum master addresses blockers
            await scrum_master.send_message("@dev_jane let me check with @anna_designer about the design assets. @qa_bob I'll coordinate with @alex_devops for staging environment.")
            
            # Step 6: Wait for agent responses
            agent_responses = []
            for _ in range(6):  # Wait for multiple agent responses
                response = await scrum_master.wait_for_message(timeout=5)
                if (response and response.get('type') == 'chat_message' 
                    and response.get('data', {}).get('sender', '').endswith('-bot')):
                    agent_responses.append(response)
            
            # Step 7: Verify agents acknowledged their mentions
            responding_agents = {msg['data']['sender'].replace('-bot', '') for msg in agent_responses}
            assert 'anna_designer' in responding_agents or 'alex_devops' in responding_agents, "Mentioned agents should respond"
            
            # Step 8: Scrum master wraps up
            await scrum_master.send_message("Thanks everyone! Let's have a productive day. Reach out if you need help.")
            
            # Verify standup completion
            await asyncio.sleep(2)
            all_messages = scrum_master.get_messages_by_type('chat_message')
            assert len(all_messages) >= 8, "Standup should have multiple exchanges"
            
        finally:
            await cleanup_test_clients(team_members)
    
    async def test_standup_with_impediments(self, test_scenario, production_agent_system):
        """Test: Standup where team members report impediments"""
        
        team_members = await create_test_clients("ws://localhost:8771", [
            {"user_id": "scrum_master", "role": "scrum_master"},
            {"user_id": "senior_dev", "role": "senior_developer"},
            {"user_id": "junior_dev", "role": "junior_developer"}
        ])
        
        try:
            scrum_master = team_members["scrum_master"]
            senior_dev = team_members["senior_dev"]
            junior_dev = team_members["junior_dev"]
            
            # Junior developer reports being stuck
            await junior_dev.send_message("I'm blocked on the database migration. Getting foreign key constraint errors.")
            
            # Scrum master facilitates help
            await scrum_master.send_message("@senior_dev can you help @junior_dev with the database migration issue?")
            
            # Senior developer offers assistance
            await senior_dev.send_message("@junior_dev sure! Let's pair program on this. Can you share the error details?")
            
            # Junior developer provides details
            await junior_dev.send_message("@senior_dev the error is: 'FOREIGN KEY constraint failed' when trying to migrate user_profiles table.")
            
            # Senior developer provides guidance
            await senior_dev.send_message("@junior_dev that usually means the referenced table doesn't exist yet. Check the migration order.")
            
            # Agents might also offer help
            await scrum_master.send_message("@mike_backend do you have any insights on this database migration issue?")
            
            # Wait for agent response
            agent_response = await scrum_master.wait_for_agent_response("mike_backend", timeout=10)
            if agent_response:
                response_text = agent_response['data']['text'].lower()
                db_keywords = ['database', 'migration', 'foreign key', 'constraint', 'table']
                assert any(keyword in response_text for keyword in db_keywords)
            
            # Resolution
            await junior_dev.send_message("Thanks @senior_dev and @mike_backend! I'll check the migration dependencies.")
            
        finally:
            await cleanup_test_clients(team_members)


class TestSprintPlanningScenario:
    """Test sprint planning meeting scenario"""
    
    async def test_sprint_planning_session(self, test_scenario, production_agent_system):
        """Test: Complete sprint planning with story estimation"""
        
        team_members = await create_test_clients("ws://localhost:8771", [
            {"user_id": "product_owner", "role": "product_owner"},
            {"user_id": "scrum_master", "role": "scrum_master"},
            {"user_id": "tech_lead", "role": "tech_lead"},
            {"user_id": "dev1", "role": "developer"},
            {"user_id": "dev2", "role": "developer"},
            {"user_id": "qa_lead", "role": "qa_lead"}
        ])
        
        try:
            po = team_members["product_owner"]
            sm = team_members["scrum_master"]
            tl = team_members["tech_lead"]
            dev1 = team_members["dev1"]
            dev2 = team_members["dev2"]
            qa = team_members["qa_lead"]
            
            # Step 1: Product owner presents sprint goal
            await po.send_message("Sprint Goal: Implement user profile management with photo upload and privacy settings.")
            
            # Step 2: Present user stories
            stories = [
                "As a user, I want to upload a profile photo so that others can recognize me",
                "As a user, I want to set privacy settings so that I can control who sees my information",
                "As a user, I want to edit my profile information so that I can keep it up to date"
            ]
            
            for i, story in enumerate(stories, 1):
                await po.send_message(f"Story {i}: {story}")
            
            # Step 3: Tech lead breaks down technical requirements
            await tl.send_message("Technical breakdown: We'll need file upload API, image processing, privacy controls, and profile CRUD operations.")
            
            # Step 4: Team discusses implementation approach
            await dev1.send_message("For file upload, should we use cloud storage or local storage?")
            
            await tl.send_message("@alex_devops what's our current cloud storage setup? @david_security any security considerations for file uploads?")
            
            # Step 5: Wait for agent input
            agent_responses = []
            for _ in range(4):
                response = await tl.wait_for_message(timeout=8)
                if (response and response.get('type') == 'chat_message' 
                    and response.get('data', {}).get('sender', '').endswith('-bot')):
                    agent_responses.append(response)
            
            # Step 6: Verify technical agents provided input
            responding_agents = {msg['data']['sender'].replace('-bot', '') for msg in agent_responses}
            technical_input = any(agent in responding_agents for agent in ['alex_devops', 'david_security'])
            
            if technical_input:
                response_texts = [msg['data']['text'].lower() for msg in agent_responses]
                technical_keywords = ['storage', 'security', 'upload', 'cloud', 'file']
                assert any(any(keyword in text for keyword in technical_keywords) 
                          for text in response_texts)
            
            # Step 7: Estimation discussion
            await sm.send_message("Let's estimate these stories. Story 1 (profile photo upload) - what's your estimate?")
            
            await dev1.send_message("I think 5 story points - need to handle file validation, resizing, and storage.")
            await dev2.send_message("Agreed on 5 points. The image processing will take some time.")
            await qa.send_message("From testing perspective, we need to test different file formats and sizes.")
            
            # Step 8: Finalize sprint commitment
            await po.send_message("Based on our capacity and estimates, let's commit to stories 1 and 2 for this sprint.")
            
            await sm.send_message("Sprint commitment confirmed. @sarah_lead can you create the technical tasks?")
            
            # Step 9: Wait for tech lead agent response
            tech_lead_response = await sm.wait_for_agent_response("sarah_lead", timeout=10)
            if tech_lead_response:
                response_text = tech_lead_response['data']['text'].lower()
                task_keywords = ['tasks', 'breakdown', 'technical', 'implementation', 'create']
                assert any(keyword in response_text for keyword in task_keywords)
            
        finally:
            await cleanup_test_clients(team_members)


class TestIncidentResponseScenario:
    """Test incident response and crisis management"""
    
    async def test_production_incident_response(self, test_scenario, production_agent_system):
        """Test: Production incident response workflow"""
        
        team_members = await create_test_clients("ws://localhost:8771", [
            {"user_id": "on_call_engineer", "role": "sre"},
            {"user_id": "incident_commander", "role": "incident_commander"},
            {"user_id": "backend_dev", "role": "backend_developer"},
            {"user_id": "frontend_dev", "role": "frontend_developer"}
        ])
        
        try:
            on_call = team_members["on_call_engineer"]
            commander = team_members["incident_commander"]
            backend = team_members["backend_dev"]
            frontend = team_members["frontend_dev"]
            
            # Step 1: Incident detection
            await on_call.send_message("🚨 INCIDENT: API response times spiked to 5+ seconds. Users reporting login failures.")
            
            # Step 2: Incident commander takes charge
            await commander.send_message("I'm taking incident command. @on_call_engineer what's the current status?")
            
            # Step 3: Initial assessment
            await on_call.send_message("Database connections are maxed out. CPU at 90% on all API servers.")
            
            # Step 4: Assemble response team
            await commander.send_message("@backend_dev @alex_devops @lisa_qa please join incident response. @mike_backend any recent deployments?")
            
            # Step 5: Wait for agent responses
            agent_responses = []
            for _ in range(5):
                response = await commander.wait_for_message(timeout=8)
                if (response and response.get('type') == 'chat_message' 
                    and response.get('data', {}).get('sender', '').endswith('-bot')):
                    agent_responses.append(response)
            
            # Step 6: Verify agents are responding to incident
            responding_agents = {msg['data']['sender'].replace('-bot', '') for msg in agent_responses}
            incident_response = any(agent in responding_agents 
                                  for agent in ['alex_devops', 'lisa_qa', 'mike_backend'])
            
            if incident_response:
                response_texts = [msg['data']['text'].lower() for msg in agent_responses]
                incident_keywords = ['deployment', 'database', 'server', 'check', 'investigate']
                assert any(any(keyword in text for keyword in incident_keywords) 
                          for text in response_texts)
            
            # Step 7: Investigation and mitigation
            await backend.send_message("Checking recent deployments... Last deploy was 2 hours ago with database schema changes.")
            
            await commander.send_message("@alex_devops can you scale up the database connections? @mike_backend investigate the schema changes.")
            
            # Step 8: Status updates
            await on_call.send_message("Database connection pool increased. Response times improving to 2 seconds.")
            
            # Step 9: Resolution
            await backend.send_message("Found the issue - missing index on new user_activity table. Deploying fix now.")
            
            await on_call.send_message("✅ Response times back to normal. All systems green.")
            
            # Step 10: Post-incident
            await commander.send_message("Incident resolved. @lisa_qa please schedule post-mortem for tomorrow.")
            
            # Verify incident was handled
            all_messages = commander.get_messages_by_type('chat_message')
            assert len(all_messages) >= 10, "Incident response should have multiple exchanges"
            
            # Check for incident keywords
            message_texts = [msg['data']['text'].lower() for msg in all_messages]
            incident_handled = any(any(keyword in text for keyword in ['incident', 'resolved', 'fix', 'deploy']) 
                                 for text in message_texts)
            assert incident_handled, "Incident response should show resolution"
            
        finally:
            await cleanup_test_clients(team_members)
    
    async def test_security_incident_escalation(self, test_scenario, production_agent_system):
        """Test: Security incident with proper escalation"""
        
        team_members = await create_test_clients("ws://localhost:8771", [
            {"user_id": "security_analyst", "role": "security_analyst"},
            {"user_id": "ciso", "role": "ciso"},
            {"user_id": "sre", "role": "sre"}
        ])
        
        try:
            analyst = team_members["security_analyst"]
            ciso = team_members["ciso"]
            sre = team_members["sre"]
            
            # Step 1: Security alert
            await analyst.send_message("🔒 SECURITY ALERT: Unusual login patterns detected. Possible brute force attack on admin accounts.")
            
            # Step 2: Escalate to CISO
            await analyst.send_message("@ciso immediate attention required. Multiple failed login attempts from suspicious IPs.")
            
            # Step 3: CISO takes charge
            await ciso.send_message("Acknowledged. @david_security please assess the threat level. @sre block suspicious IPs immediately.")
            
            # Step 4: Wait for security agent response
            security_response = await ciso.wait_for_agent_response("david_security", timeout=10)
            if security_response:
                response_text = security_response['data']['text'].lower()
                security_keywords = ['security', 'threat', 'attack', 'block', 'investigate']
                assert any(keyword in response_text for keyword in security_keywords)
            
            # Step 5: Immediate response
            await sre.send_message("IPs blocked via firewall. Monitoring for additional suspicious activity.")
            
            # Step 6: Investigation
            await analyst.send_message("Analysis shows coordinated attack from botnet. Recommend enabling 2FA for all admin accounts.")
            
            # Step 7: Mitigation
            await ciso.send_message("@david_security implement emergency 2FA for all admin accounts. @sre increase monitoring.")
            
            # Step 8: Resolution
            await analyst.send_message("Attack mitigated. All admin accounts secured with 2FA. Threat neutralized.")
            
        finally:
            await cleanup_test_clients(team_members)


class TestCodeReviewScenario:
    """Test code review and collaboration workflow"""
    
    async def test_pull_request_review_cycle(self, test_scenario, production_agent_system):
        """Test: Complete pull request review cycle"""
        
        team_members = await create_test_clients("ws://localhost:8771", [
            {"user_id": "developer", "role": "developer"},
            {"user_id": "senior_dev", "role": "senior_developer"},
            {"user_id": "tech_lead", "role": "tech_lead"}
        ])
        
        try:
            dev = team_members["developer"]
            senior = team_members["senior_dev"]
            lead = team_members["tech_lead"]
            
            # Step 1: Developer submits PR
            await dev.send_message("PR #456 ready for review: Added user authentication with JWT tokens")
            
            # Step 2: Request specific reviewers
            await dev.send_message("@senior_dev @tech_lead please review when you have time. @david_security security review needed.")
            
            # Step 3: Senior developer starts review
            await senior.send_message("Looking at PR #456 now. @developer the JWT implementation looks good overall.")
            
            # Step 4: Senior developer finds issues
            await senior.send_message("@developer found a few issues: 1) Token expiration not handled 2) Missing input validation 3) No rate limiting")
            
            # Step 5: Wait for security agent input
            security_response = await senior.wait_for_agent_response("david_security", timeout=10)
            if security_response:
                response_text = security_response['data']['text'].lower()
                security_keywords = ['security', 'jwt', 'token', 'validation', 'authentication']
                assert any(keyword in response_text for keyword in security_keywords)
            
            # Step 6: Developer responds to feedback
            await dev.send_message("@senior_dev thanks for the review! I'll address those issues. @david_security any other security concerns?")
            
            # Step 7: Tech lead provides architectural feedback
            await lead.send_message("@developer consider using refresh tokens for better security. @sarah_lead thoughts on the architecture?")
            
            # Step 8: Wait for tech lead agent response
            arch_response = await lead.wait_for_agent_response("sarah_lead", timeout=10)
            if arch_response:
                response_text = arch_response['data']['text'].lower()
                arch_keywords = ['architecture', 'design', 'pattern', 'structure', 'implementation']
                assert any(keyword in response_text for keyword in arch_keywords)
            
            # Step 9: Developer updates PR
            await dev.send_message("Updated PR #456 with all feedback addressed. Added refresh tokens, input validation, and rate limiting.")
            
            # Step 10: Final approval
            await senior.send_message("LGTM! @tech_lead ready for your final approval.")
            await lead.send_message("Approved! Great work @developer. Merging now.")
            
        finally:
            await cleanup_test_clients(team_members)


class TestOnboardingScenario:
    """Test new team member onboarding"""
    
    async def test_new_developer_onboarding(self, test_scenario, production_agent_system):
        """Test: New developer onboarding process"""
        
        team_members = await create_test_clients("ws://localhost:8771", [
            {"user_id": "new_developer", "role": "junior_developer"},
            {"user_id": "mentor", "role": "senior_developer"},
            {"user_id": "team_lead", "role": "team_lead"},
            {"user_id": "hr_rep", "role": "hr"}
        ])
        
        try:
            new_dev = team_members["new_developer"]
            mentor = team_members["mentor"]
            lead = team_members["team_lead"]
            hr = team_members["hr_rep"]
            
            # Step 1: New developer introduction
            await new_dev.send_message("Hi everyone! I'm Alex, the new junior developer. Excited to join the team!")
            
            # Step 2: Team welcomes new member
            await mentor.send_message("Welcome Alex! I'm your assigned mentor. Let's get you set up.")
            await lead.send_message("Welcome to the team @new_developer! @mentor please help with the onboarding checklist.")
            
            # Step 3: HR provides initial guidance
            await hr.send_message("@new_developer welcome! I've sent you the onboarding materials. @team_lead please ensure dev environment setup.")
            
            # Step 4: Technical setup guidance
            await mentor.send_message("@new_developer let's start with development environment. Do you have Docker and Git installed?")
            
            await new_dev.send_message("@mentor yes, I have both installed. What's next?")
            
            # Step 5: Mentor provides technical guidance
            await mentor.send_message("@new_developer great! Let's clone the repository and set up the local environment. @alex_devops can you provide the setup documentation?")
            
            # Step 6: Wait for DevOps agent response
            devops_response = await mentor.wait_for_agent_response("alex_devops", timeout=10)
            if devops_response:
                response_text = devops_response['data']['text'].lower()
                setup_keywords = ['setup', 'environment', 'docker', 'documentation', 'repository']
                assert any(keyword in response_text for keyword in setup_keywords)
            
            # Step 7: First task assignment
            await lead.send_message("@new_developer once you're set up, I'll assign you a starter task. @mentor please pair with Alex on the first few tasks.")
            
            # Step 8: Knowledge sharing
            await new_dev.send_message("@mentor what are our coding standards and best practices?")
            
            await mentor.send_message("@new_developer we follow PEP 8 for Python, use type hints, and require tests. @sarah_lead can you share the coding guidelines?")
            
            # Step 9: Wait for tech lead agent response
            guidelines_response = await mentor.wait_for_agent_response("sarah_lead", timeout=10)
            if guidelines_response:
                response_text = guidelines_response['data']['text'].lower()
                guidelines_keywords = ['standards', 'guidelines', 'best practices', 'coding', 'quality']
                assert any(keyword in response_text for keyword in guidelines_keywords)
            
            # Step 10: First week check-in
            await lead.send_message("@new_developer how's your first day going? Any questions or blockers?")
            
            await new_dev.send_message("Going well! Environment is set up and I'm reading through the codebase. Thanks everyone for the warm welcome!")
            
        finally:
            await cleanup_test_clients(team_members)


class TestPerformanceTestingScenario:
    """Test performance and load testing scenarios"""
    
    async def test_high_volume_chat_simulation(self, test_scenario, production_agent_system):
        """Test: High volume chat simulation with multiple concurrent users"""
        
        # Create many concurrent users
        user_count = 10
        users = []
        
        for i in range(user_count):
            user = await test_scenario.create_client(f"user_{i}", "developer")
            users.append(user)
        
        try:
            # Step 1: All users join simultaneously
            join_tasks = []
            for i, user in enumerate(users):
                task = user.send_message(f"User {i} joining the high-volume test")
                join_tasks.append(task)
            
            await asyncio.gather(*join_tasks)
            
            # Step 2: Rapid message exchange
            message_tasks = []
            for round_num in range(5):  # 5 rounds of messages
                for i, user in enumerate(users):
                    task = user.send_message(f"Round {round_num} message from user {i}")
                    message_tasks.append(task)
                
                # Execute round of messages
                await asyncio.gather(*message_tasks)
                message_tasks.clear()
                
                # Small delay between rounds
                await asyncio.sleep(0.5)
            
            # Step 3: Agent mentions under load
            mention_tasks = []
            for i in range(0, user_count, 2):  # Every other user mentions an agent
                task = users[i].send_message(f"@sarah_lead user {i} needs help with performance testing")
                mention_tasks.append(task)
            
            await asyncio.gather(*mention_tasks)
            
            # Step 4: Wait for system to process all messages
            await asyncio.sleep(5)
            
            # Step 5: Verify message delivery
            for i, user in enumerate(users):
                message_count = len(user.get_messages_by_type('chat_message'))
                assert message_count >= user_count * 5, f"User {i} should receive messages from all users"
            
            # Step 6: Performance verification
            # Check that agents are still responsive under load
            test_user = users[0]
            await test_user.send_message("@mike_backend are you still responsive after the load test?")
            
            agent_response = await test_user.wait_for_agent_response("mike_backend", timeout=15)
            assert agent_response is not None, "Agents should remain responsive under load"
            
        finally:
            # Cleanup all users
            for user in users:
                await user.disconnect()
    
    async def test_message_burst_handling(self, test_scenario, production_agent_system):
        """Test: System handling of message bursts"""
        
        user = await test_scenario.create_client("burst_tester", "developer")
        
        try:
            # Step 1: Send burst of messages
            burst_size = 50
            burst_messages = []
            
            start_time = time.time()
            for i in range(burst_size):
                await user.send_message(f"Burst message {i} - testing system capacity")
                await asyncio.sleep(0.01)  # Very small delay
            
            end_time = time.time()
            burst_duration = end_time - start_time
            
            logger.info(f"Sent {burst_size} messages in {burst_duration:.2f} seconds")
            
            # Step 2: Wait for all messages to be processed
            await asyncio.sleep(3)
            
            # Step 3: Verify all messages were received
            received_messages = user.get_messages_by_type('chat_message')
            assert len(received_messages) >= burst_size, "All burst messages should be received"
            
            # Step 4: Test agent responsiveness after burst
            await user.send_message("@emma_frontend are you responsive after the message burst?")
            
            agent_response = await user.wait_for_agent_response("emma_frontend", timeout=10)
            assert agent_response is not None, "Agent should respond after message burst"
            
            # Step 5: Verify message ordering
            burst_messages_received = [msg for msg in received_messages 
                                     if "Burst message" in msg['data']['text']]
            
            # Check if messages are in reasonable order (some reordering is acceptable)
            ordered_count = 0
            for i in range(len(burst_messages_received) - 1):
                current_num = int(burst_messages_received[i]['data']['text'].split()[2])
                next_num = int(burst_messages_received[i + 1]['data']['text'].split()[2])
                if next_num > current_num:
                    ordered_count += 1
            
            # Allow some reordering but expect mostly ordered
            order_ratio = ordered_count / (len(burst_messages_received) - 1)
            assert order_ratio > 0.8, f"Messages should be mostly ordered, got {order_ratio:.2f}"
            
        finally:
            await user.disconnect()


if __name__ == "__main__":
    # Run real-world scenario tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])