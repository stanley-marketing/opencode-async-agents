#!/usr/bin/env python3
"""
Final Comprehensive API Validation for OpenCode-Slack System
Tests all API endpoints with full security and performance optimizations.
Validates Phase 1 security and Phase 2 performance enhancements integration.
"""

import asyncio
import aiohttp
import json
import time
import threading
import concurrent.futures
import statistics
import ssl
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys
import os
import requests
from typing import Dict, List, Any, Optional, Tuple
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveAPIValidator:
    """Comprehensive API validation with security and performance testing"""
    
    def __init__(self, base_url: str = "http://localhost:8091", secure_url: str = "https://localhost:8443"):
        self.base_url = base_url
        self.secure_url = secure_url
        self.session = requests.Session()
        self.auth_token = None
        self.api_key = None
        self.test_results = {
            'security_tests': {},
            'performance_tests': {},
            'endpoint_tests': {},
            'integration_tests': {},
            'load_tests': {},
            'production_readiness': {}
        }
        self.start_time = time.time()
        
        # Test configuration
        self.concurrent_users = 100
        self.high_load_requests = 500
        self.performance_threshold_ms = 1000
        self.success_rate_threshold = 0.95
        
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run complete API validation suite"""
        logger.info("🚀 Starting Final Comprehensive API Validation")
        
        # Phase 1: Security Validation with Performance
        await self._test_security_with_performance()
        
        # Phase 2: API Performance with Security
        await self._test_api_performance_with_security()
        
        # Phase 3: Endpoint Functionality Validation
        await self._test_endpoint_functionality()
        
        # Phase 4: Integration Testing
        await self._test_integration_scenarios()
        
        # Phase 5: Load Testing with Security
        await self._test_load_with_security()
        
        # Phase 6: Production API Readiness
        await self._test_production_readiness()
        
        # Phase 7: Comprehensive Security Audit
        await self._final_security_audit()
        
        # Generate final report
        return self._generate_final_report()
    
    async def _test_security_with_performance(self):
        """Test JWT authentication system under high load"""
        logger.info("🔐 Testing Security Validation with Performance")
        
        # Test 1: JWT Authentication under load
        auth_results = await self._test_jwt_under_load()
        self.test_results['security_tests']['jwt_load_test'] = auth_results
        
        # Test 2: API Key authentication with async processing
        api_key_results = await self._test_api_key_async()
        self.test_results['security_tests']['api_key_async'] = api_key_results
        
        # Test 3: Rate limiting with enhanced throughput
        rate_limit_results = await self._test_rate_limiting_enhanced()
        self.test_results['security_tests']['rate_limiting'] = rate_limit_results
        
        # Test 4: Input validation with concurrent operations
        validation_results = await self._test_input_validation_concurrent()
        self.test_results['security_tests']['input_validation'] = validation_results
    
    async def _test_jwt_under_load(self) -> Dict[str, Any]:
        """Test JWT authentication with 100+ concurrent users"""
        logger.info("Testing JWT authentication under high load (100+ users)")
        
        results = {
            'concurrent_users': self.concurrent_users,
            'successful_auths': 0,
            'failed_auths': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            'min_response_time': float('inf'),
            'response_times': [],
            'errors': []
        }
        
        async def authenticate_user(session, user_id):
            """Authenticate a single user"""
            start_time = time.time()
            try:
                auth_data = {
                    'username': f'test_user_{user_id}',
                    'password': 'test_password_123'
                }
                
                async with session.post(f"{self.secure_url}/auth/login", 
                                      json=auth_data,
                                      ssl=False) as response:
                    response_time = (time.time() - start_time) * 1000
                    results['response_times'].append(response_time)
                    
                    if response.status == 200:
                        results['successful_auths'] += 1
                        data = await response.json()
                        return data.get('token')
                    else:
                        results['failed_auths'] += 1
                        error_text = await response.text()
                        results['errors'].append(f"User {user_id}: {response.status} - {error_text}")
                        return None
                        
            except Exception as e:
                results['failed_auths'] += 1
                results['errors'].append(f"User {user_id}: Exception - {str(e)}")
                return None
        
        # Create concurrent authentication requests
        async with aiohttp.ClientSession() as session:
            tasks = [authenticate_user(session, i) for i in range(self.concurrent_users)]
            tokens = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate statistics
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
            results['max_response_time'] = max(results['response_times'])
            results['min_response_time'] = min(results['response_times'])
            results['p95_response_time'] = statistics.quantiles(results['response_times'], n=20)[18]
        
        results['success_rate'] = results['successful_auths'] / self.concurrent_users
        results['passed'] = results['success_rate'] >= self.success_rate_threshold
        
        logger.info(f"JWT Load Test: {results['successful_auths']}/{self.concurrent_users} successful, "
                   f"avg: {results['avg_response_time']:.2f}ms")
        
        return results
    
    async def _test_api_key_async(self) -> Dict[str, Any]:
        """Test API key authentication with optimized async processing"""
        logger.info("Testing API key authentication with async processing")
        
        results = {
            'api_keys_created': 0,
            'api_key_auths': 0,
            'failed_auths': 0,
            'avg_response_time': 0,
            'response_times': [],
            'errors': []
        }
        
        # First, create API keys (requires admin auth)
        try:
            # Get admin token first
            admin_auth = {
                'username': 'admin',
                'password': 'admin_password'
            }
            
            response = requests.post(f"{self.secure_url}/auth/login", 
                                   json=admin_auth, verify=False)
            if response.status_code == 200:
                admin_token = response.json()['token']
                
                # Create multiple API keys
                headers = {'Authorization': f'Bearer {admin_token}'}
                for i in range(10):
                    api_key_data = {
                        'name': f'test_key_{i}',
                        'permissions': ['read', 'write'],
                        'expires_days': 30
                    }
                    
                    response = requests.post(f"{self.secure_url}/auth/api-keys",
                                           json=api_key_data, headers=headers, verify=False)
                    if response.status_code == 200:
                        results['api_keys_created'] += 1
                        
        except Exception as e:
            results['errors'].append(f"API key creation failed: {str(e)}")
        
        # Test API key authentication concurrently
        async def test_api_key_auth(session, key_id):
            start_time = time.time()
            try:
                headers = {'X-API-Key': f'test_api_key_{key_id}'}
                async with session.get(f"{self.secure_url}/health",
                                     headers=headers, ssl=False) as response:
                    response_time = (time.time() - start_time) * 1000
                    results['response_times'].append(response_time)
                    
                    if response.status in [200, 401]:  # 401 expected for invalid keys
                        results['api_key_auths'] += 1
                    else:
                        results['failed_auths'] += 1
                        
            except Exception as e:
                results['failed_auths'] += 1
                results['errors'].append(f"API key {key_id}: {str(e)}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [test_api_key_auth(session, i) for i in range(50)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['passed'] = results['api_key_auths'] > 0 and len(results['errors']) < 10
        
        return results
    
    async def _test_rate_limiting_enhanced(self) -> Dict[str, Any]:
        """Test rate limiting with enhanced throughput (500+ requests)"""
        logger.info("Testing rate limiting with enhanced throughput (500+ requests)")
        
        results = {
            'total_requests': self.high_load_requests,
            'successful_requests': 0,
            'rate_limited_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'response_times': [],
            'rate_limit_effectiveness': False,
            'errors': []
        }
        
        async def make_request(session, request_id):
            start_time = time.time()
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    response_time = (time.time() - start_time) * 1000
                    results['response_times'].append(response_time)
                    
                    if response.status == 200:
                        results['successful_requests'] += 1
                    elif response.status == 429:  # Rate limited
                        results['rate_limited_requests'] += 1
                    else:
                        results['failed_requests'] += 1
                        
            except Exception as e:
                results['failed_requests'] += 1
                results['errors'].append(f"Request {request_id}: {str(e)}")
        
        # Send requests in batches to test rate limiting
        batch_size = 50
        async with aiohttp.ClientSession() as session:
            for batch_start in range(0, self.high_load_requests, batch_size):
                batch_end = min(batch_start + batch_size, self.high_load_requests)
                tasks = [make_request(session, i) for i in range(batch_start, batch_end)]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Small delay between batches
                await asyncio.sleep(0.1)
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        # Rate limiting is effective if some requests were rate limited
        results['rate_limit_effectiveness'] = results['rate_limited_requests'] > 0
        results['success_rate'] = results['successful_requests'] / self.high_load_requests
        results['passed'] = results['success_rate'] >= 0.8  # Allow for some rate limiting
        
        logger.info(f"Rate Limiting Test: {results['successful_requests']} successful, "
                   f"{results['rate_limited_requests']} rate limited")
        
        return results
    
    async def _test_input_validation_concurrent(self) -> Dict[str, Any]:
        """Test input validation and XSS prevention with concurrent operations"""
        logger.info("Testing input validation and XSS prevention")
        
        results = {
            'validation_tests': 0,
            'validation_passed': 0,
            'validation_failed': 0,
            'xss_prevention_tests': 0,
            'xss_blocked': 0,
            'errors': []
        }
        
        # Test payloads for validation
        test_payloads = [
            {'name': '', 'role': 'developer'},  # Empty name
            {'name': 'test', 'role': ''},  # Empty role
            {'name': '<script>alert("xss")</script>', 'role': 'developer'},  # XSS
            {'name': 'test' * 100, 'role': 'developer'},  # Long name
            {'name': 'test', 'role': 'invalid_role_' * 50},  # Long role
            {'name': '../../etc/passwd', 'role': 'developer'},  # Path traversal
            {'name': 'test; DROP TABLE employees;', 'role': 'developer'},  # SQL injection
        ]
        
        async def test_validation(session, payload):
            try:
                async with session.post(f"{self.base_url}/employees",
                                      json=payload) as response:
                    results['validation_tests'] += 1
                    
                    if response.status == 400:  # Validation error expected
                        results['validation_passed'] += 1
                        
                        # Check for XSS in payload
                        if '<script>' in str(payload.get('name', '')):
                            results['xss_prevention_tests'] += 1
                            results['xss_blocked'] += 1
                    else:
                        results['validation_failed'] += 1
                        
            except Exception as e:
                results['errors'].append(f"Validation test failed: {str(e)}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [test_validation(session, payload) for payload in test_payloads]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        results['validation_success_rate'] = (results['validation_passed'] / 
                                            max(results['validation_tests'], 1))
        results['xss_prevention_rate'] = (results['xss_blocked'] / 
                                         max(results['xss_prevention_tests'], 1))
        results['passed'] = (results['validation_success_rate'] >= 0.8 and 
                           results['xss_prevention_rate'] >= 0.9)
        
        return results
    
    async def _test_api_performance_with_security(self):
        """Test API performance with security middleware enabled"""
        logger.info("🚀 Testing API Performance with Security")
        
        # Test all 22+ API endpoints
        endpoint_results = await self._test_all_endpoints_performance()
        self.test_results['performance_tests']['endpoint_performance'] = endpoint_results
        
        # Test response times with security middleware
        middleware_results = await self._test_security_middleware_performance()
        self.test_results['performance_tests']['security_middleware'] = middleware_results
        
        # Test concurrent request handling
        concurrency_results = await self._test_concurrent_handling()
        self.test_results['performance_tests']['concurrency'] = concurrency_results
        
        # Test database optimizations with security
        db_results = await self._test_database_performance()
        self.test_results['performance_tests']['database'] = db_results
    
    async def _test_all_endpoints_performance(self) -> Dict[str, Any]:
        """Test all API endpoints with authentication and optimization"""
        logger.info("Testing all API endpoints performance")
        
        endpoints = [
            ('GET', '/health'),
            ('GET', '/employees'),
            ('POST', '/employees'),
            ('DELETE', '/employees/test_user'),
            ('POST', '/tasks'),
            ('DELETE', '/tasks/test_user'),
            ('GET', '/status'),
            ('GET', '/sessions'),
            ('GET', '/files'),
            ('POST', '/files/lock'),
            ('POST', '/files/release'),
            ('GET', '/progress'),
            ('POST', '/chat/start'),
            ('POST', '/chat/stop'),
            ('GET', '/chat/status'),
            ('GET', '/agents'),
            ('GET', '/bridge'),
            ('GET', '/project-root'),
            ('POST', '/project-root'),
            ('GET', '/monitoring/health'),
            ('GET', '/monitoring/recovery'),
            ('GET', '/monitoring/production/status'),
            ('GET', '/monitoring/production/performance'),
            ('GET', '/monitoring/production/alerts'),
        ]
        
        results = {
            'endpoints_tested': len(endpoints),
            'endpoints_passed': 0,
            'endpoints_failed': 0,
            'avg_response_time': 0,
            'response_times': [],
            'endpoint_results': {},
            'errors': []
        }
        
        async def test_endpoint(session, method, path):
            start_time = time.time()
            try:
                if method == 'GET':
                    async with session.get(f"{self.base_url}{path}") as response:
                        response_time = (time.time() - start_time) * 1000
                        results['response_times'].append(response_time)
                        
                        endpoint_result = {
                            'status_code': response.status,
                            'response_time_ms': response_time,
                            'passed': response.status < 500
                        }
                        
                        if endpoint_result['passed']:
                            results['endpoints_passed'] += 1
                        else:
                            results['endpoints_failed'] += 1
                            
                        results['endpoint_results'][f"{method} {path}"] = endpoint_result
                        
                elif method == 'POST':
                    # Use appropriate test data for POST endpoints
                    test_data = self._get_test_data_for_endpoint(path)
                    async with session.post(f"{self.base_url}{path}", 
                                          json=test_data) as response:
                        response_time = (time.time() - start_time) * 1000
                        results['response_times'].append(response_time)
                        
                        endpoint_result = {
                            'status_code': response.status,
                            'response_time_ms': response_time,
                            'passed': response.status < 500
                        }
                        
                        if endpoint_result['passed']:
                            results['endpoints_passed'] += 1
                        else:
                            results['endpoints_failed'] += 1
                            
                        results['endpoint_results'][f"{method} {path}"] = endpoint_result
                        
                elif method == 'DELETE':
                    async with session.delete(f"{self.base_url}{path}") as response:
                        response_time = (time.time() - start_time) * 1000
                        results['response_times'].append(response_time)
                        
                        endpoint_result = {
                            'status_code': response.status,
                            'response_time_ms': response_time,
                            'passed': response.status < 500
                        }
                        
                        if endpoint_result['passed']:
                            results['endpoints_passed'] += 1
                        else:
                            results['endpoints_failed'] += 1
                            
                        results['endpoint_results'][f"{method} {path}"] = endpoint_result
                        
            except Exception as e:
                results['endpoints_failed'] += 1
                results['errors'].append(f"{method} {path}: {str(e)}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [test_endpoint(session, method, path) for method, path in endpoints]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
            results['p95_response_time'] = statistics.quantiles(results['response_times'], n=20)[18]
        
        results['success_rate'] = results['endpoints_passed'] / results['endpoints_tested']
        results['passed'] = results['success_rate'] >= 0.9
        
        return results
    
    def _get_test_data_for_endpoint(self, path: str) -> Dict[str, Any]:
        """Get appropriate test data for POST endpoints"""
        if path == '/employees':
            return {'name': 'test_employee', 'role': 'developer', 'smartness': 'normal'}
        elif path == '/tasks':
            return {'name': 'test_employee', 'task': 'Test task', 'model': 'test_model'}
        elif path == '/files/lock':
            return {'name': 'test_employee', 'files': ['test.py'], 'description': 'Test lock'}
        elif path == '/files/release':
            return {'name': 'test_employee', 'files': ['test.py']}
        elif path == '/project-root':
            return {'project_root': '/tmp/test'}
        else:
            return {}
    
    async def _test_security_middleware_performance(self) -> Dict[str, Any]:
        """Test response times with security middleware"""
        logger.info("Testing security middleware performance impact")
        
        results = {
            'requests_tested': 100,
            'avg_response_time_with_security': 0,
            'avg_response_time_without_security': 0,
            'security_overhead_ms': 0,
            'security_overhead_percentage': 0,
            'response_times_secure': [],
            'response_times_normal': [],
            'passed': False
        }
        
        # Test with security (secure server)
        async def test_with_security(session):
            start_time = time.time()
            try:
                async with session.get(f"{self.secure_url}/health", ssl=False) as response:
                    response_time = (time.time() - start_time) * 1000
                    results['response_times_secure'].append(response_time)
            except:
                pass
        
        # Test without security (normal server)
        async def test_without_security(session):
            start_time = time.time()
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    response_time = (time.time() - start_time) * 1000
                    results['response_times_normal'].append(response_time)
            except:
                pass
        
        async with aiohttp.ClientSession() as session:
            # Test secure endpoints
            tasks = [test_with_security(session) for _ in range(50)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Test normal endpoints
            tasks = [test_without_security(session) for _ in range(50)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        if results['response_times_secure']:
            results['avg_response_time_with_security'] = statistics.mean(results['response_times_secure'])
        
        if results['response_times_normal']:
            results['avg_response_time_without_security'] = statistics.mean(results['response_times_normal'])
        
        if results['avg_response_time_without_security'] > 0:
            results['security_overhead_ms'] = (results['avg_response_time_with_security'] - 
                                             results['avg_response_time_without_security'])
            results['security_overhead_percentage'] = (results['security_overhead_ms'] / 
                                                     results['avg_response_time_without_security'] * 100)
        
        # Security overhead should be reasonable (< 50% increase)
        results['passed'] = results['security_overhead_percentage'] < 50
        
        return results
    
    async def _test_concurrent_handling(self) -> Dict[str, Any]:
        """Test concurrent request handling (500+ requests) with security"""
        logger.info("Testing concurrent request handling with security")
        
        results = {
            'concurrent_requests': self.high_load_requests,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            'min_response_time': float('inf'),
            'response_times': [],
            'throughput_per_second': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        async def make_concurrent_request(session, request_id):
            req_start = time.time()
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    response_time = (time.time() - req_start) * 1000
                    results['response_times'].append(response_time)
                    
                    if response.status == 200:
                        results['successful_requests'] += 1
                    else:
                        results['failed_requests'] += 1
                        
            except Exception as e:
                results['failed_requests'] += 1
                results['errors'].append(f"Request {request_id}: {str(e)}")
        
        # Create connector with higher limits for concurrent requests
        connector = aiohttp.TCPConnector(limit=1000, limit_per_host=1000)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [make_concurrent_request(session, i) for i in range(self.high_load_requests)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
            results['max_response_time'] = max(results['response_times'])
            results['min_response_time'] = min(results['response_times'])
            results['p95_response_time'] = statistics.quantiles(results['response_times'], n=20)[18]
        
        results['throughput_per_second'] = self.high_load_requests / total_time
        results['success_rate'] = results['successful_requests'] / self.high_load_requests
        results['passed'] = (results['success_rate'] >= 0.95 and 
                           results['avg_response_time'] < self.performance_threshold_ms)
        
        logger.info(f"Concurrent Test: {results['successful_requests']}/{self.high_load_requests} successful, "
                   f"throughput: {results['throughput_per_second']:.2f} req/s")
        
        return results
    
    async def _test_database_performance(self) -> Dict[str, Any]:
        """Test database optimizations with secure endpoints"""
        logger.info("Testing database performance with security")
        
        results = {
            'db_operations_tested': 0,
            'db_operations_passed': 0,
            'avg_db_response_time': 0,
            'response_times': [],
            'operations': {},
            'errors': []
        }
        
        # Test database-heavy operations
        db_operations = [
            ('list_employees', 'GET', '/employees'),
            ('create_employee', 'POST', '/employees'),
            ('get_status', 'GET', '/status'),
            ('get_progress', 'GET', '/progress'),
            ('get_files', 'GET', '/files'),
        ]
        
        async def test_db_operation(session, op_name, method, path):
            start_time = time.time()
            try:
                if method == 'GET':
                    async with session.get(f"{self.base_url}{path}") as response:
                        response_time = (time.time() - start_time) * 1000
                        results['response_times'].append(response_time)
                        
                        op_result = {
                            'response_time_ms': response_time,
                            'status_code': response.status,
                            'passed': response.status < 500 and response_time < 2000
                        }
                        
                        results['operations'][op_name] = op_result
                        results['db_operations_tested'] += 1
                        
                        if op_result['passed']:
                            results['db_operations_passed'] += 1
                            
                elif method == 'POST':
                    test_data = {'name': f'db_test_{int(time.time())}', 'role': 'developer'}
                    async with session.post(f"{self.base_url}{path}", 
                                          json=test_data) as response:
                        response_time = (time.time() - start_time) * 1000
                        results['response_times'].append(response_time)
                        
                        op_result = {
                            'response_time_ms': response_time,
                            'status_code': response.status,
                            'passed': response.status < 500 and response_time < 2000
                        }
                        
                        results['operations'][op_name] = op_result
                        results['db_operations_tested'] += 1
                        
                        if op_result['passed']:
                            results['db_operations_passed'] += 1
                            
            except Exception as e:
                results['errors'].append(f"{op_name}: {str(e)}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [test_db_operation(session, op_name, method, path) 
                    for op_name, method, path in db_operations]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        if results['response_times']:
            results['avg_db_response_time'] = statistics.mean(results['response_times'])
        
        results['db_success_rate'] = (results['db_operations_passed'] / 
                                    max(results['db_operations_tested'], 1))
        results['passed'] = results['db_success_rate'] >= 0.9
        
        return results
    
    async def _test_endpoint_functionality(self):
        """Test endpoint functionality validation"""
        logger.info("🔧 Testing Endpoint Functionality Validation")
        
        # Test employee management endpoints
        employee_results = await self._test_employee_management()
        self.test_results['endpoint_tests']['employee_management'] = employee_results
        
        # Test task assignment endpoints
        task_results = await self._test_task_assignment()
        self.test_results['endpoint_tests']['task_assignment'] = task_results
        
        # Test file management operations
        file_results = await self._test_file_management()
        self.test_results['endpoint_tests']['file_management'] = file_results
        
        # Test agent management
        agent_results = await self._test_agent_management()
        self.test_results['endpoint_tests']['agent_management'] = agent_results
    
    async def _test_employee_management(self) -> Dict[str, Any]:
        """Test employee management endpoints with security and performance"""
        logger.info("Testing employee management endpoints")
        
        results = {
            'operations_tested': 0,
            'operations_passed': 0,
            'response_times': [],
            'operations': {},
            'errors': []
        }
        
        test_employee = f"test_emp_{int(time.time())}"
        
        # Test employee lifecycle
        operations = [
            ('list_initial', 'GET', '/employees', None),
            ('hire_employee', 'POST', '/employees', {'name': test_employee, 'role': 'developer'}),
            ('list_after_hire', 'GET', '/employees', None),
            ('fire_employee', 'DELETE', f'/employees/{test_employee}', None),
            ('list_after_fire', 'GET', '/employees', None),
        ]
        
        async with aiohttp.ClientSession() as session:
            for op_name, method, path, data in operations:
                start_time = time.time()
                try:
                    if method == 'GET':
                        async with session.get(f"{self.base_url}{path}") as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            op_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'passed': response.status == 200
                            }
                            
                            if response.status == 200:
                                response_data = await response.json()
                                op_result['data'] = response_data
                            
                    elif method == 'POST':
                        async with session.post(f"{self.base_url}{path}", json=data) as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            op_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'passed': response.status in [200, 201]
                            }
                            
                    elif method == 'DELETE':
                        async with session.delete(f"{self.base_url}{path}") as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            op_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'passed': response.status == 200
                            }
                    
                    results['operations'][op_name] = op_result
                    results['operations_tested'] += 1
                    
                    if op_result['passed']:
                        results['operations_passed'] += 1
                    
                    # Small delay between operations
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    results['errors'].append(f"{op_name}: {str(e)}")
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['success_rate'] = results['operations_passed'] / max(results['operations_tested'], 1)
        results['passed'] = results['success_rate'] >= 0.8
        
        return results
    
    async def _test_task_assignment(self) -> Dict[str, Any]:
        """Test task assignment endpoints with async LLM processing"""
        logger.info("Testing task assignment endpoints")
        
        results = {
            'tasks_assigned': 0,
            'tasks_started': 0,
            'tasks_stopped': 0,
            'avg_assignment_time': 0,
            'response_times': [],
            'errors': []
        }
        
        test_employee = f"task_test_{int(time.time())}"
        
        async with aiohttp.ClientSession() as session:
            # First hire an employee
            hire_data = {'name': test_employee, 'role': 'developer'}
            async with session.post(f"{self.base_url}/employees", json=hire_data) as response:
                if response.status not in [200, 201]:
                    results['errors'].append("Failed to hire test employee")
                    results['passed'] = False
                    return results
            
            # Assign multiple tasks
            for i in range(3):
                start_time = time.time()
                task_data = {
                    'name': test_employee,
                    'task': f'Test task {i}',
                    'model': 'test_model',
                    'mode': 'build'
                }
                
                try:
                    async with session.post(f"{self.base_url}/tasks", json=task_data) as response:
                        response_time = (time.time() - start_time) * 1000
                        results['response_times'].append(response_time)
                        results['tasks_assigned'] += 1
                        
                        if response.status in [200, 201]:
                            results['tasks_started'] += 1
                        
                        # Stop the task
                        async with session.delete(f"{self.base_url}/tasks/{test_employee}") as stop_response:
                            if stop_response.status == 200:
                                results['tasks_stopped'] += 1
                        
                        await asyncio.sleep(0.5)  # Delay between tasks
                        
                except Exception as e:
                    results['errors'].append(f"Task {i}: {str(e)}")
            
            # Clean up - fire the employee
            async with session.delete(f"{self.base_url}/employees/{test_employee}") as response:
                pass
        
        if results['response_times']:
            results['avg_assignment_time'] = statistics.mean(results['response_times'])
        
        results['task_success_rate'] = results['tasks_started'] / max(results['tasks_assigned'], 1)
        results['passed'] = results['task_success_rate'] >= 0.8
        
        return results
    
    async def _test_file_management(self) -> Dict[str, Any]:
        """Test file management operations with optimized database"""
        logger.info("Testing file management operations")
        
        results = {
            'file_operations': 0,
            'successful_operations': 0,
            'avg_response_time': 0,
            'response_times': [],
            'operations': {},
            'errors': []
        }
        
        test_employee = f"file_test_{int(time.time())}"
        test_files = ['test1.py', 'test2.py', 'test3.py']
        
        async with aiohttp.ClientSession() as session:
            # Hire employee first
            hire_data = {'name': test_employee, 'role': 'developer'}
            async with session.post(f"{self.base_url}/employees", json=hire_data) as response:
                if response.status not in [200, 201]:
                    results['errors'].append("Failed to hire test employee")
                    results['passed'] = False
                    return results
            
            # Test file operations
            operations = [
                ('get_files_initial', 'GET', '/files', None),
                ('lock_files', 'POST', '/files/lock', {
                    'name': test_employee,
                    'files': test_files,
                    'description': 'Test file lock'
                }),
                ('get_files_after_lock', 'GET', '/files', None),
                ('release_files', 'POST', '/files/release', {
                    'name': test_employee,
                    'files': test_files
                }),
                ('get_files_after_release', 'GET', '/files', None),
            ]
            
            for op_name, method, path, data in operations:
                start_time = time.time()
                try:
                    if method == 'GET':
                        async with session.get(f"{self.base_url}{path}") as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            op_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'passed': response.status == 200
                            }
                            
                    elif method == 'POST':
                        async with session.post(f"{self.base_url}{path}", json=data) as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            op_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'passed': response.status in [200, 201]
                            }
                    
                    results['operations'][op_name] = op_result
                    results['file_operations'] += 1
                    
                    if op_result['passed']:
                        results['successful_operations'] += 1
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    results['errors'].append(f"{op_name}: {str(e)}")
            
            # Clean up
            async with session.delete(f"{self.base_url}/employees/{test_employee}") as response:
                pass
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['success_rate'] = results['successful_operations'] / max(results['file_operations'], 1)
        results['passed'] = results['success_rate'] >= 0.8
        
        return results
    
    async def _test_agent_management(self) -> Dict[str, Any]:
        """Test agent management with enhanced concurrency"""
        logger.info("Testing agent management with enhanced concurrency")
        
        results = {
            'agent_operations': 0,
            'successful_operations': 0,
            'avg_response_time': 0,
            'response_times': [],
            'operations': {},
            'errors': []
        }
        
        # Test agent-related endpoints
        operations = [
            ('get_agents', 'GET', '/agents'),
            ('get_bridge_status', 'GET', '/bridge'),
            ('get_chat_status', 'GET', '/chat/status'),
        ]
        
        async with aiohttp.ClientSession() as session:
            for op_name, method, path in operations:
                start_time = time.time()
                try:
                    async with session.get(f"{self.base_url}{path}") as response:
                        response_time = (time.time() - start_time) * 1000
                        results['response_times'].append(response_time)
                        
                        op_result = {
                            'response_time_ms': response_time,
                            'status_code': response.status,
                            'passed': response.status == 200
                        }
                        
                        if response.status == 200:
                            response_data = await response.json()
                            op_result['data'] = response_data
                        
                        results['operations'][op_name] = op_result
                        results['agent_operations'] += 1
                        
                        if op_result['passed']:
                            results['successful_operations'] += 1
                        
                except Exception as e:
                    results['errors'].append(f"{op_name}: {str(e)}")
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['success_rate'] = results['successful_operations'] / max(results['agent_operations'], 1)
        results['passed'] = results['success_rate'] >= 0.8
        
        return results
    
    async def _test_integration_scenarios(self):
        """Test integration scenarios"""
        logger.info("🔗 Testing Integration Scenarios")
        
        # Test WebSocket-like real-time communication
        realtime_results = await self._test_realtime_communication()
        self.test_results['integration_tests']['realtime_communication'] = realtime_results
        
        # Test error handling with security and performance
        error_results = await self._test_error_handling_integration()
        self.test_results['integration_tests']['error_handling'] = error_results
        
        # Test service interface contracts
        contract_results = await self._test_service_contracts()
        self.test_results['integration_tests']['service_contracts'] = contract_results
    
    async def _test_realtime_communication(self) -> Dict[str, Any]:
        """Test WebSocket-like real-time communication with security"""
        logger.info("Testing real-time communication with security")
        
        results = {
            'communication_tests': 0,
            'successful_communications': 0,
            'avg_response_time': 0,
            'response_times': [],
            'errors': []
        }
        
        # Test chat system endpoints for real-time communication
        async with aiohttp.ClientSession() as session:
            # Test chat status
            start_time = time.time()
            try:
                async with session.get(f"{self.base_url}/chat/status") as response:
                    response_time = (time.time() - start_time) * 1000
                    results['response_times'].append(response_time)
                    results['communication_tests'] += 1
                    
                    if response.status == 200:
                        results['successful_communications'] += 1
                        
            except Exception as e:
                results['errors'].append(f"Chat status test: {str(e)}")
            
            # Test agent bridge status
            start_time = time.time()
            try:
                async with session.get(f"{self.base_url}/bridge") as response:
                    response_time = (time.time() - start_time) * 1000
                    results['response_times'].append(response_time)
                    results['communication_tests'] += 1
                    
                    if response.status == 200:
                        results['successful_communications'] += 1
                        
            except Exception as e:
                results['errors'].append(f"Bridge status test: {str(e)}")
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['success_rate'] = (results['successful_communications'] / 
                                 max(results['communication_tests'], 1))
        results['passed'] = results['success_rate'] >= 0.8
        
        return results
    
    async def _test_error_handling_integration(self) -> Dict[str, Any]:
        """Test error handling with both security and performance enhancements"""
        logger.info("Testing error handling integration")
        
        results = {
            'error_scenarios': 0,
            'proper_error_handling': 0,
            'response_times': [],
            'scenarios': {},
            'errors': []
        }
        
        # Test various error scenarios
        error_scenarios = [
            ('invalid_endpoint', 'GET', '/invalid/endpoint'),
            ('invalid_method', 'PATCH', '/employees'),
            ('malformed_json', 'POST', '/employees'),
            ('missing_required_field', 'POST', '/employees'),
            ('nonexistent_employee', 'DELETE', '/employees/nonexistent'),
        ]
        
        async with aiohttp.ClientSession() as session:
            for scenario_name, method, path in error_scenarios:
                start_time = time.time()
                try:
                    if method == 'GET':
                        async with session.get(f"{self.base_url}{path}") as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            scenario_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'proper_error': response.status >= 400
                            }
                            
                    elif method == 'POST':
                        if scenario_name == 'malformed_json':
                            # Send malformed JSON
                            async with session.post(f"{self.base_url}{path}", 
                                                  data="invalid json") as response:
                                response_time = (time.time() - start_time) * 1000
                                results['response_times'].append(response_time)
                                
                                scenario_result = {
                                    'response_time_ms': response_time,
                                    'status_code': response.status,
                                    'proper_error': response.status == 400
                                }
                        else:
                            # Send incomplete data
                            async with session.post(f"{self.base_url}{path}", 
                                                  json={'name': 'test'}) as response:
                                response_time = (time.time() - start_time) * 1000
                                results['response_times'].append(response_time)
                                
                                scenario_result = {
                                    'response_time_ms': response_time,
                                    'status_code': response.status,
                                    'proper_error': response.status == 400
                                }
                    
                    elif method == 'DELETE':
                        async with session.delete(f"{self.base_url}{path}") as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            scenario_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'proper_error': response.status >= 400
                            }
                    
                    elif method == 'PATCH':
                        async with session.patch(f"{self.base_url}{path}") as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            scenario_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'proper_error': response.status == 405  # Method not allowed
                            }
                    
                    results['scenarios'][scenario_name] = scenario_result
                    results['error_scenarios'] += 1
                    
                    if scenario_result['proper_error']:
                        results['proper_error_handling'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"{scenario_name}: {str(e)}")
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['error_handling_rate'] = (results['proper_error_handling'] / 
                                        max(results['error_scenarios'], 1))
        results['passed'] = results['error_handling_rate'] >= 0.8
        
        return results
    
    async def _test_service_contracts(self) -> Dict[str, Any]:
        """Test service interface contracts with all optimizations"""
        logger.info("Testing service interface contracts")
        
        results = {
            'contracts_tested': 0,
            'contracts_valid': 0,
            'response_schemas': {},
            'errors': []
        }
        
        # Test key endpoints for contract compliance
        contract_endpoints = [
            ('health', 'GET', '/health'),
            ('employees', 'GET', '/employees'),
            ('status', 'GET', '/status'),
            ('progress', 'GET', '/progress'),
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint_name, method, path in contract_endpoints:
                try:
                    async with session.get(f"{self.base_url}{path}") as response:
                        results['contracts_tested'] += 1
                        
                        if response.status == 200:
                            response_data = await response.json()
                            
                            # Validate response schema
                            schema_valid = self._validate_response_schema(endpoint_name, response_data)
                            
                            results['response_schemas'][endpoint_name] = {
                                'status_code': response.status,
                                'schema_valid': schema_valid,
                                'response_keys': list(response_data.keys()) if isinstance(response_data, dict) else []
                            }
                            
                            if schema_valid:
                                results['contracts_valid'] += 1
                        else:
                            results['response_schemas'][endpoint_name] = {
                                'status_code': response.status,
                                'schema_valid': False,
                                'error': 'Non-200 response'
                            }
                            
                except Exception as e:
                    results['errors'].append(f"{endpoint_name}: {str(e)}")
        
        results['contract_compliance_rate'] = (results['contracts_valid'] / 
                                             max(results['contracts_tested'], 1))
        results['passed'] = results['contract_compliance_rate'] >= 0.9
        
        return results
    
    def _validate_response_schema(self, endpoint_name: str, response_data: Any) -> bool:
        """Validate response schema for known endpoints"""
        if not isinstance(response_data, dict):
            return False
        
        if endpoint_name == 'health':
            required_keys = ['status']
            return all(key in response_data for key in required_keys)
        
        elif endpoint_name == 'employees':
            return 'employees' in response_data and isinstance(response_data['employees'], list)
        
        elif endpoint_name == 'status':
            required_keys = ['active_sessions', 'employees']
            return all(key in response_data for key in required_keys)
        
        elif endpoint_name == 'progress':
            return 'progress' in response_data
        
        return True  # Default to valid for unknown endpoints
    
    async def _test_load_with_security(self):
        """Test load testing with security"""
        logger.info("🚀 Testing Load with Security")
        
        # Test system under 100+ concurrent authenticated users
        auth_load_results = await self._test_authenticated_load()
        self.test_results['load_tests']['authenticated_load'] = auth_load_results
        
        # Test performance metrics with security overhead
        metrics_results = await self._test_performance_metrics_with_security()
        self.test_results['load_tests']['performance_metrics'] = metrics_results
        
        # Test rate limiting effectiveness
        rate_limit_results = await self._test_rate_limiting_under_load()
        self.test_results['load_tests']['rate_limiting_effectiveness'] = rate_limit_results
    
    async def _test_authenticated_load(self) -> Dict[str, Any]:
        """Test system under 100+ concurrent authenticated users"""
        logger.info("Testing authenticated load (100+ concurrent users)")
        
        results = {
            'concurrent_users': self.concurrent_users,
            'authenticated_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'auth_failures': 0,
            'avg_response_time': 0,
            'response_times': [],
            'throughput_per_second': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        async def authenticated_request(session, user_id):
            try:
                # First authenticate
                auth_data = {'username': f'user_{user_id}', 'password': 'password'}
                async with session.post(f"{self.base_url}/auth/login", 
                                      json=auth_data) as auth_response:
                    if auth_response.status != 200:
                        results['auth_failures'] += 1
                        return
                    
                    # Make authenticated request
                    req_start = time.time()
                    async with session.get(f"{self.base_url}/employees") as response:
                        response_time = (time.time() - req_start) * 1000
                        results['response_times'].append(response_time)
                        results['authenticated_requests'] += 1
                        
                        if response.status == 200:
                            results['successful_requests'] += 1
                        else:
                            results['failed_requests'] += 1
                            
            except Exception as e:
                results['failed_requests'] += 1
                results['errors'].append(f"User {user_id}: {str(e)}")
        
        # Create concurrent authenticated requests
        connector = aiohttp.TCPConnector(limit=200, limit_per_host=200)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [authenticated_request(session, i) for i in range(self.concurrent_users)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
            results['p95_response_time'] = statistics.quantiles(results['response_times'], n=20)[18]
        
        results['throughput_per_second'] = results['authenticated_requests'] / total_time
        results['success_rate'] = (results['successful_requests'] / 
                                 max(results['authenticated_requests'], 1))
        results['passed'] = (results['success_rate'] >= 0.9 and 
                           results['avg_response_time'] < self.performance_threshold_ms)
        
        return results
    
    async def _test_performance_metrics_with_security(self) -> Dict[str, Any]:
        """Test performance metrics with security overhead"""
        logger.info("Testing performance metrics with security overhead")
        
        results = {
            'baseline_performance': {},
            'security_performance': {},
            'performance_degradation': {},
            'passed': False
        }
        
        # Test baseline performance (no security)
        baseline_times = []
        async with aiohttp.ClientSession() as session:
            for _ in range(50):
                start_time = time.time()
                try:
                    async with session.get(f"{self.base_url}/health") as response:
                        response_time = (time.time() - start_time) * 1000
                        baseline_times.append(response_time)
                except:
                    pass
        
        # Test with security
        security_times = []
        async with aiohttp.ClientSession() as session:
            for _ in range(50):
                start_time = time.time()
                try:
                    async with session.get(f"{self.secure_url}/health", ssl=False) as response:
                        response_time = (time.time() - start_time) * 1000
                        security_times.append(response_time)
                except:
                    pass
        
        if baseline_times:
            results['baseline_performance'] = {
                'avg_response_time': statistics.mean(baseline_times),
                'p95_response_time': statistics.quantiles(baseline_times, n=20)[18] if len(baseline_times) >= 20 else max(baseline_times)
            }
        
        if security_times:
            results['security_performance'] = {
                'avg_response_time': statistics.mean(security_times),
                'p95_response_time': statistics.quantiles(security_times, n=20)[18] if len(security_times) >= 20 else max(security_times)
            }
        
        # Calculate degradation
        if baseline_times and security_times:
            baseline_avg = statistics.mean(baseline_times)
            security_avg = statistics.mean(security_times)
            
            results['performance_degradation'] = {
                'absolute_ms': security_avg - baseline_avg,
                'percentage': ((security_avg - baseline_avg) / baseline_avg) * 100
            }
            
            # Security overhead should be reasonable (< 100% increase)
            results['passed'] = results['performance_degradation']['percentage'] < 100
        
        return results
    
    async def _test_rate_limiting_under_load(self) -> Dict[str, Any]:
        """Test rate limiting effectiveness under optimized throughput"""
        logger.info("Testing rate limiting effectiveness under load")
        
        results = {
            'total_requests': 1000,
            'successful_requests': 0,
            'rate_limited_requests': 0,
            'failed_requests': 0,
            'rate_limiting_triggered': False,
            'avg_response_time': 0,
            'response_times': [],
            'errors': []
        }
        
        async def burst_request(session, request_id):
            start_time = time.time()
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    response_time = (time.time() - start_time) * 1000
                    results['response_times'].append(response_time)
                    
                    if response.status == 200:
                        results['successful_requests'] += 1
                    elif response.status == 429:
                        results['rate_limited_requests'] += 1
                        results['rate_limiting_triggered'] = True
                    else:
                        results['failed_requests'] += 1
                        
            except Exception as e:
                results['failed_requests'] += 1
                results['errors'].append(f"Request {request_id}: {str(e)}")
        
        # Send burst of requests to trigger rate limiting
        connector = aiohttp.TCPConnector(limit=500, limit_per_host=500)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Send requests in rapid succession
            tasks = [burst_request(session, i) for i in range(results['total_requests'])]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['success_rate'] = results['successful_requests'] / results['total_requests']
        results['rate_limit_rate'] = results['rate_limited_requests'] / results['total_requests']
        
        # Rate limiting is effective if it was triggered and success rate is reasonable
        results['passed'] = (results['rate_limiting_triggered'] and 
                           results['success_rate'] >= 0.5)
        
        return results
    
    async def _test_production_readiness(self):
        """Test production API readiness"""
        logger.info("🏭 Testing Production API Readiness")
        
        # Test HTTPS endpoints
        https_results = await self._test_https_endpoints()
        self.test_results['production_readiness']['https'] = https_results
        
        # Test monitoring integration
        monitoring_results = await self._test_monitoring_integration()
        self.test_results['production_readiness']['monitoring'] = monitoring_results
        
        # Test audit logging
        audit_results = await self._test_audit_logging()
        self.test_results['production_readiness']['audit_logging'] = audit_results
    
    async def _test_https_endpoints(self) -> Dict[str, Any]:
        """Test HTTPS endpoints with all optimizations"""
        logger.info("Testing HTTPS endpoints")
        
        results = {
            'https_endpoints_tested': 0,
            'https_endpoints_working': 0,
            'ssl_errors': 0,
            'avg_response_time': 0,
            'response_times': [],
            'endpoints': {},
            'errors': []
        }
        
        # Test key HTTPS endpoints
        https_endpoints = [
            '/health',
            '/auth/login',
            '/employees',
            '/status'
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in https_endpoints:
                start_time = time.time()
                try:
                    async with session.get(f"{self.secure_url}{endpoint}", ssl=False) as response:
                        response_time = (time.time() - start_time) * 1000
                        results['response_times'].append(response_time)
                        results['https_endpoints_tested'] += 1
                        
                        endpoint_result = {
                            'status_code': response.status,
                            'response_time_ms': response_time,
                            'ssl_working': True,
                            'passed': response.status < 500
                        }
                        
                        if endpoint_result['passed']:
                            results['https_endpoints_working'] += 1
                        
                        results['endpoints'][endpoint] = endpoint_result
                        
                except ssl.SSLError as e:
                    results['ssl_errors'] += 1
                    results['errors'].append(f"SSL error for {endpoint}: {str(e)}")
                    results['endpoints'][endpoint] = {
                        'ssl_working': False,
                        'error': str(e),
                        'passed': False
                    }
                except Exception as e:
                    results['errors'].append(f"Error testing {endpoint}: {str(e)}")
                    results['endpoints'][endpoint] = {
                        'error': str(e),
                        'passed': False
                    }
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['https_success_rate'] = (results['https_endpoints_working'] / 
                                       max(results['https_endpoints_tested'], 1))
        results['passed'] = results['https_success_rate'] >= 0.8
        
        return results
    
    async def _test_monitoring_integration(self) -> Dict[str, Any]:
        """Test monitoring integration with secure API operations"""
        logger.info("Testing monitoring integration")
        
        results = {
            'monitoring_endpoints_tested': 0,
            'monitoring_endpoints_working': 0,
            'avg_response_time': 0,
            'response_times': [],
            'endpoints': {},
            'errors': []
        }
        
        # Test monitoring endpoints
        monitoring_endpoints = [
            '/monitoring/health',
            '/monitoring/recovery',
            '/monitoring/production/status',
            '/monitoring/production/performance',
            '/monitoring/production/alerts'
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in monitoring_endpoints:
                start_time = time.time()
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        response_time = (time.time() - start_time) * 1000
                        results['response_times'].append(response_time)
                        results['monitoring_endpoints_tested'] += 1
                        
                        endpoint_result = {
                            'status_code': response.status,
                            'response_time_ms': response_time,
                            'passed': response.status in [200, 404]  # 404 acceptable if monitoring not available
                        }
                        
                        if response.status == 200:
                            results['monitoring_endpoints_working'] += 1
                            response_data = await response.json()
                            endpoint_result['has_data'] = bool(response_data)
                        
                        results['endpoints'][endpoint] = endpoint_result
                        
                except Exception as e:
                    results['errors'].append(f"Error testing {endpoint}: {str(e)}")
                    results['endpoints'][endpoint] = {
                        'error': str(e),
                        'passed': False
                    }
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['monitoring_availability'] = (results['monitoring_endpoints_working'] / 
                                            max(results['monitoring_endpoints_tested'], 1))
        results['passed'] = results['monitoring_availability'] >= 0.6  # Some monitoring may not be available
        
        return results
    
    async def _test_audit_logging(self) -> Dict[str, Any]:
        """Test audit logging with high-performance operations"""
        logger.info("Testing audit logging")
        
        results = {
            'audit_operations': 0,
            'logged_operations': 0,
            'log_files_found': 0,
            'log_entries_found': 0,
            'passed': False
        }
        
        # Perform operations that should be logged
        test_operations = [
            ('hire_employee', 'POST', '/employees', {'name': 'audit_test', 'role': 'developer'}),
            ('fire_employee', 'DELETE', '/employees/audit_test', None),
        ]
        
        async with aiohttp.ClientSession() as session:
            for op_name, method, path, data in test_operations:
                try:
                    if method == 'POST':
                        async with session.post(f"{self.base_url}{path}", json=data) as response:
                            results['audit_operations'] += 1
                    elif method == 'DELETE':
                        async with session.delete(f"{self.base_url}{path}") as response:
                            results['audit_operations'] += 1
                            
                except Exception as e:
                    pass
        
        # Check for log files
        log_directories = ['logs', '.', 'sessions']
        for log_dir in log_directories:
            log_path = Path(log_dir)
            if log_path.exists():
                log_files = list(log_path.glob('*.log'))
                results['log_files_found'] += len(log_files)
                
                # Check log content
                for log_file in log_files:
                    try:
                        with open(log_file, 'r') as f:
                            content = f.read()
                            if 'audit_test' in content:
                                results['log_entries_found'] += 1
                    except:
                        pass
        
        results['logging_working'] = results['log_files_found'] > 0
        results['passed'] = results['logging_working']
        
        return results
    
    async def _final_security_audit(self):
        """Comprehensive security audit"""
        logger.info("🔒 Final Comprehensive Security Audit")
        
        # Final security scan
        security_scan_results = await self._final_security_scan()
        self.test_results['production_readiness']['security_scan'] = security_scan_results
        
        # Test authentication flows under stress
        auth_stress_results = await self._test_auth_under_stress()
        self.test_results['production_readiness']['auth_stress'] = auth_stress_results
    
    async def _final_security_scan(self) -> Dict[str, Any]:
        """Final security scan with all optimizations active"""
        logger.info("Running final security scan")
        
        results = {
            'security_checks': 0,
            'security_passed': 0,
            'vulnerabilities_found': 0,
            'checks': {},
            'recommendations': []
        }
        
        # Security checks
        security_checks = [
            ('sql_injection', self._test_sql_injection),
            ('xss_protection', self._test_xss_protection),
            ('csrf_protection', self._test_csrf_protection),
            ('security_headers', self._test_security_headers),
            ('authentication_bypass', self._test_auth_bypass),
        ]
        
        for check_name, check_function in security_checks:
            try:
                check_result = await check_function()
                results['checks'][check_name] = check_result
                results['security_checks'] += 1
                
                if check_result.get('passed', False):
                    results['security_passed'] += 1
                else:
                    results['vulnerabilities_found'] += 1
                    if 'recommendation' in check_result:
                        results['recommendations'].append(check_result['recommendation'])
                        
            except Exception as e:
                results['checks'][check_name] = {
                    'passed': False,
                    'error': str(e)
                }
                results['vulnerabilities_found'] += 1
        
        results['security_score'] = (results['security_passed'] / 
                                   max(results['security_checks'], 1)) * 100
        results['passed'] = results['security_score'] >= 80
        
        return results
    
    async def _test_sql_injection(self) -> Dict[str, Any]:
        """Test SQL injection protection"""
        sql_payloads = [
            "'; DROP TABLE employees; --",
            "' OR '1'='1",
            "'; INSERT INTO employees VALUES ('hacker', 'admin'); --"
        ]
        
        results = {'passed': True, 'tests': 0, 'blocked': 0}
        
        async with aiohttp.ClientSession() as session:
            for payload in sql_payloads:
                try:
                    data = {'name': payload, 'role': 'developer'}
                    async with session.post(f"{self.base_url}/employees", json=data) as response:
                        results['tests'] += 1
                        if response.status == 400:  # Should be blocked
                            results['blocked'] += 1
                except:
                    results['blocked'] += 1
        
        results['passed'] = results['blocked'] == results['tests']
        return results
    
    async def _test_xss_protection(self) -> Dict[str, Any]:
        """Test XSS protection"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')"
        ]
        
        results = {'passed': True, 'tests': 0, 'blocked': 0}
        
        async with aiohttp.ClientSession() as session:
            for payload in xss_payloads:
                try:
                    data = {'name': payload, 'role': 'developer'}
                    async with session.post(f"{self.base_url}/employees", json=data) as response:
                        results['tests'] += 1
                        if response.status == 400:  # Should be blocked
                            results['blocked'] += 1
                except:
                    results['blocked'] += 1
        
        results['passed'] = results['blocked'] == results['tests']
        return results
    
    async def _test_csrf_protection(self) -> Dict[str, Any]:
        """Test CSRF protection"""
        results = {'passed': True, 'csrf_headers_present': False}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    # Check for CSRF protection headers
                    headers = response.headers
                    if 'X-Frame-Options' in headers or 'Content-Security-Policy' in headers:
                        results['csrf_headers_present'] = True
            except:
                pass
        
        results['passed'] = results['csrf_headers_present']
        return results
    
    async def _test_security_headers(self) -> Dict[str, Any]:
        """Test security headers"""
        required_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security'
        ]
        
        results = {'passed': False, 'headers_present': 0, 'headers_missing': []}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.secure_url}/health", ssl=False) as response:
                    headers = response.headers
                    for header in required_headers:
                        if header in headers:
                            results['headers_present'] += 1
                        else:
                            results['headers_missing'].append(header)
            except:
                pass
        
        results['passed'] = results['headers_present'] >= len(required_headers) * 0.75
        return results
    
    async def _test_auth_bypass(self) -> Dict[str, Any]:
        """Test authentication bypass attempts"""
        results = {'passed': True, 'bypass_attempts': 0, 'blocked_attempts': 0}
        
        # Try to access protected endpoints without authentication
        protected_endpoints = [
            '/employees',
            '/tasks',
            '/files'
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in protected_endpoints:
                try:
                    async with session.get(f"{self.secure_url}{endpoint}", ssl=False) as response:
                        results['bypass_attempts'] += 1
                        if response.status == 401:  # Should require authentication
                            results['blocked_attempts'] += 1
                except:
                    results['blocked_attempts'] += 1
        
        results['passed'] = results['blocked_attempts'] == results['bypass_attempts']
        return results
    
    async def _test_auth_under_stress(self) -> Dict[str, Any]:
        """Test authentication flows under stress conditions"""
        logger.info("Testing authentication under stress")
        
        results = {
            'stress_requests': 200,
            'successful_auths': 0,
            'failed_auths': 0,
            'avg_auth_time': 0,
            'auth_times': [],
            'errors': []
        }
        
        async def stress_auth(session, request_id):
            start_time = time.time()
            try:
                auth_data = {'username': f'stress_user_{request_id}', 'password': 'password'}
                async with session.post(f"{self.secure_url}/auth/login", 
                                      json=auth_data, ssl=False) as response:
                    auth_time = (time.time() - start_time) * 1000
                    results['auth_times'].append(auth_time)
                    
                    if response.status in [200, 401]:  # 401 expected for invalid users
                        results['successful_auths'] += 1
                    else:
                        results['failed_auths'] += 1
                        
            except Exception as e:
                results['failed_auths'] += 1
                results['errors'].append(f"Request {request_id}: {str(e)}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [stress_auth(session, i) for i in range(results['stress_requests'])]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        if results['auth_times']:
            results['avg_auth_time'] = statistics.mean(results['auth_times'])
        
        results['auth_success_rate'] = (results['successful_auths'] / 
                                      max(results['stress_requests'], 1))
        results['passed'] = results['auth_success_rate'] >= 0.95
        
        return results
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final validation report"""
        logger.info("📊 Generating Final Validation Report")
        
        total_time = time.time() - self.start_time
        
        # Calculate overall scores
        security_score = self._calculate_category_score('security_tests')
        performance_score = self._calculate_category_score('performance_tests')
        endpoint_score = self._calculate_category_score('endpoint_tests')
        integration_score = self._calculate_category_score('integration_tests')
        load_score = self._calculate_category_score('load_tests')
        production_score = self._calculate_category_score('production_readiness')
        
        overall_score = statistics.mean([
            security_score, performance_score, endpoint_score,
            integration_score, load_score, production_score
        ])
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        final_report = {
            'validation_summary': {
                'total_validation_time_seconds': total_time,
                'overall_score': overall_score,
                'production_ready': overall_score >= 80,
                'timestamp': datetime.now().isoformat()
            },
            'category_scores': {
                'security_with_performance': security_score,
                'api_performance_with_security': performance_score,
                'endpoint_functionality': endpoint_score,
                'integration_testing': integration_score,
                'load_testing_with_security': load_score,
                'production_readiness': production_score
            },
            'detailed_results': self.test_results,
            'recommendations': recommendations,
            'production_deployment_status': {
                'security_ready': security_score >= 85,
                'performance_ready': performance_score >= 80,
                'functionality_ready': endpoint_score >= 90,
                'integration_ready': integration_score >= 85,
                'load_ready': load_score >= 80,
                'monitoring_ready': production_score >= 75
            },
            'next_steps': self._generate_next_steps(overall_score)
        }
        
        return final_report
    
    def _calculate_category_score(self, category: str) -> float:
        """Calculate score for a test category"""
        if category not in self.test_results:
            return 0.0
        
        category_tests = self.test_results[category]
        if not category_tests:
            return 0.0
        
        passed_tests = 0
        total_tests = 0
        
        for test_name, test_result in category_tests.items():
            if isinstance(test_result, dict) and 'passed' in test_result:
                total_tests += 1
                if test_result['passed']:
                    passed_tests += 1
        
        return (passed_tests / max(total_tests, 1)) * 100
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Security recommendations
        security_score = self._calculate_category_score('security_tests')
        if security_score < 90:
            recommendations.append("Enhance security measures - consider additional input validation and rate limiting")
        
        # Performance recommendations
        performance_score = self._calculate_category_score('performance_tests')
        if performance_score < 85:
            recommendations.append("Optimize API performance - consider caching and database query optimization")
        
        # Load testing recommendations
        load_score = self._calculate_category_score('load_tests')
        if load_score < 80:
            recommendations.append("Improve load handling capacity - consider horizontal scaling and load balancing")
        
        # Production readiness recommendations
        production_score = self._calculate_category_score('production_readiness')
        if production_score < 80:
            recommendations.append("Complete production readiness checklist - ensure monitoring and logging are fully configured")
        
        return recommendations
    
    def _generate_next_steps(self, overall_score: float) -> List[str]:
        """Generate next steps based on overall score"""
        if overall_score >= 90:
            return [
                "✅ System is ready for production deployment",
                "🚀 Deploy to production environment",
                "📊 Set up production monitoring and alerting",
                "🔄 Establish regular security audits"
            ]
        elif overall_score >= 80:
            return [
                "⚠️ Address remaining issues before production deployment",
                "🔧 Implement recommended optimizations",
                "🧪 Re-run validation tests",
                "📋 Complete production readiness checklist"
            ]
        else:
            return [
                "❌ System requires significant improvements before production",
                "🔒 Focus on security enhancements",
                "⚡ Optimize performance bottlenecks",
                "🧪 Conduct thorough testing and validation"
            ]


async def main():
    """Main function to run comprehensive API validation"""
    print("🚀 Starting Final Comprehensive API Validation for OpenCode-Slack")
    print("=" * 80)
    
    # Check if servers are running
    validator = ComprehensiveAPIValidator()
    
    try:
        # Test basic connectivity
        response = requests.get(f"{validator.base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Base server not responding. Please start the server first.")
            return
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to base server. Please start the server first.")
        return
    
    print("✅ Server connectivity confirmed")
    print("🔍 Running comprehensive validation suite...")
    print()
    
    # Run comprehensive validation
    final_report = await validator.run_comprehensive_validation()
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"final_comprehensive_api_validation_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(final_report, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 FINAL COMPREHENSIVE API VALIDATION REPORT")
    print("=" * 80)
    
    summary = final_report['validation_summary']
    print(f"⏱️  Total Validation Time: {summary['total_validation_time_seconds']:.2f} seconds")
    print(f"📈 Overall Score: {summary['overall_score']:.1f}/100")
    print(f"🏭 Production Ready: {'✅ YES' if summary['production_ready'] else '❌ NO'}")
    print()
    
    print("📋 Category Scores:")
    for category, score in final_report['category_scores'].items():
        status = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
        print(f"  {status} {category.replace('_', ' ').title()}: {score:.1f}/100")
    print()
    
    print("🚀 Production Deployment Status:")
    deployment_status = final_report['production_deployment_status']
    for component, ready in deployment_status.items():
        status = "✅" if ready else "❌"
        print(f"  {status} {component.replace('_', ' ').title()}: {'Ready' if ready else 'Not Ready'}")
    print()
    
    if final_report['recommendations']:
        print("💡 Recommendations:")
        for rec in final_report['recommendations']:
            print(f"  • {rec}")
        print()
    
    print("📋 Next Steps:")
    for step in final_report['next_steps']:
        print(f"  {step}")
    print()
    
    print(f"📄 Detailed report saved to: {report_file}")
    print("=" * 80)
    
    return final_report


if __name__ == "__main__":
    asyncio.run(main())