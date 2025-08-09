#!/usr/bin/env python3
"""
Comprehensive Authentication Load Testing Suite for OpenCode-Slack
Tests all authentication mechanisms under extreme load conditions for 100% production readiness.
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import random
import statistics
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any
from unittest.mock import Mock, patch, MagicMock
import requests
import jwt
import hashlib
import secrets

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.security.auth import AuthManager, auth_manager, require_auth, optional_auth
from src.security.rate_limiter import RateLimiter, rate_limiter
from src.server import OpencodeSlackServer
from src.enhanced_server import EnhancedOpencodeSlackServer


class AuthenticationLoadTestSuite(unittest.TestCase):
    """Comprehensive authentication load testing suite"""
    
    def setUp(self):
        """Set up comprehensive test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "auth_load_test.db")
        self.sessions_dir = os.path.join(self.temp_dir, "sessions")
        
        # Test configuration
        self.test_config = {
            'concurrent_users': 100,
            'stress_users': 500,
            'extreme_users': 1000,
            'requests_per_user': 50,
            'test_duration': 30,  # seconds
            'performance_targets': {
                'auth_response_time_ms': 20,
                'throughput_ops_per_sec': 5557,
                'success_rate_percent': 99.9,
                'concurrent_auth_limit': 100
            }
        }
        
        # Test results tracking
        self.test_results = {
            'jwt_authentication': [],
            'api_key_authentication': [],
            'authentication_integration': [],
            'security_under_load': [],
            'performance_metrics': [],
            'production_readiness': [],
            'security_validation': [],
            'system_integration': []
        }
        
        # Performance metrics
        self.performance_metrics = {
            'response_times': [],
            'throughput_measurements': [],
            'error_rates': [],
            'concurrent_users_handled': 0,
            'peak_ops_per_second': 0,
            'authentication_overhead': 0
        }
        
        # Initialize test server
        self._setup_test_server()
        
        print(f"🔐 Authentication Load Test Suite initialized")
        print(f"   Target: {self.test_config['concurrent_users']} concurrent users")
        print(f"   Performance target: <{self.test_config['performance_targets']['auth_response_time_ms']}ms response time")
        print(f"   Throughput target: {self.test_config['performance_targets']['throughput_ops_per_sec']} ops/sec")
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            if hasattr(self, 'server') and self.server:
                self.server.stop()
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def _setup_test_server(self):
        """Set up test server with authentication"""
        try:
            # Mock environment loading to avoid conflicts
            with patch.object(OpencodeSlackServer, '_load_environment'):
                self.server = OpencodeSlackServer(
                    host="localhost",
                    port=0,  # Use random available port
                    db_path=self.db_path,
                    sessions_dir=self.sessions_dir
                )
            
            # Get the test client
            self.client = self.server.app.test_client()
            self.client.testing = True
            
            # Initialize auth manager for testing
            self.auth_manager = AuthManager(
                secret_key="test_secret_key_for_load_testing",
                token_expiry_hours=24
            )
            
            print("✅ Test server initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize test server: {e}")
            self.server = None
            self.client = None
            self.auth_manager = None
    
    # ==================== JWT AUTHENTICATION LOAD TESTING ====================
    
    def test_jwt_authentication_under_load(self):
        """Test JWT token authentication under 100+ concurrent users"""
        print("\n🧪 Testing JWT authentication under load...")
        
        if not self.auth_manager:
            self.skipTest("Auth manager not available")
        
        try:
            # Create test users
            test_users = []
            for i in range(self.test_config['concurrent_users']):
                username = f"load_user_{i}"
                password = f"secure_password_{i}"
                self.auth_manager.create_user(username, password, ["user"], ["read", "write"])
                test_users.append((username, password))
            
            # Concurrent JWT authentication test
            def authenticate_user(user_data):
                username, password = user_data
                start_time = time.time()
                
                try:
                    # Authenticate and get JWT token
                    user = self.auth_manager.authenticate_user(username, password)
                    if user:
                        token = self.auth_manager.generate_jwt_token(username)
                        
                        # Verify token
                        payload = self.auth_manager.verify_jwt_token(token)
                        
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000  # ms
                        
                        return {
                            'success': payload is not None,
                            'response_time_ms': response_time,
                            'username': username,
                            'token_length': len(token) if token else 0
                        }
                    else:
                        return {'success': False, 'error': 'Authentication failed'}
                        
                except Exception as e:
                    return {'success': False, 'error': str(e)}
            
            # Execute concurrent authentication
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                futures = [executor.submit(authenticate_user, user) for user in test_users]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            end_time = time.time()
            
            # Analyze results
            successful_auths = [r for r in results if r.get('success')]
            failed_auths = [r for r in results if not r.get('success')]
            
            if successful_auths:
                response_times = [r['response_time_ms'] for r in successful_auths]
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)
                p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            else:
                avg_response_time = max_response_time = min_response_time = p95_response_time = 0
            
            total_time = end_time - start_time
            throughput = len(successful_auths) / total_time if total_time > 0 else 0
            success_rate = len(successful_auths) / len(results) * 100 if results else 0
            
            # Performance validation
            performance_target_met = (
                avg_response_time <= self.test_config['performance_targets']['auth_response_time_ms'] and
                success_rate >= self.test_config['performance_targets']['success_rate_percent'] and
                len(successful_auths) >= self.test_config['concurrent_users'] * 0.95
            )
            
            self.test_results['jwt_authentication'].append({
                'test': 'jwt_concurrent_load',
                'success': performance_target_met,
                'metrics': {
                    'concurrent_users': len(test_users),
                    'successful_auths': len(successful_auths),
                    'failed_auths': len(failed_auths),
                    'success_rate_percent': success_rate,
                    'avg_response_time_ms': avg_response_time,
                    'max_response_time_ms': max_response_time,
                    'min_response_time_ms': min_response_time,
                    'p95_response_time_ms': p95_response_time,
                    'throughput_auths_per_sec': throughput,
                    'total_duration_sec': total_time
                },
                'timestamp': datetime.now()
            })
            
            # Update performance metrics
            self.performance_metrics['response_times'].extend(response_times)
            self.performance_metrics['concurrent_users_handled'] = max(
                self.performance_metrics['concurrent_users_handled'], 
                len(successful_auths)
            )
            self.performance_metrics['peak_ops_per_second'] = max(
                self.performance_metrics['peak_ops_per_second'],
                throughput
            )
            
            print(f"   ✅ JWT Load Test: {len(successful_auths)}/{len(test_users)} successful")
            print(f"   📊 Avg Response Time: {avg_response_time:.2f}ms (target: <{self.test_config['performance_targets']['auth_response_time_ms']}ms)")
            print(f"   🚀 Throughput: {throughput:.2f} auths/sec")
            print(f"   📈 Success Rate: {success_rate:.2f}%")
            
            self.assertTrue(performance_target_met, 
                          f"JWT authentication performance targets not met: {avg_response_time:.2f}ms avg response time")
            
        except Exception as e:
            self.test_results['jwt_authentication'].append({
                'test': 'jwt_concurrent_load',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            })
            self.fail(f"JWT load test failed: {e}")
    
    def test_jwt_token_refresh_under_stress(self):
        """Test JWT token refresh mechanisms under stress conditions"""
        print("\n🧪 Testing JWT token refresh under stress...")
        
        if not self.auth_manager:
            self.skipTest("Auth manager not available")
        
        try:
            # Create test user
            username = "refresh_test_user"
            password = "secure_password"
            self.auth_manager.create_user(username, password, ["user"], ["read", "write"])
            
            # Generate initial token
            initial_token = self.auth_manager.generate_jwt_token(username)
            
            # Stress test token refresh
            def refresh_token_stress():
                results = []
                for i in range(100):  # 100 refresh operations per thread
                    start_time = time.time()
                    try:
                        # Verify current token
                        payload = self.auth_manager.verify_jwt_token(initial_token)
                        if payload:
                            # Generate new token
                            new_token = self.auth_manager.generate_jwt_token(username)
                            # Verify new token
                            new_payload = self.auth_manager.verify_jwt_token(new_token)
                            
                            end_time = time.time()
                            response_time = (end_time - start_time) * 1000
                            
                            results.append({
                                'success': new_payload is not None,
                                'response_time_ms': response_time,
                                'iteration': i
                            })
                        else:
                            results.append({'success': False, 'error': 'Token verification failed'})
                    except Exception as e:
                        results.append({'success': False, 'error': str(e)})
                
                return results
            
            # Execute concurrent refresh operations
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(refresh_token_stress) for _ in range(10)]
                all_results = []
                for future in concurrent.futures.as_completed(futures):
                    all_results.extend(future.result())
            end_time = time.time()
            
            # Analyze results
            successful_refreshes = [r for r in all_results if r.get('success')]
            failed_refreshes = [r for r in all_results if not r.get('success')]
            
            if successful_refreshes:
                response_times = [r['response_time_ms'] for r in successful_refreshes]
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
            else:
                avg_response_time = max_response_time = 0
            
            total_time = end_time - start_time
            refresh_throughput = len(successful_refreshes) / total_time if total_time > 0 else 0
            success_rate = len(successful_refreshes) / len(all_results) * 100 if all_results else 0
            
            # Performance validation
            refresh_performance_ok = (
                avg_response_time <= self.test_config['performance_targets']['auth_response_time_ms'] * 1.5 and  # Allow 50% more time for refresh
                success_rate >= 95.0 and
                len(successful_refreshes) >= 900  # 90% of 1000 total operations
            )
            
            self.test_results['jwt_authentication'].append({
                'test': 'jwt_refresh_stress',
                'success': refresh_performance_ok,
                'metrics': {
                    'total_refresh_operations': len(all_results),
                    'successful_refreshes': len(successful_refreshes),
                    'failed_refreshes': len(failed_refreshes),
                    'success_rate_percent': success_rate,
                    'avg_response_time_ms': avg_response_time,
                    'max_response_time_ms': max_response_time,
                    'refresh_throughput_per_sec': refresh_throughput,
                    'total_duration_sec': total_time
                },
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ JWT Refresh Stress: {len(successful_refreshes)}/{len(all_results)} successful")
            print(f"   📊 Avg Response Time: {avg_response_time:.2f}ms")
            print(f"   🚀 Refresh Throughput: {refresh_throughput:.2f} ops/sec")
            print(f"   📈 Success Rate: {success_rate:.2f}%")
            
            self.assertTrue(refresh_performance_ok, 
                          f"JWT refresh performance targets not met: {success_rate:.2f}% success rate")
            
        except Exception as e:
            self.test_results['jwt_authentication'].append({
                'test': 'jwt_refresh_stress',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            })
            self.fail(f"JWT refresh stress test failed: {e}")
    
    def test_jwt_performance_overhead_measurement(self):
        """Measure JWT authentication overhead on system performance"""
        print("\n🧪 Measuring JWT authentication overhead...")
        
        if not self.auth_manager:
            self.skipTest("Auth manager not available")
        
        try:
            # Create test user
            username = "overhead_test_user"
            password = "secure_password"
            self.auth_manager.create_user(username, password, ["user"], ["read", "write"])
            token = self.auth_manager.generate_jwt_token(username)
            
            # Baseline performance (no authentication)
            def baseline_operation():
                start_time = time.time()
                # Simulate basic operation
                result = {"status": "ok", "data": list(range(100))}
                end_time = time.time()
                return (end_time - start_time) * 1000
            
            # Authenticated operation
            def authenticated_operation():
                start_time = time.time()
                # Verify token
                payload = self.auth_manager.verify_jwt_token(token)
                if payload:
                    # Simulate same operation
                    result = {"status": "ok", "data": list(range(100))}
                end_time = time.time()
                return (end_time - start_time) * 1000
            
            # Measure baseline performance
            baseline_times = []
            for _ in range(1000):
                baseline_times.append(baseline_operation())
            
            # Measure authenticated performance
            auth_times = []
            for _ in range(1000):
                auth_times.append(authenticated_operation())
            
            # Calculate overhead
            avg_baseline = statistics.mean(baseline_times)
            avg_auth = statistics.mean(auth_times)
            overhead_ms = avg_auth - avg_baseline
            overhead_percent = (overhead_ms / avg_baseline) * 100 if avg_baseline > 0 else 0
            
            # Performance validation (overhead should be minimal)
            overhead_acceptable = overhead_percent <= 10.0  # Less than 10% overhead
            
            self.test_results['jwt_authentication'].append({
                'test': 'jwt_performance_overhead',
                'success': overhead_acceptable,
                'metrics': {
                    'baseline_avg_ms': avg_baseline,
                    'authenticated_avg_ms': avg_auth,
                    'overhead_ms': overhead_ms,
                    'overhead_percent': overhead_percent,
                    'operations_tested': 1000
                },
                'timestamp': datetime.now()
            })
            
            # Update performance metrics
            self.performance_metrics['authentication_overhead'] = overhead_percent
            
            print(f"   ✅ JWT Overhead: {overhead_ms:.3f}ms ({overhead_percent:.2f}%)")
            print(f"   📊 Baseline: {avg_baseline:.3f}ms, Authenticated: {avg_auth:.3f}ms")
            
            self.assertTrue(overhead_acceptable, 
                          f"JWT authentication overhead too high: {overhead_percent:.2f}%")
            
        except Exception as e:
            self.test_results['jwt_authentication'].append({
                'test': 'jwt_performance_overhead',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            })
            self.fail(f"JWT overhead measurement failed: {e}")
    
    # ==================== API KEY AUTHENTICATION TESTING ====================
    
    def test_api_key_authentication_concurrent_load(self):
        """Test API key authentication with 500+ concurrent requests"""
        print("\n🧪 Testing API key authentication under concurrent load...")
        
        if not self.auth_manager:
            self.skipTest("Auth manager not available")
        
        try:
            # Generate test API keys
            api_keys = []
            for i in range(50):  # 50 API keys, each will be used by 10 concurrent requests
                key_name = f"load_test_key_{i}"
                api_key = self.auth_manager.generate_api_key(
                    key_name, 
                    permissions=["read", "write"], 
                    expires_days=1
                )
                api_keys.append((api_key, key_name))
            
            # Concurrent API key authentication test
            def authenticate_with_api_key(key_data):
                api_key, key_name = key_data
                results = []
                
                # Each API key performs multiple operations
                for i in range(10):
                    start_time = time.time()
                    try:
                        # Verify API key
                        key_info = self.auth_manager.verify_api_key(api_key)
                        
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        results.append({
                            'success': key_info is not None,
                            'response_time_ms': response_time,
                            'key_name': key_name,
                            'iteration': i
                        })
                        
                    except Exception as e:
                        results.append({
                            'success': False,
                            'error': str(e),
                            'key_name': key_name,
                            'iteration': i
                        })
                
                return results
            
            # Execute concurrent API key operations
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                futures = [executor.submit(authenticate_with_api_key, key_data) for key_data in api_keys]
                all_results = []
                for future in concurrent.futures.as_completed(futures):
                    all_results.extend(future.result())
            end_time = time.time()
            
            # Analyze results
            successful_auths = [r for r in all_results if r.get('success')]
            failed_auths = [r for r in all_results if not r.get('success')]
            
            if successful_auths:
                response_times = [r['response_time_ms'] for r in successful_auths]
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                p95_response_time = statistics.quantiles(response_times, n=20)[18]
            else:
                avg_response_time = max_response_time = p95_response_time = 0
            
            total_time = end_time - start_time
            throughput = len(successful_auths) / total_time if total_time > 0 else 0
            success_rate = len(successful_auths) / len(all_results) * 100 if all_results else 0
            
            # Performance validation
            api_key_performance_ok = (
                avg_response_time <= self.test_config['performance_targets']['auth_response_time_ms'] and
                success_rate >= self.test_config['performance_targets']['success_rate_percent'] and
                len(successful_auths) >= 450  # 90% of 500 operations
            )
            
            self.test_results['api_key_authentication'].append({
                'test': 'api_key_concurrent_load',
                'success': api_key_performance_ok,
                'metrics': {
                    'total_operations': len(all_results),
                    'successful_auths': len(successful_auths),
                    'failed_auths': len(failed_auths),
                    'success_rate_percent': success_rate,
                    'avg_response_time_ms': avg_response_time,
                    'max_response_time_ms': max_response_time,
                    'p95_response_time_ms': p95_response_time,
                    'throughput_auths_per_sec': throughput,
                    'total_duration_sec': total_time,
                    'api_keys_tested': len(api_keys)
                },
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ API Key Load Test: {len(successful_auths)}/{len(all_results)} successful")
            print(f"   📊 Avg Response Time: {avg_response_time:.2f}ms")
            print(f"   🚀 Throughput: {throughput:.2f} auths/sec")
            print(f"   📈 Success Rate: {success_rate:.2f}%")
            
            self.assertTrue(api_key_performance_ok, 
                          f"API key authentication performance targets not met")
            
        except Exception as e:
            self.test_results['api_key_authentication'].append({
                'test': 'api_key_concurrent_load',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            })
            self.fail(f"API key load test failed: {e}")
    
    def test_api_key_rate_limiting_under_load(self):
        """Test API key rate limiting under high load"""
        print("\n🧪 Testing API key rate limiting under load...")
        
        if not self.auth_manager:
            self.skipTest("Auth manager not available")
        
        try:
            # Create rate limiter for testing
            test_rate_limiter = RateLimiter()
            
            # Generate API key for rate limiting test
            api_key = self.auth_manager.generate_api_key(
                "rate_limit_test_key",
                permissions=["read"],
                expires_days=1
            )
            
            # Test rate limiting with burst requests
            def burst_requests():
                results = []
                client_id = f"api_key:rate_limit_test_key"
                
                # Send burst of requests (more than rate limit)
                for i in range(150):  # Exceed typical rate limit
                    start_time = time.time()
                    allowed, info = test_rate_limiter.is_allowed(client_id, "/test/endpoint", limit=100)
                    end_time = time.time()
                    
                    results.append({
                        'allowed': allowed,
                        'response_time_ms': (end_time - start_time) * 1000,
                        'remaining': info.get('remaining', 0),
                        'limit': info.get('limit', 0),
                        'request_number': i
                    })
                
                return results
            
            # Execute rate limiting test
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(burst_requests) for _ in range(5)]
                all_results = []
                for future in concurrent.futures.as_completed(futures):
                    all_results.extend(future.result())
            end_time = time.time()
            
            # Analyze rate limiting effectiveness
            allowed_requests = [r for r in all_results if r['allowed']]
            blocked_requests = [r for r in all_results if not r['allowed']]
            
            rate_limiting_effective = (
                len(blocked_requests) > 0 and  # Some requests should be blocked
                len(allowed_requests) <= 500 and  # Should not exceed reasonable limit
                len(blocked_requests) >= len(all_results) * 0.1  # At least 10% blocked
            )
            
            if allowed_requests:
                avg_response_time = statistics.mean([r['response_time_ms'] for r in allowed_requests])
            else:
                avg_response_time = 0
            
            self.test_results['api_key_authentication'].append({
                'test': 'api_key_rate_limiting',
                'success': rate_limiting_effective,
                'metrics': {
                    'total_requests': len(all_results),
                    'allowed_requests': len(allowed_requests),
                    'blocked_requests': len(blocked_requests),
                    'blocking_rate_percent': len(blocked_requests) / len(all_results) * 100,
                    'avg_response_time_ms': avg_response_time,
                    'rate_limiting_effective': rate_limiting_effective
                },
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Rate Limiting Test: {len(blocked_requests)}/{len(all_results)} blocked")
            print(f"   🚫 Blocking Rate: {len(blocked_requests) / len(all_results) * 100:.2f}%")
            print(f"   📊 Avg Response Time: {avg_response_time:.2f}ms")
            
            self.assertTrue(rate_limiting_effective, 
                          "Rate limiting not effective under load")
            
        except Exception as e:
            self.test_results['api_key_authentication'].append({
                'test': 'api_key_rate_limiting',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            })
            self.fail(f"API key rate limiting test failed: {e}")
    
    # ==================== SECURITY UNDER LOAD TESTS ====================
    
    def test_input_validation_under_stress(self):
        """Test input validation performance under concurrent operations"""
        print("\n🧪 Testing input validation under stress...")
        
        if not self.auth_manager:
            self.skipTest("Auth manager not available")
        
        try:
            # Malicious input patterns
            malicious_inputs = [
                "'; DROP TABLE employees; --",  # SQL injection
                "<script>alert('xss')</script>",  # XSS
                "../../etc/passwd",  # Path traversal
                "admin' OR '1'='1",  # SQL injection variant
                "<img src=x onerror=alert(1)>",  # XSS variant
                "$(rm -rf /)",  # Command injection
                "' UNION SELECT * FROM users --",  # SQL injection
                "javascript:alert('xss')",  # JavaScript injection
                "../../../windows/system32",  # Path traversal variant
                "1; cat /etc/passwd",  # Command injection variant
            ]
            
            # Test input validation under load
            def validate_malicious_input(input_data):
                results = []
                
                for i in range(10):  # 10 validation attempts per thread
                    start_time = time.time()
                    try:
                        # Test user creation with malicious input
                        success = self.auth_manager.create_user(
                            input_data, 
                            "password123", 
                            ["user"], 
                            ["read"]
                        )
                        
                        # Should fail for malicious input
                        validation_effective = not success
                        
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        results.append({
                            'validation_effective': validation_effective,
                            'response_time_ms': response_time,
                            'input_blocked': not success,
                            'iteration': i
                        })
                        
                    except Exception as e:
                        # Exception is good - means validation caught the malicious input
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        results.append({
                            'validation_effective': True,
                            'response_time_ms': response_time,
                            'input_blocked': True,
                            'exception': str(e),
                            'iteration': i
                        })
                
                return results
            
            # Execute concurrent validation tests
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(validate_malicious_input, input_data) 
                          for input_data in malicious_inputs]
                all_results = []
                for future in concurrent.futures.as_completed(futures):
                    all_results.extend(future.result())
            end_time = time.time()
            
            # Analyze validation effectiveness
            effective_validations = [r for r in all_results if r.get('validation_effective')]
            blocked_inputs = [r for r in all_results if r.get('input_blocked')]
            
            if all_results:
                response_times = [r['response_time_ms'] for r in all_results]
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
            else:
                avg_response_time = max_response_time = 0
            
            validation_effectiveness = len(effective_validations) / len(all_results) * 100 if all_results else 0
            blocking_rate = len(blocked_inputs) / len(all_results) * 100 if all_results else 0
            
            # Security validation (should block 100% of malicious inputs)
            security_effective = (
                validation_effectiveness >= 100.0 and
                blocking_rate >= 100.0 and
                avg_response_time <= 50.0  # Validation should be fast
            )
            
            self.test_results['security_under_load'].append({
                'test': 'input_validation_stress',
                'success': security_effective,
                'metrics': {
                    'total_validations': len(all_results),
                    'effective_validations': len(effective_validations),
                    'blocked_inputs': len(blocked_inputs),
                    'validation_effectiveness_percent': validation_effectiveness,
                    'blocking_rate_percent': blocking_rate,
                    'avg_response_time_ms': avg_response_time,
                    'max_response_time_ms': max_response_time,
                    'malicious_patterns_tested': len(malicious_inputs)
                },
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Input Validation: {validation_effectiveness:.1f}% effective")
            print(f"   🚫 Blocking Rate: {blocking_rate:.1f}%")
            print(f"   📊 Avg Response Time: {avg_response_time:.2f}ms")
            
            self.assertTrue(security_effective, 
                          f"Input validation not 100% effective: {validation_effectiveness:.1f}%")
            
        except Exception as e:
            self.test_results['security_under_load'].append({
                'test': 'input_validation_stress',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            })
            self.fail(f"Input validation stress test failed: {e}")
    
    def test_brute_force_protection_under_load(self):
        """Test brute force protection under extreme load"""
        print("\n🧪 Testing brute force protection under load...")
        
        if not self.auth_manager:
            self.skipTest("Auth manager not available")
        
        try:
            # Create target user
            target_username = "brute_force_target"
            correct_password = "correct_password_123"
            self.auth_manager.create_user(target_username, correct_password, ["user"], ["read"])
            
            # Brute force attack simulation
            def brute_force_attack():
                results = []
                wrong_passwords = [
                    "password123", "admin", "123456", "password", "qwerty",
                    "letmein", "welcome", "monkey", "dragon", "master"
                ]
                
                for i in range(50):  # 50 attempts per thread
                    start_time = time.time()
                    try:
                        # Use wrong password
                        wrong_password = random.choice(wrong_passwords)
                        user = self.auth_manager.authenticate_user(target_username, wrong_password)
                        
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        results.append({
                            'authentication_failed': user is None,
                            'response_time_ms': response_time,
                            'attempt_number': i,
                            'password_used': wrong_password
                        })
                        
                    except Exception as e:
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        results.append({
                            'authentication_failed': True,
                            'response_time_ms': response_time,
                            'attempt_number': i,
                            'exception': str(e)
                        })
                
                return results
            
            # Execute concurrent brute force attempts
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
                futures = [executor.submit(brute_force_attack) for _ in range(20)]
                all_results = []
                for future in concurrent.futures.as_completed(futures):
                    all_results.extend(future.result())
            end_time = time.time()
            
            # Analyze brute force protection
            failed_attempts = [r for r in all_results if r.get('authentication_failed')]
            successful_attempts = [r for r in all_results if not r.get('authentication_failed')]
            
            if all_results:
                response_times = [r['response_time_ms'] for r in all_results]
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
            else:
                avg_response_time = max_response_time = 0
            
            protection_rate = len(failed_attempts) / len(all_results) * 100 if all_results else 0
            
            # Brute force protection should block all wrong attempts
            protection_effective = (
                protection_rate >= 100.0 and  # All wrong attempts should fail
                len(successful_attempts) == 0 and  # No successful brute force
                avg_response_time <= 100.0  # Should not cause significant delay
            )
            
            self.test_results['security_under_load'].append({
                'test': 'brute_force_protection',
                'success': protection_effective,
                'metrics': {
                    'total_attempts': len(all_results),
                    'failed_attempts': len(failed_attempts),
                    'successful_attempts': len(successful_attempts),
                    'protection_rate_percent': protection_rate,
                    'avg_response_time_ms': avg_response_time,
                    'max_response_time_ms': max_response_time,
                    'concurrent_attackers': 20
                },
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Brute Force Protection: {protection_rate:.1f}% effective")
            print(f"   🚫 Blocked Attempts: {len(failed_attempts)}/{len(all_results)}")
            print(f"   📊 Avg Response Time: {avg_response_time:.2f}ms")
            
            self.assertTrue(protection_effective, 
                          f"Brute force protection not 100% effective: {protection_rate:.1f}%")
            
        except Exception as e:
            self.test_results['security_under_load'].append({
                'test': 'brute_force_protection',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            })
            self.fail(f"Brute force protection test failed: {e}")
    
    # ==================== COMPREHENSIVE TESTING ORCHESTRATION ====================
    
    def test_comprehensive_authentication_load_validation(self):
        """Run comprehensive authentication load testing for 100% production readiness"""
        print("\n🚀 COMPREHENSIVE AUTHENTICATION LOAD TESTING")
        print("=" * 80)
        print(f"🎯 Target: 100% Production Readiness Validation")
        print(f"📊 Performance Targets:")
        print(f"   • Response Time: <{self.test_config['performance_targets']['auth_response_time_ms']}ms")
        print(f"   • Throughput: {self.test_config['performance_targets']['throughput_ops_per_sec']} ops/sec")
        print(f"   • Success Rate: {self.test_config['performance_targets']['success_rate_percent']}%")
        print(f"   • Concurrent Users: {self.test_config['concurrent_users']}+")
        print("=" * 80)
        
        # Execute all authentication load tests
        test_methods = [
            # JWT Authentication Load Testing
            self.test_jwt_authentication_under_load,
            self.test_jwt_token_refresh_under_stress,
            self.test_jwt_performance_overhead_measurement,
            
            # API Key Authentication Testing
            self.test_api_key_authentication_concurrent_load,
            self.test_api_key_rate_limiting_under_load,
            
            # Security Under Load
            self.test_input_validation_under_stress,
            self.test_brute_force_protection_under_load,
        ]
        
        # Execute all tests
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"   ❌ Test {test_method.__name__} failed: {e}")
        
        # Generate comprehensive report
        self._generate_comprehensive_authentication_report()
    
    def _generate_comprehensive_authentication_report(self):
        """Generate comprehensive authentication load testing report"""
        print("\n📊 COMPREHENSIVE AUTHENTICATION LOAD TESTING REPORT")
        print("=" * 80)
        
        total_tests = 0
        passed_tests = 0
        critical_failures = []
        
        # Analyze results by category
        for category, results in self.test_results.items():
            if not results:
                continue
                
            print(f"\n🔍 {category.replace('_', ' ').title()}:")
            category_passed = 0
            
            for result in results:
                total_tests += 1
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                
                if 'metrics' in result:
                    metrics = result['metrics']
                    details = f"{result['test']}"
                    
                    # Add key metrics to display
                    if 'success_rate_percent' in metrics:
                        details += f" (Success: {metrics['success_rate_percent']:.1f}%)"
                    if 'avg_response_time_ms' in metrics:
                        details += f" (Avg: {metrics['avg_response_time_ms']:.2f}ms)"
                    if 'throughput_auths_per_sec' in metrics:
                        details += f" (Throughput: {metrics['throughput_auths_per_sec']:.1f} ops/sec)"
                    
                    print(f"   {status} {details}")
                else:
                    print(f"   {status} {result['test']}")
                    if 'error' in result:
                        print(f"       Error: {result['error']}")
                
                if result['success']:
                    passed_tests += 1
                    category_passed += 1
                else:
                    critical_failures.append(f"{category}: {result['test']}")
            
            category_rate = category_passed / len(results) if results else 0
            print(f"   📈 Category Success Rate: {category_rate:.1%} ({category_passed}/{len(results)})")
        
        # Overall performance metrics
        print(f"\n📈 PERFORMANCE METRICS SUMMARY:")
        if self.performance_metrics['response_times']:
            avg_response_time = statistics.mean(self.performance_metrics['response_times'])
            p95_response_time = statistics.quantiles(self.performance_metrics['response_times'], n=20)[18]
            print(f"   • Average Response Time: {avg_response_time:.2f}ms")
            print(f"   • 95th Percentile Response Time: {p95_response_time:.2f}ms")
        
        print(f"   • Peak Throughput: {self.performance_metrics['peak_ops_per_second']:.2f} ops/sec")
        print(f"   • Max Concurrent Users Handled: {self.performance_metrics['concurrent_users_handled']}")
        print(f"   • Authentication Overhead: {self.performance_metrics['authentication_overhead']:.2f}%")
        
        # Overall assessment
        overall_rate = passed_tests / total_tests if total_tests > 0 else 0
        print(f"\n📈 OVERALL SUCCESS RATE: {overall_rate:.1%} ({passed_tests}/{total_tests})")
        
        # Production readiness assessment
        print(f"\n🎯 PRODUCTION READINESS ASSESSMENT:")
        
        # Check if all performance targets are met
        performance_targets_met = True
        target_checks = []
        
        if self.performance_metrics['response_times']:
            avg_response_time = statistics.mean(self.performance_metrics['response_times'])
            response_time_ok = avg_response_time <= self.test_config['performance_targets']['auth_response_time_ms']
            target_checks.append(("Response Time", response_time_ok, f"{avg_response_time:.2f}ms"))
            performance_targets_met &= response_time_ok
        
        throughput_ok = self.performance_metrics['peak_ops_per_second'] >= self.test_config['performance_targets']['throughput_ops_per_sec'] * 0.8
        target_checks.append(("Throughput", throughput_ok, f"{self.performance_metrics['peak_ops_per_second']:.2f} ops/sec"))
        performance_targets_met &= throughput_ok
        
        concurrent_users_ok = self.performance_metrics['concurrent_users_handled'] >= self.test_config['concurrent_users'] * 0.95
        target_checks.append(("Concurrent Users", concurrent_users_ok, f"{self.performance_metrics['concurrent_users_handled']} users"))
        performance_targets_met &= concurrent_users_ok
        
        overhead_ok = self.performance_metrics['authentication_overhead'] <= 10.0
        target_checks.append(("Auth Overhead", overhead_ok, f"{self.performance_metrics['authentication_overhead']:.2f}%"))
        performance_targets_met &= overhead_ok
        
        # Display target check results
        for target_name, target_met, value in target_checks:
            status = "✅" if target_met else "❌"
            print(f"   {status} {target_name}: {value}")
        
        # Final production readiness verdict
        production_ready = overall_rate >= 0.95 and performance_targets_met and len(critical_failures) == 0
        
        if production_ready:
            print(f"\n🎉 PRODUCTION READINESS: ✅ APPROVED")
            print(f"   🚀 System is ready for enterprise deployment")
            print(f"   🔐 Authentication system meets all performance and security requirements")
            print(f"   📊 All load testing targets achieved")
        else:
            print(f"\n🚨 PRODUCTION READINESS: ❌ NOT APPROVED")
            print(f"   ⚠️  Critical issues must be resolved before production deployment")
            
            if overall_rate < 0.95:
                print(f"   • Overall success rate too low: {overall_rate:.1%} (required: 95%+)")
            
            if not performance_targets_met:
                print(f"   • Performance targets not met")
                for target_name, target_met, value in target_checks:
                    if not target_met:
                        print(f"     - {target_name}: {value}")
            
            if critical_failures:
                print(f"   • Critical test failures:")
                for failure in critical_failures[:5]:  # Show first 5
                    print(f"     - {failure}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if production_ready:
            print(f"   ✅ System approved for production deployment")
            print(f"   🔄 Continue monitoring authentication performance in production")
            print(f"   📈 Consider implementing additional monitoring for sustained load")
        else:
            print(f"   🔧 Address critical failures before production deployment")
            print(f"   📊 Optimize authentication performance to meet targets")
            print(f"   🔍 Conduct additional load testing after fixes")
        
        # Save detailed report
        report_data = {
            'overall_success_rate': overall_rate,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'production_ready': production_ready,
            'performance_metrics': self.performance_metrics,
            'performance_targets': self.test_config['performance_targets'],
            'target_checks': {name: {'met': met, 'value': value} for name, met, value in target_checks},
            'test_results': self.test_results,
            'critical_failures': critical_failures,
            'timestamp': datetime.now().isoformat()
        }
        
        report_path = os.path.join(self.temp_dir, "authentication_load_test_report.json")
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        print(f"✅ Authentication load testing completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Final assertion for test framework
        self.assertTrue(production_ready, 
                       f"Authentication system not ready for production: {overall_rate:.1%} success rate")


if __name__ == '__main__':
    # Configure logging for test output
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run the comprehensive authentication load testing
    suite = unittest.TestLoader().loadTestsFromTestCase(AuthenticationLoadTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)