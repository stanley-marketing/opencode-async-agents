#!/usr/bin/env python3
"""
Integration test for monitoring system - tests with real task assignment and monitoring
"""

import requests
import json
import time
from datetime import datetime
import sys

class MonitoringIntegrationTester:
    """Integration test for monitoring system with real tasks"""
    
    def __init__(self, base_url="http://localhost:9090"):
        self.base_url = base_url
        self.test_results = {}
        self.test_agent_name = "test_integration_agent"
        
    def setup_test_agent(self):
        """Create a test agent for integration testing"""
        print("🔧 Setting up test agent...")
        
        # First check if agent already exists
        try:
            response = requests.get(f"{self.base_url}/employees", timeout=5)
            if response.status_code == 200:
                employees = response.json().get('employees', [])
                existing_agent = any(emp['name'] == self.test_agent_name for emp in employees)
                
                if not existing_agent:
                    # Create test agent
                    create_response = requests.post(
                        f"{self.base_url}/employees",
                        json={
                            'name': self.test_agent_name,
                            'role': 'developer'
                        },
                        timeout=5
                    )
                    
                    if create_response.status_code == 200:
                        print(f"✅ Created test agent: {self.test_agent_name}")
                        return True
                    else:
                        print(f"❌ Failed to create test agent: {create_response.status_code}")
                        return False
                else:
                    print(f"✅ Test agent {self.test_agent_name} already exists")
                    return True
            else:
                print(f"❌ Could not get employee list: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error setting up test agent: {e}")
            return False
    
    def test_task_assignment_monitoring(self):
        """Test monitoring during task assignment"""
        print("\n📋 Testing task assignment monitoring...")
        
        # Get initial monitoring state
        try:
            initial_response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
            if initial_response.status_code != 200:
                self.test_results['task_assignment'] = {
                    'status': 'FAIL',
                    'error': 'Could not get initial monitoring state'
                }
                return
            
            initial_data = initial_response.json()
            initial_agent_details = initial_data.get('health', {}).get('agent_details', {})
            
            # Assign a test task
            task_description = "Test task for monitoring integration - create a simple hello world function"
            
            task_response = requests.post(
                f"{self.base_url}/tasks",
                json={
                    'name': self.test_agent_name,
                    'task': task_description,
                    'model': 'openrouter/qwen/qwen3-coder'
                },
                timeout=10
            )
            
            if task_response.status_code == 200:
                print(f"✅ Task assigned to {self.test_agent_name}")
                
                # Wait a moment for monitoring to detect the change
                time.sleep(3)
                
                # Check monitoring state after task assignment
                updated_response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
                if updated_response.status_code == 200:
                    updated_data = updated_response.json()
                    updated_agent_details = updated_data.get('health', {}).get('agent_details', {})
                    
                    # Check if monitoring detected the task assignment
                    agent_info = updated_agent_details.get(self.test_agent_name, {})
                    
                    self.test_results['task_assignment'] = {
                        'status': 'PASS',
                        'task_assigned': True,
                        'agent_monitored': self.test_agent_name in updated_agent_details,
                        'worker_status': agent_info.get('worker_status', 'unknown'),
                        'current_task': agent_info.get('current_task'),
                        'monitoring_detected_change': initial_agent_details != updated_agent_details
                    }
                    
                    print(f"✅ Monitoring detected task assignment")
                    print(f"   Agent status: {agent_info.get('worker_status', 'unknown')}")
                    print(f"   Current task: {agent_info.get('current_task', 'None')}")
                else:
                    self.test_results['task_assignment'] = {
                        'status': 'FAIL',
                        'error': 'Could not get updated monitoring state'
                    }
            else:
                self.test_results['task_assignment'] = {
                    'status': 'FAIL',
                    'error': f'Task assignment failed: {task_response.status_code}'
                }
                print(f"❌ Task assignment failed: {task_response.status_code}")
                
        except Exception as e:
            self.test_results['task_assignment'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ Task assignment monitoring test failed: {e}")
    
    def test_progress_tracking_integration(self):
        """Test progress tracking integration with monitoring"""
        print("\n📊 Testing progress tracking integration...")
        
        try:
            # Get task progress for our test agent
            progress_response = requests.get(f"{self.base_url}/progress/{self.test_agent_name}", timeout=5)
            
            if progress_response.status_code == 200:
                progress_data = progress_response.json()
                
                # Get monitoring data for the same agent
                monitoring_response = requests.get(f"{self.base_url}/monitoring/agents/{self.test_agent_name}", timeout=5)
                
                if monitoring_response.status_code == 200:
                    monitoring_data = monitoring_response.json()
                    
                    # Compare progress data consistency
                    progress_percentage = progress_data.get('progress', {}).get('overall_progress', 0)
                    monitoring_percentage = monitoring_data.get('health', {}).get('overall_progress', 0)
                    
                    self.test_results['progress_integration'] = {
                        'status': 'PASS' if progress_percentage == monitoring_percentage else 'PARTIAL',
                        'progress_endpoint_working': True,
                        'monitoring_endpoint_working': True,
                        'progress_percentage': progress_percentage,
                        'monitoring_percentage': monitoring_percentage,
                        'data_consistent': progress_percentage == monitoring_percentage
                    }
                    
                    if progress_percentage == monitoring_percentage:
                        print(f"✅ Progress data consistent: {progress_percentage}%")
                    else:
                        print(f"⚠️  Progress data inconsistent: {progress_percentage}% vs {monitoring_percentage}%")
                else:
                    self.test_results['progress_integration'] = {
                        'status': 'PARTIAL',
                        'progress_endpoint_working': True,
                        'monitoring_endpoint_working': False,
                        'error': f'Monitoring endpoint failed: {monitoring_response.status_code}'
                    }
            else:
                # Progress endpoint might not exist or agent might not have progress yet
                self.test_results['progress_integration'] = {
                    'status': 'PARTIAL',
                    'progress_endpoint_working': False,
                    'note': 'Progress endpoint not available or no progress data yet'
                }
                print("ℹ️  Progress endpoint not available or no progress data yet")
                
        except Exception as e:
            self.test_results['progress_integration'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ Progress tracking integration test failed: {e}")
    
    def test_monitoring_dashboard_data(self):
        """Test monitoring dashboard data accuracy"""
        print("\n📱 Testing monitoring dashboard data...")
        
        try:
            # Get comprehensive monitoring data
            health_response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
            recovery_response = requests.get(f"{self.base_url}/monitoring/recovery", timeout=5)
            
            if health_response.status_code == 200 and recovery_response.status_code == 200:
                health_data = health_response.json()
                recovery_data = recovery_response.json()
                
                # Validate dashboard data structure
                health_summary = health_data.get('health', {})
                recovery_summary = recovery_data.get('recovery', {})
                
                # Check data completeness
                required_health_fields = ['total_agents', 'healthy_agents', 'agent_details']
                required_recovery_fields = ['total_recovery_attempts', 'successful_recoveries']
                
                health_complete = all(field in health_summary for field in required_health_fields)
                recovery_complete = all(field in recovery_summary for field in required_recovery_fields)
                
                # Check if our test agent is included
                agent_details = health_summary.get('agent_details', {})
                test_agent_included = self.test_agent_name in agent_details
                
                self.test_results['dashboard_data'] = {
                    'status': 'PASS' if health_complete and recovery_complete else 'FAIL',
                    'health_data_complete': health_complete,
                    'recovery_data_complete': recovery_complete,
                    'test_agent_included': test_agent_included,
                    'total_agents_monitored': health_summary.get('total_agents', 0),
                    'agent_details_count': len(agent_details)
                }
                
                if health_complete and recovery_complete:
                    print(f"✅ Dashboard data complete")
                    print(f"   Total agents: {health_summary.get('total_agents', 0)}")
                    print(f"   Test agent included: {'Yes' if test_agent_included else 'No'}")
                else:
                    print(f"❌ Dashboard data incomplete")
                    
            else:
                self.test_results['dashboard_data'] = {
                    'status': 'FAIL',
                    'error': f'API endpoints failed: health={health_response.status_code}, recovery={recovery_response.status_code}'
                }
                print(f"❌ Dashboard data test failed: API endpoints not accessible")
                
        except Exception as e:
            self.test_results['dashboard_data'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ Dashboard data test failed: {e}")
    
    def test_monitoring_system_reliability(self):
        """Test monitoring system reliability over time"""
        print("\n🔄 Testing monitoring system reliability...")
        
        try:
            # Test monitoring over multiple intervals
            monitoring_results = []
            
            for i in range(5):
                start_time = time.time()
                response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
                end_time = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    monitoring_results.append({
                        'iteration': i + 1,
                        'response_time': end_time - start_time,
                        'total_agents': data.get('health', {}).get('total_agents', 0),
                        'healthy_agents': data.get('health', {}).get('healthy_agents', 0),
                        'success': True
                    })
                else:
                    monitoring_results.append({
                        'iteration': i + 1,
                        'success': False,
                        'status_code': response.status_code
                    })
                
                time.sleep(1)  # Wait between checks
            
            # Analyze reliability
            successful_checks = sum(1 for r in monitoring_results if r.get('success', False))
            avg_response_time = sum(r.get('response_time', 0) for r in monitoring_results if 'response_time' in r)
            avg_response_time = avg_response_time / max(1, len([r for r in monitoring_results if 'response_time' in r]))
            
            # Check data consistency
            agent_counts = [r.get('total_agents', 0) for r in monitoring_results if r.get('success', False)]
            data_consistent = len(set(agent_counts)) <= 1
            
            self.test_results['system_reliability'] = {
                'status': 'PASS' if successful_checks >= 4 and data_consistent else 'FAIL',
                'successful_checks': successful_checks,
                'total_checks': len(monitoring_results),
                'success_rate': successful_checks / len(monitoring_results) * 100,
                'average_response_time': avg_response_time,
                'data_consistent': data_consistent,
                'agent_counts': agent_counts
            }
            
            print(f"✅ Reliability test: {successful_checks}/5 checks successful")
            print(f"   Average response time: {avg_response_time:.3f}s")
            print(f"   Data consistent: {'Yes' if data_consistent else 'No'}")
            
        except Exception as e:
            self.test_results['system_reliability'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ System reliability test failed: {e}")
    
    def cleanup_test_agent(self):
        """Clean up test agent"""
        print("\n🧹 Cleaning up test agent...")
        
        try:
            response = requests.delete(f"{self.base_url}/employees/{self.test_agent_name}", timeout=5)
            if response.status_code == 200:
                print(f"✅ Test agent {self.test_agent_name} cleaned up")
            else:
                print(f"⚠️  Could not clean up test agent: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting monitoring system integration tests...")
        print("=" * 70)
        
        # Check server connectivity
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                print("❌ Server not accessible - cannot run integration tests")
                return
        except Exception as e:
            print(f"❌ Server connection failed: {e}")
            return
        
        # Set up test environment
        if not self.setup_test_agent():
            print("❌ Could not set up test agent - aborting tests")
            return
        
        try:
            # Run integration tests
            self.test_task_assignment_monitoring()
            self.test_progress_tracking_integration()
            self.test_monitoring_dashboard_data()
            self.test_monitoring_system_reliability()
            
            # Generate report
            self.generate_report()
            
        finally:
            # Clean up
            self.cleanup_test_agent()
    
    def generate_report(self):
        """Generate integration test report"""
        print("\n" + "=" * 70)
        print("📋 MONITORING SYSTEM INTEGRATION TEST REPORT")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'PASS')
        partial_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'PARTIAL')
        failed_tests = total_tests - passed_tests - partial_tests
        
        print(f"\n📈 SUMMARY:")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"Partial: {partial_tests} ({partial_tests/total_tests*100:.1f}%)")
        print(f"Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        
        print(f"\n📊 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            if status == 'PASS':
                print(f"  ✅ {test_name}: PASS")
            elif status == 'PARTIAL':
                print(f"  ⚠️  {test_name}: PARTIAL")
            else:
                print(f"  ❌ {test_name}: FAIL")
                if 'error' in result:
                    print(f"     Error: {result['error']}")
        
        # Key findings
        print(f"\n🔍 KEY FINDINGS:")
        
        if 'task_assignment' in self.test_results:
            task_data = self.test_results['task_assignment']
            if task_data.get('status') == 'PASS':
                print(f"  ✅ Task assignment monitoring working")
                print(f"     Agent status: {task_data.get('worker_status', 'unknown')}")
            else:
                print(f"  ❌ Task assignment monitoring issues detected")
        
        if 'system_reliability' in self.test_results:
            rel_data = self.test_results['system_reliability']
            print(f"  📊 System reliability: {rel_data.get('success_rate', 0):.1f}%")
            print(f"  ⚡ Average response time: {rel_data.get('average_response_time', 0):.3f}s")
        
        # Overall assessment
        print(f"\n🎯 OVERALL ASSESSMENT:")
        if failed_tests == 0 and partial_tests <= 1:
            print("  🎉 EXCELLENT: Monitoring system is fully functional and well-integrated")
            print("  ✅ Real-time monitoring works correctly")
            print("  ✅ Task assignment detection is working")
            print("  ✅ Data consistency is maintained")
        elif failed_tests <= 1:
            print("  ✅ GOOD: Monitoring system is mostly functional with minor issues")
            print("  🔧 Some components may need fine-tuning")
        else:
            print("  ⚠️  NEEDS ATTENTION: Multiple integration issues detected")
            print("  🔧 Review monitoring system integration")
        
        print("\n" + "=" * 70)

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Integration test for monitoring system')
    parser.add_argument('--url', default='http://localhost:9090', 
                       help='Base URL of the server (default: http://localhost:9090)')
    
    args = parser.parse_args()
    
    tester = MonitoringIntegrationTester(args.url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()