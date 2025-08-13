# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
Agent Discovery Optimizer
Implements efficient agent discovery, routing, and load balancing mechanisms.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
import hashlib
import json
import logging
import threading
import time

logger = logging.getLogger(__name__)

class AgentCapability:
    """Represents an agent's capabilities and current state"""

    def __init__(self, agent_name: str, role: str, expertise: List[str]):
        self.agent_name = agent_name
        self.role = role
        self.expertise = set(expertise)
        self.current_load = 0
        self.max_load = 5  # Maximum concurrent tasks
        self.performance_score = 1.0
        self.last_activity = datetime.now()
        self.status = "idle"  # idle, working, stuck, offline
        self.response_times = deque(maxlen=10)
        self.success_rate = 1.0
        self.task_history = deque(maxlen=50)

    def can_handle_task(self, task_type: str, required_expertise: Set[str]) -> bool:
        """Check if agent can handle a specific task"""
        if self.status == "offline":
            return False

        if self.current_load >= self.max_load:
            return False

        # Check expertise overlap
        if required_expertise and not required_expertise.intersection(self.expertise):
            return False

        return True

    def calculate_suitability_score(self, task_type: str, required_expertise: Set[str]) -> float:
        """Calculate how suitable this agent is for a task"""
        if not self.can_handle_task(task_type, required_expertise):
            return 0.0

        # Base score from performance
        score = self.performance_score * self.success_rate

        # Expertise match bonus
        if required_expertise:
            expertise_match = len(required_expertise.intersection(self.expertise)) / len(required_expertise)
            score *= (1.0 + expertise_match)

        # Load penalty
        load_factor = 1.0 - (self.current_load / self.max_load)
        score *= load_factor

        # Recent activity bonus
        time_since_activity = (datetime.now() - self.last_activity).total_seconds()
        if time_since_activity < 300:  # 5 minutes
            score *= 1.2
        elif time_since_activity > 3600:  # 1 hour
            score *= 0.8

        return score

    def update_performance(self, response_time: float, success: bool):
        """Update agent performance metrics"""
        self.response_times.append(response_time)
        self.last_activity = datetime.now()

        # Update success rate (exponential moving average)
        self.success_rate = 0.9 * self.success_rate + 0.1 * (1.0 if success else 0.0)

        # Update performance score based on response time
        avg_response_time = sum(self.response_times) / len(self.response_times)
        if avg_response_time < 1.0:
            self.performance_score = min(2.0, self.performance_score * 1.05)
        elif avg_response_time > 5.0:
            self.performance_score = max(0.1, self.performance_score * 0.95)

    def assign_task(self, task_id: str, task_type: str):
        """Assign task to agent"""
        self.current_load += 1
        self.status = "working"
        self.task_history.append({
            'task_id': task_id,
            'task_type': task_type,
            'assigned_at': datetime.now()
        })

    def complete_task(self, task_id: str, success: bool, response_time: float):
        """Mark task as completed"""
        self.current_load = max(0, self.current_load - 1)
        if self.current_load == 0:
            self.status = "idle"

        self.update_performance(response_time, success)

        # Update task history
        for task in self.task_history:
            if task.get('task_id') == task_id:
                task['completed_at'] = datetime.now()
                task['success'] = success
                task['response_time'] = response_time
                break

