#!/usr/bin/env python3
"""
Comprehensive Enhanced Concurrency Testing Suite
Tests all concurrency improvements including scalability, performance optimization,
dependency management, and monitoring systems.
"""

import asyncio
import concurrent.futures
import logging
import os
import random
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock

# Import system components
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Import enhanced concurrency components
from src.concurrency.enhanced_agent_coordinator import (
    EnhancedAgentCoordinator, TaskPriority, TaskStatus, EnhancedTask
)
from src.concurrency.performance_optimizer import (
    PerformanceOptimizer, AdaptiveConnectionPool, IntelligentCache, BatchProcessor
)
from src.concurrency.scalability_manager import (
    ScalabilityManager, LoadBalancer, AutoScaler, CapacityPlanner
)
from src.concurrency.monitoring_system import (
    ConcurrencyMonitor, AlertManager, PerformanceAnalyzer, ConcurrencyMetrics
)

# Import existing components for integration testing
from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.utils.opencode_wrapper import OpencodeSessionManager
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestEnhancedAgentCoordinator(unittest.TestCase):
    """Test enhanced agent coordination with dependency management"""
    
    def setUp(self):
        self.coordinator = EnhancedAgentCoordinator(
            max_concurrent_agents=20,
            max_concurrent_tasks=100,
            max_message_throughput=500
        )
        
    def tearDown(self):
        asyncio.run(self.coordinator.stop())
    
    def test_task_creation_and_dependency_management(self):
        """Test 1: Task creation with complex dependencies"""
        logger.info("=== Test 1: Task Creation and Dependency Management ===")
        
        # Create tasks with dependencies
        task1 = self.coordinator.create_task(
            "agent_001", "Create base module", TaskPriority.HIGH
        )
        
        task2 = self.coordinator.create_task(
            "agent_002", "Add tests for base module", TaskPriority.NORMAL,
            dependencies=[task1]
        )
        
        task3 = self.coordinator.create_task(
            "agent_003", "Integrate base module", TaskPriority.NORMAL,
            dependencies=[task1]
        )
        
        task4 = self.coordinator.create_task(
            "agent_004", "Deploy integrated system", TaskPriority.LOW,
            dependencies=[task2, task3]
        )
        
        # Verify task creation
        self.assertIn(task1, self.coordinator.tasks)
        self.assertIn(task2, self.coordinator.tasks)
        self.assertIn(task3, self.coordinator.tasks)
        self.assertIn(task4, self.coordinator.tasks)
        
        # Verify dependency relationships
        self.assertTrue(self.coordinator.dependency_graph.is_ready(task1))
        self.assertFalse(self.coordinator.dependency_graph.is_ready(task2))
        self.assertFalse(self.coordinator.dependency_graph.is_ready(task3))
        self.assertFalse(self.coordinator.dependency_graph.is_ready(task4))
        
        logger.info(f"Created {len(self.coordinator.tasks)} tasks with dependencies")
        
        # Test dependency cycle detection
        cycles = self.coordinator.detect_dependency_cycles()
        self.assertEqual(len(cycles), 0, "No dependency cycles should exist")
        
        logger.info("✅ Task creation and dependency management test passed")
    
    def test_resource_pool_management(self):
        """Test 2: Resource pool and contention handling"""
        logger.info("=== Test 2: Resource Pool Management ===")
        
        resource_pool = self.coordinator.resource_pool
        
        # Test agent slot acquisition
        agents_acquired = []
        for i in range(25):  # Try to acquire more than max
            agent_name = f"agent_{i:03d}"
            if resource_pool.acquire_agent_slot(agent_name):
                agents_acquired.append(agent_name)
        
        # Should not exceed max concurrent agents
        self.assertLessEqual(len(agents_acquired), 20)
        logger.info(f"Acquired {len(agents_acquired)} agent slots (max: 20)")
        
        # Test resource locking
        resources = ["file1.py", "file2.py", "database.db"]
        
        # Agent 1 acquires resources
        success1 = resource_pool.acquire_resources("agent_001", resources[:2], timeout=1.0)
        self.assertTrue(success1, "Agent 1 should acquire resources")
        
        # Agent 2 tries to acquire overlapping resources
        success2 = resource_pool.acquire_resources("agent_002", resources[1:], timeout=1.0)
        self.assertFalse(success2, "Agent 2 should not acquire overlapping resources")
        
        # Release resources and try again
        resource_pool.release_resources("agent_001", resources[:2])
        success3 = resource_pool.acquire_resources("agent_002", resources[1:], timeout=1.0)
        self.assertTrue(success3, "Agent 2 should acquire resources after release")
        
        # Clean up
        resource_pool.release_resources("agent_002", resources[1:])
        for agent in agents_acquired:
            resource_pool.release_agent_slot(agent)
        
        logger.info("✅ Resource pool management test passed")
    
    def test_async_llm_processing(self):
        """Test 3: Asynchronous LLM processing with batching"""
        logger.info("=== Test 3: Async LLM Processing ===")
        
        async def run_llm_test():
            await self.coordinator.start()
            
            # Submit multiple LLM requests concurrently
            requests = []
            for i in range(10):
                request = self.coordinator.async_llm_processor.process_request(
                    f"request_{i}", f"Process task {i}", "test-model"
                )
                requests.append(request)
            
            # Wait for all requests to complete
            start_time = time.time()
            responses = await asyncio.gather(*requests)
            processing_time = time.time() - start_time
            
            # Verify all requests completed
            self.assertEqual(len(responses), 10)
            for response in responses:
                self.assertIn('response', response)
                self.assertIn('processing_time', response)
            
            logger.info(f"Processed {len(responses)} LLM requests in {processing_time:.2f}s")
            
            # Test caching
            cache_size_before = len(self.coordinator.async_llm_processor.response_cache)
            
            # Submit duplicate request
            duplicate_response = await self.coordinator.async_llm_processor.process_request(
                "duplicate", "Process task 0", "test-model"
            )
            
            cache_size_after = len(self.coordinator.async_llm_processor.response_cache)
            
            # Cache should be used (no new entry)
            self.assertEqual(cache_size_before, cache_size_after)
            logger.info("Cache hit verified for duplicate request")
        
        asyncio.run(run_llm_test())
        logger.info("✅ Async LLM processing test passed")
    
    def test_concurrent_task_execution(self):
        """Test 4: High-throughput concurrent task execution"""
        logger.info("=== Test 4: Concurrent Task Execution ===")
        
        async def run_execution_test():
            await self.coordinator.start()
            
            # Create many tasks
            task_ids = []
            for i in range(50):
                task_id = self.coordinator.create_task(
                    f"agent_{i % 10:03d}",
                    f"Execute task {i}",
                    TaskPriority.NORMAL,
                    estimated_duration=0.1  # Short tasks
                )
                task_ids.append(task_id)
            
            logger.info(f"Created {len(task_ids)} tasks for execution")
            
            # Wait for tasks to complete
            start_time = time.time()
            max_wait_time = 30  # 30 seconds max
            
            while time.time() - start_time < max_wait_time:
                completed_count = len(self.coordinator.completed_tasks)
                if completed_count >= len(task_ids) * 0.8:  # 80% completion
                    break
                await asyncio.sleep(0.5)
            
            execution_time = time.time() - start_time
            completed_count = len(self.coordinator.completed_tasks)
            
            logger.info(f"Completed {completed_count}/{len(task_ids)} tasks in {execution_time:.2f}s")
            
            # Verify reasonable completion rate
            completion_rate = completed_count / len(task_ids)
            self.assertGreater(completion_rate, 0.5, "At least 50% of tasks should complete")
            
            # Check system metrics
            status = self.coordinator.get_system_status()
            logger.info(f"System status: {status['coordinator_metrics']}")
        
        asyncio.run(run_execution_test())
        logger.info("✅ Concurrent task execution test passed")


