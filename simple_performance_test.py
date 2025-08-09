#!/usr/bin/env python3
"""
Simplified Performance Test for OpenCode-Slack Agent Orchestration System
"""

import json
import requests
import time
import threading
import psutil
import statistics
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any

class SimplePerformanceTest:
    def __init__(self, server_url: str = "http://localhost:9090"):
        self.server_url = server_url
        self.session = requests.Session()
        self.metrics = {
            'response_times': [],
            'errors': [],
            'resource_usage': [],
            'throughput_data': []
        }
        self.test_employees = []
        
    def log(self, message: str):
        """Log message with timestamp"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def record_response_time(self, operation: str, duration: float):
        """Record response time"""
        self.metrics['response_times'].append({
            'operation': operation,
            'duration': duration,
            'timestamp': time.time()
        })
        
    def record_error(self, error_type: str, details: str = ""):
        """Record error"""
        self.metrics['errors'].append({
            'type': error_type,
            'details': details,
            'timestamp': time.time()
        })
        
    def monitor_resources(self, duration: int = 60):
        """Monitor system resources for specified duration"""
        def monitor():
            end_time = time.time() + duration
            while time.time() < end_time:
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    
                    self.metrics['resource_usage'].append({
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory.used / (1024 * 1024),
                        'memory_percent': memory.percent,
                        'timestamp': time.time()
                    })
                except Exception as e:
                    self.log(f"Error monitoring resources: {e}")
                    
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        return monitor_thread
        
    def test_server_health(self) -> bool:
        """Test server health endpoint"""
        self.log("Testing server health...")
        start_time = time.time()
        
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=10)
            duration = time.time() - start_time
            self.record_response_time('health_check', duration)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Server healthy: {data}")
                return True
            else:
                self.record_error('health_check_failed', f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.record_response_time('health_check', duration)
            self.record_error('health_check_exception', str(e))
            self.log(f"❌ Health check failed: {e}")
            return False
            
    def create_employee(self, name: str, role: str = "developer") -> bool:
        """Create a test employee"""
        start_time = time.time()
        
        try:
            response = self.session.post(
                f"{self.server_url}/employees",
                json={'name': name, 'role': role},
                timeout=15
            )
            
            duration = time.time() - start_time
            self.record_response_time('create_employee', duration)
            
            if response.status_code == 200:
                self.test_employees.append(name)
                self.log(f"✅ Created employee: {name}")
                return True
            else:
                self.record_error('create_employee_failed', f"Status: {response.status_code}")
                self.log(f"❌ Failed to create employee {name}: {response.status_code}")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.record_response_time('create_employee', duration)
            self.record_error('create_employee_exception', str(e))
            self.log(f"❌ Exception creating employee {name}: {e}")
            return False
            
    def assign_task(self, employee_name: str, task: str) -> bool:
        """Assign a task to an employee"""
        start_time = time.time()
        
        try:
            response = self.session.post(
                f"{self.server_url}/tasks",
                json={'name': employee_name, 'task': task},
                timeout=30
            )
            
            duration = time.time() - start_time
            self.record_response_time('assign_task', duration)
            
            if response.status_code == 200:
                self.log(f"✅ Assigned task to {employee_name}: {task[:50]}...")
                return True
            else:
                self.record_error('assign_task_failed', f"Status: {response.status_code}")
                self.log(f"❌ Failed to assign task to {employee_name}: {response.status_code}")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.record_response_time('assign_task', duration)
            self.record_error('assign_task_exception', str(e))
            self.log(f"❌ Exception assigning task to {employee_name}: {e}")
            return False
            
    def get_system_status(self) -> Dict:
        """Get system status"""
        start_time = time.time()
        
        try:
            response = self.session.get(f"{self.server_url}/status", timeout=10)
            duration = time.time() - start_time
            self.record_response_time('get_status', duration)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.record_error('get_status_failed', f"Status: {response.status_code}")
                return {}
                
        except Exception as e:
            duration = time.time() - start_time
            self.record_response_time('get_status', duration)
            self.record_error('get_status_exception', str(e))
            return {}
            
    def cleanup_employees(self):
        """Clean up test employees"""
        self.log("Cleaning up test employees...")
        
        for employee_name in self.test_employees:
            try:
                response = self.session.delete(f"{self.server_url}/employees/{employee_name}")
                if response.status_code == 200:
                    self.log(f"✅ Removed employee: {employee_name}")
                else:
                    self.log(f"⚠️ Failed to remove employee {employee_name}: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Exception removing employee {employee_name}: {e}")
                
        self.test_employees.clear()
        
    def test_basic_functionality(self):
        """Test basic system functionality"""
        self.log("=== Testing Basic Functionality ===")
        
        # Test 1: Server health
        if not self.test_server_health():
            return False
            
        # Test 2: Create employees
        self.log("Creating test employees...")
        employees_created = 0
        for i in range(5):
            if self.create_employee(f"perf_test_{i}", "developer"):
                employees_created += 1
                
        self.log(f"Created {employees_created}/5 employees")
        
        # Test 3: Assign tasks
        self.log("Assigning tasks...")
        tasks_assigned = 0
        test_tasks = [
            "Create a simple HTML file",
            "Add CSS styling",
            "Write a JavaScript function",
            "Add error handling",
            "Update documentation"
        ]
        
        for i, employee in enumerate(self.test_employees[:5]):
            if self.assign_task(employee, test_tasks[i % len(test_tasks)]):
                tasks_assigned += 1
                
        self.log(f"Assigned {tasks_assigned} tasks")
        
        # Test 4: Check system status
        status = self.get_system_status()
        if status:
            self.log(f"System status: {status.get('active_sessions', 0)} active sessions")
            
        return True
        
    def test_concurrent_operations(self, num_employees: int = 10, num_tasks: int = 20):
        """Test concurrent operations"""
        self.log(f"=== Testing Concurrent Operations ({num_employees} employees, {num_tasks} tasks) ===")
        
        # Create employees concurrently
        start_time = time.time()
        
        def create_employee_worker(i):
            return self.create_employee(f"concurrent_test_{i}", "developer")
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_employee_worker, i) for i in range(num_employees)]
            created_count = sum(1 for future in concurrent.futures.as_completed(futures) if future.result())
            
        creation_duration = time.time() - start_time
        self.log(f"Created {created_count}/{num_employees} employees in {creation_duration:.2f}s")
        
        # Assign tasks concurrently
        start_time = time.time()
        
        def assign_task_worker(i):
            employee = self.test_employees[i % len(self.test_employees)]
            task = f"Concurrent task {i}: Create feature component"
            return self.assign_task(employee, task)
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(assign_task_worker, i) for i in range(num_tasks)]
            assigned_count = sum(1 for future in concurrent.futures.as_completed(futures) if future.result())
            
        assignment_duration = time.time() - start_time
        throughput = num_tasks / assignment_duration
        
        self.metrics['throughput_data'].append({
            'operations': num_tasks,
            'duration': assignment_duration,
            'throughput': throughput
        })
        
        self.log(f"Assigned {assigned_count}/{num_tasks} tasks in {assignment_duration:.2f}s")
        self.log(f"Throughput: {throughput:.2f} tasks/second")
        
    def test_response_time_under_load(self):
        """Test response times under increasing load"""
        self.log("=== Testing Response Times Under Load ===")
        
        load_levels = [1, 5, 10, 15, 20]
        
        for load in load_levels:
            self.log(f"Testing with load level: {load} concurrent requests")
            
            def status_check_worker():
                return self.get_system_status()
                
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=load) as executor:
                futures = [executor.submit(status_check_worker) for _ in range(load)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
                
            duration = time.time() - start_time
            successful = sum(1 for r in results if r)
            
            self.log(f"Load {load}: {successful}/{load} successful in {duration:.2f}s")
            
            # Small delay between load tests
            time.sleep(2)
            
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        self.log("Generating performance report...")
        
        # Calculate response time statistics
        response_times = [rt['duration'] for rt in self.metrics['response_times']]
        response_stats = {}
        
        if response_times:
            response_stats = {
                'count': len(response_times),
                'mean': statistics.mean(response_times),
                'median': statistics.median(response_times),
                'min': min(response_times),
                'max': max(response_times),
                'std_dev': statistics.stdev(response_times) if len(response_times) > 1 else 0
            }
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            response_stats['p95'] = sorted_times[int(len(sorted_times) * 0.95)]
            response_stats['p99'] = sorted_times[int(len(sorted_times) * 0.99)]
            
        # Calculate resource usage statistics
        resource_stats = {}
        if self.metrics['resource_usage']:
            cpu_usage = [r['cpu_percent'] for r in self.metrics['resource_usage']]
            memory_usage = [r['memory_mb'] for r in self.metrics['resource_usage']]
            
            resource_stats = {
                'cpu': {
                    'mean': statistics.mean(cpu_usage),
                    'max': max(cpu_usage),
                    'min': min(cpu_usage)
                },
                'memory': {
                    'mean_mb': statistics.mean(memory_usage),
                    'max_mb': max(memory_usage),
                    'min_mb': min(memory_usage)
                }
            }
            
        # Calculate throughput statistics
        throughput_stats = {}
        if self.metrics['throughput_data']:
            throughputs = [t['throughput'] for t in self.metrics['throughput_data']]
            throughput_stats = {
                'mean': statistics.mean(throughputs),
                'max': max(throughputs),
                'min': min(throughputs)
            }
            
        # Error analysis
        error_stats = {
            'total_errors': len(self.metrics['errors']),
            'error_rate': len(self.metrics['errors']) / len(self.metrics['response_times']) * 100 if self.metrics['response_times'] else 0,
            'error_types': {}
        }
        
        for error in self.metrics['errors']:
            error_type = error['type']
            error_stats['error_types'][error_type] = error_stats['error_types'].get(error_type, 0) + 1
            
        # Performance grade
        grade = 'A'
        if response_stats.get('mean', 0) > 5.0 or error_stats['error_rate'] > 10:
            grade = 'D'
        elif response_stats.get('mean', 0) > 2.0 or error_stats['error_rate'] > 5:
            grade = 'C'
        elif response_stats.get('mean', 0) > 1.0 or error_stats['error_rate'] > 2:
            grade = 'B'
            
        report = {
            'timestamp': datetime.now().isoformat(),
            'server_url': self.server_url,
            'performance_grade': grade,
            'response_times': response_stats,
            'resource_usage': resource_stats,
            'throughput': throughput_stats,
            'errors': error_stats,
            'system_info': {
                'cpu_cores': psutil.cpu_count(),
                'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 2)
            }
        }
        
        return report
        
    def run_performance_tests(self):
        """Run all performance tests"""
        self.log("🚀 Starting OpenCode-Slack Performance Tests")
        self.log("=" * 60)
        
        # Start resource monitoring
        monitor_thread = self.monitor_resources(duration=300)  # 5 minutes
        
        try:
            # Test 1: Basic functionality
            if not self.test_basic_functionality():
                self.log("❌ Basic functionality test failed")
                return None
                
            time.sleep(5)  # Allow system to stabilize
            
            # Test 2: Concurrent operations
            self.test_concurrent_operations(num_employees=8, num_tasks=15)
            
            time.sleep(5)  # Allow system to stabilize
            
            # Test 3: Response time under load
            self.test_response_time_under_load()
            
            # Generate report
            report = self.generate_performance_report()
            
            # Save report
            report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
                
            self.log(f"📊 Performance report saved: {report_file}")
            
            return report
            
        except Exception as e:
            self.log(f"❌ Performance test failed: {e}")
            return None
            
        finally:
            # Cleanup
            self.cleanup_employees()
            
            # Wait for monitoring to complete
            if monitor_thread.is_alive():
                monitor_thread.join(timeout=5)
                
    def print_summary(self, report: Dict[str, Any]):
        """Print performance test summary"""
        if not report:
            return
            
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE TEST SUMMARY")
        print("=" * 60)
        
        print(f"🎯 Performance Grade: {report['performance_grade']}")
        print(f"🖥️  System: {report['system_info']['cpu_cores']} cores, {report['system_info']['total_memory_gb']}GB RAM")
        
        if report['response_times']:
            rt = report['response_times']
            print(f"\n⏱️  Response Times:")
            print(f"   Mean: {rt['mean']:.3f}s")
            print(f"   Median: {rt['median']:.3f}s")
            print(f"   P95: {rt['p95']:.3f}s")
            print(f"   Max: {rt['max']:.3f}s")
            print(f"   Operations: {rt['count']}")
            
        if report['throughput']:
            tp = report['throughput']
            print(f"\n🚀 Throughput:")
            print(f"   Peak: {tp['max']:.2f} ops/sec")
            print(f"   Average: {tp['mean']:.2f} ops/sec")
            
        if report['resource_usage']:
            ru = report['resource_usage']
            print(f"\n💻 Resource Usage:")
            print(f"   Peak CPU: {ru['cpu']['max']:.1f}%")
            print(f"   Avg CPU: {ru['cpu']['mean']:.1f}%")
            print(f"   Peak Memory: {ru['memory']['max_mb']:.1f} MB")
            print(f"   Avg Memory: {ru['memory']['mean_mb']:.1f} MB")
            
        errors = report['errors']
        print(f"\n❌ Errors:")
        print(f"   Total: {errors['total_errors']}")
        print(f"   Error Rate: {errors['error_rate']:.1f}%")
        
        if errors['error_types']:
            print("   Types:")
            for error_type, count in errors['error_types'].items():
                print(f"     {error_type}: {count}")
                
        print("\n" + "=" * 60)

def main():
    """Main function"""
    # Test with the running server
    tester = SimplePerformanceTest("http://localhost:9090")
    
    # Run performance tests
    report = tester.run_performance_tests()
    
    if report:
        tester.print_summary(report)
        print("✅ Performance testing completed successfully!")
        return 0
    else:
        print("❌ Performance testing failed!")
        return 1

if __name__ == "__main__":
    exit(main())