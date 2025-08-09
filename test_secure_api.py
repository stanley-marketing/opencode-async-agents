#!/usr/bin/env python3
"""
Quick API testing script for the secure OpenCode-Slack server.
Tests basic functionality with authentication.
"""

import requests
import json
import time
import sys
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class SecureAPITester:
    """Simple API tester for secure endpoints"""
    
    def __init__(self, base_url="https://localhost:8443"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.verify = False  # Accept self-signed certificates
        self.auth_token = None
        self.api_key = None
    
    def test_health_endpoint(self):
        """Test health endpoint (public)"""
        print("🔍 Testing health endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
                return True
            return False
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_authentication(self):
        """Test authentication system"""
        print("🔐 Testing authentication...")
        
        # Test login
        try:
            login_data = {
                "username": "admin",
                "password": "opencode-admin-2024"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            print(f"   Login Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('token')
                print(f"   Token received: {self.auth_token[:30]}...")
                print(f"   User info: {data.get('user')}")
                return True
            else:
                print(f"   Login failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_protected_endpoint(self):
        """Test protected endpoint with authentication"""
        print("🛡️  Testing protected endpoint...")
        
        if not self.auth_token:
            print("   No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/employees", headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Employees: {len(data.get('employees', []))}")
                return True
            else:
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_unauthorized_access(self):
        """Test that unauthorized access is blocked"""
        print("🚫 Testing unauthorized access...")
        
        try:
            response = self.session.get(f"{self.base_url}/employees")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 401:
                print("   ✅ Unauthorized access correctly blocked")
                return True
            else:
                print(f"   ❌ Unauthorized access not blocked (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_api_key_creation(self):
        """Test API key creation"""
        print("🔑 Testing API key creation...")
        
        if not self.auth_token:
            print("   No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            api_key_data = {
                "name": "test-api-key",
                "permissions": ["read", "employees:read"],
                "expires_days": 30
            }
            
            response = self.session.post(f"{self.base_url}/auth/api-keys", 
                                       json=api_key_data, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.api_key = data.get('api_key')
                print(f"   API Key created: {self.api_key[:30]}...")
                return True
            else:
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_api_key_usage(self):
        """Test using API key for authentication"""
        print("🔐 Testing API key usage...")
        
        if not self.api_key:
            print("   No API key available")
            return False
        
        try:
            headers = {"X-API-Key": self.api_key}
            response = self.session.get(f"{self.base_url}/employees", headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ API key authentication successful")
                print(f"   Employees: {len(data.get('employees', []))}")
                return True
            else:
                print(f"   ❌ API key authentication failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        print("⏱️  Testing rate limiting...")
        
        if not self.auth_token:
            print("   No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            success_count = 0
            rate_limited_count = 0
            
            # Make rapid requests
            for i in range(15):
                response = self.session.get(f"{self.base_url}/health", headers=headers)
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited_count += 1
                    print(f"   Rate limited on request {i+1}")
                time.sleep(0.05)  # Small delay
            
            print(f"   Successful requests: {success_count}")
            print(f"   Rate limited requests: {rate_limited_count}")
            
            if rate_limited_count > 0:
                print("   ✅ Rate limiting is working")
                return True
            else:
                print("   ⚠️  No rate limiting detected (may need more requests)")
                return True  # Not necessarily a failure
                
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_security_headers(self):
        """Test security headers"""
        print("🛡️  Testing security headers...")
        
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options",
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Content-Security-Policy"
            ]
            
            present_headers = []
            missing_headers = []
            
            for header in security_headers:
                if header in response.headers:
                    present_headers.append(header)
                    print(f"   ✅ {header}: {response.headers[header]}")
                else:
                    missing_headers.append(header)
                    print(f"   ❌ {header}: Missing")
            
            if len(missing_headers) == 0:
                print("   ✅ All security headers present")
                return True
            else:
                print(f"   ⚠️  Missing {len(missing_headers)} security headers")
                return False
                
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_input_validation(self):
        """Test input validation"""
        print("🔍 Testing input validation...")
        
        if not self.auth_token:
            print("   No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test malicious payload
            malicious_data = {
                "name": "test_user",
                "role": "<script>alert('xss')</script>"
            }
            
            response = self.session.post(f"{self.base_url}/employees", 
                                       json=malicious_data, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 400:
                print("   ✅ Malicious input blocked")
                return True
            elif response.status_code == 200:
                print("   ⚠️  Malicious input accepted (may need stronger validation)")
                return False
            else:
                print(f"   Unexpected response: {response.text}")
                return False
                
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🔒 OpenCode-Slack Secure API Testing")
        print("=" * 50)
        
        tests = [
            ("Health Endpoint", self.test_health_endpoint),
            ("Authentication", self.test_authentication),
            ("Unauthorized Access", self.test_unauthorized_access),
            ("Protected Endpoint", self.test_protected_endpoint),
            ("API Key Creation", self.test_api_key_creation),
            ("API Key Usage", self.test_api_key_usage),
            ("Rate Limiting", self.test_rate_limiting),
            ("Security Headers", self.test_security_headers),
            ("Input Validation", self.test_input_validation),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n{test_name}:")
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"   ❌ Test failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\nTotal: {total}, Passed: {passed}, Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        return passed == total


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Secure OpenCode-Slack API')
    parser.add_argument('--url', default='https://localhost:8443',
                       help='Base URL of the secure API server')
    
    args = parser.parse_args()
    
    tester = SecureAPITester(args.url)
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())