class TaskRouter:
    """Routes tasks to optimal agents"""

    def __init__(self):
        self.routing_strategies = {
            'round_robin': self._round_robin_strategy,
            'least_loaded': self._least_loaded_strategy,
            'best_fit': self._best_fit_strategy,
            'performance_based': self._performance_based_strategy
        }
        self.default_strategy = 'performance_based'
        self.strategy_counters = defaultdict(int)

    def route_task(self, task_type: str, required_expertise: Set[str],
                   available_agents: List[AgentCapability],
                   strategy: Optional[str] = None) -> Optional[AgentCapability]:
        """Route task to best available agent"""
        if not available_agents:
            return None

        # Filter agents that can handle the task
        capable_agents = [
            agent for agent in available_agents
            if agent.can_handle_task(task_type, required_expertise)
        ]

        if not capable_agents:
            return None

        # Use specified strategy or default
        strategy = strategy or self.default_strategy
        routing_func = self.routing_strategies.get(strategy, self._performance_based_strategy)

        selected_agent = routing_func(task_type, required_expertise, capable_agents)

        if selected_agent:
            self.strategy_counters[strategy] += 1

        return selected_agent

    def _round_robin_strategy(self, task_type: str, required_expertise: Set[str],
                             agents: List[AgentCapability]) -> Optional[AgentCapability]:
        """Round-robin selection"""
        if not agents:
            return None

        # Simple round-robin based on counter
        index = self.strategy_counters['round_robin'] % len(agents)
        return agents[index]

    def _least_loaded_strategy(self, task_type: str, required_expertise: Set[str],
                              agents: List[AgentCapability]) -> Optional[AgentCapability]:
        """Select agent with least current load"""
        return min(agents, key=lambda a: a.current_load)

    def _best_fit_strategy(self, task_type: str, required_expertise: Set[str],
                          agents: List[AgentCapability]) -> Optional[AgentCapability]:
        """Select agent with best expertise match"""
        if not required_expertise:
            return self._least_loaded_strategy(task_type, required_expertise, agents)

        best_agent = None
        best_match_score = 0

        for agent in agents:
            match_score = len(required_expertise.intersection(agent.expertise))
            if match_score > best_match_score:
                best_match_score = match_score
                best_agent = agent
            elif match_score == best_match_score and best_agent:
                # Tie-breaker: use load
                if agent.current_load < best_agent.current_load:
                    best_agent = agent

        return best_agent or agents[0]

    def _performance_based_strategy(self, task_type: str, required_expertise: Set[str],
                                   agents: List[AgentCapability]) -> Optional[AgentCapability]:
        """Select agent based on suitability score"""
        best_agent = None
        best_score = 0

        for agent in agents:
            score = agent.calculate_suitability_score(task_type, required_expertise)
            if score > best_score:
                best_score = score
                best_agent = agent

        return best_agent

class AgentLoadBalancer:
    """Balances load across agents"""

    def __init__(self, rebalance_interval: int = 60):
        self.rebalance_interval = rebalance_interval
        self.load_history = defaultdict(lambda: deque(maxlen=60))  # 1 hour of history
        self.rebalance_thread = None
        self.running = False
        self.lock = threading.RLock()

    def start_rebalancing(self, agent_discovery):
        """Start automatic load rebalancing"""
        if self.running:
            return

        self.running = True
        self.rebalance_thread = threading.Thread(
            target=self._rebalance_loop,
            args=(agent_discovery,),
            daemon=True
        )
        self.rebalance_thread.start()
        logger.info("Started agent load balancing")

    def stop_rebalancing(self):
        """Stop automatic load rebalancing"""
        self.running = False
        if self.rebalance_thread:
            self.rebalance_thread.join(timeout=5)
        logger.info("Stopped agent load balancing")

    def _rebalance_loop(self, agent_discovery):
        """Main rebalancing loop"""
        while self.running:
            try:
                self._perform_rebalancing(agent_discovery)
                time.sleep(self.rebalance_interval)
            except Exception as e:
                logger.error(f"Error in rebalancing loop: {e}")
                time.sleep(self.rebalance_interval)

    def _perform_rebalancing(self, agent_discovery):
        """Perform load rebalancing"""
        with self.lock:
            agents = agent_discovery.get_all_agents()
            if len(agents) < 2:
                return

            # Calculate load statistics
            loads = [agent.current_load for agent in agents.values()]
            avg_load = sum(loads) / len(loads)
            max_load = max(loads)
            min_load = min(loads)

            # Check if rebalancing is needed
            load_variance = max_load - min_load
            if load_variance <= 1:  # Loads are already balanced
                return

            # Find overloaded and underloaded agents
            overloaded = [a for a in agents.values() if a.current_load > avg_load + 1]
            underloaded = [a for a in agents.values() if a.current_load < avg_load - 1]

            if not overloaded or not underloaded:
                return

            # Log rebalancing action
            logger.info(f"Rebalancing load: avg={avg_load:.1f}, variance={load_variance}")

            # Update agent max loads based on performance
            self._adjust_agent_capacities(agents.values())

    def _adjust_agent_capacities(self, agents):
        """Adjust agent capacities based on performance"""
        for agent in agents:
            # Increase capacity for high-performing agents
            if agent.performance_score > 1.5 and agent.success_rate > 0.95:
                agent.max_load = min(10, agent.max_load + 1)
            # Decrease capacity for low-performing agents
            elif agent.performance_score < 0.5 or agent.success_rate < 0.8:
                agent.max_load = max(1, agent.max_load - 1)

    def record_load_metrics(self, agents: Dict[str, AgentCapability]):
        """Record load metrics for analysis"""
        with self.lock:
            timestamp = datetime.now()
            for agent_name, agent in agents.items():
                self.load_history[agent_name].append({
                    'timestamp': timestamp,
                    'load': agent.current_load,
                    'max_load': agent.max_load,
                    'performance': agent.performance_score
                })

