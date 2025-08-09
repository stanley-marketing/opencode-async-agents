"""
WebSocket Performance Metrics Collection and Monitoring
Real-time metrics collection for WebSocket performance optimization
"""

import asyncio
import json
import logging
import time
import psutil
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Union
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
import aiofiles
import os

logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetrics:
    """Metrics for individual WebSocket connections"""
    user_id: str
    role: str
    connected_at: datetime
    last_activity: datetime
    
    # Message metrics
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    
    # Performance metrics
    avg_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    latency_samples: List[float] = field(default_factory=list)
    
    # Error tracking
    error_count: int = 0
    connection_drops: int = 0
    reconnection_count: int = 0
    
    # Health status
    is_healthy: bool = True
    last_ping_ms: float = 0.0
    ping_failures: int = 0
    
    def update_latency(self, latency_ms: float):
        """Update latency metrics"""
        self.latency_samples.append(latency_ms)
        if len(self.latency_samples) > 100:  # Keep last 100 samples
            self.latency_samples.pop(0)
        
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        self.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
    
    def get_percentile_latency(self, percentile: float) -> float:
        """Get latency percentile (e.g., 0.95 for P95)"""
        if not self.latency_samples:
            return 0.0
        
        sorted_samples = sorted(self.latency_samples)
        index = int(len(sorted_samples) * percentile)
        return sorted_samples[min(index, len(sorted_samples) - 1)]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'user_id': self.user_id,
            'role': self.role,
            'connected_at': self.connected_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'connection_duration_seconds': (datetime.now() - self.connected_at).total_seconds(),
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'avg_latency_ms': self.avg_latency_ms,
            'min_latency_ms': self.min_latency_ms if self.min_latency_ms != float('inf') else 0.0,
            'max_latency_ms': self.max_latency_ms,
            'p50_latency_ms': self.get_percentile_latency(0.5),
            'p95_latency_ms': self.get_percentile_latency(0.95),
            'p99_latency_ms': self.get_percentile_latency(0.99),
            'error_count': self.error_count,
            'connection_drops': self.connection_drops,
            'reconnection_count': self.reconnection_count,
            'is_healthy': self.is_healthy,
            'last_ping_ms': self.last_ping_ms,
            'ping_failures': self.ping_failures
        }