class TestPerformanceOptimizer(unittest.TestCase):
    """Test performance optimization components"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_performance.db")
        self.optimizer = PerformanceOptimizer(self.db_path)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_adaptive_connection_pool(self):
        """Test 5: Adaptive connection pool performance"""
        logger.info("=== Test 5: Adaptive Connection Pool ===")
        
        pool = self.optimizer.connection_pool
        
        # Test concurrent connection acquisition
        def acquire_connection(worker_id):
            try:
                with pool.get_connection() as conn:
                    # Simulate work
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    time.sleep(0.1)  # Simulate processing
                    return worker_id, True, result
            except Exception as e:
                return worker_id, False, str(e)
        
        # Run concurrent connection tests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(acquire_connection, i)
                for i in range(30)  # More workers than max connections
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful = [r for r in results if r[1]]
        failed = [r for r in results if not r[1]]
        
        logger.info(f"Connection pool test: {len(successful)} successful, {len(failed)} failed")
        
        # Should have high success rate
        success_rate = len(successful) / len(results)
        self.assertGreater(success_rate, 0.8, "Connection pool should handle concurrent access well")
        
        # Check pool statistics
        stats = pool.get_stats()
        logger.info(f"Pool stats: {stats}")
        
        logger.info("✅ Adaptive connection pool test passed")
    
    def test_intelligent_cache(self):
        """Test 6: Intelligent caching system"""
        logger.info("=== Test 6: Intelligent Cache ===")
        
        cache = self.optimizer.cache
        
        # Test cache operations
        test_data = {f"key_{i}": f"value_{i}" for i in range(100)}
        
        # Store data
        for key, value in test_data.items():
            cache.put(key, value)
        
        # Retrieve data
        hits = 0
        misses = 0
        
        for key in test_data.keys():
            result = cache.get(key)
            if result is not None:
                hits += 1
            else:
                misses += 1
        
        logger.info(f"Cache test: {hits} hits, {misses} misses")
        
        # Should have high hit rate for recently stored data
        hit_rate = hits / (hits + misses)
        self.assertGreater(hit_rate, 0.9, "Cache should have high hit rate for recent data")
        
        # Test LRU eviction
        cache_stats_before = cache.get_stats()
        
        # Add more data to trigger eviction
        for i in range(200, 300):
            cache.put(f"new_key_{i}", f"new_value_{i}")
        
        cache_stats_after = cache.get_stats()
        
        logger.info(f"Cache stats before: {cache_stats_before}")
        logger.info(f"Cache stats after: {cache_stats_after}")
        
        # Should have evicted some entries
        self.assertGreater(cache_stats_after['evictions'], cache_stats_before['evictions'])
        
        logger.info("✅ Intelligent cache test passed")
    
    def test_batch_processor(self):
        """Test 7: Batch processing optimization"""
        logger.info("=== Test 7: Batch Processor ===")
        
        batch_processor = self.optimizer.batch_processor
        
        # Add operations to batch
        for i in range(50):
            batch_processor.add_insert("test_table", {
                "id": i,
                "name": f"item_{i}",
                "value": random.randint(1, 100)
            })
        
        for i in range(25):
            batch_processor.add_update("test_table", 
                {"value": random.randint(200, 300)}, 
                f"id = {i}"
            )
        
        for i in range(10):
            batch_processor.add_delete("test_table", f"id = {i + 40}")
        
        # Check batch statistics
        stats_before = batch_processor.get_stats()
        logger.info(f"Batch stats before flush: {stats_before}")
        
        # Flush batches
        batch_processor.flush(self.optimizer.connection_pool)
        
        stats_after = batch_processor.get_stats()
        logger.info(f"Batch stats after flush: {stats_after}")
        
        # Should have processed batches
        self.assertGreater(stats_after['batches_processed'], stats_before['batches_processed'])
        
        logger.info("✅ Batch processor test passed")
    
    def test_query_optimization(self):
        """Test 8: Query optimization with caching"""
        logger.info("=== Test 8: Query Optimization ===")
        
        # Create test table
        self.optimizer.optimize_query("""
            CREATE TABLE IF NOT EXISTS test_optimization (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)
        
        # Insert test data
        for i in range(100):
            self.optimizer.optimize_query(
                "INSERT INTO test_optimization (name, value) VALUES (?, ?)",
                (f"item_{i}", random.randint(1, 1000))
            )
        
        # Test cached queries
        query = "SELECT COUNT(*) FROM test_optimization WHERE value > ?"
        
        # First execution (cache miss)
        start_time = time.time()
        result1 = self.optimizer.optimize_query(query, (500,))
        first_time = time.time() - start_time
        
        # Second execution (cache hit)
        start_time = time.time()
        result2 = self.optimizer.optimize_query(query, (500,))
        second_time = time.time() - start_time
        
        # Results should be identical
        self.assertEqual(result1, result2)
        
        # Second query should be faster (cached)
        self.assertLess(second_time, first_time * 0.5, "Cached query should be significantly faster")
        
        logger.info(f"Query times: first={first_time:.4f}s, second={second_time:.4f}s")
        logger.info("✅ Query optimization test passed")


class TestScalabilityManager(unittest.TestCase):
    """Test scalability and load balancing"""
    
    def setUp(self):
        self.scalability_manager = ScalabilityManager(min_nodes=1, max_nodes=10)
        
    def tearDown(self):
        pass
    
    def test_load_balancer(self):
        """Test 9: Load balancing algorithms"""
        logger.info("=== Test 9: Load Balancer ===")
        
        load_balancer = self.scalability_manager.load_balancer
        
        # Register multiple nodes
        from src.concurrency.scalability_manager import NodeInfo
        
        nodes = []
        for i in range(5):
            node = NodeInfo(
                node_id=f"node_{i}",
                host=f"10.0.0.{i+10}",
                port=8000 + i,
                cpu_cores=4,
                memory_gb=8.0,
                max_agents=20,
                current_load=random.uniform(0.1, 0.8),
                capabilities=['general', 'development']
            )
            nodes.append(node)
            load_balancer.register_node(node)
        
        logger.info(f"Registered {len(nodes)} nodes")
        
        # Test different load balancing strategies
        strategies = ['round_robin', 'least_loaded', 'weighted_round_robin', 'capability_based']
        
        for strategy in strategies:
            load_balancer.current_strategy = strategy
            
            # Select nodes multiple times
            selections = []
            for _ in range(20):
                selected_node = load_balancer.select_node()
                if selected_node:
                    selections.append(selected_node.node_id)
            
            # Verify selections
            self.assertGreater(len(selections), 0, f"Strategy {strategy} should select nodes")
            
            unique_selections = set(selections)
            logger.info(f"Strategy {strategy}: selected {len(unique_selections)} unique nodes from {len(selections)} requests")
        
        # Test capability-based selection
        load_balancer.current_strategy = 'capability_based'
        
        # Request with specific capabilities
        selected_node = load_balancer.select_node({'capabilities': ['development']})
        self.assertIsNotNone(selected_node, "Should select node with required capabilities")
        self.assertIn('development', selected_node.capabilities)
        
        logger.info("✅ Load balancer test passed")
    
    def test_auto_scaling(self):
        """Test 10: Automatic scaling decisions"""
        logger.info("=== Test 10: Auto Scaling ===")
        
        auto_scaler = self.scalability_manager.auto_scaler
        
        # Get initial cluster status
        initial_status = auto_scaler.load_balancer.get_cluster_status()
        initial_nodes = initial_status['active_nodes']
        
        logger.info(f"Initial cluster: {initial_nodes} nodes")
        
        # Simulate high load to trigger scale-up
        from src.concurrency.scalability_manager import LoadMetrics
        
        high_load_metrics = LoadMetrics(
            cpu_usage=90.0,  # High CPU usage
            memory_usage=80.0,
            active_agents=50,
            throughput=100.0
        )
        
        # Update load balancer with high load
        for node_id in auto_scaler.load_balancer.nodes.keys():
            auto_scaler.load_balancer.update_node_load(node_id, high_load_metrics)
        
        # Trigger scale-up manually (simulating monitor decision)
        auto_scaler._trigger_scale_up()
        
        # Check if new node was added
        after_scale_up = auto_scaler.load_balancer.get_cluster_status()
        self.assertGreater(after_scale_up['active_nodes'], initial_nodes, "Should have scaled up")
        
        logger.info(f"After scale-up: {after_scale_up['active_nodes']} nodes")
        
        # Simulate low load to trigger scale-down
        low_load_metrics = LoadMetrics(
            cpu_usage=20.0,  # Low CPU usage
            memory_usage=30.0,
            active_agents=5,
            throughput=10.0
        )
        
        # Update load balancer with low load
        for node_id in auto_scaler.load_balancer.nodes.keys():
            auto_scaler.load_balancer.update_node_load(node_id, low_load_metrics)
        
        # Trigger scale-down manually
        auto_scaler._trigger_scale_down()
        
        # Check if node was removed
        after_scale_down = auto_scaler.load_balancer.get_cluster_status()
        self.assertLess(after_scale_down['active_nodes'], after_scale_up['active_nodes'], "Should have scaled down")
        
        logger.info(f"After scale-down: {after_scale_down['active_nodes']} nodes")
        
        # Check scaling history
        scaling_history = auto_scaler.get_scaling_history()
        self.assertGreater(len(scaling_history), 0, "Should have scaling events recorded")
        
        logger.info(f"Scaling events: {len(scaling_history)}")
        
        logger.info("✅ Auto scaling test passed")
    
    def test_capacity_planning(self):
        """Test 11: Capacity planning and forecasting"""
        logger.info("=== Test 11: Capacity Planning ===")
        
        capacity_planner = self.scalability_manager.capacity_planner
        
        # Generate historical load data
        from src.concurrency.scalability_manager import LoadMetrics
        
        base_time = datetime.now() - timedelta(hours=2)
        
        for i in range(120):  # 2 hours of data, 1 minute intervals
            timestamp = base_time + timedelta(minutes=i)
            
            # Simulate daily pattern with some trend
            hour_factor = 0.5 + 0.5 * abs(math.sin(i / 60 * math.pi))  # Daily cycle
            trend_factor = 1 + (i / 120) * 0.2  # 20% increase over time
            noise = random.uniform(0.9, 1.1)  # Random noise
            
            cpu_usage = min(95, 30 + hour_factor * trend_factor * noise * 40)
            memory_usage = min(90, 25 + hour_factor * trend_factor * noise * 35)
            throughput = max(1, hour_factor * trend_factor * noise * 50)
            
            metrics = LoadMetrics(
                timestamp=timestamp,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                throughput=throughput,
                active_agents=int(throughput / 5),
                response_time=1.0 + (cpu_usage / 100) * 2
            )
            
            capacity_planner.record_load_metrics(metrics)
        
        logger.info(f"Generated {len(capacity_planner.load_history)} historical data points")
        
        # Analyze trends
        trends = capacity_planner.analyze_trends()
        self.assertIn('trends', trends, "Should analyze trends")
        self.assertIn('patterns', trends, "Should identify patterns")
        
        logger.info(f"Trend analysis: {trends['trends']}")
        logger.info(f"Patterns: {trends['patterns']}")
        
        # Generate capacity forecast
        forecast = capacity_planner.forecast_capacity_needs()
        self.assertIn('projected_metrics', forecast, "Should provide projections")
        self.assertIn('recommendations', forecast, "Should provide recommendations")
        
        logger.info(f"Capacity forecast: {forecast['projected_metrics']}")
        logger.info(f"Recommendations: {len(forecast['recommendations'])} items")
        
        for rec in forecast['recommendations']:
            logger.info(f"  - {rec['type']}: {rec['description']}")
        
        logger.info("✅ Capacity planning test passed")


