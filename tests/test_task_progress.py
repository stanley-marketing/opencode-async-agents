import unittest
import os
import tempfile
import sys
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trackers.task_progress import TaskProgressTracker

class TestTaskProgressTracker(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.tracker = TaskProgressTracker(self.test_dir)
    
    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_create_task_file(self):
        """Test that we can create a task file for an employee"""
        task_file = self.tracker.create_task_file(
            "sarah", 
            "implement auth feature", 
            ["src/auth.py", "src/user.py"]
        )
        
        # Check that the file was created
        self.assertTrue(os.path.exists(task_file))
        
        # Check the content
        with open(task_file, 'r') as f:
            content = f.read()
        
        self.assertIn("# Current Task: implement auth feature", content)
        self.assertIn("- src/auth.py (not started)", content)
        self.assertIn("- src/user.py (not started)", content)
    
    def test_get_task_progress(self):
        """Test that we can get task progress"""
        # Create a task file first
        self.tracker.create_task_file(
            "sarah", 
            "implement auth feature", 
            ["src/auth.py", "src/user.py"]
        )
        
        # Get the progress
        progress = self.tracker.get_task_progress("sarah")
        
        # Check the progress data
        self.assertIsNotNone(progress)
        self.assertEqual(progress['employee'], 'sarah')
        self.assertEqual(progress['task_description'], 'implement auth feature')
        self.assertIn('src/auth.py', progress['file_status'])
        self.assertIn('src/user.py', progress['file_status'])
    
    def test_update_file_status(self):
        """Test that we can update file status"""
        # Create a task file first
        self.tracker.create_task_file(
            "sarah", 
            "implement auth feature", 
            ["src/auth.py"]
        )
        
        # Update the file status
        result = self.tracker.update_file_status(
            "sarah", 
            "src/auth.py", 
            50, 
            "halfway done with JWT implementation"
        )
        
        self.assertTrue(result)
        
        # Check that the status was updated
        progress = self.tracker.get_task_progress("sarah")
        self.assertEqual(progress['file_status']['src/auth.py']['percentage'], 50)
    
    def test_suggest_file_releases(self):
        """Test that we can suggest files to release"""
        # Create a task file first
        self.tracker.create_task_file(
            "sarah", 
            "implement auth feature", 
            ["src/auth.py", "src/user.py"]
        )
        
        # Manually update one file to be ready for release
        task_file = os.path.join(self.test_dir, "sarah", "current_task.md")
        with open(task_file, 'r') as f:
            content = f.read()
        
        # Update content to mark one file as ready
        content = content.replace(
            "- src/auth.py: 0% complete (not started)", 
            "- src/auth.py: 100% complete (READY TO RELEASE)"
        )
        
        with open(task_file, 'w') as f:
            f.write(content)
        
        # Check suggested releases
        releases = self.tracker.suggest_file_releases("sarah")
        self.assertIn("src/auth.py", releases)
        self.assertNotIn("src/user.py", releases)

if __name__ == '__main__':
    unittest.main()