#!/usr/bin/env python3
"""
Comprehensive Performance and Load Testing Suite for OpenCode-Slack Agent Orchestration System

This suite evaluates:
1. System response times under various load conditions
2. Throughput capacity for task processing
3. Resource utilization (CPU, memory, network) during peak loads
4. Scalability limits and performance degradation points
5. Agent response times during high concurrent task execution
6. System stability under sustained load
7. Performance of communication channels under stress
"""

import asyncio
import concurrent.futures
import json
import logging
import multiprocessing
import os
import psutil
import random
import requests
import statistics
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import subprocess

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.utils.opencode_wrapper import OpencodeSessionManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Collects and analyzes performance metrics"""
    
    def __init__(self):
        self.response_times = []
        self.throughput_data = []
        self.resource_usage = []
        self.error_counts = defaultdict(int)
        self.start_time = None
        self.end_time = None
        
    def record_response_time(self, operation: str, duration: float):
        """Record response time for an operation"""
        self.response_times.append({
            'operation': operation,
            'duration': duration,
            'timestamp': time.time()
        })
        
    def record_throughput(self, operations_per_second: float, timestamp: float = None):
        """Record throughput measurement"""
        self.throughput_data.append({
            'ops_per_second': operations_per_second,
            'timestamp': timestamp or time.time()
        })
        
    def record_resource_usage(self, cpu_percent: float, memory_mb: float, 
                            network_bytes_sent: int = 0, network_bytes_recv: int = 0):
        """Record system resource usage"""
        self.resource_usage.append({
            'cpu_percent': cpu_percent,
            'memory_mb': memory_mb,
            'network_bytes_sent': network_bytes_sent,
            'network_bytes_recv': network_bytes_recv,
            'timestamp': time.time()
        })
        
    def record_error(self, error_type: str):
        """Record an error occurrence"""
        self.error_counts[error_type] += 1
        
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate and return performance statistics"""
        stats = {
            'test_duration': self.end_time - self.start_time if self.end_time and self.start_time else 0,
            'total_operations': len(self.response_times),
            'total_errors': sum(self.error_counts.values()),
            'error_rate': 0,
            'response_times': {},
            'throughput': {},
            'resource_usage': {},
            'errors_by_type': dict(self.error_counts)
        }
        
        if self.response_times:
            durations = [rt['duration'] for rt in self.response_times]
            stats['response_times'] = {
                'mean': statistics.mean(durations),
                'median': statistics.median(durations),
                'min': min(durations),
                'max': max(durations),
                'p95': self._percentile(durations, 95),
                'p99': self._percentile(durations, 99),
                'std_dev': statistics.stdev(durations) if len(durations) > 1 else 0
            }
            
            stats['error_rate'] = stats['total_errors'] / stats['total_operations'] * 100
            
        if self.throughput_data:
            throughputs = [t['ops_per_second'] for t in self.throughput_data]
            stats['throughput'] = {
                'mean_ops_per_second': statistics.mean(throughputs),
                'peak_ops_per_second': max(throughputs),
                'min_ops_per_second': min(throughputs)
            }
            
        if self.resource_usage:
            cpu_usage = [r['cpu_percent'] for r in self.resource_usage]
            memory_usage = [r['memory_mb'] for r in self.resource_usage]
            
            stats['resource_usage'] = {
                'cpu': {
                    'mean_percent': statistics.mean(cpu_usage),
                    'peak_percent': max(cpu_usage),
                    'min_percent': min(cpu_usage)
                },
                'memory': {
                    'mean_mb': statistics.mean(memory_usage),
                    'peak_mb': max(memory_usage),
                    'min_mb': min(memory_usage)
                }
            }
            
        return stats
        
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

