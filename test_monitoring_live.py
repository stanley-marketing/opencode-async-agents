#!/usr/bin/env python3
"""
Live monitoring system test - tests against running server
"""

import requests
import json
import time
import sys
from datetime import datetime

class LiveMonitoringTester:
    """Test monitoring system against live server"""
    
    def __init__(self, base_url="http://localhost:8082"):
        self.base_url = base_url
        self.test_results = {}
        
    def test_server_connectivity(self):
        """Test basic server connectivity"""
        print("🔗 Testing server connectivity...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.test_results['connectivity'] = {
                    'status': 'PASS',
                    'server_healthy': data.get('status') == 'healthy',
                    'total_agents': data.get('total_agents', 0),
                    'chat_enabled': data.get('chat_enabled', False)
                }
                print(f"✅ Server is healthy with {data.get('total_agents', 0)} agents")
                return True
            else:
                self.test_results['connectivity'] = {
                    'status': 'FAIL',
                    'status_code': response.status_code
                }
                print(f"❌ Server returned status code: {response.status_code}")
                return False
        except Exception as e:
            self.test_results['connectivity'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ Connection failed: {e}")
            return False
    
    def test_monitoring_health_endpoint(self):
        """Test monitoring health endpoint"""
        print("\n🔍 Testing monitoring health endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                health = data.get('health', {})
                
                # Validate health data structure
                required_fields = ['total_agents', 'healthy_agents', 'stuck_agents', 'agent_details']
                missing_fields = [field for field in required_fields if field not in health]
                
                if not missing_fields:
                    self.test_results['health_endpoint'] = {
                        'status': 'PASS',
                        'total_agents': health.get('total_agents', 0),
                        'healthy_agents': health.get('healthy_agents', 0),
                        'stuck_agents': health.get('stuck_agents', 0),
                        'agent_count': len(health.get('agent_details', {}))
                    }
                    print(f"✅ Health endpoint working - {health.get('total_agents', 0)} agents monitored")
                    
                    # Test individual agent details
                    agent_details = health.get('agent_details', {})
                    if agent_details:
                        sample_agent = list(agent_details.keys())[0]
                        agent_info = agent_details[sample_agent]
                        
                        required_agent_fields = ['worker_status', 'health_status', 'overall_progress']
                        agent_fields_present = all(field in agent_info for field in required_agent_fields)
                        
                        self.test_results['agent_details_structure'] = {
                            'status': 'PASS' if agent_fields_present else 'FAIL',
                            'sample_agent': sample_agent,
                            'fields_present': agent_fields_present,
                            'agent_status': agent_info.get('worker_status'),
                            'health_status': agent_info.get('health_status')
                        }
                        
                        if agent_fields_present:
                            print(f"✅ Agent details structure valid for {sample_agent}")
                        else:
                            print(f"❌ Agent details missing required fields for {sample_agent}")
                    
                else:
                    self.test_results['health_endpoint'] = {
                        'status': 'FAIL',
                        'missing_fields': missing_fields
                    }
                    print(f"❌ Health endpoint missing fields: {missing_fields}")
            else:
                self.test_results['health_endpoint'] = {
                    'status': 'FAIL',
                    'status_code': response.status_code
                }
                print(f"❌ Health endpoint returned status: {response.status_code}")
                
        except Exception as e:
            self.test_results['health_endpoint'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ Health endpoint test failed: {e}")
    
    def test_monitoring_recovery_endpoint(self):
        """Test monitoring recovery endpoint"""
        print("\n🔄 Testing monitoring recovery endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/monitoring/recovery", timeout=5)
            if response.status_code == 200:
                data = response.json()
                recovery = data.get('recovery', {})
                
                # Validate recovery data structure
                required_fields = ['total_recovery_attempts', 'successful_recoveries', 'failed_recoveries']
                missing_fields = [field for field in required_fields if field not in recovery]
                
                if not missing_fields:
                    self.test_results['recovery_endpoint'] = {
                        'status': 'PASS',
                        'total_attempts': recovery.get('total_recovery_attempts', 0),
                        'successful': recovery.get('successful_recoveries', 0),
                        'failed': recovery.get('failed_recoveries', 0),
                        'escalations': recovery.get('escalations', 0)
                    }
                    print(f"✅ Recovery endpoint working - {recovery.get('total_recovery_attempts', 0)} total attempts")
                else:
                    self.test_results['recovery_endpoint'] = {
                        'status': 'FAIL',
                        'missing_fields': missing_fields
                    }
                    print(f"❌ Recovery endpoint missing fields: {missing_fields}")
            else:
                self.test_results['recovery_endpoint'] = {
                    'status': 'FAIL',
                    'status_code': response.status_code
                }
                print(f"❌ Recovery endpoint returned status: {response.status_code}")
                
        except Exception as e:
            self.test_results['recovery_endpoint'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ Recovery endpoint test failed: {e}")
    
    def test_agent_specific_monitoring(self):
        """Test agent-specific monitoring endpoint"""
        print("\n👤 Testing agent-specific monitoring...")
        
        # First get list of agents
        try:
            health_response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                agents = list(health_data.get('health', {}).get('agent_details', {}).keys())
                
                if agents:
                    test_agent = agents[0]  # Test first available agent
                    
                    response = requests.get(f"{self.base_url}/monitoring/agents/{test_agent}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Validate agent-specific data
                        required_fields = ['agent', 'health', 'recovery_history']
                        missing_fields = [field for field in required_fields if field not in data]
                        
                        if not missing_fields:
                            self.test_results['agent_specific_monitoring'] = {
                                'status': 'PASS',
                                'test_agent': test_agent,
                                'agent_name_match': data.get('agent') == test_agent,
                                'has_health_data': bool(data.get('health')),
                                'has_recovery_history': isinstance(data.get('recovery_history'), list)
                            }
                            print(f"✅ Agent-specific monitoring working for {test_agent}")
                        else:
                            self.test_results['agent_specific_monitoring'] = {
                                'status': 'FAIL',
                                'missing_fields': missing_fields
                            }
                            print(f"❌ Agent monitoring missing fields: {missing_fields}")
                    else:
                        self.test_results['agent_specific_monitoring'] = {
                            'status': 'FAIL',
                            'status_code': response.status_code
                        }
                        print(f"❌ Agent monitoring returned status: {response.status_code}")
                else:
                    self.test_results['agent_specific_monitoring'] = {
                        'status': 'FAIL',
                        'error': 'No agents available for testing'
                    }
                    print("❌ No agents available for testing")
            else:
                self.test_results['agent_specific_monitoring'] = {
                    'status': 'FAIL',
                    'error': 'Could not get agent list'
                }
                print("❌ Could not get agent list for testing")
                
        except Exception as e:
            self.test_results['agent_specific_monitoring'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ Agent-specific monitoring test failed: {e}")
    
    def test_real_time_monitoring(self):
        """Test real-time monitoring updates"""
        print("\n⏱️  Testing real-time monitoring updates...")
        
        try:
            # Get initial state
            initial_response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
            if initial_response.status_code != 200:
                self.test_results['real_time_monitoring'] = {
                    'status': 'FAIL',
                    'error': 'Could not get initial state'
                }
                return
            
            initial_data = initial_response.json()
            initial_timestamp = datetime.now()
            
            # Wait a moment
            time.sleep(2)
            
            # Get updated state
            updated_response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
            if updated_response.status_code == 200:
                updated_data = updated_response.json()
                updated_timestamp = datetime.now()
                
                # Check if monitoring is actively updating
                time_diff = (updated_timestamp - initial_timestamp).total_seconds()
                
                self.test_results['real_time_monitoring'] = {
                    'status': 'PASS',
                    'time_difference': time_diff,
                    'data_consistent': initial_data == updated_data,
                    'monitoring_active': time_diff > 0
                }
                print(f"✅ Real-time monitoring active - {time_diff:.1f}s between checks")
            else:
                self.test_results['real_time_monitoring'] = {
                    'status': 'FAIL',
                    'error': 'Could not get updated state'
                }
                print("❌ Could not get updated monitoring state")
                
        except Exception as e:
            self.test_results['real_time_monitoring'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ Real-time monitoring test failed: {e}")
    
    def test_data_accuracy(self):
        """Test monitoring data accuracy"""
        print("\n📊 Testing monitoring data accuracy...")
        
        try:
            # Get data from multiple endpoints
            health_response = requests.get(f"{self.base_url}/health", timeout=5)
            monitoring_response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
            
            if health_response.status_code == 200 and monitoring_response.status_code == 200:
                health_data = health_response.json()
                monitoring_data = monitoring_response.json()
                
                # Compare agent counts
                basic_agent_count = health_data.get('total_agents', 0)
                monitoring_agent_count = monitoring_data.get('health', {}).get('total_agents', 0)
                
                # Check consistency
                counts_match = basic_agent_count == monitoring_agent_count
                
                # Validate health status logic
                health_summary = monitoring_data.get('health', {})
                total_calculated = (
                    health_summary.get('healthy_agents', 0) +
                    health_summary.get('stuck_agents', 0) +
                    health_summary.get('stagnant_agents', 0) +
                    health_summary.get('error_agents', 0)
                )
                
                totals_match = total_calculated == health_summary.get('total_agents', 0)
                
                self.test_results['data_accuracy'] = {
                    'status': 'PASS' if counts_match and totals_match else 'FAIL',
                    'agent_counts_match': counts_match,
                    'basic_count': basic_agent_count,
                    'monitoring_count': monitoring_agent_count,
                    'health_totals_match': totals_match,
                    'calculated_total': total_calculated,
                    'reported_total': health_summary.get('total_agents', 0)
                }
                
                if counts_match and totals_match:
                    print(f"✅ Data accuracy verified - {basic_agent_count} agents consistent")
                else:
                    print(f"❌ Data inconsistency detected")
                    if not counts_match:
                        print(f"   Agent count mismatch: {basic_agent_count} vs {monitoring_agent_count}")
                    if not totals_match:
                        print(f"   Health totals mismatch: {total_calculated} vs {health_summary.get('total_agents', 0)}")
            else:
                self.test_results['data_accuracy'] = {
                    'status': 'FAIL',
                    'error': 'Could not get data from endpoints'
                }
                print("❌ Could not get data for accuracy testing")
                
        except Exception as e:
            self.test_results['data_accuracy'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"❌ Data accuracy test failed: {e}")
    
    def run_all_tests(self):
        """Run all live monitoring tests"""
        print("🚀 Starting live monitoring system tests...")
        print("=" * 60)
        
        # Test server connectivity first
        if not self.test_server_connectivity():
            print("\n❌ Server not accessible - cannot run monitoring tests")
            return
        
        # Run monitoring-specific tests
        self.test_monitoring_health_endpoint()
        self.test_monitoring_recovery_endpoint()
        self.test_agent_specific_monitoring()
        self.test_real_time_monitoring()
        self.test_data_accuracy()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("📋 LIVE MONITORING SYSTEM TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'PASS')
        failed_tests = total_tests - passed_tests
        
        print(f"\n📈 SUMMARY:")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        
        print(f"\n📊 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            if status == 'PASS':
                print(f"  ✅ {test_name}: PASS")
            else:
                print(f"  ❌ {test_name}: FAIL")
                if 'error' in result:
                    print(f"     Error: {result['error']}")
        
        # Key metrics
        if 'connectivity' in self.test_results and self.test_results['connectivity'].get('status') == 'PASS':
            conn_data = self.test_results['connectivity']
            print(f"\n🔍 KEY METRICS:")
            print(f"  Server Status: {'Healthy' if conn_data.get('server_healthy') else 'Unhealthy'}")
            print(f"  Total Agents: {conn_data.get('total_agents', 0)}")
            print(f"  Chat Enabled: {'Yes' if conn_data.get('chat_enabled') else 'No'}")
        
        if 'health_endpoint' in self.test_results and self.test_results['health_endpoint'].get('status') == 'PASS':
            health_data = self.test_results['health_endpoint']
            print(f"  Healthy Agents: {health_data.get('healthy_agents', 0)}")
            print(f"  Stuck Agents: {health_data.get('stuck_agents', 0)}")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        if failed_tests == 0:
            print("  ✅ All monitoring systems are functioning correctly")
            print("  ✅ Real-time monitoring is active and accurate")
            print("  ✅ API endpoints are responsive and returning valid data")
        else:
            print("  ⚠️  Some monitoring components need attention")
            if 'connectivity' in self.test_results and self.test_results['connectivity'].get('status') == 'FAIL':
                print("  🔧 Check server connectivity and ensure it's running")
            if any('endpoint' in name and result.get('status') == 'FAIL' for name, result in self.test_results.items()):
                print("  🔧 Review monitoring endpoint implementations")
            if 'data_accuracy' in self.test_results and self.test_results['data_accuracy'].get('status') == 'FAIL':
                print("  🔧 Investigate data consistency issues between endpoints")
        
        print("\n" + "=" * 60)

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test live monitoring system')
    parser.add_argument('--url', default='http://localhost:8082', 
                       help='Base URL of the server (default: http://localhost:8082)')
    
    args = parser.parse_args()
    
    tester = LiveMonitoringTester(args.url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()