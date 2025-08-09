#!/usr/bin/env python3
"""
Stress Test for OpenCode-Slack Agent Orchestration System
Tests system limits and identifies performance degradation points
"""

import json
import requests
import time
import threading
import psutil
import statistics
import concurrent.futures
import random
from datetime import datetime
from typing import List, Dict, Any

class StressTest:
    def __init__(self, server_url: str = "http://localhost:9090"):
        self.server_url = server_url
        self.session = requests.Session()
        self.metrics = {
            'scalability_results': [],
            'stress_results': [],
            'resource_peaks': [],
            'failure_points': []
        }
        self.test_employees = []
        
    def log(self, message: str):
        """Log message with timestamp"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def cleanup_all_employees(self):
        """Clean up all test employees"""
        try:
            response = self.session.get(f"{self.server_url}/employees")
            if response.status_code == 200:
                employees = response.json().get('employees', [])
                for employee in employees:
                    if employee['name'].startswith(('stress_', 'scale_', 'perf_', 'concurrent_')):
                        self.session.delete(f"{self.server_url}/employees/{employee['name']}")
        except Exception as e:
            self.log(f"Error cleaning up: {e}")
            
    def create_employees_batch(self, count: int, prefix: str = "stress") -> int:
        """Create employees in batch and return success count"""
        def create_worker(i):
            try:
                response = self.session.post(
                    f"{self.server_url}/employees",
                    json={'name': f"{prefix}_{i:03d}", 'role': 'developer'},
                    timeout=10
                )
                return response.status_code == 200
            except:
                return False
                
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_worker, i) for i in range(count)]
            success_count = sum(1 for future in concurrent.futures.as_completed(futures) if future.result())
            
        return success_count
        
    def assign_tasks_batch(self, employees: List[str], tasks_per_employee: int = 1) -> Dict:
        """Assign tasks in batch and measure performance"""
        tasks = [
            "Create HTML component",
            "Add CSS styling",
            "Implement JavaScript logic",
            "Write unit tests",
            "Update documentation",
            "Add error handling",
            "Optimize performance",
            "Fix linting issues"
        ]
        
        assignments = []
        for employee in employees:
            for i in range(tasks_per_employee):
                task = random.choice(tasks)
                assignments.append((employee, f"{task} (batch {i+1})"))
                
        def assign_worker(assignment):
            employee, task = assignment
            try:
                start_time = time.time()
                response = self.session.post(
                    f"{self.server_url}/tasks",
                    json={'name': employee, 'task': task},
                    timeout=20
                )
                duration = time.time() - start_time
                return {
                    'success': response.status_code == 200,
                    'duration': duration,
                    'employee': employee,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'duration': time.time() - start_time,
                    'employee': employee,
                    'error': str(e)
                }
                
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(assign_worker, assignment) for assignment in assignments]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
        total_duration = time.time() - start_time
        successful = sum(1 for r in results if r['success'])
        
        return {
            'total_assignments': len(assignments),
            'successful': successful,
            'failed': len(assignments) - successful,
            'duration': total_duration,
            'throughput': len(assignments) / total_duration,
            'success_rate': successful / len(assignments) * 100,
            'avg_response_time': statistics.mean([r['duration'] for r in results]),
            'results': results
        }
        
    def monitor_system_resources(self, duration: int = 60) -> Dict:
        """Monitor system resources and return peak usage"""
        resource_data = []
        
        def monitor():
            end_time = time.time() + duration
            while time.time() < end_time:
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    disk = psutil.disk_usage('/')
                    
                    resource_data.append({
                        'timestamp': time.time(),
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_mb': memory.used / (1024 * 1024),
                        'disk_percent': disk.percent
                    })
                except Exception as e:
                    self.log(f"Resource monitoring error: {e}")
                    
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        monitor_thread.join()
        
        if resource_data:
            return {
                'peak_cpu': max(r['cpu_percent'] for r in resource_data),
                'avg_cpu': statistics.mean(r['cpu_percent'] for r in resource_data),
                'peak_memory_percent': max(r['memory_percent'] for r in resource_data),
                'peak_memory_mb': max(r['memory_mb'] for r in resource_data),
                'avg_memory_mb': statistics.mean(r['memory_mb'] for r in resource_data),
                'samples': len(resource_data)
            }
        return {}
        
    def test_scalability_limits(self):
        """Test system scalability by increasing employee count"""
        self.log("=== Testing Scalability Limits ===")
        
        employee_counts = [10, 25, 50, 75, 100, 150, 200]
        
        for count in employee_counts:
            self.log(f"Testing with {count} employees...")
            
            # Clean up previous test
            self.cleanup_all_employees()
            time.sleep(3)
            
            # Start resource monitoring
            monitor_thread = threading.Thread(
                target=lambda: self.monitor_system_resources(60), 
                daemon=True
            )
            monitor_thread.start()
            
            # Create employees
            start_time = time.time()
            created = self.create_employees_batch(count, f"scale_{count}")
            creation_time = time.time() - start_time
            
            if created < count * 0.7:  # Less than 70% success
                self.log(f"❌ Only created {created}/{count} employees - system overloaded")
                self.metrics['failure_points'].append({
                    'test': 'employee_creation',
                    'target_count': count,
                    'actual_count': created,
                    'success_rate': created / count * 100
                })
                break
                
            # Get employee list for task assignment
            response = self.session.get(f"{self.server_url}/employees")
            if response.status_code == 200:
                employees = [emp['name'] for emp in response.json().get('employees', []) 
                           if emp['name'].startswith(f"scale_{count}")]
            else:
                employees = []
                
            # Assign one task to each employee
            if employees:
                task_results = self.assign_tasks_batch(employees[:min(count, len(employees))])
                
                result = {
                    'employee_count': count,
                    'employees_created': created,
                    'creation_time': creation_time,
                    'task_assignment': task_results,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.metrics['scalability_results'].append(result)
                
                self.log(f"Results for {count} employees:")
                self.log(f"  Created: {created}/{count} ({created/count*100:.1f}%)")
                self.log(f"  Task success rate: {task_results['success_rate']:.1f}%")
                self.log(f"  Throughput: {task_results['throughput']:.2f} tasks/sec")
                self.log(f"  Avg response time: {task_results['avg_response_time']:.3f}s")
                
                # Check for performance degradation
                if len(self.metrics['scalability_results']) > 1:
                    prev = self.metrics['scalability_results'][-2]
                    current = self.metrics['scalability_results'][-1]
                    
                    prev_throughput = prev['task_assignment']['throughput']
                    current_throughput = current['task_assignment']['throughput']
                    
                    if current_throughput < prev_throughput * 0.5:  # 50% degradation
                        self.log(f"⚠️ Significant performance degradation detected!")
                        self.metrics['failure_points'].append({
                            'test': 'performance_degradation',
                            'employee_count': count,
                            'throughput_drop': (prev_throughput - current_throughput) / prev_throughput * 100
                        })
                        
            # Wait for resource monitoring to complete
            monitor_thread.join(timeout=5)
            
            # Small delay between tests
            time.sleep(5)
            
    def test_sustained_high_load(self, duration_minutes: int = 5):
        """Test system under sustained high load"""
        self.log(f"=== Testing Sustained High Load ({duration_minutes} minutes) ===")
        
        # Create a moderate number of employees
        employee_count = 30
        created = self.create_employees_batch(employee_count, "sustained")
        
        if created < employee_count * 0.8:
            self.log(f"❌ Could not create enough employees for sustained test")
            return
            
        # Get employee list
        response = self.session.get(f"{self.server_url}/employees")
        employees = [emp['name'] for emp in response.json().get('employees', []) 
                    if emp['name'].startswith("sustained")]
        
        self.log(f"Starting sustained load test with {len(employees)} employees")
        
        # Start resource monitoring
        resource_data = []
        monitoring = True
        
        def resource_monitor():
            while monitoring:
                try:
                    cpu = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    resource_data.append({
                        'timestamp': time.time(),
                        'cpu': cpu,
                        'memory_mb': memory.used / (1024 * 1024),
                        'memory_percent': memory.percent
                    })
                except:
                    pass
                    
        monitor_thread = threading.Thread(target=resource_monitor, daemon=True)
        monitor_thread.start()
        
        # Run sustained load
        end_time = time.time() + (duration_minutes * 60)
        task_count = 0
        successful_tasks = 0
        failed_tasks = 0
        
        while time.time() < end_time:
            # Assign tasks to random employees
            batch_size = min(10, len(employees))
            selected_employees = random.sample(employees, batch_size)
            
            results = self.assign_tasks_batch(selected_employees, 1)
            task_count += results['total_assignments']
            successful_tasks += results['successful']
            failed_tasks += results['failed']
            
            # Log progress every 50 tasks
            if task_count % 50 == 0:
                elapsed = (time.time() - (end_time - duration_minutes * 60)) / 60
                self.log(f"Sustained load progress: {task_count} tasks in {elapsed:.1f}min")
                
            # Small delay to prevent overwhelming
            time.sleep(random.uniform(1, 3))
            
        # Stop monitoring
        monitoring = False
        monitor_thread.join(timeout=5)
        
        # Calculate results
        total_duration = duration_minutes * 60
        avg_throughput = task_count / total_duration
        success_rate = successful_tasks / task_count * 100 if task_count > 0 else 0
        
        sustained_result = {
            'duration_minutes': duration_minutes,
            'total_tasks': task_count,
            'successful_tasks': successful_tasks,
            'failed_tasks': failed_tasks,
            'success_rate': success_rate,
            'avg_throughput': avg_throughput,
            'resource_usage': {
                'peak_cpu': max(r['cpu'] for r in resource_data) if resource_data else 0,
                'avg_cpu': statistics.mean(r['cpu'] for r in resource_data) if resource_data else 0,
                'peak_memory_mb': max(r['memory_mb'] for r in resource_data) if resource_data else 0,
                'avg_memory_mb': statistics.mean(r['memory_mb'] for r in resource_data) if resource_data else 0
            }
        }
        
        self.metrics['stress_results'].append(sustained_result)
        
        self.log(f"Sustained load test completed:")
        self.log(f"  Total tasks: {task_count}")
        self.log(f"  Success rate: {success_rate:.1f}%")
        self.log(f"  Avg throughput: {avg_throughput:.2f} tasks/sec")
        self.log(f"  Peak CPU: {sustained_result['resource_usage']['peak_cpu']:.1f}%")
        self.log(f"  Peak Memory: {sustained_result['resource_usage']['peak_memory_mb']:.1f} MB")
        
    def test_communication_stress(self):
        """Test communication channels under stress"""
        self.log("=== Testing Communication Channel Stress ===")
        
        # Rapid status requests
        request_counts = [50, 100, 200, 500]
        
        for count in request_counts:
            self.log(f"Testing {count} rapid status requests...")
            
            def status_worker():
                try:
                    start_time = time.time()
                    response = self.session.get(f"{self.server_url}/status", timeout=5)
                    duration = time.time() - start_time
                    return {
                        'success': response.status_code == 200,
                        'duration': duration,
                        'status_code': response.status_code
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'duration': 5.0,  # timeout
                        'error': str(e)
                    }
                    
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(status_worker) for _ in range(count)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
                
            total_duration = time.time() - start_time
            successful = sum(1 for r in results if r['success'])
            
            comm_result = {
                'request_count': count,
                'successful': successful,
                'success_rate': successful / count * 100,
                'total_duration': total_duration,
                'throughput': count / total_duration,
                'avg_response_time': statistics.mean([r['duration'] for r in results])
            }
            
            self.log(f"Communication stress {count} requests:")
            self.log(f"  Success rate: {comm_result['success_rate']:.1f}%")
            self.log(f"  Throughput: {comm_result['throughput']:.2f} req/sec")
            self.log(f"  Avg response: {comm_result['avg_response_time']:.3f}s")
            
            if comm_result['success_rate'] < 90:
                self.log(f"⚠️ Communication channel showing stress at {count} requests")
                self.metrics['failure_points'].append({
                    'test': 'communication_stress',
                    'request_count': count,
                    'success_rate': comm_result['success_rate']
                })
                
    def generate_stress_report(self) -> Dict[str, Any]:
        """Generate comprehensive stress test report"""
        self.log("Generating stress test report...")
        
        # Find scalability limits
        scalability_limit = None
        if self.metrics['scalability_results']:
            for result in self.metrics['scalability_results']:
                task_success = result['task_assignment']['success_rate']
                if task_success < 80:  # Less than 80% task success
                    scalability_limit = result['employee_count']
                    break
                    
        # Identify bottlenecks
        bottlenecks = []
        recommendations = []
        
        for failure in self.metrics['failure_points']:
            if failure['test'] == 'employee_creation':
                bottlenecks.append(f"Employee creation fails at {failure['target_count']} employees")
                recommendations.append("Optimize employee creation process")
            elif failure['test'] == 'performance_degradation':
                bottlenecks.append(f"Performance degrades significantly at {failure['employee_count']} employees")
                recommendations.append("Implement load balancing or resource pooling")
            elif failure['test'] == 'communication_stress':
                bottlenecks.append(f"Communication channel stressed at {failure['request_count']} requests")
                recommendations.append("Implement request throttling or caching")
                
        # Performance grade based on scalability and stability
        if scalability_limit and scalability_limit < 50:
            grade = 'D'
        elif scalability_limit and scalability_limit < 100:
            grade = 'C'
        elif len(bottlenecks) > 2:
            grade = 'B'
        else:
            grade = 'A'
            
        report = {
            'timestamp': datetime.now().isoformat(),
            'performance_grade': grade,
            'scalability_limit': scalability_limit,
            'bottlenecks_identified': bottlenecks,
            'recommendations': recommendations,
            'scalability_results': self.metrics['scalability_results'],
            'stress_results': self.metrics['stress_results'],
            'failure_points': self.metrics['failure_points'],
            'system_info': {
                'cpu_cores': psutil.cpu_count(),
                'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 2)
            }
        }
        
        return report
        
    def run_stress_tests(self):
        """Run all stress tests"""
        self.log("🔥 Starting OpenCode-Slack Stress Tests")
        self.log("=" * 60)
        
        try:
            # Clean up any existing test data
            self.cleanup_all_employees()
            time.sleep(2)
            
            # Test 1: Scalability limits
            self.test_scalability_limits()
            
            # Clean up between tests
            self.cleanup_all_employees()
            time.sleep(3)
            
            # Test 2: Sustained high load
            self.test_sustained_high_load(duration_minutes=3)
            
            # Test 3: Communication stress
            self.test_communication_stress()
            
            # Generate report
            report = self.generate_stress_report()
            
            # Save report
            report_file = f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
                
            self.log(f"📊 Stress test report saved: {report_file}")
            
            return report
            
        except Exception as e:
            self.log(f"❌ Stress test failed: {e}")
            return None
            
        finally:
            # Final cleanup
            self.cleanup_all_employees()
            
    def print_stress_summary(self, report: Dict[str, Any]):
        """Print stress test summary"""
        if not report:
            return
            
        print("\n" + "=" * 60)
        print("🔥 STRESS TEST SUMMARY")
        print("=" * 60)
        
        print(f"🎯 Performance Grade: {report['performance_grade']}")
        print(f"🖥️  System: {report['system_info']['cpu_cores']} cores, {report['system_info']['total_memory_gb']}GB RAM")
        
        if report['scalability_limit']:
            print(f"📈 Scalability Limit: {report['scalability_limit']} employees")
        else:
            print(f"📈 Scalability: No hard limit found (tested up to 200 employees)")
            
        if report['scalability_results']:
            best_result = max(report['scalability_results'], 
                            key=lambda x: x['task_assignment']['throughput'])
            print(f"🚀 Peak Throughput: {best_result['task_assignment']['throughput']:.2f} tasks/sec")
            print(f"   (at {best_result['employee_count']} employees)")
            
        if report['stress_results']:
            sustained = report['stress_results'][0]
            print(f"⏱️  Sustained Load:")
            print(f"   Tasks: {sustained['total_tasks']} over {sustained['duration_minutes']} minutes")
            print(f"   Success Rate: {sustained['success_rate']:.1f}%")
            print(f"   Avg Throughput: {sustained['avg_throughput']:.2f} tasks/sec")
            print(f"   Peak CPU: {sustained['resource_usage']['peak_cpu']:.1f}%")
            
        if report['bottlenecks_identified']:
            print(f"\n⚠️  Bottlenecks Identified:")
            for bottleneck in report['bottlenecks_identified']:
                print(f"   • {bottleneck}")
                
        if report['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"   • {rec}")
                
        print("\n" + "=" * 60)

def main():
    """Main function"""
    # Test with the running server
    tester = StressTest("http://localhost:9090")
    
    # Run stress tests
    report = tester.run_stress_tests()
    
    if report:
        tester.print_stress_summary(report)
        print("✅ Stress testing completed successfully!")
        return 0
    else:
        print("❌ Stress testing failed!")
        return 1

if __name__ == "__main__":
    exit(main())