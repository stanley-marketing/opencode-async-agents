"""
Individual communication agent implementation.
Handles specific employee communication in the chat.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base_communication_agent import BaseCommunicationAgent
from src.chat.message_parser import ParsedMessage, MessageParser
from src.chat.chat_config import config
from .react_agent import ReActAgent
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class CommunicationAgent(BaseCommunicationAgent):
    """Communication agent for a specific employee"""
    
    def __init__(self, employee_name: str, role: str, expertise: list = None, task_tracker = None):
        super().__init__(employee_name, role, expertise)
        self.message_parser = MessageParser()
        
        # Worker agent communication
        self.worker_status = "idle"  # idle, working, stuck, completed
        self.current_task = None
        self.task_progress = ""
        
        # Task tracking
        self.task_tracker = task_tracker
        
        # Initialize memory manager for short-term memory
        try:
            self.memory_manager = MemoryManager(employee_name)
            logger.info(f"Memory manager initialized for {employee_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize memory manager for {employee_name}: {e}")
            self.memory_manager = None
        
        # Initialize ReAct agent for intelligent conversations
        try:
            self.react_agent = ReActAgent(
                employee_name=employee_name,
                role=role,
                expertise=expertise or [],
                memory_manager=self.memory_manager,
                task_tracker=self.task_tracker
            )
            logger.info(f"ReAct agent initialized for {employee_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize ReAct agent for {employee_name}: {e}")
            self.react_agent = None
        
        # Callbacks for worker agent integration
        self.on_task_assigned = None
        self.on_help_received = None
    
    def handle_mention(self, message: ParsedMessage) -> Optional[str]:
        """Handle when this agent is mentioned"""
        self._add_recent_message(message)
        
        # Store conversation in memory
        if self.memory_manager:
            self.memory_manager.add_conversation(message.sender, message.text)
        
        # Check if it's asking for explanation or clarification (should be handled by ReAct agent)
        text_lower = message.text.lower()
        if any(keyword in text_lower for keyword in ['explain', 'what does', 'what mean', 'clarify', 'what is']):
            # Let the ReAct agent handle explanation requests
            return self._handle_general_mention(message)
        
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
        
        # Store conversation in memory
        if self.memory_manager:
            self.memory_manager.add_conversation(message.sender, message.text)
        
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
        
        # Check if agent is already working on something
        if self.worker_status == "working" and self.current_task:
            # User is asking for something while we're already working
            # Use status mode to explain what's currently happening
            return self._handle_status_inquiry(message)
        
        # ALWAYS use ReAct agent for task assignment responses (FORWARD mode)
        # The ReAct agent should handle ALL reasoning and response generation
        
        # Create context for the conversation with recent message history
        context = {
            "sender": message.sender,
            "timestamp": message.timestamp.isoformat() if message.timestamp else "unknown",
            "chat_type": "task_assignment",
            "recent_messages": self._get_recent_message_context()
        }
        
        # Let the ReAct agent handle the entire task assignment process in FORWARD mode
        if self.react_agent:
            try:
                response = self.react_agent.handle_message(message.text, context, mode="forward")
                if response and response.strip():
                    self._record_response()
                    
                    # Try to extract and assign the task to worker if callback is set
                    task_description = self.message_parser.extract_task_description(
                        message.text, self.employee_name
                    )

                    # If we couldn't extract from the original user message, try to parse it from the ReAct agent's response
                    if not task_description:
                        import re
                        match = re.search(r"Started coding task:\s*(.*)", response)
                        if match:
                            task_description = match.group(1).strip()

                    if self.on_task_assigned and task_description:
                        try:
                            assignment_successful = self.on_task_assigned(task_description)
                            if assignment_successful:
                                self.current_task = task_description
                                self.worker_status = "working"
                                self.active_tasks.add(task_description)
                        except Exception as e:
                            logger.error(f"Error notifying worker agent: {e}")
                    
                    return response
                else:
                    logger.warning(f"ReAct agent returned empty response for {self.employee_name}")
            except Exception as e:
                logger.warning(f"ReAct agent failed for {self.employee_name}: {e}")
        
        # Only fallback if ReAct agent completely fails
        self._record_response()
        return "I'm having trouble processing that request right now. Could you please try again?"
    
    def _handle_status_inquiry(self, message: ParsedMessage) -> str:
        """Handle when user asks about status while agent is working"""
        
        # Create context for status inquiry
        context = {
            "sender": message.sender,
            "timestamp": message.timestamp.isoformat() if message.timestamp else "unknown",
            "chat_type": "status_inquiry",
            "current_task": self.current_task,
            "worker_status": self.worker_status,
            "recent_messages": self._get_recent_message_context()
        }
        
        # Use ReAct agent in STATUS mode to explain current work
        if self.react_agent:
            try:
                response = self.react_agent.explain_current_status(self.employee_name)
                if response and response.strip():
                    self._record_response()
                    return response
                else:
                    logger.warning(f"ReAct agent returned empty status response for {self.employee_name}")
            except Exception as e:
                logger.warning(f"ReAct agent status check failed for {self.employee_name}: {e}")
        
        # Fallback status response
        self._record_response()
        return f"I'm currently working on: {self.current_task}. Let me finish this task first."
    
    def handle_task_completion(self, task_output: str, task_description: str | None = None) -> str:
        """Handle when a task completes and analyze the results (BACKWARD mode)"""
        
        # Use ReAct agent in BACKWARD mode to analyze task results
        if self.react_agent:
            try:
                # Update status
                self.worker_status = "completed"
                self.current_task = None
                
                # Analyze the task output and provide summary
                response = self.react_agent.analyze_task_results(task_output, task_description)
                if response and response.strip():

                    self._record_response()
                    return response
                else:
                    logger.warning(f"ReAct agent returned empty analysis for {self.employee_name}")
            except Exception as e:
                logger.warning(f"ReAct agent analysis failed for {self.employee_name}: {e}")
        
        # Fallback response if analysis failed or produced nothing meaningful
        self._record_response()
        return f"Task completed. Here's what happened:\n\n{task_output[:500]}..."
    
    def _handle_direct_help_request(self, message: ParsedMessage) -> str:
        """Handle a help request directed specifically at this agent"""
        
        # ALWAYS use ReAct agent for help requests
        # The ReAct agent should handle ALL reasoning and response generation
        
        # Create context for the conversation with recent message history
        context = {
            "sender": message.sender,
            "timestamp": message.timestamp.isoformat() if message.timestamp else "unknown",
            "chat_type": "help_request",
            "recent_messages": self._get_recent_message_context()
        }
        
        # Let the ReAct agent handle the help request
        if self.react_agent:
            try:
                response = self.react_agent.handle_message(message.text, context)
                if response and response.strip():
                    self._record_response()
                    return response
                else:
                    logger.warning(f"ReAct agent returned empty response for {self.employee_name}")
            except Exception as e:
                logger.warning(f"ReAct agent failed for {self.employee_name}: {e}")
        
        # Only fallback if ReAct agent completely fails
        self._record_response()
        return "I'm having trouble processing that request right now. Could you please try again?"
        
    def _handle_general_mention(self, message: ParsedMessage) -> str:
        """Handle a general mention (not task assignment or help request)"""
        
        # Check if this is a status inquiry while working
        if self.worker_status == "working" and self.current_task:
            text_lower = message.text.lower()
            if any(keyword in text_lower for keyword in ['what', 'how', 'status', 'progress', 'doing', 'working']):
                return self._handle_status_inquiry(message)
        
        # ALWAYS use ReAct agent for ALL responses
        # The ReAct agent should handle ALL reasoning and response generation
        
        # Create context for the conversation with recent message history
        context = {
            "sender": message.sender,
            "timestamp": message.timestamp.isoformat() if message.timestamp else "unknown",
            "chat_type": "general_mention",
            "recent_messages": self._get_recent_message_context()
        }
        
        # Get intelligent response from ReAct agent in FORWARD mode
        if self.react_agent:
            try:
                response = self.react_agent.handle_message(message.text, context, mode="forward")
                
                # Ensure we have a response
                if response and response.strip():
                    self._record_response()
                    return response
                else:
                    logger.warning(f"ReAct agent returned empty response for {self.employee_name}")
            except Exception as e:
                logger.warning(f"ReAct agent failed for {self.employee_name}: {e}")
        
        # Only fallback if ReAct agent completely fails
        self._record_response()
        return "I'm having trouble processing that request right now. Could you please try again?"

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
        
        # Use ReAct agent for intelligent discussion participation
        if self.react_agent and self._has_valuable_input(message):
            try:
                # Create context for the discussion
                context = {
                    "sender": message.sender,
                    "timestamp": message.timestamp.isoformat() if message.timestamp else "unknown",
                    "chat_type": "general_discussion",
                    "recent_messages": [
                        {
                            "sender": msg.sender,
                            "text": msg.text[:100] + "..." if len(msg.text) > 100 else msg.text,
                            "timestamp": msg.timestamp.isoformat() if msg.timestamp else "unknown"
                        }
                        for msg in list(self.recent_messages)[-5:]  # Last 5 messages for context
                    ]
                }
                
                # Get intelligent response from ReAct agent
                response = self.react_agent.handle_message(
                    f"General discussion in progress. Message from {message.sender}: {message.text}", 
                    context
                )
                
                # Only respond if we have something meaningful to add
                if response and len(response.strip()) > 10:  # At least 10 characters
                    self._record_response()
                    return response
            except Exception as e:
                logger.warning(f"ReAct agent discussion response failed for {self.employee_name}: {e}")
        
        # Fall back to simple responses for general discussion
        # Only respond if we have something valuable to add
        if not self._has_valuable_input(message):
            return None
        
        # Generate a brief, professional response
        response = self._generate_discussion_response(message)
        if response:
            self._record_response()
            return response
        
        return None

    def _get_recent_message_context(self) -> List[Dict]:
        """Get recent message context for ReAct agent"""
        context = []
        for msg in self.recent_messages[-5:]:  # Last 5 messages
            context.append({
                "sender": msg.sender,
                "text": msg.text,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else "unknown"
            })
        return context

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
        
        text_lower = message.text.lower()
        
        # More engaging responses based on context
        if "problem" in text_lower or "issue" in text_lower or "error" in text_lower:
            responses = [
                "That sounds challenging. Have you checked the logs for more details?",
                "I've seen similar issues before. Would you like me to help troubleshoot?",
                "That's frustrating. Let me know if there's anything I can do to help resolve it."
            ]
        elif "idea" in text_lower or "suggestion" in text_lower:
            responses = [
                "That's an interesting idea! I'd love to hear more details.",
                "Great suggestion! How do you think we could implement that?",
                "I like where you're going with this. What's the next step?"
            ]
        elif "progress" in text_lower or "status" in text_lower:
            responses = [
                "How's the progress coming along? Anything I can help with?",
                "That's good to hear! Let me know if you need any assistance.",
                "Sounds like good progress. Keep up the great work!"
            ]
        else:
            # Keep responses brief and professional
            responses = [
                "That's a good point.",
                "I agree with that approach.",
                "That should work well.",
                "Good idea.",
                "That makes sense.",
                "Interesting perspective!",
                "I hadn't thought of that.",
                "That could be very useful."
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

    def notify_worker_completed(self, task: str, task_output: str = None):
        """Called when worker agent completes a task"""
        self.worker_status = "completed"
        self.current_task = None
        
        if task in self.active_tasks:
            self.active_tasks.remove(task)
        
        # Analyze task output (if provided) and generate summary
        summary_msg = ""
        if task_output and self.react_agent:
            try:
                summary_msg = self.handle_task_completion(task_output, task)
            except Exception as e:
                logger.warning(f"Analysis failed for {self.employee_name}: {e}")
        
        # Announce completion
        completion_message = self.format_completion(task)
        if summary_msg:
            completion_message += "\n\n" + summary_msg
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