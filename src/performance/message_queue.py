"""
High-Performance Message Queue System
Implements Redis/RabbitMQ-like functionality with message reliability and priority queuing
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable, Union
import threading
from concurrent.futures import ThreadPoolExecutor
import pickle
import lz4.frame
import orjson
import aiofiles
import os

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MessageStatus(Enum):
    """Message processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


@dataclass
class QueueMessage:
    """Message in the queue with metadata"""
    id: str
    content: dict
    priority: MessagePriority
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    status: MessageStatus = MessageStatus.PENDING
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    user_id: Optional[str] = None
    group_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.tags, list):
            self.tags = set(self.tags)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'content': self.content,
            'priority': self.priority.value,
            'created_at': self.created_at.isoformat(),
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'status': self.status.value,
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'tags': list(self.tags),
            'user_id': self.user_id,
            'group_id': self.group_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'QueueMessage':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            content=data['content'],
            priority=MessagePriority(data['priority']),
            created_at=datetime.fromisoformat(data['created_at']),
            scheduled_at=datetime.fromisoformat(data['scheduled_at']) if data.get('scheduled_at') else None,
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            status=MessageStatus(data.get('status', 'pending')),
            processing_started_at=datetime.fromisoformat(data['processing_started_at']) if data.get('processing_started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            error_message=data.get('error_message'),
            tags=set(data.get('tags', [])),
            user_id=data.get('user_id'),
            group_id=data.get('group_id')
        )


@dataclass
class QueueStats:
    """Queue statistics"""
    total_messages: int = 0
    pending_messages: int = 0
    processing_messages: int = 0
    completed_messages: int = 0
    failed_messages: int = 0
    dead_letter_messages: int = 0
    messages_per_second: float = 0.0
    avg_processing_time_ms: float = 0.0
    queue_depth: int = 0
    oldest_message_age_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_mb: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class MessageProcessor:
    """Base class for message processors"""
    
    async def process(self, message: QueueMessage) -> bool:
        """Process a message. Return True if successful, False if failed."""
        raise NotImplementedError
    
    async def on_failure(self, message: QueueMessage, error: Exception):
        """Handle message processing failure"""
        pass
    
    async def on_success(self, message: QueueMessage):
        """Handle successful message processing"""
        pass


class DefaultMessageProcessor(MessageProcessor):
    """Default message processor that logs messages"""
    
    async def process(self, message: QueueMessage) -> bool:
        """Process message by logging it"""
        logger.info(f"Processing message {message.id}: {message.content}")
        await asyncio.sleep(0.001)  # Simulate processing time
        return True


class PriorityQueue:
    """Priority queue implementation with multiple priority levels"""
    
    def __init__(self):
        self.queues = {
            MessagePriority.CRITICAL: deque(),
            MessagePriority.HIGH: deque(),
            MessagePriority.NORMAL: deque(),
            MessagePriority.LOW: deque()
        }
        self.lock = asyncio.Lock()
        self.not_empty = asyncio.Condition(self.lock)
        self._size = 0
    
    async def put(self, message: QueueMessage):
        """Add message to appropriate priority queue"""
        async with self.not_empty:
            self.queues[message.priority].append(message)
            self._size += 1
            self.not_empty.notify()
    
    async def get(self) -> Optional[QueueMessage]:
        """Get highest priority message"""
        async with self.not_empty:
            while self._size == 0:
                await self.not_empty.wait()
            
            # Check queues in priority order
            for priority in [MessagePriority.CRITICAL, MessagePriority.HIGH, 
                           MessagePriority.NORMAL, MessagePriority.LOW]:
                if self.queues[priority]:
                    message = self.queues[priority].popleft()
                    self._size -= 1
                    return message
            
            return None
    
    async def peek(self) -> Optional[QueueMessage]:
        """Peek at highest priority message without removing it"""
        async with self.lock:
            for priority in [MessagePriority.CRITICAL, MessagePriority.HIGH, 
                           MessagePriority.NORMAL, MessagePriority.LOW]:
                if self.queues[priority]:
                    return self.queues[priority][0]
            return None
    
    def size(self) -> int:
        """Get total queue size"""
        return self._size
    
    def size_by_priority(self) -> Dict[MessagePriority, int]:
        """Get queue size by priority"""
        return {priority: len(queue) for priority, queue in self.queues.items()}
    
    async def clear(self):
        """Clear all queues"""
        async with self.lock:
            for queue in self.queues.values():
                queue.clear()
            self._size = 0


