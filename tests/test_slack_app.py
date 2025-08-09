import unittest
import sys
from pathlib import Path
import json

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.slack_app import app

class TestSlackApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_hire_command(self):
        # Test the /hire command
        response = self.app.post('/slack/command', data={
            'command': '/hire',
            'text': 'sarah developer',
            'user_name': 'test_user'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['response_type'], 'ephemeral')
        self.assertIn('Successfully hired sarah as a developer!', data['text'])
    
    def test_fire_command(self):
        # Test the /fire command
        # First hire an employee
        self.app.post('/slack/command', data={
            'command': '/hire',
            'text': 'sarah developer',
            'user_name': 'test_user'
        })
        
        # Then fire the employee
        response = self.app.post('/slack/command', data={
            'command': '/fire',
            'text': 'sarah',
            'user_name': 'test_user'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['response_type'], 'ephemeral')
        self.assertIn('Successfully fired sarah.', data['text'])
    
    def test_employees_command(self):
        # Test the /employees command
        response = self.app.post('/slack/command', data={
            'command': '/employees',
            'text': '',
            'user_name': 'test_user'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['response_type'], 'ephemeral')
    
    def test_unknown_command(self):
        # Test an unknown command
        response = self.app.post('/slack/command', data={
            'command': '/unknown',
            'text': '',
            'user_name': 'test_user'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['response_type'], 'ephemeral')
        self.assertIn('Unknown command', data['text'])

if __name__ == '__main__':
    unittest.main()