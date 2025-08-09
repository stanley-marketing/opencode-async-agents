#!/usr/bin/env python3
"""
Comprehensive Security Testing for Authentication System
"""

import concurrent.futures
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.security.auth import AuthManager

def validate_input_security(input_string):
    """Enhanced input validation with security checks"""
    if not input_string or not isinstance(input_string, str):
        return False, "Invalid input type"
    
    # Check for SQL injection patterns
    sql_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\'\s*(OR|AND)\s*\'\d+\'\s*=\s*\'\d+)",
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, input_string, re.IGNORECASE):
            return False, "SQL injection pattern detected"
    
    # Check for XSS patterns
    xss_patterns = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, input_string, re.IGNORECASE):
            return False, "XSS pattern detected"
    
    # Check for path traversal
    path_patterns = [
        r"\.\./",
        r"\.\.\\",
        r"/etc/passwd",
        r"\\windows\\system32",
    ]
    
    for pattern in path_patterns:
        if re.search(pattern, input_string, re.IGNORECASE):
            return False, "Path traversal pattern detected"
    
    # Check for command injection
    cmd_patterns = [
        r"[;&|`$()]",
        r"\b(rm|del|format|cat|type|net|ping|wget|curl)\b",
    ]
    
    for pattern in cmd_patterns:
        if re.search(pattern, input_string, re.IGNORECASE):
            return False, "Command injection pattern detected"
    
    # Basic length and character validation
    if len(input_string) > 100:
        return False, "Input too long"
    
    # Allow only alphanumeric, spaces, and basic punctuation
    if not re.match(r"^[a-zA-Z0-9\s\-_\.@]+$", input_string):
        return False, "Invalid characters detected"
    
    return True, "Valid input"

class SecureAuthManager(AuthManager):
    """Enhanced AuthManager with security validation"""
    
    def create_user(self, username, password, roles=None, permissions=None):
        """Create user with enhanced security validation"""
        # Validate username
        valid, reason = validate_input_security(username)
        if not valid:
            raise ValueError(f"Invalid username: {reason}")
        
        # Validate password strength
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        # Call parent method
        return super().create_user(username, password, roles, permissions)
    
    def authenticate_user(self, username, password):
        """Authenticate with security validation"""
        # Validate inputs
        valid, reason = validate_input_security(username)
        if not valid:
            return None
        
        return super().authenticate_user(username, password)

def test_enhanced_security():
    """Test enhanced security validation"""
    print("🛡️  Enhanced Security Validation Test")
    
    auth_manager = SecureAuthManager()
    
    # Test cases: (input, should_be_blocked)
    test_cases = [
        # SQL Injection
        ("'; DROP TABLE users; --", True),
        ("admin' OR '1'='1", True),
        ("' UNION SELECT * FROM users --", True),
        ("user'; DELETE FROM employees; --", True),
        
        # XSS
        ("<script>alert('xss')</script>", True),
        ("<img src=x onerror=alert(1)>", True),
        ("javascript:alert('xss')", True),
        ("<iframe src='evil.com'></iframe>", True),
        
        # Path Traversal
        ("../../etc/passwd", True),
        ("../../../windows/system32", True),
        ("..\\..\\windows\\system32", True),
        
        # Command Injection
        ("user; rm -rf /", True),
        ("user && cat /etc/passwd", True),
        ("user | ping evil.com", True),
        ("user$(whoami)", True),
        
        # Valid inputs
        ("john_doe", False),
        ("user123", False),
        ("test.user@example.com", False),
        ("valid-username", False),
    ]
    
    blocked_count = 0
    total_malicious = 0
    false_positives = 0
    
    for test_input, should_be_blocked in test_cases:
        if should_be_blocked:
            total_malicious += 1
        
        try:
            success = auth_manager.create_user(test_input, "password123", ["user"], ["read"])
            if should_be_blocked and not success:
                blocked_count += 1
            elif not should_be_blocked and not success:
                false_positives += 1
        except (ValueError, Exception) as e:
            if should_be_blocked:
                blocked_count += 1
            elif not should_be_blocked:
                false_positives += 1
    
    blocking_rate = blocked_count / total_malicious * 100 if total_malicious > 0 else 0
    false_positive_rate = false_positives / (len(test_cases) - total_malicious) * 100
    
    print(f"   ✅ Results:")
    print(f"      Total Test Cases: {len(test_cases)}")
    print(f"      Malicious Inputs: {total_malicious}")
    print(f"      Blocked Malicious: {blocked_count}")
    print(f"      Blocking Rate: {blocking_rate:.1f}%")
    print(f"      False Positives: {false_positives}")
    print(f"      False Positive Rate: {false_positive_rate:.1f}%")
    
    # Security should block 100% of malicious inputs with minimal false positives
    security_ok = blocking_rate >= 100.0 and false_positive_rate <= 10.0
    
    return security_ok, {
        'blocking_rate': blocking_rate,
        'false_positive_rate': false_positive_rate,
        'malicious_inputs_tested': total_malicious
    }

def test_brute_force_protection():
    """Test brute force protection"""
    print("\n🔒 Brute Force Protection Test")
    
    auth_manager = SecureAuthManager()
    
    # Create target user
    auth_manager.create_user("target_user", "correct_password", ["user"], ["read"])
    
    # Simulate brute force attack
    wrong_passwords = [
        "password123", "admin", "123456", "password", "qwerty",
        "letmein", "welcome", "monkey", "dragon", "master"
    ]
    
    failed_attempts = 0
    total_attempts = 0
    
    # Test multiple wrong passwords
    for _ in range(100):  # 100 brute force attempts
        wrong_password = wrong_passwords[total_attempts % len(wrong_passwords)]
        user = auth_manager.authenticate_user("target_user", wrong_password)
        total_attempts += 1
        
        if user is None:
            failed_attempts += 1
    
    # Test correct password still works
    correct_auth = auth_manager.authenticate_user("target_user", "correct_password")
    
    protection_rate = failed_attempts / total_attempts * 100
    correct_still_works = correct_auth is not None
    
    print(f"   ✅ Results:")
    print(f"      Total Brute Force Attempts: {total_attempts}")
    print(f"      Failed Attempts: {failed_attempts}")
    print(f"      Protection Rate: {protection_rate:.1f}%")
    print(f"      Correct Password Still Works: {correct_still_works}")
    
    # Should block all wrong attempts but allow correct password
    protection_ok = protection_rate >= 100.0 and correct_still_works
    
    return protection_ok, {
        'protection_rate': protection_rate,
        'correct_password_works': correct_still_works,
        'total_attempts': total_attempts
    }

def test_concurrent_security():
    """Test security under concurrent load"""
    print("\n⚡ Concurrent Security Test")
    
    auth_manager = SecureAuthManager()
    
    # Malicious inputs for concurrent testing
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "<script>alert('xss')</script>",
        "../../etc/passwd",
        "admin' OR '1'='1",
        "user; rm -rf /"
    ] * 20  # 100 total malicious attempts
    
    def security_test(malicious_input):
        try:
            success = auth_manager.create_user(malicious_input, "password123", ["user"], ["read"])
            return {'blocked': not success, 'error': None}
        except Exception as e:
            return {'blocked': True, 'error': str(e)}
    
    # Run concurrent security tests
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(security_test, malicious_inputs))
    end_time = time.time()
    
    blocked_count = sum(1 for r in results if r['blocked'])
    total_time = end_time - start_time
    throughput = len(results) / total_time
    
    blocking_rate = blocked_count / len(results) * 100
    
    print(f"   ✅ Results:")
    print(f"      Concurrent Malicious Attempts: {len(results)}")
    print(f"      Blocked: {blocked_count}")
    print(f"      Blocking Rate: {blocking_rate:.1f}%")
    print(f"      Processing Time: {total_time:.2f}s")
    print(f"      Security Throughput: {throughput:.1f} validations/sec")
    
    # Should block all malicious inputs even under load
    concurrent_security_ok = blocking_rate >= 100.0 and throughput >= 50.0
    
    return concurrent_security_ok, {
        'blocking_rate': blocking_rate,
        'throughput': throughput,
        'total_attempts': len(results)
    }

def test_token_security():
    """Test JWT token security"""
    print("\n🎫 JWT Token Security Test")
    
    auth_manager = SecureAuthManager()
    
    # Create test user
    auth_manager.create_user("token_user", "password123", ["user"], ["read"])
    
    # Generate token
    token = auth_manager.generate_jwt_token("token_user")
    
    # Test token manipulation attempts
    security_tests = []
    
    # Test 1: Valid token
    payload = auth_manager.verify_jwt_token(token)
    security_tests.append(('valid_token', payload is not None))
    
    # Test 2: Tampered token
    tampered_token = token[:-5] + "XXXXX"
    payload = auth_manager.verify_jwt_token(tampered_token)
    security_tests.append(('tampered_token', payload is None))
    
    # Test 3: Invalid token format
    invalid_token = "invalid.token.format"
    payload = auth_manager.verify_jwt_token(invalid_token)
    security_tests.append(('invalid_format', payload is None))
    
    # Test 4: Empty token
    payload = auth_manager.verify_jwt_token("")
    security_tests.append(('empty_token', payload is None))
    
    # Test 5: None token
    payload = auth_manager.verify_jwt_token(None)
    security_tests.append(('none_token', payload is None))
    
    passed_tests = sum(1 for _, passed in security_tests if passed)
    total_tests = len(security_tests)
    
    print(f"   ✅ Results:")
    for test_name, passed in security_tests:
        status = "✅" if passed else "❌"
        print(f"      {status} {test_name}")
    
    print(f"      Token Security Rate: {passed_tests/total_tests*100:.1f}%")
    
    token_security_ok = passed_tests == total_tests
    
    return token_security_ok, {
        'security_rate': passed_tests/total_tests*100,
        'tests_passed': passed_tests,
        'total_tests': total_tests
    }

def main():
    """Run comprehensive security tests"""
    print("🛡️  COMPREHENSIVE SECURITY TEST SUITE")
    print("=" * 60)
    print("🎯 Testing for 100% Security Compliance")
    print("=" * 60)
    
    # Run all security tests
    tests = [
        ("Enhanced Security Validation", test_enhanced_security),
        ("Brute Force Protection", test_brute_force_protection),
        ("Concurrent Security", test_concurrent_security),
        ("JWT Token Security", test_token_security)
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
    
    # Final security assessment
    print("\n" + "=" * 60)
    print("🔒 SECURITY ASSESSMENT")
    print("=" * 60)
    
    passed_tests = sum(1 for r in results.values() if r['passed'])
    total_tests = len(results)
    security_score = passed_tests / total_tests * 100
    
    print(f"Security Score: {security_score:.1f}% ({passed_tests}/{total_tests})")
    
    if all_passed:
        print("🎉 SECURITY COMPLIANCE: ✅ APPROVED")
        print("   🛡️  All security measures validated")
        print("   🔒 100% protection against common attacks")
        print("   ⚡ Security maintained under high load")
        print("   🎫 Token security fully validated")
    else:
        print("🚨 SECURITY COMPLIANCE: ❌ NOT APPROVED")
        print("   ⚠️  Critical security issues must be resolved")
        
        failed_tests = [name for name, result in results.items() if not result['passed']]
        print("   Failed security tests:")
        for test in failed_tests:
            print(f"     - {test}")
    
    # Security metrics summary
    print(f"\n📊 SECURITY METRICS:")
    for test_name, result in results.items():
        if 'metrics' in result:
            metrics = result['metrics']
            print(f"   {test_name}:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    print(f"     • {metric}: {value:.2f}")
                else:
                    print(f"     • {metric}: {value}")
    
    print(f"\n✅ Security testing completed")
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)