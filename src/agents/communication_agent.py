"""
Individual communication agent implementation.
Handles specific employee communication in the chat.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .base_communication_agent import BaseCommunicationAgent
from src.chat.message_parser import ParsedMessage, MessageParser
from src.chat.chat_config import config

logger = logging.getLogger(__name__)

class CommunicationAgent(BaseCommunicationAgent):
    """Communication agent for a specific employee"""
    
    def __init__(self, employee_name: str, role: str, expertise: list = None):
        super().__init__(employee_name, role, expertise)
        self.message_parser = MessageParser()
        
        # Worker agent communication
        self.worker_status = "idle"  # idle, working, stuck, completed
        self.current_task = None
        self.task_progress = ""
        
        # Callbacks for worker agent integration
        self.on_task_assigned = None
        self.on_help_received = None
    
    def handle_mention(self, message: ParsedMessage) -> Optional[str]:
        """Handle when this agent is mentioned"""
        self._add_recent_message(message)
        
        # Check if it's a task assignment
        if self.message_parser.is_task_assignment(message.text, message.mentions):
            return self._handle_task_assignment(message)
        
        # Check if it's a help request directed at us
        if self.message_parser.is_help_request(message.text):
            return self._handle_direct_help_request(message)
        
        # General mention - acknowledge politely
        return self._handle_general_mention(message)
    
    def handle_general_message(self, message: ParsedMessage) -> Optional[str]:
        """Handle general messages (decide whether to respond)"""
        self._add_recent_message(message)
        
        # Check if we should offer help
        if self.should_offer_help(message):
            return self._offer_help(message)
        
        # Check if we should respond to general discussion
        if self.should_respond_to_general_message(message):
            return self._respond_to_general_discussion(message)
        
        return None
    
    def handle_help_request(self, message: ParsedMessage) -> Optional[str]:
        """Handle help requests from other agents"""
        if not self.should_offer_help(message):
            return None
        
        return self._offer_help(message)
    
    def _handle_task_assignment(self, message: ParsedMessage) -> str:
        """Handle a task being assigned to this agent"""
        
        # Extract task description
        task_description = self.message_parser.extract_task_description(
            message.text, self.employee_name
        )
        
        # Update state
        self.current_task = task_description
        self.worker_status = "working"
        self.active_tasks.add(task_description)
        
        # Notify worker agent if callback is set
        if self.on_task_assigned:
            try:
                self.on_task_assigned(task_description)
            except Exception as e:
                logger.error(f"Error notifying worker agent: {e}")
        
        # Record response and return acknowledgment
        self._record_response()
        return self.format_acknowledgment(task_description)
    
    def _handle_direct_help_request(self, message: ParsedMessage) -> str:
        """Handle a help request directed specifically at this agent"""
        
        # Analyze what kind of help is needed
        help_topic = self._analyze_help_topic(message.text)
        
        if help_topic and help_topic in self.expertise:
            suggestion = self._generate_help_suggestion(help_topic, message.text)
            self._record_response()
            return self.format_help_offer(suggestion)
        else:
            self._record_response()
            return "I'm not sure I can help with that, but let me think about it."
    
    def _handle_general_mention(self, message: ParsedMessage) -> str:
        """Handle a general mention (not task assignment or help request)"""
        responses = [
            "Yes?",
            "How can I help?",
            "What's up?",
            "I'm here.",
        ]
        
        import random
        self._record_response()
        return random.choice(responses)
    
    def _offer_help(self, message: ParsedMessage) -> Optional[str]:
        """Offer help on a message"""
        
        # Analyze what help might be needed
        help_topic = self._analyze_help_topic(message.text)
        
        if not help_topic or help_topic not in self.expertise:
            return None
        
        suggestion = self._generate_help_suggestion(help_topic, message.text)
        if suggestion:
            self._record_response()
            return self.format_help_offer(suggestion)
        
        return None
    
    def _respond_to_general_discussion(self, message: ParsedMessage) -> Optional[str]:
        """Respond to general discussion if relevant"""
        
        # Only respond if we have something valuable to add
        if not self._has_valuable_input(message):
            return None
        
        # Generate a brief, professional response
        response = self._generate_discussion_response(message)
        if response:
            self._record_response()
            return response
        
        return None
    
    def _analyze_help_topic(self, text: str) -> Optional[str]:
        """Analyze what topic help is needed for"""
        text_lower = text.lower()
        
        # Map keywords to expertise areas
        topic_keywords = {
            'html': ['html', 'markup', 'tags', 'elements'],
            'css': ['css', 'style', 'styling', 'layout', 'design'],
            'javascript': ['javascript', 'js', 'function', 'script'],
            'python': ['python', 'py', 'django', 'flask'],
            'database': ['database', 'sql', 'query', 'db'],
            'api': ['api', 'endpoint', 'rest', 'http'],
            'testing': ['test', 'testing', 'bug', 'error'],
        }
        
        for topic, keywords in topic_keywords.items():
            if topic in self.expertise and any(keyword in text_lower for keyword in keywords):
                return topic
        
        return None
    
    def _generate_help_suggestion(self, topic: str, context: str) -> Optional[str]:
        """Generate a helpful suggestion based on topic and context"""
        
        # Topic-specific suggestions
        suggestions = {
            'html': [
                "checking your HTML syntax and closing tags",
                "using semantic HTML elements",
                "validating your HTML structure",
            ],
            'css': [
                "using CSS Grid or Flexbox for layout",
                "checking CSS specificity issues",
                "using browser dev tools to debug styles",
            ],
            'javascript': [
                "checking the browser console for errors",
                "using console.log to debug your code",
                "making sure your variables are properly scoped",
            ],
            'python': [
                "checking your Python syntax and indentation",
                "using print statements to debug",
                "checking if all required modules are imported",
            ],
            'database': [
                "checking your SQL query syntax",
                "making sure your database connection is working",
                "verifying your table and column names",
            ],
            'api': [
                "checking your API endpoint URL",
                "verifying your request headers and parameters",
                "testing with a tool like curl or Postman",
            ],
            'testing': [
                "writing unit tests to isolate the issue",
                "checking error logs for more details",
                "testing with different input values",
            ],
        }
        
        topic_suggestions = suggestions.get(topic, [])
        if topic_suggestions:
            import random
            return random.choice(topic_suggestions)
        
        return None
    
    def _has_valuable_input(self, message: ParsedMessage) -> bool:
        """Check if agent has valuable input for general discussion"""
        
        # Only respond if message is about our expertise
        if not self._is_message_relevant(message):
            return False
        
        # Don't respond if someone else already helped
        recent_help = any(
            msg.sender != self.employee_name and 
            any(word in msg.text.lower() for word in ['try', 'use', 'check', 'maybe'])
            for msg in self.recent_messages[-3:]  # Last 3 messages
        )
        
        return not recent_help
    
    def _generate_discussion_response(self, message: ParsedMessage) -> Optional[str]:
        """Generate a response to general discussion"""
        
        # Keep responses brief and professional
        responses = [
            "That's a good point.",
            "I agree with that approach.",
            "That should work well.",
            "Good idea.",
            "That makes sense.",
        ]
        
        import random
        return random.choice(responses)
    
    # Worker agent integration methods
    
    def notify_worker_stuck(self, task: str, progress: str, issue: str = ""):
        """Called when worker agent gets stuck"""
        self.worker_status = "stuck"
        self.task_progress = progress
        
        # Request help from team
        help_message = self.format_help_request(task, progress, issue)
        return help_message
    
    def notify_worker_completed(self, task: str):
        """Called when worker agent completes a task"""
        self.worker_status = "completed"
        self.current_task = None
        
        if task in self.active_tasks:
            self.active_tasks.remove(task)
        
        # Announce completion
        completion_message = self.format_completion(task)
        return completion_message
    
    def provide_help_to_worker(self, help_messages: list) -> str:
        """Provide collected help messages to worker agent"""
        
        if not help_messages:
            return "No specific help was offered, but you can continue with your current approach."
        
        # Summarize help received
        help_summary = "Here's what the team suggested:\\n"
        for i, msg in enumerate(help_messages, 1):
            help_summary += f"{i}. {msg}\\n"
        
        # Notify callback if set
        if self.on_help_received:
            try:
                self.on_help_received(help_summary)
            except Exception as e:
                logger.error(f"Error providing help to worker: {e}")
        
        return help_summary
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            'employee_name': self.employee_name,
            'role': self.role,
            'expertise': self.expertise,
            'worker_status': self.worker_status,
            'current_task': self.current_task,
            'active_tasks': list(self.active_tasks),
            'last_response': self.last_response_time.isoformat() if self.last_response_time else None,
        }