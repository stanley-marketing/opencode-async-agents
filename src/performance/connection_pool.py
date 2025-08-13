# SPDX-License-Identifier: MIT
"""
High-Performance WebSocket Connection Pool
Manages connection pooling and load balancing for optimal performance
"""

import asyncio
import logging
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor
import psutil

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolStats:
    """Connection pool statistics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    peak_connections: int = 0
    connection_creates: int = 0
    connection_destroys: int = 0
    pool_hits: int = 0
    pool_misses: int = 0
    avg_connection_age_seconds: float = 0.0
    utilization_percent: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ConnectionMetrics:
    """Per-connection metrics for pool management"""
    created_at: datetime
    last_used: datetime
    use_count: int = 0
    bytes_transferred: int = 0
    error_count: int = 0
    is_healthy: bool = True
    priority: int = 1  # 1=normal, 2=high, 3=critical
    
    def update_usage(self, bytes_count: int = 0):
        """Update connection usage metrics"""
        self.last_used = datetime.now()
        self.use_count += 1
        self.bytes_transferred += bytes_count
    
    def get_age_seconds(self) -> float:
        """Get connection age in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_idle_seconds(self) -> float:
        """Get idle time in seconds"""
        return (datetime.now() - self.last_used).total_seconds()


class ConnectionGroup:
    """Manages a group of connections with load balancing"""
    
    def __init__(self, group_id: str, max_size: int = 100):
        self.group_id = group_id
        self.max_size = max_size
        self.connections: Dict[str, Any] = {}  # user_id -> connection
        self.metrics: Dict[str, ConnectionMetrics] = {}
        self.round_robin_index = 0
        self.lock = asyncio.Lock()
        
        # Load balancing strategies
        self.load_balance_strategy = "round_robin"  # round_robin, least_connections, least_latency
        
    async def add_connection(self, user_id: str, connection: Any) -> bool:
        """Add connection to group"""
        async with self.lock:
            if len(self.connections) >= self.max_size:
                # Remove oldest idle connection
                await self._evict_idle_connection()
            
            self.connections[user_id] = connection
            self.metrics[user_id] = ConnectionMetrics(
                created_at=datetime.now(),
                last_used=datetime.now()
            )
            
            logger.debug(f"Added connection {user_id} to group {self.group_id}")
            return True
    
    async def remove_connection(self, user_id: str) -> bool:
        """Remove connection from group"""
        async with self.lock:
            if user_id in self.connections:
                del self.connections[user_id]
                if user_id in self.metrics:
                    del self.metrics[user_id]
                logger.debug(f"Removed connection {user_id} from group {self.group_id}")
                return True
            return False
    
    async def get_connection(self, user_id: str) -> Optional[Any]:
        """Get specific connection"""
        async with self.lock:
            connection = self.connections.get(user_id)
            if connection and user_id in self.metrics:
                self.metrics[user_id].update_usage()
            return connection
    
    async def get_best_connection(self) -> Optional[Tuple[str, Any]]:
        """Get best connection based on load balancing strategy"""
        async with self.lock:
            if not self.connections:
                return None
            
            if self.load_balance_strategy == "round_robin":
                return await self._get_round_robin_connection()
            elif self.load_balance_strategy == "least_connections":
                return await self._get_least_used_connection()
            elif self.load_balance_strategy == "least_latency":
                return await self._get_lowest_latency_connection()
            else:
                return await self._get_round_robin_connection()
    
    async def _get_round_robin_connection(self) -> Optional[Tuple[str, Any]]:
        """Get connection using round-robin strategy"""
        if not self.connections:
            return None
        
        connection_list = list(self.connections.items())
        if self.round_robin_index >= len(connection_list):
            self.round_robin_index = 0
        
        user_id, connection = connection_list[self.round_robin_index]
        self.round_robin_index = (self.round_robin_index + 1) % len(connection_list)
        
        if user_id in self.metrics:
            self.metrics[user_id].update_usage()
        
        return user_id, connection
    
    async def _get_least_used_connection(self) -> Optional[Tuple[str, Any]]:
        """Get connection with least usage"""
        if not self.connections:
            return None
        
        best_user_id = min(
            self.connections.keys(),
            key=lambda uid: self.metrics.get(uid, ConnectionMetrics(datetime.now(), datetime.now())).use_count
        )
        
        connection = self.connections[best_user_id]
        if best_user_id in self.metrics:
            self.metrics[best_user_id].update_usage()
        
        return best_user_id, connection
    
    async def _get_lowest_latency_connection(self) -> Optional[Tuple[str, Any]]:
        """Get connection with lowest latency (if available)"""
        if not self.connections:
            return None
        
        # For now, fall back to least used
        # In a real implementation, you'd track latency per connection
        return await self._get_least_used_connection()
    
    async def _evict_idle_connection(self):
        """Evict the most idle connection"""
        if not self.connections:
            return
        
        # Find most idle connection
        most_idle_user_id = max(
            self.connections.keys(),
            key=lambda uid: self.metrics.get(uid, ConnectionMetrics(datetime.now(), datetime.now())).get_idle_seconds()
        )
        
        await self.remove_connection(most_idle_user_id)
        logger.debug(f"Evicted idle connection {most_idle_user_id} from group {self.group_id}")
    
    async def cleanup_stale_connections(self, max_idle_seconds: int = 300):
        """Clean up stale connections"""
        async with self.lock:
            stale_connections = []
            
            for user_id, metrics in self.metrics.items():
                if metrics.get_idle_seconds() > max_idle_seconds:
                    stale_connections.append(user_id)
            
            for user_id in stale_connections:
                await self.remove_connection(user_id)
            
            if stale_connections:
                logger.info(f"Cleaned up {len(stale_connections)} stale connections from group {self.group_id}")
    
    def get_stats(self) -> dict:
        """Get group statistics"""
        total_connections = len(self.connections)
        if not self.metrics:
            return {
                'group_id': self.group_id,
                'total_connections': total_connections,
                'max_size': self.max_size,
                'utilization_percent': 0.0,
                'avg_age_seconds': 0.0,
                'avg_idle_seconds': 0.0
            }
        
        avg_age = sum(m.get_age_seconds() for m in self.metrics.values()) / len(self.metrics)
        avg_idle = sum(m.get_idle_seconds() for m in self.metrics.values()) / len(self.metrics)
        utilization = (total_connections / self.max_size) * 100
        
        return {
            'group_id': self.group_id,
            'total_connections': total_connections,
            'max_size': self.max_size,
            'utilization_percent': utilization,
            'avg_age_seconds': avg_age,
            'avg_idle_seconds': avg_idle,
            'load_balance_strategy': self.load_balance_strategy
        }


