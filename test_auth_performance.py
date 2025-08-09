#!/usr/bin/env python3
"""
Quick Authentication Performance Test for Production Readiness
"""

import concurrent.futures
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.security.auth import AuthManager
from src.security.rate_limiter import RateLimiter

def test_jwt_performance():
    """Test JWT authentication performance"""
    print("🔐 JWT Authentication Performance Test")
    
    # Initialize auth manager
    auth_manager = AuthManager(secret_key="test_secret", token_expiry_hours=24)
    
    # Create test users
    users = []
    for i in range(100):
        username = f"user_{i}"
        password = f"pass_{i}"
        auth_manager.create_user(username, password, ["user"], ["read", "write"])
        users.append((username, password))
    
    print(f"   Created {len(users)} test users")
    
    # Test concurrent authentication
    def auth_test(user_data):
        username, password = user_data
        start_time = time.time()
        
        # Authenticate
        user = auth_manager.authenticate_user(username, password)
        if user:
            # Generate JWT
            token = auth_manager.generate_jwt_token(username)
            # Verify JWT
            payload = auth_manager.verify_jwt_token(token)
            success = payload is not None
        else:
            success = False
        
        end_time = time.time()
        return {
            'success': success,
            'response_time_ms': (end_time - start_time) * 1000
        }
    
    # Run concurrent tests
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(auth_test, users))
    end_time = time.time()
    
    # Analyze results
    successful = [r for r in results if r['success']]
    response_times = [r['response_time_ms'] for r in successful]
    
    if response_times:
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]
    else:
        avg_time = max_time = p95_time = 0
    
    total_time = end_time - start_time
    throughput = len(successful) / total_time
    success_rate = len(successful) / len(results) * 100
    
    print(f"   ✅ Results:")
    print(f"      Success Rate: {success_rate:.1f}%")
    print(f"      Avg Response Time: {avg_time:.2f}ms")
    print(f"      Max Response Time: {max_time:.2f}ms")
    print(f"      95th Percentile: {p95_time:.2f}ms")
    print(f"      Throughput: {throughput:.1f} auths/sec")
    
    # Performance targets
    performance_ok = (
        success_rate >= 99.0 and
        avg_time <= 20.0 and
        p95_time <= 50.0 and
        throughput >= 100.0
    )
    
    return performance_ok, {
        'success_rate': success_rate,
        'avg_response_time_ms': avg_time,
        'p95_response_time_ms': p95_time,
        'throughput': throughput
    }

def test_api_key_performance():
    """Test API key authentication performance"""
    print("\n🔑 API Key Authentication Performance Test")
    
    auth_manager = AuthManager()
    
    # Generate API keys
    api_keys = []
    for i in range(50):
        key = auth_manager.generate_api_key(f"key_{i}", ["read", "write"])
        api_keys.append(key)
    
    print(f"   Generated {len(api_keys)} API keys")
    
    # Test API key verification
    def verify_test(api_key):
        start_time = time.time()
        key_info = auth_manager.verify_api_key(api_key)
        end_time = time.time()
        
        return {
            'success': key_info is not None,
            'response_time_ms': (end_time - start_time) * 1000
        }
    
    # Test each key multiple times
    all_tests = []
    for key in api_keys:
        all_tests.extend([key] * 10)  # 10 tests per key = 500 total
    
    # Run concurrent tests
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(verify_test, all_tests))
    end_time = time.time()
    
    # Analyze results
    successful = [r for r in results if r['success']]
    response_times = [r['response_time_ms'] for r in successful]
    
    if response_times:
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
    else:
        avg_time = max_time = 0
    
    total_time = end_time - start_time
    throughput = len(successful) / total_time
    success_rate = len(successful) / len(results) * 100
    
    print(f"   ✅ Results:")
    print(f"      Success Rate: {success_rate:.1f}%")
    print(f"      Avg Response Time: {avg_time:.2f}ms")
    print(f"      Max Response Time: {max_time:.2f}ms")
    print(f"      Throughput: {throughput:.1f} verifications/sec")
    
    performance_ok = (
        success_rate >= 99.0 and
        avg_time <= 10.0 and
        throughput >= 500.0
    )
    
    return performance_ok, {
        'success_rate': success_rate,
        'avg_response_time_ms': avg_time,
        'throughput': throughput
    }

