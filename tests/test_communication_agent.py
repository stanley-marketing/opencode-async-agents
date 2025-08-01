"""
Tests for ReAct Agent functionality.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import os
from dotenv import load_dotenv

from src.agents.react_agent import ReActAgent
from src.chat.message_parser import ParsedMessage

# Load environment variables from .env file
load_dotenv()


class TestReActAgent(unittest.TestCase):
    """Test cases for ReActAgent"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Use the API key from .env file, or fallback to test key
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = "test-key"
        
        with patch('src.agents.react_agent.ChatOpenAI'), \
             patch('src.services.llm_service.ChatOpenAI'):
            self.agent = ReActAgent(
                employee_name="john",
                role="developer",
                expertise=["python", "javascript", "api"]
            )
    
    def test_initialization(self):
        """Test ReActAgent initialization"""
        self.assertEqual(self.agent.employee_name, "john")
        self.assertEqual(self.agent.role, "developer")
        self.assertEqual(self.agent.expertise, ["python", "javascript", "api"])
        self.assertIsNotNone(self.agent.tools)
        self.assertIsNotNone(self.agent.agent_executor)
    
    def create_test_message(self, text, sender="testuser", mentions=None):
        """Helper to create test messages"""
        if mentions is None:
            mentions = []
        
        return ParsedMessage(
            message_id=1,
            text=text,
            sender=sender,
            timestamp=datetime.now(),
            mentions=mentions,
            is_command=False
        )
    
    def test_handle_message_basic_functionality(self):
        """Test basic message handling functionality"""
        # Test that the method exists and can be called
        response = self.agent.handle_message("Hello")
        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
    
    def test_handle_message_with_context(self):
        """Test handling message with additional context"""
        context = {"user_id": "U123", "channel": "general"}
        
        # Test that context can be passed without errors
        response = self.agent.handle_message("Start a new task", context)
        
        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
    
    def test_handle_message_error_handling(self):
        """Test that error handling works properly"""
        # Test with an invalid message that might cause issues
        response = self.agent.handle_message("")
        
        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
    
    def test_tools_are_properly_initialized(self):
        """Test that all required tools are properly initialized"""
        tool_names = [tool.name for tool in self.agent.tools]
        
        self.assertIn("start_task", tool_names)
        self.assertIn("look_at_project", tool_names)
        self.assertIn("check_progress", tool_names)
    
    def test_agent_has_correct_expertise(self):
        """Test that agent maintains expertise information"""
        self.assertIn("python", self.agent.expertise)
        self.assertIn("javascript", self.agent.expertise)
        self.assertIn("api", self.agent.expertise)
    
    def test_project_context_is_set(self):
        """Test that project context is properly set"""
        self.assertIsNotNone(self.agent.project_context)
        self.assertIn("opencode-slack", self.agent.project_context)
    
    def test_llm_service_is_initialized(self):
        """Test that LLM service is properly initialized"""
        self.assertIsNotNone(self.agent.llm_service)
        self.assertIsNotNone(self.agent.llm)
    
    def test_get_agent_info(self):
        """Test getting agent information"""
        info = self.agent.get_agent_info()
        
        self.assertEqual(info["employee_name"], "john")
        self.assertEqual(info["role"], "developer")
        self.assertEqual(info["expertise"], ["python", "javascript", "api"])
        self.assertIn("available_tools", info)
        self.assertIn("start_task", info["available_tools"])
        self.assertIn("look_at_project", info["available_tools"])
        self.assertIn("check_progress", info["available_tools"])
    
    def test_update_project_context(self):
        """Test updating project context"""
        new_context = "Updated project context with new information"
        
        self.agent.update_project_context(new_context)
        
        self.assertEqual(self.agent.project_context, new_context)
        self.assertIsNotNone(self.agent.agent)
        self.assertIsNotNone(self.agent.agent_executor)


if __name__ == '__main__':
    unittest.main()