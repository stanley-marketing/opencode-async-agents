# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
Real-time Communication Monitor
Provides comprehensive monitoring, metrics collection, and alerting for communication systems.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
import asyncio
import json
import logging
import os
import psutil
import statistics
import threading
import time

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and aggregates performance metrics"""

    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics_data = defaultdict(lambda: deque())
        self.aggregated_metrics = {}
        self.lock = threading.RLock()

        # Metric definitions
        self.metric_definitions = {
            'message_throughput': {'unit': 'msg/s', 'type': 'rate'},
            'message_latency': {'unit': 'ms', 'type': 'histogram'},
            'success_rate': {'unit': '%', 'type': 'percentage'},
            'queue_size': {'unit': 'count', 'type': 'gauge'},
            'agent_response_time': {'unit': 'ms', 'type': 'histogram'},
            'error_rate': {'unit': '%', 'type': 'percentage'},
            'cpu_usage': {'unit': '%', 'type': 'gauge'},
            'memory_usage': {'unit': 'MB', 'type': 'gauge'},
            'network_io': {'unit': 'bytes/s', 'type': 'rate'}
        }

    def record_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Record a metric value"""
        if timestamp is None:
            timestamp = datetime.now()

        with self.lock:
            self.metrics_data[metric_name].append({
                'value': value,
                'timestamp': timestamp
            })

            # Clean old data
            self._cleanup_old_data(metric_name)

    def record_batch_metrics(self, metrics: Dict[str, float], timestamp: Optional[datetime] = None):
        """Record multiple metrics at once"""
        if timestamp is None:
            timestamp = datetime.now()

        for metric_name, value in metrics.items():
            self.record_metric(metric_name, value, timestamp)

    def get_metric_summary(self, metric_name: str, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get summary statistics for a metric"""
        with self.lock:
            if metric_name not in self.metrics_data:
                return {}

            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            recent_data = [
                entry for entry in self.metrics_data[metric_name]
                if entry['timestamp'] >= cutoff_time
            ]

            if not recent_data:
                return {}

            values = [entry['value'] for entry in recent_data]

            summary = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
                'p95': self._percentile(values, 95),
                'p99': self._percentile(values, 99),
                'time_window_minutes': time_window_minutes,
                'unit': self.metric_definitions.get(metric_name, {}).get('unit', ''),
                'type': self.metric_definitions.get(metric_name, {}).get('type', 'gauge')
            }

            return summary

    def get_time_series(self, metric_name: str, time_window_minutes: int = 60,
                       bucket_size_minutes: int = 5) -> List[Dict[str, Any]]:
        """Get time series data for a metric"""
        with self.lock:
            if metric_name not in self.metrics_data:
                return []

            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            recent_data = [
                entry for entry in self.metrics_data[metric_name]
                if entry['timestamp'] >= cutoff_time
            ]

            if not recent_data:
                return []

            # Group data into buckets
            buckets = defaultdict(list)
            bucket_size = timedelta(minutes=bucket_size_minutes)

            for entry in recent_data:
                bucket_start = entry['timestamp'].replace(second=0, microsecond=0)
                bucket_start = bucket_start.replace(
                    minute=(bucket_start.minute // bucket_size_minutes) * bucket_size_minutes
                )
                buckets[bucket_start].append(entry['value'])

            # Calculate bucket statistics
            time_series = []
            for bucket_time in sorted(buckets.keys()):
                values = buckets[bucket_time]
                time_series.append({
                    'timestamp': bucket_time.isoformat(),
                    'count': len(values),
                    'mean': statistics.mean(values),
                    'min': min(values),
                    'max': max(values)
                })

            return time_series

    def _cleanup_old_data(self, metric_name: str):
        """Remove old metric data"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

        while (self.metrics_data[metric_name] and
               self.metrics_data[metric_name][0]['timestamp'] < cutoff_time):
            self.metrics_data[metric_name].popleft()

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

class AlertManager:
    """Manages alerts and notifications"""

    def __init__(self):
        self.alert_rules = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_callbacks = []
        self.lock = threading.RLock()

    def add_alert_rule(self, rule_name: str, metric_name: str, condition: str,
                      threshold: float, duration_minutes: int = 5):
        """Add an alert rule"""
        with self.lock:
            self.alert_rules[rule_name] = {
                'metric_name': metric_name,
                'condition': condition,  # 'gt', 'lt', 'eq'
                'threshold': threshold,
                'duration_minutes': duration_minutes,
                'created_at': datetime.now()
            }

        logger.info(f"Added alert rule: {rule_name}")

    def remove_alert_rule(self, rule_name: str):
        """Remove an alert rule"""
        with self.lock:
            if rule_name in self.alert_rules:
                del self.alert_rules[rule_name]
                logger.info(f"Removed alert rule: {rule_name}")

    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)

    def check_alerts(self, metrics_collector: MetricsCollector):
        """Check all alert rules against current metrics"""
        with self.lock:
            for rule_name, rule in self.alert_rules.items():
                self._check_single_alert(rule_name, rule, metrics_collector)

    def _check_single_alert(self, rule_name: str, rule: Dict[str, Any],
                           metrics_collector: MetricsCollector):
        """Check a single alert rule"""
        metric_summary = metrics_collector.get_metric_summary(
            rule['metric_name'],
            rule['duration_minutes']
        )

        if not metric_summary:
            return

        current_value = metric_summary['mean']
        threshold = rule['threshold']
        condition = rule['condition']

        # Check condition
        alert_triggered = False
        if condition == 'gt' and current_value > threshold:
            alert_triggered = True
        elif condition == 'lt' and current_value < threshold:
            alert_triggered = True
        elif condition == 'eq' and abs(current_value - threshold) < 0.001:
            alert_triggered = True

        # Handle alert state
        if alert_triggered:
            if rule_name not in self.active_alerts:
                # New alert
                alert = {
                    'rule_name': rule_name,
                    'metric_name': rule['metric_name'],
                    'current_value': current_value,
                    'threshold': threshold,
                    'condition': condition,
                    'triggered_at': datetime.now(),
                    'severity': self._calculate_severity(current_value, threshold, condition)
                }

                self.active_alerts[rule_name] = alert
                self.alert_history.append(alert.copy())

                # Notify callbacks
                for callback in self.alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Error in alert callback: {e}")

                logger.warning(f"Alert triggered: {rule_name}")
        else:
            if rule_name in self.active_alerts:
                # Alert resolved
                resolved_alert = self.active_alerts[rule_name].copy()
                resolved_alert['resolved_at'] = datetime.now()
                resolved_alert['status'] = 'resolved'

                del self.active_alerts[rule_name]
                self.alert_history.append(resolved_alert)

                logger.info(f"Alert resolved: {rule_name}")

    def _calculate_severity(self, current_value: float, threshold: float, condition: str) -> str:
        """Calculate alert severity"""
        if condition == 'gt':
            ratio = current_value / threshold
            if ratio > 2.0:
                return 'critical'
            elif ratio > 1.5:
                return 'high'
            else:
                return 'medium'
        elif condition == 'lt':
            ratio = threshold / current_value if current_value > 0 else float('inf')
            if ratio > 2.0:
                return 'critical'
            elif ratio > 1.5:
                return 'high'
            else:
                return 'medium'
        else:
            return 'medium'

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        with self.lock:
            return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self.lock:
            return [
                alert for alert in self.alert_history
                if alert['triggered_at'] >= cutoff_time
            ]

