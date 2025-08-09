#!/usr/bin/env python3
"""
Enhanced Agent Coordinator for OpenCode-Slack System
Implements advanced concurrency optimizations, task dependency management,
and high-throughput agent coordination.
"""

from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue, PriorityQueue, Empty
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
import asyncio
import logging
import threading
import time
import uuid
import weakref

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels for scheduling"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class TaskDependency:
    """Represents a task dependency relationship"""
    task_id: str
    depends_on: str
    dependency_type: str = "completion"  # completion, resource, data
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class EnhancedTask:
    """Enhanced task with dependency and scheduling information"""
    task_id: str
    agent_name: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    required_resources: List[str] = field(default_factory=list)
    estimated_duration: Optional[int] = None  # seconds
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value < other.priority.value


class ResourcePool:
    """Thread-safe resource pool for managing shared resources"""

    def __init__(self, max_concurrent_agents: int = 50):
        self.max_concurrent_agents = max_concurrent_agents
        self.active_agents: Set[str] = set()
        self.resource_locks: Dict[str, str] = {}  # resource -> agent_name
        self.resource_queues: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)

    def acquire_agent_slot(self, agent_name: str) -> bool:
        """Acquire a slot for agent execution"""
        with self.condition:
            if len(self.active_agents) < self.max_concurrent_agents:
                self.active_agents.add(agent_name)
                self.condition.notify_all()
                return True
            return False

    def release_agent_slot(self, agent_name: str):
        """Release agent execution slot"""
        with self.condition:
            self.active_agents.discard(agent_name)
            self.condition.notify_all()

    def acquire_resources(self, agent_name: str, resources: List[str], timeout: float = 30.0) -> bool:
        """Acquire multiple resources atomically"""
        with self.condition:
            start_time = time.time()

            while time.time() - start_time < timeout:
                # Check if all resources are available
                available = all(
                    resource not in self.resource_locks
                    for resource in resources
                )

                if available:
                    # Acquire all resources atomically
                    for resource in resources:
                        self.resource_locks[resource] = agent_name
                    self.condition.notify_all()
                    return True

                # Wait for resources to become available
                self.condition.wait(timeout=1.0)

            return False

    def release_resources(self, agent_name: str, resources: List[str]):
        """Release multiple resources"""
        with self.condition:
            for resource in resources:
                if self.resource_locks.get(resource) == agent_name:
                    del self.resource_locks[resource]

                    # Notify waiting tasks
                    if resource in self.resource_queues:
                        while self.resource_queues[resource]:
                            waiting_task = self.resource_queues[resource].popleft()
                            # Notify the waiting task (implementation depends on task queue)
                            break

            self.condition.notify_all()

    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource utilization status"""
        with self.lock:
            return {
                'active_agents': len(self.active_agents),
                'max_agents': self.max_concurrent_agents,
                'utilization': len(self.active_agents) / self.max_concurrent_agents,
                'locked_resources': len(self.resource_locks),
                'resource_locks': dict(self.resource_locks)
            }


class DependencyGraph:
    """Manages task dependencies and resolves execution order"""

    def __init__(self):
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.dependents: Dict[str, Set[str]] = defaultdict(set)
        self.completed_tasks: Set[str] = set()
        self.lock = threading.RLock()

    def add_dependency(self, task_id: str, depends_on: str):
        """Add a dependency relationship"""
        with self.lock:
            if task_id != depends_on:  # Prevent self-dependency
                self.dependencies[task_id].add(depends_on)
                self.dependents[depends_on].add(task_id)

    def remove_dependency(self, task_id: str, depends_on: str):
        """Remove a dependency relationship"""
        with self.lock:
            self.dependencies[task_id].discard(depends_on)
            self.dependents[depends_on].discard(task_id)

    def mark_completed(self, task_id: str) -> List[str]:
        """Mark task as completed and return newly ready tasks"""
        with self.lock:
            self.completed_tasks.add(task_id)
            ready_tasks = []

            # Check all dependent tasks
            for dependent_task in self.dependents[task_id]:
                if self.is_ready(dependent_task):
                    ready_tasks.append(dependent_task)

            return ready_tasks

    def is_ready(self, task_id: str) -> bool:
        """Check if task is ready to execute (all dependencies completed)"""
        with self.lock:
            return all(
                dep in self.completed_tasks
                for dep in self.dependencies[task_id]
            )

    def get_ready_tasks(self, task_ids: List[str]) -> List[str]:
        """Get all tasks that are ready to execute"""
        with self.lock:
            return [task_id for task_id in task_ids if self.is_ready(task_id)]

    def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies"""
        with self.lock:
            visited = set()
            rec_stack = set()
            cycles = []

            def dfs(node, path):
                if node in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(node)
                    cycles.append(path[cycle_start:] + [node])
                    return

                if node in visited:
                    return

                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                for neighbor in self.dependencies[node]:
                    dfs(neighbor, path.copy())

                rec_stack.remove(node)

            for task_id in self.dependencies:
                if task_id not in visited:
                    dfs(task_id, [])

            return cycles