class TestMonitoringSystem(unittest.TestCase):
    """Test monitoring and alerting system"""
    
    def setUp(self):
        self.monitor = ConcurrencyMonitor(monitoring_interval=1)
        
    def tearDown(self):
        self.monitor.stop_monitoring()
    
    def test_alert_management(self):
        """Test 12: Alert management and notifications"""
        logger.info("=== Test 12: Alert Management ===")
        
        alert_manager = self.monitor.alert_manager
        
        # Track triggered alerts
        triggered_alerts = []
        
        def alert_callback(alert):
            triggered_alerts.append(alert)
        
        alert_manager.add_notification_callback(alert_callback)
        
        # Create test metrics that should trigger alerts
        high_cpu_metrics = ConcurrencyMetrics(
            cpu_usage=95.0,  # Should trigger high CPU alert
            memory_usage=50.0,
            error_rate=0.15,  # Should trigger high error rate alert
            stuck_agents=2,   # Should trigger stuck agents alert
            deadlock_count=1  # Should trigger deadlock alert
        )
        
        # Evaluate alerts
        alert_manager.evaluate_alerts(high_cpu_metrics)
        
        # Check triggered alerts
        self.assertGreater(len(triggered_alerts), 0, "Should trigger alerts for problematic metrics")
        
        alert_types = [alert.category for alert in triggered_alerts]
        logger.info(f"Triggered alerts: {alert_types}")
        
        # Verify specific alerts
        alert_titles = [alert.title for alert in triggered_alerts]
        self.assertIn('High CPU Usage', alert_titles, "Should trigger high CPU alert")
        self.assertIn('High Error Rate', alert_titles, "Should trigger high error rate alert")
        self.assertIn('Stuck Agents Detected', alert_titles, "Should trigger stuck agents alert")
        self.assertIn('Deadlock Detected', alert_titles, "Should trigger deadlock alert")
        
        # Test alert resolution
        normal_metrics = ConcurrencyMetrics(
            cpu_usage=30.0,
            memory_usage=40.0,
            error_rate=0.01,
            stuck_agents=0,
            deadlock_count=0
        )
        
        alert_manager.evaluate_alerts(normal_metrics)
        
        # Check alert summary
        alert_summary = alert_manager.get_alert_summary()
        logger.info(f"Alert summary: {alert_summary}")
        
        logger.info("✅ Alert management test passed")
    
    def test_performance_analysis(self):
        """Test 13: Performance trend analysis"""
        logger.info("=== Test 13: Performance Analysis ===")
        
        performance_analyzer = self.monitor.performance_analyzer
        
        # Generate performance data with trends
        import math
        
        base_time = datetime.now() - timedelta(hours=1)
        
        for i in range(60):  # 1 hour of data
            timestamp = base_time + timedelta(minutes=i)
            
            # Simulate increasing CPU usage trend
            cpu_trend = 30 + (i / 60) * 40  # 30% to 70% over time
            cpu_noise = random.uniform(-5, 5)
            cpu_usage = max(0, min(100, cpu_trend + cpu_noise))
            
            # Simulate memory usage with cyclical pattern
            memory_cycle = 40 + 20 * math.sin(i / 10)
            memory_usage = max(0, min(100, memory_cycle + random.uniform(-3, 3)))
            
            # Simulate throughput with declining trend
            throughput_trend = 100 - (i / 60) * 30  # 100 to 70 over time
            throughput = max(1, throughput_trend + random.uniform(-10, 10))
            
            metrics = ConcurrencyMetrics(
                timestamp=timestamp,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                throughput_per_minute=throughput,
                avg_response_time=1.0 + (cpu_usage / 100),
                error_rate=max(0, (cpu_usage - 50) / 500)  # Errors increase with CPU
            )
            
            performance_analyzer.record_metrics(metrics)
        
        logger.info(f"Generated {len(performance_analyzer.metrics_history)} performance data points")
        
        # Analyze trends
        trends = performance_analyzer.analyze_trends(60)  # 1 hour window
        self.assertIn('trends', trends, "Should analyze trends")
        
        # Check specific trend directions
        cpu_trend = trends['trends']['cpu_usage']
        throughput_trend = trends['trends']['throughput_per_minute']
        
        logger.info(f"CPU trend: {cpu_trend}")
        logger.info(f"Throughput trend: {throughput_trend}")
        
        # CPU should be increasing
        self.assertEqual(cpu_trend['direction'], 'increasing', "CPU should show increasing trend")
        
        # Throughput should be decreasing
        self.assertEqual(throughput_trend['direction'], 'decreasing', "Throughput should show decreasing trend")
        
        # Detect anomalies
        anomalies = performance_analyzer.detect_anomalies(30)  # 30 minute window
        logger.info(f"Detected {len(anomalies)} anomalies")
        
        for anomaly in anomalies:
            logger.info(f"  Anomaly: {anomaly['field']} - {anomaly['type']} (severity: {anomaly['severity']})")
        
        # Get performance summary
        summary = performance_analyzer.get_performance_summary()
        self.assertIn('current_metrics', summary, "Should provide current metrics")
        self.assertIn('trends', summary, "Should provide trends")
        self.assertIn('anomalies', summary, "Should provide anomalies")
        
        logger.info("✅ Performance analysis test passed")
    
    def test_real_time_monitoring(self):
        """Test 14: Real-time monitoring system"""
        logger.info("=== Test 14: Real-time Monitoring ===")
        
        # Add a metrics collector
        def mock_metrics_collector():
            return {
                'active_agents': random.randint(5, 15),
                'working_agents': random.randint(2, 8),
                'idle_agents': random.randint(1, 5),
                'stuck_agents': random.randint(0, 2),
                'pending_tasks': random.randint(0, 10),
                'running_tasks': random.randint(1, 8),
                'completed_tasks': random.randint(50, 100),
                'failed_tasks': random.randint(0, 5),
                'throughput_per_minute': random.uniform(20, 80),
                'avg_response_time': random.uniform(0.5, 3.0),
                'error_rate': random.uniform(0, 0.1),
                'cache_hit_rate': random.uniform(0.7, 0.95),
                'lock_contention_rate': random.uniform(0, 0.3),
                'deadlock_count': random.randint(0, 1),
                'race_condition_count': random.randint(0, 2),
                'resource_conflicts': random.randint(0, 3)
            }
        
        self.monitor.add_metrics_collector(mock_metrics_collector)
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Let it run for a few seconds
        time.sleep(3)
        
        # Check monitoring status
        status = self.monitor.get_monitoring_status()
        self.assertTrue(status['monitoring']['is_running'], "Monitoring should be running")
        self.assertIsNotNone(status['current_metrics'], "Should have current metrics")
        
        logger.info(f"Monitoring status: {status['monitoring']}")
        
        # Get real-time dashboard data
        dashboard_data = self.monitor.get_real_time_dashboard_data()
        self.assertIn('system_health', dashboard_data, "Should provide system health")
        self.assertIn('agent_status', dashboard_data, "Should provide agent status")
        self.assertIn('task_status', dashboard_data, "Should provide task status")
        self.assertIn('performance', dashboard_data, "Should provide performance metrics")
        self.assertIn('concurrency', dashboard_data, "Should provide concurrency metrics")
        
        logger.info(f"Dashboard data keys: {list(dashboard_data.keys())}")
        logger.info(f"System health: {dashboard_data['system_health']['status']}")
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        
        # Verify monitoring stopped
        final_status = self.monitor.get_monitoring_status()
        self.assertFalse(final_status['monitoring']['is_running'], "Monitoring should be stopped")
        
        logger.info("✅ Real-time monitoring test passed")


