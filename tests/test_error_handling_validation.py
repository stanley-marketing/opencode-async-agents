#!/usr/bin/env python3
"""
Comprehensive Error Handling Validation Test Suite
Tests failure scenarios, recovery mechanisms, and system resilience
"""

import unittest
import sys
import os
import time
import threading
import tempfile
import signal
import subprocess
import json
import socket
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import OpencodeSlackServer
from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.agents.agent_manager import AgentManager
from src.chat.telegram_manager import TelegramManager
from src.utils.opencode_wrapper import OpencodeSessionManager, OpencodeSession

# Optional monitoring imports
try:
    from src.monitoring.agent_health_monitor import AgentHealthMonitor
    from src.monitoring.agent_recovery_manager import AgentRecoveryManager
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


class ErrorHandlingValidationTest(unittest.TestCase):
    """Comprehensive error handling validation test suite"""
    
    def setUp(self):
        """Set up test environment with temporary resources"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_employees.db")
        self.sessions_dir = os.path.join(self.temp_dir, "test_sessions")
        
        # Initialize core components
        self.file_manager = FileOwnershipManager(self.db_path)
        self.task_tracker = TaskProgressTracker(self.sessions_dir)
        
        # Mock telegram manager for testing
        self.telegram_manager = MockTelegramManager()
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        
        # Initialize session manager
        self.session_manager = OpencodeSessionManager(
            self.file_manager, self.sessions_dir, quiet_mode=True
        )
        
        # Set up monitoring system if available
        self.health_monitor = None
        self.recovery_manager = None
        if MONITORING_AVAILABLE:
            self._setup_monitoring_system()
        
        # Test results tracking
        self.test_results = {
            'agent_crash_recovery': [],
            'network_failure_handling': [],
            'task_timeout_scenarios': [],
            'system_resilience': [],
            'error_reporting': [],
            'graceful_degradation': [],
            'recovery_effectiveness': [],
            'error_propagation': []
        }
        
        print(f"🔧 Test environment initialized in {self.temp_dir}")
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def _setup_monitoring_system(self):
        """Set up monitoring system for testing"""
        try:
            self.agent_manager.setup_monitoring_system(self.task_tracker, self.session_manager)
            self.health_monitor = AgentHealthMonitor(self.agent_manager, self.task_tracker, polling_interval=1)
            self.recovery_manager = AgentRecoveryManager(self.agent_manager, self.session_manager)
            print("🔍 Monitoring system initialized for testing")
        except Exception as e:
            print(f"⚠️ Monitoring system setup failed: {e}")
    
    # ==================== AGENT CRASH RECOVERY TESTS ====================
    
    def test_agent_crash_and_restart(self):
        """Test agent crash detection and automatic restart"""
        print("\n🧪 Testing agent crash recovery...")
        
        # Create test employee and agent
        self.file_manager.hire_employee("crash_test_agent", "developer")
        agent = self.agent_manager.create_agent("crash_test_agent", "developer")
        
        # Simulate agent crash by corrupting its state
        original_status = agent.get_status()
        agent.worker_status = "crashed"
        agent.current_task = "test_task_before_crash"
        
        # Test crash detection
        crashed_status = agent.get_status()
        self.assertNotEqual(original_status, crashed_status)
        
        # Test recovery mechanism
        if self.recovery_manager:
            # Simulate recovery
            recovery_success = self.recovery_manager._restart_stuck_agent("crash_test_agent")
            
            self.test_results['agent_crash_recovery'].append({
                'test': 'agent_crash_and_restart',
                'success': recovery_success,
                'details': f"Agent recovery {'succeeded' if recovery_success else 'failed'}",
                'timestamp': datetime.now()
            })
        
        print(f"   ✅ Agent crash recovery test completed")
    
    def test_multiple_agent_failures(self):
        """Test system behavior when multiple agents fail simultaneously"""
        print("\n🧪 Testing multiple agent failures...")
        
        # Create multiple test agents
        agent_names = ["agent1", "agent2", "agent3"]
        for name in agent_names:
            self.file_manager.hire_employee(name, "developer")
            self.agent_manager.create_agent(name, "developer")
        
        # Simulate simultaneous failures
        failure_count = 0
        recovery_count = 0
        
        for name in agent_names:
            agent = self.agent_manager.agents[name]
            agent.worker_status = "stuck"
            failure_count += 1
            
            # Test individual recovery
            if self.recovery_manager:
                recovery_success = self.recovery_manager._restart_stuck_agent(name)
                if recovery_success:
                    recovery_count += 1
        
        recovery_rate = recovery_count / failure_count if failure_count > 0 else 0
        
        self.test_results['agent_crash_recovery'].append({
            'test': 'multiple_agent_failures',
            'success': recovery_rate >= 0.5,  # At least 50% recovery rate
            'details': f"Recovered {recovery_count}/{failure_count} agents ({recovery_rate:.1%})",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Multiple agent failure test completed: {recovery_count}/{failure_count} recovered")
    
    # ==================== NETWORK FAILURE HANDLING TESTS ====================
    
    def test_telegram_connection_failure(self):
        """Test handling of Telegram connection failures"""
        print("\n🧪 Testing Telegram connection failure handling...")
        
        # Test connection failure simulation
        original_connected = self.telegram_manager.is_connected()
        
        # Simulate network failure
        self.telegram_manager.simulate_network_failure()
        failed_connected = self.telegram_manager.is_connected()
        
        # Test message sending during failure
        send_success = self.telegram_manager.send_message("test message", "test_agent")
        
        # Test reconnection
        self.telegram_manager.restore_network()
        restored_connected = self.telegram_manager.is_connected()
        
        # Test message sending after restoration
        restored_send_success = self.telegram_manager.send_message("test message", "test_agent")
        
        self.test_results['network_failure_handling'].append({
            'test': 'telegram_connection_failure',
            'success': not send_success and restored_send_success,
            'details': f"Failed during outage: {not send_success}, Recovered: {restored_send_success}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Telegram connection failure test completed")
    
    def test_api_rate_limiting(self):
        """Test handling of API rate limiting"""
        print("\n🧪 Testing API rate limiting handling...")
        
        # Simulate rapid message sending to trigger rate limiting
        messages_sent = 0
        rate_limited = False
        
        for i in range(10):  # Try to send many messages quickly
            success = self.telegram_manager.send_message(f"Message {i}", "test_agent")
            if success:
                messages_sent += 1
            else:
                rate_limited = True
                break
            time.sleep(0.1)  # Small delay
        
        self.test_results['network_failure_handling'].append({
            'test': 'api_rate_limiting',
            'success': rate_limited,  # Rate limiting should kick in
            'details': f"Sent {messages_sent} messages before rate limiting",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ API rate limiting test completed: {messages_sent} messages sent")
    
    # ==================== TASK TIMEOUT SCENARIOS ====================
    
    def test_task_timeout_handling(self):
        """Test handling of task timeouts"""
        print("\n🧪 Testing task timeout handling...")
        
        # Create test employee
        self.file_manager.hire_employee("timeout_test", "developer")
        
        # Create a session with a very short timeout
        session = OpencodeSession(
            "timeout_test", "long running task", 
            self.file_manager, self.task_tracker,
            quiet_mode=True
        )
        
        # Mock a long-running process
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # Process still running
            mock_process.communicate.return_value = ("", "")
            mock_popen.return_value = mock_process
            
            # Start session
            session_id = session.start_session()
            
            # Wait briefly then stop
            time.sleep(0.5)
            session.stop_session()
            
            # Check if cleanup was called
            cleanup_success = not session.is_running
        
        self.test_results['task_timeout_scenarios'].append({
            'test': 'task_timeout_handling',
            'success': cleanup_success,
            'details': f"Session cleanup {'succeeded' if cleanup_success else 'failed'}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Task timeout handling test completed")
    
    def test_stuck_task_detection(self):
        """Test detection and handling of stuck tasks"""
        print("\n🧪 Testing stuck task detection...")
        
        if not self.health_monitor:
            print("   ⚠️ Monitoring system not available, skipping test")
            return
        
        # Create test employee and start monitoring
        self.file_manager.hire_employee("stuck_test", "developer")
        agent = self.agent_manager.create_agent("stuck_test", "developer")
        
        # Simulate stuck state
        agent.worker_status = "working"
        agent.current_task = "stuck_task"
        
        # Create fake history to simulate stuck state
        if hasattr(self.health_monitor, 'agent_history'):
            fake_status = {
                'worker_status': 'working',
                'current_task': 'stuck_task'
            }
            
            # Add multiple identical status records to simulate stuck state
            for i in range(5):
                status_record = {
                    'timestamp': datetime.now() - timedelta(minutes=i),
                    'status': fake_status,
                    'task_progress': {'overall_progress': 25}
                }
                if 'stuck_test' not in self.health_monitor.agent_history:
                    self.health_monitor.agent_history['stuck_test'] = []
                self.health_monitor.agent_history['stuck_test'].append(status_record)
        
        # Test anomaly detection
        anomalies = self.health_monitor._detect_anomalies('stuck_test', {
            'timestamp': datetime.now(),
            'status': fake_status,
            'task_progress': {'overall_progress': 25}
        })
        
        stuck_detected = "STUCK_STATE" in anomalies or "PROGRESS_STAGNANT" in anomalies
        
        self.test_results['task_timeout_scenarios'].append({
            'test': 'stuck_task_detection',
            'success': stuck_detected,
            'details': f"Anomalies detected: {anomalies}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Stuck task detection test completed: {anomalies}")
    
    # ==================== SYSTEM RESILIENCE TESTS ====================
    
    def test_database_corruption_recovery(self):
        """Test recovery from database corruption"""
        print("\n🧪 Testing database corruption recovery...")
        
        # Create some test data
        self.file_manager.hire_employee("db_test", "developer")
        
        # Simulate database corruption by writing invalid data
        try:
            with open(self.db_path, 'w') as f:
                f.write("CORRUPTED DATA")
            
            # Try to create new file manager (should handle corruption)
            new_file_manager = FileOwnershipManager(self.db_path)
            recovery_success = True
            
        except Exception as e:
            recovery_success = False
            print(f"   Database recovery failed: {e}")
        
        self.test_results['system_resilience'].append({
            'test': 'database_corruption_recovery',
            'success': recovery_success,
            'details': f"Database recovery {'succeeded' if recovery_success else 'failed'}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Database corruption recovery test completed")
    
    def test_file_system_errors(self):
        """Test handling of file system errors"""
        print("\n🧪 Testing file system error handling...")
        
        # Test with non-existent directory
        invalid_sessions_dir = "/invalid/path/sessions"
        
        try:
            # This should handle the error gracefully
            invalid_tracker = TaskProgressTracker(invalid_sessions_dir)
            # Try to create a task file
            invalid_tracker.create_task_file("test_employee", "test task", ["test.py"])
            fs_error_handled = True
        except Exception as e:
            fs_error_handled = False
            print(f"   File system error not handled: {e}")
        
        self.test_results['system_resilience'].append({
            'test': 'file_system_errors',
            'success': fs_error_handled,
            'details': f"File system error {'handled' if fs_error_handled else 'not handled'}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ File system error handling test completed")
    
    def test_memory_pressure_handling(self):
        """Test system behavior under memory pressure"""
        print("\n🧪 Testing memory pressure handling...")
        
        # Create many agents to simulate memory pressure
        agent_count = 50
        creation_success = 0
        
        for i in range(agent_count):
            try:
                employee_name = f"memory_test_{i}"
                self.file_manager.hire_employee(employee_name, "developer")
                self.agent_manager.create_agent(employee_name, "developer")
                creation_success += 1
            except Exception as e:
                print(f"   Agent creation failed at {i}: {e}")
                break
        
        # Test system still responds
        try:
            status = self.agent_manager.get_agent_status()
            system_responsive = len(status) > 0
        except Exception:
            system_responsive = False
        
        self.test_results['system_resilience'].append({
            'test': 'memory_pressure_handling',
            'success': system_responsive and creation_success > 10,
            'details': f"Created {creation_success} agents, system responsive: {system_responsive}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Memory pressure test completed: {creation_success} agents created")
    
    # ==================== ERROR REPORTING TESTS ====================
    
    def test_error_logging_accuracy(self):
        """Test accuracy and completeness of error logging"""
        print("\n🧪 Testing error logging accuracy...")
        
        # Capture log output
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('src')
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        # Generate test errors
        try:
            # Trigger an error in agent manager
            self.agent_manager.create_agent("", "invalid_role")
        except Exception:
            pass
        
        try:
            # Trigger an error in file manager
            self.file_manager.lock_files("nonexistent_employee", ["test.py"], "test")
        except Exception:
            pass
        
        # Check if errors were logged
        log_output = log_capture.getvalue()
        errors_logged = len(log_output.split('\n')) > 1
        
        logger.removeHandler(handler)
        
        self.test_results['error_reporting'].append({
            'test': 'error_logging_accuracy',
            'success': errors_logged,
            'details': f"Errors logged: {errors_logged}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Error logging accuracy test completed")
    
    def test_error_propagation_chain(self):
        """Test proper error propagation through the system"""
        print("\n🧪 Testing error propagation chain...")
        
        # Test error propagation from session to agent to manager
        propagation_chain = []
        
        # Create test employee
        self.file_manager.hire_employee("propagation_test", "developer")
        
        # Mock session manager to simulate error
        with patch.object(self.session_manager, 'start_employee_task') as mock_start:
            mock_start.side_effect = Exception("Simulated session error")
            
            try:
                # This should propagate the error up
                result = self.agent_manager._handle_task_assignment("propagation_test", "test task")
                propagation_chain.append(f"Task assignment returned: {result}")
            except Exception as e:
                propagation_chain.append(f"Exception caught: {e}")
        
        error_propagated = len(propagation_chain) > 0
        
        self.test_results['error_propagation'].append({
            'test': 'error_propagation_chain',
            'success': error_propagated,
            'details': f"Propagation chain: {propagation_chain}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Error propagation test completed")
    
    # ==================== GRACEFUL DEGRADATION TESTS ====================
    
    def test_partial_system_failure(self):
        """Test graceful degradation when parts of the system fail"""
        print("\n🧪 Testing graceful degradation...")
        
        # Disable telegram manager
        self.telegram_manager.simulate_network_failure()
        
        # Test that core functionality still works
        core_functions_working = 0
        total_functions = 4
        
        try:
            # Test employee management
            self.file_manager.hire_employee("degradation_test", "developer")
            core_functions_working += 1
        except Exception:
            pass
        
        try:
            # Test agent creation
            self.agent_manager.create_agent("degradation_test", "developer")
            core_functions_working += 1
        except Exception:
            pass
        
        try:
            # Test file locking
            self.file_manager.lock_files("degradation_test", ["test.py"], "test")
            core_functions_working += 1
        except Exception:
            pass
        
        try:
            # Test progress tracking
            self.task_tracker.create_task_file("degradation_test", "test task", ["test.py"])
            core_functions_working += 1
        except Exception:
            pass
        
        degradation_success = core_functions_working >= 3  # Most functions should work
        
        self.test_results['graceful_degradation'].append({
            'test': 'partial_system_failure',
            'success': degradation_success,
            'details': f"{core_functions_working}/{total_functions} core functions working",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Graceful degradation test completed: {core_functions_working}/{total_functions} working")
    
    # ==================== RECOVERY EFFECTIVENESS TESTS ====================
    
    def test_recovery_speed(self):
        """Test speed and effectiveness of recovery mechanisms"""
        print("\n🧪 Testing recovery speed and effectiveness...")
        
        if not self.recovery_manager:
            print("   ⚠️ Recovery manager not available, skipping test")
            return
        
        # Create test agent
        self.file_manager.hire_employee("recovery_speed_test", "developer")
        agent = self.agent_manager.create_agent("recovery_speed_test", "developer")
        
        # Simulate failure
        agent.worker_status = "stuck"
        failure_time = datetime.now()
        
        # Trigger recovery
        recovery_success = self.recovery_manager._restart_stuck_agent("recovery_speed_test")
        recovery_time = datetime.now()
        
        # Calculate recovery duration
        recovery_duration = (recovery_time - failure_time).total_seconds()
        
        # Recovery should be fast (under 5 seconds for test)
        speed_acceptable = recovery_duration < 5.0
        
        self.test_results['recovery_effectiveness'].append({
            'test': 'recovery_speed',
            'success': recovery_success and speed_acceptable,
            'details': f"Recovery took {recovery_duration:.2f}s, success: {recovery_success}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Recovery speed test completed: {recovery_duration:.2f}s")
    
    def test_recovery_completeness(self):
        """Test completeness of recovery (all resources cleaned up)"""
        print("\n🧪 Testing recovery completeness...")
        
        # Create test session with locked files
        self.file_manager.hire_employee("completeness_test", "developer")
        
        # Lock some files
        lock_result = self.file_manager.lock_files(
            "completeness_test", ["test1.py", "test2.py"], "test task"
        )
        
        # Simulate session crash
        session = OpencodeSession(
            "completeness_test", "test task",
            self.file_manager, self.task_tracker,
            quiet_mode=True
        )
        
        # Start and immediately stop to simulate crash
        session_id = session.start_session()
        time.sleep(0.1)
        session.stop_session()
        
        # Check if files were released
        locked_files = self.file_manager.get_all_locked_files()
        files_released = len(locked_files) == 0
        
        self.test_results['recovery_effectiveness'].append({
            'test': 'recovery_completeness',
            'success': files_released,
            'details': f"Files released: {files_released}, remaining locks: {len(locked_files)}",
            'timestamp': datetime.now()
        })
        
        print(f"   ✅ Recovery completeness test completed: {len(locked_files)} locks remaining")
    
    # ==================== TEST EXECUTION AND REPORTING ====================
    
    def test_comprehensive_error_handling_validation(self):
        """Run all error handling validation tests and generate report"""
        print("\n🚀 Starting Comprehensive Error Handling Validation")
        print("=" * 60)
        
        # Run all test categories
        test_methods = [
            # Agent crash recovery
            self.test_agent_crash_and_restart,
            self.test_multiple_agent_failures,
            
            # Network failure handling
            self.test_telegram_connection_failure,
            self.test_api_rate_limiting,
            
            # Task timeout scenarios
            self.test_task_timeout_handling,
            self.test_stuck_task_detection,
            
            # System resilience
            self.test_database_corruption_recovery,
            self.test_file_system_errors,
            self.test_memory_pressure_handling,
            
            # Error reporting
            self.test_error_logging_accuracy,
            self.test_error_propagation_chain,
            
            # Graceful degradation
            self.test_partial_system_failure,
            
            # Recovery effectiveness
            self.test_recovery_speed,
            self.test_recovery_completeness,
        ]
        
        # Execute all tests
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"   ❌ Test {test_method.__name__} failed with exception: {e}")
        
        # Generate comprehensive report
        self._generate_validation_report()
    
    def _generate_validation_report(self):
        """Generate comprehensive validation report"""
        print("\n📊 ERROR HANDLING VALIDATION REPORT")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        
        for category, results in self.test_results.items():
            if not results:
                continue
                
            print(f"\n🔍 {category.replace('_', ' ').title()}:")
            category_passed = 0
            
            for result in results:
                total_tests += 1
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                print(f"   {status} {result['test']}: {result['details']}")
                
                if result['success']:
                    passed_tests += 1
                    category_passed += 1
            
            category_rate = category_passed / len(results) if results else 0
            print(f"   📈 Category Success Rate: {category_rate:.1%} ({category_passed}/{len(results)})")
        
        # Overall statistics
        overall_rate = passed_tests / total_tests if total_tests > 0 else 0
        print(f"\n📈 OVERALL SUCCESS RATE: {overall_rate:.1%} ({passed_tests}/{total_tests})")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if overall_rate >= 0.9:
            print("   🎉 Excellent error handling! System shows strong resilience.")
        elif overall_rate >= 0.7:
            print("   👍 Good error handling with room for improvement.")
        elif overall_rate >= 0.5:
            print("   ⚠️  Moderate error handling. Consider strengthening failure scenarios.")
        else:
            print("   🚨 Poor error handling. Significant improvements needed.")
        
        # Specific recommendations based on failures
        failed_categories = [cat for cat, results in self.test_results.items() 
                           if results and not all(r['success'] for r in results)]
        
        if failed_categories:
            print(f"\n🔧 PRIORITY AREAS FOR IMPROVEMENT:")
            for category in failed_categories:
                print(f"   • {category.replace('_', ' ').title()}")
        
        print(f"\n✅ Validation completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


class MockTelegramManager:
    """Mock Telegram manager for testing"""
    
    def __init__(self):
        self.messages = []
        self.connected = True
        self.network_failure = False
        self.message_count = 0
        
    def add_message_handler(self, handler):
        pass
    
    def is_connected(self):
        return self.connected and not self.network_failure
    
    def send_message(self, text, sender_name="system", reply_to=None):
        if self.network_failure:
            return False
        
        # Simulate rate limiting
        self.message_count += 1
        if self.message_count > 5:  # Rate limit after 5 messages
            return False
        
        self.messages.append({
            'text': text,
            'sender': sender_name,
            'timestamp': datetime.now()
        })
        return True
    
    def simulate_network_failure(self):
        """Simulate network failure"""
        self.network_failure = True
        self.connected = False
    
    def restore_network(self):
        """Restore network connection"""
        self.network_failure = False
        self.connected = True
        self.message_count = 0  # Reset rate limiting


if __name__ == '__main__':
    # Run the comprehensive validation
    suite = unittest.TestLoader().loadTestsFromTestCase(ErrorHandlingValidationTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)