class WebSocketConnectionPool:
    """High-performance WebSocket connection pool with load balancing"""
    
    def __init__(self, max_connections: int = 2000, max_groups: int = 50):
        self.max_connections = max_connections
        self.max_groups = max_groups
        
        # Connection groups (by role, region, etc.)
        self.groups: Dict[str, ConnectionGroup] = {}
        self.default_group = ConnectionGroup("default", max_connections)
        
        # Global connection tracking
        self.all_connections: Dict[str, Any] = {}  # user_id -> connection
        self.connection_to_group: Dict[str, str] = {}  # user_id -> group_id
        
        # Pool statistics
        self.stats = ConnectionPoolStats()
        self.peak_connections = 0
        
        # Background tasks
        self.cleanup_task = None
        self.stats_task = None
        self.is_running = False
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pool-worker")
        
        # Locks
        self.global_lock = asyncio.Lock()
        
    async def start(self):
        """Start the connection pool"""
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.stats_task = asyncio.create_task(self._stats_loop())
        logger.info("Connection pool started")
    
    async def stop(self):
        """Stop the connection pool"""
        self.is_running = False
        
        # Cancel background tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.stats_task:
            self.stats_task.cancel()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("Connection pool stopped")
    
    async def add_connection(self, connection: Any, group_id: str = "default") -> bool:
        """Add connection to pool"""
        user_id = getattr(connection, 'user_id', str(id(connection)))
        
        async with self.global_lock:
            # Check global limit
            if len(self.all_connections) >= self.max_connections:
                logger.warning("Connection pool at capacity")
                return False
            
            # Get or create group
            if group_id not in self.groups:
                if len(self.groups) >= self.max_groups:
                    group_id = "default"  # Fall back to default group
                else:
                    self.groups[group_id] = ConnectionGroup(
                        group_id, 
                        max_size=max(100, self.max_connections // self.max_groups)
                    )
            
            group = self.groups.get(group_id, self.default_group)
            
            # Add to group
            if await group.add_connection(user_id, connection):
                self.all_connections[user_id] = connection
                self.connection_to_group[user_id] = group_id
                
                # Update stats
                self.stats.total_connections = len(self.all_connections)
                self.stats.connection_creates += 1
                self.peak_connections = max(self.peak_connections, self.stats.total_connections)
                self.stats.peak_connections = self.peak_connections
                
                logger.debug(f"Added connection {user_id} to pool (group: {group_id})")
                return True
            
            return False
    
    async def remove_connection(self, connection: Any) -> bool:
        """Remove connection from pool"""
        user_id = getattr(connection, 'user_id', str(id(connection)))
        
        async with self.global_lock:
            if user_id not in self.all_connections:
                return False
            
            # Remove from group
            group_id = self.connection_to_group.get(user_id, "default")
            group = self.groups.get(group_id, self.default_group)
            await group.remove_connection(user_id)
            
            # Remove from global tracking
            del self.all_connections[user_id]
            if user_id in self.connection_to_group:
                del self.connection_to_group[user_id]
            
            # Update stats
            self.stats.total_connections = len(self.all_connections)
            self.stats.connection_destroys += 1
            
            logger.debug(f"Removed connection {user_id} from pool")
            return True
    
    async def get_connection(self, user_id: str) -> Optional[Any]:
        """Get specific connection"""
        if user_id not in self.all_connections:
            self.stats.pool_misses += 1
            return None
        
        group_id = self.connection_to_group.get(user_id, "default")
        group = self.groups.get(group_id, self.default_group)
        
        connection = await group.get_connection(user_id)
        if connection:
            self.stats.pool_hits += 1
        else:
            self.stats.pool_misses += 1
        
        return connection
    
    async def get_connections_by_group(self, group_id: str) -> List[Any]:
        """Get all connections in a group"""
        if group_id not in self.groups:
            return []
        
        group = self.groups[group_id]
        async with group.lock:
            return list(group.connections.values())
    
    async def get_best_connection_from_group(self, group_id: str) -> Optional[Any]:
        """Get best connection from specific group"""
        if group_id not in self.groups:
            return None
        
        group = self.groups[group_id]
        result = await group.get_best_connection()
        
        if result:
            user_id, connection = result
            self.stats.pool_hits += 1
            return connection
        else:
            self.stats.pool_misses += 1
            return None
    
    async def broadcast_to_group(self, group_id: str, message: dict, 
                                exclude_user: str = None) -> int:
        """Broadcast message to all connections in a group"""
        connections = await self.get_connections_by_group(group_id)
        
        if not connections:
            return 0
        
        # Filter out excluded user
        if exclude_user:
            connections = [
                conn for conn in connections 
                if getattr(conn, 'user_id', None) != exclude_user
            ]
        
        # Send to all connections concurrently
        tasks = []
        for connection in connections:
            if hasattr(connection, 'send_message'):
                tasks.append(connection.send_message(message))
        
        if not tasks:
            return 0
        
        # Execute with limited concurrency
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for result in results if result is True)
        
        return successful
    
    async def broadcast_to_all(self, message: dict, exclude_user: str = None) -> int:
        """Broadcast message to all connections"""
        connections = list(self.all_connections.values())
        
        if not connections:
            return 0
        
        # Filter out excluded user
        if exclude_user:
            connections = [
                conn for conn in connections 
                if getattr(conn, 'user_id', None) != exclude_user
            ]
        
        # Send to all connections with batching
        batch_size = 100
        total_successful = 0
        
        for i in range(0, len(connections), batch_size):
            batch = connections[i:i + batch_size]
            tasks = []
            
            for connection in batch:
                if hasattr(connection, 'send_message'):
                    tasks.append(connection.send_message(message))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                total_successful += sum(1 for result in results if result is True)
        
        return total_successful
    
    async def set_group_load_balance_strategy(self, group_id: str, strategy: str):
        """Set load balancing strategy for a group"""
        if group_id in self.groups:
            self.groups[group_id].load_balance_strategy = strategy
            logger.info(f"Set load balance strategy for group {group_id}: {strategy}")
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.is_running:
            try:
                # Clean up stale connections in all groups
                cleanup_tasks = []
                for group in self.groups.values():
                    cleanup_tasks.append(group.cleanup_stale_connections())
                
                if cleanup_tasks:
                    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                
                # Clean up empty groups
                empty_groups = [
                    group_id for group_id, group in self.groups.items()
                    if not group.connections and group_id != "default"
                ]
                
                for group_id in empty_groups:
                    del self.groups[group_id]
                    logger.debug(f"Removed empty group: {group_id}")
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(30)
    
    async def _stats_loop(self):
        """Background statistics collection loop"""
        while self.is_running:
            try:
                await self._update_stats()
                await asyncio.sleep(10)  # Update stats every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in stats loop: {e}")
                await asyncio.sleep(30)
    
    async def _update_stats(self):
        """Update pool statistics"""
        total_connections = len(self.all_connections)
        
        # Calculate utilization
        utilization = (total_connections / self.max_connections) * 100
        
        # Calculate average connection age
        if self.all_connections:
            total_age = 0
            connection_count = 0
            
            for group in self.groups.values():
                for metrics in group.metrics.values():
                    total_age += metrics.get_age_seconds()
                    connection_count += 1
            
            avg_age = total_age / connection_count if connection_count > 0 else 0
        else:
            avg_age = 0
        
        # Update stats
        self.stats.total_connections = total_connections
        self.stats.active_connections = total_connections  # All are considered active
        self.stats.idle_connections = 0  # Would need more sophisticated tracking
        self.stats.avg_connection_age_seconds = avg_age
        self.stats.utilization_percent = utilization
        self.stats.last_updated = datetime.now()
    
    def get_stats(self) -> ConnectionPoolStats:
        """Get pool statistics"""
        return self.stats
    
    def get_detailed_stats(self) -> dict:
        """Get detailed statistics including group stats"""
        group_stats = {}
        for group_id, group in self.groups.items():
            group_stats[group_id] = group.get_stats()
        
        return {
            'pool_stats': {
                'total_connections': self.stats.total_connections,
                'max_connections': self.max_connections,
                'peak_connections': self.stats.peak_connections,
                'utilization_percent': self.stats.utilization_percent,
                'connection_creates': self.stats.connection_creates,
                'connection_destroys': self.stats.connection_destroys,
                'pool_hits': self.stats.pool_hits,
                'pool_misses': self.stats.pool_misses,
                'hit_ratio': (self.stats.pool_hits / max(self.stats.pool_hits + self.stats.pool_misses, 1)) * 100,
                'avg_connection_age_seconds': self.stats.avg_connection_age_seconds,
                'last_updated': self.stats.last_updated.isoformat()
            },
            'group_stats': group_stats,
            'system_stats': {
                'total_groups': len(self.groups),
                'max_groups': self.max_groups,
                'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024
            }
        }
    
    def get_utilization(self) -> float:
        """Get current pool utilization percentage"""
        return self.stats.utilization_percent
    
    async def health_check(self) -> dict:
        """Perform health check on the connection pool"""
        healthy_connections = 0
        unhealthy_connections = 0
        
        for connection in self.all_connections.values():
            if hasattr(connection, 'is_healthy'):
                if connection.is_healthy:
                    healthy_connections += 1
                else:
                    unhealthy_connections += 1
            else:
                healthy_connections += 1  # Assume healthy if no health attribute
        
        health_percentage = (healthy_connections / max(len(self.all_connections), 1)) * 100
        
        return {
            'status': 'healthy' if health_percentage >= 95 else 'degraded' if health_percentage >= 80 else 'unhealthy',
            'total_connections': len(self.all_connections),
            'healthy_connections': healthy_connections,
            'unhealthy_connections': unhealthy_connections,
            'health_percentage': health_percentage,
            'utilization_percentage': self.stats.utilization_percent,
            'groups_count': len(self.groups),
            'timestamp': datetime.now().isoformat()
        }


