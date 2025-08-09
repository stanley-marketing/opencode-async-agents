#!/usr/bin/env python3
"""
Comprehensive API endpoint testing for OpenCode-Slack system
Tests all endpoints to verify 500 error fixes
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Any

class APITester:
    """Comprehensive API endpoint tester"""
    
    def __init__(self, base_url: str = "http://localhost:8093"):
        self.base_url = base_url
        self.results = []
        self.session = requests.Session()
        self.session.timeout = 10
    
    def wait_for_server(self, max_wait: int = 120) -> bool:
        """Wait for server to be ready"""
        print(f"🔍 Waiting for server at {self.base_url} to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = self.session.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print(f"✅ Server is ready! ({time.time() - start_time:.1f}s)")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            print(".", end="", flush=True)
            time.sleep(2)
        
        print(f"\n❌ Server not ready after {max_wait}s")
        return False
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict = None, 
                     expected_status: int = 200, description: str = "") -> Dict:
        """Test a single endpoint"""
        
        url = f"{self.base_url}{endpoint}"
        test_name = f"{method} {endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Check if response is JSON
            try:
                response_data = response.json()
                json_valid = True
            except json.JSONDecodeError:
                response_data = response.text
                json_valid = False
            
            success = response.status_code == expected_status
            
            result = {
                'test_name': test_name,
                'description': description,
                'method': method,
                'endpoint': endpoint,
                'status_code': response.status_code,
                'expected_status': expected_status,
                'success': success,
                'json_valid': json_valid,
                'response_size': len(response.text),
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'error': None,
                'response_preview': str(response_data)[:200] if json_valid else response.text[:200]
            }
            
            if not success:
                result['error'] = f"Expected {expected_status}, got {response.status_code}"
            
            self.results.append(result)
            return result
            
        except Exception as e:
            result = {
                'test_name': test_name,
                'description': description,
                'method': method,
                'endpoint': endpoint,
                'status_code': 'ERROR',
                'expected_status': expected_status,
                'success': False,
                'json_valid': False,
                'response_size': 0,
                'response_time_ms': 0,
                'error': str(e),
                'response_preview': str(e)
            }
            
            self.results.append(result)
            return result
    
    def run_comprehensive_tests(self) -> Dict:
        """Run all API endpoint tests"""
        
        print("🧪 Running comprehensive API endpoint tests...")
        print("=" * 60)
        
        # Core system endpoints
        print("\n📋 Testing Core System Endpoints...")
        self.test_endpoint("GET", "/health", description="System health check")
        self.test_endpoint("GET", "/status", description="System status")
        self.test_endpoint("GET", "/employees", description="List employees")
        self.test_endpoint("GET", "/sessions", description="Active sessions")
        self.test_endpoint("GET", "/files", description="Locked files")
        self.test_endpoint("GET", "/progress", description="Task progress")
        self.test_endpoint("GET", "/agents", description="Agent status")
        self.test_endpoint("GET", "/bridge", description="Bridge status")
        self.test_endpoint("GET", "/project-root", description="Project root")
        
        # Employee management endpoints
        print("\n👥 Testing Employee Management Endpoints...")
        unique_name = f"test_fixed_user_{int(time.time())}"
        self.test_endpoint("POST", "/employees", 
                          data={"name": unique_name, "role": "developer", "smartness": "normal"},
                          expected_status=201, description="Create employee")
        
        self.test_endpoint("DELETE", f"/employees/{unique_name}", 
                          expected_status=200, description="Delete employee")
        
        # Chat system endpoints
        print("\n💬 Testing Chat System Endpoints...")
        self.test_endpoint("GET", "/chat/status", description="Chat status")
        self.test_endpoint("GET", "/chat/debug", description="Chat debug info")
        
        # Monitoring endpoints (previously failing)
        print("\n🔍 Testing Monitoring Endpoints (Previously Failing)...")
        self.test_endpoint("GET", "/monitoring/health", description="Monitoring health")
        self.test_endpoint("GET", "/monitoring/recovery", description="Monitoring recovery")
        
        # Production monitoring endpoints (previously failing)
        print("\n🏭 Testing Production Monitoring Endpoints (Previously Failing)...")
        self.test_endpoint("GET", "/monitoring/production/status", description="Production status")
        self.test_endpoint("GET", "/monitoring/production/performance", description="Production performance")
        self.test_endpoint("GET", "/monitoring/production/alerts", description="Production alerts")
        
        # Error handling tests
        print("\n⚠️  Testing Error Handling...")
        self.test_endpoint("GET", "/nonexistent", expected_status=404, description="Non-existent endpoint")
        self.test_endpoint("POST", "/employees", 
                          data={"name": "", "role": ""},
                          expected_status=400, description="Invalid employee data")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        # Categorize results
        core_tests = [r for r in self.results if any(ep in r['endpoint'] for ep in ['/health', '/status', '/employees', '/sessions', '/files', '/progress', '/agents', '/bridge', '/project-root'])]
        monitoring_tests = [r for r in self.results if '/monitoring/' in r['endpoint']]
        error_tests = [r for r in self.results if r['expected_status'] >= 400]
        
        # Calculate success rates
        core_success = sum(1 for r in core_tests if r['success']) / len(core_tests) * 100 if core_tests else 0
        monitoring_success = sum(1 for r in monitoring_tests if r['success']) / len(monitoring_tests) * 100 if monitoring_tests else 0
        
        # Identify fixed issues
        previously_failing = [
            '/monitoring/health',
            '/monitoring/recovery', 
            '/monitoring/production/status',
            '/monitoring/production/alerts'
        ]
        
        fixed_endpoints = []
        still_failing = []
        
        for endpoint in previously_failing:
            result = next((r for r in self.results if r['endpoint'] == endpoint), None)
            if result:
                if result['success']:
                    fixed_endpoints.append(endpoint)
                else:
                    still_failing.append(endpoint)
        
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'test_timestamp': datetime.now().isoformat()
            },
            'category_results': {
                'core_endpoints': {
                    'total': len(core_tests),
                    'passed': sum(1 for r in core_tests if r['success']),
                    'success_rate': core_success
                },
                'monitoring_endpoints': {
                    'total': len(monitoring_tests),
                    'passed': sum(1 for r in monitoring_tests if r['success']),
                    'success_rate': monitoring_success
                },
                'error_handling': {
                    'total': len(error_tests),
                    'passed': sum(1 for r in error_tests if r['success']),
                    'success_rate': sum(1 for r in error_tests if r['success']) / len(error_tests) * 100 if error_tests else 0
                }
            },
            'fix_validation': {
                'previously_failing_endpoints': previously_failing,
                'fixed_endpoints': fixed_endpoints,
                'still_failing_endpoints': still_failing,
                'fix_success_rate': (len(fixed_endpoints) / len(previously_failing) * 100) if previously_failing else 0
            },
            'performance_metrics': {
                'avg_response_time_ms': sum(r['response_time_ms'] for r in self.results if isinstance(r['response_time_ms'], (int, float))) / total_tests if total_tests > 0 else 0,
                'max_response_time_ms': max((r['response_time_ms'] for r in self.results if isinstance(r['response_time_ms'], (int, float))), default=0),
                'json_valid_responses': sum(1 for r in self.results if r['json_valid'])
            },
            'detailed_results': self.results
        }
        
        return report
    
    def print_report(self, report: Dict):
        """Print formatted test report"""
        
        print("\n" + "=" * 80)
        print("🧪 COMPREHENSIVE API ENDPOINT TEST REPORT")
        print("=" * 80)
        
        # Summary
        summary = report['test_summary']
        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']} ✅")
        print(f"   Failed: {summary['failed_tests']} ❌")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        
        # Category results
        print(f"\n📋 CATEGORY RESULTS:")
        for category, results in report['category_results'].items():
            status = "✅" if results['success_rate'] >= 80 else "⚠️" if results['success_rate'] >= 50 else "❌"
            print(f"   {category.replace('_', ' ').title()}: {results['passed']}/{results['total']} ({results['success_rate']:.1f}%) {status}")
        
        # Fix validation
        fix_results = report['fix_validation']
        print(f"\n🔧 FIX VALIDATION:")
        print(f"   Previously Failing Endpoints: {len(fix_results['previously_failing_endpoints'])}")
        print(f"   Fixed Endpoints: {len(fix_results['fixed_endpoints'])} ✅")
        print(f"   Still Failing: {len(fix_results['still_failing_endpoints'])} ❌")
        print(f"   Fix Success Rate: {fix_results['fix_success_rate']:.1f}%")
        
        if fix_results['fixed_endpoints']:
            print(f"   ✅ Fixed: {', '.join(fix_results['fixed_endpoints'])}")
        
        if fix_results['still_failing_endpoints']:
            print(f"   ❌ Still Failing: {', '.join(fix_results['still_failing_endpoints'])}")
        
        # Performance
        perf = report['performance_metrics']
        print(f"\n⚡ PERFORMANCE METRICS:")
        print(f"   Average Response Time: {perf['avg_response_time_ms']:.1f}ms")
        print(f"   Max Response Time: {perf['max_response_time_ms']:.1f}ms")
        print(f"   JSON Valid Responses: {perf['json_valid_responses']}/{summary['total_tests']}")
        
        # Detailed results
        print(f"\n📝 DETAILED RESULTS:")
        for result in report['detailed_results']:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['test_name']}: {result['status_code']} ({result['response_time_ms']:.0f}ms)")
            if not result['success'] and result['error']:
                print(f"      Error: {result['error']}")
        
        # Conclusion
        print(f"\n🎯 CONCLUSION:")
        if summary['success_rate'] >= 90:
            print("   🎉 EXCELLENT: All critical API endpoints are working correctly!")
        elif summary['success_rate'] >= 80:
            print("   ✅ GOOD: Most API endpoints are working, minor issues remain.")
        elif summary['success_rate'] >= 60:
            print("   ⚠️  FAIR: Some API endpoints are working, significant issues remain.")
        else:
            print("   ❌ POOR: Major API endpoint issues detected.")
        
        if fix_results['fix_success_rate'] >= 80:
            print("   🔧 API fixes were largely successful!")
        else:
            print("   🔧 API fixes need additional work.")

def main():
    """Main test execution"""
    
    # Check for custom base URL
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8093"
    
    print(f"🚀 OpenCode-Slack API Endpoint Comprehensive Testing")
    print(f"🎯 Target: {base_url}")
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = APITester(base_url)
    
    # Wait for server to be ready
    if not tester.wait_for_server():
        print("❌ Server not available, exiting...")
        sys.exit(1)
    
    # Run tests
    report = tester.run_comprehensive_tests()
    
    # Print report
    tester.print_report(report)
    
    # Save report to file
    report_file = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: {report_file}")
    
    # Exit with appropriate code
    success_rate = report['test_summary']['success_rate']
    if success_rate >= 80:
        print("✅ Tests completed successfully!")
        sys.exit(0)
    else:
        print("❌ Tests completed with failures!")
        sys.exit(1)

if __name__ == "__main__":
    main()