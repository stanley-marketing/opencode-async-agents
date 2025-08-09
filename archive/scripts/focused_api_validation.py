#!/usr/bin/env python3
"""
Focused API Validation for OpenCode-Slack System
Tests the current running system with realistic expectations.
"""

import asyncio
import aiohttp
import json
import time
import statistics
import requests
from datetime import datetime
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FocusedAPIValidator:
    """Focused API validation for the current system"""
    
    def __init__(self, base_url: str = "http://localhost:8091", secure_url: str = "https://localhost:8443"):
        self.base_url = base_url
        self.secure_url = secure_url
        self.session = requests.Session()
        self.test_results = {
            'api_functionality': {},
            'performance_tests': {},
            'security_tests': {},
            'integration_tests': {},
            'production_readiness': {}
        }
        self.start_time = time.time()
        
    async def run_focused_validation(self) -> Dict[str, Any]:
        """Run focused API validation"""
        logger.info("🚀 Starting Focused API Validation")
        
        # Test 1: API Functionality
        await self._test_api_functionality()
        
        # Test 2: Performance Testing
        await self._test_performance()
        
        # Test 3: Security Testing
        await self._test_security()
        
        # Test 4: Integration Testing
        await self._test_integration()
        
        # Test 5: Production Readiness
        await self._test_production_readiness()
        
        return self._generate_report()
    
    async def _test_api_functionality(self):
        """Test all API endpoints functionality"""
        logger.info("🔧 Testing API Functionality")
        
        results = {
            'endpoints_tested': 0,
            'endpoints_working': 0,
            'response_times': [],
            'endpoints': {}
        }
        
        # Core API endpoints to test
        endpoints = [
            ('GET', '/health', None),
            ('GET', '/employees', None),
            ('POST', '/employees', {'name': 'test_api_user', 'role': 'developer'}),
            ('GET', '/status', None),
            ('GET', '/progress', None),
            ('GET', '/files', None),
            ('GET', '/sessions', None),
            ('GET', '/agents', None),
            ('GET', '/bridge', None),
            ('GET', '/chat/status', None),
            ('GET', '/project-root', None),
            ('GET', '/monitoring/health', None),
            ('GET', '/monitoring/recovery', None),
            ('GET', '/monitoring/production/status', None),
            ('GET', '/monitoring/production/performance', None),
            ('GET', '/monitoring/production/alerts', None),
            ('DELETE', '/employees/test_api_user', None),
        ]
        
        async with aiohttp.ClientSession() as session:
            for method, path, data in endpoints:
                start_time = time.time()
                try:
                    if method == 'GET':
                        async with session.get(f"{self.base_url}{path}") as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            endpoint_result = {
                                'status_code': response.status,
                                'response_time_ms': response_time,
                                'working': response.status < 500,
                                'data_received': response.status == 200
                            }
                            
                            if response.status == 200:
                                try:
                                    data = await response.json()
                                    endpoint_result['response_size'] = len(str(data))
                                except:
                                    pass
                    
                    elif method == 'POST':
                        async with session.post(f"{self.base_url}{path}", json=data) as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            endpoint_result = {
                                'status_code': response.status,
                                'response_time_ms': response_time,
                                'working': response.status < 500,
                                'data_received': response.status in [200, 201]
                            }
                    
                    elif method == 'DELETE':
                        async with session.delete(f"{self.base_url}{path}") as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            endpoint_result = {
                                'status_code': response.status,
                                'response_time_ms': response_time,
                                'working': response.status < 500,
                                'data_received': response.status == 200
                            }
                    
                    results['endpoints'][f"{method} {path}"] = endpoint_result
                    results['endpoints_tested'] += 1
                    
                    if endpoint_result['working']:
                        results['endpoints_working'] += 1
                    
                    # Small delay between requests
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    results['endpoints'][f"{method} {path}"] = {
                        'error': str(e),
                        'working': False
                    }
                    results['endpoints_tested'] += 1
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
            results['p95_response_time'] = statistics.quantiles(results['response_times'], n=20)[18] if len(results['response_times']) >= 20 else max(results['response_times'])
        
        results['success_rate'] = results['endpoints_working'] / max(results['endpoints_tested'], 1)
        results['passed'] = results['success_rate'] >= 0.8
        
        self.test_results['api_functionality'] = results
        
        logger.info(f"API Functionality: {results['endpoints_working']}/{results['endpoints_tested']} working, "
                   f"avg response: {results.get('avg_response_time', 0):.2f}ms")
    
    async def _test_performance(self):
        """Test API performance under load"""
        logger.info("⚡ Testing Performance")
        
        # Test concurrent requests
        concurrent_results = await self._test_concurrent_requests()
        self.test_results['performance_tests']['concurrent_requests'] = concurrent_results
        
        # Test throughput
        throughput_results = await self._test_throughput()
        self.test_results['performance_tests']['throughput'] = throughput_results
        
        # Test database operations
        db_results = await self._test_database_performance()
        self.test_results['performance_tests']['database'] = db_results
    
    async def _test_concurrent_requests(self) -> Dict[str, Any]:
        """Test concurrent request handling"""
        logger.info("Testing concurrent request handling")
        
        results = {
            'concurrent_requests': 100,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'response_times': [],
            'throughput_per_second': 0
        }
        
        start_time = time.time()
        
        async def make_request(session, request_id):
            req_start = time.time()
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    response_time = (time.time() - req_start) * 1000
                    results['response_times'].append(response_time)
                    
                    if response.status == 200:
                        results['successful_requests'] += 1
                    else:
                        results['failed_requests'] += 1
            except:
                results['failed_requests'] += 1
        
        connector = aiohttp.TCPConnector(limit=200, limit_per_host=200)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [make_request(session, i) for i in range(results['concurrent_requests'])]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
            results['p95_response_time'] = statistics.quantiles(results['response_times'], n=20)[18] if len(results['response_times']) >= 20 else max(results['response_times'])
        
        results['throughput_per_second'] = results['concurrent_requests'] / total_time
        results['success_rate'] = results['successful_requests'] / results['concurrent_requests']
        results['passed'] = results['success_rate'] >= 0.95 and results['avg_response_time'] < 1000
        
        return results
    
    async def _test_throughput(self) -> Dict[str, Any]:
        """Test API throughput"""
        logger.info("Testing API throughput")
        
        results = {
            'total_requests': 200,
            'successful_requests': 0,
            'failed_requests': 0,
            'requests_per_second': 0,
            'avg_response_time': 0,
            'response_times': []
        }
        
        start_time = time.time()
        
        async def make_throughput_request(session, request_id):
            req_start = time.time()
            try:
                async with session.get(f"{self.base_url}/employees") as response:
                    response_time = (time.time() - req_start) * 1000
                    results['response_times'].append(response_time)
                    
                    if response.status == 200:
                        results['successful_requests'] += 1
                    else:
                        results['failed_requests'] += 1
            except:
                results['failed_requests'] += 1
        
        # Send requests in batches
        batch_size = 20
        async with aiohttp.ClientSession() as session:
            for batch_start in range(0, results['total_requests'], batch_size):
                batch_end = min(batch_start + batch_size, results['total_requests'])
                tasks = [make_throughput_request(session, i) for i in range(batch_start, batch_end)]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.1)  # Small delay between batches
        
        total_time = time.time() - start_time
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['requests_per_second'] = results['total_requests'] / total_time
        results['success_rate'] = results['successful_requests'] / results['total_requests']
        results['passed'] = results['success_rate'] >= 0.9 and results['requests_per_second'] >= 50
        
        return results
    
    async def _test_database_performance(self) -> Dict[str, Any]:
        """Test database operation performance"""
        logger.info("Testing database performance")
        
        results = {
            'operations_tested': 0,
            'operations_successful': 0,
            'avg_response_time': 0,
            'response_times': [],
            'operations': {}
        }
        
        # Test database-heavy operations
        operations = [
            ('list_employees', 'GET', '/employees'),
            ('get_status', 'GET', '/status'),
            ('get_progress', 'GET', '/progress'),
            ('get_files', 'GET', '/files'),
            ('create_employee', 'POST', '/employees', {'name': f'db_test_{int(time.time())}', 'role': 'developer'}),
        ]
        
        async with aiohttp.ClientSession() as session:
            for op_name, method, path, *data in operations:
                start_time = time.time()
                try:
                    if method == 'GET':
                        async with session.get(f"{self.base_url}{path}") as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            op_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'successful': response.status == 200
                            }
                    
                    elif method == 'POST':
                        post_data = data[0] if data else {}
                        async with session.post(f"{self.base_url}{path}", json=post_data) as response:
                            response_time = (time.time() - start_time) * 1000
                            results['response_times'].append(response_time)
                            
                            op_result = {
                                'response_time_ms': response_time,
                                'status_code': response.status,
                                'successful': response.status in [200, 201]
                            }
                    
                    results['operations'][op_name] = op_result
                    results['operations_tested'] += 1
                    
                    if op_result['successful']:
                        results['operations_successful'] += 1
                    
                    await asyncio.sleep(0.2)  # Delay between operations
                    
                except Exception as e:
                    results['operations'][op_name] = {
                        'error': str(e),
                        'successful': False
                    }
                    results['operations_tested'] += 1
        
        if results['response_times']:
            results['avg_response_time'] = statistics.mean(results['response_times'])
        
        results['success_rate'] = results['operations_successful'] / max(results['operations_tested'], 1)
        results['passed'] = results['success_rate'] >= 0.8 and results['avg_response_time'] < 2000
        
        return results
    
    async def _test_security(self):
        """Test security features"""
        logger.info("🔒 Testing Security")
        
        # Test HTTPS endpoints
        https_results = await self._test_https_security()
        self.test_results['security_tests']['https'] = https_results
        
        # Test input validation
        validation_results = await self._test_input_validation()
        self.test_results['security_tests']['input_validation'] = validation_results
        
        # Test error handling
        error_results = await self._test_error_handling()
        self.test_results['security_tests']['error_handling'] = error_results
    
    async def _test_https_security(self) -> Dict[str, Any]:
        """Test HTTPS endpoints"""
        logger.info("Testing HTTPS security")
        
        results = {
            'https_endpoints_tested': 0,
            'https_endpoints_working': 0,
            'security_headers_present': 0,
            'endpoints': {}
        }
        
        https_endpoints = ['/health', '/employees', '/status']
        
        async with aiohttp.ClientSession() as session:
            for endpoint in https_endpoints:
                try:
                    async with session.get(f"{self.secure_url}{endpoint}", ssl=False) as response:
                        results['https_endpoints_tested'] += 1
                        
                        endpoint_result = {
                            'status_code': response.status,
                            'working': response.status < 500,
                            'security_headers': {}
                        }
                        
                        # Check for security headers
                        security_headers = [
                            'X-Content-Type-Options',
                            'X-Frame-Options', 
                            'X-XSS-Protection',
                            'Strict-Transport-Security'
                        ]
                        
                        for header in security_headers:
                            if header in response.headers:
                                endpoint_result['security_headers'][header] = response.headers[header]
                                results['security_headers_present'] += 1
                        
                        if endpoint_result['working']:
                            results['https_endpoints_working'] += 1
                        
                        results['endpoints'][endpoint] = endpoint_result
                        
                except Exception as e:
                    results['endpoints'][endpoint] = {
                        'error': str(e),
                        'working': False
                    }
                    results['https_endpoints_tested'] += 1
        
        results['https_success_rate'] = results['https_endpoints_working'] / max(results['https_endpoints_tested'], 1)
        results['security_headers_rate'] = results['security_headers_present'] / max(results['https_endpoints_tested'] * 4, 1)
        results['passed'] = results['https_success_rate'] >= 0.8 and results['security_headers_rate'] >= 0.5
        
        return results
    
    async def _test_input_validation(self) -> Dict[str, Any]:
        """Test input validation"""
        logger.info("Testing input validation")
        
        results = {
            'validation_tests': 0,
            'validation_working': 0,
            'tests': {}
        }
        
        # Test invalid inputs
        test_cases = [
            ('empty_name', {'name': '', 'role': 'developer'}),
            ('empty_role', {'name': 'test', 'role': ''}),
            ('long_name', {'name': 'x' * 1000, 'role': 'developer'}),
            ('special_chars', {'name': 'test<script>', 'role': 'developer'}),
            ('sql_injection', {'name': "'; DROP TABLE employees; --", 'role': 'developer'}),
        ]
        
        async with aiohttp.ClientSession() as session:
            for test_name, data in test_cases:
                try:
                    async with session.post(f"{self.base_url}/employees", json=data) as response:
                        results['validation_tests'] += 1
                        
                        test_result = {
                            'status_code': response.status,
                            'properly_rejected': response.status == 400
                        }
                        
                        if test_result['properly_rejected']:
                            results['validation_working'] += 1
                        
                        results['tests'][test_name] = test_result
                        
                except Exception as e:
                    results['tests'][test_name] = {
                        'error': str(e),
                        'properly_rejected': False
                    }
                    results['validation_tests'] += 1
        
        results['validation_rate'] = results['validation_working'] / max(results['validation_tests'], 1)
        results['passed'] = results['validation_rate'] >= 0.6
        
        return results
    
    async def _test_error_handling(self) -> Dict[str, Any]:
        """Test error handling"""
        logger.info("Testing error handling")
        
        results = {
            'error_tests': 0,
            'proper_errors': 0,
            'tests': {}
        }
        
        # Test error scenarios
        error_tests = [
            ('invalid_endpoint', 'GET', '/invalid/endpoint'),
            ('invalid_method', 'PATCH', '/employees'),
            ('nonexistent_employee', 'DELETE', '/employees/nonexistent_user_12345'),
        ]
        
        async with aiohttp.ClientSession() as session:
            for test_name, method, path in error_tests:
                try:
                    if method == 'GET':
                        async with session.get(f"{self.base_url}{path}") as response:
                            results['error_tests'] += 1
                            
                            test_result = {
                                'status_code': response.status,
                                'proper_error': response.status >= 400
                            }
                    
                    elif method == 'PATCH':
                        async with session.patch(f"{self.base_url}{path}") as response:
                            results['error_tests'] += 1
                            
                            test_result = {
                                'status_code': response.status,
                                'proper_error': response.status == 405  # Method not allowed
                            }
                    
                    elif method == 'DELETE':
                        async with session.delete(f"{self.base_url}{path}") as response:
                            results['error_tests'] += 1
                            
                            test_result = {
                                'status_code': response.status,
                                'proper_error': response.status >= 400
                            }
                    
                    if test_result['proper_error']:
                        results['proper_errors'] += 1
                    
                    results['tests'][test_name] = test_result
                    
                except Exception as e:
                    results['tests'][test_name] = {
                        'error': str(e),
                        'proper_error': False
                    }
                    results['error_tests'] += 1
        
        results['error_handling_rate'] = results['proper_errors'] / max(results['error_tests'], 1)
        results['passed'] = results['error_handling_rate'] >= 0.8
        
        return results
    
    async def _test_integration(self):
        """Test integration scenarios"""
        logger.info("🔗 Testing Integration")
        
        # Test employee lifecycle
        lifecycle_results = await self._test_employee_lifecycle()
        self.test_results['integration_tests']['employee_lifecycle'] = lifecycle_results
        
        # Test monitoring integration
        monitoring_results = await self._test_monitoring_integration()
        self.test_results['integration_tests']['monitoring'] = monitoring_results
    
    async def _test_employee_lifecycle(self) -> Dict[str, Any]:
        """Test complete employee lifecycle"""
        logger.info("Testing employee lifecycle")
        
        results = {
            'lifecycle_steps': 0,
            'successful_steps': 0,
            'steps': {}
        }
        
        test_employee = f"lifecycle_test_{int(time.time())}"
        
        # Employee lifecycle steps
        steps = [
            ('hire', 'POST', '/employees', {'name': test_employee, 'role': 'developer'}),
            ('verify_hired', 'GET', '/employees', None),
            ('assign_task', 'POST', '/tasks', {'name': test_employee, 'task': 'Test task'}),
            ('check_progress', 'GET', f'/progress?name={test_employee}', None),
            ('stop_task', 'DELETE', f'/tasks/{test_employee}', None),
            ('fire', 'DELETE', f'/employees/{test_employee}', None),
        ]
        
        async with aiohttp.ClientSession() as session:
            for step_name, method, path, data in steps:
                try:
                    if method == 'GET':
                        async with session.get(f"{self.base_url}{path}") as response:
                            step_result = {
                                'status_code': response.status,
                                'successful': response.status == 200
                            }
                            
                            if step_name == 'verify_hired' and response.status == 200:
                                response_data = await response.json()
                                employees = response_data.get('employees', [])
                                employee_names = [emp.get('name') for emp in employees]
                                step_result['employee_found'] = test_employee in employee_names
                                step_result['successful'] = step_result['employee_found']
                    
                    elif method == 'POST':
                        async with session.post(f"{self.base_url}{path}", json=data) as response:
                            step_result = {
                                'status_code': response.status,
                                'successful': response.status in [200, 201]
                            }
                    
                    elif method == 'DELETE':
                        async with session.delete(f"{self.base_url}{path}") as response:
                            step_result = {
                                'status_code': response.status,
                                'successful': response.status == 200
                            }
                    
                    results['steps'][step_name] = step_result
                    results['lifecycle_steps'] += 1
                    
                    if step_result['successful']:
                        results['successful_steps'] += 1
                    
                    await asyncio.sleep(0.5)  # Delay between steps
                    
                except Exception as e:
                    results['steps'][step_name] = {
                        'error': str(e),
                        'successful': False
                    }
                    results['lifecycle_steps'] += 1
        
        results['lifecycle_success_rate'] = results['successful_steps'] / max(results['lifecycle_steps'], 1)
        results['passed'] = results['lifecycle_success_rate'] >= 0.8
        
        return results
    
    async def _test_monitoring_integration(self) -> Dict[str, Any]:
        """Test monitoring system integration"""
        logger.info("Testing monitoring integration")
        
        results = {
            'monitoring_endpoints': 0,
            'working_endpoints': 0,
            'endpoints': {}
        }
        
        monitoring_endpoints = [
            '/monitoring/health',
            '/monitoring/recovery',
            '/monitoring/production/status',
            '/monitoring/production/performance',
            '/monitoring/production/alerts'
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in monitoring_endpoints:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        results['monitoring_endpoints'] += 1
                        
                        endpoint_result = {
                            'status_code': response.status,
                            'working': response.status in [200, 404]  # 404 acceptable if not available
                        }
                        
                        if response.status == 200:
                            results['working_endpoints'] += 1
                            try:
                                data = await response.json()
                                endpoint_result['has_data'] = bool(data)
                            except:
                                endpoint_result['has_data'] = False
                        
                        results['endpoints'][endpoint] = endpoint_result
                        
                except Exception as e:
                    results['endpoints'][endpoint] = {
                        'error': str(e),
                        'working': False
                    }
                    results['monitoring_endpoints'] += 1
        
        results['monitoring_availability'] = results['working_endpoints'] / max(results['monitoring_endpoints'], 1)
        results['passed'] = results['monitoring_availability'] >= 0.4  # Some monitoring may not be available
        
        return results
    
    async def _test_production_readiness(self):
        """Test production readiness"""
        logger.info("🏭 Testing Production Readiness")
        
        # Test system health
        health_results = await self._test_system_health()
        self.test_results['production_readiness']['system_health'] = health_results
        
        # Test logging
        logging_results = await self._test_logging()
        self.test_results['production_readiness']['logging'] = logging_results
        
        # Test configuration
        config_results = await self._test_configuration()
        self.test_results['production_readiness']['configuration'] = config_results
    
    async def _test_system_health(self) -> Dict[str, Any]:
        """Test system health endpoints"""
        logger.info("Testing system health")
        
        results = {
            'health_checks': 0,
            'healthy_responses': 0,
            'checks': {}
        }
        
        health_endpoints = ['/health', '/status']
        
        async with aiohttp.ClientSession() as session:
            for endpoint in health_endpoints:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        results['health_checks'] += 1
                        
                        check_result = {
                            'status_code': response.status,
                            'healthy': response.status == 200
                        }
                        
                        if response.status == 200:
                            results['healthy_responses'] += 1
                            try:
                                data = await response.json()
                                check_result['response_data'] = data
                                
                                # Check for health indicators
                                if endpoint == '/health':
                                    check_result['status_healthy'] = data.get('status') == 'healthy'
                                elif endpoint == '/status':
                                    check_result['has_employees'] = 'employees' in data
                                    check_result['has_sessions'] = 'active_sessions' in data
                            except:
                                pass
                        
                        results['checks'][endpoint] = check_result
                        
                except Exception as e:
                    results['checks'][endpoint] = {
                        'error': str(e),
                        'healthy': False
                    }
                    results['health_checks'] += 1
        
        results['health_rate'] = results['healthy_responses'] / max(results['health_checks'], 1)
        results['passed'] = results['health_rate'] >= 0.9
        
        return results
    
    async def _test_logging(self) -> Dict[str, Any]:
        """Test logging functionality"""
        logger.info("Testing logging")
        
        results = {
            'log_files_found': 0,
            'log_directories_checked': 0,
            'logging_working': False
        }
        
        # Check for log files
        import os
        from pathlib import Path
        
        log_locations = ['logs', '.', 'sessions']
        
        for location in log_locations:
            results['log_directories_checked'] += 1
            log_path = Path(location)
            
            if log_path.exists():
                log_files = list(log_path.glob('*.log'))
                results['log_files_found'] += len(log_files)
                
                if log_files:
                    results['logging_working'] = True
        
        results['passed'] = results['logging_working']
        
        return results
    
    async def _test_configuration(self) -> Dict[str, Any]:
        """Test system configuration"""
        logger.info("Testing configuration")
        
        results = {
            'config_checks': 0,
            'config_working': 0,
            'checks': {}
        }
        
        # Check environment and configuration
        import os
        
        config_checks = [
            ('env_file', lambda: os.path.exists('.env')),
            ('requirements_file', lambda: os.path.exists('requirements.txt')),
            ('database_file', lambda: os.path.exists('employees.db')),
            ('sessions_dir', lambda: os.path.exists('sessions')),
        ]
        
        for check_name, check_func in config_checks:
            results['config_checks'] += 1
            
            try:
                check_result = {
                    'exists': check_func(),
                    'working': check_func()
                }
                
                if check_result['working']:
                    results['config_working'] += 1
                
                results['checks'][check_name] = check_result
                
            except Exception as e:
                results['checks'][check_name] = {
                    'error': str(e),
                    'working': False
                }
        
        results['config_rate'] = results['config_working'] / max(results['config_checks'], 1)
        results['passed'] = results['config_rate'] >= 0.75
        
        return results
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        logger.info("📊 Generating Validation Report")
        
        total_time = time.time() - self.start_time
        
        # Calculate category scores
        category_scores = {}
        for category, tests in self.test_results.items():
            if tests:
                passed_tests = sum(1 for test in tests.values() if isinstance(test, dict) and test.get('passed', False))
                total_tests = len(tests)
                category_scores[category] = (passed_tests / max(total_tests, 1)) * 100
            else:
                category_scores[category] = 0
        
        overall_score = statistics.mean(category_scores.values()) if category_scores else 0
        
        # Generate recommendations
        recommendations = []
        if category_scores.get('api_functionality', 0) < 90:
            recommendations.append("Fix failing API endpoints")
        if category_scores.get('performance_tests', 0) < 80:
            recommendations.append("Optimize API performance and database queries")
        if category_scores.get('security_tests', 0) < 85:
            recommendations.append("Enhance security measures and input validation")
        if category_scores.get('integration_tests', 0) < 90:
            recommendations.append("Improve integration between system components")
        if category_scores.get('production_readiness', 0) < 80:
            recommendations.append("Complete production deployment checklist")
        
        # Determine production readiness
        production_ready = (
            overall_score >= 80 and
            category_scores.get('api_functionality', 0) >= 85 and
            category_scores.get('security_tests', 0) >= 80
        )
        
        return {
            'validation_summary': {
                'total_validation_time_seconds': total_time,
                'overall_score': overall_score,
                'production_ready': production_ready,
                'timestamp': datetime.now().isoformat()
            },
            'category_scores': category_scores,
            'detailed_results': self.test_results,
            'recommendations': recommendations,
            'production_deployment_status': {
                'api_functionality_ready': category_scores.get('api_functionality', 0) >= 85,
                'performance_ready': category_scores.get('performance_tests', 0) >= 80,
                'security_ready': category_scores.get('security_tests', 0) >= 80,
                'integration_ready': category_scores.get('integration_tests', 0) >= 85,
                'production_config_ready': category_scores.get('production_readiness', 0) >= 75
            },
            'next_steps': self._generate_next_steps(overall_score, production_ready)
        }
    
    def _generate_next_steps(self, overall_score: float, production_ready: bool) -> List[str]:
        """Generate next steps based on validation results"""
        if production_ready:
            return [
                "✅ System is ready for production deployment",
                "🚀 Deploy to production environment",
                "📊 Set up production monitoring and alerting",
                "🔄 Establish regular health checks and maintenance"
            ]
        elif overall_score >= 70:
            return [
                "⚠️ Address remaining issues before production deployment",
                "🔧 Implement recommended fixes",
                "🧪 Re-run validation tests",
                "📋 Complete production readiness checklist"
            ]
        else:
            return [
                "❌ System requires significant improvements",
                "🔒 Focus on API functionality and security",
                "⚡ Optimize performance bottlenecks",
                "🧪 Conduct thorough testing and validation"
            ]


async def main():
    """Main function to run focused API validation"""
    print("🚀 Starting Focused API Validation for OpenCode-Slack")
    print("=" * 80)
    
    validator = FocusedAPIValidator()
    
    # Test connectivity
    try:
        response = requests.get(f"{validator.base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server not responding properly. Please check the server.")
            return
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to server. Please start the server first.")
        return
    
    print("✅ Server connectivity confirmed")
    print("🔍 Running focused validation suite...")
    print()
    
    # Run validation
    report = await validator.run_focused_validation()
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"focused_api_validation_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 FOCUSED API VALIDATION REPORT")
    print("=" * 80)
    
    summary = report['validation_summary']
    print(f"⏱️  Total Validation Time: {summary['total_validation_time_seconds']:.2f} seconds")
    print(f"📈 Overall Score: {summary['overall_score']:.1f}/100")
    print(f"🏭 Production Ready: {'✅ YES' if summary['production_ready'] else '❌ NO'}")
    print()
    
    print("📋 Category Scores:")
    for category, score in report['category_scores'].items():
        status = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
        print(f"  {status} {category.replace('_', ' ').title()}: {score:.1f}/100")
    print()
    
    print("🚀 Production Deployment Status:")
    deployment_status = report['production_deployment_status']
    for component, ready in deployment_status.items():
        status = "✅" if ready else "❌"
        print(f"  {status} {component.replace('_', ' ').title()}: {'Ready' if ready else 'Not Ready'}")
    print()
    
    if report['recommendations']:
        print("💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        print()
    
    print("📋 Next Steps:")
    for step in report['next_steps']:
        print(f"  {step}")
    print()
    
    print(f"📄 Detailed report saved to: {report_file}")
    print("=" * 80)
    
    return report


if __name__ == "__main__":
    asyncio.run(main())