# Load balancing strategies
class LoadBalanceStrategy:
    """Base class for load balancing strategies"""
    
    @staticmethod
    async def select_connection(connections: Dict[str, Any], 
                              metrics: Dict[str, ConnectionMetrics]) -> Optional[str]:
        """Select best connection based on strategy"""
        raise NotImplementedError


class RoundRobinStrategy(LoadBalanceStrategy):
    """Round-robin load balancing"""
    
    def __init__(self):
        self.index = 0
    
    async def select_connection(self, connections: Dict[str, Any], 
                              metrics: Dict[str, ConnectionMetrics]) -> Optional[str]:
        if not connections:
            return None
        
        connection_list = list(connections.keys())
        if self.index >= len(connection_list):
            self.index = 0
        
        selected = connection_list[self.index]
        self.index = (self.index + 1) % len(connection_list)
        
        return selected


class LeastConnectionsStrategy(LoadBalanceStrategy):
    """Least connections load balancing"""
    
    @staticmethod
    async def select_connection(connections: Dict[str, Any], 
                              metrics: Dict[str, ConnectionMetrics]) -> Optional[str]:
        if not connections:
            return None
        
        return min(
            connections.keys(),
            key=lambda uid: metrics.get(uid, ConnectionMetrics(datetime.now(), datetime.now())).use_count
        )


