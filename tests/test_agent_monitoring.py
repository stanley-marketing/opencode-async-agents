"""
Test cases for the agent monitoring system
"""

import unittest
import sys
from pathlib import Path
import tempfile
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.agents.agent_manager import AgentManager
from src.chat.telegram_manager import TelegramManager


class TestAgentMonitoring(unittest.TestCase):
    """Test cases for agent monitoring system"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create temporary database and sessions directory for testing
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        
        self.test_sessions_dir = tempfile.mkdtemp()
        
        # Initialize components
        self.file_manager = FileOwnershipManager(self.test_db.name)
        self.task_tracker = TaskProgressTracker(self.test_sessions_dir)
        
        # Mock telegram manager for testing
        class MockTelegramManager:
            def __init__(self):
                self.messages = []
            
            def add_message_handler(self, handler):
                pass
            
            def is_connected(self):
                return False
        
        self.telegram_manager = MockTelegramManager()
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
    
    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Clean up temporary files
        try:
            os.unlink(self.test_db.name)
        except:
            pass
        
        try:
            import shutil
            shutil.rmtree(self.test_sessions_dir)
        except:
            pass
    
    def test_monitoring_system_imports(self):
        """Test that monitoring system components can be imported"""
        try:
            from src.monitoring.agent_health_monitor import AgentHealthMonitor
            from src.monitoring.agent_recovery_manager import AgentRecoveryManager
            from src.monitoring.monitoring_dashboard import MonitoringDashboard
            monitoring_available = True
        except ImportError:
            monitoring_available = False
        
        # This test should pass if the files exist and can be imported
        self.assertTrue(monitoring_available, "Monitoring system components should be importable")
    
    def test_health_monitor_initialization(self):
        """Test that AgentHealthMonitor can be initialized"""
        try:
            from src.monitoring.agent_health_monitor import AgentHealthMonitor
            health_monitor = AgentHealthMonitor(self.agent_manager, self.task_tracker)
            self.assertIsNotNone(health_monitor)
        except ImportError:
            self.skipTest("Monitoring system not available")
        except Exception as e:
            self.fail(f"AgentHealthMonitor initialization failed: {e}")
    
    def test_recovery_manager_initialization(self):
        """Test that AgentRecoveryManager can be initialized"""
        try:
            from src.monitoring.agent_recovery_manager import AgentRecoveryManager
            
            # Mock session manager for testing
            class MockSessionManager:
                def __init__(self):
                    self.active_sessions = {}
                
                def get_active_sessions(self):
                    return self.active_sessions
            
            session_manager = MockSessionManager()
            recovery_manager = AgentRecoveryManager(self.agent_manager, session_manager)
            self.assertIsNotNone(recovery_manager)
        except ImportError:
            self.skipTest("Monitoring system not available")
        except Exception as e:
            self.fail(f"AgentRecoveryManager initialization failed: {e}")
    
    def test_monitoring_dashboard_initialization(self):
        """Test that MonitoringDashboard can be initialized"""
        try:
            from src.monitoring.monitoring_dashboard import MonitoringDashboard
            from src.monitoring.agent_health_monitor import AgentHealthMonitor
            from src.monitoring.agent_recovery_manager import AgentRecoveryManager
            
            # Mock session manager for testing
            class MockSessionManager:
                def __init__(self):
                    self.active_sessions = {}
                
                def get_active_sessions(self):
                    return self.active_sessions
            
            # Initialize monitoring components
            health_monitor = AgentHealthMonitor(self.agent_manager, self.task_tracker)
            session_manager = MockSessionManager()
            recovery_manager = AgentRecoveryManager(self.agent_manager, session_manager)
            
            # Initialize dashboard
            dashboard = MonitoringDashboard(health_monitor, recovery_manager)
            self.assertIsNotNone(dashboard)
        except ImportError:
            self.skipTest("Monitoring system not available")
        except Exception as e:
            self.fail(f"MonitoringDashboard initialization failed: {e}")


if __name__ == '__main__':
    unittest.main()