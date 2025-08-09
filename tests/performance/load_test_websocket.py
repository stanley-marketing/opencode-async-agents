"""
Comprehensive WebSocket Load Testing Suite
Tests WebSocket performance under various load conditions for 1000+ concurrent users
"""

import asyncio
import json
import logging
import time
import uuid
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
import aiohttp
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import orjson
import random
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.performance.websocket_optimizer import HighPerformanceWebSocketManager
from monitoring.websocket_metrics import WebSocketMetricsCollector

logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Configuration for load testing"""
    # Connection settings
    server_host: str = "localhost"
    server_port: int = 8765
    max_connections: int = 1000
    connection_ramp_rate: int = 50  # connections per second
    
    # Test duration
    test_duration_seconds: int = 300  # 5 minutes
    warmup_duration_seconds: int = 30
    cooldown_duration_seconds: int = 30
    
    # Message patterns
    messages_per_connection_per_minute: int = 10
    message_size_bytes: int = 1024
    message_burst_probability: float = 0.1  # 10% chance of burst
    message_burst_size: int = 5
    
    # Performance targets
    target_latency_p95_ms: float = 100.0
    target_latency_p99_ms: float = 200.0
    target_throughput_msg_per_sec: float = 1000.0
    target_error_rate_percent: float = 1.0
    
    # Test scenarios
    enable_stress_test: bool = True
    enable_spike_test: bool = True
    enable_endurance_test: bool = True
    enable_connection_churn_test: bool = True


@dataclass
class ConnectionStats:
    """Statistics for a single connection"""
    user_id: str
    connected_at: datetime
    disconnected_at: Optional[datetime] = None
    
    # Message metrics
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    
    # Latency metrics
    latencies: List[float] = field(default_factory=list)
    min_latency: float = float('inf')
    max_latency: float = 0.0
    avg_latency: float = 0.0
    
    # Error tracking
    connection_errors: int = 0
    message_errors: int = 0
    timeouts: int = 0
    
    # Connection health
    successful_connections: int = 0
    failed_connections: int = 0
    reconnections: int = 0
    
    def update_latency(self, latency_ms: float):
        """Update latency statistics"""
        self.latencies.append(latency_ms)
        self.min_latency = min(self.min_latency, latency_ms)
        self.max_latency = max(self.max_latency, latency_ms)
        self.avg_latency = sum(self.latencies) / len(self.latencies)
    
    def get_percentile_latency(self, percentile: float) -> float:
        """Get latency percentile"""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * percentile)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]


@dataclass
class LoadTestResults:
    """Results from load testing"""
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    
    # Overall metrics
    total_connections_attempted: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    peak_concurrent_connections: int = 0
    
    # Message metrics
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_bytes_transferred: int = 0
    
    # Performance metrics
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    
    # Throughput metrics
    messages_per_second: float = 0.0
    bytes_per_second: float = 0.0
    connections_per_second: float = 0.0
    
    # Error metrics
    total_errors: int = 0
    connection_error_rate: float = 0.0
    message_error_rate: float = 0.0
    timeout_rate: float = 0.0
    
    # Resource usage
    peak_cpu_usage: float = 0.0
    peak_memory_usage_mb: float = 0.0
    avg_cpu_usage: float = 0.0
    avg_memory_usage_mb: float = 0.0
    
    # Test results
    passed_latency_target: bool = False
    passed_throughput_target: bool = False
    passed_error_rate_target: bool = False
    overall_success: bool = False
    
    # Detailed stats
    connection_stats: List[ConnectionStats] = field(default_factory=list)
    timeline_metrics: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'config': {
                'server_host': self.config.server_host,
                'server_port': self.config.server_port,
                'max_connections': self.config.max_connections,
                'test_duration_seconds': self.config.test_duration_seconds,
                'target_latency_p95_ms': self.config.target_latency_p95_ms,
                'target_throughput_msg_per_sec': self.config.target_throughput_msg_per_sec,
                'target_error_rate_percent': self.config.target_error_rate_percent
            },
            'test_info': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'duration_seconds': (self.end_time - self.start_time).total_seconds()
            },
            'connection_metrics': {
                'total_attempted': self.total_connections_attempted,
                'successful': self.successful_connections,
                'failed': self.failed_connections,
                'peak_concurrent': self.peak_concurrent_connections,
                'success_rate': (self.successful_connections / max(self.total_connections_attempted, 1)) * 100
            },
            'message_metrics': {
                'total_sent': self.total_messages_sent,
                'total_received': self.total_messages_received,
                'total_bytes': self.total_bytes_transferred,
                'messages_per_second': self.messages_per_second,
                'bytes_per_second': self.bytes_per_second
            },
            'latency_metrics': {
                'avg_ms': self.avg_latency_ms,
                'p50_ms': self.p50_latency_ms,
                'p95_ms': self.p95_latency_ms,
                'p99_ms': self.p99_latency_ms,
                'max_ms': self.max_latency_ms
            },
            'error_metrics': {
                'total_errors': self.total_errors,
                'connection_error_rate': self.connection_error_rate,
                'message_error_rate': self.message_error_rate,
                'timeout_rate': self.timeout_rate
            },
            'resource_usage': {
                'peak_cpu_usage': self.peak_cpu_usage,
                'peak_memory_mb': self.peak_memory_usage_mb,
                'avg_cpu_usage': self.avg_cpu_usage,
                'avg_memory_mb': self.avg_memory_usage_mb
            },
            'test_results': {
                'passed_latency_target': self.passed_latency_target,
                'passed_throughput_target': self.passed_throughput_target,
                'passed_error_rate_target': self.passed_error_rate_target,
                'overall_success': self.overall_success
            },
            'performance_grade': self._calculate_performance_grade()
        }
    
    def _calculate_performance_grade(self) -> str:
        """Calculate overall performance grade"""
        score = 0
        
        # Latency score (40% weight)
        if self.p95_latency_ms <= self.config.target_latency_p95_ms:
            score += 40
        elif self.p95_latency_ms <= self.config.target_latency_p95_ms * 1.5:
            score += 20
        
        # Throughput score (30% weight)
        if self.messages_per_second >= self.config.target_throughput_msg_per_sec:
            score += 30
        elif self.messages_per_second >= self.config.target_throughput_msg_per_sec * 0.8:
            score += 15
        
        # Error rate score (20% weight)
        if self.connection_error_rate <= self.config.target_error_rate_percent:
            score += 20
        elif self.connection_error_rate <= self.config.target_error_rate_percent * 2:
            score += 10
        
        # Resource efficiency score (10% weight)
        if self.peak_cpu_usage <= 70 and self.peak_memory_usage_mb <= 1000:
            score += 10
        elif self.peak_cpu_usage <= 85 and self.peak_memory_usage_mb <= 2000:
            score += 5
        
        # Convert to grade
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"


class WebSocketLoadTestClient:
    """Individual WebSocket client for load testing"""
    
    def __init__(self, user_id: str, server_url: str, config: LoadTestConfig):
        self.user_id = user_id
        self.server_url = server_url
        self.config = config
        
        self.websocket = None
        self.is_connected = False
        self.stats = ConnectionStats(user_id, datetime.now())
        
        # Message tracking
        self.pending_messages: Dict[str, float] = {}  # message_id -> send_time
        self.message_queue = asyncio.Queue()
        
        # Tasks
        self.send_task = None
        self.receive_task = None
        self.ping_task = None
    
    async def connect(self) -> bool:
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(
                self.server_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
                max_size=10 * 1024 * 1024
            )
            
            # Send authentication
            auth_message = {
                'type': 'auth',
                'user_id': self.user_id,
                'role': 'load_test_user'
            }
            
            await self.websocket.send(orjson.dumps(auth_message))
            
            # Wait for auth response
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            auth_response = orjson.loads(response)
            
            if auth_response.get('type') == 'auth_success':
                self.is_connected = True
                self.stats.successful_connections += 1
                
                # Start background tasks
                self.send_task = asyncio.create_task(self._send_loop())
                self.receive_task = asyncio.create_task(self._receive_loop())
                self.ping_task = asyncio.create_task(self._ping_loop())
                
                return True
            else:
                self.stats.failed_connections += 1
                return False
                
        except Exception as e:
            logger.debug(f"Connection failed for {self.user_id}: {e}")
            self.stats.connection_errors += 1
            self.stats.failed_connections += 1
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        self.is_connected = False
        self.stats.disconnected_at = datetime.now()
        
        # Cancel tasks
        for task in [self.send_task, self.receive_task, self.ping_task]:
            if task and not task.done():
                task.cancel()
        
        # Close WebSocket
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
    
    async def send_message(self, content: dict) -> bool:
        """Send a message"""
        if not self.is_connected or not self.websocket:
            return False
        
        try:
            message_id = str(uuid.uuid4())
            message = {
                'type': 'chat_message',
                'id': message_id,
                'text': content.get('text', f'Load test message from {self.user_id}'),
                'timestamp': time.time()
            }
            
            # Track message for latency measurement
            send_time = time.time()
            self.pending_messages[message_id] = send_time
            
            # Send message
            serialized = orjson.dumps(message)
            await self.websocket.send(serialized)
            
            # Update stats
            self.stats.messages_sent += 1
            self.stats.bytes_sent += len(serialized)
            
            return True
            
        except Exception as e:
            logger.debug(f"Send error for {self.user_id}: {e}")
            self.stats.message_errors += 1
            return False
    
    async def _send_loop(self):
        """Background task for sending messages"""
        try:
            while self.is_connected:
                # Calculate message interval
                messages_per_minute = self.config.messages_per_connection_per_minute
                base_interval = 60.0 / messages_per_minute if messages_per_minute > 0 else 60.0
                
                # Add some randomness
                interval = base_interval * (0.8 + random.random() * 0.4)
                
                await asyncio.sleep(interval)
                
                if not self.is_connected:
                    break
                
                # Check for message burst
                message_count = 1
                if random.random() < self.config.message_burst_probability:
                    message_count = self.config.message_burst_size
                
                # Send messages
                for _ in range(message_count):
                    if not self.is_connected:
                        break
                    
                    # Generate message content
                    text = f"Load test message {self.stats.messages_sent + 1} from {self.user_id}"
                    if len(text) < self.config.message_size_bytes:
                        # Pad message to target size
                        padding = "x" * (self.config.message_size_bytes - len(text) - 10)
                        text += f" {padding}"
                    
                    await self.send_message({'text': text})
                    
                    if message_count > 1:
                        await asyncio.sleep(0.1)  # Small delay between burst messages
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Send loop error for {self.user_id}: {e}")
    
    async def _receive_loop(self):
        """Background task for receiving messages"""
        try:
            while self.is_connected:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=30)
                    
                    # Parse message
                    try:
                        data = orjson.loads(message)
                        await self._handle_received_message(data)
                    except orjson.JSONDecodeError:
                        self.stats.message_errors += 1
                    
                except asyncio.TimeoutError:
                    self.stats.timeouts += 1
                except ConnectionClosed:
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Receive loop error for {self.user_id}: {e}")
    
    async def _handle_received_message(self, data: dict):
        """Handle received message"""
        message_type = data.get('type')
        
        if message_type == 'chat_message':
            # Check if this is a response to our message
            message_id = data.get('id')
            if message_id in self.pending_messages:
                # Calculate latency
                send_time = self.pending_messages.pop(message_id)
                latency_ms = (time.time() - send_time) * 1000
                self.stats.update_latency(latency_ms)
            
            self.stats.messages_received += 1
            self.stats.bytes_received += len(orjson.dumps(data))
            
        elif message_type == 'pong':
            # Handle ping response
            timestamp = data.get('timestamp', 0)
            if timestamp > 0:
                latency_ms = (time.time() - timestamp) * 1000
                self.stats.update_latency(latency_ms)
    
    async def _ping_loop(self):
        """Background task for sending pings"""
        try:
            while self.is_connected:
                await asyncio.sleep(30)  # Ping every 30 seconds
                
                if not self.is_connected:
                    break
                
                try:
                    ping_message = {
                        'type': 'ping',
                        'timestamp': time.time()
                    }
                    await self.websocket.send(orjson.dumps(ping_message))
                except Exception as e:
                    logger.debug(f"Ping error for {self.user_id}: {e}")
                    
        except asyncio.CancelledError:
            pass


class WebSocketLoadTester:
    """Main load testing orchestrator"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.server_url = f"ws://{config.server_host}:{config.server_port}"
        
        # Test state
        self.clients: List[WebSocketLoadTestClient] = []
        self.active_connections = 0
        self.peak_connections = 0
        
        # Metrics collection
        self.metrics_collector = WebSocketMetricsCollector(collection_interval=1)
        self.resource_monitor_task = None
        self.resource_metrics = []
        
        # Results
        self.results = None
        self.start_time = None
        self.end_time = None
    
    async def run_load_test(self) -> LoadTestResults:
        """Run comprehensive load test"""
        logger.info("Starting WebSocket load test")
        logger.info(f"Target: {self.config.max_connections} connections, "
                   f"{self.config.test_duration_seconds}s duration")
        
        self.start_time = datetime.now()
        
        try:
            # Start metrics collection
            await self.metrics_collector.start_collection()
            self.resource_monitor_task = asyncio.create_task(self._monitor_resources())
            
            # Run test phases
            await self._warmup_phase()
            await self._main_test_phase()
            await self._cooldown_phase()
            
            # Collect results
            self.end_time = datetime.now()
            self.results = await self._compile_results()
            
            logger.info("Load test completed")
            return self.results
            
        finally:
            # Cleanup
            await self._cleanup()
    
    async def _warmup_phase(self):
        """Warmup phase - gradually increase connections"""
        logger.info("Starting warmup phase")
        
        warmup_connections = min(100, self.config.max_connections // 10)
        await self._ramp_up_connections(warmup_connections)
        
        # Let connections stabilize
        await asyncio.sleep(self.config.warmup_duration_seconds)
        
        logger.info(f"Warmup completed with {len(self.clients)} connections")
    
    async def _main_test_phase(self):
        """Main test phase - full load testing"""
        logger.info("Starting main test phase")
        
        # Ramp up to full capacity
        await self._ramp_up_connections(self.config.max_connections)
        
        # Run test scenarios
        if self.config.enable_stress_test:
            await self._stress_test()
        
        if self.config.enable_spike_test:
            await self._spike_test()
        
        if self.config.enable_endurance_test:
            await self._endurance_test()
        
        if self.config.enable_connection_churn_test:
            await self._connection_churn_test()
        
        logger.info("Main test phase completed")
    
    async def _cooldown_phase(self):
        """Cooldown phase - gradually reduce connections"""
        logger.info("Starting cooldown phase")
        
        # Gradually disconnect clients
        disconnect_batch_size = max(1, len(self.clients) // 10)
        
        while self.clients:
            batch = self.clients[:disconnect_batch_size]
            disconnect_tasks = [client.disconnect() for client in batch]
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            
            self.clients = self.clients[disconnect_batch_size:]
            self.active_connections = len(self.clients)
            
            await asyncio.sleep(1)
        
        logger.info("Cooldown completed")
    
    async def _ramp_up_connections(self, target_connections: int):
        """Gradually increase connections to target"""
        current_connections = len(self.clients)
        
        if current_connections >= target_connections:
            return
        
        connections_to_add = target_connections - current_connections
        batch_size = max(1, self.config.connection_ramp_rate)
        
        logger.info(f"Ramping up from {current_connections} to {target_connections} connections")
        
        for i in range(0, connections_to_add, batch_size):
            batch_end = min(i + batch_size, connections_to_add)
            
            # Create batch of clients
            batch_tasks = []
            for j in range(i, batch_end):
                user_id = f"load_test_user_{current_connections + j + 1}"
                client = WebSocketLoadTestClient(user_id, self.server_url, self.config)
                self.clients.append(client)
                batch_tasks.append(client.connect())
            
            # Connect batch
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Update connection count
            successful = sum(1 for result in results if result is True)
            self.active_connections = len([c for c in self.clients if c.is_connected])
            self.peak_connections = max(self.peak_connections, self.active_connections)
            
            logger.debug(f"Connected batch: {successful}/{len(batch_tasks)} successful, "
                        f"total active: {self.active_connections}")
            
            # Rate limiting
            await asyncio.sleep(1.0)
    
    async def _stress_test(self):
        """Stress test - sustained high load"""
        logger.info("Running stress test")
        
        # Increase message rate temporarily
        original_rate = self.config.messages_per_connection_per_minute
        self.config.messages_per_connection_per_minute = original_rate * 2
        
        # Run for a portion of test duration
        stress_duration = min(60, self.config.test_duration_seconds // 4)
        await asyncio.sleep(stress_duration)
        
        # Restore original rate
        self.config.messages_per_connection_per_minute = original_rate
        
        logger.info("Stress test completed")
    
    async def _spike_test(self):
        """Spike test - sudden load increase"""
        logger.info("Running spike test")
        
        # Create spike connections
        spike_connections = min(200, self.config.max_connections // 5)
        spike_clients = []
        
        # Rapid connection burst
        connect_tasks = []
        for i in range(spike_connections):
            user_id = f"spike_user_{i}"
            client = WebSocketLoadTestClient(user_id, self.server_url, self.config)
            spike_clients.append(client)
            connect_tasks.append(client.connect())
        
        # Connect all at once
        await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        # Hold spike for short duration
        await asyncio.sleep(30)
        
        # Disconnect spike clients
        disconnect_tasks = [client.disconnect() for client in spike_clients]
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        logger.info("Spike test completed")
    
    async def _endurance_test(self):
        """Endurance test - sustained load over time"""
        logger.info("Running endurance test")
        
        # Run for majority of test duration
        endurance_duration = max(120, self.config.test_duration_seconds // 2)
        
        # Monitor for connection stability
        start_connections = self.active_connections
        
        await asyncio.sleep(endurance_duration)
        
        end_connections = len([c for c in self.clients if c.is_connected])
        connection_stability = (end_connections / max(start_connections, 1)) * 100
        
        logger.info(f"Endurance test completed - connection stability: {connection_stability:.1f}%")
    
    async def _connection_churn_test(self):
        """Connection churn test - frequent connect/disconnect"""
        logger.info("Running connection churn test")
        
        churn_duration = 60  # 1 minute of churn
        churn_rate = 10      # connections per second
        
        start_time = time.time()
        
        while time.time() - start_time < churn_duration:
            # Disconnect some clients
            if self.clients:
                disconnect_count = min(churn_rate, len(self.clients) // 10)
                clients_to_disconnect = self.clients[:disconnect_count]
                
                disconnect_tasks = [client.disconnect() for client in clients_to_disconnect]
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
                
                # Remove from active list
                self.clients = self.clients[disconnect_count:]
            
            # Connect new clients
            connect_tasks = []
            for i in range(churn_rate):
                user_id = f"churn_user_{int(time.time())}_{i}"
                client = WebSocketLoadTestClient(user_id, self.server_url, self.config)
                self.clients.append(client)
                connect_tasks.append(client.connect())
            
            await asyncio.gather(*connect_tasks, return_exceptions=True)
            
            # Update active connections
            self.active_connections = len([c for c in self.clients if c.is_connected])
            
            await asyncio.sleep(1)
        
        logger.info("Connection churn test completed")
    
    async def _monitor_resources(self):
        """Monitor system resources during test"""
        try:
            while True:
                # Collect resource metrics
                process = psutil.Process()
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                # System metrics
                system_memory = psutil.virtual_memory()
                
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'system_memory_percent': system_memory.percent,
                    'active_connections': self.active_connections,
                    'total_clients': len(self.clients)
                }
                
                self.resource_metrics.append(metrics)
                
                await asyncio.sleep(5)  # Collect every 5 seconds
                
        except asyncio.CancelledError:
            pass
    
    async def _compile_results(self) -> LoadTestResults:
        """Compile test results"""
        logger.info("Compiling test results")
        
        # Aggregate connection stats
        all_latencies = []
        total_messages_sent = 0
        total_messages_received = 0
        total_bytes_transferred = 0
        total_errors = 0
        successful_connections = 0
        failed_connections = 0
        
        for client in self.clients:
            stats = client.stats
            
            all_latencies.extend(stats.latencies)
            total_messages_sent += stats.messages_sent
            total_messages_received += stats.messages_received
            total_bytes_transferred += stats.bytes_sent + stats.bytes_received
            total_errors += stats.connection_errors + stats.message_errors + stats.timeouts
            successful_connections += stats.successful_connections
            failed_connections += stats.failed_connections
        
        # Calculate latency percentiles
        if all_latencies:
            sorted_latencies = sorted(all_latencies)
            avg_latency = statistics.mean(sorted_latencies)
            p50_latency = statistics.median(sorted_latencies)
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]
            max_latency = max(sorted_latencies)
        else:
            avg_latency = p50_latency = p95_latency = p99_latency = max_latency = 0.0
        
        # Calculate rates
        test_duration = (self.end_time - self.start_time).total_seconds()
        messages_per_second = total_messages_sent / max(test_duration, 1)
        bytes_per_second = total_bytes_transferred / max(test_duration, 1)
        
        # Calculate error rates
        total_attempts = len(self.clients)
        connection_error_rate = (failed_connections / max(total_attempts, 1)) * 100
        message_error_rate = (total_errors / max(total_messages_sent + total_messages_received, 1)) * 100
        
        # Resource usage
        if self.resource_metrics:
            peak_cpu = max(m['cpu_percent'] for m in self.resource_metrics)
            peak_memory = max(m['memory_mb'] for m in self.resource_metrics)
            avg_cpu = statistics.mean(m['cpu_percent'] for m in self.resource_metrics)
            avg_memory = statistics.mean(m['memory_mb'] for m in self.resource_metrics)
        else:
            peak_cpu = avg_cpu = peak_memory = avg_memory = 0.0
        
        # Evaluate against targets
        passed_latency = p95_latency <= self.config.target_latency_p95_ms
        passed_throughput = messages_per_second >= self.config.target_throughput_msg_per_sec
        passed_error_rate = connection_error_rate <= self.config.target_error_rate_percent
        
        overall_success = passed_latency and passed_throughput and passed_error_rate
        
        # Create results object
        results = LoadTestResults(
            config=self.config,
            start_time=self.start_time,
            end_time=self.end_time,
            total_connections_attempted=total_attempts,
            successful_connections=successful_connections,
            failed_connections=failed_connections,
            peak_concurrent_connections=self.peak_connections,
            total_messages_sent=total_messages_sent,
            total_messages_received=total_messages_received,
            total_bytes_transferred=total_bytes_transferred,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_latency_ms=max_latency,
            messages_per_second=messages_per_second,
            bytes_per_second=bytes_per_second,
            total_errors=total_errors,
            connection_error_rate=connection_error_rate,
            message_error_rate=message_error_rate,
            peak_cpu_usage=peak_cpu,
            peak_memory_usage_mb=peak_memory,
            avg_cpu_usage=avg_cpu,
            avg_memory_usage_mb=avg_memory,
            passed_latency_target=passed_latency,
            passed_throughput_target=passed_throughput,
            passed_error_rate_target=passed_error_rate,
            overall_success=overall_success,
            connection_stats=[client.stats for client in self.clients],
            timeline_metrics=self.resource_metrics
        )
        
        return results
    
    async def _cleanup(self):
        """Cleanup resources"""
        # Stop metrics collection
        await self.metrics_collector.stop_collection()
        
        # Cancel resource monitoring
        if self.resource_monitor_task:
            self.resource_monitor_task.cancel()
            try:
                await self.resource_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect remaining clients
        if self.clients:
            disconnect_tasks = [client.disconnect() for client in self.clients]
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        logger.info("Load test cleanup completed")


async def run_websocket_load_test(config: LoadTestConfig = None) -> LoadTestResults:
    """Run WebSocket load test with specified configuration"""
    if config is None:
        config = LoadTestConfig()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run load tester
    load_tester = WebSocketLoadTester(config)
    results = await load_tester.run_load_test()
    
    # Print summary
    print("\n" + "="*80)
    print("WEBSOCKET LOAD TEST RESULTS")
    print("="*80)
    print(f"Test Duration: {(results.end_time - results.start_time).total_seconds():.1f} seconds")
    print(f"Peak Connections: {results.peak_concurrent_connections}")
    print(f"Messages Sent: {results.total_messages_sent:,}")
    print(f"Throughput: {results.messages_per_second:.1f} msg/sec")
    print(f"Latency P95: {results.p95_latency_ms:.1f}ms")
    print(f"Latency P99: {results.p99_latency_ms:.1f}ms")
    print(f"Error Rate: {results.connection_error_rate:.2f}%")
    print(f"Peak CPU: {results.peak_cpu_usage:.1f}%")
    print(f"Peak Memory: {results.peak_memory_usage_mb:.1f}MB")
    print(f"Performance Grade: {results._calculate_performance_grade()}")
    print(f"Overall Success: {'✅ PASS' if results.overall_success else '❌ FAIL'}")
    print("="*80)
    
    return results


if __name__ == "__main__":
    # Example usage
    config = LoadTestConfig(
        max_connections=1000,
        test_duration_seconds=300,
        messages_per_connection_per_minute=20,
        target_latency_p95_ms=100.0,
        target_throughput_msg_per_sec=1000.0
    )
    
    # Run the test
    results = asyncio.run(run_websocket_load_test(config))
    
    # Save results to file
    import json
    with open(f"load_test_results_{int(time.time())}.json", 'w') as f:
        json.dump(results.to_dict(), f, indent=2, default=str)
    
    print(f"\nResults saved to load_test_results_{int(time.time())}.json")