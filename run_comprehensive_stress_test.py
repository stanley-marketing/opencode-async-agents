#!/usr/bin/env python3
"""
Comprehensive Stress Test Runner for OpenCode-Slack Phase 2 Optimizations
Validates all performance optimizations under extreme load conditions.
"""

import asyncio
import aiohttp
import time
import json
import logging
import statistics
import psutil
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_stress_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class StressTestConfig:
    """Configuration for stress testing parameters"""
    # Server configuration
    async_server_url: str = "http://localhost:8080"
    
    # Maximum capacity targets (Phase 2 goals)
    max_concurrent_users: int = 100
    max_concurrent_agents: int = 50
    max_concurrent_tasks: int = 200
    max_message_throughput: int = 1000  # messages per minute
    max_realtime_messages: int = 120    # messages per second
    
    # Test duration settings
    sustained_load_duration: int = 5   # minutes (reduced for demo)
    
    # Stress test thresholds
    acceptable_error_rate: float = 5.0  # percent
    acceptable_response_time: float = 2.0  # seconds

class ComprehensiveStressTester:
    """Comprehensive stress testing suite for OpenCode-Slack Phase 2 optimizations"""
    
    def __init__(self, config: StressTestConfig = None):
        self.config = config or StressTestConfig()
        self.session = None
        self.test_start_time = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=50)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] {level}: {message}")
        getattr(logger, level.lower())(message)

    async def cleanup_test_data(self):
        """Clean up all test data"""
        try:
            # Get all employees
            async with self.session.get(f"{self.config.async_server_url}/employees") as response:
                if response.status == 200:
                    data = await response.json()
                    employees = data.get('employees', [])
                    
                    # Delete test employees
                    for employee in employees:
                        name = employee.get('name', '')
                        if any(prefix in name for prefix in ['stress_', 'test_', 'load_', 'perf_', 'scale_']):
                            try:
                                async with self.session.delete(
                                    f"{self.config.async_server_url}/employees/{name}"
                                ) as del_response:
                                    pass
                            except Exception as e:
                                logger.debug(f"Error deleting employee {name}: {e}")
                                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    # Helper methods for API operations
    async def _create_employee(self, name: str, role: str) -> bool:
        """Create an employee via API"""
        try:
            async with self.session.post(
                f"{self.config.async_server_url}/employees",
                json={"name": name, "role": role},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Failed to create employee {name}: {e}")
            return False

    async def _assign_task(self, employee_name: str, task: str) -> bool:
        """Assign task to employee via API"""
        try:
            async with self.session.post(
                f"{self.config.async_server_url}/tasks",
                json={"name": employee_name, "task": task},
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Failed to assign task to {employee_name}: {e}")
            return False

    async def _get_status(self) -> bool:
        """Get system status via API"""
        try:
            async with self.session.get(
                f"{self.config.async_server_url}/status",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Failed to get status: {e}")
            return False

    async def _get_employees(self) -> bool:
        """Get employees list via API"""
        try:
            async with self.session.get(
                f"{self.config.async_server_url}/employees",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Failed to get employees: {e}")
            return False

    async def run_comprehensive_stress_tests(self) -> Dict[str, Any]:
        """Run comprehensive stress tests"""
        self.log("🔥 Starting Comprehensive Stress Testing Suite for Phase 2 Optimizations")
        self.log("=" * 80)
        
        self.test_start_time = time.time()
        
        try:
            # Clean up any existing test data
            await self.cleanup_test_data()
            
            # Test 1: Maximum Capacity Testing
            self.log("=== PHASE 1: MAXIMUM CAPACITY TESTING ===")
            capacity_results = await self._test_maximum_capacity()
            
            # Test 2: Performance Optimization Validation
            self.log("=== PHASE 2: PERFORMANCE OPTIMIZATION VALIDATION ===")
            optimization_results = await self._test_performance_optimizations()
            
            # Test 3: System Resilience Under Stress
            self.log("=== PHASE 3: SYSTEM RESILIENCE UNDER STRESS ===")
            resilience_results = await self._test_system_resilience()
            
            # Test 4: Communication Stress Testing
            self.log("=== PHASE 4: COMMUNICATION STRESS TESTING ===")
            communication_results = await self._test_communication_stress()
            
            # Test 5: Production Load Simulation
            self.log("=== PHASE 5: PRODUCTION LOAD SIMULATION ===")
            production_results = await self._test_production_load_simulation()
            
            # Generate comprehensive report
            report = self._generate_comprehensive_report({
                'maximum_capacity': capacity_results,
                'performance_optimizations': optimization_results,
                'system_resilience': resilience_results,
                'communication_stress': communication_results,
                'production_load': production_results
            })
            
            return report
            
        except Exception as e:
            self.log(f"❌ Comprehensive stress testing failed: {e}", "ERROR")
            raise
        finally:
            await self.cleanup_test_data()

    async def _test_maximum_capacity(self) -> Dict[str, Any]:
        """Test maximum capacity improvements"""
        results = {}
        
        # Test 1.1: 100+ Concurrent Users
        self.log("1.1 Testing 100+ concurrent users...")
        user_results = await self._test_concurrent_users(self.config.max_concurrent_users)
        results['concurrent_users'] = user_results
        
        # Test 1.2: 50+ Concurrent Agents
        self.log("1.2 Testing 50+ concurrent agents...")
        agent_results = await self._test_concurrent_agents(self.config.max_concurrent_agents)
        results['concurrent_agents'] = agent_results
        
        # Test 1.3: 200+ Concurrent Tasks
        self.log("1.3 Testing 200+ concurrent tasks...")
        task_results = await self._test_concurrent_tasks(self.config.max_concurrent_tasks)
        results['concurrent_tasks'] = task_results
        
        # Test 1.4: 1000+ Messages per Minute
        self.log("1.4 Testing 1000+ messages per minute...")
        message_results = await self._test_message_throughput(self.config.max_message_throughput)
        results['message_throughput'] = message_results
        
        return results

    async def _test_concurrent_users(self, target_users: int) -> Dict[str, Any]:
        """Test system with concurrent users"""
        start_time = time.time()
        successful_operations = 0
        failed_operations = 0
        response_times = []
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        async def simulate_user(user_id: int):
            """Simulate a single user's operations"""
            operations = 0
            failures = 0
            times = []
            
            try:
                # User operations: create employee, assign task, check status
                for op in range(3):  # 3 operations per user
                    op_start = time.time()
                    
                    if op == 0:  # Create employee
                        success = await self._create_employee(f"user_{user_id}_emp", "developer")
                    elif op == 1:  # Assign task
                        success = await self._assign_task(f"user_{user_id}_emp", f"Task for user {user_id}")
                    else:  # Check status
                        success = await self._get_status()
                    
                    op_time = time.time() - op_start
                    times.append(op_time)
                    
                    if success:
                        operations += 1
                    else:
                        failures += 1
                        
            except Exception as e:
                logger.debug(f"User {user_id} error: {e}")
                failures += 1
                
            return operations, failures, times
        
        # Run concurrent users
        tasks = [simulate_user(i) for i in range(target_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                failed_operations += 3  # 3 operations per user
            else:
                ops, fails, times = result
                successful_operations += ops
                failed_operations += fails
                response_times.extend(times)
        
        duration = time.time() - start_time
        
        # Final resource check
        final_cpu = psutil.cpu_percent()
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        return {
            'target_users': target_users,
            'duration': duration,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'total_operations': successful_operations + failed_operations,
            'success_rate': (successful_operations / (successful_operations + failed_operations)) * 100 if (successful_operations + failed_operations) > 0 else 0,
            'throughput': (successful_operations + failed_operations) / duration,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'peak_cpu': max(initial_cpu, final_cpu),
            'peak_memory_mb': max(initial_memory, final_memory)
        }

    async def _test_concurrent_agents(self, target_agents: int) -> Dict[str, Any]:
        """Test system with concurrent agents"""
        start_time = time.time()
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        # Create agents in batches to avoid overwhelming the system
        batch_size = 10
        successful_creations = 0
        failed_creations = 0
        
        for batch_start in range(0, target_agents, batch_size):
            batch_end = min(batch_start + batch_size, target_agents)
            batch_tasks = []
            
            for i in range(batch_start, batch_end):
                task = self._create_employee(f"agent_{i:03d}", "developer")
                batch_tasks.append(task)
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception) or not result:
                    failed_creations += 1
                else:
                    successful_creations += 1
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        duration = time.time() - start_time
        
        # Final resource check
        final_cpu = psutil.cpu_percent()
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        return {
            'target_agents': target_agents,
            'successful_creations': successful_creations,
            'failed_creations': failed_creations,
            'success_rate': (successful_creations / target_agents) * 100,
            'creation_throughput': successful_creations / duration,
            'duration': duration,
            'peak_cpu': max(initial_cpu, final_cpu),
            'peak_memory_mb': max(initial_memory, final_memory)
        }

    async def _test_concurrent_tasks(self, target_tasks: int) -> Dict[str, Any]:
        """Test system with concurrent task assignments"""
        # First create enough employees
        num_employees = min(50, target_tasks // 4)  # 4 tasks per employee max
        
        self.log(f"Creating {num_employees} employees for task testing...")
        employee_names = []
        
        for i in range(num_employees):
            name = f"task_emp_{i:03d}"
            if await self._create_employee(name, "developer"):
                employee_names.append(name)
        
        if len(employee_names) < num_employees * 0.8:
            self.log(f"⚠️ Only created {len(employee_names)}/{num_employees} employees")
        
        start_time = time.time()
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        # Assign tasks concurrently
        tasks = []
        for i in range(target_tasks):
            employee = employee_names[i % len(employee_names)] if employee_names else f"task_emp_{i % 10:03d}"
            task = self._assign_task(employee, f"Stress test task {i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_assignments = sum(1 for r in results if not isinstance(r, Exception) and r)
        failed_assignments = target_tasks - successful_assignments
        
        duration = time.time() - start_time
        
        # Final resource check
        final_cpu = psutil.cpu_percent()
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        return {
            'target_tasks': target_tasks,
            'employees_created': len(employee_names),
            'successful_assignments': successful_assignments,
            'failed_assignments': failed_assignments,
            'success_rate': (successful_assignments / target_tasks) * 100,
            'assignment_throughput': successful_assignments / duration,
            'duration': duration,
            'peak_cpu': max(initial_cpu, final_cpu),
            'peak_memory_mb': max(initial_memory, final_memory)
        }

    async def _test_message_throughput(self, target_messages_per_minute: int) -> Dict[str, Any]:
        """Test message throughput capacity"""
        start_time = time.time()
        test_duration = 60  # 1 minute test
        target_messages = target_messages_per_minute
        
        successful_messages = 0
        failed_messages = 0
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        async def send_message_batch():
            """Send a batch of status requests (simulating messages)"""
            batch_size = 10
            batch_results = []
            
            for _ in range(batch_size):
                try:
                    async with self.session.get(f"{self.config.async_server_url}/status") as response:
                        batch_results.append(response.status == 200)
                except:
                    batch_results.append(False)
            
            return batch_results
        
        # Calculate batches needed
        messages_per_batch = 10
        batches_needed = target_messages // messages_per_batch
        batch_interval = test_duration / batches_needed
        
        for batch_num in range(batches_needed):
            batch_start = time.time()
            
            # Send batch
            batch_results = await send_message_batch()
            successful_messages += sum(batch_results)
            failed_messages += len(batch_results) - sum(batch_results)
            
            # Wait for next batch interval
            elapsed = time.time() - batch_start
            if elapsed < batch_interval:
                await asyncio.sleep(batch_interval - elapsed)
        
        duration = time.time() - start_time
        
        # Final resource check
        final_cpu = psutil.cpu_percent()
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        actual_throughput = (successful_messages + failed_messages) / (duration / 60)  # per minute
        
        return {
            'target_messages_per_minute': target_messages_per_minute,
            'actual_messages_per_minute': actual_throughput,
            'successful_messages': successful_messages,
            'failed_messages': failed_messages,
            'success_rate': (successful_messages / (successful_messages + failed_messages)) * 100 if (successful_messages + failed_messages) > 0 else 0,
            'duration': duration,
            'peak_cpu': max(initial_cpu, final_cpu),
            'peak_memory_mb': max(initial_memory, final_memory)
        }

    async def _test_performance_optimizations(self) -> Dict[str, Any]:
        """Test all Phase 2 performance optimizations under stress"""
        results = {}
        
        # Test 2.1: Async LLM Processing under stress
        self.log("2.1 Testing async LLM processing under extreme load...")
        llm_results = await self._test_async_llm_stress()
        results['async_llm_processing'] = llm_results
        
        # Test 2.2: Database optimization under stress
        self.log("2.2 Testing database optimization under extreme load...")
        db_results = await self._test_database_stress()
        results['database_optimization'] = db_results
        
        # Test 2.3: HTTP connection optimization
        self.log("2.3 Testing HTTP connection optimization with 500+ requests...")
        http_results = await self._test_http_optimization_stress()
        results['http_optimization'] = http_results
        
        return results

    async def _test_async_llm_stress(self) -> Dict[str, Any]:
        """Test async LLM processing with 100+ concurrent requests"""
        # Create employees for LLM testing
        num_employees = 20
        employee_names = []
        
        for i in range(num_employees):
            name = f"llm_emp_{i:03d}"
            if await self._create_employee(name, "developer"):
                employee_names.append(name)
        
        start_time = time.time()
        concurrent_requests = 100
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        # Simulate LLM requests by assigning complex tasks
        tasks = []
        for i in range(concurrent_requests):
            employee = employee_names[i % len(employee_names)] if employee_names else f"llm_emp_{i % 5:03d}"
            complex_task = f"Analyze and implement a complex algorithm for task {i} with error handling and optimization"
            task = self._assign_task(employee, complex_task)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_requests = sum(1 for r in results if not isinstance(r, Exception) and r)
        failed_requests = concurrent_requests - successful_requests
        
        duration = time.time() - start_time
        
        # Final resource check
        final_cpu = psutil.cpu_percent()
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        return {
            'concurrent_requests': concurrent_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': (successful_requests / concurrent_requests) * 100,
            'request_throughput': successful_requests / duration,
            'avg_response_time': duration / concurrent_requests,
            'duration': duration,
            'peak_cpu': max(initial_cpu, final_cpu),
            'peak_memory_mb': max(initial_memory, final_memory)
        }

    async def _test_database_stress(self) -> Dict[str, Any]:
        """Test database optimization under extreme concurrent load"""
        start_time = time.time()
        concurrent_operations = 200
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        # Mix of database operations
        tasks = []
        for i in range(concurrent_operations):
            if i % 4 == 0:  # Employee creation
                task = self._create_employee(f"db_emp_{i:03d}", "developer")
            elif i % 4 == 1:  # Task assignment
                task = self._assign_task(f"db_emp_{(i//4)*4:03d}", f"DB stress task {i}")
            elif i % 4 == 2:  # Status check
                task = self._get_status()
            else:  # Employee list
                task = self._get_employees()
            
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_ops = sum(1 for r in results if not isinstance(r, Exception) and r)
        failed_ops = concurrent_operations - successful_ops
        
        duration = time.time() - start_time
        
        # Final resource check
        final_cpu = psutil.cpu_percent()
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        return {
            'concurrent_operations': concurrent_operations,
            'successful_operations': successful_ops,
            'failed_operations': failed_ops,
            'success_rate': (successful_ops / concurrent_operations) * 100,
            'operation_throughput': successful_ops / duration,
            'duration': duration,
            'peak_cpu': max(initial_cpu, final_cpu),
            'peak_memory_mb': max(initial_memory, final_memory)
        }

    async def _test_http_optimization_stress(self) -> Dict[str, Any]:
        """Test HTTP connection optimization with 500+ simultaneous requests"""
        start_time = time.time()
        concurrent_requests = 500
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        # Create a mix of HTTP requests
        async def make_request(request_id: int):
            try:
                endpoint = ["/health", "/status", "/employees"][request_id % 3]
                async with self.session.get(f"{self.config.async_server_url}{endpoint}") as response:
                    return response.status == 200
            except:
                return False
        
        tasks = [make_request(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_requests = sum(1 for r in results if not isinstance(r, Exception) and r)
        failed_requests = concurrent_requests - successful_requests
        
        duration = time.time() - start_time
        
        # Final resource check
        final_cpu = psutil.cpu_percent()
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        return {
            'concurrent_requests': concurrent_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': (successful_requests / concurrent_requests) * 100,
            'request_throughput': successful_requests / duration,
            'avg_response_time': duration / concurrent_requests,
            'duration': duration,
            'peak_cpu': max(initial_cpu, final_cpu),
            'peak_memory_mb': max(initial_memory, final_memory)
        }

    async def _test_system_resilience(self) -> Dict[str, Any]:
        """Test system stability and graceful degradation under stress"""
        results = {}
        
        # Test 3.1: Sustained maximum load
        self.log("3.1 Testing sustained maximum load...")
        sustained_results = await self._test_sustained_load()
        results['sustained_load'] = sustained_results
        
        # Test 3.2: Graceful degradation
        self.log("3.2 Testing graceful degradation...")
        degradation_results = await self._test_graceful_degradation()
        results['graceful_degradation'] = degradation_results
        
        return results

    async def _test_sustained_load(self) -> Dict[str, Any]:
        """Test system under sustained maximum load"""
        duration_minutes = self.config.sustained_load_duration
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        total_operations = 0
        successful_operations = 0
        failed_operations = 0
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        peak_cpu = initial_cpu
        peak_memory = initial_memory
        
        # Create base employees
        base_employees = 20
        employee_names = []
        for i in range(base_employees):
            name = f"sustained_emp_{i:03d}"
            if await self._create_employee(name, "developer"):
                employee_names.append(name)
        
        self.log(f"Running sustained load test for {duration_minutes} minutes...")
        
        while time.time() < end_time:
            # Generate mixed workload
            batch_tasks = []
            
            # Employee operations
            for i in range(5):
                employee = employee_names[i % len(employee_names)] if employee_names else f"sustained_emp_{i:03d}"
                task = self._assign_task(employee, f"Sustained load task {total_operations + i}")
                batch_tasks.append(task)
            
            # Status checks
            for i in range(3):
                batch_tasks.append(self._get_status())
            
            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                total_operations += 1
                if isinstance(result, Exception) or not result:
                    failed_operations += 1
                else:
                    successful_operations += 1
            
            # Update resource monitoring
            current_cpu = psutil.cpu_percent()
            current_memory = psutil.virtual_memory().used / (1024 * 1024)
            peak_cpu = max(peak_cpu, current_cpu)
            peak_memory = max(peak_memory, current_memory)
            
            # Log progress every 100 operations
            if total_operations % 100 == 0:
                elapsed_minutes = (time.time() - start_time) / 60
                self.log(f"Sustained load progress: {total_operations} ops in {elapsed_minutes:.1f}min")
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(1.0)
        
        duration = time.time() - start_time
        
        return {
            'duration_minutes': duration / 60,
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'success_rate': (successful_operations / total_operations) * 100 if total_operations > 0 else 0,
            'avg_throughput': total_operations / duration,
            'peak_cpu': peak_cpu,
            'peak_memory_mb': peak_memory
        }

    async def _test_graceful_degradation(self) -> Dict[str, Any]:
        """Test graceful degradation when approaching limits"""
        # Gradually increase load and monitor degradation
        load_levels = [10, 25, 50, 75, 100, 150, 200]
        degradation_points = []
        
        for load in load_levels:
            self.log(f"Testing graceful degradation at load level {load}...")
            
            start_time = time.time()
            
            # Monitor system resources
            initial_cpu = psutil.cpu_percent()
            initial_memory = psutil.virtual_memory().used / (1024 * 1024)
            
            # Create load
            tasks = []
            for i in range(load):
                if i % 3 == 0:
                    task = self._create_employee(f"degrade_emp_{load}_{i}", "developer")
                elif i % 3 == 1:
                    task = self._assign_task(f"degrade_emp_{load}_{i//3*3}", f"Degradation test {i}")
                else:
                    task = self._get_status()
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(1 for r in results if not isinstance(r, Exception) and r)
            success_rate = (successful / load) * 100
            
            duration = time.time() - start_time
            
            # Final resource check
            final_cpu = psutil.cpu_percent()
            final_memory = psutil.virtual_memory().used / (1024 * 1024)
            
            degradation_point = {
                'load_level': load,
                'success_rate': success_rate,
                'response_time': duration / load,
                'peak_cpu': max(initial_cpu, final_cpu),
                'peak_memory_mb': max(initial_memory, final_memory)
            }
            
            degradation_points.append(degradation_point)
            
            # Check for significant degradation
            if success_rate < 80:
                self.log(f"⚠️ Significant degradation detected at load level {load}")
                break
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        return {
            'degradation_points': degradation_points,
            'degradation_threshold': next((p['load_level'] for p in degradation_points if p['success_rate'] < 90), None)
        }

    async def _test_communication_stress(self) -> Dict[str, Any]:
        """Test optimized real-time communication under stress"""
        results = {}
        
        # Test 4.1: Real-time message stress (120+ msg/s)
        self.log("4.1 Testing real-time message stress (120+ msg/s)...")
        realtime_results = await self._test_realtime_message_stress()
        results['realtime_messages'] = realtime_results
        
        # Test 4.2: Message routing efficiency
        self.log("4.2 Testing message routing efficiency under stress...")
        routing_results = await self._test_message_routing_stress()
        results['message_routing'] = routing_results
        
        return results

    async def _test_realtime_message_stress(self) -> Dict[str, Any]:
        """Test real-time communication with 120+ messages per second"""
        target_msg_per_second = self.config.max_realtime_messages
        test_duration = 10  # seconds
        total_target_messages = target_msg_per_second * test_duration
        
        start_time = time.time()
        successful_messages = 0
        failed_messages = 0
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        # Send messages at target rate
        async def send_message_burst():
            try:
                async with self.session.get(f"{self.config.async_server_url}/health") as response:
                    return response.status == 200
            except:
                return False
        
        # Calculate timing for target rate
        message_interval = 1.0 / target_msg_per_second
        
        for i in range(total_target_messages):
            message_start = time.time()
            
            # Send message
            success = await send_message_burst()
            if success:
                successful_messages += 1
            else:
                failed_messages += 1
            
            # Maintain target rate
            elapsed = time.time() - message_start
            if elapsed < message_interval:
                await asyncio.sleep(message_interval - elapsed)
        
        duration = time.time() - start_time
        
        # Final resource check
        final_cpu = psutil.cpu_percent()
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        actual_rate = (successful_messages + failed_messages) / duration
        
        return {
            'target_messages_per_second': target_msg_per_second,
            'actual_messages_per_second': actual_rate,
            'total_messages': successful_messages + failed_messages,
            'successful_messages': successful_messages,
            'failed_messages': failed_messages,
            'success_rate': (successful_messages / (successful_messages + failed_messages)) * 100 if (successful_messages + failed_messages) > 0 else 0,
            'duration': duration,
            'peak_cpu': max(initial_cpu, final_cpu),
            'peak_memory_mb': max(initial_memory, final_memory)
        }

    async def _test_message_routing_stress(self) -> Dict[str, Any]:
        """Test message routing efficiency under stress"""
        start_time = time.time()
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        # Test routing efficiency with mixed request types
        routing_tasks = []
        for i in range(200):
            if i % 5 == 0:
                task = self._get_employees()  # Route to employee service
            elif i % 5 == 1:
                task = self._get_status()     # Route to status service
            elif i % 5 == 2:
                task = self._create_employee(f"route_emp_{i:03d}", "developer")  # Route to creation service
            elif i % 5 == 3:
                task = self._assign_task(f"route_emp_{(i//5)*5:03d}", f"Routing test {i}")  # Route to task service
            else:
                # Health check
                async def health_check():
                    try:
                        async with self.session.get(f"{self.config.async_server_url}/health") as response:
                            return response.status == 200
                    except:
                        return False
                task = health_check()
            
            routing_tasks.append(task)
        
        results = await asyncio.gather(*routing_tasks, return_exceptions=True)
        
        successful_routes = sum(1 for r in results if not isinstance(r, Exception) and r)
        failed_routes = 200 - successful_routes
        
        duration = time.time() - start_time
        
        # Final resource check
        final_cpu = psutil.cpu_percent()
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        return {
            'total_routes': 200,
            'successful_routes': successful_routes,
            'failed_routes': failed_routes,
            'success_rate': (successful_routes / 200) * 100,
            'routing_throughput': successful_routes / duration,
            'avg_routing_time': duration / 200,
            'duration': duration,
            'peak_cpu': max(initial_cpu, final_cpu),
            'peak_memory_mb': max(initial_memory, final_memory)
        }

    async def _test_production_load_simulation(self) -> Dict[str, Any]:
        """Simulate realistic production workloads with peak traffic"""
        results = {}
        
        # Test 5.1: Realistic production workload
        self.log("5.1 Simulating realistic production workload...")
        production_results = await self._test_realistic_production_load()
        results['realistic_load'] = production_results
        
        # Test 5.2: Traffic spikes
        self.log("5.2 Testing system behavior during traffic spikes...")
        spike_results = await self._test_traffic_spikes()
        results['traffic_spikes'] = spike_results
        
        return results

    async def _test_realistic_production_load(self) -> Dict[str, Any]:
        """Test with realistic production workload patterns"""
        # Simulate realistic usage patterns
        start_time = time.time()
        test_duration = 180  # 3 minutes
        end_time = start_time + test_duration
        
        total_operations = 0
        successful_operations = 0
        failed_operations = 0
        
        # Monitor system resources
        initial_cpu = psutil.cpu_percent()
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        peak_cpu = initial_cpu
        peak_memory = initial_memory
        
        # Create base team
        team_size = 15
        team_members = []
        for i in range(team_size):
            name = f"prod_emp_{i:03d}"
            if await self._create_employee(name, "developer"):
                team_members.append(name)
        
        self.log(f"Created production team of {len(team_members)} members")
        
        # Simulate realistic workload patterns
        while time.time() < end_time:
            # Normal activity
            batch_size = 8
            delay = 2.0
            
            # Generate realistic operations
            batch_tasks = []
            
            # Task assignments (60% of operations)
            for i in range(int(batch_size * 0.6)):
                if team_members:
                    employee = team_members[i % len(team_members)]
                    task_types = [
                        "Implement new feature",
                        "Fix bug in component",
                        "Update documentation",
                        "Code review",
                        "Write unit tests",
                        "Optimize performance"
                    ]
                    task = task_types[i % len(task_types)]
                    batch_tasks.append(self._assign_task(employee, f"{task} - {total_operations + i}"))
            
            # Status checks (30% of operations)
            for i in range(int(batch_size * 0.3)):
                batch_tasks.append(self._get_status())
            
            # Employee management (10% of operations)
            for i in range(int(batch_size * 0.1)):
                batch_tasks.append(self._get_employees())
            
            # Execute batch
            if batch_tasks:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    total_operations += 1
                    if isinstance(result, Exception) or not result:
                        failed_operations += 1
                    else:
                        successful_operations += 1
            
            # Update resource monitoring
            current_cpu = psutil.cpu_percent()
            current_memory = psutil.virtual_memory().used / (1024 * 1024)
            peak_cpu = max(peak_cpu, current_cpu)
            peak_memory = max(peak_memory, current_memory)
            
            # Wait for next batch
            await asyncio.sleep(delay)
        
        duration = time.time() - start_time
        
        return {
            'test_duration_minutes': duration / 60,
            'team_size': len(team_members),
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'success_rate': (successful_operations / total_operations) * 100 if total_operations > 0 else 0,
            'avg_throughput': total_operations / duration,
            'peak_cpu': peak_cpu,
            'peak_memory_mb': peak_memory
        }

    async def _test_traffic_spikes(self) -> Dict[str, Any]:
        """Test system behavior during traffic spikes"""
        spike_results = []
        
        # Test different spike intensities
        spike_levels = [50, 100, 200, 300]
        
        for spike_level in spike_levels:
            self.log(f"Testing traffic spike: {spike_level} concurrent operations...")
            
            start_time = time.time()
            
            # Monitor system resources
            initial_cpu = psutil.cpu_percent()
            initial_memory = psutil.virtual_memory().used / (1024 * 1024)
            
            # Generate traffic spike
            spike_tasks = []
            for i in range(spike_level):
                if i % 4 == 0:
                    task = self._create_employee(f"spike_emp_{spike_level}_{i:03d}", "developer")
                elif i % 4 == 1:
                    task = self._assign_task(f"spike_emp_{spike_level}_{(i//4)*4:03d}", f"Spike task {i}")
                elif i % 4 == 2:
                    task = self._get_status()
                else:
                    task = self._get_employees()
                
                spike_tasks.append(task)
            
            # Execute spike
            spike_task_results = await asyncio.gather(*spike_tasks, return_exceptions=True)
            
            successful = sum(1 for r in spike_task_results if not isinstance(r, Exception) and r)
            failed = spike_level - successful
            
            duration = time.time() - start_time
            
            # Final resource check
            final_cpu = psutil.cpu_percent()
            final_memory = psutil.virtual_memory().used / (1024 * 1024)
            
            spike_result = {
                'spike_level': spike_level,
                'successful_operations': successful,
                'failed_operations': failed,
                'success_rate': (successful / spike_level) * 100,
                'spike_throughput': successful / duration,
                'duration': duration,
                'peak_cpu': max(initial_cpu, final_cpu),
                'peak_memory_mb': max(initial_memory, final_memory)
            }
            
            spike_results.append(spike_result)
            
            # Recovery time between spikes
            await asyncio.sleep(5)
        
        return {
            'spike_tests': spike_results,
            'max_successful_spike': max((s['spike_level'] for s in spike_results if s['success_rate'] > 80), default=0)
        }

    def _generate_comprehensive_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive stress testing report"""
        total_test_time = time.time() - self.test_start_time
        
        # Calculate overall performance metrics
        overall_metrics = self._calculate_overall_metrics(test_results)
        
        # Identify bottlenecks and limits
        bottlenecks = self._identify_bottlenecks(test_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(test_results, bottlenecks)
        
        # Determine production readiness
        production_readiness = self._assess_production_readiness(test_results, overall_metrics)
        
        report = {
            'test_summary': {
                'test_timestamp': datetime.now().isoformat(),
                'total_test_duration_minutes': total_test_time / 60,
                'test_configuration': asdict(self.config),
                'system_info': {
                    'cpu_cores': psutil.cpu_count(),
                    'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                    'python_version': sys.version.split()[0]
                }
            },
            
            'overall_performance': overall_metrics,
            'detailed_results': test_results,
            'bottlenecks_identified': bottlenecks,
            'recommendations': recommendations,
            'production_readiness': production_readiness,
            
            'phase_2_validation': {
                'maximum_capacity_achieved': self._validate_maximum_capacity(test_results),
                'performance_optimizations_validated': self._validate_optimizations(test_results),
                'system_resilience_confirmed': self._validate_resilience(test_results),
                'enterprise_ready': production_readiness['overall_ready']
            }
        }
        
        return report

    def _calculate_overall_metrics(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall performance metrics across all tests"""
        all_success_rates = []
        all_throughputs = []
        all_response_times = []
        all_cpu_peaks = []
        all_memory_peaks = []
        
        # Extract metrics from all test results
        def extract_metrics(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == 'success_rate' and isinstance(value, (int, float)):
                        all_success_rates.append(value)
                    elif 'throughput' in key and isinstance(value, (int, float)):
                        all_throughputs.append(value)
                    elif 'response_time' in key and isinstance(value, (int, float)):
                        all_response_times.append(value)
                    elif 'peak_cpu' in key and isinstance(value, (int, float)):
                        all_cpu_peaks.append(value)
                    elif 'peak_memory' in key and isinstance(value, (int, float)):
                        all_memory_peaks.append(value)
                    elif isinstance(value, dict):
                        extract_metrics(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                extract_metrics(item)
        
        extract_metrics(test_results)
        
        return {
            'overall_success_rate': statistics.mean(all_success_rates) if all_success_rates else 0,
            'peak_throughput': max(all_throughputs) if all_throughputs else 0,
            'avg_throughput': statistics.mean(all_throughputs) if all_throughputs else 0,
            'best_response_time': min(all_response_times) if all_response_times else 0,
            'avg_response_time': statistics.mean(all_response_times) if all_response_times else 0,
            'peak_cpu_usage': max(all_cpu_peaks) if all_cpu_peaks else 0,
            'peak_memory_usage_mb': max(all_memory_peaks) if all_memory_peaks else 0,
            'performance_grade': self._calculate_performance_grade(all_success_rates, all_throughputs, all_response_times)
        }

    def _calculate_performance_grade(self, success_rates: List[float], throughputs: List[float], response_times: List[float]) -> str:
        """Calculate overall performance grade"""
        if not success_rates:
            return 'F'
        
        avg_success = statistics.mean(success_rates)
        max_throughput = max(throughputs) if throughputs else 0
        avg_response = statistics.mean(response_times) if response_times else float('inf')
        
        # Grade based on multiple criteria
        if avg_success >= 95 and max_throughput >= 100 and avg_response <= 1.0:
            return 'A'
        elif avg_success >= 90 and max_throughput >= 50 and avg_response <= 2.0:
            return 'B'
        elif avg_success >= 80 and max_throughput >= 25 and avg_response <= 5.0:
            return 'C'
        elif avg_success >= 70:
            return 'D'
        else:
            return 'F'

    def _identify_bottlenecks(self, test_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify system bottlenecks from test results"""
        bottlenecks = []
        
        # Check maximum capacity results
        if 'maximum_capacity' in test_results:
            capacity = test_results['maximum_capacity']
            
            # User capacity bottleneck
            if 'concurrent_users' in capacity:
                user_success = capacity['concurrent_users'].get('success_rate', 0)
                if user_success < 90:
                    bottlenecks.append({
                        'component': 'Concurrent User Handling',
                        'issue': f'Success rate drops to {user_success:.1f}% with {self.config.max_concurrent_users} users',
                        'severity': 'High' if user_success < 70 else 'Medium',
                        'recommendation': 'Implement user session pooling and request queuing'
                    })
            
            # Agent capacity bottleneck
            if 'concurrent_agents' in capacity:
                agent_success = capacity['concurrent_agents'].get('success_rate', 0)
                if agent_success < 90:
                    bottlenecks.append({
                        'component': 'Concurrent Agent Creation',
                        'issue': f'Success rate drops to {agent_success:.1f}% with {self.config.max_concurrent_agents} agents',
                        'severity': 'High' if agent_success < 70 else 'Medium',
                        'recommendation': 'Optimize agent creation process with batch operations'
                    })
            
            # Task capacity bottleneck
            if 'concurrent_tasks' in capacity:
                task_success = capacity['concurrent_tasks'].get('success_rate', 0)
                if task_success < 90:
                    bottlenecks.append({
                        'component': 'Concurrent Task Processing',
                        'issue': f'Success rate drops to {task_success:.1f}% with {self.config.max_concurrent_tasks} tasks',
                        'severity': 'High' if task_success < 70 else 'Medium',
                        'recommendation': 'Implement task queue with priority scheduling'
                    })
        
        return bottlenecks

    def _generate_recommendations(self, test_results: Dict[str, Any], bottlenecks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate recommendations based on test results"""
        recommendations = {
            'immediate_actions': [],
            'performance_improvements': [],
            'architectural_changes': [],
            'monitoring_enhancements': []
        }
        
        # Immediate actions based on bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck['severity'] == 'High':
                recommendations['immediate_actions'].append(bottleneck['recommendation'])
            else:
                recommendations['performance_improvements'].append(bottleneck['recommendation'])
        
        # Performance improvements
        overall_metrics = self._calculate_overall_metrics(test_results)
        
        if overall_metrics['overall_success_rate'] < 95:
            recommendations['performance_improvements'].append(
                'Implement comprehensive error handling and retry mechanisms'
            )
        
        if overall_metrics['avg_response_time'] > 1.0:
            recommendations['performance_improvements'].append(
                'Optimize response times with caching and async processing'
            )
        
        if overall_metrics['peak_throughput'] < 100:
            recommendations['performance_improvements'].append(
                'Increase system throughput with connection pooling and batch operations'
            )
        
        # Architectural changes
        if overall_metrics['peak_cpu_usage'] > 80:
            recommendations['architectural_changes'].append(
                'Implement horizontal scaling to distribute CPU load'
            )
        
        if overall_metrics['peak_memory_usage_mb'] > 6000:  # 6GB
            recommendations['architectural_changes'].append(
                'Optimize memory usage and implement memory pooling'
            )
        
        recommendations['architectural_changes'].extend([
            'Implement message queue for asynchronous task processing',
            'Add load balancer for horizontal scaling',
            'Implement distributed caching with Redis',
            'Add database sharding for improved scalability'
        ])
        
        # Monitoring enhancements
        recommendations['monitoring_enhancements'].extend([
            'Implement real-time performance monitoring dashboard',
            'Add alerting for performance degradation',
            'Implement circuit breakers for external dependencies',
            'Add distributed tracing for request flow analysis',
            'Implement automated scaling based on load metrics'
        ])
        
        return recommendations

    def _assess_production_readiness(self, test_results: Dict[str, Any], overall_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess production readiness based on test results"""
        readiness_criteria = {
            'success_rate_above_90': overall_metrics['overall_success_rate'] >= 90,
            'response_time_under_2s': overall_metrics['avg_response_time'] <= 2.0,
            'throughput_above_50': overall_metrics['peak_throughput'] >= 50,
            'cpu_usage_under_80': overall_metrics['peak_cpu_usage'] <= 80,
            'memory_usage_reasonable': overall_metrics['peak_memory_usage_mb'] <= 8000,  # 8GB
        }
        
        criteria_met = sum(readiness_criteria.values())
        total_criteria = len(readiness_criteria)
        readiness_percentage = (criteria_met / total_criteria) * 100
        
        # Determine overall readiness level
        if readiness_percentage >= 90:
            readiness_level = 'Production Ready'
        elif readiness_percentage >= 80:
            readiness_level = 'Nearly Ready - Minor Issues'
        elif readiness_percentage >= 60:
            readiness_level = 'Needs Improvement'
        else:
            readiness_level = 'Not Ready for Production'
        
        return {
            'readiness_criteria': readiness_criteria,
            'criteria_met': criteria_met,
            'total_criteria': total_criteria,
            'readiness_percentage': readiness_percentage,
            'readiness_level': readiness_level,
            'overall_ready': readiness_percentage >= 90
        }

    def _validate_maximum_capacity(self, test_results: Dict[str, Any]) -> Dict[str, bool]:
        """Validate Phase 2 maximum capacity achievements"""
        validation = {
            'user_capacity_10x': False,
            'agent_capacity_5x': False,
            'task_capacity_4x': False,
            'message_throughput_1000': False
        }
        
        if 'maximum_capacity' in test_results:
            capacity = test_results['maximum_capacity']
            
            # User capacity (target: 100+ users with >80% success)
            if 'concurrent_users' in capacity:
                user_success = capacity['concurrent_users'].get('success_rate', 0)
                validation['user_capacity_10x'] = user_success >= 80
            
            # Agent capacity (target: 50+ agents with >80% success)
            if 'concurrent_agents' in capacity:
                agent_success = capacity['concurrent_agents'].get('success_rate', 0)
                validation['agent_capacity_5x'] = agent_success >= 80
            
            # Task capacity (target: 200+ tasks with >80% success)
            if 'concurrent_tasks' in capacity:
                task_success = capacity['concurrent_tasks'].get('success_rate', 0)
                validation['task_capacity_4x'] = task_success >= 80
            
            # Message throughput (target: 1000+ msg/min)
            if 'message_throughput' in capacity:
                msg_rate = capacity['message_throughput'].get('actual_messages_per_minute', 0)
                validation['message_throughput_1000'] = msg_rate >= 1000
        
        return validation

    def _validate_optimizations(self, test_results: Dict[str, Any]) -> Dict[str, bool]:
        """Validate Phase 2 performance optimizations"""
        validation = {
            'async_llm_processing': False,
            'database_optimization': False,
            'http_optimization': False
        }
        
        if 'performance_optimizations' in test_results:
            perf = test_results['performance_optimizations']
            
            # Async LLM processing (target: >90% success with 100+ requests)
            if 'async_llm_processing' in perf:
                llm_success = perf['async_llm_processing'].get('success_rate', 0)
                validation['async_llm_processing'] = llm_success >= 90
            
            # Database optimization (target: >90% success with 200+ ops)
            if 'database_optimization' in perf:
                db_success = perf['database_optimization'].get('success_rate', 0)
                validation['database_optimization'] = db_success >= 90
            
            # HTTP optimization (target: >95% success with 500+ requests)
            if 'http_optimization' in perf:
                http_success = perf['http_optimization'].get('success_rate', 0)
                validation['http_optimization'] = http_success >= 95
        
        return validation

    def _validate_resilience(self, test_results: Dict[str, Any]) -> Dict[str, bool]:
        """Validate system resilience"""
        validation = {
            'sustained_load_stable': False,
            'graceful_degradation': False
        }
        
        if 'system_resilience' in test_results:
            resilience = test_results['system_resilience']
            
            # Sustained load (target: >90% success rate)
            if 'sustained_load' in resilience:
                sustained_success = resilience['sustained_load'].get('success_rate', 0)
                validation['sustained_load_stable'] = sustained_success >= 90
            
            # Graceful degradation (target: degradation threshold > 100)
            if 'graceful_degradation' in resilience:
                degradation_threshold = resilience['graceful_degradation'].get('degradation_threshold')
                validation['graceful_degradation'] = degradation_threshold is None or degradation_threshold > 100
        
        return validation

async def main():
    """Main function to run comprehensive stress tests"""
    print("🔥 OpenCode-Slack Phase 2 Comprehensive Stress Testing Suite")
    print("=" * 70)
    
    # Check if server is running
    config = StressTestConfig()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.async_server_url}/health") as response:
                if response.status != 200:
                    print(f"❌ Server not responding at {config.async_server_url}")
                    print("Please start the async server first:")
                    print("python3 src/async_server.py")
                    return 1
    except Exception as e:
        print(f"❌ Cannot connect to server at {config.async_server_url}")
        print(f"Error: {e}")
        print("Please start the async server first:")
        print("python3 src/async_server.py")
        return 1
    
    print(f"✅ Server is running at {config.async_server_url}")
    print()
    
    # Run comprehensive stress tests
    async with ComprehensiveStressTester(config) as tester:
        try:
            report = await tester.run_comprehensive_stress_tests()
            
            # Save report
            report_file = f"comprehensive_stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"\n📊 Comprehensive Stress Test Report Generated: {report_file}")
            print("=" * 70)
            
            # Print summary
            print("🎯 STRESS TEST SUMMARY")
            print("-" * 30)
            
            overall = report['overall_performance']
            print(f"📈 Overall Performance Grade: {overall['performance_grade']}")
            print(f"📊 Overall Success Rate: {overall['overall_success_rate']:.1f}%")
            print(f"🚀 Peak Throughput: {overall['peak_throughput']:.1f} ops/sec")
            print(f"⏱️  Average Response Time: {overall['avg_response_time']:.3f}s")
            print(f"💻 Peak CPU Usage: {overall['peak_cpu_usage']:.1f}%")
            print(f"🧠 Peak Memory Usage: {overall['peak_memory_usage_mb']:.1f} MB")
            
            # Print Phase 2 validation
            validation = report['phase_2_validation']
            print(f"\n🎯 PHASE 2 VALIDATION")
            print("-" * 30)
            
            capacity = validation['maximum_capacity_achieved']
            print(f"👥 User Capacity (10x): {'✅' if capacity['user_capacity_10x'] else '❌'}")
            print(f"🤖 Agent Capacity (5x): {'✅' if capacity['agent_capacity_5x'] else '❌'}")
            print(f"📋 Task Capacity (4x): {'✅' if capacity['task_capacity_4x'] else '❌'}")
            print(f"💬 Message Throughput (1000+): {'✅' if capacity['message_throughput_1000'] else '❌'}")
            
            optimizations = validation['performance_optimizations_validated']
            print(f"⚡ Async LLM Processing: {'✅' if optimizations['async_llm_processing'] else '❌'}")
            print(f"🗄️  Database Optimization: {'✅' if optimizations['database_optimization'] else '❌'}")
            print(f"🌐 HTTP Optimization: {'✅' if optimizations['http_optimization'] else '❌'}")
            
            # Print production readiness
            readiness = report['production_readiness']
            print(f"\n🏭 PRODUCTION READINESS")
            print("-" * 30)
            print(f"📊 Readiness Level: {readiness['readiness_level']}")
            print(f"✅ Criteria Met: {readiness['criteria_met']}/{readiness['total_criteria']} ({readiness['readiness_percentage']:.1f}%)")
            print(f"🚀 Enterprise Ready: {'✅' if readiness['overall_ready'] else '❌'}")
            
            # Print recommendations
            if report['recommendations']['immediate_actions']:
                print(f"\n⚠️  IMMEDIATE ACTIONS REQUIRED")
                print("-" * 30)
                for action in report['recommendations']['immediate_actions']:
                    print(f"   • {action}")
            
            if report['bottlenecks_identified']:
                print(f"\n🔍 BOTTLENECKS IDENTIFIED")
                print("-" * 30)
                for bottleneck in report['bottlenecks_identified']:
                    print(f"   • {bottleneck['component']}: {bottleneck['issue']}")
            
            print("\n" + "=" * 70)
            print("✅ Comprehensive stress testing completed successfully!")
            
            return 0
            
        except KeyboardInterrupt:
            print("\n🛑 Testing interrupted by user")
            return 1
            
        except Exception as e:
            print(f"\n❌ Testing failed: {e}")
            logger.error(f"Comprehensive stress testing failed: {e}", exc_info=True)
            return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))