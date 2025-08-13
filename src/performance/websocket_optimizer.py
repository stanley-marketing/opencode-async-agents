# SPDX-License-Identifier: MIT
"""
High-Performance WebSocket Optimizer for OpenCode-Slack
Optimizes WebSocket connections for 1000+ concurrent users with <100ms latency
"""

import asyncio
import json
import logging
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable, Tuple
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException
import uvloop
import orjson  # Fast JSON serialization
import lz4.frame  # Fast compression
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    from .connection_pool import WebSocketConnectionPool
    from .message_queue import HighPerformanceMessageQueue
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from connection_pool import WebSocketConnectionPool
    from message_queue import HighPerformanceMessageQueue

try:
    from ..monitoring.production_metrics_collector import MetricsCollector
except ImportError:
    # Create a simple metrics collector fallback
    class MetricsCollector:
        def __init__(self):
            pass
        def collect_metric(self, *args, **kwargs):
            pass

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    connections_count: int = 0
    messages_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_received: int = 0
    error_rate_percent: float = 0.0
    throughput_mbps: float = 0.0
    
    # Advanced metrics
    connection_pool_utilization: float = 0.0
    message_queue_depth: int = 0
    serialization_time_ms: float = 0.0
    compression_ratio: float = 0.0
    gc_collections: int = 0
    
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConnectionStats:
    """Per-connection statistics"""
    user_id: str
    connected_at: datetime
    last_activity: datetime
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    avg_latency_ms: float = 0.0
    error_count: int = 0
    
    def update_activity(self):
        self.last_activity = datetime.now()


class OptimizedWebSocketConnection:
    """High-performance WebSocket connection wrapper"""
    
    def __init__(self, websocket: WebSocketServerProtocol, user_id: str, 
                 role: str = "user", compression_enabled: bool = True):
        self.websocket = websocket
        self.user_id = user_id
        self.role = role
        self.compression_enabled = compression_enabled
        
        # Performance tracking
        self.stats = ConnectionStats(user_id, datetime.now(), datetime.now())
        self.latency_samples = deque(maxlen=100)  # Keep last 100 latency samples
        
        # Message buffering for batch sending
        self.message_buffer = []
        self.buffer_lock = asyncio.Lock()
        self.last_flush = time.time()
        
        # Connection health
        self.is_healthy = True
        self.last_ping = time.time()
        self.ping_failures = 0
        
    async def send_message(self, message: dict, priority: int = 1) -> bool:
        """Send message with performance optimizations"""
        start_time = time.time()
        
        try:
            # Serialize with fast JSON
            serialized = orjson.dumps(message)
            
            # Compress if enabled and message is large enough
            if self.compression_enabled and len(serialized) > 1024:
                compressed = lz4.frame.compress(serialized)
                if len(compressed) < len(serialized):
                    serialized = compressed
                    message['_compressed'] = True
            
            # Send message
            await self.websocket.send(serialized)
            
            # Update statistics
            latency_ms = (time.time() - start_time) * 1000
            self.latency_samples.append(latency_ms)
            self.stats.messages_sent += 1
            self.stats.bytes_sent += len(serialized)
            self.stats.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
            self.stats.update_activity()
            
            return True
            
        except (ConnectionClosed, WebSocketException) as e:
            logger.warning(f"Failed to send message to {self.user_id}: {e}")
            self.stats.error_count += 1
            self.is_healthy = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to {self.user_id}: {e}")
            self.stats.error_count += 1
            return False
    
    async def send_batch(self, messages: List[dict]) -> int:
        """Send multiple messages in a batch for better performance"""
        if not messages:
            return 0
            
        successful = 0
        for message in messages:
            if await self.send_message(message):
                successful += 1
            else:
                break  # Stop on first failure
                
        return successful
    
    async def ping_check(self) -> bool:
        """Perform health check ping"""
        try:
            pong_waiter = await self.websocket.ping()
            await asyncio.wait_for(pong_waiter, timeout=5.0)
            self.last_ping = time.time()
            self.ping_failures = 0
            self.is_healthy = True
            return True
        except Exception:
            self.ping_failures += 1
            if self.ping_failures >= 3:
                self.is_healthy = False
            return False
    
    def get_performance_stats(self) -> dict:
        """Get connection performance statistics"""
        return {
            'user_id': self.user_id,
            'role': self.role,
            'connected_duration_seconds': (datetime.now() - self.stats.connected_at).total_seconds(),
            'messages_sent': self.stats.messages_sent,
            'messages_received': self.stats.messages_received,
            'bytes_sent': self.stats.bytes_sent,
            'bytes_received': self.stats.bytes_received,
            'avg_latency_ms': self.stats.avg_latency_ms,
            'p95_latency_ms': sorted(self.latency_samples)[int(len(self.latency_samples) * 0.95)] if self.latency_samples else 0,
            'error_count': self.stats.error_count,
            'is_healthy': self.is_healthy,
            'ping_failures': self.ping_failures,
            'compression_enabled': self.compression_enabled
        }


