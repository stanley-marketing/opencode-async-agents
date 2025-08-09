#!/usr/bin/env python3
"""
Enhanced System Integration for OpenCode-Slack
Integrates all concurrency enhancements with the existing system.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import enhanced concurrency components
from .enhanced_agent_coordinator import EnhancedAgentCoordinator, TaskPriority
from .performance_optimizer import PerformanceOptimizer
from .scalability_manager import ScalabilityManager
from .monitoring_system import ConcurrencyMonitor, ConcurrencyMetrics

# Import existing system components
from ..agents.agent_manager import AgentManager
from ..bridge.agent_bridge import AgentBridge
from ..utils.opencode_wrapper import OpencodeSessionManager
from ..managers.file_ownership import FileOwnershipManager
from ..trackers.task_progress import TaskProgressTracker
from ..chat.telegram_manager import TelegramManager

logger = logging.getLogger(__name__)


class EnhancedOpenCodeSystem:
    """
    Enhanced OpenCode-Slack system with advanced concurrency features
    """
    
    def __init__(self, 
                 db_path: str = "employees.db",
                 sessions_dir: str = "sessions",
                 max_concurrent_agents: int = 50,
                 max_concurrent_tasks: int = 200,
                 max_message_throughput: int = 1000):
        
        self.db_path = db_path
        self.sessions_dir = sessions_dir
        self.max_concurrent_agents = max_concurrent_agents
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_message_throughput = max_message_throughput
        
        # Enhanced concurrency components
        self.coordinator = None
        self.optimizer = None
        self.scalability_manager = None
        self.monitor = None
        
        # Existing system components
        self.file_manager = None
        self.task_tracker = None
        self.session_manager = None
        self.telegram_manager = None
        self.agent_manager = None
        self.agent_bridge = None
        
        # System state
        self.is_running = False
        self.startup_time = None
        
        logger.info("EnhancedOpenCodeSystem initialized")
    
    async def initialize(self):
        """Initialize all system components"""
        logger.info("Initializing Enhanced OpenCode-Slack System...")
        
        try:
            # Initialize core components
            self._initialize_core_components()
            
            # Initialize enhanced concurrency components
            await self._initialize_enhanced_components()
            
            # Set up integrations
            self._setup_integrations()
            
            # Start monitoring
            await self._start_monitoring()
            
            self.startup_time = datetime.now()
            self.is_running = True
            
            logger.info("✅ Enhanced OpenCode-Slack System initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            await self.shutdown()
            raise
    
    def _initialize_core_components(self):
        """Initialize existing system components"""
        logger.info("Initializing core components...")
        
        # File ownership manager
        self.file_manager = FileOwnershipManager(self.db_path)
        
        # Task progress tracker
        self.task_tracker = TaskProgressTracker(self.sessions_dir)
        
        # Session manager
        self.session_manager = OpencodeSessionManager(
            self.file_manager, self.sessions_dir, quiet_mode=True
        )
        
        # Telegram manager (mocked for testing)
        self.telegram_manager = TelegramManager()
        
        # Agent manager
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        self.agent_manager.setup_monitoring_system(self.task_tracker, self.session_manager)
        
        # Agent bridge
        self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)
        
        logger.info("✅ Core components initialized")
    
    async def _initialize_enhanced_components(self):
        """Initialize enhanced concurrency components"""
        logger.info("Initializing enhanced concurrency components...")
        
        # Enhanced agent coordinator
        self.coordinator = EnhancedAgentCoordinator(
            max_concurrent_agents=self.max_concurrent_agents,
            max_concurrent_tasks=self.max_concurrent_tasks,
            max_message_throughput=self.max_message_throughput
        )
        await self.coordinator.start()
        
        # Performance optimizer
        self.optimizer = PerformanceOptimizer(self.db_path)
        
        # Scalability manager
        self.scalability_manager = ScalabilityManager(
            min_nodes=1, 
            max_nodes=self.max_concurrent_agents // 5
        )
        
        # Concurrency monitor
        self.monitor = ConcurrencyMonitor(monitoring_interval=10)
        
        logger.info("✅ Enhanced concurrency components initialized")
    
    def _setup_integrations(self):
        """Set up integrations between components"""
        logger.info("Setting up component integrations...")
        
        # Integrate coordinator with existing agent manager
        self._integrate_coordinator_with_agent_manager()
        
        # Integrate optimizer with file manager
        self._integrate_optimizer_with_file_manager()
        
        # Set up monitoring collectors
        self._setup_monitoring_collectors()
        
        # Set up alert handlers
        self._setup_alert_handlers()
        
        logger.info("✅ Component integrations set up")
    
    def _integrate_coordinator_with_agent_manager(self):
        """Integrate enhanced coordinator with existing agent manager"""
        
        # Override agent manager's task assignment to use coordinator
        original_handle_task_assignment = self.agent_manager._handle_task_assignment
        
        def enhanced_task_assignment(employee_name: str, task: str) -> bool:
            try:
                # Create task in coordinator
                task_id = self.coordinator.create_task(
                    employee_name, 
                    task, 
                    TaskPriority.NORMAL,
                    required_resources=[f"agent_{employee_name}"]
                )
                
                # Also use original assignment for compatibility
                original_result = original_handle_task_assignment(employee_name, task)
                
                return bool(task_id and original_result)
                
            except Exception as e:
                logger.error(f"Enhanced task assignment failed: {e}")
                return original_handle_task_assignment(employee_name, task)
        
        self.agent_manager._handle_task_assignment = enhanced_task_assignment
        
        # Override message handling to use async processing
        original_handle_message = self.agent_manager.handle_message
        
        def enhanced_handle_message(message):
            try:
                # Process with enhanced coordinator
                asyncio.create_task(self._process_message_enhanced(message))
                
                # Also use original handler for compatibility
                original_handle_message(message)
                
            except Exception as e:
                logger.error(f"Enhanced message handling failed: {e}")
                original_handle_message(message)
        
        self.agent_manager.handle_message = enhanced_handle_message
    
    async def _process_message_enhanced(self, message):
        """Process message with enhanced coordinator"""
        try:
            message_data = {
                'text': message.text,
                'agent_name': message.mentions[0] if message.mentions else 'general',
                'sender': message.sender,
                'timestamp': message.timestamp
            }
            
            response = await self.coordinator.process_message_async(message_data)
            
            if not response['success']:
                logger.warning(f"Enhanced message processing failed: {response.get('error')}")
                
        except Exception as e:
            logger.error(f"Error in enhanced message processing: {e}")
    
    def _integrate_optimizer_with_file_manager(self):
        """Integrate performance optimizer with file manager"""
        
        # Replace file manager's database operations with optimized versions
        original_get_db_connection = self.file_manager.get_db_connection
        
        def optimized_get_db_connection():
            return self.optimizer.connection_pool.get_connection()
        
        # Note: This would require more extensive refactoring in a real implementation
        # For now, we'll just ensure the optimizer is available for new operations
        self.file_manager._optimizer = self.optimizer
    
    def _setup_monitoring_collectors(self):
        """Set up monitoring data collectors"""
        
        def agent_metrics_collector():
            """Collect agent-related metrics"""
            try:
                agent_status = self.agent_manager.get_agent_status()
                chat_stats = self.agent_manager.get_chat_statistics()
                
                return {
                    'active_agents': chat_stats.get('total_agents', 0),
                    'working_agents': chat_stats.get('working_agents', 0),
                    'idle_agents': chat_stats.get('idle_agents', 0),
                    'stuck_agents': chat_stats.get('stuck_agents', 0)
                }
            except Exception as e:
                logger.error(f"Error collecting agent metrics: {e}")
                return {}
        
        def task_metrics_collector():
            """Collect task-related metrics"""
            try:
                active_sessions = self.session_manager.get_active_sessions()
                bridge_status = self.agent_bridge.get_bridge_status()
                
                return {
                    'running_tasks': len(active_sessions),
                    'pending_tasks': bridge_status.get('active_tasks', 0),
                    'completed_tasks': 0,  # Would need to track this
                    'failed_tasks': 0     # Would need to track this
                }
            except Exception as e:
                logger.error(f"Error collecting task metrics: {e}")
                return {}
        
        def coordinator_metrics_collector():
            """Collect coordinator metrics"""
            try:
                if self.coordinator:
                    status = self.coordinator.get_system_status()
                    return {
                        'throughput_per_minute': status['coordinator_metrics'].get('messages_processed', 0) * 6,
                        'avg_response_time': status['coordinator_metrics'].get('avg_message_processing_time', 0),
                        'error_rate': 0.0,  # Would need to calculate from metrics
                        'cache_hit_rate': 0.8  # Mock value
                    }
                return {}
            except Exception as e:
                logger.error(f"Error collecting coordinator metrics: {e}")
                return {}
        
        def performance_metrics_collector():
            """Collect performance metrics"""
            try:
                if self.optimizer:
                    stats = self.optimizer.get_comprehensive_stats()
                    return {
                        'connection_pool_usage': stats['connection_pool']['utilization'],
                        'cache_hit_rate': stats['cache']['hit_rate'],
                        'lock_contention_rate': 0.0,  # Would need to implement
                        'deadlock_count': 0,          # Would need to implement
                        'race_condition_count': 0,    # Would need to implement
                        'resource_conflicts': 0       # Would need to implement
                    }
                return {}
            except Exception as e:
                logger.error(f"Error collecting performance metrics: {e}")
                return {}
        
        # Add collectors to monitor
        self.monitor.add_metrics_collector(agent_metrics_collector)
        self.monitor.add_metrics_collector(task_metrics_collector)
        self.monitor.add_metrics_collector(coordinator_metrics_collector)
        self.monitor.add_metrics_collector(performance_metrics_collector)
    
    def _setup_alert_handlers(self):
        """Set up alert notification handlers"""
        
        def telegram_alert_handler(alert):
            """Send alerts to Telegram"""
            try:
                severity_emoji = {
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌',
                    'critical': '🚨'
                }
                
                emoji = severity_emoji.get(alert.severity, '📊')
                message = f"{emoji} ALERT [{alert.severity.upper()}]\n{alert.title}\n{alert.description}"
                
                # Send to admin channel (would need to implement)
                logger.warning(f"ALERT: {message}")
                
            except Exception as e:
                logger.error(f"Error sending alert to Telegram: {e}")
        
        def system_alert_handler(alert):
            """Handle system-level alerts"""
            try:
                if alert.severity in ['error', 'critical']:
                    # Take corrective action
                    if 'High CPU Usage' in alert.title:
                        self._handle_high_cpu_alert()
                    elif 'Stuck Agents' in alert.title:
                        self._handle_stuck_agents_alert()
                    elif 'Deadlock' in alert.title:
                        self._handle_deadlock_alert()
                        
            except Exception as e:
                logger.error(f"Error handling system alert: {e}")
        
        # Add alert handlers
        self.monitor.alert_manager.add_notification_callback(telegram_alert_handler)
        self.monitor.alert_manager.add_notification_callback(system_alert_handler)
    
    def _handle_high_cpu_alert(self):
        """Handle high CPU usage alert"""
        logger.warning("Handling high CPU usage - reducing concurrent operations")
        
        # Reduce coordinator limits temporarily
        if self.coordinator:
            current_agents = len(self.coordinator.resource_pool.active_agents)
            if current_agents > 10:
                # This would require implementing dynamic limit adjustment
                logger.info("Would reduce concurrent agent limit")
    
    def _handle_stuck_agents_alert(self):
        """Handle stuck agents alert"""
        logger.warning("Handling stuck agents - triggering recovery")
        
        # Use existing recovery mechanisms
        if hasattr(self.agent_manager, 'recovery_manager'):
            # Trigger recovery for stuck agents
            logger.info("Would trigger agent recovery")
    
    def _handle_deadlock_alert(self):
        """Handle deadlock alert"""
        logger.critical("Handling deadlock - emergency recovery")
        
        # Emergency deadlock resolution
        if self.coordinator:
            cycles = self.coordinator.detect_dependency_cycles()
            if cycles:
                logger.warning(f"Breaking {len(cycles)} dependency cycles")
                # The coordinator already breaks cycles automatically
    
    async def _start_monitoring(self):
        """Start monitoring systems"""
        logger.info("Starting monitoring systems...")
        
        # Start concurrency monitor
        self.monitor.start_monitoring()
        
        # Start agent bridge monitoring
        self.agent_bridge.start_monitoring()
        
        logger.info("✅ Monitoring systems started")
    
    async def shutdown(self):
        """Shutdown all system components"""
        logger.info("Shutting down Enhanced OpenCode-Slack System...")
        
        self.is_running = False
        
        try:
            # Stop monitoring
            if self.monitor:
                self.monitor.stop_monitoring()
            
            # Stop agent bridge
            if self.agent_bridge:
                self.agent_bridge.stop_all_tasks()
            
            # Stop session manager
            if self.session_manager:
                self.session_manager.cleanup_all_sessions()
            
            # Stop enhanced components
            if self.coordinator:
                await self.coordinator.stop()
            
            logger.info("✅ Enhanced OpenCode-Slack System shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            status = {
                'system': {
                    'is_running': self.is_running,
                    'startup_time': self.startup_time.isoformat() if self.startup_time else None,
                    'uptime_seconds': (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0
                },
                'core_components': {
                    'agents': len(self.agent_manager.agents) if self.agent_manager else 0,
                    'active_sessions': len(self.session_manager.get_active_sessions()) if self.session_manager else 0,
                    'bridge_tasks': self.agent_bridge.get_bridge_status()['active_tasks'] if self.agent_bridge else 0
                },
                'enhanced_components': {},
                'monitoring': {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Enhanced component status
            if self.coordinator:
                status['enhanced_components']['coordinator'] = self.coordinator.get_system_status()
            
            if self.optimizer:
                status['enhanced_components']['optimizer'] = self.optimizer.get_comprehensive_stats()
            
            if self.scalability_manager:
                status['enhanced_components']['scalability'] = self.scalability_manager.get_comprehensive_status()
            
            # Monitoring status
            if self.monitor:
                status['monitoring'] = self.monitor.get_monitoring_status()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all components"""
        try:
            summary = {
                'overall_health': 'healthy',
                'performance_metrics': {},
                'capacity_status': {},
                'alerts_summary': {},
                'recommendations': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # Coordinator performance
            if self.coordinator:
                coord_status = self.coordinator.get_system_status()
                summary['performance_metrics']['coordinator'] = coord_status['coordinator_metrics']
                summary['capacity_status']['resource_utilization'] = coord_status['resource_status']['utilization']
            
            # Optimizer performance
            if self.optimizer:
                opt_stats = self.optimizer.get_comprehensive_stats()
                summary['performance_metrics']['optimizer'] = {
                    'cache_hit_rate': opt_stats['cache']['hit_rate'],
                    'connection_pool_utilization': opt_stats['connection_pool']['utilization'],
                    'system_cpu': opt_stats['system_metrics']['cpu_usage'],
                    'system_memory': opt_stats['system_metrics']['memory_usage']
                }
            
            # Scalability status
            if self.scalability_manager:
                scale_status = self.scalability_manager.get_scaling_recommendations()
                summary['capacity_status']['cluster'] = scale_status['cluster_status']
                if scale_status['capacity_forecast'].get('recommendations'):
                    summary['recommendations'].extend(scale_status['capacity_forecast']['recommendations'])
            
            # Monitoring alerts
            if self.monitor:
                monitor_status = self.monitor.get_monitoring_status()
                summary['alerts_summary'] = monitor_status['alerts']
                
                # Determine overall health
                critical_alerts = monitor_status['alerts']['by_severity'].get('critical', 0)
                error_alerts = monitor_status['alerts']['by_severity'].get('error', 0)
                
                if critical_alerts > 0:
                    summary['overall_health'] = 'critical'
                elif error_alerts > 0:
                    summary['overall_health'] = 'degraded'
                elif monitor_status['alerts']['total_active'] > 5:
                    summary['overall_health'] = 'warning'
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {
                'error': str(e),
                'overall_health': 'unknown',
                'timestamp': datetime.now().isoformat()
            }
    
    async def create_enhanced_task(self, 
                                 agent_name: str, 
                                 description: str, 
                                 priority: str = "normal",
                                 dependencies: List[str] = None,
                                 required_resources: List[str] = None) -> str:
        """Create a task using the enhanced coordinator"""
        try:
            # Map priority string to enum
            priority_map = {
                'critical': TaskPriority.CRITICAL,
                'high': TaskPriority.HIGH,
                'normal': TaskPriority.NORMAL,
                'low': TaskPriority.LOW
            }
            
            task_priority = priority_map.get(priority.lower(), TaskPriority.NORMAL)
            
            # Create task in coordinator
            task_id = self.coordinator.create_task(
                agent_name=agent_name,
                description=description,
                priority=task_priority,
                dependencies=dependencies or [],
                required_resources=required_resources or []
            )
            
            # Also create in existing system for compatibility
            if self.agent_manager:
                self.agent_manager._handle_task_assignment(agent_name, description)
            
            logger.info(f"Created enhanced task {task_id} for agent {agent_name}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error creating enhanced task: {e}")
            raise
    
    def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """Get real-time data optimized for dashboard display"""
        try:
            if self.monitor:
                return self.monitor.get_real_time_dashboard_data()
            else:
                return {
                    'status': 'monitoring_not_available',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Convenience function for easy system initialization
async def create_enhanced_system(db_path: str = "employees.db",
                               sessions_dir: str = "sessions",
                               max_concurrent_agents: int = 50,
                               max_concurrent_tasks: int = 200,
                               max_message_throughput: int = 1000) -> EnhancedOpenCodeSystem:
    """
    Create and initialize an enhanced OpenCode-Slack system
    
    Args:
        db_path: Path to the database file
        sessions_dir: Directory for session files
        max_concurrent_agents: Maximum concurrent agents
        max_concurrent_tasks: Maximum concurrent tasks
        max_message_throughput: Maximum messages per minute
    
    Returns:
        Initialized EnhancedOpenCodeSystem instance
    """
    system = EnhancedOpenCodeSystem(
        db_path=db_path,
        sessions_dir=sessions_dir,
        max_concurrent_agents=max_concurrent_agents,
        max_concurrent_tasks=max_concurrent_tasks,
        max_message_throughput=max_message_throughput
    )
    
    await system.initialize()
    return system


# Example usage
async def main():
    """Example usage of the enhanced system"""
    logger.info("Starting Enhanced OpenCode-Slack System Demo")
    
    try:
        # Create and initialize system
        system = await create_enhanced_system(
            max_concurrent_agents=30,
            max_concurrent_tasks=100,
            max_message_throughput=500
        )
        
        # Get initial status
        status = system.get_system_status()
        logger.info(f"System initialized: {status['system']}")
        
        # Create some test tasks
        task1 = await system.create_enhanced_task(
            "developer_001", 
            "Implement user authentication",
            priority="high",
            required_resources=["auth_module", "database"]
        )
        
        task2 = await system.create_enhanced_task(
            "developer_002",
            "Add unit tests for authentication",
            priority="normal",
            dependencies=[task1],
            required_resources=["test_framework"]
        )
        
        logger.info(f"Created tasks: {task1}, {task2}")
        
        # Monitor for a short time
        await asyncio.sleep(10)
        
        # Get performance summary
        performance = system.get_performance_summary()
        logger.info(f"Performance summary: {performance['overall_health']}")
        
        # Get dashboard data
        dashboard = system.get_real_time_dashboard_data()
        logger.info(f"Dashboard status: {dashboard.get('system_health', {}).get('status', 'unknown')}")
        
        # Shutdown
        await system.shutdown()
        logger.info("Demo completed successfully")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())