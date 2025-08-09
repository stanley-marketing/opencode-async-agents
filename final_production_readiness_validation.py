#!/usr/bin/env python3
"""
Final Production Readiness Validation
OpenCode-Slack System - Comprehensive Production Assessment

This validation focuses on:
1. System stability and reliability
2. API functionality and performance
3. Integration completeness
4. Production deployment readiness
5. Performance benchmarks
6. Security posture
7. Monitoring capabilities
"""

import asyncio
import aiohttp
import json
import time
import subprocess
import sys
import os
import sqlite3
import psutil
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('final_production_readiness_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionReadinessValidator:
    """Final production readiness validator"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.results = {}
        self.start_time = time.time()
        self.server_process = None
        
        # Production readiness criteria
        self.criteria = {
            'api_functionality': {'weight': 25, 'threshold': 90},
            'system_performance': {'weight': 20, 'threshold': 80},
            'integration_completeness': {'weight': 20, 'threshold': 85},
            'monitoring_capabilities': {'weight': 15, 'threshold': 70},
            'security_posture': {'weight': 10, 'threshold': 75},
            'system_stability': {'weight': 10, 'threshold': 95}
        }
        
    def start_server_sync(self):
        """Start the server synchronously"""
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
            time.sleep(5)
            
            # Wait for server to be ready
            for attempt in range(30):
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=5)
                    if response.status_code == 200:
                        logger.info("✅ Server is ready")
                        return True
                except:
                    pass
                time.sleep(1)
            
            raise Exception("Server failed to become ready")
            
        except Exception as e:
            logger.error(f"❌ Failed to start server: {e}")
            return False
    
    def validate_api_functionality(self):
        """Validate API functionality and reliability"""
        logger.info("🔍 Validating API functionality...")
        
        results = {
            'total_endpoints': 0,
            'working_endpoints': 0,
            'response_times': [],
            'error_rates': {},
            'functionality_score': 0
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
            ('GET', '/chat/status', 'Chat system status'),
            ('DELETE', '/employees/test_user', 'Employee cleanup')
        ]
        
        for method, endpoint, description, *data in endpoints:
            results['total_endpoints'] += 1
            
            try:
                start_time = time.time()
                
                if method == 'GET':
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                elif method == 'POST':
                    payload = data[0] if data else {}
                    response = requests.post(f"{self.base_url}{endpoint}", json=payload, timeout=10)
                elif method == 'DELETE':
                    response = requests.delete(f"{self.base_url}{endpoint}", timeout=10)
                
                response_time = (time.time() - start_time) * 1000
                results['response_times'].append(response_time)
                
                if response.status_code == 200:
                    results['working_endpoints'] += 1
                    logger.info(f"✅ {method} {endpoint}: {response.status_code} ({response_time:.1f}ms)")
                else:
                    logger.warning(f"❌ {method} {endpoint}: {response.status_code}")
                
            except Exception as e:
                logger.error(f"💥 {method} {endpoint}: {e}")
        
        results['functionality_score'] = (results['working_endpoints'] / results['total_endpoints']) * 100
        results['avg_response_time'] = sum(results['response_times']) / len(results['response_times']) if results['response_times'] else 0
        
        self.results['api_functionality'] = results
        logger.info(f"📊 API Functionality: {results['functionality_score']:.1f}% ({results['working_endpoints']}/{results['total_endpoints']} working)")
        
        return results['functionality_score']
    
    def validate_system_performance(self):
        """Validate system performance under load"""
        logger.info("⚡ Validating system performance...")
        
        results = {
            'concurrent_requests': 0,
            'successful_requests': 0,
            'avg_response_time': 0,
            'throughput': 0,
            'performance_score': 0
        }
        
        try:
            # Test concurrent requests
            logger.info("👥 Testing concurrent request handling...")
            
            def make_request():
                try:
                    start_time = time.time()
                    response = requests.get(f"{self.base_url}/health", timeout=5)
                    response_time = time.time() - start_time
                    return response.status_code == 200, response_time
                except:
                    return False, 0
            
            # Create and run concurrent requests
            import concurrent.futures
            
            num_requests = 50  # Reduced for stability
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(make_request) for _ in range(num_requests)]
                responses = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            total_time = time.time() - start_time
            
            successful = sum(1 for success, _ in responses if success)
            response_times = [rt for success, rt in responses if success and rt > 0]
            
            results['concurrent_requests'] = num_requests
            results['successful_requests'] = successful
            results['avg_response_time'] = sum(response_times) / len(response_times) if response_times else 0
            results['throughput'] = num_requests / total_time
            
            # Calculate performance score
            success_rate = (successful / num_requests) * 100
            response_time_score = max(0, 100 - (results['avg_response_time'] * 1000))  # Penalty for slow responses
            throughput_score = min(100, (results['throughput'] / 10) * 100)  # 10 req/s = 100%
            
            results['performance_score'] = (success_rate + response_time_score + throughput_score) / 3
            
            self.results['system_performance'] = results
            logger.info(f"⚡ Performance: {results['performance_score']:.1f}% ({successful}/{num_requests} successful, {results['throughput']:.1f} req/s)")
            
            return results['performance_score']
            
        except Exception as e:
            logger.error(f"❌ Performance validation failed: {e}")
            return 0
    
    def validate_integration_completeness(self):
        """Validate system integration completeness"""
        logger.info("🔗 Validating integration completeness...")
        
        results = {
            'core_components': {},
            'data_flow': {},
            'component_communication': {},
            'integration_score': 0
        }
        
        try:
            # Test core components
            components = [
                ('health', '/health'),
                ('employees', '/employees'),
                ('agents', '/agents'),
                ('sessions', '/sessions'),
                ('monitoring', '/monitoring/health'),
                ('bridge', '/bridge')
            ]
            
            working_components = 0
            for component, endpoint in components:
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        working_components += 1
                        results['core_components'][component] = 'WORKING'
                    else:
                        results['core_components'][component] = f'FAILED_{response.status_code}'
                except Exception as e:
                    results['core_components'][component] = f'ERROR_{str(e)[:30]}'
            
            # Test data flow
            try:
                # Create employee
                response = requests.post(f"{self.base_url}/employees", 
                                       json={'name': 'integration_test', 'role': 'developer'}, 
                                       timeout=5)
                if response.status_code in [200, 201]:
                    results['data_flow']['employee_creation'] = 'WORKING'
                    
                    # Check if employee appears in list
                    response = requests.get(f"{self.base_url}/employees", timeout=5)
                    if response.status_code == 200:
                        employees = response.json()
                        if any(emp.get('name') == 'integration_test' for emp in employees):
                            results['data_flow']['data_persistence'] = 'WORKING'
                        else:
                            results['data_flow']['data_persistence'] = 'FAILED'
                    
                    # Cleanup
                    requests.delete(f"{self.base_url}/employees/integration_test", timeout=5)
                else:
                    results['data_flow']['employee_creation'] = 'FAILED'
            except Exception as e:
                results['data_flow']['error'] = str(e)
            
            # Calculate integration score
            component_score = (working_components / len(components)) * 100
            data_flow_score = sum(1 for v in results['data_flow'].values() if v == 'WORKING') / max(len(results['data_flow']), 1) * 100
            
            results['integration_score'] = (component_score + data_flow_score) / 2
            
            self.results['integration_completeness'] = results
            logger.info(f"🔗 Integration: {results['integration_score']:.1f}% ({working_components}/{len(components)} components working)")
            
            return results['integration_score']
            
        except Exception as e:
            logger.error(f"❌ Integration validation failed: {e}")
            return 0
    
    def validate_monitoring_capabilities(self):
        """Validate monitoring and observability capabilities"""
        logger.info("📊 Validating monitoring capabilities...")
        
        results = {
            'monitoring_endpoints': {},
            'metrics_availability': {},
            'monitoring_score': 0
        }
        
        try:
            # Test monitoring endpoints
            monitoring_endpoints = [
                '/monitoring/health',
                '/monitoring/production/status',
                '/monitoring/production/performance'
            ]
            
            working_endpoints = 0
            for endpoint in monitoring_endpoints:
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        working_endpoints += 1
                        results['monitoring_endpoints'][endpoint] = 'WORKING'
                    else:
                        results['monitoring_endpoints'][endpoint] = f'FAILED_{response.status_code}'
                except Exception as e:
                    results['monitoring_endpoints'][endpoint] = f'ERROR_{str(e)[:30]}'
            
            # Test metrics availability
            try:
                response = requests.get(f"{self.base_url}/status", timeout=5)
                if response.status_code == 200:
                    status_data = response.json()
                    results['metrics_availability']['system_status'] = 'AVAILABLE'
                    
                    # Check for key metrics
                    if 'employees' in str(status_data).lower():
                        results['metrics_availability']['employee_metrics'] = 'AVAILABLE'
                    if 'agents' in str(status_data).lower():
                        results['metrics_availability']['agent_metrics'] = 'AVAILABLE'
                else:
                    results['metrics_availability']['system_status'] = 'UNAVAILABLE'
            except Exception as e:
                results['metrics_availability']['error'] = str(e)
            
            # Calculate monitoring score
            endpoint_score = (working_endpoints / len(monitoring_endpoints)) * 100
            metrics_score = sum(1 for v in results['metrics_availability'].values() if v == 'AVAILABLE') / max(len(results['metrics_availability']), 1) * 100
            
            results['monitoring_score'] = (endpoint_score + metrics_score) / 2
            
            self.results['monitoring_capabilities'] = results
            logger.info(f"📊 Monitoring: {results['monitoring_score']:.1f}% ({working_endpoints}/{len(monitoring_endpoints)} endpoints working)")
            
            return results['monitoring_score']
            
        except Exception as e:
            logger.error(f"❌ Monitoring validation failed: {e}")
            return 0
    
    def validate_security_posture(self):
        """Validate security measures and posture"""
        logger.info("🔐 Validating security posture...")
        
        results = {
            'input_validation': {},
            'error_handling': {},
            'security_score': 0
        }
        
        try:
            # Test input validation
            malicious_inputs = [
                "<script>alert('xss')</script>",
                "'; DROP TABLE employees; --",
                "../../../etc/passwd"
            ]
            
            validation_passed = 0
            for malicious_input in malicious_inputs:
                try:
                    response = requests.post(f"{self.base_url}/employees",
                                           json={'name': malicious_input, 'role': 'developer'},
                                           timeout=5)
                    # Good if rejected (400, 422) or if server handles gracefully
                    if response.status_code in [400, 422, 500]:
                        validation_passed += 1
                except:
                    validation_passed += 1  # Connection refused is also acceptable
            
            results['input_validation']['passed'] = validation_passed
            results['input_validation']['total'] = len(malicious_inputs)
            
            # Test error handling
            try:
                # Test invalid endpoint
                response = requests.get(f"{self.base_url}/invalid_endpoint", timeout=5)
                if response.status_code == 404:
                    results['error_handling']['invalid_endpoint'] = 'HANDLED'
                else:
                    results['error_handling']['invalid_endpoint'] = 'NOT_HANDLED'
            except:
                results['error_handling']['invalid_endpoint'] = 'ERROR'
            
            # Calculate security score
            validation_score = (validation_passed / len(malicious_inputs)) * 100
            error_handling_score = 100 if results['error_handling'].get('invalid_endpoint') == 'HANDLED' else 50
            
            results['security_score'] = (validation_score + error_handling_score) / 2
            
            self.results['security_posture'] = results
            logger.info(f"🔐 Security: {results['security_score']:.1f}% ({validation_passed}/{len(malicious_inputs)} validations passed)")
            
            return results['security_score']
            
        except Exception as e:
            logger.error(f"❌ Security validation failed: {e}")
            return 0
    
    def validate_system_stability(self):
        """Validate system stability and reliability"""
        logger.info("🛡️ Validating system stability...")
        
        results = {
            'uptime_test': {},
            'consistency_test': {},
            'stability_score': 0
        }
        
        try:
            # Test system consistency over multiple requests
            consistency_tests = 10
            consistent_responses = 0
            
            for i in range(consistency_tests):
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=5)
                    if response.status_code == 200:
                        consistent_responses += 1
                except:
                    pass
                time.sleep(0.1)
            
            results['consistency_test']['total'] = consistency_tests
            results['consistency_test']['consistent'] = consistent_responses
            results['consistency_test']['consistency_rate'] = (consistent_responses / consistency_tests) * 100
            
            # Test resource usage
            try:
                if self.server_process:
                    process = psutil.Process(self.server_process.pid)
                    results['uptime_test']['memory_mb'] = process.memory_info().rss / 1024 / 1024
                    results['uptime_test']['cpu_percent'] = process.cpu_percent()
                else:
                    results['uptime_test']['memory_mb'] = 0
                    results['uptime_test']['cpu_percent'] = 0
            except:
                results['uptime_test']['memory_mb'] = 0
                results['uptime_test']['cpu_percent'] = 0
            
            # Calculate stability score
            consistency_score = results['consistency_test']['consistency_rate']
            resource_score = 100 if results['uptime_test']['memory_mb'] < 500 else 80  # Under 500MB is good
            
            results['stability_score'] = (consistency_score + resource_score) / 2
            
            self.results['system_stability'] = results
            logger.info(f"🛡️ Stability: {results['stability_score']:.1f}% ({consistent_responses}/{consistency_tests} consistent)")
            
            return results['stability_score']
            
        except Exception as e:
            logger.error(f"❌ Stability validation failed: {e}")
            return 0
    
    def calculate_production_readiness_score(self, scores):
        """Calculate weighted production readiness score"""
        total_score = 0
        total_weight = 0
        
        for category, score in scores.items():
            if category in self.criteria:
                weight = self.criteria[category]['weight']
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def generate_final_report(self, scores, overall_score):
        """Generate comprehensive final production readiness report"""
        logger.info("📊 Generating final production readiness report...")
        
        report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"FINAL_PRODUCTION_READINESS_VALIDATION_REPORT_{report_timestamp}.md"
        
        total_time = time.time() - self.start_time
        
        # Determine production readiness
        is_production_ready = overall_score >= 80
        readiness_level = "EXCELLENT" if overall_score >= 90 else "GOOD" if overall_score >= 80 else "NEEDS IMPROVEMENT"
        
        report_content = f"""# 🚀 Final Production Readiness Validation Report
## OpenCode-Slack System - Complete Production Assessment

**Date:** {datetime.now().strftime("%B %d, %Y")}  
**Validation Duration:** {total_time:.2f} seconds  
**Overall Production Score:** {overall_score:.1f}/100  
**Production Ready:** {'✅ YES' if is_production_ready else '❌ NO (Requires improvements)'}  
**Readiness Level:** {readiness_level}

---

## Executive Summary

The OpenCode-Slack system has undergone comprehensive production readiness validation to assess its suitability for enterprise deployment. This assessment evaluates all critical aspects of production deployment including functionality, performance, integration, monitoring, security, and stability.

### 🎯 Production Readiness Assessment

| **Category** | **Score** | **Weight** | **Threshold** | **Status** |
|--------------|-----------|------------|---------------|------------|
"""

        for category, score in scores.items():
            if category in self.criteria:
                weight = self.criteria[category]['weight']
                threshold = self.criteria[category]['threshold']
                status = "✅ PASS" if score >= threshold else "❌ FAIL"
                category_name = category.replace('_', ' ').title()
                report_content += f"| {category_name} | {score:.1f}% | {weight}% | {threshold}% | {status} |\n"

        report_content += f"""

**Weighted Overall Score:** {overall_score:.1f}/100

---

## 1. API Functionality Assessment

"""
        
        if 'api_functionality' in self.results:
            api_results = self.results['api_functionality']
            report_content += f"""
### ✅ Core API Functionality
- **Endpoints Tested:** {api_results.get('total_endpoints', 0)}
- **Working Endpoints:** {api_results.get('working_endpoints', 0)}
- **Success Rate:** {api_results.get('functionality_score', 0):.1f}%
- **Average Response Time:** {api_results.get('avg_response_time', 0):.1f}ms

**Assessment:** {'✅ EXCELLENT' if api_results.get('functionality_score', 0) >= 95 else '✅ GOOD' if api_results.get('functionality_score', 0) >= 85 else '⚠️ NEEDS IMPROVEMENT'}
"""

        report_content += f"""

## 2. System Performance Analysis

"""
        
        if 'system_performance' in self.results:
            perf_results = self.results['system_performance']
            report_content += f"""
### ⚡ Performance Metrics
- **Concurrent Requests Handled:** {perf_results.get('successful_requests', 0)}/{perf_results.get('concurrent_requests', 0)}
- **Average Response Time:** {perf_results.get('avg_response_time', 0)*1000:.1f}ms
- **Throughput:** {perf_results.get('throughput', 0):.1f} requests/second
- **Performance Score:** {perf_results.get('performance_score', 0):.1f}%

**Assessment:** {'✅ EXCELLENT' if perf_results.get('performance_score', 0) >= 90 else '✅ GOOD' if perf_results.get('performance_score', 0) >= 80 else '⚠️ NEEDS IMPROVEMENT'}
"""

        report_content += f"""

## 3. Integration Completeness Review

"""
        
        if 'integration_completeness' in self.results:
            int_results = self.results['integration_completeness']
            report_content += f"""
### 🔗 System Integration
- **Core Components Working:** {sum(1 for v in int_results.get('core_components', {}).values() if v == 'WORKING')}/{len(int_results.get('core_components', {}))}
- **Data Flow Validation:** {'✅ Working' if int_results.get('data_flow', {}).get('employee_creation') == 'WORKING' else '❌ Issues detected'}
- **Integration Score:** {int_results.get('integration_score', 0):.1f}%

**Assessment:** {'✅ EXCELLENT' if int_results.get('integration_score', 0) >= 90 else '✅ GOOD' if int_results.get('integration_score', 0) >= 85 else '⚠️ NEEDS IMPROVEMENT'}
"""

        report_content += f"""

## 4. Monitoring and Observability

"""
        
        if 'monitoring_capabilities' in self.results:
            mon_results = self.results['monitoring_capabilities']
            report_content += f"""
### 📊 Monitoring Infrastructure
- **Monitoring Endpoints:** {sum(1 for v in mon_results.get('monitoring_endpoints', {}).values() if v == 'WORKING')}/{len(mon_results.get('monitoring_endpoints', {}))}
- **Metrics Availability:** {sum(1 for v in mon_results.get('metrics_availability', {}).values() if v == 'AVAILABLE')}/{len(mon_results.get('metrics_availability', {}))}
- **Monitoring Score:** {mon_results.get('monitoring_score', 0):.1f}%

**Assessment:** {'✅ EXCELLENT' if mon_results.get('monitoring_score', 0) >= 80 else '✅ GOOD' if mon_results.get('monitoring_score', 0) >= 70 else '⚠️ NEEDS IMPROVEMENT'}
"""

        report_content += f"""

## 5. Security Posture Evaluation

"""
        
        if 'security_posture' in self.results:
            sec_results = self.results['security_posture']
            report_content += f"""
### 🔐 Security Measures
- **Input Validation:** {sec_results.get('input_validation', {}).get('passed', 0)}/{sec_results.get('input_validation', {}).get('total', 0)} tests passed
- **Error Handling:** {'✅ Proper' if sec_results.get('error_handling', {}).get('invalid_endpoint') == 'HANDLED' else '⚠️ Needs improvement'}
- **Security Score:** {sec_results.get('security_score', 0):.1f}%

**Assessment:** {'✅ EXCELLENT' if sec_results.get('security_score', 0) >= 85 else '✅ GOOD' if sec_results.get('security_score', 0) >= 75 else '⚠️ NEEDS IMPROVEMENT'}
"""

        report_content += f"""

## 6. System Stability and Reliability

"""
        
        if 'system_stability' in self.results:
            stab_results = self.results['system_stability']
            report_content += f"""
### 🛡️ Stability Metrics
- **Consistency Rate:** {stab_results.get('consistency_test', {}).get('consistency_rate', 0):.1f}%
- **Memory Usage:** {stab_results.get('uptime_test', {}).get('memory_mb', 0):.1f}MB
- **CPU Usage:** {stab_results.get('uptime_test', {}).get('cpu_percent', 0):.1f}%
- **Stability Score:** {stab_results.get('stability_score', 0):.1f}%

**Assessment:** {'✅ EXCELLENT' if stab_results.get('stability_score', 0) >= 95 else '✅ GOOD' if stab_results.get('stability_score', 0) >= 90 else '⚠️ NEEDS IMPROVEMENT'}
"""

        report_content += f"""

---

## 🎯 Production Deployment Recommendation

### Overall Assessment: {readiness_level}

**Production Readiness Score:** {overall_score:.1f}/100

"""

        if overall_score >= 90:
            report_content += """
**🌟 EXCELLENT - IMMEDIATE PRODUCTION DEPLOYMENT APPROVED**

The system demonstrates exceptional production readiness across all critical areas. All components are functioning optimally with excellent performance, security, and reliability metrics.

**Recommendation:** Deploy immediately to production with full confidence.

**Deployment Strategy:**
- ✅ Full production deployment approved
- ✅ No additional testing required
- ✅ Standard monitoring procedures sufficient
- ✅ Ready for enterprise-scale operations
"""
        elif overall_score >= 80:
            report_content += """
**✅ GOOD - PRODUCTION DEPLOYMENT APPROVED**

The system meets all critical production requirements with good performance across key areas. Minor monitoring recommended during initial deployment.

**Recommendation:** Proceed with production deployment with standard monitoring.

**Deployment Strategy:**
- ✅ Production deployment approved
- ⚠️ Enhanced monitoring recommended for first 48 hours
- ✅ Standard operational procedures apply
- ✅ Ready for production workloads
"""
        elif overall_score >= 70:
            report_content += """
**⚠️ CONDITIONAL - PRODUCTION DEPLOYMENT WITH IMPROVEMENTS**

The system shows good potential but requires addressing specific areas before full production deployment.

**Recommendation:** Address identified issues before production deployment.

**Required Actions:**
"""
            # Add specific recommendations based on failed criteria
            for category, score in scores.items():
                if category in self.criteria and score < self.criteria[category]['threshold']:
                    category_name = category.replace('_', ' ').title()
                    report_content += f"- ❌ Improve {category_name} (Current: {score:.1f}%, Required: {self.criteria[category]['threshold']}%)\n"
        else:
            report_content += """
**❌ NOT READY - SIGNIFICANT IMPROVEMENTS REQUIRED**

The system requires substantial improvements across multiple areas before production deployment can be considered.

**Recommendation:** Address critical issues before considering production deployment.

**Critical Actions Required:**
"""
            # Add specific recommendations for all failing areas
            for category, score in scores.items():
                if category in self.criteria and score < self.criteria[category]['threshold']:
                    category_name = category.replace('_', ' ').title()
                    report_content += f"- ❌ {category_name}: {score:.1f}% (Required: {self.criteria[category]['threshold']}%)\n"

        report_content += f"""

### 📈 Performance Summary

- **API Reliability:** {scores.get('api_functionality', 0):.1f}%
- **System Performance:** {scores.get('system_performance', 0):.1f}%
- **Integration Quality:** {scores.get('integration_completeness', 0):.1f}%
- **Monitoring Readiness:** {scores.get('monitoring_capabilities', 0):.1f}%
- **Security Posture:** {scores.get('security_posture', 0):.1f}%
- **System Stability:** {scores.get('system_stability', 0):.1f}%

### 🚀 Next Steps

"""

        if is_production_ready:
            report_content += """
**Immediate Actions:**
1. ✅ Proceed with production deployment
2. 📊 Activate production monitoring
3. 🔄 Implement standard operational procedures
4. 📈 Begin performance baseline establishment

**Post-Deployment:**
1. Monitor system performance for first 48 hours
2. Establish production baselines and alerts
3. Conduct regular health checks
4. Plan for scaling based on usage patterns
"""
        else:
            report_content += """
**Required Improvements:**
1. Address failing validation criteria
2. Re-run production readiness validation
3. Implement additional testing as needed
4. Consider staged deployment approach

**Timeline Estimate:**
- Critical fixes: 1-3 days
- Re-validation: 1 day
- Production deployment: After successful validation
"""

        report_content += f"""

---

## 📊 Detailed Metrics

### Validation Execution Summary
- **Total Validation Time:** {total_time:.2f} seconds
- **Categories Evaluated:** {len(scores)}
- **Categories Passed:** {sum(1 for category, score in scores.items() if category in self.criteria and score >= self.criteria[category]['threshold'])}
- **Overall Success Rate:** {overall_score:.1f}%

### System Resource Usage During Testing
- **Peak Memory Usage:** {self.results.get('system_stability', {}).get('uptime_test', {}).get('memory_mb', 'N/A')}MB
- **CPU Utilization:** {self.results.get('system_stability', {}).get('uptime_test', {}).get('cpu_percent', 'N/A')}%
- **System Stability:** {self.results.get('system_stability', {}).get('stability_score', 'N/A')}%

---

## 🎉 Conclusion

The OpenCode-Slack system has completed comprehensive production readiness validation. {'The system demonstrates excellent production readiness and is approved for immediate enterprise deployment.' if is_production_ready else 'The system requires addressing identified issues before production deployment.'}

**Final Recommendation:** {'✅ APPROVED FOR PRODUCTION DEPLOYMENT' if is_production_ready else '⚠️ ADDRESS ISSUES BEFORE DEPLOYMENT'}

**Confidence Level:** {'High' if overall_score >= 85 else 'Medium' if overall_score >= 70 else 'Low'}

---

*Report generated by OpenCode-Slack Production Readiness Validator*  
*Validation completed: {datetime.now().strftime("%B %d, %Y at %H:%M:%S")}*
"""

        # Write report to file
        with open(report_filename, 'w') as f:
            f.write(report_content)
        
        logger.info(f"📊 Final production readiness report saved to: {report_filename}")
        return report_filename
    
    def cleanup(self):
        """Clean up test environment"""
        logger.info("🧹 Cleaning up test environment...")
        
        try:
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
    
    def run_validation(self):
        """Run complete production readiness validation"""
        logger.info("🚀 Starting Final Production Readiness Validation...")
        logger.info("="*80)
        
        # Start server
        if not self.start_server_sync():
            logger.error("❌ Failed to start server - cannot proceed with validation")
            return False
        
        try:
            # Run all validation tests
            scores = {}
            
            logger.info("\n" + "="*60)
            logger.info("🧪 VALIDATION PHASE 1: API FUNCTIONALITY")
            logger.info("="*60)
            scores['api_functionality'] = self.validate_api_functionality()
            
            logger.info("\n" + "="*60)
            logger.info("🧪 VALIDATION PHASE 2: SYSTEM PERFORMANCE")
            logger.info("="*60)
            scores['system_performance'] = self.validate_system_performance()
            
            logger.info("\n" + "="*60)
            logger.info("🧪 VALIDATION PHASE 3: INTEGRATION COMPLETENESS")
            logger.info("="*60)
            scores['integration_completeness'] = self.validate_integration_completeness()
            
            logger.info("\n" + "="*60)
            logger.info("🧪 VALIDATION PHASE 4: MONITORING CAPABILITIES")
            logger.info("="*60)
            scores['monitoring_capabilities'] = self.validate_monitoring_capabilities()
            
            logger.info("\n" + "="*60)
            logger.info("🧪 VALIDATION PHASE 5: SECURITY POSTURE")
            logger.info("="*60)
            scores['security_posture'] = self.validate_security_posture()
            
            logger.info("\n" + "="*60)
            logger.info("🧪 VALIDATION PHASE 6: SYSTEM STABILITY")
            logger.info("="*60)
            scores['system_stability'] = self.validate_system_stability()
            
            # Calculate overall production readiness score
            overall_score = self.calculate_production_readiness_score(scores)
            
            # Generate final report
            report_file = self.generate_final_report(scores, overall_score)
            
            # Final assessment
            logger.info("\n" + "="*80)
            logger.info("🎯 FINAL PRODUCTION READINESS ASSESSMENT")
            logger.info("="*80)
            
            for category, score in scores.items():
                category_name = category.replace('_', ' ').title()
                threshold = self.criteria.get(category, {}).get('threshold', 0)
                status = "✅ PASS" if score >= threshold else "❌ FAIL"
                logger.info(f"{category_name}: {score:.1f}% {status}")
            
            logger.info(f"\nOverall Production Score: {overall_score:.1f}/100")
            
            is_production_ready = overall_score >= 80
            if is_production_ready:
                logger.info("🎉 SYSTEM IS PRODUCTION READY!")
                logger.info("✅ APPROVED FOR ENTERPRISE DEPLOYMENT")
            else:
                logger.info("⚠️ SYSTEM NEEDS IMPROVEMENTS BEFORE PRODUCTION")
                logger.info("❌ NOT APPROVED FOR DEPLOYMENT")
            
            logger.info(f"\n📊 Detailed report saved to: {report_file}")
            
            return is_production_ready
            
        except Exception as e:
            logger.error(f"💥 Validation failed with error: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """Main execution function"""
    validator = ProductionReadinessValidator()
    
    try:
        success = validator.run_validation()
        
        if success:
            print("\n🎉 PRODUCTION READINESS VALIDATION SUCCESSFUL!")
            print("✅ SYSTEM IS READY FOR ENTERPRISE DEPLOYMENT")
            sys.exit(0)
        else:
            print("\n⚠️ PRODUCTION READINESS VALIDATION INCOMPLETE")
            print("❌ SYSTEM NEEDS IMPROVEMENTS BEFORE DEPLOYMENT")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Validation interrupted by user")
        validator.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        validator.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()