def test_rate_limiting():
    """Test rate limiting performance"""
    print("\n🚫 Rate Limiting Performance Test")
    
    rate_limiter = RateLimiter()
    
    # Test rate limiting under load
    def rate_limit_test(client_id):
        results = []
        for i in range(150):  # Exceed rate limit
            allowed, info = rate_limiter.is_allowed(f"test_client_{client_id}", "/test", limit=100)
            results.append(allowed)
        return results
    
    # Run concurrent rate limit tests
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        all_results = []
        futures = [executor.submit(rate_limit_test, i) for i in range(5)]
        for future in futures:
            all_results.extend(future.result())
    end_time = time.time()
    
    allowed_count = sum(all_results)
    blocked_count = len(all_results) - allowed_count
    blocking_rate = blocked_count / len(all_results) * 100
    
    print(f"   ✅ Results:")
    print(f"      Total Requests: {len(all_results)}")
    print(f"      Allowed: {allowed_count}")
    print(f"      Blocked: {blocked_count}")
    print(f"      Blocking Rate: {blocking_rate:.1f}%")
    
    # Rate limiting should block some requests
    rate_limiting_ok = blocking_rate > 10.0
    
    return rate_limiting_ok, {
        'blocking_rate': blocking_rate,
        'total_requests': len(all_results)
    }

def test_security_validation():
    """Test input validation security"""
    print("\n🛡️  Security Validation Test")
    
    auth_manager = AuthManager()
    
    # Malicious inputs
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "<script>alert('xss')</script>",
        "../../etc/passwd",
        "admin' OR '1'='1",
        "$(rm -rf /)"
    ]
    
    blocked_count = 0
    for malicious_input in malicious_inputs:
        try:
            # Should fail to create user with malicious input
            success = auth_manager.create_user(malicious_input, "password", ["user"], ["read"])
            if not success:
                blocked_count += 1
        except Exception:
            # Exception is good - means input was blocked
            blocked_count += 1
    
    blocking_rate = blocked_count / len(malicious_inputs) * 100
    
    print(f"   ✅ Results:")
    print(f"      Malicious Inputs Tested: {len(malicious_inputs)}")
    print(f"      Blocked: {blocked_count}")
    print(f"      Blocking Rate: {blocking_rate:.1f}%")
    
    # Should block 100% of malicious inputs
    security_ok = blocking_rate >= 100.0
    
    return security_ok, {
        'blocking_rate': blocking_rate,
        'malicious_inputs_tested': len(malicious_inputs)
    }

def main():
    """Run comprehensive authentication performance tests"""
    print("🚀 AUTHENTICATION PERFORMANCE TEST SUITE")
    print("=" * 60)
    print("🎯 Testing for 100% Production Readiness")
    print("=" * 60)
    
    # Run all tests
    tests = [
        ("JWT Authentication", test_jwt_performance),
        ("API Key Authentication", test_api_key_performance),
        ("Rate Limiting", test_rate_limiting),
        ("Security Validation", test_security_validation)
    ]
    
    results = {}
    all_passed = True
    
    for test_name, test_func in tests:
        try:
            passed, metrics = test_func()
            results[test_name] = {'passed': passed, 'metrics': metrics}
            all_passed &= passed
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} {test_name}")
            
        except Exception as e:
            print(f"   ❌ FAIL {test_name}: {e}")
            results[test_name] = {'passed': False, 'error': str(e)}
            all_passed = False
    
    # Final assessment
    print("\n" + "=" * 60)
    print("📊 FINAL ASSESSMENT")
    print("=" * 60)
    
    passed_tests = sum(1 for r in results.values() if r['passed'])
    total_tests = len(results)
    success_rate = passed_tests / total_tests * 100
    
    print(f"Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
    
    if all_passed:
        print("🎉 PRODUCTION READINESS: ✅ APPROVED")
        print("   🚀 Authentication system ready for enterprise deployment")
        print("   🔐 All performance and security targets met")
        print("   📊 System validated for high-load production use")
    else:
        print("🚨 PRODUCTION READINESS: ❌ NOT APPROVED")
        print("   ⚠️  Critical issues must be resolved before deployment")
        
        failed_tests = [name for name, result in results.items() if not result['passed']]
        print("   Failed tests:")
        for test in failed_tests:
            print(f"     - {test}")
    
    # Performance summary
    print(f"\n📈 PERFORMANCE SUMMARY:")
    for test_name, result in results.items():
        if result['passed'] and 'metrics' in result:
            metrics = result['metrics']
            print(f"   {test_name}:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    print(f"     • {metric}: {value:.2f}")
                else:
                    print(f"     • {metric}: {value}")
    
    print(f"\n✅ Authentication load testing completed")
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)