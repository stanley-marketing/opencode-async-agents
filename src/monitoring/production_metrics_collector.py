"""
Production-grade metrics collection system for OpenCode-Slack.
Implements comprehensive system performance monitoring, business metrics tracking,
and time-series data collection with optimized aggregation.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
import os
import psutil
import sqlite3
import statistics
import threading
import time

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    thread_count: int
    load_average: List[float]


@dataclass
class BusinessMetrics:
    """Business KPI metrics"""
    timestamp: datetime
    total_tasks_assigned: int
    tasks_completed: int
    tasks_in_progress: int
    tasks_failed: int
    average_task_completion_time: float
    agent_utilization_percent: float
    active_agents: int
    idle_agents: int
    stuck_agents: int
    total_agents: int
    chat_messages_sent: int
    chat_messages_received: int
    api_requests_count: int
    error_rate_percent: float


@dataclass
class PerformanceMetrics:
    """Performance and response time metrics"""
    timestamp: datetime
    api_response_times: Dict[str, List[float]]
    agent_response_times: Dict[str, List[float]]
    task_processing_times: Dict[str, float]
    database_query_times: List[float]
    file_operation_times: List[float]
    memory_usage_by_component: Dict[str, float]
    cpu_usage_by_component: Dict[str, float]


class ProductionMetricsCollector:
    """Production-grade metrics collection and aggregation system"""

    def __init__(self, agent_manager, task_tracker, session_manager,
                 db_path: str = "monitoring_metrics.db",
                 collection_interval: int = 30,
                 retention_days: int = 30):
        """
        Initialize the production metrics collector

        Args:
            agent_manager: Agent manager instance
            task_tracker: Task progress tracker instance
            session_manager: Session manager instance
            db_path: Path to metrics database
            collection_interval: Metrics collection interval in seconds
            retention_days: How long to retain metrics data
        """
        self.agent_manager = agent_manager
        self.task_tracker = task_tracker
        self.session_manager = session_manager
        self.db_path = db_path
        self.collection_interval = collection_interval
        self.retention_days = retention_days

        # Runtime metrics storage
        self.system_metrics_buffer = deque(maxlen=1000)
        self.business_metrics_buffer = deque(maxlen=1000)
        self.performance_metrics_buffer = deque(maxlen=1000)

        # Performance tracking
        self.api_response_times = defaultdict(list)
        self.agent_response_times = defaultdict(list)
        self.task_completion_times = {}
        self.database_query_times = deque(maxlen=100)
        self.file_operation_times = deque(maxlen=100)

        # Business metrics tracking
        self.task_assignments_count = 0
        self.task_completions_count = 0
        self.chat_messages_sent = 0
        self.chat_messages_received = 0
        self.api_requests_count = 0
        self.error_count = 0

        # Collection state
        self.is_collecting = False
        self.collection_thread = None

        # Initialize database
        self._init_database()

        logger.info(f"ProductionMetricsCollector initialized with {collection_interval}s interval")

    def _init_database(self):
        """Initialize the metrics database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # System metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        cpu_percent REAL,
                        memory_percent REAL,
                        memory_used_mb REAL,
                        memory_available_mb REAL,
                        disk_usage_percent REAL,
                        disk_free_gb REAL,
                        network_bytes_sent INTEGER,
                        network_bytes_recv INTEGER,
                        process_count INTEGER,
                        thread_count INTEGER,
                        load_average TEXT
                    )
                ''')

                # Business metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS business_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        total_tasks_assigned INTEGER,
                        tasks_completed INTEGER,
                        tasks_in_progress INTEGER,
                        tasks_failed INTEGER,
                        average_task_completion_time REAL,
                        agent_utilization_percent REAL,
                        active_agents INTEGER,
                        idle_agents INTEGER,
                        stuck_agents INTEGER,
                        total_agents INTEGER,
                        chat_messages_sent INTEGER,
                        chat_messages_received INTEGER,
                        api_requests_count INTEGER,
                        error_rate_percent REAL
                    )
                ''')

                # Performance metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        api_response_times TEXT,
                        agent_response_times TEXT,
                        task_processing_times TEXT,
                        database_query_times TEXT,
                        file_operation_times TEXT,
                        memory_usage_by_component TEXT,
                        cpu_usage_by_component TEXT
                    )
                ''')

                # Create indexes for better query performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_metrics(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_business_timestamp ON business_metrics(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp)')

                conn.commit()

            logger.info("Metrics database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing metrics database: {e}")
            raise

    def start_collection(self):
        """Start metrics collection"""
        if self.is_collecting:
            logger.warning("Metrics collection is already running")
            return

        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()

        logger.info("Production metrics collection started")

    def stop_collection(self):
        """Stop metrics collection"""
        if not self.is_collecting:
            logger.warning("Metrics collection is not running")
            return

        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)

        logger.info("Production metrics collection stopped")

    def _collection_loop(self):
        """Main metrics collection loop"""
        logger.info("Starting metrics collection loop")

        while self.is_collecting:
            try:
                start_time = time.time()

                # Collect all metrics
                system_metrics = self._collect_system_metrics()
                business_metrics = self._collect_business_metrics()
                performance_metrics = self._collect_performance_metrics()

                # Store in buffers
                self.system_metrics_buffer.append(system_metrics)
                self.business_metrics_buffer.append(business_metrics)
                self.performance_metrics_buffer.append(performance_metrics)

                # Persist to database
                self._persist_metrics(system_metrics, business_metrics, performance_metrics)

                # Clean up old data
                self._cleanup_old_data()

                collection_time = time.time() - start_time
                logger.debug(f"Metrics collection completed in {collection_time:.3f}s")

                # Sleep for remaining interval
                sleep_time = max(0, self.collection_interval - collection_time)
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(self.collection_interval)

    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage('/')

            # Network stats
            network = psutil.net_io_counters()

            # Process info
            process_count = len(psutil.pids())

            # Thread count for current process
            current_process = psutil.Process()
            thread_count = current_process.num_threads()

            # Load average (Unix-like systems)
            try:
                load_avg = list(os.getloadavg())
            except (OSError, AttributeError):
                load_avg = [0.0, 0.0, 0.0]  # Windows fallback

            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=disk.percent,
                disk_free_gb=disk.free / (1024 * 1024 * 1024),
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                process_count=process_count,
                thread_count=thread_count,
                load_average=load_avg
            )

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0, memory_percent=0.0, memory_used_mb=0.0,
                memory_available_mb=0.0, disk_usage_percent=0.0, disk_free_gb=0.0,
                network_bytes_sent=0, network_bytes_recv=0, process_count=0,
                thread_count=0, load_average=[0.0, 0.0, 0.0]
            )

    def _collect_business_metrics(self) -> BusinessMetrics:
        """Collect business KPI metrics"""
        try:
            # Get agent status
            agent_statuses = self.agent_manager.get_agent_status()
            total_agents = len(agent_statuses)

            active_agents = sum(1 for status in agent_statuses.values()
                              if status.get('worker_status') == 'working')
            idle_agents = sum(1 for status in agent_statuses.values()
                            if status.get('worker_status') == 'idle')
            stuck_agents = sum(1 for status in agent_statuses.values()
                             if status.get('worker_status') == 'stuck')

            # Calculate agent utilization
            agent_utilization = (active_agents / total_agents * 100) if total_agents > 0 else 0

            # Get task metrics
            all_progress = self.task_tracker.get_all_progress()
            tasks_in_progress = len([p for p in all_progress.values() if p])

            # Calculate average task completion time
            completion_times = list(self.task_completion_times.values())
            avg_completion_time = statistics.mean(completion_times) if completion_times else 0.0

            # Calculate error rate
            total_requests = max(self.api_requests_count, 1)
            error_rate = (self.error_count / total_requests * 100)

            return BusinessMetrics(
                timestamp=datetime.now(),
                total_tasks_assigned=self.task_assignments_count,
                tasks_completed=self.task_completions_count,
                tasks_in_progress=tasks_in_progress,
                tasks_failed=0,  # TODO: Implement task failure tracking
                average_task_completion_time=avg_completion_time,
                agent_utilization_percent=agent_utilization,
                active_agents=active_agents,
                idle_agents=idle_agents,
                stuck_agents=stuck_agents,
                total_agents=total_agents,
                chat_messages_sent=self.chat_messages_sent,
                chat_messages_received=self.chat_messages_received,
                api_requests_count=self.api_requests_count,
                error_rate_percent=error_rate
            )

        except Exception as e:
            logger.error(f"Error collecting business metrics: {e}")
            return BusinessMetrics(
                timestamp=datetime.now(),
                total_tasks_assigned=0, tasks_completed=0, tasks_in_progress=0,
                tasks_failed=0, average_task_completion_time=0.0,
                agent_utilization_percent=0.0, active_agents=0, idle_agents=0,
                stuck_agents=0, total_agents=0, chat_messages_sent=0,
                chat_messages_received=0, api_requests_count=0, error_rate_percent=0.0
            )

    def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect performance and response time metrics"""
        try:
            # Aggregate API response times
            api_times = {}
            for endpoint, times in self.api_response_times.items():
                if times:
                    api_times[endpoint] = {
                        'avg': statistics.mean(times),
                        'min': min(times),
                        'max': max(times),
                        'p95': statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
                        'count': len(times)
                    }

            # Aggregate agent response times
            agent_times = {}
            for agent, times in self.agent_response_times.items():
                if times:
                    agent_times[agent] = {
                        'avg': statistics.mean(times),
                        'min': min(times),
                        'max': max(times),
                        'count': len(times)
                    }

            # Get component memory usage
            memory_by_component = self._get_memory_usage_by_component()
            cpu_by_component = self._get_cpu_usage_by_component()

            return PerformanceMetrics(
                timestamp=datetime.now(),
                api_response_times=api_times,
                agent_response_times=agent_times,
                task_processing_times=dict(self.task_completion_times),
                database_query_times=list(self.database_query_times),
                file_operation_times=list(self.file_operation_times),
                memory_usage_by_component=memory_by_component,
                cpu_usage_by_component=cpu_by_component
            )

        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                api_response_times={}, agent_response_times={},
                task_processing_times={}, database_query_times=[],
                file_operation_times=[], memory_usage_by_component={},
                cpu_usage_by_component={}
            )

    def _get_memory_usage_by_component(self) -> Dict[str, float]:
        """Get memory usage breakdown by component"""
        try:
            current_process = psutil.Process()
            memory_info = current_process.memory_info()

            return {
                'total_rss_mb': memory_info.rss / (1024 * 1024),
                'total_vms_mb': memory_info.vms / (1024 * 1024),
                'agent_manager': 0.0,  # TODO: Implement component-specific tracking
                'task_tracker': 0.0,
                'session_manager': 0.0,
                'monitoring_system': 0.0
            }
        except Exception as e:
            logger.error(f"Error getting memory usage by component: {e}")
            return {}

    def _get_cpu_usage_by_component(self) -> Dict[str, float]:
        """Get CPU usage breakdown by component"""
        try:
            current_process = psutil.Process()
            cpu_percent = current_process.cpu_percent()

            return {
                'total_cpu_percent': cpu_percent,
                'agent_manager': 0.0,  # TODO: Implement component-specific tracking
                'task_tracker': 0.0,
                'session_manager': 0.0,
                'monitoring_system': 0.0
            }
        except Exception as e:
            logger.error(f"Error getting CPU usage by component: {e}")
            return {}

    def _persist_metrics(self, system_metrics: SystemMetrics,
                        business_metrics: BusinessMetrics,
                        performance_metrics: PerformanceMetrics):
        """Persist metrics to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert system metrics
                cursor.execute('''
                    INSERT INTO system_metrics (
                        timestamp, cpu_percent, memory_percent, memory_used_mb,
                        memory_available_mb, disk_usage_percent, disk_free_gb,
                        network_bytes_sent, network_bytes_recv, process_count,
                        thread_count, load_average
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    system_metrics.timestamp, system_metrics.cpu_percent,
                    system_metrics.memory_percent, system_metrics.memory_used_mb,
                    system_metrics.memory_available_mb, system_metrics.disk_usage_percent,
                    system_metrics.disk_free_gb, system_metrics.network_bytes_sent,
                    system_metrics.network_bytes_recv, system_metrics.process_count,
                    system_metrics.thread_count, json.dumps(system_metrics.load_average)
                ))

                # Insert business metrics
                cursor.execute('''
                    INSERT INTO business_metrics (
                        timestamp, total_tasks_assigned, tasks_completed, tasks_in_progress,
                        tasks_failed, average_task_completion_time, agent_utilization_percent,
                        active_agents, idle_agents, stuck_agents, total_agents,
                        chat_messages_sent, chat_messages_received, api_requests_count,
                        error_rate_percent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    business_metrics.timestamp, business_metrics.total_tasks_assigned,
                    business_metrics.tasks_completed, business_metrics.tasks_in_progress,
                    business_metrics.tasks_failed, business_metrics.average_task_completion_time,
                    business_metrics.agent_utilization_percent, business_metrics.active_agents,
                    business_metrics.idle_agents, business_metrics.stuck_agents,
                    business_metrics.total_agents, business_metrics.chat_messages_sent,
                    business_metrics.chat_messages_received, business_metrics.api_requests_count,
                    business_metrics.error_rate_percent
                ))

                # Insert performance metrics
                cursor.execute('''
                    INSERT INTO performance_metrics (
                        timestamp, api_response_times, agent_response_times,
                        task_processing_times, database_query_times, file_operation_times,
                        memory_usage_by_component, cpu_usage_by_component
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    performance_metrics.timestamp,
                    json.dumps(performance_metrics.api_response_times),
                    json.dumps(performance_metrics.agent_response_times),
                    json.dumps(performance_metrics.task_processing_times),
                    json.dumps(performance_metrics.database_query_times),
                    json.dumps(performance_metrics.file_operation_times),
                    json.dumps(performance_metrics.memory_usage_by_component),
                    json.dumps(performance_metrics.cpu_usage_by_component)
                ))

                conn.commit()

        except Exception as e:
            logger.error(f"Error persisting metrics to database: {e}")

    def _cleanup_old_data(self):
        """Clean up old metrics data based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Clean up old data from all tables
                cursor.execute('DELETE FROM system_metrics WHERE timestamp < ?', (cutoff_date,))
                cursor.execute('DELETE FROM business_metrics WHERE timestamp < ?', (cutoff_date,))
                cursor.execute('DELETE FROM performance_metrics WHERE timestamp < ?', (cutoff_date,))

                conn.commit()

        except Exception as e:
            logger.error(f"Error cleaning up old metrics data: {e}")

    # Public methods for recording metrics

    def record_api_request(self, endpoint: str, response_time: float, success: bool = True):
        """Record API request metrics"""
        self.api_requests_count += 1
        self.api_response_times[endpoint].append(response_time)

        if not success:
            self.error_count += 1

        # Keep only recent response times
        if len(self.api_response_times[endpoint]) > 1000:
            self.api_response_times[endpoint] = self.api_response_times[endpoint][-500:]

    def record_agent_response(self, agent_name: str, response_time: float):
        """Record agent response time"""
        self.agent_response_times[agent_name].append(response_time)

        # Keep only recent response times
        if len(self.agent_response_times[agent_name]) > 100:
            self.agent_response_times[agent_name] = self.agent_response_times[agent_name][-50:]

    def record_task_assignment(self, task_id: str):
        """Record task assignment"""
        self.task_assignments_count += 1

    def record_task_completion(self, task_id: str, completion_time: float):
        """Record task completion"""
        self.task_completions_count += 1
        self.task_completion_times[task_id] = completion_time

        # Keep only recent completion times
        if len(self.task_completion_times) > 1000:
            # Remove oldest entries
            oldest_keys = list(self.task_completion_times.keys())[:500]
            for key in oldest_keys:
                del self.task_completion_times[key]

    def record_chat_message(self, sent: bool = True):
        """Record chat message"""
        if sent:
            self.chat_messages_sent += 1
        else:
            self.chat_messages_received += 1

    def record_database_query(self, query_time: float):
        """Record database query time"""
        self.database_query_times.append(query_time)

    def record_file_operation(self, operation_time: float):
        """Record file operation time"""
        self.file_operation_times.append(operation_time)

    # Query methods for retrieving metrics

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        return {
            'system': asdict(self.system_metrics_buffer[-1]) if self.system_metrics_buffer else None,
            'business': asdict(self.business_metrics_buffer[-1]) if self.business_metrics_buffer else None,
            'performance': asdict(self.performance_metrics_buffer[-1]) if self.performance_metrics_buffer else None,
            'collection_status': {
                'is_collecting': self.is_collecting,
                'buffer_sizes': {
                    'system': len(self.system_metrics_buffer),
                    'business': len(self.business_metrics_buffer),
                    'performance': len(self.performance_metrics_buffer)
                }
            }
        }

    def get_metrics_history(self, hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """Get metrics history from database"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get system metrics
                cursor.execute('''
                    SELECT * FROM system_metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (start_time,))
                system_metrics = [dict(row) for row in cursor.fetchall()]

                # Get business metrics
                cursor.execute('''
                    SELECT * FROM business_metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (start_time,))
                business_metrics = [dict(row) for row in cursor.fetchall()]

                # Get performance metrics
                cursor.execute('''
                    SELECT * FROM performance_metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (start_time,))
                performance_metrics = [dict(row) for row in cursor.fetchall()]

                return {
                    'system': system_metrics,
                    'business': business_metrics,
                    'performance': performance_metrics
                }

        except Exception as e:
            logger.error(f"Error retrieving metrics history: {e}")
            return {'system': [], 'business': [], 'performance': []}

    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get aggregated metrics summary"""
        try:
            history = self.get_metrics_history(hours)

            summary = {
                'period_hours': hours,
                'system_summary': {},
                'business_summary': {},
                'performance_summary': {}
            }

            # System metrics summary
            if history['system']:
                cpu_values = [m['cpu_percent'] for m in history['system']]
                memory_values = [m['memory_percent'] for m in history['system']]

                summary['system_summary'] = {
                    'avg_cpu_percent': statistics.mean(cpu_values),
                    'max_cpu_percent': max(cpu_values),
                    'avg_memory_percent': statistics.mean(memory_values),
                    'max_memory_percent': max(memory_values),
                    'data_points': len(history['system'])
                }

            # Business metrics summary
            if history['business']:
                utilization_values = [m['agent_utilization_percent'] for m in history['business']]

                summary['business_summary'] = {
                    'avg_agent_utilization': statistics.mean(utilization_values),
                    'max_agent_utilization': max(utilization_values),
                    'total_tasks_assigned': max([m['total_tasks_assigned'] for m in history['business']]),
                    'total_tasks_completed': max([m['tasks_completed'] for m in history['business']]),
                    'data_points': len(history['business'])
                }

            return summary

        except Exception as e:
            logger.error(f"Error generating metrics summary: {e}")
            return {}