@dataclass
class ServerMetrics:
    """Server-wide WebSocket metrics"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Connection metrics
    total_connections: int = 0
    active_connections: int = 0
    peak_connections: int = 0
    connections_per_second: float = 0.0
    disconnections_per_second: float = 0.0
    
    # Message throughput
    messages_per_second: float = 0.0
    bytes_per_second: float = 0.0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    
    # Performance metrics
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    
    # System resources
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    network_io_bytes_sent: int = 0
    network_io_bytes_received: int = 0
    
    # Error metrics
    error_rate_percent: float = 0.0
    total_errors: int = 0
    connection_errors: int = 0
    message_errors: int = 0
    
    # Queue metrics
    message_queue_depth: int = 0
    message_queue_processing_rate: float = 0.0
    
    # Health indicators
    server_health_score: float = 100.0  # 0-100
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class PerformanceAlert:
    """Performance alert definition"""
    alert_id: str
    alert_type: str  # latency, throughput, error_rate, resource_usage
    severity: str    # low, medium, high, critical
    threshold: float
    current_value: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return asdict(self)


class MetricsAggregator:
    """Aggregates metrics from multiple sources"""
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size  # seconds
        self.metrics_history: deque = deque(maxlen=window_size)
        self.lock = asyncio.Lock()
    
    async def add_metrics(self, metrics: ServerMetrics):
        """Add metrics to the aggregator"""
        async with self.lock:
            self.metrics_history.append(metrics)
    
    async def get_average_metrics(self, duration_seconds: int = 60) -> Optional[ServerMetrics]:
        """Get average metrics over specified duration"""
        async with self.lock:
            if not self.metrics_history:
                return None
            
            # Filter metrics within duration
            cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
            recent_metrics = [
                m for m in self.metrics_history 
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return None
            
            # Calculate averages
            avg_metrics = ServerMetrics()
            count = len(recent_metrics)
            
            # Sum all numeric fields
            for metrics in recent_metrics:
                avg_metrics.total_connections += metrics.total_connections
                avg_metrics.active_connections += metrics.active_connections
                avg_metrics.peak_connections = max(avg_metrics.peak_connections, metrics.peak_connections)
                avg_metrics.connections_per_second += metrics.connections_per_second
                avg_metrics.disconnections_per_second += metrics.disconnections_per_second
                avg_metrics.messages_per_second += metrics.messages_per_second
                avg_metrics.bytes_per_second += metrics.bytes_per_second
                avg_metrics.avg_latency_ms += metrics.avg_latency_ms
                avg_metrics.p95_latency_ms += metrics.p95_latency_ms
                avg_metrics.p99_latency_ms += metrics.p99_latency_ms
                avg_metrics.max_latency_ms = max(avg_metrics.max_latency_ms, metrics.max_latency_ms)
                avg_metrics.cpu_usage_percent += metrics.cpu_usage_percent
                avg_metrics.memory_usage_mb += metrics.memory_usage_mb
                avg_metrics.memory_usage_percent += metrics.memory_usage_percent
                avg_metrics.error_rate_percent += metrics.error_rate_percent
                avg_metrics.total_errors += metrics.total_errors
                avg_metrics.message_queue_depth += metrics.message_queue_depth
                avg_metrics.server_health_score += metrics.server_health_score
            
            # Calculate averages
            avg_metrics.total_connections //= count
            avg_metrics.active_connections //= count
            avg_metrics.connections_per_second /= count
            avg_metrics.disconnections_per_second /= count
            avg_metrics.messages_per_second /= count
            avg_metrics.bytes_per_second /= count
            avg_metrics.avg_latency_ms /= count
            avg_metrics.p95_latency_ms /= count
            avg_metrics.p99_latency_ms /= count
            avg_metrics.cpu_usage_percent /= count
            avg_metrics.memory_usage_mb /= count
            avg_metrics.memory_usage_percent /= count
            avg_metrics.error_rate_percent /= count
            avg_metrics.message_queue_depth //= count
            avg_metrics.server_health_score /= count
            
            # Use latest timestamp
            avg_metrics.timestamp = recent_metrics[-1].timestamp
            
            return avg_metrics


class AlertManager:
    """Manages performance alerts and notifications"""
    
    def __init__(self):
        self.alert_thresholds = {
            'latency_p95_ms': 100.0,
            'latency_p99_ms': 200.0,
            'cpu_usage_percent': 80.0,
            'memory_usage_percent': 85.0,
            'error_rate_percent': 5.0,
            'connection_limit_percent': 90.0,
            'message_queue_depth': 1000
        }
        
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_callbacks: List[callable] = []
        self.lock = asyncio.Lock()
    
    def add_alert_callback(self, callback: callable):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    async def check_alerts(self, metrics: ServerMetrics, connection_metrics: List[ConnectionMetrics]):
        """Check for alert conditions"""
        alerts = []
        
        # Latency alerts
        if metrics.p95_latency_ms > self.alert_thresholds['latency_p95_ms']:
            alerts.append(PerformanceAlert(
                alert_id='latency_p95_high',
                alert_type='latency',
                severity='high' if metrics.p95_latency_ms > 150 else 'medium',
                threshold=self.alert_thresholds['latency_p95_ms'],
                current_value=metrics.p95_latency_ms,
                message=f"P95 latency is {metrics.p95_latency_ms:.1f}ms (threshold: {self.alert_thresholds['latency_p95_ms']}ms)"
            ))
        
        if metrics.p99_latency_ms > self.alert_thresholds['latency_p99_ms']:
            alerts.append(PerformanceAlert(
                alert_id='latency_p99_high',
                alert_type='latency',
                severity='critical' if metrics.p99_latency_ms > 500 else 'high',
                threshold=self.alert_thresholds['latency_p99_ms'],
                current_value=metrics.p99_latency_ms,
                message=f"P99 latency is {metrics.p99_latency_ms:.1f}ms (threshold: {self.alert_thresholds['latency_p99_ms']}ms)"
            ))
        
        # Resource alerts
        if metrics.cpu_usage_percent > self.alert_thresholds['cpu_usage_percent']:
            alerts.append(PerformanceAlert(
                alert_id='cpu_usage_high',
                alert_type='resource_usage',
                severity='critical' if metrics.cpu_usage_percent > 95 else 'high',
                threshold=self.alert_thresholds['cpu_usage_percent'],
                current_value=metrics.cpu_usage_percent,
                message=f"CPU usage is {metrics.cpu_usage_percent:.1f}% (threshold: {self.alert_thresholds['cpu_usage_percent']}%)"
            ))
        
        if metrics.memory_usage_percent > self.alert_thresholds['memory_usage_percent']:
            alerts.append(PerformanceAlert(
                alert_id='memory_usage_high',
                alert_type='resource_usage',
                severity='critical' if metrics.memory_usage_percent > 95 else 'high',
                threshold=self.alert_thresholds['memory_usage_percent'],
                current_value=metrics.memory_usage_percent,
                message=f"Memory usage is {metrics.memory_usage_percent:.1f}% (threshold: {self.alert_thresholds['memory_usage_percent']}%)"
            ))
        
        # Error rate alerts
        if metrics.error_rate_percent > self.alert_thresholds['error_rate_percent']:
            alerts.append(PerformanceAlert(
                alert_id='error_rate_high',
                alert_type='error_rate',
                severity='critical' if metrics.error_rate_percent > 10 else 'high',
                threshold=self.alert_thresholds['error_rate_percent'],
                current_value=metrics.error_rate_percent,
                message=f"Error rate is {metrics.error_rate_percent:.1f}% (threshold: {self.alert_thresholds['error_rate_percent']}%)"
            ))
        
        # Queue depth alerts
        if metrics.message_queue_depth > self.alert_thresholds['message_queue_depth']:
            alerts.append(PerformanceAlert(
                alert_id='queue_depth_high',
                alert_type='throughput',
                severity='high' if metrics.message_queue_depth > 5000 else 'medium',
                threshold=self.alert_thresholds['message_queue_depth'],
                current_value=metrics.message_queue_depth,
                message=f"Message queue depth is {metrics.message_queue_depth} (threshold: {self.alert_thresholds['message_queue_depth']})"
            ))
        
        # Process alerts
        async with self.lock:
            for alert in alerts:
                if alert.alert_id not in self.active_alerts:
                    # New alert
                    self.active_alerts[alert.alert_id] = alert
                    self.alert_history.append(alert)
                    
                    # Notify callbacks
                    for callback in self.alert_callbacks:
                        try:
                            await callback(alert)
                        except Exception as e:
                            logger.error(f"Error in alert callback: {e}")
                else:
                    # Update existing alert
                    self.active_alerts[alert.alert_id].current_value = alert.current_value
                    self.active_alerts[alert.alert_id].timestamp = alert.timestamp
            
            # Clear resolved alerts
            resolved_alerts = []
            for alert_id, alert in self.active_alerts.items():
                if alert_id not in [a.alert_id for a in alerts]:
                    resolved_alerts.append(alert_id)
            
            for alert_id in resolved_alerts:
                del self.active_alerts[alert_id]
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get currently active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[PerformanceAlert]:
        """Get alert history"""
        return list(self.alert_history)[-limit:]


class WebSocketMetricsCollector:
    """Comprehensive WebSocket metrics collection system"""
    
    def __init__(self, collection_interval: int = 1, persistence_file: str = None):
        self.collection_interval = collection_interval
        self.persistence_file = persistence_file
        
        # Metrics storage
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.server_metrics_history: deque = deque(maxlen=3600)  # 1 hour at 1s intervals
        self.current_server_metrics = ServerMetrics()
        
        # Aggregation and alerting
        self.aggregator = MetricsAggregator()
        self.alert_manager = AlertManager()
        
        # Collection state
        self.is_collecting = False
        self.collection_task: Optional[asyncio.Task] = None
        self.start_time = datetime.now()
        
        # Performance tracking
        self.last_metrics_time = time.time()
        self.last_message_count = 0
        self.last_byte_count = 0
        self.last_connection_count = 0
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="metrics")
        
        # Weak references to avoid memory leaks
        self.connection_refs: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
    
    async def start_collection(self):
        """Start metrics collection"""
        if self.is_collecting:
            return
        
        self.is_collecting = True
        self.start_time = datetime.now()
        self.collection_task = asyncio.create_task(self._collection_loop())
        
        logger.info("WebSocket metrics collection started")
    
    async def stop_collection(self):
        """Stop metrics collection"""
        if not self.is_collecting:
            return
        
        self.is_collecting = False
        
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        # Persist final metrics
        if self.persistence_file:
            await self._persist_metrics()
        
        logger.info("WebSocket metrics collection stopped")
    
    def register_connection(self, user_id: str, role: str = "user"):
        """Register a new connection for metrics tracking"""
        metrics = ConnectionMetrics(
            user_id=user_id,
            role=role,
            connected_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.connection_metrics[user_id] = metrics
        logger.debug(f"Registered connection metrics for user {user_id}")
    
    def unregister_connection(self, user_id: str):
        """Unregister a connection"""
        if user_id in self.connection_metrics:
            del self.connection_metrics[user_id]
            logger.debug(f"Unregistered connection metrics for user {user_id}")
    
    def record_message_sent(self, user_id: str, message_size: int, latency_ms: float = None):
        """Record a message sent"""
        if user_id in self.connection_metrics:
            metrics = self.connection_metrics[user_id]
            metrics.messages_sent += 1
            metrics.bytes_sent += message_size
            metrics.last_activity = datetime.now()
            
            if latency_ms is not None:
                metrics.update_latency(latency_ms)
    
    def record_message_received(self, user_id: str, message_size: int):
        """Record a message received"""
        if user_id in self.connection_metrics:
            metrics = self.connection_metrics[user_id]
            metrics.messages_received += 1
            metrics.bytes_received += message_size
            metrics.last_activity = datetime.now()
    
    def record_error(self, user_id: str, error_type: str = "general"):
        """Record an error for a connection"""
        if user_id in self.connection_metrics:
            metrics = self.connection_metrics[user_id]
            metrics.error_count += 1
            
            if error_type == "connection_drop":
                metrics.connection_drops += 1
            elif error_type == "ping_failure":
                metrics.ping_failures += 1
    
    def record_ping(self, user_id: str, ping_ms: float, success: bool = True):
        """Record a ping result"""
        if user_id in self.connection_metrics:
            metrics = self.connection_metrics[user_id]
            metrics.last_ping_ms = ping_ms
            
            if not success:
                metrics.ping_failures += 1
                if metrics.ping_failures >= 3:
                    metrics.is_healthy = False
            else:
                metrics.ping_failures = 0
                metrics.is_healthy = True
    
    def record_reconnection(self, user_id: str):
        """Record a reconnection"""
        if user_id in self.connection_metrics:
            metrics = self.connection_metrics[user_id]
            metrics.reconnection_count += 1
    
    async def _collection_loop(self):
        """Main metrics collection loop"""
        while self.is_collecting:
            try:
                # Collect current metrics
                await self._collect_server_metrics()
                
                # Add to aggregator
                await self.aggregator.add_metrics(self.current_server_metrics)
                
                # Store in history
                self.server_metrics_history.append(self.current_server_metrics)
                
                # Check for alerts
                await self.alert_manager.check_alerts(
                    self.current_server_metrics,
                    list(self.connection_metrics.values())
                )
                
                # Persist metrics periodically
                if self.persistence_file and len(self.server_metrics_history) % 60 == 0:
                    await self._persist_metrics()
                
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5)
    
    async def _collect_server_metrics(self):
        """Collect server-wide metrics"""
        now = time.time()
        current_time = datetime.now()
        
        # Connection metrics
        total_connections = len(self.connection_metrics)
        active_connections = sum(1 for m in self.connection_metrics.values() if m.is_healthy)
        
        # Calculate rates
        time_diff = now - self.last_metrics_time
        if time_diff > 0:
            # Message throughput
            current_message_count = sum(
                m.messages_sent + m.messages_received 
                for m in self.connection_metrics.values()
            )
            messages_per_second = (current_message_count - self.last_message_count) / time_diff
            
            # Byte throughput
            current_byte_count = sum(
                m.bytes_sent + m.bytes_received 
                for m in self.connection_metrics.values()
            )
            bytes_per_second = (current_byte_count - self.last_byte_count) / time_diff
            
            # Connection rate
            connections_per_second = (total_connections - self.last_connection_count) / time_diff
            
            self.last_message_count = current_message_count
            self.last_byte_count = current_byte_count
            self.last_connection_count = total_connections
        else:
            messages_per_second = 0.0
            bytes_per_second = 0.0
            connections_per_second = 0.0
        
        self.last_metrics_time = now
        
        # Latency metrics
        all_latencies = []
        for metrics in self.connection_metrics.values():
            all_latencies.extend(metrics.latency_samples)
        
        if all_latencies:
            sorted_latencies = sorted(all_latencies)
            avg_latency = sum(sorted_latencies) / len(sorted_latencies)
            p50_latency = sorted_latencies[int(len(sorted_latencies) * 0.5)]
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]
            max_latency = max(sorted_latencies)
        else:
            avg_latency = p50_latency = p95_latency = p99_latency = max_latency = 0.0
        
        # System metrics
        process = psutil.Process()
        cpu_percent = process.cpu_percent()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # System memory
        system_memory = psutil.virtual_memory()
        memory_percent = system_memory.percent
        
        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            network_bytes_sent = net_io.bytes_sent
            network_bytes_received = net_io.bytes_recv
        except:
            network_bytes_sent = network_bytes_received = 0
        
        # Error metrics
        total_errors = sum(m.error_count for m in self.connection_metrics.values())
        total_messages = sum(m.messages_sent + m.messages_received for m in self.connection_metrics.values())
        error_rate = (total_errors / max(total_messages, 1)) * 100
        
        # Health score calculation
        health_score = 100.0
        if p95_latency > 100:
            health_score -= min(20, (p95_latency - 100) / 10)
        if cpu_percent > 80:
            health_score -= min(20, (cpu_percent - 80) / 2)
        if memory_percent > 85:
            health_score -= min(20, (memory_percent - 85) / 3)
        if error_rate > 5:
            health_score -= min(20, (error_rate - 5) * 2)
        
        health_score = max(0, health_score)
        
        # Update current metrics
        self.current_server_metrics = ServerMetrics(
            timestamp=current_time,
            total_connections=total_connections,
            active_connections=active_connections,
            peak_connections=max(getattr(self.current_server_metrics, 'peak_connections', 0), total_connections),
            connections_per_second=connections_per_second,
            messages_per_second=messages_per_second,
            bytes_per_second=bytes_per_second,
            total_messages_sent=sum(m.messages_sent for m in self.connection_metrics.values()),
            total_messages_received=sum(m.messages_received for m in self.connection_metrics.values()),
            total_bytes_sent=sum(m.bytes_sent for m in self.connection_metrics.values()),
            total_bytes_received=sum(m.bytes_received for m in self.connection_metrics.values()),
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_latency_ms=max_latency,
            cpu_usage_percent=cpu_percent,
            memory_usage_mb=memory_mb,
            memory_usage_percent=memory_percent,
            network_io_bytes_sent=network_bytes_sent,
            network_io_bytes_received=network_bytes_received,
            error_rate_percent=error_rate,
            total_errors=total_errors,
            server_health_score=health_score,
            uptime_seconds=(current_time - self.start_time).total_seconds()
        )
    
    async def _persist_metrics(self):
        """Persist metrics to file"""
        if not self.persistence_file:
            return
        
        try:
            # Prepare data for persistence
            data = {
                'timestamp': datetime.now().isoformat(),
                'server_metrics': [m.to_dict() for m in list(self.server_metrics_history)[-100:]],  # Last 100 entries
                'connection_metrics': [m.to_dict() for m in self.connection_metrics.values()],
                'active_alerts': [a.to_dict() for a in self.alert_manager.get_active_alerts()],
                'collection_stats': {
                    'start_time': self.start_time.isoformat(),
                    'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
                    'total_connections_tracked': len(self.connection_metrics)
                }
            }
            
            # Write to file
            async with aiofiles.open(self.persistence_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
            
            logger.debug(f"Persisted metrics to {self.persistence_file}")
            
        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")
    
    async def load_persisted_metrics(self):
        """Load persisted metrics from file"""
        if not self.persistence_file or not os.path.exists(self.persistence_file):
            return
        
        try:
            async with aiofiles.open(self.persistence_file, 'r') as f:
                data = json.loads(await f.read())
            
            # Load server metrics history
            for metrics_data in data.get('server_metrics', []):
                metrics = ServerMetrics(**metrics_data)
                self.server_metrics_history.append(metrics)
            
            logger.info(f"Loaded {len(self.server_metrics_history)} historical metrics entries")
            
        except Exception as e:
            logger.error(f"Failed to load persisted metrics: {e}")
    
    def get_current_metrics(self) -> ServerMetrics:
        """Get current server metrics"""
        return self.current_server_metrics
    
    def get_connection_metrics(self, user_id: str = None) -> Union[ConnectionMetrics, List[ConnectionMetrics]]:
        """Get connection metrics"""
        if user_id:
            return self.connection_metrics.get(user_id)
        else:
            return list(self.connection_metrics.values())
    
    async def get_aggregated_metrics(self, duration_seconds: int = 60) -> Optional[ServerMetrics]:
        """Get aggregated metrics over specified duration"""
        return await self.aggregator.get_average_metrics(duration_seconds)
    
    def get_metrics_history(self, limit: int = 100) -> List[ServerMetrics]:
        """Get metrics history"""
        return list(self.server_metrics_history)[-limit:]
    
    def get_performance_summary(self) -> dict:
        """Get comprehensive performance summary"""
        current = self.current_server_metrics
        connections = list(self.connection_metrics.values())
        
        # Connection breakdown by role
        role_breakdown = defaultdict(int)
        for conn in connections:
            role_breakdown[conn.role] += 1
        
        # Top users by activity
        top_users = sorted(
            connections,
            key=lambda c: c.messages_sent + c.messages_received,
            reverse=True
        )[:10]
        
        return {
            'current_metrics': current.to_dict(),
            'connection_summary': {
                'total_connections': len(connections),
                'healthy_connections': sum(1 for c in connections if c.is_healthy),
                'role_breakdown': dict(role_breakdown),
                'avg_connection_age_minutes': sum(
                    (datetime.now() - c.connected_at).total_seconds() / 60
                    for c in connections
                ) / max(len(connections), 1)
            },
            'performance_indicators': {
                'latency_status': 'good' if current.p95_latency_ms < 100 else 'degraded' if current.p95_latency_ms < 200 else 'poor',
                'throughput_status': 'good' if current.messages_per_second > 100 else 'moderate' if current.messages_per_second > 50 else 'low',
                'resource_status': 'good' if current.cpu_usage_percent < 70 and current.memory_usage_percent < 80 else 'high',
                'error_status': 'good' if current.error_rate_percent < 1 else 'elevated' if current.error_rate_percent < 5 else 'high'
            },
            'top_active_users': [
                {
                    'user_id': c.user_id,
                    'role': c.role,
                    'total_messages': c.messages_sent + c.messages_received,
                    'avg_latency_ms': c.avg_latency_ms
                }
                for c in top_users
            ],
            'active_alerts': [a.to_dict() for a in self.alert_manager.get_active_alerts()],
            'collection_info': {
                'uptime_seconds': current.uptime_seconds,
                'collection_interval': self.collection_interval,
                'history_entries': len(self.server_metrics_history)
            }
        }
    
    def add_alert_callback(self, callback: callable):
        """Add callback for alert notifications"""
        self.alert_manager.add_alert_callback(callback)
    
    async def export_metrics(self, format: str = 'json', file_path: str = None) -> str:
        """Export metrics in specified format"""
        data = self.get_performance_summary()
        
        if format.lower() == 'json':
            exported_data = json.dumps(data, indent=2, default=str)
        elif format.lower() == 'csv':
            # Convert to CSV format (simplified)
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(['timestamp', 'connections', 'messages_per_second', 'avg_latency_ms', 'cpu_percent', 'memory_mb'])
            
            # Write data
            for metrics in self.server_metrics_history:
                writer.writerow([
                    metrics.timestamp.isoformat(),
                    metrics.total_connections,
                    metrics.messages_per_second,
                    metrics.avg_latency_ms,
                    metrics.cpu_usage_percent,
                    metrics.memory_usage_mb
                ])
            
            exported_data = output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        if file_path:
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(exported_data)
            logger.info(f"Exported metrics to {file_path}")
        
        return exported_data