class MessageBuffer:
    """Buffer for offline users and message reliability"""
    
    def __init__(self, max_size: int = 10000, persistence_file: str = None):
        self.max_size = max_size
        self.persistence_file = persistence_file
        self.buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))  # user_id -> messages
        self.lock = asyncio.Lock()
        
    async def add_message(self, user_id: str, message: QueueMessage):
        """Add message to user's buffer"""
        async with self.lock:
            self.buffers[user_id].append(message)
            
            # Persist if configured
            if self.persistence_file:
                await self._persist_buffer(user_id)
    
    async def get_messages(self, user_id: str, limit: int = 100) -> List[QueueMessage]:
        """Get buffered messages for user"""
        async with self.lock:
            if user_id not in self.buffers:
                return []
            
            messages = []
            for _ in range(min(limit, len(self.buffers[user_id]))):
                if self.buffers[user_id]:
                    messages.append(self.buffers[user_id].popleft())
            
            return messages
    
    async def clear_buffer(self, user_id: str):
        """Clear user's message buffer"""
        async with self.lock:
            if user_id in self.buffers:
                self.buffers[user_id].clear()
    
    async def get_buffer_size(self, user_id: str) -> int:
        """Get size of user's buffer"""
        async with self.lock:
            return len(self.buffers.get(user_id, []))
    
    async def _persist_buffer(self, user_id: str):
        """Persist user's buffer to disk"""
        if not self.persistence_file:
            return
        
        try:
            buffer_data = {
                'user_id': user_id,
                'messages': [msg.to_dict() for msg in self.buffers[user_id]],
                'timestamp': datetime.now().isoformat()
            }
            
            # Compress and save
            compressed_data = lz4.frame.compress(orjson.dumps(buffer_data))
            
            buffer_file = f"{self.persistence_file}.{user_id}"
            async with aiofiles.open(buffer_file, 'wb') as f:
                await f.write(compressed_data)
                
        except Exception as e:
            logger.error(f"Failed to persist buffer for {user_id}: {e}")
    
    async def load_persisted_buffers(self):
        """Load persisted buffers from disk"""
        if not self.persistence_file or not os.path.exists(os.path.dirname(self.persistence_file)):
            return
        
        try:
            # Find all buffer files
            buffer_dir = os.path.dirname(self.persistence_file)
            buffer_prefix = os.path.basename(self.persistence_file)
            
            for filename in os.listdir(buffer_dir):
                if filename.startswith(buffer_prefix + '.'):
                    user_id = filename[len(buffer_prefix) + 1:]
                    buffer_file = os.path.join(buffer_dir, filename)
                    
                    try:
                        async with aiofiles.open(buffer_file, 'rb') as f:
                            compressed_data = await f.read()
                        
                        # Decompress and load
                        data = orjson.loads(lz4.frame.decompress(compressed_data))
                        
                        messages = [QueueMessage.from_dict(msg_data) for msg_data in data['messages']]
                        self.buffers[user_id] = deque(messages, maxlen=1000)
                        
                        logger.info(f"Loaded {len(messages)} buffered messages for user {user_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to load buffer file {buffer_file}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to load persisted buffers: {e}")


class DeliveryConfirmationManager:
    """Manages message delivery confirmations"""
    
    def __init__(self, confirmation_timeout: int = 30):
        self.confirmation_timeout = confirmation_timeout
        self.pending_confirmations: Dict[str, QueueMessage] = {}  # message_id -> message
        self.confirmation_timers: Dict[str, asyncio.Task] = {}  # message_id -> timer task
        self.lock = asyncio.Lock()
    
    async def add_pending_confirmation(self, message: QueueMessage):
        """Add message pending confirmation"""
        async with self.lock:
            self.pending_confirmations[message.id] = message
            
            # Start confirmation timer
            timer_task = asyncio.create_task(self._confirmation_timeout_handler(message.id))
            self.confirmation_timers[message.id] = timer_task
    
    async def confirm_delivery(self, message_id: str) -> bool:
        """Confirm message delivery"""
        async with self.lock:
            if message_id not in self.pending_confirmations:
                return False
            
            # Cancel timer
            if message_id in self.confirmation_timers:
                self.confirmation_timers[message_id].cancel()
                del self.confirmation_timers[message_id]
            
            # Remove from pending
            message = self.pending_confirmations.pop(message_id)
            message.status = MessageStatus.COMPLETED
            message.completed_at = datetime.now()
            
            logger.debug(f"Confirmed delivery of message {message_id}")
            return True
    
    async def _confirmation_timeout_handler(self, message_id: str):
        """Handle confirmation timeout"""
        try:
            await asyncio.sleep(self.confirmation_timeout)
            
            async with self.lock:
                if message_id in self.pending_confirmations:
                    message = self.pending_confirmations.pop(message_id)
                    message.status = MessageStatus.FAILED
                    message.error_message = "Delivery confirmation timeout"
                    
                    logger.warning(f"Message {message_id} delivery confirmation timed out")
                    
                    # Clean up timer reference
                    if message_id in self.confirmation_timers:
                        del self.confirmation_timers[message_id]
                        
        except asyncio.CancelledError:
            pass  # Timer was cancelled (confirmation received)
    
    def get_pending_count(self) -> int:
        """Get number of pending confirmations"""
        return len(self.pending_confirmations)


class HighPerformanceMessageQueue:
    """High-performance message queue with Redis/RabbitMQ-like features"""
    
    def __init__(self, max_workers: int = 10, persistence_dir: str = "./queue_data"):
        self.max_workers = max_workers
        self.persistence_dir = persistence_dir
        
        # Core components
        self.priority_queue = PriorityQueue()
        self.message_buffer = MessageBuffer(
            persistence_file=os.path.join(persistence_dir, "message_buffers") if persistence_dir else None
        )
        self.delivery_manager = DeliveryConfirmationManager()
        
        # Message processing
        self.processors: Dict[str, MessageProcessor] = {}
        self.default_processor = DefaultMessageProcessor()
        
        # Worker management
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        self.worker_semaphore = asyncio.Semaphore(max_workers)
        
        # Statistics and monitoring
        self.stats = QueueStats()
        self.message_history: Dict[str, QueueMessage] = {}  # message_id -> message
        self.processing_times: deque = deque(maxlen=1000)  # Keep last 1000 processing times
        
        # Dead letter queue
        self.dead_letter_queue: deque = deque(maxlen=10000)
        
        # Scheduled messages
        self.scheduled_messages: List[QueueMessage] = []
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="queue-worker")
        
        # Metrics collection
        self.metrics_task: Optional[asyncio.Task] = None
        
        # Create persistence directory
        if persistence_dir:
            os.makedirs(persistence_dir, exist_ok=True)
    
    async def start_processor(self):
        """Start the message queue processor"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Load persisted buffers
        await self.message_buffer.load_persisted_buffers()
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker_task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self.workers.append(worker_task)
        
        # Start scheduler task
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        # Start metrics collection
        self.metrics_task = asyncio.create_task(self._metrics_loop())
        
        logger.info(f"Message queue processor started with {self.max_workers} workers")
    
    async def stop_processor(self):
        """Stop the message queue processor"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel all tasks
        all_tasks = self.workers + [self.scheduler_task, self.metrics_task]
        for task in all_tasks:
            if task and not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("Message queue processor stopped")
    
    async def enqueue(self, content: dict, priority: MessagePriority = MessagePriority.NORMAL,
                     scheduled_at: Optional[datetime] = None, user_id: Optional[str] = None,
                     group_id: Optional[str] = None, tags: Optional[Set[str]] = None,
                     max_retries: int = 3) -> str:
        """Enqueue a message"""
        message = QueueMessage(
            id=str(uuid.uuid4()),
            content=content,
            priority=priority,
            created_at=datetime.now(),
            scheduled_at=scheduled_at,
            user_id=user_id,
            group_id=group_id,
            tags=tags or set(),
            max_retries=max_retries
        )
        
        if scheduled_at and scheduled_at > datetime.now():
            # Schedule for later
            self.scheduled_messages.append(message)
            self.scheduled_messages.sort(key=lambda m: m.scheduled_at)
        else:
            # Add to priority queue immediately
            await self.priority_queue.put(message)
        
        # Store in history
        self.message_history[message.id] = message
        
        # Update stats
        self.stats.total_messages += 1
        self.stats.pending_messages += 1
        
        logger.debug(f"Enqueued message {message.id} with priority {priority.name}")
        return message.id
    
    async def enqueue_for_user(self, user_id: str, content: dict, 
                              priority: MessagePriority = MessagePriority.NORMAL,
                              require_confirmation: bool = False) -> str:
        """Enqueue message for specific user with optional delivery confirmation"""
        message_id = await self.enqueue(
            content=content,
            priority=priority,
            user_id=user_id,
            tags={'user_message'}
        )
        
        if require_confirmation:
            message = self.message_history[message_id]
            await self.delivery_manager.add_pending_confirmation(message)
        
        return message_id
    
    async def enqueue_batch(self, messages: List[dict], 
                           priority: MessagePriority = MessagePriority.NORMAL) -> List[str]:
        """Enqueue multiple messages in batch"""
        message_ids = []
        
        for content in messages:
            message_id = await self.enqueue(content, priority)
            message_ids.append(message_id)
        
        logger.info(f"Enqueued batch of {len(messages)} messages")
        return message_ids
    
    async def get_message_status(self, message_id: str) -> Optional[MessageStatus]:
        """Get status of a message"""
        if message_id in self.message_history:
            return self.message_history[message_id].status
        return None
    
    async def confirm_delivery(self, message_id: str) -> bool:
        """Confirm message delivery"""
        return await self.delivery_manager.confirm_delivery(message_id)
    
    async def get_buffered_messages(self, user_id: str, limit: int = 100) -> List[dict]:
        """Get buffered messages for user"""
        messages = await self.message_buffer.get_messages(user_id, limit)
        return [msg.content for msg in messages]
    
    async def buffer_message_for_offline_user(self, user_id: str, content: dict):
        """Buffer message for offline user"""
        message = QueueMessage(
            id=str(uuid.uuid4()),
            content=content,
            priority=MessagePriority.NORMAL,
            created_at=datetime.now(),
            user_id=user_id,
            tags={'offline_buffer'}
        )
        
        await self.message_buffer.add_message(user_id, message)
        logger.debug(f"Buffered message for offline user {user_id}")
    
    def register_processor(self, message_type: str, processor: MessageProcessor):
        """Register a message processor for specific message type"""
        self.processors[message_type] = processor
        logger.info(f"Registered processor for message type: {message_type}")
    
    async def _worker_loop(self, worker_name: str):
        """Worker loop for processing messages"""
        logger.debug(f"Started worker: {worker_name}")
        
        while self.is_running:
            try:
                async with self.worker_semaphore:
                    # Get message from queue
                    message = await self.priority_queue.get()
                    if not message:
                        continue
                    
                    # Process message
                    await self._process_message(message, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker {worker_name}: {e}")
                await asyncio.sleep(1)
        
        logger.debug(f"Stopped worker: {worker_name}")
    
    async def _process_message(self, message: QueueMessage, worker_name: str):
        """Process a single message"""
        start_time = time.time()
        
        try:
            # Update message status
            message.status = MessageStatus.PROCESSING
            message.processing_started_at = datetime.now()
            
            # Update stats
            self.stats.pending_messages -= 1
            self.stats.processing_messages += 1
            
            # Get appropriate processor
            message_type = message.content.get('type', 'default')
            processor = self.processors.get(message_type, self.default_processor)
            
            # Process message
            success = await processor.process(message)
            
            if success:
                # Mark as completed
                message.status = MessageStatus.COMPLETED
                message.completed_at = datetime.now()
                
                # Update stats
                self.stats.processing_messages -= 1
                self.stats.completed_messages += 1
                
                # Call success handler
                await processor.on_success(message)
                
                logger.debug(f"Successfully processed message {message.id} by {worker_name}")
                
            else:
                # Handle failure
                await self._handle_message_failure(message, Exception("Processing returned False"))
                
        except Exception as e:
            await self._handle_message_failure(message, e)
        
        finally:
            # Record processing time
            processing_time = (time.time() - start_time) * 1000
            self.processing_times.append(processing_time)
    
    async def _handle_message_failure(self, message: QueueMessage, error: Exception):
        """Handle message processing failure"""
        message.error_message = str(error)
        message.retry_count += 1
        
        # Update stats
        if message.status == MessageStatus.PROCESSING:
            self.stats.processing_messages -= 1
        
        if message.retry_count <= message.max_retries:
            # Retry message
            message.status = MessageStatus.RETRY
            await self.priority_queue.put(message)
            
            logger.warning(f"Message {message.id} failed, retrying ({message.retry_count}/{message.max_retries}): {error}")
        else:
            # Move to dead letter queue
            message.status = MessageStatus.DEAD_LETTER
            self.dead_letter_queue.append(message)
            self.stats.dead_letter_messages += 1
            
            logger.error(f"Message {message.id} moved to dead letter queue after {message.retry_count} retries: {error}")
        
        self.stats.failed_messages += 1
        
        # Call failure handler
        message_type = message.content.get('type', 'default')
        processor = self.processors.get(message_type, self.default_processor)
        await processor.on_failure(message, error)
    
    async def _scheduler_loop(self):
        """Scheduler loop for processing scheduled messages"""
        while self.is_running:
            try:
                now = datetime.now()
                
                # Check for scheduled messages that are ready
                ready_messages = []
                remaining_messages = []
                
                for message in self.scheduled_messages:
                    if message.scheduled_at <= now:
                        ready_messages.append(message)
                    else:
                        remaining_messages.append(message)
                
                # Move ready messages to priority queue
                for message in ready_messages:
                    await self.priority_queue.put(message)
                
                self.scheduled_messages = remaining_messages
                
                if ready_messages:
                    logger.debug(f"Scheduled {len(ready_messages)} messages for processing")
                
                await asyncio.sleep(1)  # Check every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5)
    
    async def _metrics_loop(self):
        """Metrics collection loop"""
        while self.is_running:
            try:
                await self._update_metrics()
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(30)
    
    async def _update_metrics(self):
        """Update queue metrics"""
        # Calculate messages per second
        if len(self.processing_times) > 1:
            recent_times = list(self.processing_times)[-100:]  # Last 100 messages
            if recent_times:
                avg_processing_time = sum(recent_times) / len(recent_times)
                self.stats.avg_processing_time_ms = avg_processing_time
                
                # Estimate messages per second based on processing time and workers
                if avg_processing_time > 0:
                    self.stats.messages_per_second = (self.max_workers * 1000) / avg_processing_time
        
        # Update queue depth
        self.stats.queue_depth = self.priority_queue.size()
        
        # Calculate oldest message age
        if self.message_history:
            oldest_pending = min(
                (msg for msg in self.message_history.values() if msg.status == MessageStatus.PENDING),
                key=lambda m: m.created_at,
                default=None
            )
            if oldest_pending:
                self.stats.oldest_message_age_seconds = (datetime.now() - oldest_pending.created_at).total_seconds()
        
        # Update timestamp
        self.stats.last_updated = datetime.now()
    
    async def get_queue_depth(self) -> int:
        """Get current queue depth"""
        return self.priority_queue.size()
    
    def get_stats(self) -> QueueStats:
        """Get queue statistics"""
        return self.stats
    
    def get_detailed_stats(self) -> dict:
        """Get detailed queue statistics"""
        priority_sizes = self.priority_queue.size_by_priority()
        
        return {
            'queue_stats': {
                'total_messages': self.stats.total_messages,
                'pending_messages': self.stats.pending_messages,
                'processing_messages': self.stats.processing_messages,
                'completed_messages': self.stats.completed_messages,
                'failed_messages': self.stats.failed_messages,
                'dead_letter_messages': self.stats.dead_letter_messages,
                'messages_per_second': self.stats.messages_per_second,
                'avg_processing_time_ms': self.stats.avg_processing_time_ms,
                'queue_depth': self.stats.queue_depth,
                'oldest_message_age_seconds': self.stats.oldest_message_age_seconds,
                'last_updated': self.stats.last_updated.isoformat()
            },
            'priority_breakdown': {
                priority.name: size for priority, size in priority_sizes.items()
            },
            'worker_stats': {
                'max_workers': self.max_workers,
                'active_workers': len([w for w in self.workers if not w.done()]),
                'is_running': self.is_running
            },
            'scheduled_messages': len(self.scheduled_messages),
            'dead_letter_queue_size': len(self.dead_letter_queue),
            'pending_confirmations': self.delivery_manager.get_pending_count(),
            'registered_processors': list(self.processors.keys())
        }
    
    async def get_dead_letter_messages(self, limit: int = 100) -> List[dict]:
        """Get messages from dead letter queue"""
        messages = list(self.dead_letter_queue)[-limit:]
        return [msg.to_dict() for msg in messages]
    
    async def requeue_dead_letter_message(self, message_id: str) -> bool:
        """Requeue a message from dead letter queue"""
        for i, message in enumerate(self.dead_letter_queue):
            if message.id == message_id:
                # Reset message for reprocessing
                message.status = MessageStatus.PENDING
                message.retry_count = 0
                message.error_message = None
                
                # Remove from dead letter queue and requeue
                del self.dead_letter_queue[i]
                await self.priority_queue.put(message)
                
                self.stats.dead_letter_messages -= 1
                self.stats.pending_messages += 1
                
                logger.info(f"Requeued dead letter message {message_id}")
                return True
        
        return False
    
    async def clear_dead_letter_queue(self):
        """Clear the dead letter queue"""
        cleared_count = len(self.dead_letter_queue)
        self.dead_letter_queue.clear()
        self.stats.dead_letter_messages = 0
        
        logger.info(f"Cleared {cleared_count} messages from dead letter queue")
        return cleared_count
    
    async def health_check(self) -> dict:
        """Perform health check on the message queue"""
        active_workers = len([w for w in self.workers if not w.done()])
        queue_depth = await self.get_queue_depth()
        
        # Determine health status
        if not self.is_running:
            status = "unhealthy"
        elif active_workers < self.max_workers * 0.5:
            status = "degraded"
        elif queue_depth > 10000:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            'status': status,
            'is_running': self.is_running,
            'active_workers': active_workers,
            'max_workers': self.max_workers,
            'queue_depth': queue_depth,
            'pending_messages': self.stats.pending_messages,
            'processing_messages': self.stats.processing_messages,
            'failed_messages': self.stats.failed_messages,
            'dead_letter_messages': self.stats.dead_letter_messages,
            'messages_per_second': self.stats.messages_per_second,
            'avg_processing_time_ms': self.stats.avg_processing_time_ms,
            'timestamp': datetime.now().isoformat()
        }