class AsyncLLMProcessor:
    """Asynchronous LLM request processor with batching and caching"""

    def __init__(self, max_concurrent_requests: int = 10, batch_size: int = 5):
        self.max_concurrent_requests = max_concurrent_requests
        self.batch_size = batch_size
        self.request_queue = asyncio.Queue()
        self.response_cache: Dict[str, Any] = {}
        self.cache_lock = threading.RLock()
        self.active_requests: Set[str] = set()
        self.request_semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.batch_processor_task = None

    async def start(self):
        """Start the async LLM processor"""
        self.batch_processor_task = asyncio.create_task(self._batch_processor())
        logger.info("AsyncLLMProcessor started")

    async def stop(self):
        """Stop the async LLM processor"""
        if self.batch_processor_task:
            self.batch_processor_task.cancel()
            try:
                await self.batch_processor_task
            except asyncio.CancelledError:
                pass
        logger.info("AsyncLLMProcessor stopped")

    async def process_request(self, request_id: str, prompt: str, model: str = None) -> Dict[str, Any]:
        """Process an LLM request asynchronously"""
        # Check cache first
        cache_key = f"{model}:{hash(prompt)}"
        with self.cache_lock:
            if cache_key in self.response_cache:
                logger.debug(f"Cache hit for request {request_id}")
                return self.response_cache[cache_key]

        # Create future for response
        response_future = asyncio.Future()

        # Add to queue
        await self.request_queue.put({
            'request_id': request_id,
            'prompt': prompt,
            'model': model,
            'cache_key': cache_key,
            'future': response_future,
            'timestamp': time.time()
        })

        # Wait for response
        return await response_future

    async def _batch_processor(self):
        """Process LLM requests in batches"""
        while True:
            try:
                batch = []

                # Collect batch
                try:
                    # Get first request (blocking)
                    first_request = await asyncio.wait_for(
                        self.request_queue.get(), timeout=1.0
                    )
                    batch.append(first_request)

                    # Collect additional requests for batch (non-blocking)
                    for _ in range(self.batch_size - 1):
                        try:
                            request = await asyncio.wait_for(
                                self.request_queue.get(), timeout=0.1
                            )
                            batch.append(request)
                        except asyncio.TimeoutError:
                            break

                except asyncio.TimeoutError:
                    continue  # No requests, continue waiting

                # Process batch
                if batch:
                    await self._process_batch(batch)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                await asyncio.sleep(1)

    async def _process_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of LLM requests"""
        async with self.request_semaphore:
            try:
                # Group by model for efficient processing
                model_groups = defaultdict(list)
                for request in batch:
                    model = request.get('model', 'default')
                    model_groups[model].append(request)

                # Process each model group
                for model, requests in model_groups.items():
                    await self._process_model_batch(model, requests)

            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                # Set error for all requests in batch
                for request in batch:
                    if not request['future'].done():
                        request['future'].set_exception(e)

    async def _process_model_batch(self, model: str, requests: List[Dict[str, Any]]):
        """Process requests for a specific model"""
        try:
            # Simulate LLM processing (replace with actual LLM calls)
            await asyncio.sleep(0.1)  # Simulated processing time

            for request in requests:
                # Simulate response
                response = {
                    'request_id': request['request_id'],
                    'response': f"Processed: {request['prompt'][:50]}...",
                    'model': model,
                    'processing_time': time.time() - request['timestamp']
                }

                # Cache response
                with self.cache_lock:
                    self.response_cache[request['cache_key']] = response

                    # Limit cache size
                    if len(self.response_cache) > 1000:
                        # Remove oldest entries
                        oldest_keys = list(self.response_cache.keys())[:100]
                        for key in oldest_keys:
                            del self.response_cache[key]

                # Set result
                if not request['future'].done():
                    request['future'].set_result(response)

        except Exception as e:
            logger.error(f"Error processing model batch for {model}: {e}")
            for request in requests:
                if not request['future'].done():
                    request['future'].set_exception(e)


class EnhancedAgentCoordinator:
    """Enhanced agent coordinator with advanced concurrency features"""

    def __init__(self,
                 max_concurrent_agents: int = 50,
                 max_concurrent_tasks: int = 200,
                 max_message_throughput: int = 1000):

        self.max_concurrent_agents = max_concurrent_agents
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_message_throughput = max_message_throughput

        # Core components
        self.resource_pool = ResourcePool(max_concurrent_agents)
        self.dependency_graph = DependencyGraph()
        self.async_llm_processor = AsyncLLMProcessor()

        # Task management
        self.tasks: Dict[str, EnhancedTask] = {}
        self.task_queue = PriorityQueue()
        self.ready_queue = Queue()
        self.completed_tasks: Set[str] = set()

        # Thread pools
        self.task_executor = ThreadPoolExecutor(
            max_workers=max_concurrent_tasks,
            thread_name_prefix="TaskExecutor"
        )
        self.message_executor = ThreadPoolExecutor(
            max_workers=max_message_throughput // 10,
            thread_name_prefix="MessageProcessor"
        )

        # Synchronization
        self.coordinator_lock = threading.RLock()
        self.shutdown_event = threading.Event()

        # Monitoring
        self.metrics = {
            'tasks_created': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'messages_processed': 0,
            'avg_task_duration': 0.0,
            'avg_message_processing_time': 0.0,
            'resource_utilization': 0.0,
            'dependency_violations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

        # Background threads
        self.scheduler_thread = None
        self.monitor_thread = None

        logger.info(f"EnhancedAgentCoordinator initialized: "
                   f"{max_concurrent_agents} agents, "
                   f"{max_concurrent_tasks} tasks, "
                   f"{max_message_throughput} msg/min")

    async def start(self):
        """Start the enhanced coordinator"""
        # Start async components
        await self.async_llm_processor.start()

        # Start background threads
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self.scheduler_thread.start()

        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self.monitor_thread.start()

        logger.info("EnhancedAgentCoordinator started")

    async def stop(self):
        """Stop the enhanced coordinator"""
        self.shutdown_event.set()

        # Stop async components
        await self.async_llm_processor.stop()

        # Shutdown thread pools
        self.task_executor.shutdown(wait=True)
        self.message_executor.shutdown(wait=True)

        logger.info("EnhancedAgentCoordinator stopped")

    def create_task(self,
                   agent_name: str,
                   description: str,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   dependencies: List[str] = None,
                   required_resources: List[str] = None,
                   estimated_duration: int = None) -> str:
        """Create a new enhanced task"""

        task_id = str(uuid.uuid4())
        dependencies = dependencies or []
        required_resources = required_resources or []

        task = EnhancedTask(
            task_id=task_id,
            agent_name=agent_name,
            description=description,
            priority=priority,
            dependencies=dependencies,
            required_resources=required_resources,
            estimated_duration=estimated_duration
        )

        with self.coordinator_lock:
            self.tasks[task_id] = task
            self.metrics['tasks_created'] += 1

            # Add dependencies to graph
            for dep in dependencies:
                self.dependency_graph.add_dependency(task_id, dep)

            # Check if task is ready to execute
            if self.dependency_graph.is_ready(task_id):
                task.status = TaskStatus.READY
                self.task_queue.put(task)

        logger.info(f"Created task {task_id} for agent {agent_name}")
        return task_id

    def add_dependency(self, task_id: str, depends_on: str):
        """Add a dependency between tasks"""
        with self.coordinator_lock:
            if task_id in self.tasks and depends_on in self.tasks:
                self.dependency_graph.add_dependency(task_id, depends_on)

                # Update task status if it's no longer ready
                task = self.tasks[task_id]
                if task.status == TaskStatus.READY and not self.dependency_graph.is_ready(task_id):
                    task.status = TaskStatus.BLOCKED

                logger.info(f"Added dependency: {task_id} depends on {depends_on}")

    def _scheduler_loop(self):
        """Main scheduler loop for task execution"""
        logger.info("Scheduler loop started")

        while not self.shutdown_event.is_set():
            try:
                # Get ready task
                try:
                    task = self.task_queue.get(timeout=1.0)
                except:
                    continue

                # Check if agent slot is available
                if not self.resource_pool.acquire_agent_slot(task.agent_name):
                    # Put task back in queue
                    self.task_queue.put(task)
                    time.sleep(0.1)
                    continue

                # Submit task for execution
                future = self.task_executor.submit(self._execute_task, task)

                # Don't wait for completion here - let it run async

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(1)

        logger.info("Scheduler loop stopped")

    def _execute_task(self, task: EnhancedTask):
        """Execute a single task"""
        start_time = time.time()

        try:
            # Update task status
            with self.coordinator_lock:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()

            # Acquire required resources
            if task.required_resources:
                if not self.resource_pool.acquire_resources(
                    task.agent_name, task.required_resources, timeout=30.0
                ):
                    raise Exception(f"Failed to acquire resources: {task.required_resources}")

            # Execute task (simulate work)
            execution_time = task.estimated_duration or 1.0
            time.sleep(min(execution_time, 5.0))  # Cap at 5 seconds for simulation

            # Mark task as completed
            with self.coordinator_lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                self.completed_tasks.add(task.task_id)
                self.metrics['tasks_completed'] += 1

                # Update average task duration
                duration = time.time() - start_time
                self.metrics['avg_task_duration'] = (
                    (self.metrics['avg_task_duration'] * (self.metrics['tasks_completed'] - 1) + duration) /
                    self.metrics['tasks_completed']
                )

                # Check for newly ready tasks
                ready_tasks = self.dependency_graph.mark_completed(task.task_id)
                for ready_task_id in ready_tasks:
                    if ready_task_id in self.tasks:
                        ready_task = self.tasks[ready_task_id]
                        ready_task.status = TaskStatus.READY
                        self.task_queue.put(ready_task)

            logger.info(f"Task {task.task_id} completed in {duration:.2f}s")

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")

            with self.coordinator_lock:
                task.status = TaskStatus.FAILED
                task.retry_count += 1
                self.metrics['tasks_failed'] += 1

                # Retry if under limit
                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.READY
                    self.task_queue.put(task)
                    logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count + 1})")

        finally:
            # Release resources
            if task.required_resources:
                self.resource_pool.release_resources(task.agent_name, task.required_resources)

            # Release agent slot
            self.resource_pool.release_agent_slot(task.agent_name)

    def _monitor_loop(self):
        """Monitor system performance and update metrics"""
        logger.info("Monitor loop started")

        while not self.shutdown_event.is_set():
            try:
                # Update resource utilization
                resource_status = self.resource_pool.get_resource_status()
                self.metrics['resource_utilization'] = resource_status['utilization']

                # Log metrics periodically
                if int(time.time()) % 60 == 0:  # Every minute
                    logger.info(f"Coordinator metrics: {self.metrics}")

                time.sleep(5)  # Update every 5 seconds

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(5)

        logger.info("Monitor loop stopped")

    async def process_message_async(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message asynchronously with LLM integration"""
        start_time = time.time()

        try:
            # Extract message information
            message_text = message_data.get('text', '')
            agent_name = message_data.get('agent_name', '')

            # Process with async LLM
            request_id = str(uuid.uuid4())
            llm_response = await self.async_llm_processor.process_request(
                request_id, message_text
            )

            # Update metrics
            processing_time = time.time() - start_time
            with self.coordinator_lock:
                self.metrics['messages_processed'] += 1
                self.metrics['avg_message_processing_time'] = (
                    (self.metrics['avg_message_processing_time'] * (self.metrics['messages_processed'] - 1) + processing_time) /
                    self.metrics['messages_processed']
                )

            return {
                'success': True,
                'response': llm_response,
                'processing_time': processing_time
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        with self.coordinator_lock:
            task_status_counts = defaultdict(int)
            for task in self.tasks.values():
                task_status_counts[task.status.value] += 1

            return {
                'coordinator_metrics': dict(self.metrics),
                'resource_status': self.resource_pool.get_resource_status(),
                'task_counts': dict(task_status_counts),
                'total_tasks': len(self.tasks),
                'dependency_graph_size': len(self.dependency_graph.dependencies),
                'cache_size': len(self.async_llm_processor.response_cache),
                'active_threads': threading.active_count(),
                'timestamp': datetime.now().isoformat()
            }

    def detect_dependency_cycles(self) -> List[List[str]]:
        """Detect circular dependencies in the task graph"""
        cycles = self.dependency_graph.detect_cycles()
        if cycles:
            self.metrics['dependency_violations'] += len(cycles)
            logger.warning(f"Detected {len(cycles)} dependency cycles: {cycles}")
        return cycles

    def optimize_task_scheduling(self):
        """Optimize task scheduling based on current system state"""
        with self.coordinator_lock:
            # Get current resource utilization
            resource_status = self.resource_pool.get_resource_status()

            # If utilization is low, increase priority of waiting tasks
            if resource_status['utilization'] < 0.5:
                waiting_tasks = [
                    task for task in self.tasks.values()
                    if task.status == TaskStatus.READY
                ]

                for task in waiting_tasks:
                    if task.priority.value > TaskPriority.HIGH.value:
                        task.priority = TaskPriority.HIGH
                        logger.debug(f"Boosted priority for task {task.task_id}")

            # Detect and resolve dependency cycles
            cycles = self.detect_dependency_cycles()
            for cycle in cycles:
                logger.warning(f"Breaking dependency cycle: {cycle}")
                # Break cycle by removing the last dependency
                if len(cycle) > 1:
                    self.dependency_graph.remove_dependency(cycle[-1], cycle[0])