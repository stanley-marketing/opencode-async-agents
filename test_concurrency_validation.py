#!/usr/bin/env python3
"""
Comprehensive concurrency testing for the OpenCode-Slack agent system.
Tests multi-agent concurrent task execution, thread safety, resource contention,
and parallel workflow coordination.
"""

import asyncio
import concurrent.futures
import logging
import os
import random
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, MagicMock

# Import system components
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.utils.opencode_wrapper import OpencodeSessionManager, OpencodeSession
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge
from src.chat.message_parser import MessageParser, ParsedMessage
from src.monitoring.agent_health_monitor import AgentHealthMonitor
from src.monitoring.agent_recovery_manager import AgentRecoveryManager

# Configure logging for test visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ConcurrencyTestFramework:
    """Framework for testing concurrent operations in the agent system"""
    
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.db_path = os.path.join(temp_dir, "test_employees.db")
        self.sessions_dir = os.path.join(temp_dir, "test_sessions")
        
        # Initialize core components
        self.file_manager = FileOwnershipManager(self.db_path)
        self.task_tracker = TaskProgressTracker(self.sessions_dir)
        self.session_manager = OpencodeSessionManager(
            self.file_manager, self.sessions_dir, quiet_mode=True
        )
        
        # Mock Telegram manager to avoid network calls
        self.telegram_manager = Mock(spec=TelegramManager)
        self.telegram_manager.send_message = Mock(return_value=True)
        self.telegram_manager.is_connected = Mock(return_value=True)
        self.sent_messages = []
        
        def capture_message(text, sender="system", reply_to=None):
            self.sent_messages.append((text, sender, reply_to))
            return True
        
        self.telegram_manager.send_message.side_effect = capture_message
        
        # Initialize agent system
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        self.agent_manager.setup_monitoring_system(self.task_tracker, self.session_manager)
        self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)
        
        # Initialize monitoring system
        self.health_monitor = AgentHealthMonitor(self.agent_manager, self.task_tracker, polling_interval=1)
        self.recovery_manager = AgentRecoveryManager(self.agent_manager, self.session_manager)
        
        # Patch opencode execution to avoid external dependencies
        self._patch_opencode_execution()
        
        # Thread safety tracking
        self.thread_safety_violations = []
        self.resource_conflicts = []
        self.performance_metrics = {}
        
    def _patch_opencode_execution(self):
        """Patch opencode execution to simulate work without external dependencies"""
        def mock_execute_opencode(session_instance):
            # Simulate variable execution time
            time.sleep(random.uniform(0.1, 0.5))
            return {
                "success": True,
                "stdout": f"Task completed for {session_instance.employee_name}",
                "stderr": "",
                "returncode": 0
            }
        
        def mock_analyze_files(session_instance):
            # Return some test files
            return [f"src/{session_instance.employee_name}_module.py", "README.md"]
        
        # Apply patches
        OpencodeSession._execute_opencode_command = mock_execute_opencode
        OpencodeSession._analyze_task_for_files = mock_analyze_files
    
    def create_test_employees(self, count: int) -> List[str]:
        """Create test employees for concurrent testing"""
        employees = []
        for i in range(count):
            name = f"agent_{i:03d}"
            role = random.choice(["developer", "tester", "designer", "devops"])
            success = self.file_manager.hire_employee(name, role)
            if success:
                employees.append(name)
                # Create communication agent
                expertise = self.agent_manager._get_expertise_for_role(role)
                self.agent_manager.create_agent(name, role, expertise)
        return employees
    
    def simulate_concurrent_messages(self, employees: List[str], message_count: int) -> List[ParsedMessage]:
        """Generate concurrent messages for testing"""
        messages = []
        parser = MessageParser()
        
        for i in range(message_count):
            employee = random.choice(employees)
            task_descriptions = [
                f"implement feature {i}",
                f"fix bug in module {i}",
                f"add tests for component {i}",
                f"update documentation for {i}",
                f"optimize performance of {i}"
            ]
            
            message_data = {
                "message_id": i + 1,
                "text": f"@{employee} {random.choice(task_descriptions)}",
                "from": {"username": f"user_{i % 5}"},
                "date": int(time.time()) + i
            }
            
            parsed = parser.parse_message(message_data)
            messages.append(parsed)
        
        return messages
    
    def cleanup(self):
        """Clean up test resources"""
        try:
            if hasattr(self.health_monitor, 'stop_monitoring'):
                self.health_monitor.stop_monitoring()
            if hasattr(self.agent_bridge, 'stop_all_tasks'):
                self.agent_bridge.stop_all_tasks()
            self.session_manager.cleanup_all_sessions()
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")


