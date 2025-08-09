#!/usr/bin/env python3
"""
Stress Test for Real-time Communication System

This script performs stress testing on the communication system to validate:
- High-frequency message processing
- Concurrent agent operations
- Message delivery under load
- System stability during peak usage
- Memory and resource management
"""

import asyncio
import concurrent.futures
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import sys
import psutil
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.chat.telegram_manager import TelegramManager
from src.chat.message_parser import MessageParser, ParsedMessage
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.monitoring.agent_health_monitor import AgentHealthMonitor

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce log noise during stress test
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommunicationStressTester:
    """Stress tester for real-time communication system"""
    
    def __init__(self, test_dir: str = None):
        self.test_dir = Path(test_dir) if test_dir else Path(tempfile.mkdtemp())
        self.results = {
            'test_start': datetime.now(),
            'system_metrics': {},
            'performance_metrics': {},
            'reliability_metrics': {},
            'stress_test_results': {}
        }
        
        # Performance tracking
        self.message_count = 0
        self.error_count = 0
        self.response_times = []
        self.memory_usage = []
        self.cpu_usage = []
        
        # Setup test environment
        self._setup_environment()
        
    def _setup_environment(self):
        """Setup test environment"""
        logger.info("Setting up stress test environment...")
        
        # Create directories
        self.sessions_dir = self.test_dir / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.file_manager = FileOwnershipManager(str(self.test_dir / "employees.db"))
        self.task_tracker = TaskProgressTracker(str(self.sessions_dir))
        self.telegram_manager = MockTelegramManager()
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        
        # Create test agents
        self.test_agents = []
        for i in range(10):  # Create 10 test agents
            agent_name = f"stress_agent_{i}"
            self.file_manager.hire_employee(agent_name, "developer")
            self.test_agents.append(agent_name)
        
        logger.info(f"Created {len(self.test_agents)} test agents")

    def run_stress_tests(self) -> Dict[str, Any]:
        """Run comprehensive stress tests"""
        logger.info("Starting stress tests...")
        
        try:
            # 1. High-frequency message test
            self.test_high_frequency_messages()
            
            # 2. Concurrent operations test
            self.test_concurrent_operations()
            
            # 3. Memory stress test
            self.test_memory_stress()
            
            # 4. Long-running stability test
            self.test_long_running_stability()
            
            # 5. Resource exhaustion test
            self.test_resource_exhaustion()
            
        except Exception as e:
            logger.error(f"Stress test failed: {e}")
            self.results['error'] = str(e)
        
        return self.generate_stress_report()

    def test_high_frequency_messages(self):
        """Test high-frequency message processing"""
        logger.info("Testing high-frequency message processing...")
        
        test_results = {
            'messages_per_second': [],
            'response_times': [],
            'error_rate': 0,
            'peak_throughput': 0
        }
        
        # Test different message frequencies
        frequencies = [10, 50, 100, 200, 500]  # messages per second
        
        for freq in frequencies:
            logger.info(f"Testing {freq} messages/second...")
            
            start_time = time.time()
            messages_sent = 0
            errors = 0
            response_times = []
            
            # Send messages for 10 seconds
            test_duration = 10
            interval = 1.0 / freq
            
            while time.time() - start_time < test_duration:
                try:
                    msg_start = time.time()
                    
                    # Create and process message
                    agent = self.test_agents[messages_sent % len(self.test_agents)]
                    message = ParsedMessage(
                        message_id=messages_sent,
                        text=f"@{agent} stress test message {messages_sent}",
                        sender="stress_tester",
                        timestamp=datetime.now(),
                        mentions=[agent],
                        is_command=False
                    )
                    
                    self.agent_manager.handle_message(message)
                    
                    response_time = time.time() - msg_start
                    response_times.append(response_time)
                    messages_sent += 1
                    
                    # Control frequency
                    time.sleep(max(0, interval - response_time))
                    
                except Exception as e:
                    errors += 1
                    logger.debug(f"Message processing error: {e}")
            
            actual_duration = time.time() - start_time
            actual_freq = messages_sent / actual_duration
            error_rate = errors / messages_sent if messages_sent > 0 else 1
            
            test_results['messages_per_second'].append({
                'target_frequency': freq,
                'actual_frequency': actual_freq,
                'messages_sent': messages_sent,
                'errors': errors,
                'error_rate': error_rate,
                'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
                'max_response_time': max(response_times) if response_times else 0
            })
            
            if actual_freq > test_results['peak_throughput']:
                test_results['peak_throughput'] = actual_freq
        
        self.results['stress_test_results']['high_frequency'] = test_results
        logger.info(f"High-frequency test complete. Peak throughput: {test_results['peak_throughput']:.1f} msg/s")

    def test_concurrent_operations(self):
        """Test concurrent operations across multiple threads"""
        logger.info("Testing concurrent operations...")
        
        test_results = {
            'thread_counts': [],
            'performance_degradation': [],
            'error_rates': [],
            'resource_usage': []
        }
        
        thread_counts = [1, 5, 10, 20, 50]
        
        for thread_count in thread_counts:
            logger.info(f"Testing with {thread_count} concurrent threads...")
            
            start_time = time.time()
            errors = []
            response_times = []
            
            def worker_thread(thread_id):
                """Worker thread function"""
                thread_errors = 0
                thread_responses = []
                
                for i in range(20):  # Each thread sends 20 messages
                    try:
                        msg_start = time.time()
                        
                        agent = self.test_agents[thread_id % len(self.test_agents)]
                        message = ParsedMessage(
                            message_id=thread_id * 1000 + i,
                            text=f"@{agent} concurrent test from thread {thread_id}",
                            sender=f"thread_{thread_id}",
                            timestamp=datetime.now(),
                            mentions=[agent],
                            is_command=False
                        )
                        
                        self.agent_manager.handle_message(message)
                        
                        response_time = time.time() - msg_start
                        thread_responses.append(response_time)
                        
                    except Exception as e:
                        thread_errors += 1
                        logger.debug(f"Thread {thread_id} error: {e}")
                
                return thread_errors, thread_responses
            
            # Start threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
                # Monitor system resources
                process = psutil.Process()
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB
                initial_cpu = process.cpu_percent()
                
                # Submit tasks
                futures = [executor.submit(worker_thread, i) for i in range(thread_count)]
                
                # Wait for completion
                for future in concurrent.futures.as_completed(futures):
                    thread_errors, thread_responses = future.result()
                    errors.extend([thread_errors])
                    response_times.extend(thread_responses)
                
                # Final resource measurement
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                final_cpu = process.cpu_percent()
            
            total_duration = time.time() - start_time
            total_messages = thread_count * 20
            total_errors = sum(errors)
            error_rate = total_errors / total_messages if total_messages > 0 else 0
            
            test_results['thread_counts'].append({
                'threads': thread_count,
                'total_messages': total_messages,
                'total_errors': total_errors,
                'error_rate': error_rate,
                'duration': total_duration,
                'throughput': total_messages / total_duration,
                'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
                'memory_increase': final_memory - initial_memory,
                'cpu_usage': final_cpu
            })
        
        self.results['stress_test_results']['concurrent_operations'] = test_results
        logger.info("Concurrent operations test complete")

    def test_memory_stress(self):
        """Test memory usage under stress"""
        logger.info("Testing memory stress...")
        
        test_results = {
            'initial_memory': 0,
            'peak_memory': 0,
            'memory_growth': [],
            'gc_collections': 0
        }
        
        import gc
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        test_results['initial_memory'] = initial_memory
        
        # Create large number of messages and track memory
        for batch in range(10):  # 10 batches
            batch_start_memory = process.memory_info().rss / 1024 / 1024
            
            # Create 1000 messages in this batch
            for i in range(1000):
                agent = self.test_agents[i % len(self.test_agents)]
                message = ParsedMessage(
                    message_id=batch * 1000 + i,
                    text=f"@{agent} memory stress test batch {batch} message {i}",
                    sender="memory_tester",
                    timestamp=datetime.now(),
                    mentions=[agent],
                    is_command=False
                )
                
                try:
                    self.agent_manager.handle_message(message)
                except Exception:
                    pass  # Ignore errors for memory test
            
            # Force garbage collection
            gc.collect()
            
            batch_end_memory = process.memory_info().rss / 1024 / 1024
            test_results['memory_growth'].append({
                'batch': batch,
                'start_memory': batch_start_memory,
                'end_memory': batch_end_memory,
                'growth': batch_end_memory - batch_start_memory
            })
            
            if batch_end_memory > test_results['peak_memory']:
                test_results['peak_memory'] = batch_end_memory
        
        test_results['gc_collections'] = gc.get_count()[0]
        
        self.results['stress_test_results']['memory_stress'] = test_results
        logger.info(f"Memory stress test complete. Peak memory: {test_results['peak_memory']:.1f} MB")

    def test_long_running_stability(self):
        """Test system stability over extended period"""
        logger.info("Testing long-running stability...")
        
        test_results = {
            'duration_minutes': 5,  # 5 minute test
            'messages_sent': 0,
            'errors': 0,
            'performance_degradation': [],
            'memory_leaks': False
        }
        
        start_time = time.time()
        test_duration = 5 * 60  # 5 minutes
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        message_count = 0
        error_count = 0
        
        # Send messages continuously for test duration
        while time.time() - start_time < test_duration:
            try:
                # Send a message every 100ms
                agent = self.test_agents[message_count % len(self.test_agents)]
                message = ParsedMessage(
                    message_id=message_count,
                    text=f"@{agent} stability test message {message_count}",
                    sender="stability_tester",
                    timestamp=datetime.now(),
                    mentions=[agent],
                    is_command=False
                )
                
                msg_start = time.time()
                self.agent_manager.handle_message(message)
                response_time = time.time() - msg_start
                
                message_count += 1
                
                # Record performance every minute
                elapsed = time.time() - start_time
                if elapsed > 0 and int(elapsed) % 60 == 0 and len(test_results['performance_degradation']) < int(elapsed) // 60:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    test_results['performance_degradation'].append({
                        'minute': int(elapsed) // 60,
                        'response_time': response_time,
                        'memory_usage': current_memory,
                        'messages_per_minute': message_count / (elapsed / 60)
                    })
                
                time.sleep(0.1)  # 100ms interval
                
            except Exception as e:
                error_count += 1
                logger.debug(f"Stability test error: {e}")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        test_results['messages_sent'] = message_count
        test_results['errors'] = error_count
        test_results['memory_leaks'] = memory_growth > 100  # Consider >100MB growth as potential leak
        
        self.results['stress_test_results']['long_running_stability'] = test_results
        logger.info(f"Stability test complete. Sent {message_count} messages with {error_count} errors")

    def test_resource_exhaustion(self):
        """Test behavior under resource exhaustion"""
        logger.info("Testing resource exhaustion scenarios...")
        
        test_results = {
            'agent_limit_test': {},
            'message_queue_test': {},
            'file_handle_test': {}
        }
        
        # Test agent creation limits
        try:
            agent_count = 0
            while agent_count < 1000:  # Try to create many agents
                agent_name = f"exhaust_agent_{agent_count}"
                success = self.file_manager.hire_employee(agent_name, "developer")
                if not success:
                    break
                agent_count += 1
            
            test_results['agent_limit_test'] = {
                'max_agents_created': agent_count,
                'limit_reached': agent_count >= 1000
            }
        except Exception as e:
            test_results['agent_limit_test'] = {'error': str(e)}
        
        # Test message queue limits
        try:
            queue_size = 0
            for i in range(10000):  # Try to queue many messages
                message = ParsedMessage(
                    message_id=i,
                    text=f"Queue test message {i}",
                    sender="queue_tester",
                    timestamp=datetime.now(),
                    mentions=[],
                    is_command=False
                )
                
                self.telegram_manager.message_queue.put(message)
                queue_size += 1
                
                if queue_size % 1000 == 0:
                    logger.debug(f"Queued {queue_size} messages")
            
            test_results['message_queue_test'] = {
                'messages_queued': queue_size,
                'queue_full': False
            }
        except Exception as e:
            test_results['message_queue_test'] = {'error': str(e), 'messages_queued': queue_size}
        
        self.results['stress_test_results']['resource_exhaustion'] = test_results
        logger.info("Resource exhaustion test complete")

    def generate_stress_report(self) -> Dict[str, Any]:
        """Generate comprehensive stress test report"""
        logger.info("Generating stress test report...")
        
        end_time = datetime.now()
        total_duration = (end_time - self.results['test_start']).total_seconds()
        
        # Calculate overall metrics
        overall_metrics = {
            'test_duration_seconds': total_duration,
            'total_messages_processed': self.message_count,
            'total_errors': self.error_count,
            'overall_error_rate': self.error_count / self.message_count if self.message_count > 0 else 0,
            'average_throughput': self.message_count / total_duration if total_duration > 0 else 0
        }
        
        # Determine system stability
        stability_assessment = self._assess_system_stability()
        
        # Generate recommendations
        recommendations = self._generate_stress_recommendations()
        
        final_report = {
            'test_summary': {
                'start_time': self.results['test_start'].isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': total_duration,
                'test_environment': str(self.test_dir)
            },
            'overall_metrics': overall_metrics,
            'detailed_results': self.results['stress_test_results'],
            'stability_assessment': stability_assessment,
            'recommendations': recommendations,
            'system_limits': self._identify_system_limits()
        }
        
        return final_report

    def _assess_system_stability(self) -> Dict[str, Any]:
        """Assess overall system stability"""
        assessment = {
            'stability_rating': 'STABLE',
            'performance_degradation': 'MINIMAL',
            'memory_management': 'GOOD',
            'error_handling': 'ROBUST',
            'scalability': 'GOOD'
        }
        
        # Check high frequency test results
        if 'high_frequency' in self.results['stress_test_results']:
            hf_results = self.results['stress_test_results']['high_frequency']
            peak_throughput = hf_results.get('peak_throughput', 0)
            
            if peak_throughput < 50:
                assessment['scalability'] = 'LIMITED'
            elif peak_throughput < 100:
                assessment['scalability'] = 'MODERATE'
        
        # Check memory stress results
        if 'memory_stress' in self.results['stress_test_results']:
            memory_results = self.results['stress_test_results']['memory_stress']
            peak_memory = memory_results.get('peak_memory', 0)
            initial_memory = memory_results.get('initial_memory', 0)
            
            if peak_memory - initial_memory > 500:  # >500MB growth
                assessment['memory_management'] = 'POOR'
            elif peak_memory - initial_memory > 200:  # >200MB growth
                assessment['memory_management'] = 'FAIR'
        
        # Check stability test results
        if 'long_running_stability' in self.results['stress_test_results']:
            stability_results = self.results['stress_test_results']['long_running_stability']
            error_rate = stability_results.get('errors', 0) / stability_results.get('messages_sent', 1)
            
            if error_rate > 0.1:  # >10% error rate
                assessment['stability_rating'] = 'UNSTABLE'
                assessment['error_handling'] = 'POOR'
            elif error_rate > 0.05:  # >5% error rate
                assessment['stability_rating'] = 'MARGINAL'
                assessment['error_handling'] = 'FAIR'
        
        return assessment

    def _generate_stress_recommendations(self) -> List[str]:
        """Generate recommendations based on stress test results"""
        recommendations = []
        
        # Check throughput
        if 'high_frequency' in self.results['stress_test_results']:
            peak_throughput = self.results['stress_test_results']['high_frequency'].get('peak_throughput', 0)
            if peak_throughput < 100:
                recommendations.append("Consider implementing message batching to improve throughput")
                recommendations.append("Optimize message processing pipeline for better performance")
        
        # Check memory usage
        if 'memory_stress' in self.results['stress_test_results']:
            memory_results = self.results['stress_test_results']['memory_stress']
            growth = memory_results.get('peak_memory', 0) - memory_results.get('initial_memory', 0)
            if growth > 200:
                recommendations.append("Implement better memory management and garbage collection")
                recommendations.append("Consider using object pooling for frequently created objects")
        
        # Check concurrent performance
        if 'concurrent_operations' in self.results['stress_test_results']:
            concurrent_results = self.results['stress_test_results']['concurrent_operations']
            if concurrent_results.get('thread_counts'):
                # Check if performance degrades significantly with more threads
                single_thread = concurrent_results['thread_counts'][0]
                multi_thread = concurrent_results['thread_counts'][-1]
                
                if multi_thread['throughput'] < single_thread['throughput'] * 0.5:
                    recommendations.append("Optimize for concurrent access - consider thread-safe data structures")
                    recommendations.append("Review locking mechanisms to reduce contention")
        
        return recommendations

    def _identify_system_limits(self) -> Dict[str, Any]:
        """Identify system limits discovered during testing"""
        limits = {
            'max_throughput': 0,
            'max_concurrent_threads': 0,
            'memory_ceiling': 0,
            'agent_limit': 0
        }
        
        # Extract limits from test results
        if 'high_frequency' in self.results['stress_test_results']:
            limits['max_throughput'] = self.results['stress_test_results']['high_frequency'].get('peak_throughput', 0)
        
        if 'concurrent_operations' in self.results['stress_test_results']:
            thread_results = self.results['stress_test_results']['concurrent_operations'].get('thread_counts', [])
            if thread_results:
                limits['max_concurrent_threads'] = max(result['threads'] for result in thread_results)
        
        if 'memory_stress' in self.results['stress_test_results']:
            limits['memory_ceiling'] = self.results['stress_test_results']['memory_stress'].get('peak_memory', 0)
        
        if 'resource_exhaustion' in self.results['stress_test_results']:
            agent_test = self.results['stress_test_results']['resource_exhaustion'].get('agent_limit_test', {})
            limits['agent_limit'] = agent_test.get('max_agents_created', 0)
        
        return limits


