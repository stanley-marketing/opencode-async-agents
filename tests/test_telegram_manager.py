"""
Tests for TelegramManager functionality.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime
import threading
import time

from src.chat.telegram_manager import TelegramManager
from src.chat.message_parser import ParsedMessage


class TestTelegramManager(unittest.TestCase):
    """Test cases for TelegramManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        with patch('src.chat.telegram_manager.config') as mock_config:
            mock_config.bot_token = "test_token"
            mock_config.chat_id = "test_chat_id"
            mock_config.max_message_length = 4096
            mock_config.max_messages_per_hour = 20
            mock_config.response_delay_seconds = 2
            mock_config.get_bot_name.return_value = "TestBot"
            mock_config.is_configured.return_value = True
            
            self.telegram_manager = TelegramManager()
    
    def test_initialization(self):
        """Test TelegramManager initialization"""
        self.assertEqual(self.telegram_manager.bot_token, "test_token")
        self.assertEqual(self.telegram_manager.chat_id, "test_chat_id")
        self.assertFalse(self.telegram_manager.is_polling)
        self.assertEqual(len(self.telegram_manager.message_handlers), 0)
    
    def test_add_message_handler(self):
        """Test adding message handlers"""
        handler = Mock()
        self.telegram_manager.add_message_handler(handler)
        
        self.assertEqual(len(self.telegram_manager.message_handlers), 1)
        self.assertIn(handler, self.telegram_manager.message_handlers)
    
    @patch('src.chat.telegram_manager.config')
    def test_start_polling_not_configured(self, mock_config):
        """Test start_polling when not configured"""
        mock_config.is_configured.return_value = False
        
        self.telegram_manager.start_polling()
        
        self.assertFalse(self.telegram_manager.is_polling)
        self.assertIsNone(self.telegram_manager.polling_thread)
    
    @patch('src.chat.telegram_manager.config')
    def test_start_polling_success(self, mock_config):
        """Test successful start_polling"""
        mock_config.is_configured.return_value = True
        
        self.telegram_manager.start_polling()
        
        self.assertTrue(self.telegram_manager.is_polling)
        self.assertIsNotNone(self.telegram_manager.polling_thread)
        self.assertTrue(self.telegram_manager.polling_thread.daemon)
        
        # Clean up
        self.telegram_manager.stop_polling()
    
    def test_stop_polling(self):
        """Test stop_polling"""
        # Start polling first
        with patch('src.chat.telegram_manager.config') as mock_config:
            mock_config.is_configured.return_value = True
            self.telegram_manager.start_polling()
            
            # Now stop it
            self.telegram_manager.stop_polling()
            
            self.assertFalse(self.telegram_manager.is_polling)
    
    @patch('requests.get')
    def test_get_updates_success(self, mock_get):
        """Test successful _get_updates"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': True,
            'result': [
                {'update_id': 1, 'message': {'text': 'test'}},
                {'update_id': 2, 'message': {'text': 'test2'}}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        updates = self.telegram_manager._get_updates()
        
        self.assertEqual(len(updates), 2)
        self.assertEqual(self.telegram_manager.last_update_id, 2)
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_updates_api_error(self, mock_get):
        """Test _get_updates with API error"""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': False, 'error': 'test error'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        updates = self.telegram_manager._get_updates()
        
        self.assertEqual(len(updates), 0)
    
    @patch('requests.get')
    def test_get_updates_exception(self, mock_get):
        """Test _get_updates with exception"""
        mock_get.side_effect = Exception("Network error")
        
        updates = self.telegram_manager._get_updates()
        
        self.assertEqual(len(updates), 0)
    
    def test_process_update_no_message(self):
        """Test _process_update with no message data"""
        update = {'update_id': 1}
        handler = Mock()
        self.telegram_manager.add_message_handler(handler)
        
        self.telegram_manager._process_update(update)
        
        handler.assert_not_called()
    
    def test_process_update_wrong_chat(self):
        """Test _process_update from wrong chat"""
        update = {
            'update_id': 1,
            'message': {
                'message_id': 1,
                'text': 'test',
                'chat': {'id': 'wrong_chat_id'},
                'from': {'username': 'testuser'},
                'date': 1234567890
            }
        }
        handler = Mock()
        self.telegram_manager.add_message_handler(handler)
        
        self.telegram_manager._process_update(update)
        
        handler.assert_not_called()
    
    def test_process_update_success(self):
        """Test successful _process_update"""
        update = {
            'update_id': 1,
            'message': {
                'message_id': 1,
                'text': '@john please help',
                'chat': {'id': 'test_chat_id'},
                'from': {'username': 'testuser'},
                'date': 1234567890
            }
        }
        handler = Mock()
        self.telegram_manager.add_message_handler(handler)
        
        self.telegram_manager._process_update(update)
        
        handler.assert_called_once()
        # Check that the parsed message was passed correctly
        call_args = handler.call_args[0][0]
        self.assertIsInstance(call_args, ParsedMessage)
        self.assertEqual(call_args.text, '@john please help')
        self.assertEqual(call_args.sender, 'testuser')
        self.assertIn('john', call_args.mentions)
    
    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful send_message"""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.telegram_manager.send_message("Hello", "testuser")
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Check the request data
        call_args = mock_post.call_args
        self.assertIn('json', call_args[1])
        json_data = call_args[1]['json']
        self.assertEqual(json_data['chat_id'], 'test_chat_id')
        self.assertIn('TestBot: Hello', json_data['text'])
    
    @patch('requests.post')
    def test_send_message_rate_limited(self, mock_post):
        """Test send_message with rate limiting"""
        # Send a message first to trigger rate limiting
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # First message should succeed
        result1 = self.telegram_manager.send_message("Hello", "testuser")
        self.assertTrue(result1)
        
        # Second message immediately should be rate limited
        result2 = self.telegram_manager.send_message("Hello again", "testuser")
        self.assertFalse(result2)
    
    @patch('requests.post')
    def test_send_message_api_error(self, mock_post):
        """Test send_message with API error"""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': False, 'error': 'test error'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.telegram_manager.send_message("Hello", "testuser")
        
        self.assertFalse(result)
    
    @patch('requests.post')
    def test_send_message_exception(self, mock_post):
        """Test send_message with exception"""
        mock_post.side_effect = Exception("Network error")
        
        result = self.telegram_manager.send_message("Hello", "testuser")
        
        self.assertFalse(result)
    
    def test_send_message_truncation(self):
        """Test message truncation for long messages"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {'ok': True}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # Create a very long message
            long_message = "A" * 5000
            
            result = self.telegram_manager.send_message(long_message, "testuser")
            
            self.assertTrue(result)
            
            # Check that message was truncated
            call_args = mock_post.call_args
            json_data = call_args[1]['json']
            self.assertTrue(json_data['text'].endswith('...'))
            self.assertLessEqual(len(json_data['text']), 4096)
    
    @patch('requests.get')
    def test_is_connected_success(self, mock_get):
        """Test successful is_connected"""
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.telegram_manager.is_connected()
        
        self.assertTrue(result)
    
    @patch('requests.get')
    def test_is_connected_failure(self, mock_get):
        """Test is_connected failure"""
        mock_get.side_effect = Exception("Network error")
        
        result = self.telegram_manager.is_connected()
        
        self.assertFalse(result)
    
    @patch('requests.get')
    def test_get_chat_info_success(self, mock_get):
        """Test successful get_chat_info"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': True,
            'result': {'id': 'test_chat_id', 'title': 'Test Chat'}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.telegram_manager.get_chat_info()
        
        self.assertEqual(result['id'], 'test_chat_id')
        self.assertEqual(result['title'], 'Test Chat')
    
    @patch('requests.get')
    def test_get_chat_info_failure(self, mock_get):
        """Test get_chat_info failure"""
        mock_get.side_effect = Exception("Network error")
        
        result = self.telegram_manager.get_chat_info()
        
        self.assertEqual(result, {})
    
    def test_rate_limiting_logic(self):
        """Test rate limiting logic"""
        sender = "testuser"
        
        # Should be able to send initially
        self.assertTrue(self.telegram_manager._can_send_message(sender))
        
        # Record a message sent
        self.telegram_manager._record_message_sent(sender)
        
        # Should be rate limited immediately after
        self.assertFalse(self.telegram_manager._can_send_message(sender))
        
        # Wait for rate limit to expire
        time.sleep(3)  # Wait longer than response_delay_seconds
        
        # Should be able to send again
        self.assertTrue(self.telegram_manager._can_send_message(sender))


if __name__ == '__main__':
    unittest.main()