class SystemResourceMonitor:
    """Monitors system resources"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.monitoring = False
        self.monitor_thread = None
        self.process = psutil.Process()

        # Network I/O tracking
        self.last_network_io = None
        self.last_network_time = None

    def start_monitoring(self, interval_seconds: int = 5):
        """Start resource monitoring"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()

        logger.info("Started system resource monitoring")

    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("Stopped system resource monitoring")

    def _monitor_loop(self, interval_seconds: int):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                time.sleep(interval_seconds)

    def _collect_system_metrics(self):
        """Collect system metrics"""
        timestamp = datetime.now()

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        self.metrics_collector.record_metric('cpu_usage', cpu_percent, timestamp)

        # Memory usage
        memory_info = psutil.virtual_memory()
        memory_mb = memory_info.used / (1024 * 1024)
        self.metrics_collector.record_metric('memory_usage', memory_mb, timestamp)

        # Process-specific metrics
        try:
            process_cpu = self.process.cpu_percent()
            process_memory = self.process.memory_info().rss / (1024 * 1024)

            self.metrics_collector.record_metric('process_cpu_usage', process_cpu, timestamp)
            self.metrics_collector.record_metric('process_memory_usage', process_memory, timestamp)
        except Exception as e:
            logger.debug(f"Error collecting process metrics: {e}")

        # Network I/O
        try:
            network_io = psutil.net_io_counters()
            current_time = time.time()

            if self.last_network_io and self.last_network_time:
                time_diff = current_time - self.last_network_time
                bytes_sent_rate = (network_io.bytes_sent - self.last_network_io.bytes_sent) / time_diff
                bytes_recv_rate = (network_io.bytes_recv - self.last_network_io.bytes_recv) / time_diff

                self.metrics_collector.record_metric('network_bytes_sent_rate', bytes_sent_rate, timestamp)
                self.metrics_collector.record_metric('network_bytes_recv_rate', bytes_recv_rate, timestamp)

            self.last_network_io = network_io
            self.last_network_time = current_time

        except Exception as e:
            logger.debug(f"Error collecting network metrics: {e}")