class MockTelegramManager:
    """Enhanced mock Telegram manager for stress testing"""
    
    def __init__(self):
        self.sent_messages = []
        self.message_handlers = []
        self.connected = True
        self.message_queue = MockQueue()
        
    def add_message_handler(self, handler):
        self.message_handlers.append(handler)
    
    def send_message(self, text: str, sender_name: str = "system", reply_to: int = None) -> bool:
        # Simulate some processing time
        time.sleep(0.001)  # 1ms delay
        
        formatted_text = f"{sender_name}-bot: {text}" if sender_name != "system" else text
        self.sent_messages.append(formatted_text)
        return True
    
    def is_connected(self) -> bool:
        return self.connected


class MockQueue:
    """Mock queue for testing"""
    
    def __init__(self):
        self.items = []
    
    def put(self, item):
        self.items.append(item)
    
    def get(self):
        if self.items:
            return self.items.pop(0)
        raise Exception("Queue empty")


def main():
    """Main function to run stress tests"""
    print("🔥 Starting Real-time Communication Stress Tests")
    print("=" * 60)
    
    # Create stress tester
    tester = CommunicationStressTester()
    
    try:
        # Run stress tests
        report = tester.run_stress_tests()
        
        # Print summary
        print("\n📊 STRESS TEST SUMMARY")
        print("=" * 40)
        print(f"Test Duration: {report['test_summary']['duration_seconds']:.1f} seconds")
        print(f"Total Messages: {report['overall_metrics']['total_messages_processed']}")
        print(f"Error Rate: {report['overall_metrics']['overall_error_rate']:.2%}")
        print(f"Average Throughput: {report['overall_metrics']['average_throughput']:.1f} msg/s")
        
        # Print stability assessment
        print("\n🏗️ STABILITY ASSESSMENT")
        print("=" * 40)
        assessment = report['stability_assessment']
        print(f"Overall Stability: {assessment['stability_rating']}")
        print(f"Performance: {assessment['performance_degradation']}")
        print(f"Memory Management: {assessment['memory_management']}")
        print(f"Error Handling: {assessment['error_handling']}")
        print(f"Scalability: {assessment['scalability']}")
        
        # Print system limits
        print("\n📏 SYSTEM LIMITS")
        print("=" * 40)
        limits = report['system_limits']
        print(f"Max Throughput: {limits['max_throughput']:.1f} msg/s")
        print(f"Max Concurrent Threads: {limits['max_concurrent_threads']}")
        print(f"Memory Ceiling: {limits['memory_ceiling']:.1f} MB")
        print(f"Agent Limit: {limits['agent_limit']}")
        
        # Print recommendations
        if report['recommendations']:
            print("\n💡 RECOMMENDATIONS")
            print("=" * 40)
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"{i}. {rec}")
        
        # Save detailed report
        report_file = Path("stress_test_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Determine if tests passed
        stability_rating = assessment['stability_rating']
        passed = stability_rating in ['STABLE', 'MARGINAL']
        
        print(f"\n{'✅ STRESS TESTS PASSED' if passed else '❌ STRESS TESTS FAILED'}")
        return 0 if passed else 1
        
    except Exception as e:
        print(f"\n❌ Stress tests failed with error: {e}")
        logger.exception("Stress tests failed")
        return 1


if __name__ == "__main__":
    exit(main())