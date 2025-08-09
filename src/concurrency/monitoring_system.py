#!/usr/bin/env python3
"""
Advanced Monitoring System for OpenCode-Slack Concurrency
Implements real-time monitoring, alerting, and performance analytics.
"""

from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from queue import Queue, Empty
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
import asyncio
import json
import logging
import os
import psutil
import socket
import statistics
import threading
import time
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyMetrics:
    """Comprehensive concurrency metrics"""
    timestamp: datetime = field(default_factory=datetime.now)

    # Agent metrics
    active_agents: int = 0
    idle_agents: int = 0
    working_agents: int = 0
    stuck_agents: int = 0

    # Task metrics
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0

    # Performance metrics
    avg_task_duration: float = 0.0
    avg_response_time: float = 0.0
    throughput_per_minute: float = 0.0
    error_rate: float = 0.0

    # Resource metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    thread_count: int = 0
    connection_pool_usage: float = 0.0
    cache_hit_rate: float = 0.0

    # Concurrency metrics
    lock_contention_rate: float = 0.0
    deadlock_count: int = 0
    race_condition_count: int = 0
    resource_conflicts: int = 0


@dataclass
class Alert:
    """Alert definition"""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    severity: str = "info"  # info, warning, error, critical
    category: str = "general"
    title: str = ""
    description: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False


class AlertManager:
    """Manages alerts and notifications"""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_history = deque(maxlen=1000)
        self.notification_callbacks: List[Callable] = []
        self.lock = threading.RLock()

        # Default alert rules
        self._setup_default_alert_rules()

        logger.info("AlertManager initialized")

    def _setup_default_alert_rules(self):
        """Setup default alerting rules"""
        self.alert_rules = [
            {
                'name': 'high_cpu_usage',
                'condition': lambda m: m.cpu_usage > 90,
                'severity': 'critical',
                'category': 'performance',
                'title': 'High CPU Usage',
                'description': 'CPU usage is above 90%'
            },
            {
                'name': 'high_memory_usage',
                'condition': lambda m: m.memory_usage > 85,
                'severity': 'warning',
                'category': 'performance',
                'title': 'High Memory Usage',
                'description': 'Memory usage is above 85%'
            },
            {
                'name': 'stuck_agents',
                'condition': lambda m: m.stuck_agents > 0,
                'severity': 'error',
                'category': 'agents',
                'title': 'Stuck Agents Detected',
                'description': 'One or more agents are stuck'
            },
            {
                'name': 'high_error_rate',
                'condition': lambda m: m.error_rate > 0.1,
                'severity': 'error',
                'category': 'reliability',
                'title': 'High Error Rate',
                'description': 'Error rate is above 10%'
            },
            {
                'name': 'low_throughput',
                'condition': lambda m: m.throughput_per_minute < 10,
                'severity': 'warning',
                'category': 'performance',
                'title': 'Low Throughput',
                'description': 'Throughput is below 10 tasks/minute'
            },
            {
                'name': 'deadlock_detected',
                'condition': lambda m: m.deadlock_count > 0,
                'severity': 'critical',
                'category': 'concurrency',
                'title': 'Deadlock Detected',
                'description': 'Deadlock condition detected'
            },
            {
                'name': 'high_lock_contention',
                'condition': lambda m: m.lock_contention_rate > 0.5,
                'severity': 'warning',
                'category': 'concurrency',
                'title': 'High Lock Contention',
                'description': 'Lock contention rate is above 50%'
            }
        ]

    def evaluate_alerts(self, metrics: ConcurrencyMetrics):
        """Evaluate alert rules against current metrics"""
        with self.lock:
            for rule in self.alert_rules:
                try:
                    if rule['condition'](metrics):
                        self._trigger_alert(rule, metrics)
                    else:
                        self._resolve_alert(rule['name'])
                except Exception as e:
                    logger.error(f"Error evaluating alert rule {rule['name']}: {e}")

    def _trigger_alert(self, rule: Dict[str, Any], metrics: ConcurrencyMetrics):
        """Trigger an alert"""
        alert_key = rule['name']

        # Check if alert already exists and is not resolved
        if alert_key in self.alerts and not self.alerts[alert_key].resolved:
            return  # Don't create duplicate alerts

        alert = Alert(
            severity=rule['severity'],
            category=rule['category'],
            title=rule['title'],
            description=rule['description'],
            metrics=asdict(metrics)
        )

        self.alerts[alert_key] = alert
        self.alert_history.append(alert)

        # Notify callbacks
        for callback in self.notification_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert notification callback: {e}")

        logger.warning(f"Alert triggered: {alert.title} - {alert.description}")

    def _resolve_alert(self, alert_key: str):
        """Resolve an alert"""
        if alert_key in self.alerts and not self.alerts[alert_key].resolved:
            self.alerts[alert_key].resolved = True
            logger.info(f"Alert resolved: {alert_key}")

    def add_notification_callback(self, callback: Callable[[Alert], None]):
        """Add a notification callback"""
        self.notification_callbacks.append(callback)

    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        with self.lock:
            for alert in self.alerts.values():
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    logger.info(f"Alert acknowledged: {alert_id}")
                    break

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts"""
        with self.lock:
            return [alert for alert in self.alerts.values() if not alert.resolved]

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics"""
        with self.lock:
            active_alerts = self.get_active_alerts()

            severity_counts = defaultdict(int)
            category_counts = defaultdict(int)

            for alert in active_alerts:
                severity_counts[alert.severity] += 1
                category_counts[alert.category] += 1

            return {
                'total_active': len(active_alerts),
                'by_severity': dict(severity_counts),
                'by_category': dict(category_counts),
                'total_history': len(self.alert_history),
                'last_updated': datetime.now().isoformat()
            }


