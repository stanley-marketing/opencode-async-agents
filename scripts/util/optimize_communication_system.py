#!/usr/bin/env python3
"""
Communication System Optimization Integration Script
Integrates all optimized communication components into the existing OpenCode-Slack system.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio
import json
import logging
import os
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.communication.optimized_message_router import OptimizedMessageRouter, Message
from src.communication.enhanced_telegram_manager import EnhancedTelegramManager
from src.communication.agent_discovery_optimizer import AgentDiscoveryOptimizer
from src.communication.realtime_monitor import RealtimeMonitor

# Import existing components
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.bridge.agent_bridge import AgentBridge
from src.utils.opencode_wrapper import OpencodeSessionManager

# Configure logging
logging.basicConfig(
    level    =  logging.INFO,
    format    =  '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger     =   logging.getLogger(__name__)

class OptimizedCommunicationSystem:
    """Integrated optimized communication system"""

    def __init__(self, config: Optional[Dict[str, Any]]     =   None):
        self.config     =   config or self._load_default_config()

        # Core components
        self.file_manager     =   None
        self.task_tracker     =   None
        self.session_manager     =   None

        # Optimized communication components
        self.message_router     =   None
        self.enhanced_telegram     =   None
        self.agent_discovery     =   None
        self.realtime_monitor     =   None

        # Legacy components (for compatibility)
        self.legacy_agent_manager     =   None
        self.agent_bridge     =   None

        # System state
        self.running     =   False
        self.optimization_metrics     =   {
            'start_time': None,
            'messages_processed': 0,
            'agents_optimized': 0,
            'performance_improvements': {},
            'reliability_improvements': {}
        }

        logger.info("Optimized Communication System initialized")

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            'message_router': {
                'max_workers': 10,
                'queue_size': 5000,
                'enable_compression': True,
                'enable_deduplication': True
            },
            'telegram_manager': {
                'rate_limit': 60,  # messages per minute
                'burst_capacity': 20,
                'batch_size': 5,
                'batch_timeout': 1.0,
                'connection_pool_size': 5
            },
            'agent_discovery': {
                'default_strategy': 'performance_based',
                'load_balancing': True,
                'performance_tracking': True
            },
            'monitoring': {
                'metrics_retention_hours': 24,
                'alert_check_interval': 30,
                'resource_monitoring': True
            },
            'optimization': {
                'target_throughput': 100,  # messages per second
                'target_latency': 50,      # milliseconds
                'target_success_rate': 95, # percentage
                'enable_auto_scaling': True
            }
        }

    def initialize_system(self, db_path: str     =   "employees.db", sessions_dir: str     =   "sessions"):
        """Initialize the complete system"""
        logger.info("Initializing optimized communication system...")

        try:
            # Initialize core components
            self._initialize_core_components(db_path, sessions_dir)

            # Initialize optimized communication components
            self._initialize_optimized_components()

            # Set up integrations
            self._setup_component_integrations()

            # Initialize monitoring and alerts
            self._setup_monitoring_and_alerts()

            logger.info("System initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            return False

    def _initialize_core_components(self, db_path: str, sessions_dir: str):
        """Initialize core OpenCode-Slack components"""
        logger.info("Initializing core components...")

        # File management
        self.file_manager     =   FileOwnershipManager(db_path)

        # Task tracking
        os.makedirs(sessions_dir, exist_ok    =  True)
        self.task_tracker     =   TaskProgressTracker(sessions_dir)

        # Session management
        self.session_manager     =   OpencodeSessionManager(
            self.file_manager, sessions_dir, quiet_mode    =  True
        )

        logger.info("Core components initialized")

    def _initialize_optimized_components(self):
        """Initialize optimized communication components"""
        logger.info("Initializing optimized communication components...")

        # Message Router
        router_config     =   self.config['message_router']
        self.message_router     =   OptimizedMessageRouter(
            max_workers    =  router_config['max_workers'],
            queue_size    =  router_config['queue_size']
        )
        self.message_router.enable_compression     =   router_config['enable_compression']
        self.message_router.enable_deduplication     =   router_config['enable_deduplication']

        # Enhanced Telegram Manager
        self.enhanced_telegram     =   EnhancedTelegramManager()

        # Agent Discovery Optimizer
        self.agent_discovery     =   AgentDiscoveryOptimizer()

        # Real-time Monitor
        self.realtime_monitor     =   RealtimeMonitor(self._handle_alert)

        logger.info("Optimized communication components initialized")

    def _setup_component_integrations(self):
        """Set up integrations between components"""
        logger.info("Setting up component integrations...")

        # Register message handlers
        self.message_router.register_handler('telegram', self._handle_telegram_message)
        self.message_router.register_handler('agent_discovery', self._handle_agent_discovery_message)

        # Set up routes
        self.message_router.add_route('telegram', 'telegram', weight    =  1.0)
        self.message_router.add_route('agent_task', 'agent_discovery', weight    =  1.0)

        # Initialize legacy components for compatibility
        self._initialize_legacy_compatibility()

        # Set up monitoring integrations
        self._setup_monitoring_integrations()

        logger.info("Component integrations completed")

    def _initialize_legacy_compatibility(self):
        """Initialize legacy components for backward compatibility"""
        logger.info("Setting up legacy compatibility...")

        try:
            # Create enhanced Telegram manager wrapper
            from src.chat.telegram_manager import TelegramManager

            # Replace the legacy telegram manager with enhanced version
            self.legacy_agent_manager     =   AgentManager(self.file_manager, self.enhanced_telegram)

            # Set up monitoring system
            if hasattr(self.legacy_agent_manager, 'setup_monitoring_system'):
                self.legacy_agent_manager.setup_monitoring_system(
                    self.task_tracker, self.session_manager
                )

            # Sync existing agents
            self.legacy_agent_manager.sync_agents_with_employees()

            # Create agent bridge
            self.agent_bridge     =   AgentBridge(self.session_manager, self.legacy_agent_manager)

            # Migrate agents to optimized discovery system
            self._migrate_agents_to_optimizer()

            logger.info("Legacy compatibility setup completed")

        except Exception as e:
            logger.warning(f"Legacy compatibility setup failed: {e}")

    def _migrate_agents_to_optimizer(self):
        """Migrate existing agents to the optimized discovery system"""
        if not self.legacy_agent_manager:
            return

        logger.info("Migrating agents to optimized discovery system...")

        try:
            # Get existing agents
            existing_agents     =   self.legacy_agent_manager.get_agent_status()

            for agent_name, status in existing_agents.items():
                # Register agent in optimizer
                role     =   status.get('role', 'developer')
                expertise     =   status.get('expertise', [])

                self.agent_discovery.register_agent(agent_name, role, expertise)

                # Update status
                worker_status     =   status.get('worker_status', 'idle')
                current_load     =   1 if worker_status == 'working' else 0

                self.agent_discovery.update_agent_status(agent_name, worker_status, current_load)

            self.optimization_metrics['agents_optimized']     =   len(existing_agents)
            logger.info(f"Migrated {len(existing_agents)} agents to optimizer")

        except Exception as e:
            logger.error(f"Agent migration failed: {e}")

    def _setup_monitoring_integrations(self):
        """Set up monitoring integrations"""
        logger.info("Setting up monitoring integrations...")

        # Add middleware to message router for monitoring
        def monitoring_middleware(message: Message) -> Message:
            self.realtime_monitor.record_message_event(
                'message_sent',
                latency_ms    =  0,  # Will be updated by handler
                success    =  True,
                timestamp    =  datetime.now()
            )
            return message

        self.message_router.add_middleware(monitoring_middleware)

        # Set up periodic metrics collection
        self._setup_periodic_metrics_collection()

        logger.info("Monitoring integrations completed")

    def _setup_periodic_metrics_collection(self):
        """Set up periodic collection of system metrics"""
        def collect_metrics():
            while self.running:
                try:
                    # Collect router metrics
                    router_metrics     =   self.message_router.get_metrics()
                    self.realtime_monitor.record_message_event(
                        'queue_size',
                        size    =  router_metrics.get('current_queue_size', 0)
                    )

                    # Collect discovery metrics
                    discovery_metrics     =   self.agent_discovery.get_system_metrics()

                    # Collect Telegram metrics
                    telegram_metrics     =   self.enhanced_telegram.get_performance_metrics()

                    # Update optimization metrics
                    self._update_optimization_metrics(router_metrics, discovery_metrics, telegram_metrics)

                    time.sleep(30)  # Collect every 30 seconds

                except Exception as e:
                    logger.error(f"Error collecting metrics: {e}")
                    time.sleep(30)

        metrics_thread     =   threading.Thread(target    =  collect_metrics, daemon    =  True)
        metrics_thread.start()

    def _setup_monitoring_and_alerts(self):
        """Set up monitoring and alerting"""
        logger.info("Setting up monitoring and alerts...")

        # Add custom alerts for optimization targets
        opt_config     =   self.config['optimization']

        # Throughput alert
        self.realtime_monitor.add_custom_alert(
            'low_throughput',
            'message_throughput',
            'lt',
            opt_config['target_throughput'] * 0.8,  # 80% of target
            duration_minutes    =  5
        )

        # Latency alert
        self.realtime_monitor.add_custom_alert(
            'high_latency',
            'message_latency',
            'gt',
            opt_config['target_latency'] * 1.5,  # 150% of target
            duration_minutes    =  3
        )

        # Success rate alert
        self.realtime_monitor.add_custom_alert(
            'low_success_rate',
            'success_rate',
            'lt',
            opt_config['target_success_rate'],
            duration_minutes    =  5
        )

        logger.info("Monitoring and alerts configured")

    def start_system(self):
        """Start the optimized communication system"""
        if self.running:
            logger.warning("System is already running")
            return False

        logger.info("Starting optimized communication system...")

        try:
            # Start core components
            self.message_router.start()
            self.agent_discovery.start()
            self.realtime_monitor.start_monitoring()

            # Start Telegram polling if configured
            if hasattr(self.enhanced_telegram, 'start_polling'):
                try:
                    self.enhanced_telegram.start_polling()
                    logger.info("Enhanced Telegram polling started")
                except Exception as e:
                    logger.warning(f"Telegram polling failed to start: {e}")

            # Start agent bridge monitoring
            if self.agent_bridge:
                try:
                    self.agent_bridge.start_monitoring()
                    logger.info("Agent bridge monitoring started")
                except Exception as e:
                    logger.warning(f"Agent bridge monitoring failed: {e}")

            self.running     =   True
            self.optimization_metrics['start_time']     =   datetime.now()

            logger.info("Optimized communication system started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            return False

    def stop_system(self):
        """Stop the optimized communication system"""
        if not self.running:
            logger.warning("System is not running")
            return

        logger.info("Stopping optimized communication system...")

        try:
            self.running     =   False

            # Stop components
            if self.message_router:
                self.message_router.stop()

            if self.agent_discovery:
                self.agent_discovery.stop()

            if self.realtime_monitor:
                self.realtime_monitor.stop_monitoring()

            if self.enhanced_telegram and hasattr(self.enhanced_telegram, 'stop_polling'):
                self.enhanced_telegram.stop_polling()

            logger.info("Optimized communication system stopped")

        except Exception as e:
            logger.error(f"Error stopping system: {e}")

    def _handle_telegram_message(self, message: Message) -> bool:
        """Handle Telegram message routing"""
        try:
            # Extract Telegram-specific data
            chat_id     =   message.metadata.get('chat_id')
            reply_to     =   message.metadata.get('reply_to')

            # Send through enhanced Telegram manager
            success     =   self.enhanced_telegram.send_message(
                message.content,
                message.sender,
                reply_to
            )

            # Record metrics
            if success:
                self.optimization_metrics['messages_processed'] +    =   1

            return success

        except Exception as e:
            logger.error(f"Error handling Telegram message: {e}")
            return False

    def _handle_agent_discovery_message(self, message: Message) -> bool:
        """Handle agent discovery message routing"""
        try:
            # Extract task information
            task_type     =   message.metadata.get('task_type', 'general')
            expertise     =   message.metadata.get('expertise', [])

            # Find best agent
            agent_name     =   self.agent_discovery.find_best_agent(task_type, expertise)

            if agent_name:
                # Assign task
                task_id     =   message.metadata.get('task_id', message.id)
                success     =   self.agent_discovery.assign_task(agent_name, task_id, task_type)

                # Record metrics
                self.realtime_monitor.record_message_event(
                    'agent_response',
                    agent_name    =  agent_name,
                    response_time_ms    =  50,  # Estimated
                    success    =  success
                )

                return success

            return False

        except Exception as e:
            logger.error(f"Error handling agent discovery message: {e}")
            return False

    def _handle_alert(self, alert: Dict[str, Any]):
        """Handle system alerts"""
        logger.warning(f"System alert: {alert['rule_name']} - {alert['current_value']}")

        # Implement auto-scaling if enabled
        if self.config['optimization']['enable_auto_scaling']:
            self._handle_auto_scaling(alert)

    def _handle_auto_scaling(self, alert: Dict[str, Any]):
        """Handle automatic scaling based on alerts"""
        rule_name     =   alert['rule_name']

        try:
            if rule_name == 'low_throughput':
                # Increase message router workers
                current_workers     =   self.message_router.max_workers
                if current_workers < 20:
                    # This would require implementing dynamic worker scaling
                    logger.info(f"Auto-scaling: Would increase workers from {current_workers}")

            elif rule_name == 'high_latency':
                # Optimize routing strategy
                logger.info("Auto-scaling: Optimizing routing strategy for lower latency")

            elif rule_name == 'large_queue_size':
                # Increase processing capacity
                logger.info("Auto-scaling: Would increase processing capacity")

        except Exception as e:
            logger.error(f"Auto-scaling failed: {e}")

    def _update_optimization_metrics(self, router_metrics: Dict, discovery_metrics: Dict, telegram_metrics: Dict):
        """Update optimization performance metrics"""
        try:
            # Calculate performance improvements
            current_throughput     =   router_metrics.get('current_throughput_per_second', 0)
            target_throughput     =   self.config['optimization']['target_throughput']

            self.optimization_metrics['performance_improvements']     =   {
                'throughput_ratio': current_throughput / target_throughput if target_throughput > 0 else 0,
                'success_rate': router_metrics.get('success_rate', 0),
                'average_latency_ms': router_metrics.get('average_latency_ms', 0),
                'agent_utilization': discovery_metrics.get('system_utilization', 0),
                'telegram_success_rate': telegram_metrics.get('success_rate', 0)
            }

            # Calculate reliability improvements
            self.optimization_metrics['reliability_improvements']     =   {
                'error_rate': 1.0 - router_metrics.get('success_rate', 1.0),
                'queue_stability': 1.0 - (router_metrics.get('current_queue_size', 0) / router_metrics.get('peak_queue_size', 1)),
                'agent_health': discovery_metrics.get('routing_success_rate', 0),
                'system_uptime': (datetime.now() - self.optimization_metrics['start_time']).total_seconds() if self.optimization_metrics['start_time'] else 0
            }

        except Exception as e:
            logger.error(f"Error updating optimization metrics: {e}")

    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report"""
        if not self.running:
            return {'error': 'System not running'}

        try:
            # Get component metrics
            router_metrics     =   self.message_router.get_metrics()
            discovery_metrics     =   self.agent_discovery.get_system_metrics()
            telegram_metrics     =   self.enhanced_telegram.get_performance_metrics()
            monitor_data     =   self.realtime_monitor.get_dashboard_data()

            # Calculate optimization achievements
            target_config     =   self.config['optimization']
            achievements     =   {
                'throughput_target_met': router_metrics.get('current_throughput_per_second', 0) >   =  target_config['target_throughput'],
                'latency_target_met': router_metrics.get('average_latency_ms', float('inf')) <   =  target_config['target_latency'],
                'success_rate_target_met': router_metrics.get('success_rate', 0) >   =  target_config['target_success_rate'] / 100,
                'system_stable': len(monitor_data.get('active_alerts', [])) == 0
            }

            # Generate recommendations
            recommendations     =   []

            if not achievements['throughput_target_met']:
                recommendations.append("Consider increasing message router workers or optimizing message processing")

            if not achievements['latency_target_met']:
                recommendations.append("Optimize message routing algorithms and reduce processing overhead")

            if not achievements['success_rate_target_met']:
                recommendations.append("Improve error handling and implement better retry mechanisms")

            if not achievements['system_stable']:
                recommendations.append("Address active alerts to improve system stability")

            return {
                'optimization_summary': {
                    'system_running': self.running,
                    'uptime_seconds': (datetime.now() - self.optimization_metrics['start_time']).total_seconds() if self.optimization_metrics['start_time'] else 0,
                    'messages_processed': self.optimization_metrics['messages_processed'],
                    'agents_optimized': self.optimization_metrics['agents_optimized']
                },
                'performance_metrics': {
                    'router': router_metrics,
                    'discovery': discovery_metrics,
                    'telegram': telegram_metrics
                },
                'target_achievements': achievements,
                'optimization_improvements': self.optimization_metrics.get('performance_improvements', {}),
                'reliability_improvements': self.optimization_metrics.get('reliability_improvements', {}),
                'monitoring_data': monitor_data,
                'recommendations': recommendations,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating optimization report: {e}")
            return {'error': str(e)}

    def send_optimized_message(self, content: str, sender: str, recipient: str,
                              priority: int     =   2, task_type: Optional[str]     =   None,
                              expertise: Optional[List[str]]     =   None) -> bool:
        """Send message through optimized routing"""
        try:
            message     =   Message(
                id    =  f"opt_{int(time.time() * 1000)}_{sender}",
                content    =  content,
                sender    =  sender,
                recipient    =  recipient,
                priority    =  priority,
                metadata    =  {
                    'task_type': task_type,
                    'expertise': expertise or [],
                    'optimized': True
                }
            )

            return self.message_router.send_message(message)

        except Exception as e:
            logger.error(f"Error sending optimized message: {e}")
            return False

def main():
    """Main function to demonstrate the optimized system"""
    print("🚀 OpenCode-Slack Communication System Optimization")
    print("    =  " * 60)

    # Initialize system
    system     =   OptimizedCommunicationSystem()

    try:
        # Initialize and start
        if not system.initialize_system():
            print("❌ Failed to initialize system")
            return 1

        if not system.start_system():
            print("❌ Failed to start system")
            return 1

        print("✅ Optimized communication system started successfully")

        # Run for a short demonstration
        print("\n📊 Running optimization demonstration...")

        # Send test messages
        for i in range(10):
            success     =   system.send_optimized_message(
                f"Test message {i}",
                f"test_sender_{i}",
                "telegram",
                priority    =  2,
                task_type    =  "test_task",
                expertise    =  ["python"]
            )
            print(f"Message {i}: {'✅' if success else '❌'}")
            time.sleep(0.1)

        # Wait for processing
        time.sleep(2)

        # Get optimization report
        report     =   system.get_optimization_report()

        print("\n📈 OPTIMIZATION REPORT")
        print("    =  " * 40)

        if 'error' not in report:
            summary     =   report['optimization_summary']
            achievements     =   report['target_achievements']

            print(f"System Uptime: {summary['uptime_seconds']: .1f} seconds")
            print(f"Messages Processed: {summary['messages_processed']}")
            print(f"Agents Optimized: {summary['agents_optimized']}")

            print("\n🎯 Target Achievements: ")
            for target, achieved in achievements.items():
                target_name     =   target.replace('_', ' ').title()
                print(f"  {target_name}: {'✅' if achieved else '❌'}")

            if report['recommendations']:
                print("\n💡 Recommendations: ")
                for i, rec in enumerate(report['recommendations'], 1):
                    print(f"  {i}. {rec}")
        else:
            print(f"❌ Error generating report: {report['error']}")

        # Save report
        report_file     =   f"optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent    =  2, default    =  str)

        print(f"\n📄 Detailed report saved to: {report_file}")

        # Stop system
        system.stop_system()
        print("\n✅ System stopped successfully")

        return 0

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        system.stop_system()
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("System error")
        system.stop_system()
        return 1

if __name__ == "__main__":
    exit(main())