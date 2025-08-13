# SPDX-License-Identifier: MIT
"""
Production-grade monitoring system integration for OpenCode-Slack.
Integrates all monitoring components: metrics collection, alerting, observability,
health checks, and dashboard into a unified production-ready system.
"""

from .production_alerting_system import ProductionAlertingSystem
from .production_dashboard import ProductionDashboard
from .production_health_checks import ProductionHealthChecker
from .production_metrics_collector import ProductionMetricsCollector
from .production_observability import ProductionObservabilitySystem
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import json
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)


@dataclass
class MonitoringConfiguration:
    """Production monitoring system configuration"""
    metrics_collection_interval: int = 30
    health_check_interval: int = 30
    alert_processing_interval: int = 15
    dashboard_port: int = 8083
    dashboard_host: str = "0.0.0.0"
    auto_recovery_enabled: bool = True
    data_retention_days: int = 30
    enable_dashboard: bool = True
    enable_mobile_dashboard: bool = True
    service_name: str = "opencode-slack"


class ProductionMonitoringSystem:
    """Unified production monitoring system"""

    def __init__(self, agent_manager, task_tracker, session_manager,
                 config: Optional[MonitoringConfiguration] = None):
        """
        Initialize the production monitoring system

        Args:
            agent_manager: Agent manager instance
            task_tracker: Task tracker instance
            session_manager: Session manager instance
            config: Monitoring configuration
        """
        self.agent_manager = agent_manager
        self.task_tracker = task_tracker
        self.session_manager = session_manager
        self.config = config or MonitoringConfiguration()

        # System state
        self.is_running = False
        self.start_time = None

        # Initialize monitoring components
        self._initialize_components()

        # Setup integration
        self._setup_integration()

        logger.info("ProductionMonitoringSystem initialized")

    def _initialize_components(self):
        """Initialize all monitoring components"""
        try:
            # Initialize metrics collector
            self.metrics_collector = ProductionMetricsCollector(
                agent_manager=self.agent_manager,
                task_tracker=self.task_tracker,
                session_manager=self.session_manager,
                collection_interval=self.config.metrics_collection_interval,
                retention_days=self.config.data_retention_days
            )

            # Initialize observability system
            self.observability_system = ProductionObservabilitySystem(
                service_name=self.config.service_name
            )

            # Initialize alerting system
            self.alerting_system = ProductionAlertingSystem(
                metrics_collector=self.metrics_collector
            )

            # Initialize health checker
            self.health_checker = ProductionHealthChecker(
                agent_manager=self.agent_manager,
                task_tracker=self.task_tracker,
                session_manager=self.session_manager,
                check_interval=self.config.health_check_interval
            )

            # Initialize dashboard (if enabled)
            if self.config.enable_dashboard:
                self.dashboard = ProductionDashboard(
                    metrics_collector=self.metrics_collector,
                    alerting_system=self.alerting_system,
                    observability_system=self.observability_system,
                    host=self.config.dashboard_host,
                    port=self.config.dashboard_port
                )
            else:
                self.dashboard = None

            logger.info("All monitoring components initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing monitoring components: {e}")
            raise

    def _setup_integration(self):
        """Setup integration between monitoring components"""
        try:
            # Setup observability decorators for key methods
            self._setup_observability_decorators()

            # Setup alerting callbacks
            self._setup_alerting_callbacks()

            # Setup health check recovery integration
            self._setup_health_check_integration()

            # Setup metrics collection hooks
            self._setup_metrics_hooks()

            logger.info("Monitoring component integration setup complete")

        except Exception as e:
            logger.error(f"Error setting up monitoring integration: {e}")
            raise

    def _setup_observability_decorators(self):
        """Setup observability decorators for key system methods"""
        try:
            # Decorate agent manager methods
            if hasattr(self.agent_manager, 'get_agent_status'):
                original_method = self.agent_manager.get_agent_status
                self.agent_manager.get_agent_status = self.observability_system.observe_operation(
                    'agent_manager.get_agent_status'
                )(original_method)

            # Decorate task tracker methods
            if hasattr(self.task_tracker, 'get_task_progress'):
                original_method = self.task_tracker.get_task_progress
                self.task_tracker.get_task_progress = self.observability_system.observe_operation(
                    'task_tracker.get_task_progress'
                )(original_method)

            # Decorate session manager methods
            if hasattr(self.session_manager, 'start_employee_task'):
                original_method = self.session_manager.start_employee_task
                self.session_manager.start_employee_task = self.observability_system.observe_operation(
                    'session_manager.start_employee_task'
                )(original_method)

            logger.debug("Observability decorators applied")

        except Exception as e:
            logger.error(f"Error setting up observability decorators: {e}")

    def _setup_alerting_callbacks(self):
        """Setup alerting system callbacks"""
        try:
            # Setup escalation callback for health checker
            def health_escalation_callback(component: str, issues: List[str], recovery_record: Dict[str, Any]):
                """Handle health check escalations"""
                logger.warning(f"Health check escalation for {component}: {issues}")

                # Create alert for health issues
                if self.alerting_system:
                    # This would create an alert - simplified for demo
                    pass

            # Setup recovery callback for alerting
            def alert_recovery_callback(agent_name: str, anomalies: List[str], status_record: Dict[str, Any]):
                """Handle alert-triggered recovery"""
                logger.info(f"Alert-triggered recovery for {agent_name}: {anomalies}")

                # Trigger health check recovery if available
                if self.health_checker and self.health_checker.auto_recovery_enabled:
                    for anomaly in anomalies:
                        if anomaly == "STUCK_STATE":
                            self.health_checker.trigger_manual_recovery('restart_stuck_agents')
                        elif anomaly == "PROGRESS_STAGNANT":
                            self.health_checker.trigger_manual_recovery('restart_sessions')

            # Set callbacks
            if hasattr(self.health_checker, 'set_escalation_callback'):
                self.health_checker.set_escalation_callback(health_escalation_callback)

            logger.debug("Alerting callbacks setup complete")

        except Exception as e:
            logger.error(f"Error setting up alerting callbacks: {e}")

    def _setup_health_check_integration(self):
        """Setup health check integration with recovery systems"""
        try:
            # Enable auto recovery if configured
            if self.health_checker:
                self.health_checker.enable_auto_recovery(self.config.auto_recovery_enabled)

            logger.debug("Health check integration setup complete")

        except Exception as e:
            logger.error(f"Error setting up health check integration: {e}")

    def _setup_metrics_hooks(self):
        """Setup metrics collection hooks"""
        try:
            # Hook into agent manager for task assignments
            if hasattr(self.agent_manager, 'create_agent'):
                original_method = self.agent_manager.create_agent

                def hooked_create_agent(*args, **kwargs):
                    result = original_method(*args, **kwargs)
                    # Record agent creation metric
                    if self.metrics_collector:
                        self.metrics_collector.record_task_assignment(f"agent_creation_{int(time.time())}")
                    return result

                self.agent_manager.create_agent = hooked_create_agent

            # Hook into session manager for task completions
            if hasattr(self.session_manager, 'stop_employee_task'):
                original_method = self.session_manager.stop_employee_task

                def hooked_stop_task(*args, **kwargs):
                    try:
                        start_time = time.time()
                        result = original_method(*args, **kwargs)
                        completion_time = (time.time() - start_time) * 1000

                        # Record task completion metric
                        if self.metrics_collector:
                            self.metrics_collector.record_task_completion(
                                f"task_completion_{int(time.time())}",
                                completion_time
                            )
                        return result
                    except Exception as e:
                        # If hook fails, still call original method
                        logger.error(f"Error in monitoring hook: {e}")
                        return original_method(*args, **kwargs)

                self.session_manager.stop_employee_task = hooked_stop_task

            logger.debug("Metrics hooks setup complete")

        except Exception as e:
            logger.error(f"Error setting up metrics hooks: {e}")

    def start(self):
        """Start the production monitoring system"""
        if self.is_running:
            logger.warning("Production monitoring system is already running")
            return

        try:
            self.is_running = True
            self.start_time = datetime.now()

            # Start metrics collection
            self.metrics_collector.start_collection()
            logger.info("✅ Metrics collection started")

            # Start alerting system
            self.alerting_system.start_processing()
            logger.info("✅ Alerting system started")

            # Start health checking
            self.health_checker.start_health_checking()
            logger.info("✅ Health checking started")

            # Start dashboard (if enabled)
            if self.dashboard:
                self.dashboard.start()
                logger.info("✅ Dashboard started")

            # Log startup summary
            self._log_startup_summary()

            logger.info("🚀 Production monitoring system started successfully")

        except Exception as e:
            logger.error(f"Error starting production monitoring system: {e}")
            self.stop()
            raise

    def stop(self):
        """Stop the production monitoring system"""
        if not self.is_running:
            logger.warning("Production monitoring system is not running")
            return

        try:
            logger.info("🛑 Stopping production monitoring system...")

            # Stop dashboard
            if self.dashboard:
                self.dashboard.stop()
                logger.info("✅ Dashboard stopped")

            # Stop health checking
            self.health_checker.stop_health_checking()
            logger.info("✅ Health checking stopped")

            # Stop alerting system
            self.alerting_system.stop_processing()
            logger.info("✅ Alerting system stopped")

            # Stop metrics collection
            self.metrics_collector.stop_collection()
            logger.info("✅ Metrics collection stopped")

            self.is_running = False

            # Log shutdown summary
            self._log_shutdown_summary()

            logger.info("✅ Production monitoring system stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping production monitoring system: {e}")

    def _log_startup_summary(self):
        """Log startup summary"""
        print("\n" + "="*80)
        print("🔍 PRODUCTION MONITORING SYSTEM STARTED")
        print("="*80)
        print(f"📊 Metrics Collection: Every {self.config.metrics_collection_interval}s")
        print(f"🏥 Health Checks: Every {self.config.health_check_interval}s")
        print(f"🚨 Alert Processing: Every {self.config.alert_processing_interval}s")
        print(f"🔄 Auto Recovery: {'Enabled' if self.config.auto_recovery_enabled else 'Disabled'}")
        print(f"📅 Data Retention: {self.config.data_retention_days} days")

        if self.dashboard:
            print(f"🎛️  Dashboard: http://{self.config.dashboard_host}:{self.config.dashboard_port}")
            if self.config.enable_mobile_dashboard:
                print(f"📱 Mobile Dashboard: http://{self.config.dashboard_host}:{self.config.dashboard_port}/mobile")

        print("\n📈 MONITORING CAPABILITIES:")
        print("  • Real-time system metrics (CPU, Memory, Disk, Network)")
        print("  • Business KPIs (Task completion, Agent utilization)")
        print("  • Performance profiling and bottleneck detection")
        print("  • Distributed tracing with correlation IDs")
        print("  • Structured logging with search capabilities")
        print("  • Intelligent alerting with escalation")
        print("  • Deep health checks with auto-recovery")
        print("  • Role-based dashboards (Operations, Executive, Performance)")
        print("  • Mobile-responsive monitoring interface")

        print("\n🔧 RECOVERY ACTIONS AVAILABLE:")
        recovery_actions = list(self.health_checker.recovery_actions.keys())
        for action in recovery_actions:
            print(f"  • {action.replace('_', ' ').title()}")

        print("\n🚨 ALERT RULES CONFIGURED:")
        alert_rules = list(self.alerting_system.alert_rules.keys())
        for rule in alert_rules:
            print(f"  • {rule.replace('_', ' ').title()}")

        print("\n" + "="*80)

    def _log_shutdown_summary(self):
        """Log shutdown summary"""
        if self.start_time:
            uptime = datetime.now() - self.start_time
            print(f"\n📊 Monitoring System Uptime: {uptime}")

        # Get final statistics
        try:
            metrics_summary = self.metrics_collector.get_current_metrics()
            health_summary = self.health_checker.get_overall_health()
            alert_stats = self.alerting_system.get_alerting_statistics()

            print(f"📈 Final Metrics: {len(metrics_summary)} data points collected")
            print(f"🏥 Health Status: {health_summary.get('status', 'unknown').upper()}")
            print(f"🚨 Active Alerts: {alert_stats.get('active_alerts', 0)}")

        except Exception as e:
            logger.debug(f"Error getting shutdown statistics: {e}")

    # Public API methods

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            return {
                'monitoring_system': {
                    'is_running': self.is_running,
                    'start_time': self.start_time.isoformat() if self.start_time else None,
                    'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                    'configuration': {
                        'metrics_collection_interval': self.config.metrics_collection_interval,
                        'health_check_interval': self.config.health_check_interval,
                        'alert_processing_interval': self.config.alert_processing_interval,
                        'dashboard_port': self.config.dashboard_port,
                        'dashboard_host': self.config.dashboard_host,
                        'auto_recovery_enabled': self.config.auto_recovery_enabled,
                        'data_retention_days': self.config.data_retention_days,
                        'enable_dashboard': self.config.enable_dashboard,
                        'enable_mobile_dashboard': self.config.enable_mobile_dashboard,
                        'service_name': self.config.service_name
                    }
                },
                'metrics': self.metrics_collector.get_current_metrics(),
                'health': self.health_checker.get_overall_health(),
                'alerts': {
                    'active_alerts': self.alerting_system.get_active_alerts(),
                    'statistics': self.alerting_system.get_alerting_statistics()
                },
                'observability': self.observability_system.get_system_health(),
                'dashboard_url': f"http://{self.config.dashboard_host}:{self.config.dashboard_port}" if self.dashboard else None
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary"""
        try:
            return {
                'metrics_summary': self.metrics_collector.get_metrics_summary(hours),
                'performance_profiles': self.observability_system.profiler.get_performance_summary(hours),
                'health_trends': self._get_health_trends(hours),
                'alert_trends': self._get_alert_trends(hours)
            }
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {'error': str(e)}

    def _get_health_trends(self, hours: int) -> Dict[str, Any]:
        """Get health trends over time"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Count health check results by status over time
            health_trends = {
                'healthy': 0,
                'degraded': 0,
                'unhealthy': 0,
                'critical': 0
            }

            for result in self.health_checker.health_history:
                if result.timestamp >= cutoff_time:
                    status = result.status.value
                    if status in health_trends:
                        health_trends[status] += 1

            return health_trends
        except Exception as e:
            logger.error(f"Error getting health trends: {e}")
            return {}

    def _get_alert_trends(self, hours: int) -> Dict[str, Any]:
        """Get alert trends over time"""
        try:
            alert_history = self.alerting_system.get_alert_history(hours)

            # Count alerts by severity
            alert_trends = {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'info': 0
            }

            for alert in alert_history:
                severity = alert.get('severity', 'info')
                if severity in alert_trends:
                    alert_trends[severity] += 1

            return alert_trends
        except Exception as e:
            logger.error(f"Error getting alert trends: {e}")
            return {}

    def trigger_health_check(self) -> Dict[str, Any]:
        """Trigger immediate health check"""
        try:
            return self.health_checker.force_health_check()
        except Exception as e:
            logger.error(f"Error triggering health check: {e}")
            return {'error': str(e)}

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            return self.alerting_system.acknowledge_alert(alert_id, acknowledged_by)
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False

    def trigger_recovery_action(self, action_name: str) -> bool:
        """Trigger manual recovery action"""
        try:
            return self.health_checker.trigger_manual_recovery(action_name)
        except Exception as e:
            logger.error(f"Error triggering recovery action {action_name}: {e}")
            return False

    def get_observability_data(self, correlation_id: Optional[str] = None,
                              trace_id: Optional[str] = None,
                              hours: int = 24) -> Dict[str, Any]:
        """Get observability data"""
        try:
            return self.observability_system.get_observability_data(
                correlation_id=correlation_id,
                trace_id=trace_id,
                hours=hours
            )
        except Exception as e:
            logger.error(f"Error getting observability data: {e}")
            return {'error': str(e)}

    def update_configuration(self, new_config: MonitoringConfiguration):
        """Update monitoring configuration"""
        try:
            old_config = self.config
            self.config = new_config

            # Apply configuration changes
            if old_config.auto_recovery_enabled != new_config.auto_recovery_enabled:
                self.health_checker.enable_auto_recovery(new_config.auto_recovery_enabled)

            logger.info("Monitoring configuration updated")
            return True

        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False

    def export_monitoring_data(self, format: str = 'json', hours: int = 24) -> str:
        """Export monitoring data"""
        try:
            data = {
                'export_timestamp': datetime.now().isoformat(),
                'export_format': format,
                'time_range_hours': hours,
                'system_status': self.get_system_status(),
                'performance_summary': self.get_performance_summary(hours),
                'metrics_history': self.metrics_collector.get_metrics_history(hours),
                'alert_history': self.alerting_system.get_alert_history(hours),
                'recovery_history': self.health_checker.get_recovery_history(hours)
            }

            if format.lower() == 'json':
                return json.dumps(data, indent=2, default=str)
            else:
                return str(data)

        except Exception as e:
            logger.error(f"Error exporting monitoring data: {e}")
            return f"Error: {str(e)}"

    def get_monitoring_recommendations(self) -> List[str]:
        """Get monitoring system recommendations"""
        recommendations = []

        try:
            # Check system health
            health_status = self.health_checker.get_overall_health()
            if health_status['status'] != 'healthy':
                recommendations.append("Review and address system health issues")

            # Check alert volume
            alert_stats = self.alerting_system.get_alerting_statistics()
            if alert_stats.get('active_alerts', 0) > 10:
                recommendations.append("High number of active alerts - review alert thresholds")

            # Check performance
            observability_health = self.observability_system.get_system_health()
            if observability_health['health_score'] < 80:
                recommendations.extend(observability_health.get('recommendations', []))

            # Check configuration
            if not self.config.auto_recovery_enabled:
                recommendations.append("Consider enabling auto-recovery for faster issue resolution")

            if self.config.metrics_collection_interval > 60:
                recommendations.append("Consider reducing metrics collection interval for better visibility")

            if not recommendations:
                recommendations.append("Monitoring system is performing well - continue current practices")

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Error generating recommendations - check system logs")

        return recommendations