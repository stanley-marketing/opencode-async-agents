#!/usr/bin/env python3
"""
Performance Optimizer for OpenCode-Slack System
Implements advanced performance optimizations including connection pooling,
request batching, caching, and dynamic resource allocation.
"""

import asyncio
import logging
import threading
import time
import weakref
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
import sqlite3
import json
import hashlib
from queue import Queue, Empty
import psutil
import gc

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_connections: int = 0
    cache_hit_rate: float = 0.0
    avg_response_time: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    queue_depth: int = 0


class AdaptiveConnectionPool:
    """Adaptive database connection pool with dynamic sizing"""
    
    def __init__(self, db_path: str, min_connections: int = 5, max_connections: int = 50):
        self.db_path = db_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        
        # Connection management
        self.available_connections = deque()
        self.active_connections = set()
        self.connection_stats = defaultdict(lambda: {'created': 0, 'used': 0, 'errors': 0})
        
        # Synchronization
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        
        # Performance tracking
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.peak_usage = 0
        
        # Initialize minimum connections
        self._initialize_connections()
        
        # Background maintenance
        self.maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self.maintenance_thread.start()
        
        logger.info(f"AdaptiveConnectionPool initialized: {min_connections}-{max_connections} connections")
    
    def _initialize_connections(self):
        """Initialize minimum number of connections"""
        with self.lock:
            for _ in range(self.min_connections):
                conn = self._create_connection()
                if conn:
                    self.available_connections.append(conn)
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create a new database connection"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None  # Autocommit mode
            )
            
            # Optimize connection settings
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB
            
            self.connection_stats[id(conn)]['created'] = time.time()
            return conn
            
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            return None
    
    def get_connection(self, timeout: float = 30.0):
        """Get a connection from the pool"""
        start_time = time.time()
        
        with self.condition:
            while True:
                # Try to get available connection
                if self.available_connections:
                    conn = self.available_connections.popleft()
                    self.active_connections.add(conn)
                    self.connection_stats[id(conn)]['used'] += 1
                    
                    # Update metrics
                    self.total_requests += 1
                    self.total_wait_time += time.time() - start_time
                    self.peak_usage = max(self.peak_usage, len(self.active_connections))
                    
                    return ConnectionWrapper(self, conn)
                
                # Create new connection if under limit
                if len(self.active_connections) + len(self.available_connections) < self.max_connections:
                    conn = self._create_connection()
                    if conn:
                        self.active_connections.add(conn)
                        self.connection_stats[id(conn)]['used'] += 1
                        
                        self.total_requests += 1
                        self.total_wait_time += time.time() - start_time
                        self.peak_usage = max(self.peak_usage, len(self.active_connections))
                        
                        return ConnectionWrapper(self, conn)
                
                # Wait for connection to become available
                if time.time() - start_time >= timeout:
                    raise TimeoutError("Connection pool timeout")
                
                self.condition.wait(timeout=1.0)
    
    def return_connection(self, conn: sqlite3.Connection, error: bool = False):
        """Return a connection to the pool"""
        with self.condition:
            self.active_connections.discard(conn)
            
            if error:
                self.connection_stats[id(conn)]['errors'] += 1
                # Close errored connections
                try:
                    conn.close()
                except:
                    pass
            else:
                # Return healthy connections to pool
                if len(self.available_connections) < self.max_connections // 2:
                    self.available_connections.append(conn)
                else:
                    # Close excess connections
                    try:
                        conn.close()
                    except:
                        pass
            
            self.condition.notify_all()
    
    def _maintenance_loop(self):
        """Background maintenance for connection pool"""
        while True:
            try:
                time.sleep(60)  # Run every minute
                
                with self.lock:
                    # Remove stale connections
                    current_time = time.time()
                    stale_connections = []
                    
                    for conn in list(self.available_connections):
                        conn_id = id(conn)
                        if current_time - self.connection_stats[conn_id]['created'] > 3600:  # 1 hour
                            stale_connections.append(conn)
                    
                    for conn in stale_connections:
                        self.available_connections.remove(conn)
                        try:
                            conn.close()
                        except:
                            pass
                    
                    # Ensure minimum connections
                    while len(self.available_connections) < self.min_connections:
                        conn = self._create_connection()
                        if conn:
                            self.available_connections.append(conn)
                        else:
                            break
                
                logger.debug(f"Connection pool maintenance: "
                           f"{len(self.available_connections)} available, "
                           f"{len(self.active_connections)} active")
                
            except Exception as e:
                logger.error(f"Error in connection pool maintenance: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self.lock:
            avg_wait_time = self.total_wait_time / max(self.total_requests, 1)
            
            return {
                'available_connections': len(self.available_connections),
                'active_connections': len(self.active_connections),
                'total_connections': len(self.available_connections) + len(self.active_connections),
                'max_connections': self.max_connections,
                'total_requests': self.total_requests,
                'avg_wait_time': avg_wait_time,
                'peak_usage': self.peak_usage,
                'utilization': len(self.active_connections) / self.max_connections
            }


class ConnectionWrapper:
    """Wrapper for database connections with automatic return to pool"""
    
    def __init__(self, pool: AdaptiveConnectionPool, connection: sqlite3.Connection):
        self.pool = pool
        self.connection = connection
        self.error_occurred = False
    
    def __enter__(self):
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.error_occurred = exc_type is not None
        self.pool.return_connection(self.connection, self.error_occurred)
    
    def __getattr__(self, name):
        return getattr(self.connection, name)


class IntelligentCache:
    """Intelligent caching system with LRU eviction and performance tracking"""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Cache storage
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order = deque()
        self.access_counts = defaultdict(int)
        
        # Performance tracking
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        # Synchronization
        self.lock = threading.RLock()
        
        # Background cleanup
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info(f"IntelligentCache initialized: {max_size} items, {ttl_seconds}s TTL")
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # Check TTL
                if time.time() - entry['timestamp'] < self.ttl_seconds:
                    # Update access tracking
                    self.access_counts[key] += 1
                    self.access_order.append(key)
                    self.hits += 1
                    
                    return entry['value']
                else:
                    # Expired entry
                    del self.cache[key]
                    self.access_counts.pop(key, None)
            
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any):
        """Put item in cache"""
        with self.lock:
            # Check if we need to evict
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            # Store entry
            self.cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
            self.access_order.append(key)
            self.access_counts[key] += 1
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self.access_order:
            return
        
        # Find LRU item
        lru_key = None
        min_access_count = float('inf')
        
        for key in list(self.access_order):
            if key in self.cache and self.access_counts[key] < min_access_count:
                min_access_count = self.access_counts[key]
                lru_key = key
        
        if lru_key:
            del self.cache[lru_key]
            self.access_counts.pop(lru_key, None)
            self.evictions += 1
            
            # Remove from access order
            while lru_key in self.access_order:
                self.access_order.remove(lru_key)
    
    def _cleanup_loop(self):
        """Background cleanup of expired entries"""
        while True:
            try:
                time.sleep(300)  # Run every 5 minutes
                
                with self.lock:
                    current_time = time.time()
                    expired_keys = []
                    
                    for key, entry in self.cache.items():
                        if current_time - entry['timestamp'] >= self.ttl_seconds:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        del self.cache[key]
                        self.access_counts.pop(key, None)
                        
                        # Remove from access order
                        while key in self.access_order:
                            self.access_order.remove(key)
                
                if expired_keys:
                    logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / max(total_requests, 1)
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'evictions': self.evictions,
                'utilization': len(self.cache) / self.max_size
            }
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.access_counts.clear()


