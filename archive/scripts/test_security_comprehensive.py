#!/usr/bin/env python3
"""
Comprehensive security testing for OpenCode-Slack API.
Tests authentication, authorization, rate limiting, input validation, and security headers.
"""

import requests
import json
import time
import threading
import concurrent.futures
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityTester:
    """Comprehensive security testing suite"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.auth_token = None
        self.api_key = None
        self.test_results = []
        
        # Test data
        self.test_user = {
            "username": "admin",
            "password": "opencode-admin-2024"
        }
        
        self.malicious_payloads = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "UNION SELECT * FROM users",
            "cmd.exe /c dir",
            "/bin/sh -c ls",
            "<?php system($_GET['cmd']); ?>",
            "{{7*7}}",  # Template injection
        ]
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        logger.info(f"[{status}] {test_name}: {details}")
    
    def test_authentication_system(self) -> Dict:
        """Test authentication endpoints"""
        results = {"category": "Authentication", "tests": []}
        
        # Test 1: Login with valid credentials
        try:
            response = self.session.post(f"{self.base_url}/auth/login", 
                                       json=self.test_user)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('token')
                self.log_test_result("Valid Login", True, f"Token received: {self.auth_token[:20]}...")
                results["tests"].append({"name": "Valid Login", "status": "pass"})
            else:
                self.log_test_result("Valid Login", False, f"Status: {response.status_code}")
                results["tests"].append({"name": "Valid Login", "status": "fail"})
        except Exception as e:
            self.log_test_result("Valid Login", False, f"Exception: {e}")
            results["tests"].append({"name": "Valid Login", "status": "error"})
        
        # Test 2: Login with invalid credentials
        try:
            response = self.session.post(f"{self.base_url}/auth/login", 
                                       json={"username": "invalid", "password": "wrong"})
            
            if response.status_code == 401:
                self.log_test_result("Invalid Login Rejection", True, "Correctly rejected")
                results["tests"].append({"name": "Invalid Login Rejection", "status": "pass"})
            else:
                self.log_test_result("Invalid Login Rejection", False, f"Status: {response.status_code}")
                results["tests"].append({"name": "Invalid Login Rejection", "status": "fail"})
        except Exception as e:
            self.log_test_result("Invalid Login Rejection", False, f"Exception: {e}")
            results["tests"].append({"name": "Invalid Login Rejection", "status": "error"})
        
        # Test 3: Access protected endpoint without token
        try:
            response = self.session.get(f"{self.base_url}/employees")
            
            if response.status_code == 401:
                self.log_test_result("Unauthorized Access Blocked", True, "Access denied without token")
                results["tests"].append({"name": "Unauthorized Access Blocked", "status": "pass"})
            else:
                self.log_test_result("Unauthorized Access Blocked", False, f"Status: {response.status_code}")
                results["tests"].append({"name": "Unauthorized Access Blocked", "status": "fail"})
        except Exception as e:
            self.log_test_result("Unauthorized Access Blocked", False, f"Exception: {e}")
            results["tests"].append({"name": "Unauthorized Access Blocked", "status": "error"})
        
        # Test 4: Access protected endpoint with valid token
        if self.auth_token:
            try:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                response = self.session.get(f"{self.base_url}/employees", headers=headers)
                
                if response.status_code == 200:
                    self.log_test_result("Authorized Access", True, "Access granted with valid token")
                    results["tests"].append({"name": "Authorized Access", "status": "pass"})
                else:
                    self.log_test_result("Authorized Access", False, f"Status: {response.status_code}")
                    results["tests"].append({"name": "Authorized Access", "status": "fail"})
            except Exception as e:
                self.log_test_result("Authorized Access", False, f"Exception: {e}")
                results["tests"].append({"name": "Authorized Access", "status": "error"})
        
        # Test 5: Token refresh
        if self.auth_token:
            try:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                response = self.session.post(f"{self.base_url}/auth/refresh", headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    new_token = data.get('token')
                    self.log_test_result("Token Refresh", True, f"New token received: {new_token[:20]}...")
                    results["tests"].append({"name": "Token Refresh", "status": "pass"})
                else:
                    self.log_test_result("Token Refresh", False, f"Status: {response.status_code}")
                    results["tests"].append({"name": "Token Refresh", "status": "fail"})
            except Exception as e:
                self.log_test_result("Token Refresh", False, f"Exception: {e}")
                results["tests"].append({"name": "Token Refresh", "status": "error"})
        
        return results
    
    def test_api_key_system(self) -> Dict:
        """Test API key authentication"""
        results = {"category": "API Key Authentication", "tests": []}
        
        if not self.auth_token:
            results["tests"].append({"name": "API Key Tests", "status": "skip", "reason": "No auth token"})
            return results
        
        # Test 1: Create API key
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            api_key_data = {
                "name": "test-key",
                "permissions": ["read", "employees:read"],
                "expires_days": 30
            }
            response = self.session.post(f"{self.base_url}/auth/api-keys", 
                                       json=api_key_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.api_key = data.get('api_key')
                self.log_test_result("API Key Creation", True, f"Key created: {self.api_key[:20]}...")
                results["tests"].append({"name": "API Key Creation", "status": "pass"})
            else:
                self.log_test_result("API Key Creation", False, f"Status: {response.status_code}")
                results["tests"].append({"name": "API Key Creation", "status": "fail"})
        except Exception as e:
            self.log_test_result("API Key Creation", False, f"Exception: {e}")
            results["tests"].append({"name": "API Key Creation", "status": "error"})
        
        # Test 2: Use API key for authentication
        if self.api_key:
            try:
                headers = {"X-API-Key": self.api_key}
                response = self.session.get(f"{self.base_url}/employees", headers=headers)
                
                if response.status_code == 200:
                    self.log_test_result("API Key Authentication", True, "Access granted with API key")
                    results["tests"].append({"name": "API Key Authentication", "status": "pass"})
                else:
                    self.log_test_result("API Key Authentication", False, f"Status: {response.status_code}")
                    results["tests"].append({"name": "API Key Authentication", "status": "fail"})
            except Exception as e:
                self.log_test_result("API Key Authentication", False, f"Exception: {e}")
                results["tests"].append({"name": "API Key Authentication", "status": "error"})
        
        # Test 3: List API keys
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/auth/api-keys", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                keys = data.get('api_keys', [])
                self.log_test_result("API Key Listing", True, f"Found {len(keys)} keys")
                results["tests"].append({"name": "API Key Listing", "status": "pass"})
            else:
                self.log_test_result("API Key Listing", False, f"Status: {response.status_code}")
                results["tests"].append({"name": "API Key Listing", "status": "fail"})
        except Exception as e:
            self.log_test_result("API Key Listing", False, f"Exception: {e}")
            results["tests"].append({"name": "API Key Listing", "status": "error"})
        
        return results
    
    def test_rate_limiting(self) -> Dict:
        """Test rate limiting functionality"""
        results = {"category": "Rate Limiting", "tests": []}
        
        if not self.auth_token:
            results["tests"].append({"name": "Rate Limiting Tests", "status": "skip", "reason": "No auth token"})
            return results
        
        # Test 1: Normal rate limiting
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            success_count = 0
            rate_limited_count = 0
            
            # Make multiple requests quickly
            for i in range(20):
                response = self.session.get(f"{self.base_url}/health", headers=headers)
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited_count += 1
                time.sleep(0.1)  # Small delay
            
            if success_count > 0:
                self.log_test_result("Rate Limiting Normal", True, 
                                   f"Success: {success_count}, Rate limited: {rate_limited_count}")
                results["tests"].append({"name": "Rate Limiting Normal", "status": "pass"})
            else:
                self.log_test_result("Rate Limiting Normal", False, "No successful requests")
                results["tests"].append({"name": "Rate Limiting Normal", "status": "fail"})
        except Exception as e:
            self.log_test_result("Rate Limiting Normal", False, f"Exception: {e}")
            results["tests"].append({"name": "Rate Limiting Normal", "status": "error"})
        
        # Test 2: Concurrent rate limiting
        def make_request():
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/health", headers=headers)
            return response.status_code
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(50)]
                status_codes = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            success_count = status_codes.count(200)
            rate_limited_count = status_codes.count(429)
            
            if rate_limited_count > 0:
                self.log_test_result("Concurrent Rate Limiting", True, 
                                   f"Success: {success_count}, Rate limited: {rate_limited_count}")
                results["tests"].append({"name": "Concurrent Rate Limiting", "status": "pass"})
            else:
                self.log_test_result("Concurrent Rate Limiting", False, "No rate limiting detected")
                results["tests"].append({"name": "Concurrent Rate Limiting", "status": "fail"})
        except Exception as e:
            self.log_test_result("Concurrent Rate Limiting", False, f"Exception: {e}")
            results["tests"].append({"name": "Concurrent Rate Limiting", "status": "error"})
        
        return results
    
    def test_input_validation(self) -> Dict:
        """Test input validation and security"""
        results = {"category": "Input Validation", "tests": []}
        
        if not self.auth_token:
            results["tests"].append({"name": "Input Validation Tests", "status": "skip", "reason": "No auth token"})
            return results
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test malicious payloads
        blocked_count = 0
        total_tests = len(self.malicious_payloads)
        
        for i, payload in enumerate(self.malicious_payloads):
            try:
                # Test in employee creation
                malicious_data = {
                    "name": f"test_{i}",
                    "role": payload  # Inject malicious content in role
                }
                
                response = self.session.post(f"{self.base_url}/employees", 
                                           json=malicious_data, headers=headers)
                
                if response.status_code == 400:
                    blocked_count += 1
                    self.log_test_result(f"Malicious Payload {i+1}", True, f"Blocked: {payload[:30]}...")
                else:
                    self.log_test_result(f"Malicious Payload {i+1}", False, 
                                       f"Not blocked: {payload[:30]}... (Status: {response.status_code})")
                
                time.sleep(0.1)  # Avoid rate limiting
                
            except Exception as e:
                self.log_test_result(f"Malicious Payload {i+1}", False, f"Exception: {e}")
        
        # Summary
        if blocked_count >= total_tests * 0.8:  # At least 80% should be blocked
            self.log_test_result("Input Validation Overall", True, 
                               f"Blocked {blocked_count}/{total_tests} malicious payloads")
            results["tests"].append({"name": "Input Validation Overall", "status": "pass"})
        else:
            self.log_test_result("Input Validation Overall", False, 
                               f"Only blocked {blocked_count}/{total_tests} malicious payloads")
            results["tests"].append({"name": "Input Validation Overall", "status": "fail"})
        
        return results
    
    def test_security_headers(self) -> Dict:
        """Test security headers in responses"""
        results = {"category": "Security Headers", "tests": []}
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
        
        try:
            response = self.session.get(f"{self.base_url}/health")
            headers_present = []
            headers_missing = []
            
            for header in required_headers:
                if header in response.headers:
                    headers_present.append(header)
                else:
                    headers_missing.append(header)
            
            if len(headers_missing) == 0:
                self.log_test_result("Security Headers", True, f"All {len(required_headers)} headers present")
                results["tests"].append({"name": "Security Headers", "status": "pass"})
            else:
                self.log_test_result("Security Headers", False, f"Missing: {', '.join(headers_missing)}")
                results["tests"].append({"name": "Security Headers", "status": "fail"})
                
        except Exception as e:
            self.log_test_result("Security Headers", False, f"Exception: {e}")
            results["tests"].append({"name": "Security Headers", "status": "error"})
        
        return results
    
    def test_authorization_levels(self) -> Dict:
        """Test different authorization levels"""
        results = {"category": "Authorization", "tests": []}
        
        if not self.auth_token:
            results["tests"].append({"name": "Authorization Tests", "status": "skip", "reason": "No auth token"})
            return results
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test different endpoints with different permission requirements
        test_endpoints = [
            ("/employees", "GET", "employees:read"),
            ("/employees", "POST", "employees:write"),
            ("/tasks", "POST", "tasks:write"),
            ("/files", "GET", "files:read"),
            ("/security/stats", "GET", "admin"),
        ]
        
        for endpoint, method, permission in test_endpoints:
            try:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}", headers=headers)
                elif method == "POST":
                    response = self.session.post(f"{self.base_url}{endpoint}", 
                                               json={"test": "data"}, headers=headers)
                
                # Admin user should have access to all endpoints
                if response.status_code in [200, 400]:  # 400 might be due to invalid data, not auth
                    self.log_test_result(f"Access {endpoint} ({permission})", True, 
                                       f"Status: {response.status_code}")
                    results["tests"].append({"name": f"Access {endpoint}", "status": "pass"})
                else:
                    self.log_test_result(f"Access {endpoint} ({permission})", False, 
                                       f"Status: {response.status_code}")
                    results["tests"].append({"name": f"Access {endpoint}", "status": "fail"})
                
                time.sleep(0.1)  # Avoid rate limiting
                
            except Exception as e:
                self.log_test_result(f"Access {endpoint} ({permission})", False, f"Exception: {e}")
                results["tests"].append({"name": f"Access {endpoint}", "status": "error"})
        
        return results
    
    def test_error_handling(self) -> Dict:
        """Test error handling doesn't leak sensitive information"""
        results = {"category": "Error Handling", "tests": []}
        
        # Test various error conditions
        error_tests = [
            ("/nonexistent", "GET", "404 handling"),
            ("/employees", "PATCH", "Method not allowed"),
            ("/auth/login", "GET", "Wrong method for login"),
        ]
        
        for endpoint, method, description in error_tests:
            try:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}")
                elif method == "PATCH":
                    response = self.session.patch(f"{self.base_url}{endpoint}")
                
                # Check if error response contains sensitive information
                response_text = response.text.lower()
                sensitive_keywords = ["password", "secret", "key", "token", "traceback", "exception"]
                
                has_sensitive_info = any(keyword in response_text for keyword in sensitive_keywords)
                
                if not has_sensitive_info:
                    self.log_test_result(f"Error Handling - {description}", True, 
                                       "No sensitive information leaked")
                    results["tests"].append({"name": f"Error Handling - {description}", "status": "pass"})
                else:
                    self.log_test_result(f"Error Handling - {description}", False, 
                                       "Sensitive information detected in error response")
                    results["tests"].append({"name": f"Error Handling - {description}", "status": "fail"})
                
            except Exception as e:
                self.log_test_result(f"Error Handling - {description}", False, f"Exception: {e}")
                results["tests"].append({"name": f"Error Handling - {description}", "status": "error"})
        
        return results
    
    def run_all_tests(self) -> Dict:
        """Run all security tests"""
        print("🔒 Starting Comprehensive Security Testing")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all test categories
        test_categories = [
            self.test_authentication_system(),
            self.test_api_key_system(),
            self.test_rate_limiting(),
            self.test_input_validation(),
            self.test_security_headers(),
            self.test_authorization_levels(),
            self.test_error_handling(),
        ]
        
        end_time = time.time()
        
        # Compile results
        total_tests = sum(len(category["tests"]) for category in test_categories)
        passed_tests = sum(1 for category in test_categories 
                          for test in category["tests"] if test["status"] == "pass")
        failed_tests = sum(1 for category in test_categories 
                          for test in category["tests"] if test["status"] == "fail")
        error_tests = sum(1 for category in test_categories 
                         for test in category["tests"] if test["status"] == "error")
        skipped_tests = sum(1 for category in test_categories 
                           for test in category["tests"] if test["status"] == "skip")
        
        summary = {
            "test_summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "skipped": skipped_tests,
                "duration_seconds": round(end_time - start_time, 2)
            },
            "categories": test_categories,
            "detailed_results": self.test_results,
            "recommendations": self._generate_recommendations()
        }
        
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations based on test results"""
        recommendations = []
        
        failed_tests = [result for result in self.test_results if not result["test"].endswith("True")]
        
        if any("Rate Limiting" in test["test"] for test in failed_tests):
            recommendations.append("Implement stricter rate limiting policies")
        
        if any("Input Validation" in test["test"] for test in failed_tests):
            recommendations.append("Enhance input validation and sanitization")
        
        if any("Security Headers" in test["test"] for test in failed_tests):
            recommendations.append("Add missing security headers to all responses")
        
        if any("Error Handling" in test["test"] for test in failed_tests):
            recommendations.append("Review error responses to prevent information leakage")
        
        if not recommendations:
            recommendations.append("Security implementation looks good! Continue monitoring.")
        
        return recommendations


def main():
    """Main function to run security tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='OpenCode-Slack Security Tester')
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='Base URL of the API server')
    parser.add_argument('--output', default='security_test_results.json',
                       help='Output file for test results')
    
    args = parser.parse_args()
    
    # Run tests
    tester = SecurityTester(args.url)
    results = tester.run_all_tests()
    
    # Print summary
    print("\n" + "=" * 60)
    print("🔒 SECURITY TEST SUMMARY")
    print("=" * 60)
    
    summary = results["test_summary"]
    print(f"Total Tests: {summary['total']}")
    print(f"✅ Passed: {summary['passed']}")
    print(f"❌ Failed: {summary['failed']}")
    print(f"⚠️  Errors: {summary['errors']}")
    print(f"⏭️  Skipped: {summary['skipped']}")
    print(f"⏱️  Duration: {summary['duration_seconds']}s")
    
    success_rate = (summary['passed'] / summary['total']) * 100 if summary['total'] > 0 else 0
    print(f"📊 Success Rate: {success_rate:.1f}%")
    
    print("\n🔧 RECOMMENDATIONS:")
    for i, rec in enumerate(results["recommendations"], 1):
        print(f"  {i}. {rec}")
    
    # Save detailed results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {args.output}")
    
    # Return appropriate exit code
    if summary['failed'] > 0 or summary['errors'] > 0:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())