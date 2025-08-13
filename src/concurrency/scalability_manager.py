# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
Scalability Manager for OpenCode-Slack System
Implements horizontal scaling preparation, load balancing, and capacity planning.
"""

from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import Queue, PriorityQueue
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
import asyncio
import json
import logging
import multiprocessing as mp
import os
import psutil
import socket
import threading
import time
import uuid

logger = logging.getLogger(__name__)


@dataclass
class NodeInfo:
    """Information about a processing node"""
    node_id: str
    host: str
    port: int
    cpu_cores: int
    memory_gb: float
    max_agents: int
    current_load: float = 0.0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    status: str = "active"  # active, inactive, overloaded
    capabilities: List[str] = field(default_factory=list)


@dataclass
class LoadMetrics:
    """Load metrics for capacity planning"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_agents: int = 0
    queued_tasks: int = 0
    throughput: float = 0.0
    response_time: float = 0.0
    error_rate: float = 0.0


class LoadBalancer:
    """Intelligent load balancer for distributing work across nodes"""

    def __init__(self):
        self.nodes: Dict[str, NodeInfo] = {}
        self.load_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.lock = threading.RLock()

        # Load balancing strategies
        self.strategies = {
            'round_robin': self._round_robin_strategy,
            'least_loaded': self._least_loaded_strategy,
            'weighted_round_robin': self._weighted_round_robin_strategy,
            'capability_based': self._capability_based_strategy
        }
        self.current_strategy = 'least_loaded'
        self.round_robin_index = 0

        logger.info("LoadBalancer initialized")

    def register_node(self, node_info: NodeInfo):
        """Register a new processing node"""
        with self.lock:
            self.nodes[node_info.node_id] = node_info
            logger.info(f"Registered node {node_info.node_id} at {node_info.host}:{node_info.port}")

    def unregister_node(self, node_id: str):
        """Unregister a processing node"""
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                if node_id in self.load_history:
                    del self.load_history[node_id]
                logger.info(f"Unregistered node {node_id}")

    def update_node_load(self, node_id: str, load_metrics: LoadMetrics):
        """Update load metrics for a node"""
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id].current_load = load_metrics.cpu_usage
                self.nodes[node_id].last_heartbeat = datetime.now()
                self.load_history[node_id].append(load_metrics)

    def select_node(self, task_requirements: Dict[str, Any] = None) -> Optional[NodeInfo]:
        """Select the best node for a task"""
        with self.lock:
            active_nodes = [
                node for node in self.nodes.values()
                if node.status == "active" and
                datetime.now() - node.last_heartbeat < timedelta(minutes=2)
            ]

            if not active_nodes:
                return None

            strategy_func = self.strategies.get(self.current_strategy, self._least_loaded_strategy)
            return strategy_func(active_nodes, task_requirements)

    def _round_robin_strategy(self, nodes: List[NodeInfo], requirements: Dict[str, Any] = None) -> NodeInfo:
        """Round-robin load balancing"""
        if not nodes:
            return None

        self.round_robin_index = (self.round_robin_index + 1) % len(nodes)
        return nodes[self.round_robin_index]

    def _least_loaded_strategy(self, nodes: List[NodeInfo], requirements: Dict[str, Any] = None) -> NodeInfo:
        """Select node with lowest current load"""
        return min(nodes, key=lambda n: n.current_load)

    def _weighted_round_robin_strategy(self, nodes: List[NodeInfo], requirements: Dict[str, Any] = None) -> NodeInfo:
        """Weighted round-robin based on node capacity"""
        # Weight by inverse of current load and node capacity
        weights = []
        for node in nodes:
            capacity_weight = node.max_agents / max(node.current_load + 0.1, 0.1)
            weights.append(capacity_weight)

        # Select based on weights
        total_weight = sum(weights)
        if total_weight == 0:
            return nodes[0]

        import random
        r = random.uniform(0, total_weight)
        cumulative = 0
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return nodes[i]

        return nodes[-1]

    def _capability_based_strategy(self, nodes: List[NodeInfo], requirements: Dict[str, Any] = None) -> NodeInfo:
        """Select node based on required capabilities"""
        if not requirements or 'capabilities' not in requirements:
            return self._least_loaded_strategy(nodes, requirements)

        required_caps = set(requirements['capabilities'])

        # Filter nodes that have required capabilities
        capable_nodes = [
            node for node in nodes
            if required_caps.issubset(set(node.capabilities))
        ]

        if not capable_nodes:
            # Fallback to any available node
            capable_nodes = nodes

        return self._least_loaded_strategy(capable_nodes, requirements)

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status"""
        with self.lock:
            active_nodes = [n for n in self.nodes.values() if n.status == "active"]
            total_capacity = sum(n.max_agents for n in active_nodes)
            current_load = sum(n.current_load * n.max_agents for n in active_nodes)

            return {
                'total_nodes': len(self.nodes),
                'active_nodes': len(active_nodes),
                'total_capacity': total_capacity,
                'current_utilization': current_load / max(total_capacity, 1),
                'strategy': self.current_strategy,
                'nodes': {
                    node.node_id: {
                        'host': node.host,
                        'port': node.port,
                        'load': node.current_load,
                        'capacity': node.max_agents,
                        'status': node.status,
                        'last_heartbeat': node.last_heartbeat.isoformat()
                    }
                    for node in self.nodes.values()
                }
            }


class AutoScaler:
    """Automatic scaling based on load metrics"""

    def __init__(self, min_nodes: int = 1, max_nodes: int = 10):
        self.min_nodes = min_nodes
        self.max_nodes = max_nodes
        self.load_balancer = LoadBalancer()

        # Scaling thresholds
        self.scale_up_threshold = 0.8  # 80% utilization
        self.scale_down_threshold = 0.3  # 30% utilization
        self.scale_up_cooldown = 300  # 5 minutes
        self.scale_down_cooldown = 600  # 10 minutes

        # Scaling history
        self.last_scale_up = datetime.min
        self.last_scale_down = datetime.min
        self.scaling_events = deque(maxlen=100)

        # Monitoring
        self.metrics_history = deque(maxlen=1000)
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info(f"AutoScaler initialized: {min_nodes}-{max_nodes} nodes")

    def _monitor_loop(self):
        """Monitor cluster load and trigger scaling decisions"""
        while True:
            try:
                time.sleep(30)  # Check every 30 seconds

                cluster_status = self.load_balancer.get_cluster_status()
                current_utilization = cluster_status['current_utilization']
                active_nodes = cluster_status['active_nodes']

                # Record metrics
                metrics = LoadMetrics(
                    cpu_usage=current_utilization * 100,
                    active_agents=cluster_status['total_capacity']
                )
                self.metrics_history.append(metrics)

                # Make scaling decisions
                now = datetime.now()

                # Scale up decision
                if (current_utilization > self.scale_up_threshold and
                    active_nodes < self.max_nodes and
                    now - self.last_scale_up > timedelta(seconds=self.scale_up_cooldown)):

                    self._trigger_scale_up()

                # Scale down decision
                elif (current_utilization < self.scale_down_threshold and
                      active_nodes > self.min_nodes and
                      now - self.last_scale_down > timedelta(seconds=self.scale_down_cooldown)):

                    self._trigger_scale_down()

            except Exception as e:
                logger.error(f"Error in autoscaler monitor loop: {e}")

    def _trigger_scale_up(self):
        """Trigger scale-up operation"""
        try:
            logger.info("Triggering scale-up operation")

            # In a real implementation, this would:
            # 1. Launch new compute instances
            # 2. Deploy application to new instances
            # 3. Register new nodes with load balancer

            # For simulation, we'll create a virtual node
            new_node = NodeInfo(
                node_id=f"node_{uuid.uuid4().hex[:8]}",
                host=f"10.0.0.{len(self.load_balancer.nodes) + 10}",
                port=8000,
                cpu_cores=4,
                memory_gb=8.0,
                max_agents=20,
                capabilities=['general', 'development']
            )

            self.load_balancer.register_node(new_node)
            self.last_scale_up = datetime.now()

            self.scaling_events.append({
                'timestamp': datetime.now(),
                'action': 'scale_up',
                'node_id': new_node.node_id,
                'reason': 'High utilization'
            })

            logger.info(f"Scaled up: added node {new_node.node_id}")

        except Exception as e:
            logger.error(f"Error during scale-up: {e}")

    def _trigger_scale_down(self):
        """Trigger scale-down operation"""
        try:
            logger.info("Triggering scale-down operation")

            # Find least loaded node to remove
            cluster_status = self.load_balancer.get_cluster_status()
            if len(cluster_status['nodes']) <= self.min_nodes:
                return

            # Select node with lowest load
            least_loaded_node = min(
                self.load_balancer.nodes.values(),
                key=lambda n: n.current_load
            )

            # In a real implementation, this would:
            # 1. Drain tasks from the node
            # 2. Gracefully shutdown the node
            # 3. Terminate the compute instance

            self.load_balancer.unregister_node(least_loaded_node.node_id)
            self.last_scale_down = datetime.now()

            self.scaling_events.append({
                'timestamp': datetime.now(),
                'action': 'scale_down',
                'node_id': least_loaded_node.node_id,
                'reason': 'Low utilization'
            })

            logger.info(f"Scaled down: removed node {least_loaded_node.node_id}")

        except Exception as e:
            logger.error(f"Error during scale-down: {e}")

    def get_scaling_history(self) -> List[Dict[str, Any]]:
        """Get scaling event history"""
        return list(self.scaling_events)

    def set_scaling_thresholds(self, scale_up: float, scale_down: float):
        """Update scaling thresholds"""
        self.scale_up_threshold = scale_up
        self.scale_down_threshold = scale_down
        logger.info(f"Updated scaling thresholds: up={scale_up}, down={scale_down}")


class CapacityPlanner:
    """Capacity planning and forecasting"""

    def __init__(self):
        self.load_history = deque(maxlen=10000)  # Store more history for analysis
        self.capacity_recommendations = []

        # Forecasting parameters
        self.forecast_horizon_hours = 24
        self.trend_window_hours = 6

        logger.info("CapacityPlanner initialized")

    def record_load_metrics(self, metrics: LoadMetrics):
        """Record load metrics for analysis"""
        self.load_history.append(metrics)

    def analyze_trends(self) -> Dict[str, Any]:
        """Analyze load trends and patterns"""
        if len(self.load_history) < 100:
            return {'status': 'insufficient_data'}

        recent_metrics = list(self.load_history)[-100:]

        # Calculate trends
        cpu_trend = self._calculate_trend([m.cpu_usage for m in recent_metrics])
        memory_trend = self._calculate_trend([m.memory_usage for m in recent_metrics])
        throughput_trend = self._calculate_trend([m.throughput for m in recent_metrics])

        # Identify patterns
        patterns = self._identify_patterns(recent_metrics)

        return {
            'trends': {
                'cpu': cpu_trend,
                'memory': memory_trend,
                'throughput': throughput_trend
            },
            'patterns': patterns,
            'analysis_timestamp': datetime.now().isoformat()
        }

    def _calculate_trend(self, values: List[float]) -> Dict[str, float]:
        """Calculate trend for a series of values"""
        if len(values) < 2:
            return {'slope': 0.0, 'direction': 'stable'}

        # Simple linear regression
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))

        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)

        direction = 'increasing' if slope > 0.1 else 'decreasing' if slope < -0.1 else 'stable'

        return {
            'slope': slope,
            'direction': direction,
            'confidence': min(abs(slope) * 10, 1.0)  # Simple confidence metric
        }

    def _identify_patterns(self, metrics: List[LoadMetrics]) -> Dict[str, Any]:
        """Identify patterns in load metrics"""
        patterns = {
            'peak_hours': [],
            'low_hours': [],
            'cyclical': False,
            'volatility': 'low'
        }

        # Group by hour of day
        hourly_loads = defaultdict(list)
        for metric in metrics:
            hour = metric.timestamp.hour
            hourly_loads[hour].append(metric.cpu_usage)

        # Find peak and low hours
        hourly_averages = {
            hour: sum(loads) / len(loads)
            for hour, loads in hourly_loads.items()
        }

        if hourly_averages:
            avg_load = sum(hourly_averages.values()) / len(hourly_averages)

            patterns['peak_hours'] = [
                hour for hour, load in hourly_averages.items()
                if load > avg_load * 1.2
            ]

            patterns['low_hours'] = [
                hour for hour, load in hourly_averages.items()
                if load < avg_load * 0.8
            ]

            # Check for cyclical patterns
            load_variance = sum(
                (load - avg_load) ** 2 for load in hourly_averages.values()
            ) / len(hourly_averages)

            patterns['cyclical'] = load_variance > avg_load * 0.1

            # Determine volatility
            if load_variance > avg_load * 0.5:
                patterns['volatility'] = 'high'
            elif load_variance > avg_load * 0.2:
                patterns['volatility'] = 'medium'
            else:
                patterns['volatility'] = 'low'

        return patterns

    def forecast_capacity_needs(self) -> Dict[str, Any]:
        """Forecast future capacity needs"""
        if len(self.load_history) < 200:
            return {'status': 'insufficient_data_for_forecast'}

        trends = self.analyze_trends()
        recent_metrics = list(self.load_history)[-200:]

        # Current capacity metrics
        current_avg_cpu = sum(m.cpu_usage for m in recent_metrics[-50:]) / 50
        current_avg_memory = sum(m.memory_usage for m in recent_metrics[-50:]) / 50
        current_avg_throughput = sum(m.throughput for m in recent_metrics[-50:]) / 50

        # Project future needs based on trends
        cpu_trend_slope = trends['trends']['cpu']['slope']
        memory_trend_slope = trends['trends']['memory']['slope']
        throughput_trend_slope = trends['trends']['throughput']['slope']

        # Forecast for next 24 hours (assuming hourly data points)
        forecast_hours = 24

        projected_cpu = current_avg_cpu + (cpu_trend_slope * forecast_hours)
        projected_memory = current_avg_memory + (memory_trend_slope * forecast_hours)
        projected_throughput = current_avg_throughput + (throughput_trend_slope * forecast_hours)

        # Calculate recommended capacity
        recommendations = self._generate_capacity_recommendations(
            projected_cpu, projected_memory, projected_throughput, trends['patterns']
        )

        return {
            'forecast_horizon_hours': forecast_hours,
            'current_metrics': {
                'cpu': current_avg_cpu,
                'memory': current_avg_memory,
                'throughput': current_avg_throughput
            },
            'projected_metrics': {
                'cpu': max(0, projected_cpu),
                'memory': max(0, projected_memory),
                'throughput': max(0, projected_throughput)
            },
            'recommendations': recommendations,
            'confidence': self._calculate_forecast_confidence(trends),
            'forecast_timestamp': datetime.now().isoformat()
        }

    def _generate_capacity_recommendations(self, cpu: float, memory: float,
                                         throughput: float, patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate capacity recommendations"""
        recommendations = []

        # CPU recommendations
        if cpu > 80:
            recommendations.append({
                'type': 'scale_up',
                'resource': 'cpu',
                'urgency': 'high' if cpu > 90 else 'medium',
                'description': f'CPU utilization projected to reach {cpu:.1f}%'
            })
        elif cpu < 30:
            recommendations.append({
                'type': 'scale_down',
                'resource': 'cpu',
                'urgency': 'low',
                'description': f'CPU utilization projected to be {cpu:.1f}% - consider scaling down'
            })

        # Memory recommendations
        if memory > 85:
            recommendations.append({
                'type': 'scale_up',
                'resource': 'memory',
                'urgency': 'high' if memory > 95 else 'medium',
                'description': f'Memory utilization projected to reach {memory:.1f}%'
            })

        # Throughput recommendations
        if throughput > 1000:  # Assuming 1000 is a high throughput threshold
            recommendations.append({
                'type': 'optimize',
                'resource': 'throughput',
                'urgency': 'medium',
                'description': f'High throughput projected ({throughput:.1f}) - consider optimization'
            })

        # Pattern-based recommendations
        if patterns.get('volatility') == 'high':
            recommendations.append({
                'type': 'optimize',
                'resource': 'stability',
                'urgency': 'medium',
                'description': 'High load volatility detected - consider auto-scaling tuning'
            })

        if patterns.get('cyclical'):
            recommendations.append({
                'type': 'schedule',
                'resource': 'capacity',
                'urgency': 'low',
                'description': f'Cyclical patterns detected - peak hours: {patterns.get("peak_hours", [])}'
            })

        return recommendations

    def _calculate_forecast_confidence(self, trends: Dict[str, Any]) -> float:
        """Calculate confidence in forecast"""
        # Simple confidence calculation based on trend stability
        cpu_confidence = trends['trends']['cpu'].get('confidence', 0)
        memory_confidence = trends['trends']['memory'].get('confidence', 0)
        throughput_confidence = trends['trends']['throughput'].get('confidence', 0)

        # Average confidence with data quality factor
        data_quality = min(len(self.load_history) / 1000, 1.0)

        return (cpu_confidence + memory_confidence + throughput_confidence) / 3 * data_quality


