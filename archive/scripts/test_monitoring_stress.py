#!/usr/bin/env python3
"""
Stress test for monitoring system - simulates load and tests performance
"""

import requests
import json
import time
import threading
from datetime import datetime
import sys

class MonitoringStressTester:
    """Stress test monitoring system with load scenarios"""
    
    def __init__(self, base_url="http://localhost:8083"):
        self.base_url = base_url
        self.test_results = {}
        
    def test_monitoring_under_load(self):
        """Test monitoring system under concurrent load"""
        print("🔥 Testing monitoring system under load...")
        
        def make_requests():
            results = []
            for i in range(10):
                try:
                    start_time = time.time()
                    response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
                    end_time = time.time()
                    
                    results.append({
                        'request_id': i,
                        'status_code': response.status_code,
                        'response_time': end_time - start_time,
                        'success': response.status_code == 200
                    })
                    time.sleep(0.1)
                except Exception as e:
                    results.append({
                        'request_id': i,
                        'error': str(e),
                        'success': False
                    })
            return results
        
        # Run concurrent requests
        threads = []
        all_results = []
        
        for t in range(3):
            thread = threading.Thread(target=lambda: all_results.extend(make_requests()))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Analyze results
        successful = sum(1 for r in all_results if r.get('success', False))
        total = len(all_results)
        avg_time = sum(r.get('response_time', 0) for r in all_results if 'response_time' in r)
        avg_time = avg_time / max(1, len([r for r in all_results if 'response_time' in r]))
        
        self.test_results['load_testing'] = {
            'status': 'PASS' if successful >= total * 0.9 else 'FAIL',
            'total_requests': total,
            'successful_requests': successful,
            'success_rate': successful / total * 100,
            'average_response_time': avg_time
        }
        
        print(f"✅ Load test: {successful}/{total} requests successful ({successful/total*100:.1f}%)")
        print(f"   Average response time: {avg_time:.3f}s")
    
    def test_endpoint_performance(self):
        """Test performance of different monitoring endpoints"""
        print("\n⚡ Testing endpoint performance...")
        
        endpoints = [
            '/health',
            '/monitoring/health',
            '/monitoring/recovery'
        ]
        
        for endpoint in endpoints:
            times = []
            successes = 0
            
            for i in range(5):
                try:
                    start_time = time.time()
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                    end_time = time.time()
                    
                    times.append(end_time - start_time)
                    if response.status_code == 200:
                        successes += 1
                except Exception:
                    pass
            
            avg_time = sum(times) / max(1, len(times))
            endpoint_name = endpoint.replace('/', '_')
            
            self.test_results[f'performance{endpoint_name}'] = {
                'status': 'PASS' if successes >= 4 else 'FAIL',
                'endpoint': endpoint,
                'average_time': avg_time,
                'success_rate': successes / 5 * 100
            }
            
            print(f"  {endpoint}: {avg_time:.3f}s avg, {successes}/5 successful")
    
    def test_data_consistency_over_time(self):
        """Test data consistency over multiple requests"""
        print("\n🔄 Testing data consistency over time...")
        
        agent_counts = []
        health_statuses = []
        
        for i in range(5):
            try:
                response = requests.get(f"{self.base_url}/monitoring/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    health = data.get('health', {})
                    
                    agent_counts.append(health.get('total_agents', 0))
                    health_statuses.append(health.get('healthy_agents', 0))
                
                time.sleep(1)
            except Exception:
                pass
        
        # Check consistency
        agent_count_consistent = len(set(agent_counts)) <= 1
        health_status_consistent = len(set(health_statuses)) <= 1
        
        self.test_results['data_consistency'] = {
            'status': 'PASS' if agent_count_consistent and health_status_consistent else 'FAIL',
            'agent_counts': agent_counts,
            'health_statuses': health_statuses,
            'agent_count_consistent': agent_count_consistent,
            'health_status_consistent': health_status_consistent
        }
        
        if agent_count_consistent and health_status_consistent:
            print(f"✅ Data consistency verified over 5 checks")
        else:
            print(f"❌ Data inconsistency detected")
            print(f"   Agent counts: {agent_counts}")
            print(f"   Health statuses: {health_statuses}")
    
    def test_error_handling(self):
        """Test error handling for invalid requests"""
        print("\n🚨 Testing error handling...")
        
        invalid_endpoints = [
            '/monitoring/agents/nonexistent_agent',
            '/monitoring/invalid_endpoint',
            '/monitoring/health/extra_path'
        ]
        
        error_handling_results = []
        
        for endpoint in invalid_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                error_handling_results.append({
                    'endpoint': endpoint,
                    'status_code': response.status_code,
                    'handles_error': response.status_code in [400, 404, 500]
                })
            except Exception as e:
                error_handling_results.append({
                    'endpoint': endpoint,
                    'error': str(e),
                    'handles_error': False
                })
        
        proper_error_handling = sum(1 for r in error_handling_results if r.get('handles_error', False))
        
        self.test_results['error_handling'] = {
            'status': 'PASS' if proper_error_handling >= len(invalid_endpoints) * 0.7 else 'FAIL',
            'total_tests': len(invalid_endpoints),
            'proper_handling': proper_error_handling,
            'results': error_handling_results
        }
        
        print(f"✅ Error handling: {proper_error_handling}/{len(invalid_endpoints)} endpoints handled properly")
    
    def run_all_tests(self):
        """Run all stress tests"""
        print("🚀 Starting monitoring system stress tests...")
        print("=" * 60)
        
        # Check server connectivity first
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                print("❌ Server not accessible - cannot run stress tests")
                return
        except Exception as e:
            print(f"❌ Server connection failed: {e}")
            return
        
        # Run stress tests
        self.test_monitoring_under_load()
        self.test_endpoint_performance()
        self.test_data_consistency_over_time()
        self.test_error_handling()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate stress test report"""
        print("\n" + "=" * 60)
        print("📋 MONITORING SYSTEM STRESS TEST REPORT")
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
        
        # Performance metrics
        if 'load_testing' in self.test_results:
            load_data = self.test_results['load_testing']
            print(f"\n⚡ PERFORMANCE METRICS:")
            print(f"  Load Test Success Rate: {load_data.get('success_rate', 0):.1f}%")
            print(f"  Average Response Time: {load_data.get('average_response_time', 0):.3f}s")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        if failed_tests == 0:
            print("  ✅ Monitoring system handles stress well")
            print("  ✅ Performance is acceptable under load")
            print("  ✅ Error handling is working properly")
        else:
            print("  ⚠️  Some stress test failures detected")
            if 'load_testing' in self.test_results and self.test_results['load_testing'].get('status') == 'FAIL':
                print("  🔧 Consider optimizing monitoring system for higher load")
            if any('performance' in name and result.get('status') == 'FAIL' for name, result in self.test_results.items()):
                print("  🔧 Review endpoint performance and consider caching")
            if 'data_consistency' in self.test_results and self.test_results['data_consistency'].get('status') == 'FAIL':
                print("  🔧 Investigate data consistency issues")
        
        print("\n" + "=" * 60)

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stress test monitoring system')
    parser.add_argument('--url', default='http://localhost:8083', 
                       help='Base URL of the server (default: http://localhost:8083)')
    
    args = parser.parse_args()
    
    tester = MonitoringStressTester(args.url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()