class SystemResourceMonitor:
    """Monitors system resource usage during tests"""
    
    def __init__(self, metrics: PerformanceMetrics, interval: float = 1.0):
        self.metrics = metrics
        self.interval = interval
        self.monitoring = False
        self.monitor_thread = None
        self.process = psutil.Process()
        
    def start_monitoring(self):
        """Start resource monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Resource monitoring started")
        
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Resource monitoring stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Get system-wide CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                
                # Get memory usage
                memory_info = psutil.virtual_memory()
                memory_mb = memory_info.used / (1024 * 1024)
                
                # Get network I/O
                net_io = psutil.net_io_counters()
                
                self.metrics.record_resource_usage(
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    network_bytes_sent=net_io.bytes_sent,
                    network_bytes_recv=net_io.bytes_recv
                )
                
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                time.sleep(self.interval)

class AgentOrchestrationLoadTester:
    """Main load testing class for the agent orchestration system"""
    
    def __init__(self, server_url: str = "http://localhost:8080"):
        self.server_url = server_url
        self.metrics = PerformanceMetrics()
        self.resource_monitor = SystemResourceMonitor(self.metrics)
        self.test_employees = []
        self.session = requests.Session()
        
        # Test configuration
        self.test_tasks = [
            "Create a simple HTML file with basic structure",
            "Add CSS styling to improve the layout",
            "Implement a JavaScript function for user interaction",
            "Write unit tests for the new functionality",
            "Update documentation with new features",
            "Optimize code for better performance",
            "Fix any linting issues in the codebase",
            "Add error handling to the application",
            "Implement logging for debugging purposes",
            "Create a configuration file for settings"
        ]
        
    def setup_test_environment(self):
        """Set up the test environment"""
        logger.info("Setting up test environment...")
        
        # Check if server is running
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=5)
            if response.status_code != 200:
                raise Exception(f"Server health check failed: {response.status_code}")
            logger.info("Server is running and healthy")
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            raise
            
        # Clean up any existing test employees
        self.cleanup_test_employees()
        
    def cleanup_test_environment(self):
        """Clean up the test environment"""
        logger.info("Cleaning up test environment...")
        self.cleanup_test_employees()
        
    def cleanup_test_employees(self):
        """Remove all test employees"""
        try:
            response = self.session.get(f"{self.server_url}/employees")
            if response.status_code == 200:
                employees = response.json().get('employees', [])
                for employee in employees:
                    if employee['name'].startswith('test_'):
                        self.session.delete(f"{self.server_url}/employees/{employee['name']}")
                        logger.debug(f"Removed test employee: {employee['name']}")
        except Exception as e:
            logger.warning(f"Error cleaning up test employees: {e}")
            
    def create_test_employees(self, count: int) -> List[str]:
        """Create test employees for load testing"""
        logger.info(f"Creating {count} test employees...")
        employees = []
        
        roles = ['developer', 'FS-developer', 'designer', 'tester']
        
        for i in range(count):
            employee_name = f"test_employee_{i:03d}"
            role = roles[i % len(roles)]
            
            start_time = time.time()
            try:
                response = self.session.post(
                    f"{self.server_url}/employees",
                    json={'name': employee_name, 'role': role},
                    timeout=10
                )
                
                duration = time.time() - start_time
                self.metrics.record_response_time('create_employee', duration)
                
                if response.status_code == 200:
                    employees.append(employee_name)
                    logger.debug(f"Created employee: {employee_name}")
                else:
                    self.metrics.record_error('create_employee_failed')
                    logger.error(f"Failed to create employee {employee_name}: {response.status_code}")
                    
            except Exception as e:
                duration = time.time() - start_time
                self.metrics.record_response_time('create_employee', duration)
                self.metrics.record_error('create_employee_exception')
                logger.error(f"Exception creating employee {employee_name}: {e}")
                
        self.test_employees = employees
        logger.info(f"Successfully created {len(employees)} test employees")
        return employees
        
    def assign_task_to_employee(self, employee_name: str, task: str) -> bool:
        """Assign a task to an employee and measure response time"""
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.server_url}/tasks",
                json={'name': employee_name, 'task': task},
                timeout=30
            )
            
            duration = time.time() - start_time
            self.metrics.record_response_time('assign_task', duration)
            
            if response.status_code == 200:
                logger.debug(f"Assigned task to {employee_name}: {task[:50]}...")
                return True
            else:
                self.metrics.record_error('assign_task_failed')
                logger.error(f"Failed to assign task to {employee_name}: {response.status_code}")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_response_time('assign_task', duration)
            self.metrics.record_error('assign_task_exception')
            logger.error(f"Exception assigning task to {employee_name}: {e}")
            return False
            
    def get_system_status(self) -> Dict:
        """Get system status and measure response time"""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.server_url}/status", timeout=10)
            
            duration = time.time() - start_time
            self.metrics.record_response_time('get_status', duration)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.metrics.record_error('get_status_failed')
                return {}
                
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_response_time('get_status', duration)
            self.metrics.record_error('get_status_exception')
            logger.error(f"Exception getting system status: {e}")
            return {}
            
    def test_concurrent_task_assignment(self, num_employees: int, num_tasks_per_employee: int):
        """Test concurrent task assignment to multiple employees"""
        logger.info(f"Testing concurrent task assignment: {num_employees} employees, {num_tasks_per_employee} tasks each")
        
        employees = self.create_test_employees(num_employees)
        if not employees:
            logger.error("No employees created, skipping concurrent task test")
            return
            
        # Create task assignments
        task_assignments = []
        for employee in employees:
            for i in range(num_tasks_per_employee):
                task = random.choice(self.test_tasks)
                task_assignments.append((employee, f"{task} (task {i+1})"))
                
        # Execute assignments concurrently
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(20, len(task_assignments))) as executor:
            futures = [
                executor.submit(self.assign_task_to_employee, employee, task)
                for employee, task in task_assignments
            ]
            
            # Wait for all tasks to complete
            completed = 0
            for future in concurrent.futures.as_completed(futures, timeout=300):
                try:
                    result = future.result()
                    if result:
                        completed += 1
                except Exception as e:
                    logger.error(f"Task assignment failed: {e}")
                    self.metrics.record_error('concurrent_task_failed')
                    
        duration = time.time() - start_time
        throughput = len(task_assignments) / duration
        self.metrics.record_throughput(throughput)
        
        logger.info(f"Concurrent task assignment completed: {completed}/{len(task_assignments)} successful in {duration:.2f}s")
        logger.info(f"Throughput: {throughput:.2f} tasks/second")
        
    def test_system_scalability(self, max_employees: int = 50, step_size: int = 10):
        """Test system scalability by gradually increasing load"""
        logger.info(f"Testing system scalability up to {max_employees} employees")
        
        scalability_results = []
        
        for num_employees in range(step_size, max_employees + 1, step_size):
            logger.info(f"Testing with {num_employees} employees...")
            
            # Clean up previous test
            self.cleanup_test_employees()
            time.sleep(2)  # Allow cleanup to complete
            
            # Create employees for this test
            employees = self.create_test_employees(num_employees)
            if len(employees) < num_employees * 0.8:  # If less than 80% created successfully
                logger.warning(f"Only created {len(employees)}/{num_employees} employees, system may be overloaded")
                
            # Assign one task to each employee
            start_time = time.time()
            successful_assignments = 0
            
            for employee in employees:
                task = random.choice(self.test_tasks)
                if self.assign_task_to_employee(employee, task):
                    successful_assignments += 1
                    
            duration = time.time() - start_time
            throughput = successful_assignments / duration if duration > 0 else 0
            
            # Get system status
            status = self.get_system_status()
            
            result = {
                'num_employees': num_employees,
                'successful_assignments': successful_assignments,
                'duration': duration,
                'throughput': throughput,
                'active_sessions': len(status.get('active_sessions', {})),
                'locked_files': len(status.get('locked_files', {}))
            }
            
            scalability_results.append(result)
            logger.info(f"Scalability test result: {result}")
            
            # Check for performance degradation
            if len(scalability_results) > 1:
                prev_throughput = scalability_results[-2]['throughput']
                current_throughput = result['throughput']
                degradation = (prev_throughput - current_throughput) / prev_throughput * 100
                
                if degradation > 20:  # More than 20% degradation
                    logger.warning(f"Performance degradation detected: {degradation:.1f}% drop in throughput")
                    
        return scalability_results
        
    def test_sustained_load(self, num_employees: int = 20, duration_minutes: int = 10):
        """Test system stability under sustained load"""
        logger.info(f"Testing sustained load: {num_employees} employees for {duration_minutes} minutes")
        
        employees = self.create_test_employees(num_employees)
        if not employees:
            logger.error("No employees created, skipping sustained load test")
            return
            
        end_time = time.time() + (duration_minutes * 60)
        task_count = 0
        
        while time.time() < end_time:
            # Assign tasks to random employees
            employee = random.choice(employees)
            task = random.choice(self.test_tasks)
            
            if self.assign_task_to_employee(employee, f"{task} (sustained test {task_count})"):
                task_count += 1
                
            # Get system status periodically
            if task_count % 10 == 0:
                status = self.get_system_status()
                logger.debug(f"Sustained load status: {len(status.get('active_sessions', {}))} active sessions")
                
            # Small delay to prevent overwhelming the system
            time.sleep(random.uniform(0.5, 2.0))
            
        logger.info(f"Sustained load test completed: {task_count} tasks assigned over {duration_minutes} minutes")
        
    def test_communication_channel_performance(self):
        """Test performance of communication channels under stress"""
        logger.info("Testing communication channel performance...")
        
        # Test multiple rapid status requests
        start_time = time.time()
        status_requests = 100
        
        for i in range(status_requests):
            self.get_system_status()
            
        duration = time.time() - start_time
        throughput = status_requests / duration
        self.metrics.record_throughput(throughput)
        
        logger.info(f"Communication channel test: {status_requests} status requests in {duration:.2f}s")
        logger.info(f"Communication throughput: {throughput:.2f} requests/second")
        
    def run_comprehensive_performance_test(self):
        """Run the complete performance test suite"""
        logger.info("Starting comprehensive performance test suite...")
        self.metrics.start_time = time.time()
        
        try:
            # Start resource monitoring
            self.resource_monitor.start_monitoring()
            
            # Set up test environment
            self.setup_test_environment()
            
            # Test 1: Basic functionality and response times
            logger.info("=== Test 1: Basic Functionality ===")
            self.create_test_employees(5)
            for employee in self.test_employees[:3]:
                task = random.choice(self.test_tasks)
                self.assign_task_to_employee(employee, task)
            time.sleep(5)  # Allow tasks to start
            
            # Test 2: Concurrent task assignment
            logger.info("=== Test 2: Concurrent Task Assignment ===")
            self.test_concurrent_task_assignment(num_employees=10, num_tasks_per_employee=2)
            time.sleep(10)  # Allow tasks to process
            
            # Test 3: System scalability
            logger.info("=== Test 3: System Scalability ===")
            scalability_results = self.test_system_scalability(max_employees=30, step_size=5)
            
            # Test 4: Communication channel performance
            logger.info("=== Test 4: Communication Channel Performance ===")
            self.test_communication_channel_performance()
            
            # Test 5: Sustained load (shorter duration for demo)
            logger.info("=== Test 5: Sustained Load ===")
            self.test_sustained_load(num_employees=15, duration_minutes=3)
            
        except Exception as e:
            logger.error(f"Error during performance testing: {e}")
            self.metrics.record_error('test_suite_exception')
            
        finally:
            # Stop resource monitoring
            self.resource_monitor.stop_monitoring()
            
            # Clean up
            self.cleanup_test_environment()
            
            # Record end time
            self.metrics.end_time = time.time()
            
        logger.info("Performance test suite completed")
        
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        logger.info("Generating performance report...")
        
        stats = self.metrics.get_statistics()
        
        # Add system information
        system_info = {
            'cpu_cores': psutil.cpu_count(),
            'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'python_version': sys.version,
            'test_timestamp': datetime.now().isoformat()
        }
        
        # Performance analysis
        analysis = {
            'performance_grade': 'A',  # Will be calculated based on metrics
            'bottlenecks_identified': [],
            'recommendations': []
        }
        
        # Analyze response times
        if stats['response_times']:
            mean_response = stats['response_times']['mean']
            p95_response = stats['response_times']['p95']
            
            if mean_response > 5.0:
                analysis['bottlenecks_identified'].append('High average response time')
                analysis['recommendations'].append('Optimize task assignment logic')
                analysis['performance_grade'] = 'C'
            elif mean_response > 2.0:
                analysis['performance_grade'] = 'B'
                
            if p95_response > 10.0:
                analysis['bottlenecks_identified'].append('High P95 response time')
                analysis['recommendations'].append('Investigate slow operations')
                
        # Analyze error rate
        if stats['error_rate'] > 10:
            analysis['bottlenecks_identified'].append('High error rate')
            analysis['recommendations'].append('Improve error handling and system stability')
            analysis['performance_grade'] = 'D'
        elif stats['error_rate'] > 5:
            analysis['performance_grade'] = 'C'
            
        # Analyze resource usage
        if stats['resource_usage']:
            cpu_usage = stats['resource_usage']['cpu']
            memory_usage = stats['resource_usage']['memory']
            
            if cpu_usage['peak_percent'] > 90:
                analysis['bottlenecks_identified'].append('High CPU usage')
                analysis['recommendations'].append('Optimize CPU-intensive operations')
                
            if memory_usage['peak_mb'] > system_info['total_memory_gb'] * 1024 * 0.8:
                analysis['bottlenecks_identified'].append('High memory usage')
                analysis['recommendations'].append('Optimize memory usage and implement cleanup')
                
        report = {
            'system_info': system_info,
            'performance_metrics': stats,
            'analysis': analysis,
            'test_summary': {
                'total_duration_minutes': round(stats['test_duration'] / 60, 2),
                'total_operations': stats['total_operations'],
                'success_rate': round(100 - stats['error_rate'], 2),
                'average_throughput': stats['throughput'].get('mean_ops_per_second', 0)
            }
        }
        
        return report

def main():
    """Main function to run performance tests"""
    print("🚀 OpenCode-Slack Agent Orchestration Performance Test Suite")
    print("=" * 70)
    
    # Check if server is specified
    server_url = os.environ.get('OPENCODE_SERVER_URL', 'http://localhost:8080')
    print(f"Testing server: {server_url}")
    
    # Initialize load tester
    load_tester = AgentOrchestrationLoadTester(server_url)
    
    try:
        # Run comprehensive performance tests
        load_tester.run_comprehensive_performance_test()
        
        # Generate and save report
        report = load_tester.generate_performance_report()
        
        # Save report to file
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n📊 Performance Report Generated: {report_file}")
        print("=" * 70)
        
        # Print summary
        summary = report['test_summary']
        analysis = report['analysis']
        
        print(f"🎯 Performance Grade: {analysis['performance_grade']}")
        print(f"⏱️  Test Duration: {summary['total_duration_minutes']} minutes")
        print(f"📈 Total Operations: {summary['total_operations']}")
        print(f"✅ Success Rate: {summary['success_rate']}%")
        print(f"🚀 Average Throughput: {summary['average_throughput']:.2f} ops/sec")
        
        if analysis['bottlenecks_identified']:
            print(f"\n⚠️  Bottlenecks Identified:")
            for bottleneck in analysis['bottlenecks_identified']:
                print(f"   • {bottleneck}")
                
        if analysis['recommendations']:
            print(f"\n💡 Recommendations:")
            for recommendation in analysis['recommendations']:
                print(f"   • {recommendation}")
                
        # Print detailed metrics
        metrics = report['performance_metrics']
        if metrics['response_times']:
            rt = metrics['response_times']
            print(f"\n📊 Response Time Analysis:")
            print(f"   Mean: {rt['mean']:.3f}s")
            print(f"   Median: {rt['median']:.3f}s")
            print(f"   P95: {rt['p95']:.3f}s")
            print(f"   P99: {rt['p99']:.3f}s")
            print(f"   Max: {rt['max']:.3f}s")
            
        if metrics['resource_usage']:
            ru = metrics['resource_usage']
            print(f"\n💻 Resource Usage:")
            print(f"   Peak CPU: {ru['cpu']['peak_percent']:.1f}%")
            print(f"   Peak Memory: {ru['memory']['peak_mb']:.1f} MB")
            print(f"   Avg CPU: {ru['cpu']['mean_percent']:.1f}%")
            print(f"   Avg Memory: {ru['memory']['mean_mb']:.1f} MB")
            
        print("\n" + "=" * 70)
        print("✅ Performance testing completed successfully!")
        
        return report
        
    except KeyboardInterrupt:
        print("\n🛑 Performance testing interrupted by user")
        load_tester.cleanup_test_environment()
        return None
        
    except Exception as e:
        print(f"\n❌ Performance testing failed: {e}")
        logger.error(f"Performance testing failed: {e}", exc_info=True)
        load_tester.cleanup_test_environment()
        return None

if __name__ == "__main__":
    main()