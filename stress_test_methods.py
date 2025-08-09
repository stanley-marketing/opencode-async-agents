#!/usr/bin/env python3
"""
Stress Test Methods - Core testing functionality for comprehensive stress testing
"""

import asyncio
import time
import statistics
import random
from typing import Dict, Any

class StressTestMethods:
    """Core stress testing methods"""
    
    async def run_comprehensive_stress_tests(self) -> Dict[str, Any]:
        """Run all comprehensive stress tests"""
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
            
            # Test 4: Concurrency Stress Testing
            self.log("=== PHASE 4: CONCURRENCY STRESS TESTING ===")
            concurrency_results = await self._test_concurrency_stress()
            
            # Test 5: Communication Stress Testing
            self.log("=== PHASE 5: COMMUNICATION STRESS TESTING ===")
            communication_results = await self._test_communication_stress()
            
            # Test 6: Integration Stress Testing
            self.log("=== PHASE 6: INTEGRATION STRESS TESTING ===")
            integration_results = await self._test_integration_stress()
            
            # Test 7: Production Load Simulation
            self.log("=== PHASE 7: PRODUCTION LOAD SIMULATION ===")
            production_results = await self._test_production_load_simulation()
            
            # Test 8: Failure Scenario Testing
            self.log("=== PHASE 8: FAILURE SCENARIO TESTING ===")
            failure_results = await self._test_failure_scenarios()
            
            # Generate comprehensive report
            report = self._generate_comprehensive_report({
                'maximum_capacity': capacity_results,
                'performance_optimizations': optimization_results,
                'system_resilience': resilience_results,
                'concurrency_stress': concurrency_results,
                'communication_stress': communication_results,
                'integration_stress': integration_results,
                'production_load': production_results,
                'failure_scenarios': failure_results
            })
            
            return report
            
        except Exception as e:
            self.log(f"❌ Comprehensive stress testing failed: {e}", "ERROR")
            raise
        finally:
            await self.cleanup_test_data()

    async def _test_maximum_capacity(self) -> Dict[str, Any]:
        """Test maximum capacity improvements (10x users, 5x agents, 4x tasks)"""
        self.log("Testing maximum capacity improvements...")
        
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
        self.resource_monitor.start_monitoring()
        
        start_time = time.time()
        successful_operations = 0
        failed_operations = 0
        response_times = []
        
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
        metrics = self.resource_monitor.stop_monitoring()
        
        return {
            'target_users': target_users,
            'duration': duration,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'total_operations': successful_operations + failed_operations,
            'success_rate': (successful_operations / (successful_operations + failed_operations)) * 100 if (successful_operations + failed_operations) > 0 else 0,
            'throughput': (successful_operations + failed_operations) / duration,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'peak_cpu': max(m.cpu_percent for m in metrics) if metrics else 0,
            'peak_memory_mb': max(m.memory_mb for m in metrics) if metrics else 0
        }

    async def _test_concurrent_agents(self, target_agents: int) -> Dict[str, Any]:
        """Test system with concurrent agents"""
        self.resource_monitor.start_monitoring()
        
        start_time = time.time()
        
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
        metrics = self.resource_monitor.stop_monitoring()
        
        return {
            'target_agents': target_agents,
            'successful_creations': successful_creations,
            'failed_creations': failed_creations,
            'success_rate': (successful_creations / target_agents) * 100,
            'creation_throughput': successful_creations / duration,
            'duration': duration,
            'peak_cpu': max(m.cpu_percent for m in metrics) if metrics else 0,
            'peak_memory_mb': max(m.memory_mb for m in metrics) if metrics else 0
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
        
        self.resource_monitor.start_monitoring()
        start_time = time.time()
        
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
        metrics = self.resource_monitor.stop_monitoring()
        
        return {
            'target_tasks': target_tasks,
            'employees_created': len(employee_names),
            'successful_assignments': successful_assignments,
            'failed_assignments': failed_assignments,
            'success_rate': (successful_assignments / target_tasks) * 100,
            'assignment_throughput': successful_assignments / duration,
            'duration': duration,
            'peak_cpu': max(m.cpu_percent for m in metrics) if metrics else 0,
            'peak_memory_mb': max(m.memory_mb for m in metrics) if metrics else 0
        }

    async def _test_message_throughput(self, target_messages_per_minute: int) -> Dict[str, Any]:
        """Test message throughput capacity"""
        self.resource_monitor.start_monitoring()
        
        start_time = time.time()
        test_duration = 60  # 1 minute test
        target_messages = target_messages_per_minute
        
        successful_messages = 0
        failed_messages = 0
        
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
        metrics = self.resource_monitor.stop_monitoring()
        
        actual_throughput = (successful_messages + failed_messages) / (duration / 60)  # per minute
        
        return {
            'target_messages_per_minute': target_messages_per_minute,
            'actual_messages_per_minute': actual_throughput,
            'successful_messages': successful_messages,
            'failed_messages': failed_messages,
            'success_rate': (successful_messages / (successful_messages + failed_messages)) * 100 if (successful_messages + failed_messages) > 0 else 0,
            'duration': duration,
            'peak_cpu': max(m.cpu_percent for m in metrics) if metrics else 0,
            'peak_memory_mb': max(m.memory_mb for m in metrics) if metrics else 0
        }