class AgentDiscoveryOptimizer:
    """Optimized agent discovery and routing system"""

    def __init__(self):
        self.agents: Dict[str, AgentCapability] = {}
        self.task_router = TaskRouter()
        self.load_balancer = AgentLoadBalancer()
        self.lock = threading.RLock()

        # Performance monitoring
        self.metrics = {
            'total_tasks_routed': 0,
            'successful_routes': 0,
            'failed_routes': 0,
            'average_routing_time': 0.0,
            'agent_utilization': {},
            'routing_strategy_usage': defaultdict(int)
        }

        # Task queue for high-throughput scenarios
        self.pending_tasks = deque()
        self.task_processing_thread = None
        self.processing_tasks = False

        logger.info("Agent Discovery Optimizer initialized")

    def start(self):
        """Start the optimizer"""
        self.processing_tasks = True
        self.task_processing_thread = threading.Thread(
            target=self._task_processing_loop,
            daemon=True
        )
        self.task_processing_thread.start()

        self.load_balancer.start_rebalancing(self)
        logger.info("Agent Discovery Optimizer started")

    def stop(self):
        """Stop the optimizer"""
        self.processing_tasks = False
        if self.task_processing_thread:
            self.task_processing_thread.join(timeout=5)

        self.load_balancer.stop_rebalancing()
        logger.info("Agent Discovery Optimizer stopped")

    def register_agent(self, agent_name: str, role: str, expertise: List[str]):
        """Register a new agent"""
        with self.lock:
            if agent_name in self.agents:
                # Update existing agent
                agent = self.agents[agent_name]
                agent.role = role
                agent.expertise = set(expertise)
                agent.status = "idle"
            else:
                # Create new agent
                agent = AgentCapability(agent_name, role, expertise)
                self.agents[agent_name] = agent

            logger.info(f"Registered agent: {agent_name} ({role}) with expertise: {expertise}")

    def unregister_agent(self, agent_name: str):
        """Unregister an agent"""
        with self.lock:
            if agent_name in self.agents:
                del self.agents[agent_name]
                logger.info(f"Unregistered agent: {agent_name}")

    def update_agent_status(self, agent_name: str, status: str, current_load: Optional[int] = None):
        """Update agent status"""
        with self.lock:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                agent.status = status
                agent.last_activity = datetime.now()

                if current_load is not None:
                    agent.current_load = current_load

                logger.debug(f"Updated agent {agent_name} status: {status}")

    def find_best_agent(self, task_type: str, required_expertise: List[str] = None,
                       strategy: Optional[str] = None) -> Optional[str]:
        """Find the best agent for a task"""
        start_time = time.time()

        with self.lock:
            if not self.agents:
                return None

            required_expertise_set = set(required_expertise) if required_expertise else set()
            available_agents = list(self.agents.values())

            # Route task to best agent
            selected_agent = self.task_router.route_task(
                task_type, required_expertise_set, available_agents, strategy
            )

            # Update metrics
            routing_time = time.time() - start_time
            self.metrics['total_tasks_routed'] += 1

            if selected_agent:
                self.metrics['successful_routes'] += 1
                agent_name = selected_agent.agent_name

                # Update average routing time
                total_routes = self.metrics['total_tasks_routed']
                current_avg = self.metrics['average_routing_time']
                self.metrics['average_routing_time'] = (
                    (current_avg * (total_routes - 1) + routing_time) / total_routes
                )

                logger.debug(f"Routed task '{task_type}' to agent '{agent_name}' in {routing_time:.3f}s")
                return agent_name
            else:
                self.metrics['failed_routes'] += 1
                logger.warning(f"No suitable agent found for task '{task_type}' with expertise {required_expertise}")
                return None

    def assign_task(self, agent_name: str, task_id: str, task_type: str) -> bool:
        """Assign task to specific agent"""
        with self.lock:
            if agent_name not in self.agents:
                return False

            agent = self.agents[agent_name]
            if not agent.can_handle_task(task_type, set()):
                return False

            agent.assign_task(task_id, task_type)
            logger.info(f"Assigned task '{task_id}' to agent '{agent_name}'")
            return True

    def complete_task(self, agent_name: str, task_id: str, success: bool, response_time: float):
        """Mark task as completed"""
        with self.lock:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                agent.complete_task(task_id, success, response_time)
                logger.info(f"Completed task '{task_id}' for agent '{agent_name}' (success: {success})")

    def queue_task(self, task_type: str, required_expertise: List[str] = None,
                   priority: int = 1, metadata: Dict[str, Any] = None):
        """Queue task for processing"""
        task = {
            'id': f"task_{int(time.time() * 1000)}",
            'type': task_type,
            'expertise': required_expertise or [],
            'priority': priority,
            'metadata': metadata or {},
            'queued_at': datetime.now()
        }

        # Insert based on priority
        inserted = False
        for i, existing_task in enumerate(self.pending_tasks):
            if task['priority'] > existing_task['priority']:
                self.pending_tasks.insert(i, task)
                inserted = True
                break

        if not inserted:
            self.pending_tasks.append(task)

        logger.debug(f"Queued task '{task['id']}' with priority {priority}")

    def _task_processing_loop(self):
        """Process queued tasks"""
        while self.processing_tasks:
            try:
                if self.pending_tasks:
                    task = self.pending_tasks.popleft()

                    # Find agent for task
                    agent_name = self.find_best_agent(
                        task['type'],
                        task['expertise']
                    )

                    if agent_name:
                        # Assign task
                        self.assign_task(agent_name, task['id'], task['type'])
                    else:
                        # Re-queue task if no agent available
                        self.pending_tasks.appendleft(task)
                        time.sleep(1)  # Wait before retrying
                else:
                    time.sleep(0.1)  # Short sleep when no tasks

            except Exception as e:
                logger.error(f"Error in task processing loop: {e}")
                time.sleep(1)

    def get_all_agents(self) -> Dict[str, AgentCapability]:
        """Get all registered agents"""
        with self.lock:
            return self.agents.copy()

    def get_agent_status(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get status of specific agent"""
        with self.lock:
            if agent_name not in self.agents:
                return None

            agent = self.agents[agent_name]
            return {
                'name': agent.agent_name,
                'role': agent.role,
                'expertise': list(agent.expertise),
                'status': agent.status,
                'current_load': agent.current_load,
                'max_load': agent.max_load,
                'performance_score': agent.performance_score,
                'success_rate': agent.success_rate,
                'last_activity': agent.last_activity.isoformat(),
                'avg_response_time': (
                    sum(agent.response_times) / len(agent.response_times)
                    if agent.response_times else 0.0
                )
            }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        with self.lock:
            # Calculate agent utilization
            total_agents = len(self.agents)
            if total_agents > 0:
                total_load = sum(agent.current_load for agent in self.agents.values())
                total_capacity = sum(agent.max_load for agent in self.agents.values())
                utilization = total_load / total_capacity if total_capacity > 0 else 0.0
            else:
                utilization = 0.0

            # Agent status distribution
            status_counts = defaultdict(int)
            for agent in self.agents.values():
                status_counts[agent.status] += 1

            return {
                'total_agents': total_agents,
                'total_tasks_routed': self.metrics['total_tasks_routed'],
                'successful_routes': self.metrics['successful_routes'],
                'failed_routes': self.metrics['failed_routes'],
                'routing_success_rate': (
                    self.metrics['successful_routes'] / self.metrics['total_tasks_routed']
                    if self.metrics['total_tasks_routed'] > 0 else 1.0
                ),
                'average_routing_time_ms': self.metrics['average_routing_time'] * 1000,
                'system_utilization': utilization,
                'pending_tasks': len(self.pending_tasks),
                'agent_status_distribution': dict(status_counts),
                'routing_strategy_usage': dict(self.task_router.strategy_counters)
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the discovery system"""
        metrics = self.get_system_metrics()

        # Determine health
        health = "HEALTHY"
        issues = []

        if metrics['routing_success_rate'] < 0.9:
            health = "DEGRADED"
            issues.append(f"Low routing success rate: {metrics['routing_success_rate']:.2%}")

        if metrics['system_utilization'] > 0.9:
            health = "DEGRADED"
            issues.append(f"High system utilization: {metrics['system_utilization']:.1%}")

        if metrics['pending_tasks'] > 100:
            health = "DEGRADED"
            issues.append(f"High task queue: {metrics['pending_tasks']} pending")

        offline_agents = metrics['agent_status_distribution'].get('offline', 0)
        if offline_agents > 0:
            health = "DEGRADED"
            issues.append(f"{offline_agents} agents offline")

        if metrics['total_agents'] == 0:
            health = "UNHEALTHY"
            issues.append("No agents registered")

        return {
            'status': health,
            'issues': issues,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }