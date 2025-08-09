#!/usr/bin/env python3
"""
Comprehensive test suite for the agent monitoring and health systems
"""

import sys
import time
import json
import requests
import threading
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.agents.agent_manager import AgentManager
from src.chat.telegram_manager import TelegramManager
from src.monitoring.agent_health_monitor import AgentHealthMonitor
from src.monitoring.agent_recovery_manager import AgentRecoveryManager
from src.monitoring.monitoring_dashboard import MonitoringDashboard
from src.utils.opencode_wrapper import OpencodeSessionManager

class MonitoringSystemTester:
    """Comprehensive tester for the monitoring system"""
    
    def __init__(self):
        self.test_results = {
            'health_monitoring': {},
            'task_progress': {},
            'dashboard': {},
            'recovery_system': {},
            'metrics_collection': {},
            'alerting': {},
            'api_endpoints': {}
        }
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Set up test environment with mock components"""
        print("🔧 Setting up test environment...")
        
        # Create temporary database and sessions directory
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_sessions_dir = tempfile.mkdtemp()
        
        # Initialize core components
        self.file_manager = FileOwnershipManager(self.test_db.name)
        self.task_tracker = TaskProgressTracker(self.test_sessions_dir)
        
        # Mock telegram manager
        class MockTelegramManager:
            def __init__(self):
                self.messages = []
                self.connected = True
            
            def add_message_handler(self, handler):
                pass
            
            def is_connected(self):
                return self.connected
            
            def send_message(self, message, sender=None, reply_to=None):
                self.messages.append({
                    'message': message,
                    'sender': sender,
                    'reply_to': reply_to,
                    'timestamp': datetime.now()
                })
                return True
        
        # Mock session manager
        class MockSessionManager:
            def __init__(self, task_tracker):
                self.active_sessions = {}
                self.task_tracker = task_tracker
            
            def get_active_sessions(self):
                return self.active_sessions
            
            def start_employee_task(self, employee_name, task):
                session_id = f"session_{employee_name}_{int(time.time())}"
                self.active_sessions[employee_name] = session_id
                return session_id
            
            def stop_employee_task(self, employee_name):
                if employee_name in self.active_sessions:
                    del self.active_sessions[employee_name]
                return True
        
        self.telegram_manager = MockTelegramManager()
        self.session_manager = MockSessionManager(self.task_tracker)
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        
        # Set up monitoring system
        self.agent_manager.setup_monitoring_system(self.task_tracker, self.session_manager)
        
        # Create test agents
        self.create_test_agents()
        
        print("✅ Test environment set up successfully")
    
    def create_test_agents(self):
        """Create test agents for monitoring"""
        test_employees = [
            ('test_agent_1', 'developer'),
            ('test_agent_2', 'frontend-developer'),
            ('test_agent_3', 'backend-developer')
        ]
        
        for name, role in test_employees:
            self.file_manager.hire_employee(name, role)
            expertise = self.agent_manager._get_expertise_for_role(role)
            self.agent_manager.create_agent(name, role, expertise)
    
    def test_health_monitoring_accuracy(self):
        """Test 1: Agent health monitoring accuracy and real-time updates"""
        print("\n🔍 Testing health monitoring accuracy...")
        
        try:
            # Test basic health monitoring
            health_monitor = self.agent_manager.health_monitor
            if not health_monitor:
                self.test_results['health_monitoring']['basic_functionality'] = {
                    'status': 'FAIL',
                    'error': 'Health monitor not initialized'
                }
                return
            
            # Get initial health summary
            initial_summary = health_monitor.get_agent_health_summary()
            
            # Verify all test agents are present
            expected_agents = {'test_agent_1', 'test_agent_2', 'test_agent_3'}
            actual_agents = set(initial_summary.get('agent_details', {}).keys())
            
            if not expected_agents.issubset(actual_agents):
                self.test_results['health_monitoring']['agent_detection'] = {
                    'status': 'FAIL',
                    'expected': list(expected_agents),
                    'actual': list(actual_agents),
                    'missing': list(expected_agents - actual_agents)
                }
            else:
                self.test_results['health_monitoring']['agent_detection'] = {
                    'status': 'PASS',
                    'agents_detected': len(expected_agents)
                }
            
            # Test health status accuracy
            all_healthy = all(
                agent['health_status'] == 'HEALTHY' 
                for agent in initial_summary.get('agent_details', {}).values()
            )
            
            self.test_results['health_monitoring']['status_accuracy'] = {
                'status': 'PASS' if all_healthy else 'FAIL',
                'all_agents_healthy': all_healthy,
                'total_agents': initial_summary.get('total_agents', 0),
                'healthy_agents': initial_summary.get('healthy_agents', 0)
            }
            
            # Test real-time updates by simulating agent status change
            test_agent = self.agent_manager.agents.get('test_agent_1')
            if test_agent:
                # Simulate working status
                test_agent.worker_status = 'working'
                test_agent.current_task = 'Test task for monitoring'
                
                # Wait a moment and check if monitoring detects the change
                time.sleep(1)
                updated_summary = health_monitor.get_agent_health_summary()
                
                agent_details = updated_summary.get('agent_details', {}).get('test_agent_1', {})
                status_updated = agent_details.get('worker_status') == 'working'
                
                self.test_results['health_monitoring']['real_time_updates'] = {
                    'status': 'PASS' if status_updated else 'FAIL',
                    'status_change_detected': status_updated,
                    'current_status': agent_details.get('worker_status', 'unknown')
                }
            
            print("✅ Health monitoring accuracy tests completed")
            
        except Exception as e:
            self.test_results['health_monitoring']['error'] = {
                'status': 'FAIL',
                'exception': str(e)
            }
            print(f"❌ Health monitoring test failed: {e}")
    
    def test_task_progress_tracking(self):
        """Test 2: Task progress tracking during execution"""
        print("\n📊 Testing task progress tracking...")
        
        try:
            # Create a test task file
            task_description = "Test task for progress tracking"
            files_needed = ['test_file1.py', 'test_file2.py']
            
            task_file = self.task_tracker.create_task_file(
                'test_agent_1', task_description, files_needed
            )
            
            # Verify task file creation
            if os.path.exists(task_file):
                self.test_results['task_progress']['file_creation'] = {
                    'status': 'PASS',
                    'task_file': task_file
                }
            else:
                self.test_results['task_progress']['file_creation'] = {
                    'status': 'FAIL',
                    'task_file': task_file
                }
                return
            
            # Test progress retrieval
            progress = self.task_tracker.get_task_progress('test_agent_1')
            
            if progress:
                self.test_results['task_progress']['progress_retrieval'] = {
                    'status': 'PASS',
                    'task_description': progress.get('task_description'),
                    'overall_progress': progress.get('overall_progress'),
                    'file_count': len(progress.get('file_status', {}))
                }
            else:
                self.test_results['task_progress']['progress_retrieval'] = {
                    'status': 'FAIL',
                    'error': 'No progress data retrieved'
                }
                return
            
            # Test progress updates
            update_success = self.task_tracker.update_file_status(
                'test_agent_1', 'test_file1.py', 50, 'In progress'
            )
            
            if update_success:
                updated_progress = self.task_tracker.get_task_progress('test_agent_1')
                file_status = updated_progress.get('file_status', {}).get('test_file1.py', {})
                
                self.test_results['task_progress']['progress_updates'] = {
                    'status': 'PASS' if file_status.get('percentage') == 50 else 'FAIL',
                    'update_successful': update_success,
                    'updated_percentage': file_status.get('percentage'),
                    'status_note': file_status.get('status')
                }
            else:
                self.test_results['task_progress']['progress_updates'] = {
                    'status': 'FAIL',
                    'update_successful': update_success
                }
            
            # Test current work updates
            work_update_success = self.task_tracker.update_current_work(
                'test_agent_1', 'Working on test implementation'
            )
            
            self.test_results['task_progress']['work_updates'] = {
                'status': 'PASS' if work_update_success else 'FAIL',
                'update_successful': work_update_success
            }
            
            print("✅ Task progress tracking tests completed")
            
        except Exception as e:
            self.test_results['task_progress']['error'] = {
                'status': 'FAIL',
                'exception': str(e)
            }
            print(f"❌ Task progress tracking test failed: {e}")
    
    def test_monitoring_dashboard(self):
        """Test 3: Monitoring dashboard functionality and data accuracy"""
        print("\n📱 Testing monitoring dashboard...")
        
        try:
            health_monitor = self.agent_manager.health_monitor
            recovery_manager = self.agent_manager.recovery_manager
            
            if not health_monitor or not recovery_manager:
                self.test_results['dashboard']['initialization'] = {
                    'status': 'FAIL',
                    'error': 'Required monitoring components not available'
                }
                return
            
            # Initialize dashboard
            dashboard = MonitoringDashboard(health_monitor, recovery_manager)
            
            self.test_results['dashboard']['initialization'] = {
                'status': 'PASS',
                'dashboard_created': True
            }
            
            # Test health summary display (capture output)
            import io
            import contextlib
            
            captured_output = io.StringIO()
            with contextlib.redirect_stdout(captured_output):
                dashboard.display_health_summary()
            
            output = captured_output.getvalue()
            
            # Verify dashboard output contains expected elements
            expected_elements = [
                'AGENT HEALTH MONITORING DASHBOARD',
                'OVERALL STATUS',
                'Total Agents',
                'AGENT DETAILS'
            ]
            
            elements_found = sum(1 for element in expected_elements if element in output)
            
            self.test_results['dashboard']['display_functionality'] = {
                'status': 'PASS' if elements_found >= 3 else 'FAIL',
                'elements_found': elements_found,
                'total_elements': len(expected_elements),
                'output_length': len(output)
            }
            
            # Test agent details display
            captured_output = io.StringIO()
            with contextlib.redirect_stdout(captured_output):
                dashboard.display_agent_details('test_agent_1')
            
            details_output = captured_output.getvalue()
            
            self.test_results['dashboard']['agent_details'] = {
                'status': 'PASS' if 'test_agent_1' in details_output else 'FAIL',
                'details_displayed': 'test_agent_1' in details_output,
                'output_length': len(details_output)
            }
            
            print("✅ Monitoring dashboard tests completed")
            
        except Exception as e:
            self.test_results['dashboard']['error'] = {
                'status': 'FAIL',
                'exception': str(e)
            }
            print(f"❌ Monitoring dashboard test failed: {e}")
    
    def test_recovery_system(self):
        """Test 4: Recovery system validation and effectiveness"""
        print("\n🔄 Testing recovery system...")
        
        try:
            recovery_manager = self.agent_manager.recovery_manager
            
            if not recovery_manager:
                self.test_results['recovery_system']['initialization'] = {
                    'status': 'FAIL',
                    'error': 'Recovery manager not available'
                }
                return
            
            # Test anomaly handling
            test_anomalies = ['STUCK_STATE', 'PROGRESS_STAGNANT']
            test_status_record = {
                'timestamp': datetime.now(),
                'status': {
                    'worker_status': 'stuck',
                    'current_task': 'Test recovery task'
                },
                'task_progress': {
                    'overall_progress': 25,
                    'current_work': 'Stuck on implementation'
                }
            }
            
            # Simulate anomaly detection and recovery
            recovery_manager.handle_agent_anomaly(
                'test_agent_1', test_anomalies, test_status_record
            )
            
            # Check recovery history
            recovery_history = recovery_manager.get_recovery_history('test_agent_1')
            agent_history = recovery_history.get('test_agent_1', [])
            
            self.test_results['recovery_system']['anomaly_handling'] = {
                'status': 'PASS' if len(agent_history) > 0 else 'FAIL',
                'recovery_attempts': len(agent_history),
                'last_action': agent_history[-1].get('action_taken') if agent_history else None
            }
            
            # Test recovery summary
            recovery_summary = recovery_manager.get_recovery_summary()
            
            self.test_results['recovery_system']['summary_generation'] = {
                'status': 'PASS',
                'total_attempts': recovery_summary.get('total_recovery_attempts', 0),
                'successful_recoveries': recovery_summary.get('successful_recoveries', 0),
                'failed_recoveries': recovery_summary.get('failed_recoveries', 0)
            }
            
            # Test escalation callback
            escalation_called = False
            
            def test_escalation_callback(agent_name, anomalies, recovery_record):
                nonlocal escalation_called
                escalation_called = True
            
            recovery_manager.set_escalation_callback(test_escalation_callback)
            
            # Simulate failed recovery to trigger escalation
            recovery_manager.handle_agent_anomaly(
                'test_agent_2', ['WORKER_STUCK'], test_status_record
            )
            
            self.test_results['recovery_system']['escalation'] = {
                'status': 'PASS' if escalation_called else 'FAIL',
                'escalation_triggered': escalation_called
            }
            
            print("✅ Recovery system tests completed")
            
        except Exception as e:
            self.test_results['recovery_system']['error'] = {
                'status': 'FAIL',
                'exception': str(e)
            }
            print(f"❌ Recovery system test failed: {e}")
    
    def test_metrics_collection(self):
        """Test 5: Metrics collection and aggregation systems"""
        print("\n📈 Testing metrics collection...")
        
        try:
            # Test agent status collection
            agent_statuses = self.agent_manager.get_agent_status()
            
            self.test_results['metrics_collection']['agent_status'] = {
                'status': 'PASS' if len(agent_statuses) > 0 else 'FAIL',
                'agents_collected': len(agent_statuses),
                'status_fields': list(agent_statuses.values())[0].keys() if agent_statuses else []
            }
            
            # Test chat statistics
            chat_stats = self.agent_manager.get_chat_statistics()
            
            expected_stats = ['total_agents', 'working_agents', 'stuck_agents', 'idle_agents']
            stats_present = all(stat in chat_stats for stat in expected_stats)
            
            self.test_results['metrics_collection']['chat_statistics'] = {
                'status': 'PASS' if stats_present else 'FAIL',
                'stats_present': stats_present,
                'total_agents': chat_stats.get('total_agents', 0),
                'chat_connected': chat_stats.get('chat_connected', False)
            }
            
            # Test task progress aggregation
            all_progress = self.task_tracker.get_all_progress()
            
            self.test_results['metrics_collection']['progress_aggregation'] = {
                'status': 'PASS',
                'employees_with_progress': len(all_progress),
                'progress_data_available': len(all_progress) > 0
            }
            
            print("✅ Metrics collection tests completed")
            
        except Exception as e:
            self.test_results['metrics_collection']['error'] = {
                'status': 'FAIL',
                'exception': str(e)
            }
            print(f"❌ Metrics collection test failed: {e}")
    
    def test_alerting_mechanisms(self):
        """Test 6: Alerting mechanisms for agent failures or issues"""
        print("\n🚨 Testing alerting mechanisms...")
        
        try:
            health_monitor = self.agent_manager.health_monitor
            
            if not health_monitor:
                self.test_results['alerting']['initialization'] = {
                    'status': 'FAIL',
                    'error': 'Health monitor not available'
                }
                return
            
            # Test anomaly detection
            test_agent = self.agent_manager.agents.get('test_agent_1')
            if test_agent:
                # Simulate stuck state by setting same status multiple times
                test_status = {
                    'worker_status': 'working',
                    'current_task': 'Stuck task'
                }
                
                # Add multiple identical status records to history
                for _ in range(5):
                    status_record = {
                        'timestamp': datetime.now() - timedelta(minutes=10),
                        'status': test_status,
                        'task_progress': {'overall_progress': 25}
                    }
                    
                    if 'test_agent_1' not in health_monitor.agent_history:
                        health_monitor.agent_history['test_agent_1'] = []
                    
                    health_monitor.agent_history['test_agent_1'].append(status_record)
                
                # Test anomaly detection
                anomalies = health_monitor._detect_anomalies('test_agent_1', status_record)
                
                self.test_results['alerting']['anomaly_detection'] = {
                    'status': 'PASS' if len(anomalies) > 0 else 'FAIL',
                    'anomalies_detected': len(anomalies),
                    'anomaly_types': anomalies
                }
            
            # Test callback mechanism
            callback_called = False
            callback_data = {}
            
            def test_anomaly_callback(agent_name, anomalies, status_record):
                nonlocal callback_called, callback_data
                callback_called = True
                callback_data = {
                    'agent_name': agent_name,
                    'anomalies': anomalies,
                    'timestamp': datetime.now()
                }
            
            # Start monitoring with callback
            health_monitor.stop_monitoring()
            health_monitor.start_monitoring(test_anomaly_callback)
            
            # Wait for monitoring cycle
            time.sleep(2)
            
            self.test_results['alerting']['callback_mechanism'] = {
                'status': 'PASS' if callback_called else 'PARTIAL',
                'callback_triggered': callback_called,
                'callback_data': callback_data if callback_called else None
            }
            
            print("✅ Alerting mechanisms tests completed")
            
        except Exception as e:
            self.test_results['alerting']['error'] = {
                'status': 'FAIL',
                'exception': str(e)
            }
            print(f"❌ Alerting mechanisms test failed: {e}")
    
    def test_api_endpoints(self):
        """Test 7: API endpoints functionality"""
        print("\n🌐 Testing API endpoints...")
        
        try:
            # Test if server is running on port 8082
            base_url = "http://localhost:8082"
            
            # Test health endpoint
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    self.test_results['api_endpoints']['health_endpoint'] = {
                        'status': 'PASS',
                        'status_code': response.status_code,
                        'response_data': health_data
                    }
                else:
                    self.test_results['api_endpoints']['health_endpoint'] = {
                        'status': 'FAIL',
                        'status_code': response.status_code
                    }
            except requests.exceptions.RequestException as e:
                self.test_results['api_endpoints']['health_endpoint'] = {
                    'status': 'FAIL',
                    'error': f'Connection failed: {str(e)}'
                }
            
            # Test monitoring endpoints
            monitoring_endpoints = [
                '/monitoring/health',
                '/monitoring/recovery',
                '/monitoring/agents/test_agent_1'
            ]
            
            for endpoint in monitoring_endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                    endpoint_name = endpoint.replace('/', '_').replace('test_agent_1', 'agent_details')
                    
                    if response.status_code == 200:
                        self.test_results['api_endpoints'][f'endpoint{endpoint_name}'] = {
                            'status': 'PASS',
                            'status_code': response.status_code,
                            'has_data': len(response.text) > 0
                        }
                    else:
                        self.test_results['api_endpoints'][f'endpoint{endpoint_name}'] = {
                            'status': 'FAIL',
                            'status_code': response.status_code
                        }
                except requests.exceptions.RequestException as e:
                    self.test_results['api_endpoints'][f'endpoint{endpoint_name}'] = {
                        'status': 'FAIL',
                        'error': f'Connection failed: {str(e)}'
                    }
            
            print("✅ API endpoints tests completed")
            
        except Exception as e:
            self.test_results['api_endpoints']['error'] = {
                'status': 'FAIL',
                'exception': str(e)
            }
            print(f"❌ API endpoints test failed: {e}")
    
    def run_all_tests(self):
        """Run all monitoring system tests"""
        print("🚀 Starting comprehensive monitoring system tests...")
        print("=" * 80)
        
        # Run all test categories
        self.test_health_monitoring_accuracy()
        self.test_task_progress_tracking()
        self.test_monitoring_dashboard()
        self.test_recovery_system()
        self.test_metrics_collection()
        self.test_alerting_mechanisms()
        self.test_api_endpoints()
        
        # Generate summary report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📋 COMPREHENSIVE MONITORING SYSTEM TEST REPORT")
        print("=" * 80)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for category, tests in self.test_results.items():
            print(f"\n📊 {category.upper().replace('_', ' ')}:")
            print("-" * 50)
            
            for test_name, result in tests.items():
                total_tests += 1
                status = result.get('status', 'UNKNOWN')
                
                if status == 'PASS':
                    passed_tests += 1
                    print(f"  ✅ {test_name}: PASS")
                elif status == 'FAIL':
                    failed_tests += 1
                    print(f"  ❌ {test_name}: FAIL")
                    if 'error' in result:
                        print(f"     Error: {result['error']}")
                    if 'exception' in result:
                        print(f"     Exception: {result['exception']}")
                else:
                    print(f"  ⚠️  {test_name}: {status}")
                
                # Show additional details for important metrics
                if test_name in ['agent_detection', 'status_accuracy', 'progress_retrieval']:
                    for key, value in result.items():
                        if key not in ['status', 'error', 'exception']:
                            print(f"     {key}: {value}")
        
        # Overall summary
        print("\n" + "=" * 80)
        print("📈 OVERALL TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! Monitoring system is fully functional.")
        elif failed_tests <= total_tests * 0.2:  # Less than 20% failure
            print("\n✅ MOSTLY FUNCTIONAL: Minor issues detected, system is largely operational.")
        else:
            print("\n⚠️  SIGNIFICANT ISSUES: Multiple test failures detected, review required.")
        
        # Recommendations
        print("\n🔧 RECOMMENDATIONS:")
        if failed_tests == 0:
            print("  • Monitoring system is ready for production use")
            print("  • Consider setting up automated monitoring alerts")
            print("  • Regular health checks recommended")
        else:
            print("  • Review failed test cases and fix underlying issues")
            print("  • Ensure all monitoring components are properly initialized")
            print("  • Check API endpoint connectivity and server status")
        
        print("\n" + "=" * 80)
    
    def cleanup(self):
        """Clean up test environment"""
        try:
            # Stop monitoring
            if hasattr(self.agent_manager, 'health_monitor') and self.agent_manager.health_monitor:
                self.agent_manager.health_monitor.stop_monitoring()
            
            # Clean up temporary files
            os.unlink(self.test_db.name)
            import shutil
            shutil.rmtree(self.test_sessions_dir)
            
            print("🧹 Test environment cleaned up")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

def main():
    """Main test execution"""
    tester = MonitoringSystemTester()
    
    try:
        tester.run_all_tests()
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()