class ScalabilityManager:
    """Main scalability manager coordinating all scaling components"""

    def __init__(self, min_nodes: int = 1, max_nodes: int = 20):
        self.min_nodes = min_nodes
        self.max_nodes = max_nodes

        # Core components
        self.load_balancer = LoadBalancer()
        self.auto_scaler = AutoScaler(min_nodes, max_nodes)
        self.capacity_planner = CapacityPlanner()

        # Configuration
        self.scaling_enabled = True
        self.monitoring_interval = 30  # seconds

        # Initialize local node
        self._register_local_node()

        # Start monitoring
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

        logger.info(f"ScalabilityManager initialized: {min_nodes}-{max_nodes} nodes")

    def _register_local_node(self):
        """Register the local node"""
        local_node = NodeInfo(
            node_id=f"local_{socket.gethostname()}",
            host="localhost",
            port=8000,
            cpu_cores=psutil.cpu_count(),
            memory_gb=psutil.virtual_memory().total / (1024**3),
            max_agents=50,  # Default capacity
            capabilities=['general', 'development', 'testing']
        )

        self.load_balancer.register_node(local_node)
        logger.info(f"Registered local node: {local_node.node_id}")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_info = psutil.virtual_memory()

                # Create load metrics
                metrics = LoadMetrics(
                    cpu_usage=cpu_percent,
                    memory_usage=memory_info.percent,
                    active_agents=0,  # Would be populated from actual agent manager
                    queued_tasks=0,   # Would be populated from task queue
                    throughput=0.0,   # Would be calculated from actual throughput
                    response_time=0.0 # Would be measured from actual responses
                )

                # Update components
                self.capacity_planner.record_load_metrics(metrics)

                # Update local node load
                local_node_id = f"local_{socket.gethostname()}"
                self.load_balancer.update_node_load(local_node_id, metrics)

                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in scalability monitoring loop: {e}")
                time.sleep(self.monitoring_interval)

    def select_node_for_task(self, task_requirements: Dict[str, Any] = None) -> Optional[str]:
        """Select the best node for a task"""
        node = self.load_balancer.select_node(task_requirements)
        return node.node_id if node else None

    def get_scaling_recommendations(self) -> Dict[str, Any]:
        """Get current scaling recommendations"""
        capacity_forecast = self.capacity_planner.forecast_capacity_needs()
        cluster_status = self.load_balancer.get_cluster_status()
        scaling_history = self.auto_scaler.get_scaling_history()

        return {
            'cluster_status': cluster_status,
            'capacity_forecast': capacity_forecast,
            'scaling_history': scaling_history[-10:],  # Last 10 events
            'scaling_enabled': self.scaling_enabled,
            'recommendations_timestamp': datetime.now().isoformat()
        }

    def enable_auto_scaling(self):
        """Enable automatic scaling"""
        self.scaling_enabled = True
        logger.info("Auto-scaling enabled")

    def disable_auto_scaling(self):
        """Disable automatic scaling"""
        self.scaling_enabled = False
        logger.info("Auto-scaling disabled")

    def manual_scale_up(self, count: int = 1):
        """Manually trigger scale-up"""
        for _ in range(count):
            self.auto_scaler._trigger_scale_up()
        logger.info(f"Manual scale-up triggered: {count} nodes")

    def manual_scale_down(self, count: int = 1):
        """Manually trigger scale-down"""
        for _ in range(count):
            self.auto_scaler._trigger_scale_down()
        logger.info(f"Manual scale-down triggered: {count} nodes")

    def update_scaling_thresholds(self, scale_up: float, scale_down: float):
        """Update auto-scaling thresholds"""
        self.auto_scaler.set_scaling_thresholds(scale_up, scale_down)

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive scalability status"""
        return {
            'scalability_manager': {
                'min_nodes': self.min_nodes,
                'max_nodes': self.max_nodes,
                'scaling_enabled': self.scaling_enabled,
                'monitoring_interval': self.monitoring_interval
            },
            'load_balancer': self.load_balancer.get_cluster_status(),
            'capacity_planning': self.capacity_planner.forecast_capacity_needs(),
            'scaling_history': self.auto_scaler.get_scaling_history()[-5:],
            'system_metrics': {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_connections': len(psutil.net_connections())
            },
            'timestamp': datetime.now().isoformat()
        }