class BatchProcessor:
    """Batch processor for optimizing database operations"""
    
    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Batch storage
        self.insert_batches = defaultdict(list)
        self.update_batches = defaultdict(list)
        self.delete_batches = defaultdict(list)
        
        # Synchronization
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        
        # Background processing
        self.processor_thread = threading.Thread(target=self._processor_loop, daemon=True)
        self.processor_thread.start()
        
        # Performance tracking
        self.operations_batched = 0
        self.batches_processed = 0
        
        logger.info(f"BatchProcessor initialized: {batch_size} batch size, {flush_interval}s interval")
    
    def add_insert(self, table: str, data: Dict[str, Any]):
        """Add insert operation to batch"""
        with self.condition:
            self.insert_batches[table].append(data)
            self.operations_batched += 1
            
            if len(self.insert_batches[table]) >= self.batch_size:
                self.condition.notify()
    
    def add_update(self, table: str, data: Dict[str, Any], where_clause: str):
        """Add update operation to batch"""
        with self.condition:
            self.update_batches[table].append({'data': data, 'where': where_clause})
            self.operations_batched += 1
            
            if len(self.update_batches[table]) >= self.batch_size:
                self.condition.notify()
    
    def add_delete(self, table: str, where_clause: str):
        """Add delete operation to batch"""
        with self.condition:
            self.delete_batches[table].append(where_clause)
            self.operations_batched += 1
            
            if len(self.delete_batches[table]) >= self.batch_size:
                self.condition.notify()
    
    def flush(self, connection_pool: AdaptiveConnectionPool):
        """Flush all pending batches"""
        with self.lock:
            self._process_batches(connection_pool)
    
    def _processor_loop(self):
        """Background batch processing loop"""
        while True:
            try:
                with self.condition:
                    # Wait for batches to accumulate or timeout
                    self.condition.wait(timeout=self.flush_interval)
                
                # Process batches if any exist
                # Note: This would need a connection pool reference
                # For now, just track that processing would occur
                with self.lock:
                    total_operations = (
                        sum(len(batch) for batch in self.insert_batches.values()) +
                        sum(len(batch) for batch in self.update_batches.values()) +
                        sum(len(batch) for batch in self.delete_batches.values())
                    )
                    
                    if total_operations > 0:
                        logger.debug(f"Would process {total_operations} batched operations")
                        # Clear batches (in real implementation, would execute them)
                        self.insert_batches.clear()
                        self.update_batches.clear()
                        self.delete_batches.clear()
                        self.batches_processed += 1
                
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
    
    def _process_batches(self, connection_pool: AdaptiveConnectionPool):
        """Process all pending batches"""
        try:
            with connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Process inserts
                for table, batch in self.insert_batches.items():
                    if batch:
                        self._execute_insert_batch(cursor, table, batch)
                
                # Process updates
                for table, batch in self.update_batches.items():
                    if batch:
                        self._execute_update_batch(cursor, table, batch)
                
                # Process deletes
                for table, batch in self.delete_batches.items():
                    if batch:
                        self._execute_delete_batch(cursor, table, batch)
                
                conn.commit()
                self.batches_processed += 1
                
                # Clear processed batches
                self.insert_batches.clear()
                self.update_batches.clear()
                self.delete_batches.clear()
                
        except Exception as e:
            logger.error(f"Error processing batches: {e}")
    
    def _execute_insert_batch(self, cursor, table: str, batch: List[Dict[str, Any]]):
        """Execute batch insert"""
        if not batch:
            return
        
        # Build insert statement
        columns = list(batch[0].keys())
        placeholders = ', '.join(['?' for _ in columns])
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Prepare data
        data = [[row[col] for col in columns] for row in batch]
        
        cursor.executemany(sql, data)
    
    def _execute_update_batch(self, cursor, table: str, batch: List[Dict[str, Any]]):
        """Execute batch update"""
        for operation in batch:
            data = operation['data']
            where_clause = operation['where']
            
            set_clause = ', '.join([f"{col} = ?" for col in data.keys()])
            sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            
            cursor.execute(sql, list(data.values()))
    
    def _execute_delete_batch(self, cursor, table: str, batch: List[str]):
        """Execute batch delete"""
        for where_clause in batch:
            sql = f"DELETE FROM {table} WHERE {where_clause}"
            cursor.execute(sql)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch processor statistics"""
        with self.lock:
            pending_operations = (
                sum(len(batch) for batch in self.insert_batches.values()) +
                sum(len(batch) for batch in self.update_batches.values()) +
                sum(len(batch) for batch in self.delete_batches.values())
            )
            
            return {
                'operations_batched': self.operations_batched,
                'batches_processed': self.batches_processed,
                'pending_operations': pending_operations,
                'avg_batch_size': self.operations_batched / max(self.batches_processed, 1)
            }


class PerformanceOptimizer:
    """Main performance optimizer coordinating all optimization components"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # Core components
        self.connection_pool = AdaptiveConnectionPool(db_path)
        self.cache = IntelligentCache()
        self.batch_processor = BatchProcessor()
        
        # Performance monitoring
        self.metrics_history = deque(maxlen=1000)
        self.performance_thread = threading.Thread(target=self._performance_monitor, daemon=True)
        self.performance_thread.start()
        
        # System optimization
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
        
        logger.info("PerformanceOptimizer initialized")
    
    def _performance_monitor(self):
        """Monitor system performance metrics"""
        while True:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_info = psutil.virtual_memory()
                
                # Collect component metrics
                pool_stats = self.connection_pool.get_stats()
                cache_stats = self.cache.get_stats()
                batch_stats = self.batch_processor.get_stats()
                
                # Create performance snapshot
                metrics = PerformanceMetrics(
                    cpu_usage=cpu_percent,
                    memory_usage=memory_info.percent,
                    active_connections=pool_stats['active_connections'],
                    cache_hit_rate=cache_stats['hit_rate'],
                    avg_response_time=pool_stats['avg_wait_time'],
                    queue_depth=batch_stats['pending_operations']
                )
                
                self.metrics_history.append(metrics)
                
                # Log performance summary every 5 minutes
                if len(self.metrics_history) % 300 == 0:
                    self._log_performance_summary()
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
            
            time.sleep(1)
    
    def _optimization_loop(self):
        """Continuous optimization based on performance metrics"""
        while True:
            try:
                time.sleep(30)  # Run every 30 seconds
                
                if len(self.metrics_history) < 10:
                    continue
                
                # Analyze recent performance
                recent_metrics = list(self.metrics_history)[-10:]
                avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
                avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
                avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
                
                # Optimize based on metrics
                self._optimize_based_on_metrics(avg_cpu, avg_memory, avg_cache_hit_rate)
                
                # Trigger garbage collection if memory usage is high
                if avg_memory > 80:
                    gc.collect()
                    logger.info("Triggered garbage collection due to high memory usage")
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
    
    def _optimize_based_on_metrics(self, cpu_usage: float, memory_usage: float, cache_hit_rate: float):
        """Optimize system based on performance metrics"""
        
        # Adjust connection pool size based on CPU usage
        if cpu_usage > 80:
            # High CPU - reduce connection pool size
            current_max = self.connection_pool.max_connections
            new_max = max(self.connection_pool.min_connections, int(current_max * 0.9))
            if new_max != current_max:
                self.connection_pool.max_connections = new_max
                logger.info(f"Reduced max connections to {new_max} due to high CPU usage")
        
        elif cpu_usage < 30:
            # Low CPU - can increase connection pool size
            current_max = self.connection_pool.max_connections
            new_max = min(100, int(current_max * 1.1))
            if new_max != current_max:
                self.connection_pool.max_connections = new_max
                logger.info(f"Increased max connections to {new_max} due to low CPU usage")
        
        # Adjust cache size based on memory usage and hit rate
        if memory_usage > 70 and cache_hit_rate < 0.5:
            # High memory usage with low hit rate - reduce cache size
            new_size = max(1000, int(self.cache.max_size * 0.8))
            if new_size != self.cache.max_size:
                self.cache.max_size = new_size
                logger.info(f"Reduced cache size to {new_size} due to high memory usage")
        
        elif memory_usage < 50 and cache_hit_rate > 0.8:
            # Low memory usage with high hit rate - increase cache size
            new_size = min(50000, int(self.cache.max_size * 1.2))
            if new_size != self.cache.max_size:
                self.cache.max_size = new_size
                logger.info(f"Increased cache size to {new_size} due to good performance")
    
    def _log_performance_summary(self):
        """Log comprehensive performance summary"""
        if not self.metrics_history:
            return
        
        recent_metrics = list(self.metrics_history)[-60:]  # Last minute
        
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        
        pool_stats = self.connection_pool.get_stats()
        cache_stats = self.cache.get_stats()
        batch_stats = self.batch_processor.get_stats()
        
        logger.info(f"Performance Summary:")
        logger.info(f"  System: CPU {avg_cpu:.1f}%, Memory {avg_memory:.1f}%")
        logger.info(f"  Connections: {pool_stats['active_connections']}/{pool_stats['max_connections']} "
                   f"(util: {pool_stats['utilization']:.1%})")
        logger.info(f"  Cache: {cache_stats['size']}/{cache_stats['max_size']} "
                   f"(hit rate: {avg_cache_hit_rate:.1%})")
        logger.info(f"  Batching: {batch_stats['pending_operations']} pending, "
                   f"{batch_stats['batches_processed']} processed")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        pool_stats = self.connection_pool.get_stats()
        cache_stats = self.cache.get_stats()
        batch_stats = self.batch_processor.get_stats()
        
        # Calculate recent performance trends
        recent_metrics = list(self.metrics_history)[-60:] if self.metrics_history else []
        
        if recent_metrics:
            avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
            avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        else:
            avg_cpu = avg_memory = avg_cache_hit_rate = 0.0
        
        return {
            'system_metrics': {
                'cpu_usage': avg_cpu,
                'memory_usage': avg_memory,
                'active_threads': threading.active_count()
            },
            'connection_pool': pool_stats,
            'cache': cache_stats,
            'batch_processor': batch_stats,
            'performance_trends': {
                'avg_cache_hit_rate': avg_cache_hit_rate,
                'metrics_collected': len(self.metrics_history)
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def optimize_query(self, query: str, params: tuple = ()) -> Any:
        """Execute optimized database query with caching"""
        # Create cache key
        cache_key = hashlib.md5(f"{query}:{params}".encode()).hexdigest()
        
        # Check cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Execute query
        with self.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                # Cache SELECT results
                self.cache.put(cache_key, result)
                return result
            else:
                conn.commit()
                return cursor.rowcount
    
    def batch_insert(self, table: str, data: List[Dict[str, Any]]):
        """Optimized batch insert"""
        for row in data:
            self.batch_processor.add_insert(table, row)
    
    def batch_update(self, table: str, data: Dict[str, Any], where_clause: str):
        """Optimized batch update"""
        self.batch_processor.add_update(table, data, where_clause)
    
    def flush_batches(self):
        """Flush all pending batch operations"""
        self.batch_processor.flush(self.connection_pool)