class HighPerformanceWebSocketManager:
    """Ultra-high performance WebSocket manager for 1000+ concurrent users"""
    
    def __init__(self, host="0.0.0.0", port=8765, max_connections=2000):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        
        # Use uvloop for better performance
        if hasattr(asyncio, 'set_event_loop_policy'):
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        
        # Core components
        self.connection_pool = WebSocketConnectionPool(max_connections)
        self.message_queue = HighPerformanceMessageQueue()
        self.metrics_collector = MetricsCollector()
        
        # Connection management
        self.connections: Dict[str, OptimizedWebSocketConnection] = {}
        self.connection_groups: Dict[str, Set[str]] = defaultdict(set)  # Group connections by role
        self.weak_connections = weakref.WeakValueDictionary()  # Prevent memory leaks
        
        # Performance optimization
        self.thread_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="ws-worker")
        self.serialization_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="serialize")
        
        # Server state
        self.server = None
        self.is_running = False
        self.start_time = None
        
        # Performance monitoring
        self.metrics = PerformanceMetrics()
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 metric snapshots
        self.performance_monitor_task = None
        
        # Message handlers
        self.message_handlers: List[Callable] = []
        
        # Rate limiting and throttling
        self.rate_limiters: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.global_rate_limit = 10000  # messages per second globally
        self.per_user_rate_limit = 100   # messages per minute per user
        
        # Batch processing
        self.batch_size = 50
        self.batch_timeout = 0.01  # 10ms
        self.pending_broadcasts = []
        self.broadcast_task = None
        
        # Health monitoring
        self.health_check_interval = 30  # seconds
        self.health_check_task = None
        
        # Compression settings
        self.compression_threshold = 1024  # bytes
        self.compression_enabled = True
        
    async def start_server(self) -> bool:
        """Start the high-performance WebSocket server"""
        try:
            logger.info(f"Starting high-performance WebSocket server on {self.host}:{self.port}")
            
            # Configure server with performance optimizations
            server_config = {
                'host': self.host,
                'port': self.port,
                'ping_interval': 20,
                'ping_timeout': 10,
                'close_timeout': 10,
                'max_size': 10 * 1024 * 1024,  # 10MB max message size
                'max_queue': 1000,
                'compression': 'deflate' if self.compression_enabled else None,
                'process_request': self._process_request,
                'select_subprotocol': self._select_subprotocol,
            }
            
            # Start server
            self.server = await websockets.serve(
                self._handle_connection,
                **server_config
            )
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # Start background tasks
            await self._start_background_tasks()
            
            logger.info(f"High-performance WebSocket server started successfully")
            logger.info(f"Server configuration: max_connections={self.max_connections}, "
                       f"compression={'enabled' if self.compression_enabled else 'disabled'}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            self.is_running = False
            return False
    
    async def stop_server(self):
        """Stop the WebSocket server gracefully"""
        logger.info("Stopping high-performance WebSocket server...")
        
        self.is_running = False
        
        # Stop background tasks
        await self._stop_background_tasks()
        
        # Close all connections gracefully
        await self._close_all_connections()
        
        # Stop server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Shutdown thread pools
        self.thread_pool.shutdown(wait=True)
        self.serialization_pool.shutdown(wait=True)
        
        logger.info("WebSocket server stopped successfully")
    
    async def _start_background_tasks(self):
        """Start background monitoring and optimization tasks"""
        self.performance_monitor_task = asyncio.create_task(self._performance_monitor_loop())
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        self.broadcast_task = asyncio.create_task(self._batch_broadcast_loop())
        
        # Start message queue processor
        await self.message_queue.start_processor()
    
    async def _stop_background_tasks(self):
        """Stop all background tasks"""
        tasks = [
            self.performance_monitor_task,
            self.health_check_task,
            self.broadcast_task
        ]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        await self.message_queue.stop_processor()
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection with optimizations"""
        connection_id = f"conn_{int(time.time() * 1000000)}"
        user_id = None
        connection = None
        
        try:
            # Check connection limits
            if len(self.connections) >= self.max_connections:
                await websocket.send(orjson.dumps({
                    'type': 'error',
                    'message': 'Server at capacity',
                    'code': 'CAPACITY_EXCEEDED'
                }))
                await websocket.close(code=1013, reason="Server at capacity")
                return
            
            logger.debug(f"New WebSocket connection: {connection_id}")
            
            # Fast authentication with timeout
            auth_data = await asyncio.wait_for(
                websocket.recv(), 
                timeout=10  # Reduced from 30s for faster rejection
            )
            
            # Fast JSON parsing
            try:
                auth_message = orjson.loads(auth_data)
            except orjson.JSONDecodeError:
                await websocket.send(orjson.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON in authentication'
                }))
                return
            
            # Validate authentication
            if auth_message.get('type') != 'auth':
                await websocket.send(orjson.dumps({
                    'type': 'error',
                    'message': 'Authentication required'
                }))
                return
            
            user_id = auth_message.get('user_id')
            role = auth_message.get('role', 'user')
            
            if not user_id:
                await websocket.send(orjson.dumps({
                    'type': 'error',
                    'message': 'User ID required'
                }))
                return
            
            # Check for existing connection (replace if exists)
            if user_id in self.connections:
                old_connection = self.connections[user_id]
                await old_connection.websocket.close(code=1000, reason="Replaced by new connection")
                del self.connections[user_id]
            
            # Create optimized connection
            connection = OptimizedWebSocketConnection(
                websocket, user_id, role, 
                compression_enabled=self.compression_enabled
            )
            
            # Add to connection pool
            await self.connection_pool.add_connection(connection)
            self.connections[user_id] = connection
            self.connection_groups[role].add(user_id)
            self.weak_connections[user_id] = connection
            
            # Send authentication success
            await connection.send_message({
                'type': 'auth_success',
                'user_id': user_id,
                'role': role,
                'server_time': datetime.now().isoformat(),
                'server_capabilities': {
                    'compression': self.compression_enabled,
                    'batch_messaging': True,
                    'high_performance': True
                }
            })
            
            # Broadcast user connected (async)
            asyncio.create_task(self._broadcast_user_status(user_id, 'connected', role))
            
            logger.info(f"User {user_id} authenticated successfully (role: {role})")
            
            # Handle messages from this connection
            async for raw_message in websocket:
                try:
                    await self._handle_message(connection, raw_message)
                except Exception as e:
                    logger.error(f"Error handling message from {user_id}: {e}")
                    connection.stats.error_count += 1
                    
        except asyncio.TimeoutError:
            logger.warning(f"Authentication timeout for connection {connection_id}")
        except ConnectionClosed:
            logger.debug(f"Connection {connection_id} closed during handshake")
        except Exception as e:
            logger.error(f"Error in connection {connection_id}: {e}")
        finally:
            # Clean up connection
            if user_id and user_id in self.connections:
                await self._cleanup_connection(user_id)
    
    async def _handle_message(self, connection: OptimizedWebSocketConnection, raw_message: bytes):
        """Handle incoming message with performance optimizations"""
        start_time = time.time()
        
        try:
            # Check rate limiting
            if not self._check_rate_limit(connection.user_id):
                await connection.send_message({
                    'type': 'error',
                    'message': 'Rate limit exceeded',
                    'code': 'RATE_LIMITED'
                })
                return
            
            # Fast JSON parsing
            try:
                if isinstance(raw_message, bytes):
                    # Check if compressed
                    try:
                        # Try to decompress first
                        decompressed = lz4.frame.decompress(raw_message)
                        message_data = orjson.loads(decompressed)
                    except:
                        # Not compressed, parse directly
                        message_data = orjson.loads(raw_message)
                else:
                    message_data = orjson.loads(raw_message)
            except orjson.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {connection.user_id}: {e}")
                await connection.send_message({
                    'type': 'error',
                    'message': 'Invalid JSON format'
                })
                return
            
            # Update connection stats
            connection.stats.messages_received += 1
            connection.stats.bytes_received += len(raw_message)
            connection.stats.update_activity()
            
            # Route message based on type
            message_type = message_data.get('type')
            
            if message_type == 'chat_message':
                await self._process_chat_message(connection, message_data)
            elif message_type == 'ping':
                await connection.send_message({'type': 'pong', 'timestamp': time.time()})
            elif message_type == 'typing':
                await self._handle_typing_indicator(connection, message_data)
            elif message_type == 'batch':
                await self._handle_batch_messages(connection, message_data)
            else:
                logger.warning(f"Unknown message type from {connection.user_id}: {message_type}")
            
            # Record processing time
            processing_time = (time.time() - start_time) * 1000
            if processing_time > 50:  # Log slow messages
                logger.warning(f"Slow message processing: {processing_time:.2f}ms for {message_type}")
                
        except Exception as e:
            logger.error(f"Error processing message from {connection.user_id}: {e}")
            connection.stats.error_count += 1
    
    async def _process_chat_message(self, connection: OptimizedWebSocketConnection, message_data: dict):
        """Process chat message with high performance"""
        text = message_data.get('text', '').strip()
        if not text:
            return
        
        # Add to high-performance message queue
        await self.message_queue.enqueue({
            'type': 'chat_message',
            'user_id': connection.user_id,
            'role': connection.role,
            'text': text,
            'timestamp': time.time(),
            'message_data': message_data
        })
        
        # Broadcast to other users (async, non-blocking)
        broadcast_message = {
            'type': 'chat_message',
            'data': {
                'text': text,
                'sender': connection.user_id,
                'role': connection.role,
                'timestamp': datetime.now().isoformat(),
                'reply_to': message_data.get('reply_to')
            }
        }
        
        # Add to batch broadcast queue
        self.pending_broadcasts.append((broadcast_message, connection.user_id))
    
    async def _handle_batch_messages(self, connection: OptimizedWebSocketConnection, message_data: dict):
        """Handle batch message processing"""
        messages = message_data.get('messages', [])
        if not messages:
            return
        
        # Process messages in batch
        results = []
        for msg in messages[:self.batch_size]:  # Limit batch size
            try:
                await self._handle_message(connection, orjson.dumps(msg))
                results.append({'status': 'success'})
            except Exception as e:
                results.append({'status': 'error', 'message': str(e)})
        
        # Send batch response
        await connection.send_message({
            'type': 'batch_response',
            'results': results
        })
    
    async def _batch_broadcast_loop(self):
        """Batch broadcast loop for better performance"""
        while self.is_running:
            try:
                if self.pending_broadcasts:
                    # Process broadcasts in batches
                    current_batch = self.pending_broadcasts[:self.batch_size]
                    self.pending_broadcasts = self.pending_broadcasts[self.batch_size:]
                    
                    # Group by message type for efficiency
                    grouped_messages = defaultdict(list)
                    for message, exclude_user in current_batch:
                        grouped_messages[message['type']].append((message, exclude_user))
                    
                    # Broadcast each group
                    for message_type, messages in grouped_messages.items():
                        await self._batch_broadcast_messages(messages)
                
                await asyncio.sleep(self.batch_timeout)
                
            except Exception as e:
                logger.error(f"Error in batch broadcast loop: {e}")
                await asyncio.sleep(1)
    
    async def _batch_broadcast_messages(self, messages: List[Tuple[dict, str]]):
        """Broadcast messages in batch for better performance"""
        if not messages:
            return
        
        # Prepare connection list (exclude senders)
        exclude_users = {exclude_user for _, exclude_user in messages}
        target_connections = [
            conn for user_id, conn in self.connections.items()
            if user_id not in exclude_users and conn.is_healthy
        ]
        
        # Send to all target connections concurrently
        tasks = []
        for message, _ in messages:
            for connection in target_connections:
                tasks.append(connection.send_message(message))
        
        # Execute all sends concurrently with limited concurrency
        if tasks:
            # Process in chunks to avoid overwhelming the system
            chunk_size = 100
            for i in range(0, len(tasks), chunk_size):
                chunk = tasks[i:i + chunk_size]
                await asyncio.gather(*chunk, return_exceptions=True)
    
    async def _performance_monitor_loop(self):
        """Monitor and collect performance metrics"""
        while self.is_running:
            try:
                # Collect current metrics
                current_metrics = await self._collect_performance_metrics()
                self.metrics = current_metrics
                self.metrics_history.append(current_metrics)
                
                # Log performance summary every minute
                if len(self.metrics_history) % 60 == 0:
                    await self._log_performance_summary()
                
                # Check for performance issues
                await self._check_performance_alerts()
                
                await asyncio.sleep(1)  # Collect metrics every second
                
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
                await asyncio.sleep(5)
    
    async def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect comprehensive performance metrics"""
        # System metrics
        process = psutil.Process()
        cpu_percent = process.cpu_percent()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Connection metrics
        connections_count = len(self.connections)
        healthy_connections = sum(1 for conn in self.connections.values() if conn.is_healthy)
        
        # Calculate latency percentiles
        all_latencies = []
        for conn in self.connections.values():
            all_latencies.extend(conn.latency_samples)
        
        if all_latencies:
            sorted_latencies = sorted(all_latencies)
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]
            avg_latency = sum(sorted_latencies) / len(sorted_latencies)
        else:
            p95_latency = p99_latency = avg_latency = 0.0
        
        # Message throughput
        total_messages = sum(conn.stats.messages_sent + conn.stats.messages_received 
                           for conn in self.connections.values())
        
        if len(self.metrics_history) > 0:
            time_diff = (datetime.now() - self.metrics_history[-1].timestamp).total_seconds()
            if time_diff > 0:
                prev_total = (self.metrics_history[-1].network_bytes_sent + 
                            self.metrics_history[-1].network_bytes_received)
                current_total = sum(conn.stats.bytes_sent + conn.stats.bytes_received 
                                  for conn in self.connections.values())
                messages_per_second = (current_total - prev_total) / time_diff
            else:
                messages_per_second = 0.0
        else:
            messages_per_second = 0.0
        
        # Network metrics
        total_bytes_sent = sum(conn.stats.bytes_sent for conn in self.connections.values())
        total_bytes_received = sum(conn.stats.bytes_received for conn in self.connections.values())
        
        # Error rate
        total_errors = sum(conn.stats.error_count for conn in self.connections.values())
        error_rate = (total_errors / max(total_messages, 1)) * 100
        
        # Queue metrics
        queue_depth = await self.message_queue.get_queue_depth()
        pool_utilization = self.connection_pool.get_utilization()
        
        return PerformanceMetrics(
            connections_count=connections_count,
            messages_per_second=messages_per_second,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            cpu_usage_percent=cpu_percent,
            memory_usage_mb=memory_mb,
            network_bytes_sent=total_bytes_sent,
            network_bytes_received=total_bytes_received,
            error_rate_percent=error_rate,
            connection_pool_utilization=pool_utilization,
            message_queue_depth=queue_depth,
            timestamp=datetime.now()
        )
    
    async def _health_check_loop(self):
        """Perform periodic health checks on connections"""
        while self.is_running:
            try:
                # Check connection health
                unhealthy_connections = []
                
                for user_id, connection in list(self.connections.items()):
                    if not connection.is_healthy:
                        unhealthy_connections.append(user_id)
                        continue
                    
                    # Perform ping check every 30 seconds
                    if time.time() - connection.last_ping > self.health_check_interval:
                        if not await connection.ping_check():
                            unhealthy_connections.append(user_id)
                
                # Clean up unhealthy connections
                for user_id in unhealthy_connections:
                    await self._cleanup_connection(user_id)
                
                if unhealthy_connections:
                    logger.info(f"Cleaned up {len(unhealthy_connections)} unhealthy connections")
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(10)
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limits"""
        now = time.time()
        user_requests = self.rate_limiters[user_id]
        
        # Remove old requests (older than 1 minute)
        while user_requests and now - user_requests[0] > 60:
            user_requests.popleft()
        
        # Check if under limit
        if len(user_requests) >= self.per_user_rate_limit:
            return False
        
        # Add current request
        user_requests.append(now)
        return True
    
    async def _cleanup_connection(self, user_id: str):
        """Clean up a connection and its resources"""
        if user_id not in self.connections:
            return
        
        connection = self.connections[user_id]
        
        try:
            # Remove from connection pool
            await self.connection_pool.remove_connection(connection)
            
            # Remove from groups
            for group_connections in self.connection_groups.values():
                group_connections.discard(user_id)
            
            # Close WebSocket
            if not connection.websocket.closed:
                await connection.websocket.close(code=1000, reason="Connection cleanup")
            
            # Remove from connections
            del self.connections[user_id]
            
            # Broadcast user disconnected
            asyncio.create_task(self._broadcast_user_status(user_id, 'disconnected'))
            
            logger.debug(f"Cleaned up connection for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up connection for {user_id}: {e}")
    
    async def _close_all_connections(self):
        """Close all WebSocket connections gracefully"""
        if not self.connections:
            return
        
        logger.info(f"Closing {len(self.connections)} connections...")
        
        # Send shutdown notice to all connections
        shutdown_message = {
            'type': 'server_shutdown',
            'message': 'Server is shutting down',
            'timestamp': datetime.now().isoformat()
        }
        
        # Send shutdown notice concurrently
        tasks = []
        for connection in self.connections.values():
            tasks.append(connection.send_message(shutdown_message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Close all connections
        close_tasks = []
        for connection in self.connections.values():
            if not connection.websocket.closed:
                close_tasks.append(connection.websocket.close(code=1001, reason="Server shutdown"))
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.connections.clear()
        logger.info("All connections closed")
    
    async def _broadcast_user_status(self, user_id: str, status: str, role: str = None):
        """Broadcast user status change"""
        status_message = {
            'type': 'user_status',
            'data': {
                'user_id': user_id,
                'status': status,
                'role': role,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        self.pending_broadcasts.append((status_message, None))  # Broadcast to all
    
    async def _log_performance_summary(self):
        """Log performance summary"""
        metrics = self.metrics
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        logger.info(
            f"Performance Summary - "
            f"Connections: {metrics.connections_count}, "
            f"Msg/s: {metrics.messages_per_second:.1f}, "
            f"Latency: {metrics.avg_latency_ms:.1f}ms (P95: {metrics.p95_latency_ms:.1f}ms), "
            f"CPU: {metrics.cpu_usage_percent:.1f}%, "
            f"Memory: {metrics.memory_usage_mb:.1f}MB, "
            f"Error Rate: {metrics.error_rate_percent:.2f}%, "
            f"Uptime: {uptime:.0f}s"
        )
    
    async def _check_performance_alerts(self):
        """Check for performance issues and alert"""
        metrics = self.metrics
        
        # High latency alert
        if metrics.p95_latency_ms > 100:
            logger.warning(f"High latency detected: P95 = {metrics.p95_latency_ms:.1f}ms")
        
        # High CPU usage alert
        if metrics.cpu_usage_percent > 80:
            logger.warning(f"High CPU usage: {metrics.cpu_usage_percent:.1f}%")
        
        # High memory usage alert
        if metrics.memory_usage_mb > 1000:
            logger.warning(f"High memory usage: {metrics.memory_usage_mb:.1f}MB")
        
        # High error rate alert
        if metrics.error_rate_percent > 5:
            logger.warning(f"High error rate: {metrics.error_rate_percent:.2f}%")
        
        # Connection limit alert
        if metrics.connections_count > self.max_connections * 0.9:
            logger.warning(f"Approaching connection limit: {metrics.connections_count}/{self.max_connections}")
    
    def _process_request(self, path, headers):
        """Process WebSocket request for optimization"""
        # Add custom headers for performance monitoring
        return None
    
    def _select_subprotocol(self, subprotocols):
        """Select WebSocket subprotocol"""
        # Prefer high-performance protocols
        if 'opencode-hp' in subprotocols:
            return 'opencode-hp'
        return None
    
    # Public API methods
    
    def add_message_handler(self, handler: Callable):
        """Add message handler"""
        self.message_handlers.append(handler)
    
    async def send_message_to_user(self, user_id: str, message: dict) -> bool:
        """Send message to specific user"""
        if user_id not in self.connections:
            return False
        
        connection = self.connections[user_id]
        return await connection.send_message(message)
    
    async def send_message_to_role(self, role: str, message: dict) -> int:
        """Send message to all users with specific role"""
        if role not in self.connection_groups:
            return 0
        
        tasks = []
        for user_id in self.connection_groups[role]:
            if user_id in self.connections:
                tasks.append(self.connections[user_id].send_message(message))
        
        if not tasks:
            return 0
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for result in results if result is True)
    
    async def broadcast_message(self, message: dict, exclude_user: str = None) -> int:
        """Broadcast message to all connected users"""
        self.pending_broadcasts.append((message, exclude_user))
        return len(self.connections)
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        return self.metrics
    
    def get_connection_stats(self) -> List[dict]:
        """Get statistics for all connections"""
        return [conn.get_performance_stats() for conn in self.connections.values()]
    
    def get_server_info(self) -> dict:
        """Get server information"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            'is_running': self.is_running,
            'host': self.host,
            'port': self.port,
            'max_connections': self.max_connections,
            'current_connections': len(self.connections),
            'uptime_seconds': uptime,
            'compression_enabled': self.compression_enabled,
            'performance_optimized': True,
            'version': '2.0.0-hp'
        }