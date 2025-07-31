"""
Agent manager for coordinating all communication agents.
Handles agent creation, message routing, and lifecycle management.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .communication_agent import CommunicationAgent
from src.chat.telegram_manager import TelegramManager
from src.chat.message_parser import ParsedMessage
from src.managers.file_ownership import FileOwnershipManager

logger = logging.getLogger(__name__)

class AgentManager:
    """Manages all communication agents and coordinates their interactions"""
    
    def __init__(self, file_manager: FileOwnershipManager, telegram_manager: TelegramManager):
        self.file_manager = file_manager
        self.telegram_manager = telegram_manager
        self.agents: Dict[str, CommunicationAgent] = {}
        
        # Message handling
        self.telegram_manager.add_message_handler(self.handle_message)
        
        # Help request tracking
        self.pending_help_requests: Dict[str, Dict] = {}
        
        # Initialize agents for existing employees
        self._initialize_existing_agents()
    
    def _initialize_existing_agents(self):
        """Create communication agents for existing employees"""
        employees = self.file_manager.list_employees()
        
        for employee in employees:
            name = employee['name']
            role = employee['role']
            
            # Define expertise based on role
            expertise = self._get_expertise_for_role(role)
            
            self.create_agent(name, role, expertise)
        
        logger.info(f"Initialized {len(self.agents)} communication agents")
    
    def _get_expertise_for_role(self, role: str) -> List[str]:
        """Get expertise areas based on employee role"""
        role_expertise = {
            'developer': ['python', 'javascript', 'html', 'css', 'api', 'database'],
            'FS-developer': ['python', 'javascript', 'html', 'css', 'api', 'database', 'testing'],
            'frontend-developer': ['javascript', 'html', 'css', 'react', 'vue'],
            'backend-developer': ['python', 'api', 'database', 'server'],
            'designer': ['css', 'html', 'ui', 'design'],
            'tester': ['testing', 'qa', 'debugging'],
            'devops': ['deployment', 'server', 'docker', 'ci/cd'],
        }
        
        return role_expertise.get(role.lower(), ['general'])
    
    def create_agent(self, employee_name: str, role: str, expertise: List[str] = None) -> CommunicationAgent:
        """Create a new communication agent for an employee"""
        
        if employee_name in self.agents:
            logger.warning(f"Agent for {employee_name} already exists")
            return self.agents[employee_name]
        
        if expertise is None:
            expertise = self._get_expertise_for_role(role)
        
        agent = CommunicationAgent(employee_name, role, expertise)
        
        # Set up callbacks for worker integration
        agent.on_task_assigned = lambda task: self._handle_task_assignment(employee_name, task)
        agent.on_help_received = lambda help_text: self._handle_help_received(employee_name, help_text)
        
        self.agents[employee_name] = agent
        
        logger.info(f"Created communication agent for {employee_name} ({role})")
        return agent
    
    def remove_agent(self, employee_name: str):
        """Remove a communication agent"""
        if employee_name in self.agents:
            del self.agents[employee_name]
            logger.info(f"Removed communication agent for {employee_name}")
    
    def handle_message(self, message: ParsedMessage):
        """Handle incoming messages from Telegram"""
        
        # Skip messages from our own bots
        if message.sender.endswith('-bot'):
            return
        
        logger.info(f"Processing message from {message.sender}: {message.text[:50]}...")
        
        # Handle mentions first
        responses = []
        for mentioned_employee in message.mentions:
            if mentioned_employee in self.agents:
                agent = self.agents[mentioned_employee]
                response = agent.handle_mention(message)
                if response:
                    responses.append((mentioned_employee, response))
        
        # If no mentions, let agents decide if they want to respond
        if not message.mentions:
            for employee_name, agent in self.agents.items():
                response = agent.handle_general_message(message)
                if response:
                    responses.append((employee_name, response))
                    break  # Only one agent responds to general messages
        
        # Send responses
        for employee_name, response in responses:
            success = self.telegram_manager.send_message(response, employee_name, message.message_id)
            if success:
                logger.info(f"Agent {employee_name} responded to message")
            else:
                logger.error(f"Failed to send response from {employee_name}")
    
    def _handle_task_assignment(self, employee_name: str, task: str):
        """Handle task assignment to worker agent"""
        
        # This is where we'll integrate with the existing worker system
        # For now, just log the task assignment
        logger.info(f"Task assigned to {employee_name}: {task}")
        
        # TODO: Integrate with OpencodeSessionManager to start actual work
        # session_manager.start_employee_task(employee_name, task)
    
    def _handle_help_received(self, employee_name: str, help_text: str):
        """Handle help received by an agent"""
        logger.info(f"Help provided to {employee_name}: {help_text[:100]}...")
        
        # TODO: Forward help to worker agent
    
    def request_help_for_agent(self, employee_name: str, task: str, progress: str, issue: str = "") -> bool:
        """Request help for a stuck agent"""
        
        if employee_name not in self.agents:
            logger.error(f"No agent found for {employee_name}")
            return False
        
        agent = self.agents[employee_name]
        help_message = agent.notify_worker_stuck(task, progress, issue)
        
        # Send help request to chat
        success = self.telegram_manager.send_message(help_message, employee_name)
        
        if success:
            # Track help request
            request_id = f"{employee_name}_{int(datetime.now().timestamp())}"
            self.pending_help_requests[request_id] = {
                'employee': employee_name,
                'task': task,
                'progress': progress,
                'issue': issue,
                'requested_at': datetime.now(),
                'responses': []
            }
            
            logger.info(f"Help requested for {employee_name}")
            return True
        
        return False
    
    def notify_task_completion(self, employee_name: str, task: str) -> bool:
        """Notify that an agent completed a task"""
        
        if employee_name not in self.agents:
            logger.error(f"No agent found for {employee_name}")
            return False
        
        agent = self.agents[employee_name]
        completion_message = agent.notify_worker_completed(task)
        
        # Send completion message to chat
        success = self.telegram_manager.send_message(completion_message, employee_name)
        
        if success:
            logger.info(f"Task completion announced for {employee_name}")
            return True
        
        return False
    
    def get_agent_status(self, employee_name: str = None) -> Dict[str, Any]:
        """Get status of agents"""
        
        if employee_name:
            if employee_name in self.agents:
                return self.agents[employee_name].get_status()
            else:
                return {}
        
        # Return status of all agents
        return {
            name: agent.get_status() 
            for name, agent in self.agents.items()
        }
    
    def list_active_agents(self) -> List[str]:
        """List all active communication agents"""
        return list(self.agents.keys())
    
    def is_agent_available(self, employee_name: str) -> bool:
        """Check if an agent is available for new tasks"""
        if employee_name not in self.agents:
            return False
        
        agent = self.agents[employee_name]
        return agent.worker_status in ['idle', 'completed']
    
    def get_chat_statistics(self) -> Dict[str, Any]:
        """Get statistics about chat activity"""
        
        total_agents = len(self.agents)
        working_agents = sum(1 for agent in self.agents.values() if agent.worker_status == 'working')
        stuck_agents = sum(1 for agent in self.agents.values() if agent.worker_status == 'stuck')
        
        return {
            'total_agents': total_agents,
            'working_agents': working_agents,
            'stuck_agents': stuck_agents,
            'idle_agents': total_agents - working_agents - stuck_agents,
            'pending_help_requests': len(self.pending_help_requests),
            'chat_connected': self.telegram_manager.is_connected(),
        }