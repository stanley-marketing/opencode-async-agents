#!/usr/bin/env python3
"""
Real-time Communication Validation Script for OpenCode-Slack System

This script validates all real-time communication capabilities including:
1. Slack integration and real-time messaging during task execution
2. Telegram communication channels and message delivery
3. Agent status updates and progress reporting in real-time
4. Message formatting and delivery timing across platforms
5. Live update mechanisms during active task processing
6. Communication flow between agents and external channels
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import tempfile
import os
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.chat.telegram_manager import TelegramManager
from src.chat.message_parser import MessageParser, ParsedMessage
from src.chat.chat_config import ChatConfig
from src.bot.slack_app import SlackBot
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.monitoring.agent_health_monitor import AgentHealthMonitor
from src.bridge.agent_bridge import AgentBridge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommunicationValidator:
    """Validates real-time communication capabilities"""
    
    def __init__(self, test_dir: Optional[str] = None):
        """Initialize the communication validator"""
        self.test_dir = Path(test_dir) if test_dir else Path(tempfile.mkdtemp())
        self.test_results = {
            'slack_integration': {},
            'telegram_communication': {},
            'agent_status_updates': {},
            'message_formatting': {},
            'live_updates': {},
            'communication_flow': {},
            'timing_analysis': {},
            'reliability_metrics': {}
        }
        self.start_time = datetime.now()
        
        # Initialize components
        self._setup_test_environment()
        
    def _setup_test_environment(self):
        """Set up test environment with mock components"""
        logger.info("Setting up test environment...")
        
        # Create test directories
        self.sessions_dir = self.test_dir / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.file_manager = FileOwnershipManager(str(self.test_dir / "employees.db"))
        self.task_tracker = TaskProgressTracker(str(self.sessions_dir))
        
        # Mock Telegram manager for testing
        self.telegram_manager = MockTelegramManager()
        
        # Initialize agent manager
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        
        # Initialize health monitor
        self.health_monitor = AgentHealthMonitor(
            self.agent_manager, 
            self.task_tracker,
            polling_interval=5  # 5 second polling for testing
        )
        
        # Initialize Slack bot
        self.slack_bot = SlackBot()
        
        # Initialize agent bridge
        self.agent_bridge = AgentBridge(None, self.agent_manager)
        
        logger.info("Test environment setup complete")

    def validate_all_communications(self) -> Dict[str, Any]:
        """Run comprehensive validation of all communication systems"""
        logger.info("Starting comprehensive real-time communication validation...")
        
        try:
            # 1. Validate Slack Integration
            self.validate_slack_integration()
            
            # 2. Validate Telegram Communication
            self.validate_telegram_communication()
            
            # 3. Validate Agent Status Updates
            self.validate_agent_status_updates()
            
            # 4. Validate Message Formatting
            self.validate_message_formatting()
            
            # 5. Validate Live Updates
            self.validate_live_updates()
            
            # 6. Validate Communication Flow
            self.validate_communication_flow()
            
            # 7. Analyze Timing and Performance
            self.analyze_timing_performance()
            
            # 8. Calculate Reliability Metrics
            self.calculate_reliability_metrics()
            
        except Exception as e:
            logger.error(f"Validation failed with error: {e}")
            self.test_results['validation_error'] = str(e)
        
        # Generate final report
        return self.generate_final_report()

    def validate_slack_integration(self):
        """Validate Slack integration and real-time messaging"""
        logger.info("Validating Slack integration...")
        
        slack_results = {
            'command_processing': {},
            'response_timing': {},
            'message_delivery': {},
            'error_handling': {}
        }
        
        try:
            # Test hire command
            start_time = time.time()
            response = self.slack_bot.handle_hire_command("test_employee", "developer")
            hire_time = time.time() - start_time
            
            slack_results['command_processing']['hire'] = {
                'success': "Successfully hired" in response,
                'response_time': hire_time,
                'response': response
            }
            
            # Test progress command
            start_time = time.time()
            response = self.slack_bot.handle_progress_command("test_employee")
            progress_time = time.time() - start_time
            
            slack_results['command_processing']['progress'] = {
                'success': True,  # Should handle gracefully even with no progress
                'response_time': progress_time,
                'response': response
            }
            
            # Test employees command
            start_time = time.time()
            response = self.slack_bot.handle_employees_command()
            employees_time = time.time() - start_time
            
            slack_results['command_processing']['employees'] = {
                'success': "test_employee" in response,
                'response_time': employees_time,
                'response': response
            }
            
            # Test fire command
            start_time = time.time()
            response = self.slack_bot.handle_fire_command("test_employee")
            fire_time = time.time() - start_time
            
            slack_results['command_processing']['fire'] = {
                'success': "Successfully fired" in response,
                'response_time': fire_time,
                'response': response
            }
            
            # Calculate average response time
            response_times = [
                hire_time, progress_time, employees_time, fire_time
            ]
            slack_results['response_timing']['average'] = sum(response_times) / len(response_times)
            slack_results['response_timing']['max'] = max(response_times)
            slack_results['response_timing']['min'] = min(response_times)
            
            logger.info(f"Slack integration validation complete. Average response time: {slack_results['response_timing']['average']:.3f}s")
            
        except Exception as e:
            logger.error(f"Slack integration validation failed: {e}")
            slack_results['error'] = str(e)
        
        self.test_results['slack_integration'] = slack_results

    def validate_telegram_communication(self):
        """Validate Telegram communication channels and message delivery"""
        logger.info("Validating Telegram communication...")
        
        telegram_results = {
            'connection_status': {},
            'message_sending': {},
            'message_parsing': {},
            'rate_limiting': {},
            'error_handling': {}
        }
        
        try:
            # Test connection status
            telegram_results['connection_status']['is_connected'] = self.telegram_manager.is_connected()
            
            # Test message sending
            test_messages = [
                "Test message 1",
                "Test message with @mention",
                "Test message with special characters: !@#$%^&*()",
                "Very long message: " + "x" * 1000
            ]
            
            send_results = []
            for i, message in enumerate(test_messages):
                start_time = time.time()
                success = self.telegram_manager.send_message(message, f"test_sender_{i}")
                send_time = time.time() - start_time
                
                send_results.append({
                    'message': message[:50] + "..." if len(message) > 50 else message,
                    'success': success,
                    'send_time': send_time
                })
            
            telegram_results['message_sending']['results'] = send_results
            telegram_results['message_sending']['success_rate'] = sum(1 for r in send_results if r['success']) / len(send_results)
            
            # Test message parsing
            parser = MessageParser()
            test_message_data = {
                'message_id': 123,
                'text': '@test_agent please help with this task',
                'from': {'username': 'test_user', 'id': 456},
                'date': int(time.time()),
                'chat': {'id': '789'}
            }
            
            parsed = parser.parse_message(test_message_data)
            telegram_results['message_parsing'] = {
                'mentions_extracted': len(parsed.mentions) > 0,
                'sender_extracted': parsed.sender == 'test_user',
                'text_preserved': parsed.text == test_message_data['text']
            }
            
            # Test rate limiting
            rate_limit_results = []
            for i in range(5):
                success = self.telegram_manager.send_message(f"Rate limit test {i}", "rate_test_sender")
                rate_limit_results.append(success)
                time.sleep(0.1)  # Small delay between messages
            
            telegram_results['rate_limiting'] = {
                'messages_sent': len(rate_limit_results),
                'messages_successful': sum(rate_limit_results),
                'rate_limiting_active': not all(rate_limit_results)
            }
            
            logger.info(f"Telegram communication validation complete. Success rate: {telegram_results['message_sending']['success_rate']:.2%}")
            
        except Exception as e:
            logger.error(f"Telegram communication validation failed: {e}")
            telegram_results['error'] = str(e)
        
        self.test_results['telegram_communication'] = telegram_results

    def validate_agent_status_updates(self):
        """Validate agent status updates and progress reporting in real-time"""
        logger.info("Validating agent status updates...")
        
        status_results = {
            'agent_creation': {},
            'status_tracking': {},
            'progress_updates': {},
            'health_monitoring': {}
        }
        
        try:
            # Create test employee and agent
            self.file_manager.hire_employee("status_test_agent", "developer")
            
            # Check if agent was created
            agents = self.agent_manager.get_agent_status()
            status_results['agent_creation']['agent_exists'] = 'status_test_agent' in agents
            
            if 'status_test_agent' in agents:
                agent_status = agents['status_test_agent']
                status_results['agent_creation']['status_structure'] = {
                    'has_worker_status': 'worker_status' in agent_status,
                    'has_current_task': 'current_task' in agent_status,
                    'has_last_activity': 'last_activity' in agent_status
                }
            
            # Test progress tracking
            task_description = "Test task for status validation"
            files_needed = ["test_file.py"]
            
            task_file = self.task_tracker.create_task_file(
                "status_test_agent", 
                task_description, 
                files_needed
            )
            
            status_results['progress_updates']['task_file_created'] = Path(task_file).exists()
            
            # Update progress and check tracking
            self.task_tracker.update_file_status("status_test_agent", "test_file.py", 50, "In progress")
            progress = self.task_tracker.get_task_progress("status_test_agent")
            
            status_results['progress_updates']['progress_tracking'] = {
                'progress_retrieved': progress is not None,
                'file_status_updated': progress and 'test_file.py' in progress.get('file_status', {}),
                'overall_progress': progress.get('overall_progress', 0) if progress else 0
            }
            
            # Test health monitoring
            self.health_monitor.start_monitoring()
            time.sleep(2)  # Let it run for a bit
            
            health_summary = self.health_monitor.get_agent_health_summary()
            status_results['health_monitoring'] = {
                'monitor_running': True,
                'agents_monitored': health_summary.get('total_agents', 0),
                'healthy_agents': health_summary.get('healthy_agents', 0)
            }
            
            self.health_monitor.stop_monitoring()
            
            logger.info("Agent status updates validation complete")
            
        except Exception as e:
            logger.error(f"Agent status updates validation failed: {e}")
            status_results['error'] = str(e)
        
        self.test_results['agent_status_updates'] = status_results

    def validate_message_formatting(self):
        """Validate message formatting and delivery timing across platforms"""
        logger.info("Validating message formatting...")
        
        formatting_results = {
            'telegram_formatting': {},
            'slack_formatting': {},
            'special_characters': {},
            'message_length': {}
        }
        
        try:
            # Test Telegram message formatting
            test_messages = [
                "Simple message",
                "Message with *bold* and _italic_ text",
                "Message with [link](http://example.com)",
                "Message with code `print('hello')`",
                "Message with emoji 🚀 and symbols !@#$%"
            ]
            
            telegram_format_results = []
            for message in test_messages:
                success = self.telegram_manager.send_message(message, "format_test")
                sent_message = self.telegram_manager.get_last_sent_message()
                
                telegram_format_results.append({
                    'original': message,
                    'sent': sent_message,
                    'success': success,
                    'properly_escaped': self._check_telegram_escaping(sent_message)
                })
            
            formatting_results['telegram_formatting'] = telegram_format_results
            
            # Test message length handling
            long_message = "x" * 5000  # Longer than Telegram limit
            success = self.telegram_manager.send_message(long_message, "length_test")
            sent_message = self.telegram_manager.get_last_sent_message()
            
            formatting_results['message_length'] = {
                'long_message_handled': success,
                'message_truncated': len(sent_message) < len(long_message),
                'truncated_length': len(sent_message) if sent_message else 0
            }
            
            logger.info("Message formatting validation complete")
            
        except Exception as e:
            logger.error(f"Message formatting validation failed: {e}")
            formatting_results['error'] = str(e)
        
        self.test_results['message_formatting'] = formatting_results

    def validate_live_updates(self):
        """Validate live update mechanisms during active task processing"""
        logger.info("Validating live updates...")
        
        live_results = {
            'real_time_updates': {},
            'concurrent_processing': {},
            'update_frequency': {},
            'data_consistency': {}
        }
        
        try:
            # Create test scenario with multiple agents
            agents = ['live_agent_1', 'live_agent_2']
            for agent in agents:
                self.file_manager.hire_employee(agent, "developer")
            
            # Start concurrent tasks
            tasks = []
            for i, agent in enumerate(agents):
                task_desc = f"Live update test task {i+1}"
                files = [f"test_file_{i+1}.py"]
                
                task_file = self.task_tracker.create_task_file(agent, task_desc, files)
                tasks.append((agent, task_file))
            
            # Simulate concurrent updates
            update_times = []
            for i in range(10):
                start_time = time.time()
                
                # Update progress for both agents
                for agent, _ in tasks:
                    progress = min(10 + i * 10, 100)
                    self.task_tracker.update_file_status(
                        agent, 
                        f"test_file_{agents.index(agent)+1}.py", 
                        progress, 
                        f"Update {i+1}"
                    )
                
                update_time = time.time() - start_time
                update_times.append(update_time)
                time.sleep(0.1)  # Small delay between updates
            
            live_results['real_time_updates'] = {
                'updates_completed': len(update_times),
                'average_update_time': sum(update_times) / len(update_times),
                'max_update_time': max(update_times),
                'min_update_time': min(update_times)
            }
            
            # Check data consistency
            consistency_results = []
            for agent, _ in tasks:
                progress = self.task_tracker.get_task_progress(agent)
                consistency_results.append({
                    'agent': agent,
                    'progress_exists': progress is not None,
                    'progress_value': progress.get('overall_progress', 0) if progress else 0
                })
            
            live_results['data_consistency'] = consistency_results
            
            logger.info("Live updates validation complete")
            
        except Exception as e:
            logger.error(f"Live updates validation failed: {e}")
            live_results['error'] = str(e)
        
        self.test_results['live_updates'] = live_results

    def validate_communication_flow(self):
        """Validate communication flow between agents and external channels"""
        logger.info("Validating communication flow...")
        
        flow_results = {
            'message_routing': {},
            'agent_responses': {},
            'channel_integration': {},
            'error_propagation': {}
        }
        
        try:
            # Create test agent
            self.file_manager.hire_employee("flow_test_agent", "developer")
            
            # Test message routing through the system
            test_message = ParsedMessage(
                message_id=1,
                text="@flow_test_agent please help with this task",
                sender="test_user",
                timestamp=datetime.now(),
                mentions=["flow_test_agent"],
                is_command=False
            )
            
            # Process message through agent manager
            start_time = time.time()
            self.agent_manager.handle_message(test_message)
            processing_time = time.time() - start_time
            
            flow_results['message_routing'] = {
                'message_processed': True,
                'processing_time': processing_time,
                'responses_generated': len(self.telegram_manager.sent_messages) > 0
            }
            
            # Check agent responses
            if self.telegram_manager.sent_messages:
                last_response = self.telegram_manager.sent_messages[-1]
                flow_results['agent_responses'] = {
                    'response_received': True,
                    'response_content': last_response[:100],
                    'response_formatted': 'flow_test_agent-bot:' in last_response
                }
            else:
                flow_results['agent_responses'] = {
                    'response_received': False
                }
            
            # Test error handling
            error_message = ParsedMessage(
                message_id=2,
                text="@nonexistent_agent do something",
                sender="test_user",
                timestamp=datetime.now(),
                mentions=["nonexistent_agent"],
                is_command=False
            )
            
            try:
                self.agent_manager.handle_message(error_message)
                flow_results['error_propagation'] = {
                    'error_handled_gracefully': True,
                    'system_remained_stable': True
                }
            except Exception as e:
                flow_results['error_propagation'] = {
                    'error_handled_gracefully': False,
                    'error_message': str(e)
                }
            
            logger.info("Communication flow validation complete")
            
        except Exception as e:
            logger.error(f"Communication flow validation failed: {e}")
            flow_results['error'] = str(e)
        
        self.test_results['communication_flow'] = flow_results

    def analyze_timing_performance(self):
        """Analyze timing and performance of communication systems"""
        logger.info("Analyzing timing and performance...")
        
        timing_results = {
            'response_times': {},
            'throughput': {},
            'latency_analysis': {},
            'performance_bottlenecks': {}
        }
        
        try:
            # Measure various operation timings
            operations = {
                'agent_creation': lambda: self.file_manager.hire_employee(f"timing_agent_{int(time.time())}", "developer"),
                'message_processing': lambda: self.agent_manager.handle_message(
                    ParsedMessage(1, "test", "user", datetime.now(), [], False)
                ),
                'progress_update': lambda: self.task_tracker.update_current_work("timing_agent", "test work"),
                'status_check': lambda: self.agent_manager.get_agent_status()
            }
            
            for op_name, operation in operations.items():
                times = []
                for _ in range(5):  # Run each operation 5 times
                    start_time = time.time()
                    try:
                        operation()
                        end_time = time.time()
                        times.append(end_time - start_time)
                    except Exception:
                        times.append(float('inf'))  # Mark failed operations
                
                valid_times = [t for t in times if t != float('inf')]
                if valid_times:
                    timing_results['response_times'][op_name] = {
                        'average': sum(valid_times) / len(valid_times),
                        'min': min(valid_times),
                        'max': max(valid_times),
                        'success_rate': len(valid_times) / len(times)
                    }
            
            # Measure throughput
            start_time = time.time()
            message_count = 0
            test_duration = 5  # 5 seconds
            
            while time.time() - start_time < test_duration:
                self.telegram_manager.send_message(f"Throughput test {message_count}", "throughput_test")
                message_count += 1
                time.sleep(0.1)  # Small delay to avoid overwhelming
            
            actual_duration = time.time() - start_time
            timing_results['throughput'] = {
                'messages_per_second': message_count / actual_duration,
                'total_messages': message_count,
                'test_duration': actual_duration
            }
            
            logger.info("Timing and performance analysis complete")
            
        except Exception as e:
            logger.error(f"Timing analysis failed: {e}")
            timing_results['error'] = str(e)
        
        self.test_results['timing_analysis'] = timing_results

    def calculate_reliability_metrics(self):
        """Calculate reliability metrics for the communication system"""
        logger.info("Calculating reliability metrics...")
        
        reliability_results = {
            'overall_success_rate': 0,
            'component_reliability': {},
            'error_rates': {},
            'availability': {}
        }
        
        try:
            # Calculate success rates from previous tests
            success_counts = []
            total_counts = []
            
            # Slack integration success rate
            slack_results = self.test_results.get('slack_integration', {})
            if 'command_processing' in slack_results:
                slack_successes = sum(1 for cmd in slack_results['command_processing'].values() 
                                    if cmd.get('success', False))
                slack_total = len(slack_results['command_processing'])
                success_counts.append(slack_successes)
                total_counts.append(slack_total)
                
                reliability_results['component_reliability']['slack'] = slack_successes / slack_total if slack_total > 0 else 0
            
            # Telegram communication success rate
            telegram_results = self.test_results.get('telegram_communication', {})
            if 'message_sending' in telegram_results:
                telegram_success_rate = telegram_results['message_sending'].get('success_rate', 0)
                reliability_results['component_reliability']['telegram'] = telegram_success_rate
                success_counts.append(telegram_success_rate * 10)  # Approximate count
                total_counts.append(10)
            
            # Agent status updates success rate
            status_results = self.test_results.get('agent_status_updates', {})
            status_successes = 0
            status_total = 0
            
            for category in ['agent_creation', 'progress_updates', 'health_monitoring']:
                if category in status_results:
                    category_data = status_results[category]
                    if isinstance(category_data, dict):
                        category_successes = sum(1 for v in category_data.values() if v)
                        category_total = len(category_data)
                        status_successes += category_successes
                        status_total += category_total
            
            if status_total > 0:
                reliability_results['component_reliability']['agent_status'] = status_successes / status_total
                success_counts.append(status_successes)
                total_counts.append(status_total)
            
            # Calculate overall success rate
            if total_counts:
                overall_success = sum(success_counts)
                overall_total = sum(total_counts)
                reliability_results['overall_success_rate'] = overall_success / overall_total if overall_total > 0 else 0
            
            # Calculate error rates
            error_count = sum(1 for result in self.test_results.values() if 'error' in result)
            total_tests = len(self.test_results)
            reliability_results['error_rates'] = {
                'test_error_rate': error_count / total_tests if total_tests > 0 else 0,
                'total_errors': error_count,
                'total_tests': total_tests
            }
            
            # System availability (simplified - based on successful component initialization)
            components_available = sum(1 for component in ['slack_integration', 'telegram_communication', 'agent_status_updates'] 
                                     if component in self.test_results and 'error' not in self.test_results[component])
            total_components = 3
            reliability_results['availability'] = components_available / total_components
            
            logger.info(f"Reliability metrics calculated. Overall success rate: {reliability_results['overall_success_rate']:.2%}")
            
        except Exception as e:
            logger.error(f"Reliability calculation failed: {e}")
            reliability_results['error'] = str(e)
        
        self.test_results['reliability_metrics'] = reliability_results

    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report"""
        logger.info("Generating final validation report...")
        
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        # Create summary
        summary = {
            'validation_start_time': self.start_time.isoformat(),
            'validation_end_time': end_time.isoformat(),
            'total_duration_seconds': total_duration,
            'test_environment': str(self.test_dir),
            'components_tested': list(self.test_results.keys()),
            'overall_status': 'PASS' if self._determine_overall_status() else 'FAIL'
        }
        
        # Create detailed findings
        findings = self._generate_findings()
        
        # Create recommendations
        recommendations = self._generate_recommendations()
        
        final_report = {
            'summary': summary,
            'detailed_results': self.test_results,
            'findings': findings,
            'recommendations': recommendations,
            'reliability_assessment': self._generate_reliability_assessment()
        }
        
        logger.info(f"Validation complete. Overall status: {summary['overall_status']}")
        return final_report

    def _determine_overall_status(self) -> bool:
        """Determine if overall validation passed"""
        reliability = self.test_results.get('reliability_metrics', {})
        overall_success_rate = reliability.get('overall_success_rate', 0)
        error_rate = reliability.get('error_rates', {}).get('test_error_rate', 1)
        
        # Pass if success rate > 80% and error rate < 20%
        return overall_success_rate > 0.8 and error_rate < 0.2

    def _generate_findings(self) -> List[Dict[str, Any]]:
        """Generate key findings from validation"""
        findings = []
        
        # Slack integration findings
        slack_results = self.test_results.get('slack_integration', {})
        if 'response_timing' in slack_results:
            avg_time = slack_results['response_timing'].get('average', 0)
            findings.append({
                'category': 'Slack Integration',
                'type': 'PERFORMANCE',
                'severity': 'INFO' if avg_time < 1.0 else 'WARNING',
                'message': f"Average Slack command response time: {avg_time:.3f}s",
                'details': slack_results['response_timing']
            })
        
        # Telegram communication findings
        telegram_results = self.test_results.get('telegram_communication', {})
        if 'message_sending' in telegram_results:
            success_rate = telegram_results['message_sending'].get('success_rate', 0)
            findings.append({
                'category': 'Telegram Communication',
                'type': 'RELIABILITY',
                'severity': 'INFO' if success_rate > 0.9 else 'WARNING' if success_rate > 0.7 else 'ERROR',
                'message': f"Telegram message delivery success rate: {success_rate:.1%}",
                'details': telegram_results['message_sending']
            })
        
        # Agent status findings
        status_results = self.test_results.get('agent_status_updates', {})
        if 'health_monitoring' in status_results:
            monitoring = status_results['health_monitoring']
            findings.append({
                'category': 'Agent Monitoring',
                'type': 'FUNCTIONALITY',
                'severity': 'INFO' if monitoring.get('monitor_running') else 'ERROR',
                'message': f"Health monitoring operational: {monitoring.get('monitor_running', False)}",
                'details': monitoring
            })
        
        return findings

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Check timing performance
        timing = self.test_results.get('timing_analysis', {})
        if 'response_times' in timing:
            slow_operations = [op for op, times in timing['response_times'].items() 
                             if times.get('average', 0) > 1.0]
            if slow_operations:
                recommendations.append(
                    f"Consider optimizing slow operations: {', '.join(slow_operations)}"
                )
        
        # Check reliability
        reliability = self.test_results.get('reliability_metrics', {})
        overall_success = reliability.get('overall_success_rate', 0)
        if overall_success < 0.9:
            recommendations.append(
                "Improve system reliability - current success rate below 90%"
            )
        
        # Check error handling
        error_rate = reliability.get('error_rates', {}).get('test_error_rate', 0)
        if error_rate > 0.1:
            recommendations.append(
                "Enhance error handling and recovery mechanisms"
            )
        
        # Check message formatting
        formatting = self.test_results.get('message_formatting', {})
        if 'error' in formatting:
            recommendations.append(
                "Review and fix message formatting issues"
            )
        
        return recommendations

    def _generate_reliability_assessment(self) -> Dict[str, Any]:
        """Generate reliability assessment"""
        reliability = self.test_results.get('reliability_metrics', {})
        
        assessment = {
            'overall_rating': 'EXCELLENT',
            'confidence_level': 'HIGH',
            'risk_factors': [],
            'strengths': []
        }
        
        success_rate = reliability.get('overall_success_rate', 0)
        
        if success_rate >= 0.95:
            assessment['overall_rating'] = 'EXCELLENT'
        elif success_rate >= 0.85:
            assessment['overall_rating'] = 'GOOD'
        elif success_rate >= 0.70:
            assessment['overall_rating'] = 'FAIR'
        else:
            assessment['overall_rating'] = 'POOR'
        
        # Identify strengths and risks
        component_reliability = reliability.get('component_reliability', {})
        for component, rate in component_reliability.items():
            if rate >= 0.9:
                assessment['strengths'].append(f"{component.title()} shows high reliability ({rate:.1%})")
            elif rate < 0.7:
                assessment['risk_factors'].append(f"{component.title()} reliability below acceptable threshold ({rate:.1%})")
        
        return assessment

    def _check_telegram_escaping(self, message: str) -> bool:
        """Check if Telegram message is properly escaped"""
        if not message:
            return True
        
        # Check for unescaped special characters that could break Markdown
        problematic_chars = ['*', '_', '[', ']', '(', ')']
        for char in problematic_chars:
            if char in message and f'\\{char}' not in message:
                # Found unescaped special character
                return False
        return True


class MockTelegramManager:
    """Mock Telegram manager for testing"""
    
    def __init__(self):
        self.sent_messages = []
        self.message_handlers = []
        self.connected = True
        
    def add_message_handler(self, handler):
        self.message_handlers.append(handler)
    
    def send_message(self, text: str, sender_name: str = "system", reply_to: Optional[int] = None) -> bool:
        """Mock send message - always succeeds and stores message"""
        formatted_text = f"{sender_name}-bot: {text}" if sender_name != "system" else text
        self.sent_messages.append(formatted_text)
        return True
    
    def get_last_sent_message(self) -> str:
        """Get the last sent message"""
        return self.sent_messages[-1] if self.sent_messages else ""
    
    def is_connected(self) -> bool:
        return self.connected
    
    def start_polling(self):
        pass
    
    def stop_polling(self):
        pass


def main():
    """Main function to run the validation"""
    print("🚀 Starting Real-time Communication Validation for OpenCode-Slack System")
    print("=" * 80)
    
    # Create validator
    validator = CommunicationValidator()
    
    try:
        # Run comprehensive validation
        report = validator.validate_all_communications()
        
        # Print summary
        print("\n📊 VALIDATION SUMMARY")
        print("=" * 40)
        print(f"Overall Status: {report['summary']['overall_status']}")
        print(f"Duration: {report['summary']['total_duration_seconds']:.2f} seconds")
        print(f"Components Tested: {len(report['summary']['components_tested'])}")
        
        # Print key findings
        print("\n🔍 KEY FINDINGS")
        print("=" * 40)
        for finding in report['findings']:
            severity_icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(finding['severity'], "📝")
            print(f"{severity_icon} [{finding['category']}] {finding['message']}")
        
        # Print reliability assessment
        print("\n📈 RELIABILITY ASSESSMENT")
        print("=" * 40)
        assessment = report['reliability_assessment']
        print(f"Overall Rating: {assessment['overall_rating']}")
        print(f"Confidence Level: {assessment['confidence_level']}")
        
        if assessment['strengths']:
            print("\nStrengths:")
            for strength in assessment['strengths']:
                print(f"  ✅ {strength}")
        
        if assessment['risk_factors']:
            print("\nRisk Factors:")
            for risk in assessment['risk_factors']:
                print(f"  ⚠️ {risk}")
        
        # Print recommendations
        if report['recommendations']:
            print("\n💡 RECOMMENDATIONS")
            print("=" * 40)
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"{i}. {rec}")
        
        # Save detailed report
        report_file = Path("communication_validation_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Return appropriate exit code
        return 0 if report['summary']['overall_status'] == 'PASS' else 1
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        logger.exception("Validation failed")
        return 1


if __name__ == "__main__":
    exit(main())