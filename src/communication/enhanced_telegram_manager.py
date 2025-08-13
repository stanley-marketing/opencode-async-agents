# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
Enhanced Telegram Manager with optimized communication features
Implements rate limiting optimization, message batching, and failover mechanisms.
"""

from .optimized_message_router import Message, OptimizedMessageRouter
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from src.chat.chat_config import config
from src.chat.message_parser import MessageParser, ParsedMessage
from typing import Dict, List, Optional, Callable, Any, Tuple
import asyncio
import json
import logging
import queue
import requests
import threading
import time

logger = logging.getLogger(__name__)

class RateLimitManager:
    """Advanced rate limiting with burst capacity and adaptive limits"""

    def __init__(self, base_limit: int = 30, burst_capacity: int = 10):
        self.base_limit = base_limit  # Messages per minute
        self.burst_capacity = burst_capacity  # Extra messages for bursts
        self.message_times: deque = deque()
        self.burst_used = 0
        self.lock = threading.RLock()

        # Adaptive rate limiting
        self.success_rate = 1.0
        self.adaptive_factor = 1.0
        self.last_rate_check = datetime.now()

    def can_send_message(self) -> Tuple[bool, float]:
        """Check if message can be sent, return (can_send, wait_time)"""
        with self.lock:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)

            # Remove old entries
            while self.message_times and self.message_times[0] < minute_ago:
                self.message_times.popleft()

            # Calculate current effective limit
            effective_limit = int(self.base_limit * self.adaptive_factor)

            # Check if within base limit
            if len(self.message_times) < effective_limit:
                return True, 0.0

            # Check if burst capacity available
            if self.burst_used < self.burst_capacity:
                return True, 0.0

            # Calculate wait time
            if self.message_times:
                oldest_message = self.message_times[0]
                wait_time = (oldest_message + timedelta(minutes=1) - now).total_seconds()
                return False, max(0, wait_time)

            return False, 60.0  # Default wait time

    def record_message_sent(self, success: bool = True):
        """Record that a message was sent"""
        with self.lock:
            now = datetime.now()
            self.message_times.append(now)

            # Update burst usage
            effective_limit = int(self.base_limit * self.adaptive_factor)
            if len(self.message_times) > effective_limit:
                self.burst_used += 1

            # Update success rate for adaptive limiting
            self.success_rate = 0.9 * self.success_rate + 0.1 * (1.0 if success else 0.0)

            # Adjust adaptive factor every minute
            if now - self.last_rate_check > timedelta(minutes=1):
                self._adjust_adaptive_factor()
                self.last_rate_check = now
                self.burst_used = 0  # Reset burst usage

    def _adjust_adaptive_factor(self):
        """Adjust adaptive factor based on success rate"""
        if self.success_rate < 0.8:
            # Reduce rate if success rate is low
            self.adaptive_factor = max(0.5, self.adaptive_factor * 0.9)
        elif self.success_rate > 0.95:
            # Increase rate if success rate is high
            self.adaptive_factor = min(2.0, self.adaptive_factor * 1.1)

        logger.debug(f"Adaptive factor adjusted to {self.adaptive_factor:.2f} (success rate: {self.success_rate:.2%})")

class MessageBatchProcessor:
    """Processes messages in batches for efficiency"""

    def __init__(self, batch_size: int = 5, batch_timeout: float = 2.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_batches: Dict[str, List[Dict]] = defaultdict(list)
        self.batch_timers: Dict[str, threading.Timer] = {}
        self.lock = threading.RLock()
        self.send_callback: Optional[Callable] = None

    def set_send_callback(self, callback: Callable):
        """Set callback for sending batched messages"""
        self.send_callback = callback

    def add_message(self, chat_id: str, message_data: Dict):
        """Add message to batch"""
        with self.lock:
            self.pending_batches[chat_id].append(message_data)

            # Check if batch is ready
            if len(self.pending_batches[chat_id]) >= self.batch_size:
                self._send_batch(chat_id)
            else:
                # Set/reset timer
                if chat_id in self.batch_timers:
                    self.batch_timers[chat_id].cancel()

                timer = threading.Timer(
                    self.batch_timeout,
                    lambda: self._send_batch(chat_id)
                )
                timer.start()
                self.batch_timers[chat_id] = timer

    def _send_batch(self, chat_id: str):
        """Send batch of messages"""
        with self.lock:
            if chat_id not in self.pending_batches or not self.pending_batches[chat_id]:
                return

            batch = self.pending_batches[chat_id].copy()
            self.pending_batches[chat_id].clear()

            # Cancel timer
            if chat_id in self.batch_timers:
                self.batch_timers[chat_id].cancel()
                del self.batch_timers[chat_id]

            # Send batch
            if self.send_callback:
                try:
                    self.send_callback(chat_id, batch)
                except Exception as e:
                    logger.error(f"Error sending batch to {chat_id}: {e}")

    def flush_all(self):
        """Flush all pending batches"""
        with self.lock:
            for chat_id in list(self.pending_batches.keys()):
                if self.pending_batches[chat_id]:
                    self._send_batch(chat_id)

class ConnectionPool:
    """Connection pool for HTTP requests"""

    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.sessions: queue.Queue = queue.Queue(maxsize=pool_size)
        self.lock = threading.RLock()

        # Initialize sessions
        for _ in range(pool_size):
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'OpenCode-Slack-Bot/1.0',
                'Connection': 'keep-alive'
            })
            self.sessions.put(session)

    def get_session(self, timeout: float = 5.0) -> Optional[requests.Session]:
        """Get session from pool"""
        try:
            return self.sessions.get(timeout=timeout)
        except queue.Empty:
            logger.warning("No sessions available in pool")
            return None

    def return_session(self, session: requests.Session):
        """Return session to pool"""
        try:
            self.sessions.put_nowait(session)
        except queue.Full:
            # Pool is full, close the session
            session.close()

class FailoverManager:
    """Manages failover between communication channels"""

    def __init__(self):
        self.channels: Dict[str, Dict] = {}
        self.primary_channel = None
        self.channel_health: Dict[str, float] = {}
        self.lock = threading.RLock()

    def register_channel(self, name: str, handler: Callable, priority: int = 1):
        """Register communication channel"""
        with self.lock:
            self.channels[name] = {
                'handler': handler,
                'priority': priority,
                'active': True
            }
            self.channel_health[name] = 1.0

            # Set primary channel
            if self.primary_channel is None or priority > self.channels[self.primary_channel]['priority']:
                self.primary_channel = name

        logger.info(f"Registered channel: {name} (priority: {priority})")

    def send_message(self, message: str, **kwargs) -> bool:
        """Send message with failover"""
        with self.lock:
            # Try primary channel first
            if self.primary_channel and self._try_channel(self.primary_channel, message, **kwargs):
                return True

            # Try other channels in priority order
            sorted_channels = sorted(
                [(name, info) for name, info in self.channels.items()
                 if name != self.primary_channel and info['active']],
                key=lambda x: x[1]['priority'],
                reverse=True
            )

            for channel_name, _ in sorted_channels:
                if self._try_channel(channel_name, message, **kwargs):
                    return True

            logger.error("All communication channels failed")
            return False

    def _try_channel(self, channel_name: str, message: str, **kwargs) -> bool:
        """Try sending message through specific channel"""
        try:
            channel_info = self.channels[channel_name]
            handler = channel_info['handler']

            success = handler(message, **kwargs)

            # Update health
            if success:
                self.channel_health[channel_name] = min(1.0, self.channel_health[channel_name] + 0.1)
            else:
                self.channel_health[channel_name] = max(0.0, self.channel_health[channel_name] - 0.2)

                # Deactivate channel if health is too low
                if self.channel_health[channel_name] < 0.3:
                    self.channels[channel_name]['active'] = False
                    logger.warning(f"Deactivated channel {channel_name} due to low health")

            return success

        except Exception as e:
            logger.error(f"Error in channel {channel_name}: {e}")
            self.channel_health[channel_name] = max(0.0, self.channel_health[channel_name] - 0.3)
            return False

    def get_channel_status(self) -> Dict[str, Any]:
        """Get status of all channels"""
        with self.lock:
            return {
                'primary_channel': self.primary_channel,
                'channels': {
                    name: {
                        'active': info['active'],
                        'priority': info['priority'],
                        'health': self.channel_health.get(name, 0.0)
                    }
                    for name, info in self.channels.items()
                }
            }

class EnhancedTelegramManager:
    """Enhanced Telegram manager with optimized features"""

    def __init__(self):
        self.bot_token = config.bot_token
        self.chat_id = config.chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        # Core components
        self.message_parser = MessageParser()
        self.rate_limiter = RateLimitManager(base_limit=50, burst_capacity=15)  # Increased limits
        self.batch_processor = MessageBatchProcessor(batch_size=3, batch_timeout=1.0)
        self.connection_pool = ConnectionPool(pool_size=5)
        self.failover_manager = FailoverManager()

        # Message routing
        self.message_router = OptimizedMessageRouter(max_workers=5, queue_size=5000)

        # State management
        self.message_handlers: List[Callable[[ParsedMessage], None]] = []
        self.is_polling = False
        self.polling_thread = None
        self.last_update_id = 0

        # Performance metrics
        self.metrics = {
            'messages_sent': 0,
            'messages_failed': 0,
            'messages_received': 0,
            'average_send_time': 0.0,
            'rate_limit_hits': 0,
            'batch_sends': 0,
            'failover_activations': 0
        }
        self.metrics_lock = threading.RLock()

        # Setup components
        self._setup_components()

        logger.info("Enhanced Telegram manager initialized")

    def _setup_components(self):
        """Setup internal components"""
        # Setup batch processor
        self.batch_processor.set_send_callback(self._send_batch)

        # Register Telegram as primary channel
        self.failover_manager.register_channel(
            'telegram',
            self._send_single_message,
            priority=10
        )

        # Setup message router
        self.message_router.register_handler('telegram', self._handle_routed_message)
        self.message_router.add_route('telegram', 'telegram', weight=1.0)

        # Start message router
        self.message_router.start()

    def add_message_handler(self, handler: Callable[[ParsedMessage], None]):
        """Add message handler"""
        self.message_handlers.append(handler)
        logger.info("Added message handler")

    def start_polling(self):
        """Start polling for messages"""
        if self.is_polling:
            logger.warning("Polling is already running")
            return

        if not config.is_configured():
            logger.error("Telegram bot not configured")
            return

        # Clear webhooks
        self._clear_webhook()

        self.is_polling = True
        self.polling_thread = threading.Thread(
            target=self._polling_loop,
            name="TelegramPolling",
            daemon=True
        )
        self.polling_thread.start()

        logger.info("Started enhanced Telegram polling")

    def stop_polling(self):
        """Stop polling for messages"""
        self.is_polling = False

        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=10)

        # Flush pending batches
        self.batch_processor.flush_all()

        # Stop message router
        self.message_router.stop()

        logger.info("Stopped Telegram polling")

    def send_message(self, text: str, sender_name: str = "system",
                    reply_to: Optional[int] = None, priority: int = 2) -> bool:
        """Send message with enhanced features"""
        try:
            # Format message
            if sender_name != "system":
                formatted_text = f"{config.get_bot_name(sender_name)}: {text}"
            else:
                formatted_text = text

            # Apply message formatting optimizations
            formatted_text = self._optimize_message_format(formatted_text)

            # Create message for routing
            message = Message(
                id=f"tg_{int(time.time() * 1000)}_{sender_name}",
                content=formatted_text,
                sender=sender_name,
                recipient="telegram",
                priority=priority,
                metadata={
                    'reply_to': reply_to,
                    'chat_id': self.chat_id,
                    'original_text': text
                }
            )

            # Send through router for optimal performance
            return self.message_router.send_message(message, timeout=5.0)

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            with self.metrics_lock:
                self.metrics['messages_failed'] += 1
            return False

    def send_batch_messages(self, messages: List[Tuple[str, str, Optional[int]]]) -> int:
        """Send multiple messages efficiently"""
        successful = 0

        for text, sender_name, reply_to in messages:
            if self.send_message(text, sender_name, reply_to):
                successful += 1

        return successful

    def _handle_routed_message(self, message: Message) -> bool:
        """Handle message from router"""
        try:
            # Check rate limiting
            can_send, wait_time = self.rate_limiter.can_send_message()
            if not can_send:
                if wait_time > 0:
                    logger.debug(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(min(wait_time, 5.0))  # Max 5s wait

                    # Check again after waiting
                    can_send, _ = self.rate_limiter.can_send_message()
                    if not can_send:
                        with self.metrics_lock:
                            self.metrics['rate_limit_hits'] += 1
                        return False

            # Prepare message data
            message_data = {
                'chat_id': message.metadata.get('chat_id', self.chat_id),
                'text': message.content,
                'parse_mode': 'Markdown'
            }

            if message.metadata.get('reply_to'):
                message_data['reply_to_message_id'] = message.metadata['reply_to']

            # Use batch processing for efficiency
            self.batch_processor.add_message(message_data['chat_id'], message_data)

            return True

        except Exception as e:
            logger.error(f"Error handling routed message: {e}")
            return False

    def _send_batch(self, chat_id: str, batch: List[Dict]):
        """Send batch of messages"""
        try:
            start_time = time.time()

            # Try to send as media group if possible
            if len(batch) > 1 and self._can_batch_as_media_group(batch):
                success = self._send_media_group(chat_id, batch)
            else:
                # Send individually with minimal delay
                success = True
                for message_data in batch:
                    if not self._send_single_message_direct(message_data):
                        success = False
                    time.sleep(0.1)  # Small delay between messages

            # Record metrics
            send_time = time.time() - start_time
            with self.metrics_lock:
                self.metrics['batch_sends'] += 1
                if success:
                    self.metrics['messages_sent'] += len(batch)
                    # Update average send time
                    total_messages = self.metrics['messages_sent']
                    current_avg = self.metrics['average_send_time']
                    self.metrics['average_send_time'] = (
                        (current_avg * (total_messages - len(batch)) + send_time) / total_messages
                    )
                else:
                    self.metrics['messages_failed'] += len(batch)

            # Record rate limiting
            self.rate_limiter.record_message_sent(success)

            return success

        except Exception as e:
            logger.error(f"Error sending batch: {e}")
            with self.metrics_lock:
                self.metrics['messages_failed'] += len(batch)
            return False

    def _send_single_message(self, text: str, **kwargs) -> bool:
        """Send single message through failover"""
        return self.failover_manager.send_message(text, **kwargs)

    def _send_single_message_direct(self, message_data: Dict) -> bool:
        """Send single message directly to Telegram"""
        session = self.connection_pool.get_session()
        if not session:
            logger.error("No session available")
            return False

        try:
            url = f"{self.base_url}/sendMessage"

            # Apply message optimizations
            if 'text' in message_data:
                message_data['text'] = self._optimize_message_format(message_data['text'])

            response = session.post(url, json=message_data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                success = result.get('ok', False)

                if not success:
                    logger.error(f"Telegram API error: {result}")

                    # Try fallback without markdown
                    if message_data.get('parse_mode') == 'Markdown':
                        message_data_fallback = message_data.copy()
                        message_data_fallback.pop('parse_mode', None)
                        message_data_fallback['text'] = self._strip_markdown(message_data_fallback['text'])

                        response = session.post(url, json=message_data_fallback, timeout=10)
                        if response.status_code == 200:
                            result = response.json()
                            success = result.get('ok', False)

                return success
            else:
                logger.error(f"HTTP error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
        finally:
            self.connection_pool.return_session(session)

    def _can_batch_as_media_group(self, batch: List[Dict]) -> bool:
        """Check if batch can be sent as media group"""
        # For now, only text messages, so return False
        # This can be extended for media messages
        return False

    def _send_media_group(self, chat_id: str, batch: List[Dict]) -> bool:
        """Send batch as media group"""
        # Implementation for media groups
        # For now, fall back to individual sends
        return all(self._send_single_message_direct(msg) for msg in batch)

    def _optimize_message_format(self, text: str) -> str:
        """Optimize message formatting"""
        # Escape special characters for Markdown
        text = text.replace('_', '\\_')
        text = text.replace('*', '\\*')
        text = text.replace('[', '\\[')
        text = text.replace(']', '\\]')
        text = text.replace('(', '\\(')
        text = text.replace(')', '\\)')
        text = text.replace('`', '\\`')

        # Truncate if too long
        max_length = config.max_message_length
        if len(text) > max_length:
            text = text[:max_length-3] + "..."

        return text

    def _strip_markdown(self, text: str) -> str:
        """Strip markdown formatting"""
        text = text.replace('\\_', '_')
        text = text.replace('\\*', '*')
        text = text.replace('\\[', '[')
        text = text.replace('\\]', ']')
        text = text.replace('\\(', '(')
        text = text.replace('\\)', ')')
        text = text.replace('\\`', '`')
        return text

    def _polling_loop(self):
        """Enhanced polling loop"""
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.is_polling:
            try:
                updates = self._get_updates()

                if updates is not None:
                    consecutive_errors = 0

                    for update in updates:
                        self._process_update(update)
                else:
                    consecutive_errors += 1

                # Adaptive polling interval
                if consecutive_errors > 0:
                    time.sleep(min(consecutive_errors * 2, 30))  # Exponential backoff
                else:
                    time.sleep(1)

                # Stop if too many consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive polling errors, stopping")
                    break

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                consecutive_errors += 1
                time.sleep(5)

    def _get_updates(self) -> Optional[List[Dict]]:
        """Get updates with connection pooling"""
        session = self.connection_pool.get_session()
        if not session:
            return None

        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 10,
                'limit': 100
            }

            response = session.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            if not data.get('ok'):
                logger.error(f"Telegram API error: {data}")
                return []

            updates = data.get('result', [])
            if updates:
                self.last_update_id = updates[-1]['update_id']

            return updates

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                logger.warning("Polling conflict detected")
                self._resolve_polling_conflict()
            else:
                logger.error(f"HTTP error getting updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return None
        finally:
            self.connection_pool.return_session(session)

    def _process_update(self, update: Dict):
        """Process update with metrics"""
        try:
            message_data = update.get('message')
            if not message_data:
                return

            # Only process messages from our chat
            chat_id = str(message_data.get('chat', {}).get('id', ''))
            if chat_id != self.chat_id:
                return

            # Parse message
            parsed_message = self.message_parser.parse_message(message_data)

            # Update metrics
            with self.metrics_lock:
                self.metrics['messages_received'] += 1

            # Notify handlers
            for handler in self.message_handlers:
                try:
                    handler(parsed_message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")

        except Exception as e:
            logger.error(f"Error processing update: {e}")

    def _clear_webhook(self):
        """Clear webhook"""
        session = self.connection_pool.get_session()
        if not session:
            return

        try:
            url = f"{self.base_url}/deleteWebhook"
            response = session.post(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    logger.info("Cleared webhook")

        except Exception as e:
            logger.warning(f"Error clearing webhook: {e}")
        finally:
            self.connection_pool.return_session(session)

    def _resolve_polling_conflict(self):
        """Resolve polling conflicts"""
        try:
            self._clear_webhook()
            time.sleep(2)
            self.last_update_id = 0
            logger.info("Resolved polling conflict")
        except Exception as e:
            logger.error(f"Error resolving conflict: {e}")

    def is_connected(self) -> bool:
        """Check connection status"""
        session = self.connection_pool.get_session()
        if not session:
            return False

        try:
            url = f"{self.base_url}/getMe"
            response = session.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            return data.get('ok', False)

        except Exception:
            return False
        finally:
            self.connection_pool.return_session(session)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        with self.metrics_lock:
            total_messages = self.metrics['messages_sent'] + self.metrics['messages_failed']
            success_rate = (
                self.metrics['messages_sent'] / total_messages
                if total_messages > 0 else 1.0
            )

            return {
                'messages_sent': self.metrics['messages_sent'],
                'messages_failed': self.metrics['messages_failed'],
                'messages_received': self.metrics['messages_received'],
                'success_rate': success_rate,
                'average_send_time': self.metrics['average_send_time'],
                'rate_limit_hits': self.metrics['rate_limit_hits'],
                'batch_sends': self.metrics['batch_sends'],
                'failover_activations': self.metrics['failover_activations'],
                'current_rate_limit': self.rate_limiter.adaptive_factor,
                'router_metrics': self.message_router.get_metrics(),
                'channel_status': self.failover_manager.get_channel_status()
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status"""
        metrics = self.get_performance_metrics()
        router_health = self.message_router.get_health_status()

        # Determine overall health
        health = "HEALTHY"
        issues = []

        if metrics['success_rate'] < 0.9:
            health = "DEGRADED"
            issues.append(f"Low success rate: {metrics['success_rate']:.2%}")

        if metrics['rate_limit_hits'] > 10:
            health = "DEGRADED"
            issues.append(f"Frequent rate limiting: {metrics['rate_limit_hits']} hits")

        if router_health['status'] != "HEALTHY":
            health = router_health['status']
            issues.extend(router_health['issues'])

        if not self.is_connected():
            health = "UNHEALTHY"
            issues.append("Not connected to Telegram")

        return {
            'status': health,
            'issues': issues,
            'metrics': metrics,
            'router_health': router_health,
            'timestamp': datetime.now().isoformat()
        }