class PerformanceAnalyzer:
    """Analyzes performance trends and patterns"""

    def __init__(self, history_size: int = 10000):
        self.metrics_history = deque(maxlen=history_size)
        self.analysis_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.lock = threading.RLock()

        logger.info(f"PerformanceAnalyzer initialized with {history_size} history size")

    def record_metrics(self, metrics: ConcurrencyMetrics):
        """Record metrics for analysis"""
        with self.lock:
            self.metrics_history.append(metrics)
            # Clear cache when new data arrives
            self.analysis_cache.clear()

    def analyze_trends(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Analyze performance trends over a time window"""
        cache_key = f"trends_{window_minutes}"

        with self.lock:
            # Check cache
            if cache_key in self.analysis_cache:
                cached_result, timestamp = self.analysis_cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    return cached_result

            # Calculate trends
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            recent_metrics = [
                m for m in self.metrics_history
                if m.timestamp >= cutoff_time
            ]

            if len(recent_metrics) < 2:
                return {'status': 'insufficient_data'}

            trends = self._calculate_trends(recent_metrics)

            # Cache result
            self.analysis_cache[cache_key] = (trends, time.time())

            return trends

    def _calculate_trends(self, metrics: List[ConcurrencyMetrics]) -> Dict[str, Any]:
        """Calculate trends for various metrics"""
        if len(metrics) < 2:
            return {}

        # Extract time series data
        timestamps = [(m.timestamp - metrics[0].timestamp).total_seconds() for m in metrics]

        trends = {}

        # Analyze key metrics
        metric_fields = [
            'cpu_usage', 'memory_usage', 'throughput_per_minute',
            'avg_response_time', 'error_rate', 'active_agents'
        ]

        for field in metric_fields:
            values = [getattr(m, field) for m in metrics]
            trend = self._calculate_linear_trend(timestamps, values)
            trends[field] = trend

        # Overall system health trend
        health_scores = []
        for m in metrics:
            # Simple health score calculation
            score = 100
            score -= min(m.cpu_usage, 50)  # Penalize high CPU
            score -= min(m.memory_usage, 30)  # Penalize high memory
            score -= m.error_rate * 100  # Penalize errors
            score -= m.stuck_agents * 10  # Penalize stuck agents
            health_scores.append(max(score, 0))

        trends['system_health'] = self._calculate_linear_trend(timestamps, health_scores)

        return {
            'trends': trends,
            'analysis_period': {
                'start': metrics[0].timestamp.isoformat(),
                'end': metrics[-1].timestamp.isoformat(),
                'sample_count': len(metrics)
            },
            'summary': self._generate_trend_summary(trends)
        }

    def _calculate_linear_trend(self, x_values: List[float], y_values: List[float]) -> Dict[str, float]:
        """Calculate linear trend (slope) for a series"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return {'slope': 0.0, 'direction': 'stable', 'confidence': 0.0}

        n = len(x_values)
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)

        # Calculate slope
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        # Determine direction
        if abs(slope) < 0.01:
            direction = 'stable'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'

        # Calculate confidence (R-squared)
        if len(y_values) > 1:
            y_variance = statistics.variance(y_values)
            if y_variance > 0:
                predicted_values = [y_mean + slope * (x - x_mean) for x in x_values]
                residual_variance = statistics.variance([
                    y_values[i] - predicted_values[i] for i in range(n)
                ])
                confidence = 1 - (residual_variance / y_variance)
            else:
                confidence = 1.0
        else:
            confidence = 0.0

        return {
            'slope': slope,
            'direction': direction,
            'confidence': max(0.0, min(1.0, confidence))
        }

    def _generate_trend_summary(self, trends: Dict[str, Any]) -> Dict[str, str]:
        """Generate human-readable trend summary"""
        summary = {}

        for metric, trend_data in trends.items():
            direction = trend_data.get('direction', 'stable')
            confidence = trend_data.get('confidence', 0.0)

            if confidence > 0.7:
                confidence_text = "strong"
            elif confidence > 0.4:
                confidence_text = "moderate"
            else:
                confidence_text = "weak"

            summary[metric] = f"{confidence_text} {direction} trend"

        return summary

    def detect_anomalies(self, window_minutes: int = 30) -> List[Dict[str, Any]]:
        """Detect performance anomalies"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            recent_metrics = [
                m for m in self.metrics_history
                if m.timestamp >= cutoff_time
            ]

            if len(recent_metrics) < 10:
                return []

            anomalies = []

            # Check for sudden spikes or drops
            for field in ['cpu_usage', 'memory_usage', 'error_rate', 'avg_response_time']:
                values = [getattr(m, field) for m in recent_metrics]
                anomalies.extend(self._detect_field_anomalies(field, values, recent_metrics))

            return anomalies

    def _detect_field_anomalies(self, field: str, values: List[float],
                               metrics: List[ConcurrencyMetrics]) -> List[Dict[str, Any]]:
        """Detect anomalies in a specific field"""
        if len(values) < 10:
            return []

        anomalies = []

        # Calculate baseline statistics
        baseline_values = values[:-5]  # Use all but last 5 values as baseline
        recent_values = values[-5:]    # Last 5 values

        if len(baseline_values) < 5:
            return []

        baseline_mean = statistics.mean(baseline_values)
        baseline_std = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0

        # Detect anomalies in recent values
        for i, value in enumerate(recent_values):
            if baseline_std > 0:
                z_score = abs(value - baseline_mean) / baseline_std

                if z_score > 3:  # 3 sigma rule
                    anomaly_type = 'spike' if value > baseline_mean else 'drop'
                    anomalies.append({
                        'field': field,
                        'type': anomaly_type,
                        'value': value,
                        'baseline_mean': baseline_mean,
                        'z_score': z_score,
                        'timestamp': metrics[-(5-i)].timestamp.isoformat(),
                        'severity': 'high' if z_score > 4 else 'medium'
                    })

        return anomalies

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        with self.lock:
            if not self.metrics_history:
                return {'status': 'no_data'}

            latest_metrics = self.metrics_history[-1]
            trends = self.analyze_trends(60)  # 1 hour trends
            anomalies = self.detect_anomalies(30)  # 30 minute anomaly window

            # Calculate averages over different time windows
            windows = [5, 15, 60]  # minutes
            averages = {}

            for window in windows:
                cutoff_time = datetime.now() - timedelta(minutes=window)
                window_metrics = [
                    m for m in self.metrics_history
                    if m.timestamp >= cutoff_time
                ]

                if window_metrics:
                    averages[f'{window}min'] = {
                        'cpu_usage': statistics.mean(m.cpu_usage for m in window_metrics),
                        'memory_usage': statistics.mean(m.memory_usage for m in window_metrics),
                        'throughput': statistics.mean(m.throughput_per_minute for m in window_metrics),
                        'error_rate': statistics.mean(m.error_rate for m in window_metrics),
                        'response_time': statistics.mean(m.avg_response_time for m in window_metrics)
                    }

            return {
                'current_metrics': asdict(latest_metrics),
                'averages': averages,
                'trends': trends,
                'anomalies': anomalies,
                'data_points': len(self.metrics_history),
                'analysis_timestamp': datetime.now().isoformat()
            }


class ConcurrencyMonitor:
    """Main concurrency monitoring system"""

    def __init__(self, monitoring_interval: int = 10):
        self.monitoring_interval = monitoring_interval
        self.is_running = False

        # Core components
        self.alert_manager = AlertManager()
        self.performance_analyzer = PerformanceAnalyzer()

        # Monitoring thread
        self.monitor_thread = None

        # Metrics collection
        self.metrics_collectors: List[Callable[[], Dict[str, Any]]] = []
        self.last_metrics = None

        # Setup default alert notifications
        self.alert_manager.add_notification_callback(self._default_alert_handler)

        logger.info(f"ConcurrencyMonitor initialized with {monitoring_interval}s interval")

    def add_metrics_collector(self, collector: Callable[[], Dict[str, Any]]):
        """Add a metrics collector function"""
        self.metrics_collectors.append(collector)

    def start_monitoring(self):
        """Start the monitoring system"""
        if self.is_running:
            logger.warning("Monitoring is already running")
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("Concurrency monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("Concurrency monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Collect metrics
                metrics = self._collect_metrics()

                # Store metrics
                self.last_metrics = metrics
                self.performance_analyzer.record_metrics(metrics)

                # Evaluate alerts
                self.alert_manager.evaluate_alerts(metrics)

                # Log periodic summary
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    self._log_monitoring_summary()

                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)

    def _collect_metrics(self) -> ConcurrencyMetrics:
        """Collect comprehensive metrics"""
        # Base system metrics
        cpu_usage = psutil.cpu_percent()
        memory_info = psutil.virtual_memory()

        metrics = ConcurrencyMetrics(
            cpu_usage=cpu_usage,
            memory_usage=memory_info.percent,
            thread_count=threading.active_count()
        )

        # Collect from registered collectors
        for collector in self.metrics_collectors:
            try:
                collector_metrics = collector()

                # Update metrics with collector data
                for key, value in collector_metrics.items():
                    if hasattr(metrics, key):
                        setattr(metrics, key, value)

            except Exception as e:
                logger.error(f"Error in metrics collector: {e}")

        return metrics

    def _default_alert_handler(self, alert: Alert):
        """Default alert notification handler"""
        severity_emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }

        emoji = severity_emoji.get(alert.severity, '📊')
        logger.warning(f"{emoji} ALERT [{alert.severity.upper()}] {alert.title}: {alert.description}")

    def _log_monitoring_summary(self):
        """Log periodic monitoring summary"""
        if not self.last_metrics:
            return

        alert_summary = self.alert_manager.get_alert_summary()
        performance_summary = self.performance_analyzer.get_performance_summary()

        logger.info("=== Concurrency Monitoring Summary ===")
        logger.info(f"System: CPU {self.last_metrics.cpu_usage:.1f}%, "
                   f"Memory {self.last_metrics.memory_usage:.1f}%, "
                   f"Threads {self.last_metrics.thread_count}")
        logger.info(f"Agents: {self.last_metrics.active_agents} active, "
                   f"{self.last_metrics.working_agents} working, "
                   f"{self.last_metrics.stuck_agents} stuck")
        logger.info(f"Tasks: {self.last_metrics.running_tasks} running, "
                   f"{self.last_metrics.pending_tasks} pending")
        logger.info(f"Performance: {self.last_metrics.throughput_per_minute:.1f} tasks/min, "
                   f"{self.last_metrics.avg_response_time:.2f}s response, "
                   f"{self.last_metrics.error_rate:.1%} errors")
        logger.info(f"Alerts: {alert_summary['total_active']} active")

        if performance_summary.get('anomalies'):
            logger.warning(f"Anomalies detected: {len(performance_summary['anomalies'])}")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status"""
        alert_summary = self.alert_manager.get_alert_summary()
        performance_summary = self.performance_analyzer.get_performance_summary()

        return {
            'monitoring': {
                'is_running': self.is_running,
                'interval_seconds': self.monitoring_interval,
                'collectors_count': len(self.metrics_collectors)
            },
            'current_metrics': asdict(self.last_metrics) if self.last_metrics else None,
            'alerts': alert_summary,
            'performance': performance_summary,
            'status_timestamp': datetime.now().isoformat()
        }

    def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """Get data optimized for real-time dashboard display"""
        if not self.last_metrics:
            return {'status': 'no_data'}

        # Get recent trends (last 30 minutes)
        trends = self.performance_analyzer.analyze_trends(30)
        active_alerts = self.alert_manager.get_active_alerts()

        # Critical alerts only
        critical_alerts = [a for a in active_alerts if a.severity in ['error', 'critical']]

        return {
            'system_health': {
                'cpu': self.last_metrics.cpu_usage,
                'memory': self.last_metrics.memory_usage,
                'threads': self.last_metrics.thread_count,
                'status': 'healthy' if not critical_alerts else 'degraded'
            },
            'agent_status': {
                'active': self.last_metrics.active_agents,
                'working': self.last_metrics.working_agents,
                'idle': self.last_metrics.idle_agents,
                'stuck': self.last_metrics.stuck_agents
            },
            'task_status': {
                'pending': self.last_metrics.pending_tasks,
                'running': self.last_metrics.running_tasks,
                'completed': self.last_metrics.completed_tasks,
                'failed': self.last_metrics.failed_tasks
            },
            'performance': {
                'throughput': self.last_metrics.throughput_per_minute,
                'response_time': self.last_metrics.avg_response_time,
                'error_rate': self.last_metrics.error_rate,
                'cache_hit_rate': self.last_metrics.cache_hit_rate
            },
            'concurrency': {
                'lock_contention': self.last_metrics.lock_contention_rate,
                'deadlocks': self.last_metrics.deadlock_count,
                'race_conditions': self.last_metrics.race_condition_count,
                'resource_conflicts': self.last_metrics.resource_conflicts
            },
            'alerts': {
                'critical_count': len([a for a in active_alerts if a.severity == 'critical']),
                'error_count': len([a for a in active_alerts if a.severity == 'error']),
                'warning_count': len([a for a in active_alerts if a.severity == 'warning']),
                'recent_alerts': [
                    {
                        'title': a.title,
                        'severity': a.severity,
                        'timestamp': a.timestamp.isoformat()
                    }
                    for a in active_alerts[-5:]  # Last 5 alerts
                ]
            },
            'trends': trends.get('summary', {}),
            'timestamp': datetime.now().isoformat()
        }