# SPDX-License-Identifier: MIT
"""
High-Performance WebSocket Optimization Package
Provides optimized WebSocket components for 1000+ concurrent users with <100ms latency
"""

from .websocket_optimizer import (
    HighPerformanceWebSocketManager,
    OptimizedWebSocketConnection,
    PerformanceMetrics
)
from .connection_pool import (
    WebSocketConnectionPool,
    ConnectionGroup,
    LoadBalanceStrategy,
    RoundRobinStrategy,
    LeastConnectionsStrategy,
    WeightedRoundRobinStrategy
)
from .message_queue import (
    HighPerformanceMessageQueue,
    MessagePriority,
    MessageStatus,
    QueueMessage,
    MessageProcessor,
    DefaultMessageProcessor
)

__all__ = [
    # WebSocket Optimizer
    'HighPerformanceWebSocketManager',
    'OptimizedWebSocketConnection',
    'PerformanceMetrics',
    
    # Connection Pool
    'WebSocketConnectionPool',
    'ConnectionGroup',
    'LoadBalanceStrategy',
    'RoundRobinStrategy',
    'LeastConnectionsStrategy',
    'WeightedRoundRobinStrategy',
    
    # Message Queue
    'HighPerformanceMessageQueue',
    'MessagePriority',
    'MessageStatus',
    'QueueMessage',
    'MessageProcessor',
    'DefaultMessageProcessor'
]

__version__ = "2.0.0"
__author__ = "OpenCode Performance Team"
__description__ = "High-performance WebSocket optimization for enterprise-scale applications"