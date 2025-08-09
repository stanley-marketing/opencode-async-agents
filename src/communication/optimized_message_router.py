#!/usr/bin/env python3
"""
Optimized Message Router for Real-time Communication
Implements high-performance message routing with queuing, batching, and load balancing.
"""

import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
import queue
import json
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Optimized message structure"""
    id: str
    content: str
    sender: str
    recipient: str
    priority: int = 1  # 1=low, 2=normal, 3=high, 4=critical
    timestamp: datetime = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class RouteMetrics:
    """Metrics for message routing performance"""
    messages_sent: int = 0
    messages_failed: int = 0
    total_latency: float = 0.0
    peak_queue_size: int = 0
    throughput_per_second: float = 0.0
    last_update: datetime = None
    
    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now()

class MessageQueue:
    """High-performance priority message queue"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.queues = {
            4: deque(),  # Critical
            3: deque(),  # High
            2: deque(),  # Normal
            1: deque()   # Low
        }
        self.lock = threading.RLock()
        self.not_empty = threading.Condition(self.lock)
        self.not_full = threading.Condition(self.lock)
        self.size = 0
        
    def put(self, message: Message, timeout: Optional[float] = None) -> bool:
        """Add message to queue with priority ordering"""
        with self.not_full:
            if timeout is not None:
                end_time = time.time() + timeout
                while self.size >= self.max_size:
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return False
                    self.not_full.wait(remaining)
            else:
                while self.size >= self.max_size:
                    self.not_full.wait()
            
            self.queues[message.priority].append(message)
            self.size += 1
            self.not_empty.notify()
            return True
    
    def get(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Get highest priority message from queue"""
        with self.not_empty:
            if timeout is not None:
                end_time = time.time() + timeout
                while self.size == 0:
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return None
                    self.not_empty.wait(remaining)
            else:
                while self.size == 0:
                    self.not_empty.wait()
            
            # Get from highest priority queue first
            for priority in [4, 3, 2, 1]:
                if self.queues[priority]:
                    message = self.queues[priority].popleft()
                    self.size -= 1
                    self.not_full.notify()
                    return message
            
            return None
    
    def qsize(self) -> int:
        """Get current queue size"""
        with self.lock:
            return self.size
    
    def empty(self) -> bool:
        """Check if queue is empty"""
        with self.lock:
            return self.size == 0

class MessageBatcher:
    """Batches messages for efficient delivery"""
    
    def __init__(self, batch_size: int = 10, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batches: Dict[str, List[Message]] = defaultdict(list)
        self.batch_timers: Dict[str, threading.Timer] = {}
        self.lock = threading.RLock()
        self.batch_callback: Optional[Callable] = None
    
    def set_batch_callback(self, callback: Callable[[str, List[Message]], None]):
        """Set callback for when batch is ready"""
        self.batch_callback = callback
    
    def add_message(self, message: Message):
        """Add message to batch"""
        with self.lock:
            recipient = message.recipient
            self.batches[recipient].append(message)
            
            # Check if batch is full
            if len(self.batches[recipient]) >= self.batch_size:
                self._flush_batch(recipient)
            else:
                # Set timer for batch timeout
                if recipient in self.batch_timers:
                    self.batch_timers[recipient].cancel()
                
                timer = threading.Timer(
                    self.batch_timeout,
                    lambda: self._flush_batch(recipient)
                )
                timer.start()
                self.batch_timers[recipient] = timer
    
    def _flush_batch(self, recipient: str):
        """Flush batch for recipient"""
        with self.lock:
            if recipient in self.batches and self.batches[recipient]:
                batch = self.batches[recipient].copy()
                self.batches[recipient].clear()
                
                # Cancel timer
                if recipient in self.batch_timers:
                    self.batch_timers[recipient].cancel()
                    del self.batch_timers[recipient]
                
                # Send batch
                if self.batch_callback:
                    try:
                        self.batch_callback(recipient, batch)
                    except Exception as e:
                        logger.error(f"Error in batch callback for {recipient}: {e}")
    
    def flush_all(self):
        """Flush all pending batches"""
        with self.lock:
            for recipient in list(self.batches.keys()):
                if self.batches[recipient]:
                    self._flush_batch(recipient)

class LoadBalancer:
    """Load balancer for message routing"""
    
    def __init__(self):
        self.routes: Dict[str, List[str]] = defaultdict(list)
        self.route_weights: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.route_metrics: Dict[str, RouteMetrics] = defaultdict(RouteMetrics)
        self.lock = threading.RLock()
    
    def add_route(self, recipient: str, handler: str, weight: float = 1.0):
        """Add route for recipient"""
        with self.lock:
            if handler not in self.routes[recipient]:
                self.routes[recipient].append(handler)
            self.route_weights[recipient][handler] = weight
    
    def remove_route(self, recipient: str, handler: str):
        """Remove route for recipient"""
        with self.lock:
            if handler in self.routes[recipient]:
                self.routes[recipient].remove(handler)
            if handler in self.route_weights[recipient]:
                del self.route_weights[recipient][handler]
    
    def get_best_route(self, recipient: str) -> Optional[str]:
        """Get best route for recipient based on performance"""
        with self.lock:
            available_routes = self.routes.get(recipient, [])
            if not available_routes:
                return None
            
            if len(available_routes) == 1:
                return available_routes[0]
            
            # Calculate scores based on metrics and weights
            best_route = None
            best_score = float('-inf')
            
            for route in available_routes:
                metrics = self.route_metrics[route]
                weight = self.route_weights[recipient].get(route, 1.0)
                
                # Calculate score (higher is better)
                success_rate = 1.0
                if metrics.messages_sent > 0:
                    success_rate = 1.0 - (metrics.messages_failed / metrics.messages_sent)
                
                avg_latency = 0.0
                if metrics.messages_sent > 0:
                    avg_latency = metrics.total_latency / metrics.messages_sent
                
                # Score: weight * success_rate * (1 / (1 + avg_latency))
                score = weight * success_rate * (1.0 / (1.0 + avg_latency))
                
                if score > best_score:
                    best_score = score
                    best_route = route
            
            return best_route
    
    def record_success(self, route: str, latency: float):
        """Record successful message delivery"""
        with self.lock:
            metrics = self.route_metrics[route]
            metrics.messages_sent += 1
            metrics.total_latency += latency
            metrics.last_update = datetime.now()
    
    def record_failure(self, route: str):
        """Record failed message delivery"""
        with self.lock:
            metrics = self.route_metrics[route]
            metrics.messages_failed += 1
            metrics.last_update = datetime.now()

class OptimizedMessageRouter:
    """High-performance message router with advanced features"""
    
    def __init__(self, max_workers: int = 10, queue_size: int = 10000):
        self.max_workers = max_workers
        self.queue_size = queue_size
        
        # Core components
        self.message_queue = MessageQueue(queue_size)
        self.batcher = MessageBatcher(batch_size=5, batch_timeout=0.5)
        self.load_balancer = LoadBalancer()
        
        # Worker management
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.workers_running = False
        self.worker_threads: List[threading.Thread] = []
        
        # Message handlers
        self.handlers: Dict[str, Callable] = {}
        self.middleware: List[Callable] = []
        
        # Performance monitoring
        self.metrics = {
            'messages_processed': 0,
            'messages_failed': 0,
            'average_latency': 0.0,
            'peak_queue_size': 0,
            'throughput_history': deque(maxlen=60),  # Last 60 seconds
            'start_time': datetime.now()
        }
        self.metrics_lock = threading.RLock()
        
        # Compression and deduplication
        self.enable_compression = True
        self.enable_deduplication = True
        self.message_cache: Set[str] = set()
        self.cache_max_size = 10000
        
        # Set up batch callback
        self.batcher.set_batch_callback(self._handle_batch)
        
        logger.info(f"OptimizedMessageRouter initialized with {max_workers} workers")
    
    def start(self):
        """Start the message router"""
        if self.workers_running:
            logger.warning("Message router is already running")
            return
        
        self.workers_running = True
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"MessageRouter-Worker-{i}",
                daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)
        
        # Start metrics collection
        metrics_thread = threading.Thread(
            target=self._metrics_loop,
            name="MessageRouter-Metrics",
            daemon=True
        )
        metrics_thread.start()
        
        logger.info("Message router started")
    
    def stop(self):
        """Stop the message router"""
        if not self.workers_running:
            logger.warning("Message router is not running")
            return
        
        self.workers_running = False
        
        # Flush pending batches
        self.batcher.flush_all()
        
        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=5)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("Message router stopped")
    
    def register_handler(self, handler_name: str, handler: Callable):
        """Register message handler"""
        self.handlers[handler_name] = handler
        logger.info(f"Registered handler: {handler_name}")
    
    def add_middleware(self, middleware: Callable):
        """Add middleware for message processing"""
        self.middleware.append(middleware)
        logger.info("Added middleware")
    
    def add_route(self, recipient: str, handler_name: str, weight: float = 1.0):
        """Add route for recipient"""
        if handler_name not in self.handlers:
            raise ValueError(f"Handler {handler_name} not registered")
        
        self.load_balancer.add_route(recipient, handler_name, weight)
        logger.info(f"Added route: {recipient} -> {handler_name} (weight: {weight})")
    
    def send_message(self, message: Message, timeout: Optional[float] = None) -> bool:
        """Send message through the router"""
        try:
            # Apply middleware
            for middleware in self.middleware:
                message = middleware(message)
                if message is None:
                    return False
            
            # Deduplication
            if self.enable_deduplication:
                message_hash = self._hash_message(message)
                if message_hash in self.message_cache:
                    logger.debug(f"Duplicate message detected: {message.id}")
                    return True
                
                self.message_cache.add(message_hash)
                if len(self.message_cache) > self.cache_max_size:
                    # Remove oldest entries (simple FIFO)
                    self.message_cache = set(list(self.message_cache)[1000:])
            
            # Compression
            if self.enable_compression and len(message.content) > 1000:
                message.content = self._compress_content(message.content)
                message.metadata['compressed'] = True
            
            # Add to queue
            success = self.message_queue.put(message, timeout)
            if success:
                # Update peak queue size
                with self.metrics_lock:
                    current_size = self.message_queue.qsize()
                    if current_size > self.metrics['peak_queue_size']:
                        self.metrics['peak_queue_size'] = current_size
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending message {message.id}: {e}")
            return False
    
    def send_batch(self, messages: List[Message]) -> int:
        """Send multiple messages"""
        successful = 0
        for message in messages:
            if self.send_message(message):
                successful += 1
        return successful
    
    def _worker_loop(self):
        """Main worker loop"""
        while self.workers_running:
            try:
                # Get message from queue
                message = self.message_queue.get(timeout=1.0)
                if message is None:
                    continue
                
                # Process message
                self._process_message(message)
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
    
    def _process_message(self, message: Message):
        """Process a single message"""
        start_time = time.time()
        
        try:
            # Get best route
            handler_name = self.load_balancer.get_best_route(message.recipient)
            if not handler_name:
                logger.warning(f"No route found for recipient: {message.recipient}")
                self._record_failure(message)
                return
            
            # Get handler
            handler = self.handlers.get(handler_name)
            if not handler:
                logger.error(f"Handler not found: {handler_name}")
                self._record_failure(message)
                return
            
            # Decompress if needed
            if message.metadata.get('compressed'):
                message.content = self._decompress_content(message.content)
            
            # Call handler
            success = handler(message)
            
            # Record metrics
            latency = time.time() - start_time
            if success:
                self.load_balancer.record_success(handler_name, latency)
                self._record_success(message, latency)
            else:
                self.load_balancer.record_failure(handler_name)
                self._record_failure(message)
                
                # Retry if needed
                if message.retry_count < message.max_retries:
                    message.retry_count += 1
                    self.message_queue.put(message)
                    logger.info(f"Retrying message {message.id} (attempt {message.retry_count})")
            
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
            self._record_failure(message)
    
    def _handle_batch(self, recipient: str, batch: List[Message]):
        """Handle batch of messages"""
        logger.debug(f"Processing batch of {len(batch)} messages for {recipient}")
        
        # Get handler for batch processing
        handler_name = self.load_balancer.get_best_route(recipient)
        if not handler_name:
            logger.warning(f"No route found for batch recipient: {recipient}")
            return
        
        handler = self.handlers.get(handler_name)
        if not handler:
            logger.error(f"Handler not found for batch: {handler_name}")
            return
        
        # Check if handler supports batch processing
        if hasattr(handler, 'handle_batch'):
            try:
                handler.handle_batch(batch)
            except Exception as e:
                logger.error(f"Error in batch handler: {e}")
                # Fall back to individual processing
                for message in batch:
                    self._process_message(message)
        else:
            # Process individually
            for message in batch:
                self._process_message(message)
    
    def _record_success(self, message: Message, latency: float):
        """Record successful message processing"""
        with self.metrics_lock:
            self.metrics['messages_processed'] += 1
            
            # Update average latency
            total_messages = self.metrics['messages_processed']
            current_avg = self.metrics['average_latency']
            self.metrics['average_latency'] = (
                (current_avg * (total_messages - 1) + latency) / total_messages
            )
    
    def _record_failure(self, message: Message):
        """Record failed message processing"""
        with self.metrics_lock:
            self.metrics['messages_failed'] += 1
    
    def _metrics_loop(self):
        """Collect performance metrics"""
        last_count = 0
        
        while self.workers_running:
            try:
                time.sleep(1)  # Collect every second
                
                with self.metrics_lock:
                    current_count = self.metrics['messages_processed']
                    throughput = current_count - last_count
                    self.metrics['throughput_history'].append(throughput)
                    last_count = current_count
                
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
    
    def _hash_message(self, message: Message) -> str:
        """Generate hash for message deduplication"""
        content = f"{message.sender}:{message.recipient}:{message.content}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _compress_content(self, content: str) -> str:
        """Compress message content"""
        try:
            import gzip
            import base64
            
            compressed = gzip.compress(content.encode('utf-8'))
            return base64.b64encode(compressed).decode('ascii')
        except Exception as e:
            logger.warning(f"Compression failed: {e}")
            return content
    
    def _decompress_content(self, content: str) -> str:
        """Decompress message content"""
        try:
            import gzip
            import base64
            
            compressed = base64.b64decode(content.encode('ascii'))
            return gzip.decompress(compressed).decode('utf-8')
        except Exception as e:
            logger.warning(f"Decompression failed: {e}")
            return content
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self.metrics_lock:
            current_time = datetime.now()
            uptime = (current_time - self.metrics['start_time']).total_seconds()
            
            # Calculate current throughput
            recent_throughput = list(self.metrics['throughput_history'])[-10:]
            current_throughput = sum(recent_throughput) / len(recent_throughput) if recent_throughput else 0
            
            return {
                'messages_processed': self.metrics['messages_processed'],
                'messages_failed': self.metrics['messages_failed'],
                'success_rate': (
                    (self.metrics['messages_processed'] / 
                     (self.metrics['messages_processed'] + self.metrics['messages_failed']))
                    if (self.metrics['messages_processed'] + self.metrics['messages_failed']) > 0 else 1.0
                ),
                'average_latency_ms': self.metrics['average_latency'] * 1000,
                'current_throughput_per_second': current_throughput,
                'peak_queue_size': self.metrics['peak_queue_size'],
                'current_queue_size': self.message_queue.qsize(),
                'uptime_seconds': uptime,
                'workers_active': len([t for t in self.worker_threads if t.is_alive()]),
                'routes_configured': len(self.load_balancer.routes)
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the router"""
        metrics = self.get_metrics()
        
        # Determine health status
        health = "HEALTHY"
        issues = []
        
        if metrics['success_rate'] < 0.95:
            health = "DEGRADED"
            issues.append(f"Low success rate: {metrics['success_rate']:.2%}")
        
        if metrics['average_latency_ms'] > 1000:
            health = "DEGRADED"
            issues.append(f"High latency: {metrics['average_latency_ms']:.1f}ms")
        
        if metrics['current_queue_size'] > self.queue_size * 0.8:
            health = "DEGRADED"
            issues.append(f"Queue nearly full: {metrics['current_queue_size']}/{self.queue_size}")
        
        if metrics['workers_active'] < self.max_workers * 0.8:
            health = "UNHEALTHY"
            issues.append(f"Workers down: {metrics['workers_active']}/{self.max_workers}")
        
        return {
            'status': health,
            'issues': issues,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }