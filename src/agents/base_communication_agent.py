"""
Base communication agent class.
Defines the interface and common behavior for all communication agents.
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

from src.chat.message_parser import ParsedMessage
from src.chat.chat_config import config

logger = logging.getLogger(__name__)

class BaseCommunicationAgent(ABC):
    """Base class for all communication agents"""
    
    def __init__(self, employee_name: str, role: str, expertise: List[str] = None):
        self.employee_name = employee_name
        self.role = role
        self.expertise = expertise or []
        
        # Personality traits
        self.is_timid = True
        self.is_professional = True
        self.response_probability = 0.7  # 70% chance to respond to general chat
        
        # State tracking
        self.last_response_time = None
        self.recent_messages: List[ParsedMessage] = []
        self.active_tasks: Set[str] = set()
        
        # Message templates
        self.acknowledgment_templates = [
            "Got it! I'll work on {task}.",
            "Understood. Starting work on {task}.",
            "On it! Working on {task} now.",
            "Sure thing. I'll handle {task}.",
        ]
        
        self.completion_templates = [
            "✅ Completed: {task}",
            "✅ Done with {task}",
            "✅ Finished {task} successfully",
            "✅ {task} is ready",
        ]
        
        self.help_request_templates = [
            "@team I need help with {task}. So far I've {progress}. Any suggestions?",
            "@team Stuck on {task}. I've {progress} but having trouble with {issue}. Ideas?",
            "@team Could use some help. Working on {task}, completed {progress}, but {issue}. Thoughts?",
        ]
        
        self.help_offer_templates = [
            "I might be able to help with that. Try {suggestion}.",
            "Have you considered {suggestion}?",
            "In my experience, {suggestion} usually works.",
            "Maybe try {suggestion}?",
        ]
    
    @abstractmethod
    def handle_mention(self, message: ParsedMessage) -> Optional[str]:
        """Handle when this agent is mentioned in a message"""
        pass
    
    @abstractmethod
    def handle_general_message(self, message: ParsedMessage) -> Optional[str]:
        """Handle general messages (not mentions) - decide whether to respond"""
        pass
    
    @abstractmethod
    def handle_help_request(self, message: ParsedMessage) -> Optional[str]:
        """Handle help requests from other agents"""
        pass
    
    def should_respond_to_general_message(self, message: ParsedMessage) -> bool:
        """Decide whether to respond to a general message"""
        
        # Don't respond to own messages
        if message.sender == config.get_bot_name(self.employee_name):
            return False
        
        # Don't respond too frequently (timid personality)
        if self._responded_recently():
            return False
        
        # Check if message is relevant to expertise
        if not self._is_message_relevant(message):
            return False
        
        # Random chance to respond (timid behavior)
        return random.random() < self.response_probability
    
    def should_offer_help(self, message: ParsedMessage) -> bool:
        """Decide whether to offer help on a message"""
        
        # Don't help own messages
        if message.sender == config.get_bot_name(self.employee_name):
            return False
        
        # Only help if it's a help request
        if not self.message_parser.is_help_request(message.text):
            return False
        
        # Check if we have relevant expertise
        if not self._has_relevant_expertise(message):
            return False
        
        # Random chance to offer help (professional but not pushy)
        return random.random() < config.help_offer_probability
    
    def _responded_recently(self) -> bool:
        """Check if agent responded recently (timid behavior)"""
        if not self.last_response_time:
            return False
        
        time_since_last = datetime.now() - self.last_response_time
        return time_since_last < timedelta(minutes=5)  # Wait 5 minutes between responses
    
    def _is_message_relevant(self, message: ParsedMessage) -> bool:
        """Check if message is relevant to this agent's expertise"""
        text_lower = message.text.lower()
        
        # Check if any expertise keywords are mentioned
        for skill in self.expertise:
            if skill.lower() in text_lower:
                return True
        
        # Check role-specific keywords
        role_keywords = {
            'developer': ['code', 'bug', 'function', 'api', 'database'],
            'designer': ['ui', 'design', 'layout', 'css', 'style'],
            'tester': ['test', 'testing', 'bug', 'error', 'quality'],
        }
        
        keywords = role_keywords.get(self.role.lower(), [])
        return any(keyword in text_lower for keyword in keywords)
    
    def _has_relevant_expertise(self, message: ParsedMessage) -> bool:
        """Check if agent has expertise relevant to the message"""
        return self._is_message_relevant(message)
    
    def _record_response(self):
        """Record that agent responded (for rate limiting)"""
        self.last_response_time = datetime.now()
    
    def _add_recent_message(self, message: ParsedMessage):
        """Add message to recent messages for context"""
        self.recent_messages.append(message)
        
        # Keep only last 10 messages
        if len(self.recent_messages) > 10:
            self.recent_messages = self.recent_messages[-10:]
    
    def _get_random_template(self, templates: List[str]) -> str:
        """Get a random template from a list"""
        return random.choice(templates)
    
    def format_acknowledgment(self, task: str) -> str:
        """Format a task acknowledgment message"""
        template = self._get_random_template(self.acknowledgment_templates)
        return template.format(task=task)
    
    def format_completion(self, task: str) -> str:
        """Format a task completion message"""
        template = self._get_random_template(self.completion_templates)
        return template.format(task=task)
    
    def format_help_request(self, task: str, progress: str, issue: str = "") -> str:
        """Format a help request message"""
        template = self._get_random_template(self.help_request_templates)
        return template.format(task=task, progress=progress, issue=issue)
    
    def format_help_offer(self, suggestion: str) -> str:
        """Format a help offer message"""
        template = self._get_random_template(self.help_offer_templates)
        return template.format(suggestion=suggestion)