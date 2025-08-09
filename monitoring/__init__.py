"""
Monitoring Package for OpenCode-Slack
Provides performance monitoring and metrics collection
"""

from .websocket_metrics import (
    WebSocketMetricsCollector,
    ConnectionMetrics,
    ServerMetrics,
    PerformanceAlert,
    MetricsAggregator,
    AlertManager
)

__all__ = [
    'WebSocketMetricsCollector',
    'ConnectionMetrics', 
    'ServerMetrics',
    'PerformanceAlert',
    'MetricsAggregator',
    'AlertManager'
]

__version__ = "1.0.0"