class CommunicationMetricsCollector:
    """Specialized metrics collector for communication systems"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.message_timestamps = deque(maxlen=1000)
        self.response_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.lock = threading.RLock()

    def record_message_sent(self, latency_ms: float, success: bool, timestamp: Optional[datetime] = None):
        """Record a message being sent"""
        if timestamp is None:
            timestamp = datetime.now()

        with self.lock:
            self.message_timestamps.append(timestamp)
            self.response_times.append(latency_ms)

            # Record metrics
            self.metrics_collector.record_metric('message_latency', latency_ms, timestamp)

            if not success:
                self.error_counts['send_failure'] += 1

            # Calculate throughput
            self._update_throughput_metrics(timestamp)

            # Calculate success rate
            self._update_success_rate_metrics(timestamp)

    def record_message_received(self, timestamp: Optional[datetime] = None):
        """Record a message being received"""
        if timestamp is None:
            timestamp = datetime.now()

        self.metrics_collector.record_metric('messages_received', 1, timestamp)

    def record_queue_size(self, size: int, timestamp: Optional[datetime] = None):
        """Record current queue size"""
        if timestamp is None:
            timestamp = datetime.now()

        self.metrics_collector.record_metric('queue_size', size, timestamp)

    def record_agent_response(self, agent_name: str, response_time_ms: float,
                            success: bool, timestamp: Optional[datetime] = None):
        """Record agent response metrics"""
        if timestamp is None:
            timestamp = datetime.now()

        self.metrics_collector.record_metric('agent_response_time', response_time_ms, timestamp)
        self.metrics_collector.record_metric(f'agent_{agent_name}_response_time', response_time_ms, timestamp)

        if not success:
            self.error_counts[f'agent_{agent_name}_error'] += 1

    def _update_throughput_metrics(self, timestamp: datetime):
        """Update throughput metrics"""
        # Calculate messages per second over last minute
        one_minute_ago = timestamp - timedelta(minutes=1)
        recent_messages = [
            ts for ts in self.message_timestamps
            if ts >= one_minute_ago
        ]

        throughput = len(recent_messages) / 60.0  # messages per second
        self.metrics_collector.record_metric('message_throughput', throughput, timestamp)

    def _update_success_rate_metrics(self, timestamp: datetime):
        """Update success rate metrics"""
        # Calculate success rate over last 5 minutes
        five_minutes_ago = timestamp - timedelta(minutes=5)
        recent_messages = [
            ts for ts in self.message_timestamps
            if ts >= five_minutes_ago
        ]

        if recent_messages:
            total_errors = sum(
                count for error_type, count in self.error_counts.items()
                if 'failure' in error_type or 'error' in error_type
            )

            success_rate = max(0, (len(recent_messages) - total_errors) / len(recent_messages) * 100)
            self.metrics_collector.record_metric('success_rate', success_rate, timestamp)

class RealtimeMonitor:
    """Main real-time communication monitor"""

    def __init__(self, alert_callback: Optional[Callable] = None):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.resource_monitor = SystemResourceMonitor(self.metrics_collector)
        self.comm_metrics = CommunicationMetricsCollector(self.metrics_collector)

        # Monitoring state
        self.monitoring = False
        self.alert_check_thread = None

        # Setup default alert rules
        self._setup_default_alerts()

        # Add alert callback if provided
        if alert_callback:
            self.alert_manager.add_alert_callback(alert_callback)

        logger.info("Real-time monitor initialized")

    def start_monitoring(self):
        """Start all monitoring components"""
        if self.monitoring:
            logger.warning("Monitoring is already running")
            return

        self.monitoring = True

        # Start resource monitoring
        self.resource_monitor.start_monitoring(interval_seconds=5)

        # Start alert checking
        self.alert_check_thread = threading.Thread(
            target=self._alert_check_loop,
            daemon=True
        )
        self.alert_check_thread.start()

        logger.info("Real-time monitoring started")

    def stop_monitoring(self):
        """Stop all monitoring components"""
        if not self.monitoring:
            logger.warning("Monitoring is not running")
            return

        self.monitoring = False

        # Stop resource monitoring
        self.resource_monitor.stop_monitoring()

        # Stop alert checking
        if self.alert_check_thread:
            self.alert_check_thread.join(timeout=5)

        logger.info("Real-time monitoring stopped")

    def record_message_event(self, event_type: str, **kwargs):
        """Record a communication event"""
        if event_type == 'message_sent':
            self.comm_metrics.record_message_sent(
                kwargs.get('latency_ms', 0),
                kwargs.get('success', True),
                kwargs.get('timestamp')
            )
        elif event_type == 'message_received':
            self.comm_metrics.record_message_received(kwargs.get('timestamp'))
        elif event_type == 'queue_size':
            self.comm_metrics.record_queue_size(
                kwargs.get('size', 0),
                kwargs.get('timestamp')
            )
        elif event_type == 'agent_response':
            self.comm_metrics.record_agent_response(
                kwargs.get('agent_name', 'unknown'),
                kwargs.get('response_time_ms', 0),
                kwargs.get('success', True),
                kwargs.get('timestamp')
            )

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        # Get metric summaries
        key_metrics = [
            'message_throughput', 'message_latency', 'success_rate',
            'queue_size', 'agent_response_time', 'cpu_usage', 'memory_usage'
        ]

        metric_summaries = {}
        for metric in key_metrics:
            metric_summaries[metric] = self.metrics_collector.get_metric_summary(metric, 60)

        # Get time series data
        time_series = {}
        for metric in ['message_throughput', 'message_latency', 'success_rate']:
            time_series[metric] = self.metrics_collector.get_time_series(metric, 60, 5)

        # Get alerts
        active_alerts = self.alert_manager.get_active_alerts()
        recent_alerts = self.alert_manager.get_alert_history(24)

        return {
            'metric_summaries': metric_summaries,
            'time_series': time_series,
            'active_alerts': active_alerts,
            'recent_alerts': recent_alerts,
            'timestamp': datetime.now().isoformat()
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        # Check key metrics
        throughput = self.metrics_collector.get_metric_summary('message_throughput', 5)
        success_rate = self.metrics_collector.get_metric_summary('success_rate', 5)
        latency = self.metrics_collector.get_metric_summary('message_latency', 5)

        # Determine health status
        health = "HEALTHY"
        issues = []

        if success_rate and success_rate.get('mean', 100) < 90:
            health = "DEGRADED"
            issues.append(f"Low success rate: {success_rate['mean']:.1f}%")

        if latency and latency.get('mean', 0) > 1000:
            health = "DEGRADED"
            issues.append(f"High latency: {latency['mean']:.1f}ms")

        if throughput and throughput.get('mean', 0) < 1:
            health = "DEGRADED"
            issues.append(f"Low throughput: {throughput['mean']:.1f} msg/s")

        # Check for active alerts
        active_alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a.get('severity') == 'critical']

        if critical_alerts:
            health = "UNHEALTHY"
            issues.extend([f"Critical alert: {a['rule_name']}" for a in critical_alerts])
        elif active_alerts:
            if health == "HEALTHY":
                health = "DEGRADED"
            issues.extend([f"Alert: {a['rule_name']}" for a in active_alerts])

        return {
            'status': health,
            'issues': issues,
            'active_alerts_count': len(active_alerts),
            'critical_alerts_count': len(critical_alerts),
            'timestamp': datetime.now().isoformat()
        }

    def _setup_default_alerts(self):
        """Setup default alert rules"""
        # High latency alert
        self.alert_manager.add_alert_rule(
            'high_latency',
            'message_latency',
            'gt',
            1000,  # 1 second
            duration_minutes=2
        )

        # Low success rate alert
        self.alert_manager.add_alert_rule(
            'low_success_rate',
            'success_rate',
            'lt',
            90,  # 90%
            duration_minutes=3
        )

        # High CPU usage alert
        self.alert_manager.add_alert_rule(
            'high_cpu_usage',
            'cpu_usage',
            'gt',
            80,  # 80%
            duration_minutes=5
        )

        # High memory usage alert
        self.alert_manager.add_alert_rule(
            'high_memory_usage',
            'memory_usage',
            'gt',
            1024,  # 1GB
            duration_minutes=5
        )

        # Large queue size alert
        self.alert_manager.add_alert_rule(
            'large_queue_size',
            'queue_size',
            'gt',
            100,
            duration_minutes=2
        )

    def _alert_check_loop(self):
        """Main alert checking loop"""
        while self.monitoring:
            try:
                self.alert_manager.check_alerts(self.metrics_collector)
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in alert checking: {e}")
                time.sleep(30)

    def add_custom_alert(self, rule_name: str, metric_name: str, condition: str,
                        threshold: float, duration_minutes: int = 5):
        """Add a custom alert rule"""
        self.alert_manager.add_alert_rule(
            rule_name, metric_name, condition, threshold, duration_minutes
        )

    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in specified format"""
        dashboard_data = self.get_dashboard_data()

        if format == 'json':
            return json.dumps(dashboard_data, indent=2, default=str)
        elif format == 'prometheus':
            # Convert to Prometheus format
            lines = []
            for metric_name, summary in dashboard_data['metric_summaries'].items():
                if summary:
                    lines.append(f"# HELP {metric_name} {metric_name} metric")
                    lines.append(f"# TYPE {metric_name} gauge")
                    lines.append(f"{metric_name}_mean {summary['mean']}")
                    lines.append(f"{metric_name}_max {summary['max']}")
                    lines.append(f"{metric_name}_min {summary['min']}")
            return '\n'.join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")