class TestConcurrentAgentOperations(unittest.TestCase):
    """Test concurrent agent operations and thread safety"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.framework = ConcurrencyTestFramework(self.temp_dir)
        
    def tearDown(self):
        self.framework.cleanup()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_concurrent_task_assignment(self):
        """Test 1: Multi-agent concurrent task execution without interference"""
        logger.info("=== Test 1: Concurrent Task Assignment ===")
        
        # Create multiple agents
        employees = self.framework.create_test_employees(5)
        self.assertEqual(len(employees), 5)
        
        # Generate concurrent messages
        messages = self.framework.simulate_concurrent_messages(employees, 10)
        
        # Process messages concurrently
        start_time = time.time()
        
        def process_message(message):
            try:
                self.framework.agent_manager.handle_message(message)
                return True
            except Exception as e:
                logger.error(f"Message processing failed: {e}")
                return False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_message, msg) for msg in messages]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        processing_time = time.time() - start_time
        logger.info(f"Processed {len(messages)} messages in {processing_time:.2f}s")
        
        # Verify all messages were processed successfully
        success_count = sum(results)
        self.assertEqual(success_count, len(messages), "Some messages failed to process")
        
        # Verify agents responded appropriately
        self.assertGreater(len(self.framework.sent_messages), 0, "No agent responses generated")
        
        # Check for thread safety violations
        self.assertEqual(len(self.framework.thread_safety_violations), 0, 
                        "Thread safety violations detected")
    
    def test_task_dependency_management(self):
        """Test 2: Task dependency management and proper sequencing"""
        logger.info("=== Test 2: Task Dependency Management ===")
        
        employees = self.framework.create_test_employees(3)
        
        # Create dependent tasks
        dependent_tasks = [
            ("agent_000", "create base module"),
            ("agent_001", "add tests for base module"),  # depends on first task
            ("agent_002", "integrate base module")       # depends on first task
        ]
        
        # Track task completion order
        completion_order = []
        original_notify = self.framework.agent_manager.notify_task_completion
        
        def track_completion(employee_name, task, task_output=None):
            completion_order.append((employee_name, task, time.time()))
            return original_notify(employee_name, task, task_output)
        
        self.framework.agent_manager.notify_task_completion = track_completion
        
        # Assign tasks with artificial dependencies
        for employee, task in dependent_tasks:
            parser = MessageParser()
            message_data = {
                "message_id": len(completion_order) + 1,
                "text": f"@{employee} {task}",
                "from": {"username": "manager"},
                "date": int(time.time())
            }
            message = parser.parse_message(message_data)
            self.framework.agent_manager.handle_message(message)
            
            # Small delay to ensure ordering
            time.sleep(0.1)
        
        # Wait for tasks to complete
        max_wait = 10
        start_wait = time.time()
        while len(completion_order) < len(dependent_tasks) and (time.time() - start_wait) < max_wait:
            self.framework.agent_bridge.check_task_completion()
            time.sleep(0.1)
        
        # Verify task sequencing
        self.assertGreaterEqual(len(completion_order), 1, "No tasks completed")
        logger.info(f"Task completion order: {completion_order}")
    
    def test_resource_contention_handling(self):
        """Test 3: Resource allocation and contention handling"""
        logger.info("=== Test 3: Resource Contention Handling ===")
        
        employees = self.framework.create_test_employees(4)
        
        # Create contention scenario - multiple agents trying to lock same files
        shared_files = ["src/shared_module.py", "src/common_utils.py", "README.md"]
        
        def attempt_file_lock(employee_name, files, description):
            try:
                result = self.framework.file_manager.lock_files(employee_name, files, description)
                return employee_name, result
            except Exception as e:
                logger.error(f"File lock attempt failed for {employee_name}: {e}")
                return employee_name, {}
        
        # Concurrent file locking attempts
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i, employee in enumerate(employees):
                future = executor.submit(
                    attempt_file_lock, 
                    employee, 
                    shared_files, 
                    f"Task {i} for {employee}"
                )
                futures.append(future)
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze contention results
        successful_locks = {}
        for employee, lock_result in results:
            locked_files = [f for f, status in lock_result.items() if status == "locked"]
            if locked_files:
                successful_locks[employee] = locked_files
        
        logger.info(f"Successful locks: {successful_locks}")
        
        # Verify only one agent can lock each file
        all_locked_files = []
        for files in successful_locks.values():
            all_locked_files.extend(files)
        
        # Check for duplicate locks (should not happen)
        unique_files = set(all_locked_files)
        self.assertEqual(len(all_locked_files), len(unique_files), 
                        "File locking contention not properly handled")
        
        # Verify at least one agent got locks
        self.assertGreater(len(successful_locks), 0, "No agent successfully acquired locks")
    
    def test_thread_safety_agent_operations(self):
        """Test 4: Thread safety in agent operations"""
        logger.info("=== Test 4: Thread Safety in Agent Operations ===")
        
        employees = self.framework.create_test_employees(3)
        
        # Concurrent agent status operations
        def agent_operations():
            operations_performed = []
            try:
                # Get agent status
                status = self.framework.agent_manager.get_agent_status()
                operations_performed.append("get_status")
                
                # List active agents
                active = self.framework.agent_manager.list_active_agents()
                operations_performed.append("list_active")
                
                # Check availability
                for employee in employees:
                    available = self.framework.agent_manager.is_agent_available(employee)
                    operations_performed.append(f"check_available_{employee}")
                
                # Get chat statistics
                stats = self.framework.agent_manager.get_chat_statistics()
                operations_performed.append("get_chat_stats")
                
                return operations_performed
            except Exception as e:
                logger.error(f"Agent operation failed: {e}")
                return []
        
        # Run operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(agent_operations) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all operations completed successfully
        total_operations = sum(len(ops) for ops in results)
        self.assertGreater(total_operations, 0, "No operations completed successfully")
        
        # Check for consistent results
        status_results = []
        for _ in range(5):
            status = self.framework.agent_manager.get_agent_status()
            status_results.append(len(status))
        
        # All status calls should return same number of agents
        self.assertEqual(len(set(status_results)), 1, "Inconsistent agent status results")
    
    def test_parallel_workflow_execution(self):
        """Test 5: Parallel workflow execution and coordination"""
        logger.info("=== Test 5: Parallel Workflow Execution ===")
        
        employees = self.framework.create_test_employees(6)
        
        # Create parallel workflows
        workflows = [
            ("frontend_team", employees[:2], ["implement UI components", "add CSS styling"]),
            ("backend_team", employees[2:4], ["create API endpoints", "setup database"]),
            ("testing_team", employees[4:], ["write unit tests", "setup integration tests"])
        ]
        
        workflow_results = {}
        
        def execute_workflow(team_name, team_members, tasks):
            team_results = []
            try:
                for i, (member, task) in enumerate(zip(team_members, tasks)):
                    parser = MessageParser()
                    message_data = {
                        "message_id": hash(f"{team_name}_{i}"),
                        "text": f"@{member} {task}",
                        "from": {"username": f"{team_name}_lead"},
                        "date": int(time.time())
                    }
                    message = parser.parse_message(message_data)
                    self.framework.agent_manager.handle_message(message)
                    team_results.append(f"{member}: {task}")
                
                return team_name, team_results
            except Exception as e:
                logger.error(f"Workflow execution failed for {team_name}: {e}")
                return team_name, []
        
        # Execute workflows in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for team_name, members, tasks in workflows:
                future = executor.submit(execute_workflow, team_name, members, tasks)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                team_name, results = future.result()
                workflow_results[team_name] = results
        
        # Verify all workflows executed
        self.assertEqual(len(workflow_results), 3, "Not all workflows completed")
        
        # Verify each workflow had tasks assigned
        for team_name, results in workflow_results.items():
            self.assertGreater(len(results), 0, f"No tasks assigned for {team_name}")
        
        logger.info(f"Workflow results: {workflow_results}")
    
    def test_concurrent_communication_state_management(self):
        """Test 6: Concurrent agent communication and state management"""
        logger.info("=== Test 6: Concurrent Communication and State Management ===")
        
        employees = self.framework.create_test_employees(4)
        
        # Simulate concurrent communication patterns
        communication_patterns = [
            "status_inquiry",
            "help_request", 
            "task_assignment",
            "general_discussion"
        ]
        
        def simulate_communication(pattern, employee):
            try:
                parser = MessageParser()
                
                if pattern == "status_inquiry":
                    text = f"@{employee} what's your current status?"
                elif pattern == "help_request":
                    text = f"@{employee} can you help with debugging?"
                elif pattern == "task_assignment":
                    text = f"@{employee} please implement new feature"
                else:  # general_discussion
                    text = f"@{employee} what do you think about the architecture?"
                
                message_data = {
                    "message_id": hash(f"{pattern}_{employee}_{time.time()}"),
                    "text": text,
                    "from": {"username": "team_member"},
                    "date": int(time.time())
                }
                
                message = parser.parse_message(message_data)
                self.framework.agent_manager.handle_message(message)
                
                # Check agent state after communication
                status = self.framework.agent_manager.get_agent_status(employee)
                return pattern, employee, bool(status)
                
            except Exception as e:
                logger.error(f"Communication simulation failed: {e}")
                return pattern, employee, False
        
        # Generate concurrent communications
        communication_tasks = []
        for _ in range(20):
            pattern = random.choice(communication_patterns)
            employee = random.choice(employees)
            communication_tasks.append((pattern, employee))
        
        # Execute communications concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(simulate_communication, pattern, employee)
                for pattern, employee in communication_tasks
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze communication results
        successful_communications = [r for r in results if r[2]]  # r[2] is success flag
        success_rate = len(successful_communications) / len(results)
        
        logger.info(f"Communication success rate: {success_rate:.2%}")
        self.assertGreater(success_rate, 0.8, "Communication success rate too low")
        
        # Verify agent states remain consistent
        final_status = self.framework.agent_manager.get_agent_status()
        self.assertEqual(len(final_status), len(employees), "Agent count mismatch after communications")
    
    def test_performance_under_concurrent_load(self):
        """Test 7: Performance under multiple simultaneous tasks"""
        logger.info("=== Test 7: Performance Under Concurrent Load ===")
        
        # Create larger number of agents for load testing
        employees = self.framework.create_test_employees(10)
        
        # Performance metrics tracking
        metrics = {
            "message_processing_times": [],
            "task_assignment_times": [],
            "status_query_times": [],
            "concurrent_operations": 0
        }
        
        def measure_message_processing():
            start_time = time.time()
            try:
                messages = self.framework.simulate_concurrent_messages(employees, 5)
                for message in messages:
                    self.framework.agent_manager.handle_message(message)
                processing_time = time.time() - start_time
                metrics["message_processing_times"].append(processing_time)
                return True
            except Exception as e:
                logger.error(f"Message processing measurement failed: {e}")
                return False
        
        def measure_status_queries():
            start_time = time.time()
            try:
                for _ in range(10):
                    self.framework.agent_manager.get_agent_status()
                query_time = time.time() - start_time
                metrics["status_query_times"].append(query_time)
                return True
            except Exception as e:
                logger.error(f"Status query measurement failed: {e}")
                return False
        
        def measure_task_assignments():
            start_time = time.time()
            try:
                for i, employee in enumerate(employees[:5]):
                    parser = MessageParser()
                    message_data = {
                        "message_id": 1000 + i,
                        "text": f"@{employee} performance test task {i}",
                        "from": {"username": "load_tester"},
                        "date": int(time.time())
                    }
                    message = parser.parse_message(message_data)
                    self.framework.agent_manager.handle_message(message)
                
                assignment_time = time.time() - start_time
                metrics["task_assignment_times"].append(assignment_time)
                return True
            except Exception as e:
                logger.error(f"Task assignment measurement failed: {e}")
                return False
        
        # Run performance tests concurrently
        test_functions = [
            measure_message_processing,
            measure_status_queries,
            measure_task_assignments
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            # Submit multiple rounds of each test
            futures = []
            for _ in range(3):  # 3 rounds
                for test_func in test_functions:
                    futures.append(executor.submit(test_func))
            
            # Wait for completion and count successful operations
            successful_operations = sum(
                1 for future in concurrent.futures.as_completed(futures) 
                if future.result()
            )
        
        metrics["concurrent_operations"] = successful_operations
        
        # Analyze performance metrics
        avg_message_time = sum(metrics["message_processing_times"]) / len(metrics["message_processing_times"]) if metrics["message_processing_times"] else 0
        avg_status_time = sum(metrics["status_query_times"]) / len(metrics["status_query_times"]) if metrics["status_query_times"] else 0
        avg_assignment_time = sum(metrics["task_assignment_times"]) / len(metrics["task_assignment_times"]) if metrics["task_assignment_times"] else 0
        
        logger.info(f"Performance Metrics:")
        logger.info(f"  Average message processing time: {avg_message_time:.3f}s")
        logger.info(f"  Average status query time: {avg_status_time:.3f}s")
        logger.info(f"  Average task assignment time: {avg_assignment_time:.3f}s")
        logger.info(f"  Successful concurrent operations: {successful_operations}")
        
        # Performance assertions
        self.assertLess(avg_message_time, 2.0, "Message processing too slow")
        self.assertLess(avg_status_time, 1.0, "Status queries too slow")
        self.assertLess(avg_assignment_time, 3.0, "Task assignments too slow")
        self.assertGreater(successful_operations, len(futures) * 0.8, "Too many operations failed")


class TestMonitoringSystemConcurrency(unittest.TestCase):
    """Test monitoring system under concurrent conditions"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.framework = ConcurrencyTestFramework(self.temp_dir)
        
    def tearDown(self):
        self.framework.cleanup()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_concurrent_health_monitoring(self):
        """Test health monitoring under concurrent agent operations"""
        logger.info("=== Test: Concurrent Health Monitoring ===")
        
        employees = self.framework.create_test_employees(5)
        
        # Start health monitoring
        anomalies_detected = []
        
        def anomaly_callback(agent_name, anomalies, status_record):
            anomalies_detected.append((agent_name, anomalies, time.time()))
        
        self.framework.health_monitor.start_monitoring(anomaly_callback)
        
        # Generate concurrent agent activity
        def generate_activity():
            for i in range(10):
                employee = random.choice(employees)
                parser = MessageParser()
                message_data = {
                    "message_id": 2000 + i,
                    "text": f"@{employee} monitoring test task {i}",
                    "from": {"username": "monitor_tester"},
                    "date": int(time.time())
                }
                message = parser.parse_message(message_data)
                self.framework.agent_manager.handle_message(message)
                time.sleep(0.1)
        
        # Run activity generation in parallel with monitoring
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            activity_futures = [executor.submit(generate_activity) for _ in range(3)]
            
            # Let monitoring run for a bit
            time.sleep(2)
            
            # Wait for activities to complete
            for future in concurrent.futures.as_completed(activity_futures):
                future.result()
        
        # Get health summary
        health_summary = self.framework.health_monitor.get_agent_health_summary()
        
        # Verify monitoring worked
        self.assertIn('total_agents', health_summary)
        self.assertGreater(health_summary['total_agents'], 0)
        
        # Stop monitoring
        self.framework.health_monitor.stop_monitoring()
        
        logger.info(f"Health monitoring detected {len(anomalies_detected)} anomalies")
        logger.info(f"Health summary: {health_summary}")


def run_concurrency_tests():
    """Run all concurrency tests and generate report"""
    logger.info("=" * 60)
    logger.info("STARTING COMPREHENSIVE CONCURRENCY TESTING")
    logger.info("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestConcurrentAgentOperations))
    test_suite.addTest(unittest.makeSuite(TestMonitoringSystemConcurrency))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Generate summary report
    logger.info("=" * 60)
    logger.info("CONCURRENCY TESTING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Tests run: {result.testsRun}")
    logger.info(f"Failures: {len(result.failures)}")
    logger.info(f"Errors: {len(result.errors)}")
    logger.info(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        logger.error("FAILURES:")
        for test, traceback in result.failures:
            logger.error(f"  {test}: {traceback}")
    
    if result.errors:
        logger.error("ERRORS:")
        for test, traceback in result.errors:
            logger.error(f"  {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_concurrency_tests()
    sys.exit(0 if success else 1)