class WeightedRoundRobinStrategy(LoadBalanceStrategy):
    """Weighted round-robin based on connection health and performance"""
    
    def __init__(self):
        self.weights = {}
        self.current_weights = {}
    
    async def select_connection(self, connections: Dict[str, Any], 
                              metrics: Dict[str, ConnectionMetrics]) -> Optional[str]:
        if not connections:
            return None
        
        # Update weights based on connection health and performance
        for user_id in connections.keys():
            metric = metrics.get(user_id)
            if metric:
                # Calculate weight based on health, age, and error rate
                base_weight = 100
                if metric.error_count > 0:
                    base_weight -= min(metric.error_count * 10, 50)
                if not metric.is_healthy:
                    base_weight -= 30
                
                self.weights[user_id] = max(base_weight, 10)
            else:
                self.weights[user_id] = 100
        
        # Weighted round-robin selection
        total_weight = sum(self.weights.get(uid, 100) for uid in connections.keys())
        if total_weight == 0:
            return list(connections.keys())[0]
        
        # Initialize current weights if needed
        for user_id in connections.keys():
            if user_id not in self.current_weights:
                self.current_weights[user_id] = 0
        
        # Find connection with highest current weight
        best_user_id = max(
            connections.keys(),
            key=lambda uid: self.current_weights.get(uid, 0)
        )
        
        # Update current weights
        self.current_weights[best_user_id] -= total_weight
        for user_id in connections.keys():
            self.current_weights[user_id] += self.weights.get(user_id, 100)
        
        return best_user_id