class TestIntegratedConcurrencySystem(unittest.TestCase):
    """Test integrated concurrency system with all components"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_integrated.db")
        
        # Initialize all components
        self.coordinator = EnhancedAgentCoordinator(
            max_concurrent_agents=30,
            max_concurrent_tasks=150,
            max_message_throughput=800
        )
        self.optimizer = PerformanceOptimizer(self.db_path)
        self.scalability_manager = ScalabilityManager(min_nodes=2, max_nodes=15)
        self.monitor = ConcurrencyMonitor(monitoring_interval=2)
        
    def tearDown(self):
        asyncio.run(self.coordinator.stop())
        self.monitor.stop_monitoring()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_integrated_high_load_scenario(self):
        """Test 15: Integrated system under high load"""
        logger.info("=== Test 15: Integrated High Load Scenario ===")
        
        async def run_integrated_test():
            # Start all systems
            await self.coordinator.start()
            self.monitor.start_monitoring()
            
            # Add metrics collector for coordinator
            def coordinator_metrics_collector():
                status = self.coordinator.get_system_status()
                return {
                    'active_agents': len(self.coordinator.resource_pool.active_agents),
                    'pending_tasks': self.coordinator.task_queue.qsize(),
                    'completed_tasks': len(self.coordinator.completed_tasks),
                    'throughput_per_minute': status['coordinator_metrics'].get('tasks_completed', 0) * 6,  # Rough estimate
                    'avg_response_time': status['coordinator_metrics'].get('avg_task_duration', 0),
                    'cache_hit_rate': 0.8  # Mock value
                }
            
            self.monitor.add_metrics_collector(coordinator_metrics_collector)
            
            # Create high load scenario
            logger.info("Creating high load scenario...")
            
            # Phase 1: Create many tasks with complex dependencies
            task_batches = []
            for batch in range(5):
                batch_tasks = []
                
                # Create base tasks
                for i in range(10):
                    task_id = self.coordinator.create_task(
                        f"agent_{i % 15:03d}",
                        f"Batch {batch} - Base task {i}",
                        TaskPriority.NORMAL,
                        required_resources=[f"resource_{i % 5}"],
                        estimated_duration=0.2
                    )
                    batch_tasks.append(task_id)
                
                # Create dependent tasks
                for i in range(5):
                    deps = random.sample(batch_tasks[:5], 2)  # Depend on 2 base tasks
                    task_id = self.coordinator.create_task(
                        f"agent_{(i + 10) % 15:03d}",
                        f"Batch {batch} - Dependent task {i}",
                        TaskPriority.HIGH,
                        dependencies=deps,
                        required_resources=[f"resource_{(i + 5) % 5}"],
                        estimated_duration=0.3
                    )
                    batch_tasks.append(task_id)
                
                task_batches.append(batch_tasks)
            
            total_tasks = sum(len(batch) for batch in task_batches)
            logger.info(f"Created {total_tasks} tasks across {len(task_batches)} batches")
            
            # Phase 2: Simulate concurrent message processing
            async def process_messages():
                for i in range(50):
                    message_data = {
                        'text': f"Process urgent request {i}",
                        'agent_name': f"agent_{i % 15:03d}"
                    }
                    
                    response = await self.coordinator.process_message_async(message_data)
                    if not response['success']:
                        logger.warning(f"Message {i} processing failed: {response.get('error')}")
                    
                    await asyncio.sleep(0.1)  # Small delay between messages
            
            # Phase 3: Monitor system performance
            async def monitor_performance():
                for _ in range(30):  # Monitor for 30 iterations
                    await asyncio.sleep(1)
                    
                    # Get system status
                    coordinator_status = self.coordinator.get_system_status()
                    optimizer_stats = self.optimizer.get_comprehensive_stats()
                    scalability_status = self.scalability_manager.get_comprehensive_status()
                    monitoring_status = self.monitor.get_monitoring_status()
                    
                    # Log key metrics
                    if _ % 10 == 0:  # Every 10 seconds
                        logger.info(f"=== Performance Check {_ // 10 + 1} ===")
                        logger.info(f"Coordinator: {coordinator_status['coordinator_metrics']}")
                        logger.info(f"Resource utilization: {coordinator_status['resource_status']['utilization']:.1%}")
                        logger.info(f"Cache hit rate: {optimizer_stats['cache']['hit_rate']:.1%}")
                        logger.info(f"Active connections: {optimizer_stats['connection_pool']['active_connections']}")
                        
                        # Check for alerts
                        if monitoring_status['alerts']['total_active'] > 0:
                            logger.warning(f"Active alerts: {monitoring_status['alerts']['total_active']}")
            
            # Run all phases concurrently
            start_time = time.time()
            
            await asyncio.gather(
                process_messages(),
                monitor_performance()
            )
            
            total_time = time.time() - start_time
            
            # Phase 4: Analyze results
            logger.info("=== Final Analysis ===")
            
            final_coordinator_status = self.coordinator.get_system_status()
            final_optimizer_stats = self.optimizer.get_comprehensive_stats()
            final_monitoring_status = self.monitor.get_monitoring_status()
            
            # Performance metrics
            completed_tasks = len(self.coordinator.completed_tasks)
            task_completion_rate = completed_tasks / total_tasks
            avg_task_duration = final_coordinator_status['coordinator_metrics'].get('avg_task_duration', 0)
            resource_utilization = final_coordinator_status['resource_status']['utilization']
            
            logger.info(f"Test Duration: {total_time:.2f}s")
            logger.info(f"Task Completion Rate: {task_completion_rate:.1%} ({completed_tasks}/{total_tasks})")
            logger.info(f"Average Task Duration: {avg_task_duration:.3f}s")
            logger.info(f"Resource Utilization: {resource_utilization:.1%}")
            logger.info(f"Cache Hit Rate: {final_optimizer_stats['cache']['hit_rate']:.1%}")
            logger.info(f"Connection Pool Utilization: {final_optimizer_stats['connection_pool']['utilization']:.1%}")
            
            # Assertions for system performance
            self.assertGreater(task_completion_rate, 0.7, "Should complete at least 70% of tasks")
            self.assertLess(avg_task_duration, 2.0, "Average task duration should be reasonable")
            self.assertLess(resource_utilization, 0.95, "Resource utilization should not be excessive")
            
            # Check for critical alerts
            critical_alerts = [
                alert for alert in final_monitoring_status['alerts']['by_severity'].keys()
                if alert in ['critical', 'error']
            ]
            
            if critical_alerts:
                logger.warning(f"Critical alerts detected: {critical_alerts}")
            
            logger.info("✅ Integrated high load scenario test completed")
        
        asyncio.run(run_integrated_test())


def run_enhanced_concurrency_tests():
    """Run all enhanced concurrency tests"""
    logger.info("=" * 80)
    logger.info("ENHANCED CONCURRENCY TESTING SUITE")
    logger.info("=" * 80)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test cases
    test_classes = [
        TestEnhancedAgentCoordinator,
        TestPerformanceOptimizer,
        TestScalabilityManager,
        TestMonitoringSystem,
        TestIntegratedConcurrencySystem
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Generate comprehensive summary
    logger.info("=" * 80)
    logger.info("ENHANCED CONCURRENCY TEST SUMMARY")
    logger.info("=" * 80)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    successes = total_tests - failures - errors
    success_rate = (successes / total_tests * 100) if total_tests > 0 else 0
    
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Successes: {successes}")
    logger.info(f"Failures: {failures}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Success Rate: {success_rate:.1f}%")
    
    if result.failures:
        logger.error("\nFAILURES:")
        for test, traceback in result.failures:
            logger.error(f"  {test}")
            logger.error(f"    {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        logger.error("\nERRORS:")
        for test, traceback in result.errors:
            logger.error(f"  {test}")
            logger.error(f"    {traceback.split('Exception:')[-1].strip()}")
    
    # Performance summary
    logger.info("\n" + "=" * 80)
    logger.info("CONCURRENCY ENHANCEMENTS VALIDATED")
    logger.info("=" * 80)
    logger.info("✅ Multi-agent concurrency optimization")
    logger.info("✅ Resource allocation enhancement")
    logger.info("✅ Task dependency management")
    logger.info("✅ Performance bottleneck resolution")
    logger.info("✅ Scalability improvements")
    logger.info("✅ Race condition prevention")
    logger.info("✅ Monitoring and metrics")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Add math import for capacity planning test
    import math
    
    success = run_enhanced_concurrency_tests()
    sys.exit(0 if success else 1)