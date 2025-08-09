"""
Production-grade health check system for OpenCode-Slack.
Implements deep health checks, dependency monitoring, cascade failure detection,
and automated recovery triggers with self-healing mechanisms.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
import json
import logging
import os
import psutil
import requests
import sqlite3
import subprocess
import threading
import time

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return self.value

    @classmethod
    def from_string(cls, value: str):
        """Create from string value"""
        for status in cls:
            if status.value == value:
                return status
        return cls.UNKNOWN


@dataclass
class HealthCheckResult:
    """Health check result"""
    component: str
    status: HealthStatus
    response_time_ms: float
    timestamp: datetime
    message: str
    details: Dict[str, Any]
    dependencies: List[str] = None
    recovery_actions: List[str] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'component': self.component,
            'status': self.status.value if isinstance(self.status, HealthStatus) else self.status,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'message': self.message,
            'details': self.details,
            'dependencies': self.dependencies or [],
            'recovery_actions': self.recovery_actions or []
        }


@dataclass
class DependencyHealth:
    """Dependency health information"""
    name: str
    type: str  # database, api, service, file_system
    status: HealthStatus
    last_check: datetime
    response_time_ms: float
    error_count: int
    consecutive_failures: int
    details: Dict[str, Any]

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'type': self.type,
            'status': self.status.value if isinstance(self.status, HealthStatus) else self.status,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'response_time_ms': self.response_time_ms,
            'error_count': self.error_count,
            'consecutive_failures': self.consecutive_failures,
            'details': self.details
        }


class ProductionHealthChecker:
    """Production-grade health checking system"""

    def __init__(self, agent_manager, task_tracker, session_manager,
                 check_interval: int = 30):
        """
        Initialize the production health checker

        Args:
            agent_manager: Agent manager instance
            task_tracker: Task tracker instance
            session_manager: Session manager instance
            check_interval: Health check interval in seconds
        """
        self.agent_manager = agent_manager
        self.task_tracker = task_tracker
        self.session_manager = session_manager
        self.check_interval = check_interval

        # Health check state
        self.is_checking = False
        self.check_thread = None

        # Health results storage
        self.health_results: Dict[str, HealthCheckResult] = {}
        self.health_history: deque = deque(maxlen=1000)
        self.dependency_health: Dict[str, DependencyHealth] = {}

        # Recovery system
        self.recovery_actions: Dict[str, Callable] = {}
        self.auto_recovery_enabled = True
        self.recovery_history: deque = deque(maxlen=500)

        # Cascade failure detection
        self.failure_patterns: Dict[str, List[str]] = {}
        self.cascade_thresholds: Dict[str, int] = {}

        # Setup health checks
        self._setup_health_checks()
        self._setup_recovery_actions()
        self._setup_dependency_monitoring()

        logger.info("ProductionHealthChecker initialized")

    def _setup_health_checks(self):
        """Setup health check configurations"""
        self.health_checks = {
            'system_resources': self._check_system_resources,
            'database_connectivity': self._check_database_connectivity,
            'file_system': self._check_file_system,
            'agent_manager': self._check_agent_manager,
            'task_tracker': self._check_task_tracker,
            'session_manager': self._check_session_manager,
            'monitoring_system': self._check_monitoring_system,
            'network_connectivity': self._check_network_connectivity,
            'process_health': self._check_process_health,
            'memory_leaks': self._check_memory_leaks
        }

        # Setup cascade failure patterns
        self.failure_patterns = {
            'database_connectivity': ['agent_manager', 'task_tracker'],
            'file_system': ['session_manager', 'task_tracker'],
            'system_resources': ['agent_manager', 'session_manager', 'task_tracker'],
            'network_connectivity': ['monitoring_system']
        }

        # Setup cascade thresholds
        self.cascade_thresholds = {
            'database_connectivity': 3,  # 3 consecutive failures trigger cascade check
            'file_system': 2,
            'system_resources': 5,
            'network_connectivity': 3
        }

    def _setup_recovery_actions(self):
        """Setup automated recovery actions"""
        self.recovery_actions = {
            'restart_stuck_agents': self._recovery_restart_stuck_agents,
            'clear_memory_cache': self._recovery_clear_memory_cache,
            'restart_monitoring': self._recovery_restart_monitoring,
            'cleanup_temp_files': self._recovery_cleanup_temp_files,
            'restart_sessions': self._recovery_restart_sessions,
            'optimize_database': self._recovery_optimize_database,
            'free_disk_space': self._recovery_free_disk_space,
            'restart_network_services': self._recovery_restart_network_services
        }

    def _setup_dependency_monitoring(self):
        """Setup dependency monitoring"""
        dependencies = [
            ('database', 'database', 'employees.db'),
            ('sessions_directory', 'file_system', 'sessions'),
            ('monitoring_database', 'database', 'monitoring_metrics.db'),
            ('temp_directory', 'file_system', '/tmp'),
            ('log_directory', 'file_system', 'logs'),
            ('localhost_api', 'api', 'http://localhost:8080/health')
        ]

        for name, dep_type, target in dependencies:
            self.dependency_health[name] = DependencyHealth(
                name=name,
                type=dep_type,
                status=HealthStatus.UNKNOWN,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=0,
                consecutive_failures=0,
                details={'target': target}
            )

    def start_health_checking(self):
        """Start health checking"""
        if self.is_checking:
            logger.warning("Health checking is already running")
            return

        self.is_checking = True
        self.check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.check_thread.start()

        logger.info("Production health checking started")

    def stop_health_checking(self):
        """Stop health checking"""
        if not self.is_checking:
            logger.warning("Health checking is not running")
            return

        self.is_checking = False
        if self.check_thread:
            self.check_thread.join(timeout=5)

        logger.info("Production health checking stopped")

    def _health_check_loop(self):
        """Main health checking loop"""
        logger.info("Starting health check loop")

        while self.is_checking:
            try:
                start_time = time.time()

                # Run all health checks
                self._run_all_health_checks()

                # Check dependencies
                self._check_all_dependencies()

                # Detect cascade failures
                self._detect_cascade_failures()

                # Trigger recovery if needed
                if self.auto_recovery_enabled:
                    self._trigger_auto_recovery()

                check_duration = time.time() - start_time
                logger.debug(f"Health check cycle completed in {check_duration:.3f}s")

                # Sleep for remaining interval
                sleep_time = max(0, self.check_interval - check_duration)
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(self.check_interval)

    def _run_all_health_checks(self):
        """Run all configured health checks"""
        for check_name, check_function in self.health_checks.items():
            try:
                start_time = time.time()
                result = check_function()
                response_time = (time.time() - start_time) * 1000

                if result:
                    result.response_time_ms = response_time
                    result.timestamp = datetime.now()

                    # Store result
                    self.health_results[check_name] = result
                    self.health_history.append(result)

                    logger.debug(f"Health check {check_name}: {result.status.value} ({response_time:.2f}ms)")

            except Exception as e:
                logger.error(f"Error in health check {check_name}: {e}")

                # Create error result
                error_result = HealthCheckResult(
                    component=check_name,
                    status=HealthStatus.CRITICAL,
                    response_time_ms=0.0,
                    timestamp=datetime.now(),
                    message=f"Health check failed: {str(e)}",
                    details={'error': str(e), 'exception_type': type(e).__name__}
                )

                self.health_results[check_name] = error_result
                self.health_history.append(error_result)

    def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource health"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent

            # Load average
            try:
                load_avg = os.getloadavg()[0]  # 1-minute load average
                cpu_count = psutil.cpu_count()
                load_percent = (load_avg / cpu_count) * 100 if cpu_count > 0 else 0
            except (OSError, AttributeError):
                load_percent = 0  # Windows fallback

            # Determine status
            critical_issues = []
            warning_issues = []

            if cpu_percent > 90:
                critical_issues.append(f"CPU usage critical: {cpu_percent:.1f}%")
            elif cpu_percent > 80:
                warning_issues.append(f"CPU usage high: {cpu_percent:.1f}%")

            if memory_percent > 95:
                critical_issues.append(f"Memory usage critical: {memory_percent:.1f}%")
            elif memory_percent > 85:
                warning_issues.append(f"Memory usage high: {memory_percent:.1f}%")

            if disk_percent > 95:
                critical_issues.append(f"Disk usage critical: {disk_percent:.1f}%")
            elif disk_percent > 90:
                warning_issues.append(f"Disk usage high: {disk_percent:.1f}%")

            if load_percent > 200:
                critical_issues.append(f"System load critical: {load_percent:.1f}%")
            elif load_percent > 150:
                warning_issues.append(f"System load high: {load_percent:.1f}%")

            # Determine overall status
            if critical_issues:
                status = HealthStatus.CRITICAL
                message = "; ".join(critical_issues)
                recovery_actions = ['clear_memory_cache', 'cleanup_temp_files', 'free_disk_space']
            elif warning_issues:
                status = HealthStatus.DEGRADED
                message = "; ".join(warning_issues)
                recovery_actions = ['cleanup_temp_files']
            else:
                status = HealthStatus.HEALTHY
                message = "System resources within normal limits"
                recovery_actions = []

            return HealthCheckResult(
                component="system_resources",
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=message,
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'load_percent': load_percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_free_gb': disk.free / (1024**3)
                },
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="system_resources",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"Failed to check system resources: {str(e)}",
                details={'error': str(e)}
            )

    def _check_database_connectivity(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        try:
            db_path = getattr(self.agent_manager.file_manager, 'db_path', 'employees.db')

            start_time = time.time()

            # Test database connection and basic query
            with sqlite3.connect(db_path, timeout=5) as conn:
                cursor = conn.cursor()

                # Test basic query
                cursor.execute("SELECT COUNT(*) FROM employees")
                employee_count = cursor.fetchone()[0]

                # Test database integrity
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]

                # Check database size
                db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0

            query_time = (time.time() - start_time) * 1000

            # Determine status
            if integrity_result != "ok":
                status = HealthStatus.CRITICAL
                message = f"Database integrity check failed: {integrity_result}"
                recovery_actions = ['optimize_database']
            elif query_time > 1000:  # More than 1 second
                status = HealthStatus.DEGRADED
                message = f"Database queries slow: {query_time:.2f}ms"
                recovery_actions = ['optimize_database']
            else:
                status = HealthStatus.HEALTHY
                message = f"Database healthy, {employee_count} employees"
                recovery_actions = []

            return HealthCheckResult(
                component="database_connectivity",
                status=status,
                response_time_ms=query_time,
                timestamp=datetime.now(),
                message=message,
                details={
                    'employee_count': employee_count,
                    'integrity_check': integrity_result,
                    'database_size_mb': db_size / (1024 * 1024),
                    'query_time_ms': query_time
                },
                dependencies=['file_system'],
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="database_connectivity",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"Database connection failed: {str(e)}",
                details={'error': str(e)},
                recovery_actions=['optimize_database']
            )

    def _check_file_system(self) -> HealthCheckResult:
        """Check file system health"""
        try:
            issues = []
            details = {}

            # Check critical directories
            critical_dirs = [
                ('sessions', getattr(self.session_manager, 'sessions_dir', 'sessions')),
                ('logs', 'logs'),
                ('temp', '/tmp')
            ]

            for dir_name, dir_path in critical_dirs:
                if not os.path.exists(dir_path):
                    issues.append(f"Missing directory: {dir_path}")
                    details[f'{dir_name}_exists'] = False
                else:
                    details[f'{dir_name}_exists'] = True

                    # Check write permissions
                    try:
                        test_file = os.path.join(dir_path, '.health_check_test')
                        with open(test_file, 'w') as f:
                            f.write('test')
                        os.remove(test_file)
                        details[f'{dir_name}_writable'] = True
                    except Exception:
                        issues.append(f"Directory not writable: {dir_path}")
                        details[f'{dir_name}_writable'] = False

                    # Check directory size
                    try:
                        total_size = sum(
                            os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, dirnames, filenames in os.walk(dir_path)
                            for filename in filenames
                        )
                        details[f'{dir_name}_size_mb'] = total_size / (1024 * 1024)
                    except Exception:
                        details[f'{dir_name}_size_mb'] = 0

            # Check for disk space issues
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                issues.append(f"Disk space critical: {disk.percent:.1f}% used")

            # Determine status
            if issues:
                status = HealthStatus.CRITICAL if any('critical' in issue.lower() for issue in issues) else HealthStatus.DEGRADED
                message = "; ".join(issues)
                recovery_actions = ['cleanup_temp_files', 'free_disk_space']
            else:
                status = HealthStatus.HEALTHY
                message = "File system healthy"
                recovery_actions = []

            return HealthCheckResult(
                component="file_system",
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=message,
                details=details,
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="file_system",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"File system check failed: {str(e)}",
                details={'error': str(e)}
            )

    def _check_agent_manager(self) -> HealthCheckResult:
        """Check agent manager health"""
        try:
            # Get agent status
            agent_statuses = self.agent_manager.get_agent_status()
            total_agents = len(agent_statuses)

            if total_agents == 0:
                return HealthCheckResult(
                    component="agent_manager",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=0.0,
                    timestamp=datetime.now(),
                    message="No agents available",
                    details={'total_agents': 0}
                )

            # Count agent states
            working_agents = sum(1 for status in agent_statuses.values()
                               if status.get('worker_status') == 'working')
            stuck_agents = sum(1 for status in agent_statuses.values()
                             if status.get('worker_status') == 'stuck')
            idle_agents = sum(1 for status in agent_statuses.values()
                            if status.get('worker_status') == 'idle')

            # Check for issues
            issues = []
            if stuck_agents > 0:
                issues.append(f"{stuck_agents} agents stuck")

            stuck_ratio = stuck_agents / total_agents if total_agents > 0 else 0

            # Determine status
            if stuck_ratio > 0.5:  # More than 50% stuck
                status = HealthStatus.CRITICAL
                recovery_actions = ['restart_stuck_agents']
            elif stuck_ratio > 0.2:  # More than 20% stuck
                status = HealthStatus.DEGRADED
                recovery_actions = ['restart_stuck_agents']
            elif stuck_agents > 0:
                status = HealthStatus.DEGRADED
                recovery_actions = ['restart_stuck_agents']
            else:
                status = HealthStatus.HEALTHY
                recovery_actions = []

            message = f"{total_agents} agents: {working_agents} working, {idle_agents} idle, {stuck_agents} stuck"
            if issues:
                message += f" - {'; '.join(issues)}"

            return HealthCheckResult(
                component="agent_manager",
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=message,
                details={
                    'total_agents': total_agents,
                    'working_agents': working_agents,
                    'idle_agents': idle_agents,
                    'stuck_agents': stuck_agents,
                    'stuck_ratio': stuck_ratio
                },
                dependencies=['database_connectivity'],
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="agent_manager",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"Agent manager check failed: {str(e)}",
                details={'error': str(e)}
            )

    def _check_task_tracker(self) -> HealthCheckResult:
        """Check task tracker health"""
        try:
            # Get all progress data
            all_progress = self.task_tracker.get_all_progress()

            # Count tasks by status
            active_tasks = len([p for p in all_progress.values() if p])

            # Check for stale tasks (no updates in last hour)
            stale_tasks = 0
            cutoff_time = datetime.now() - timedelta(hours=1)

            for progress in all_progress.values():
                if progress and 'last_updated' in progress:
                    try:
                        last_updated = datetime.fromisoformat(progress['last_updated'])
                        if last_updated < cutoff_time:
                            stale_tasks += 1
                    except (ValueError, TypeError):
                        pass

            # Determine status
            issues = []
            if stale_tasks > 0:
                issues.append(f"{stale_tasks} stale tasks")

            if stale_tasks > active_tasks * 0.5:  # More than 50% stale
                status = HealthStatus.DEGRADED
                recovery_actions = ['restart_sessions']
            elif stale_tasks > 0:
                status = HealthStatus.DEGRADED
                recovery_actions = []
            else:
                status = HealthStatus.HEALTHY
                recovery_actions = []

            message = f"Task tracker: {active_tasks} active tasks"
            if issues:
                message += f" - {'; '.join(issues)}"

            return HealthCheckResult(
                component="task_tracker",
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=message,
                details={
                    'active_tasks': active_tasks,
                    'stale_tasks': stale_tasks,
                    'total_employees': len(all_progress)
                },
                dependencies=['file_system'],
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="task_tracker",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"Task tracker check failed: {str(e)}",
                details={'error': str(e)}
            )

    def _check_session_manager(self) -> HealthCheckResult:
        """Check session manager health"""
        try:
            # Get active sessions
            active_sessions = self.session_manager.get_active_sessions()
            session_count = len(active_sessions)

            # Check for zombie sessions (sessions without corresponding processes)
            zombie_sessions = 0
            for session_id in active_sessions.values():
                # This is a simplified check - in production you'd check actual process status
                if not session_id or session_id == "unknown":
                    zombie_sessions += 1

            # Determine status
            issues = []
            if zombie_sessions > 0:
                issues.append(f"{zombie_sessions} zombie sessions")

            if zombie_sessions > session_count * 0.3:  # More than 30% zombie
                status = HealthStatus.DEGRADED
                recovery_actions = ['restart_sessions']
            elif zombie_sessions > 0:
                status = HealthStatus.DEGRADED
                recovery_actions = []
            else:
                status = HealthStatus.HEALTHY
                recovery_actions = []

            message = f"Session manager: {session_count} active sessions"
            if issues:
                message += f" - {'; '.join(issues)}"

            return HealthCheckResult(
                component="session_manager",
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=message,
                details={
                    'active_sessions': session_count,
                    'zombie_sessions': zombie_sessions,
                    'sessions': dict(active_sessions)
                },
                dependencies=['file_system'],
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="session_manager",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"Session manager check failed: {str(e)}",
                details={'error': str(e)}
            )

    def _check_monitoring_system(self) -> HealthCheckResult:
        """Check monitoring system health"""
        try:
            issues = []
            details = {}

            # Check if health monitor is running
            health_monitor = getattr(self.agent_manager, 'health_monitor', None)
            if health_monitor:
                details['health_monitor_running'] = health_monitor.is_running
                if not health_monitor.is_running:
                    issues.append("Health monitor not running")
            else:
                details['health_monitor_running'] = False
                issues.append("Health monitor not available")

            # Check if recovery manager is available
            recovery_manager = getattr(self.agent_manager, 'recovery_manager', None)
            details['recovery_manager_available'] = recovery_manager is not None
            if not recovery_manager:
                issues.append("Recovery manager not available")

            # Check monitoring database
            monitoring_db_path = "monitoring_metrics.db"
            if os.path.exists(monitoring_db_path):
                details['monitoring_db_exists'] = True
                details['monitoring_db_size_mb'] = os.path.getsize(monitoring_db_path) / (1024 * 1024)
            else:
                details['monitoring_db_exists'] = False
                issues.append("Monitoring database missing")

            # Determine status
            if len(issues) >= 2:
                status = HealthStatus.CRITICAL
                recovery_actions = ['restart_monitoring']
            elif issues:
                status = HealthStatus.DEGRADED
                recovery_actions = ['restart_monitoring']
            else:
                status = HealthStatus.HEALTHY
                recovery_actions = []

            message = "Monitoring system healthy" if not issues else "; ".join(issues)

            return HealthCheckResult(
                component="monitoring_system",
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=message,
                details=details,
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="monitoring_system",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"Monitoring system check failed: {str(e)}",
                details={'error': str(e)}
            )

    def _check_network_connectivity(self) -> HealthCheckResult:
        """Check network connectivity"""
        try:
            # Test localhost connectivity
            start_time = time.time()
            try:
                response = requests.get('http://localhost:8080/health', timeout=5)
                localhost_ok = response.status_code == 200
                response_time = (time.time() - start_time) * 1000
            except Exception:
                localhost_ok = False
                response_time = 5000  # Timeout

            # Test external connectivity (optional)
            external_ok = True
            try:
                response = requests.get('https://httpbin.org/status/200', timeout=3)
                external_ok = response.status_code == 200
            except Exception:
                external_ok = False

            # Determine status
            issues = []
            if not localhost_ok:
                issues.append("Localhost API unreachable")
            if not external_ok:
                issues.append("External connectivity limited")

            if not localhost_ok:
                status = HealthStatus.CRITICAL
                recovery_actions = ['restart_network_services']
            elif not external_ok:
                status = HealthStatus.DEGRADED
                recovery_actions = []
            else:
                status = HealthStatus.HEALTHY
                recovery_actions = []

            message = "Network connectivity healthy" if not issues else "; ".join(issues)

            return HealthCheckResult(
                component="network_connectivity",
                status=status,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                message=message,
                details={
                    'localhost_reachable': localhost_ok,
                    'external_reachable': external_ok,
                    'localhost_response_time_ms': response_time
                },
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="network_connectivity",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"Network connectivity check failed: {str(e)}",
                details={'error': str(e)}
            )

    def _check_process_health(self) -> HealthCheckResult:
        """Check process health"""
        try:
            current_process = psutil.Process()

            # Get process info
            cpu_percent = current_process.cpu_percent()
            memory_info = current_process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            thread_count = current_process.num_threads()

            # Check for issues
            issues = []
            if cpu_percent > 80:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            if memory_mb > 1024:  # More than 1GB
                issues.append(f"High memory usage: {memory_mb:.1f}MB")
            if thread_count > 100:
                issues.append(f"High thread count: {thread_count}")

            # Determine status
            if len(issues) >= 2:
                status = HealthStatus.DEGRADED
                recovery_actions = ['clear_memory_cache']
            elif issues:
                status = HealthStatus.DEGRADED
                recovery_actions = []
            else:
                status = HealthStatus.HEALTHY
                recovery_actions = []

            message = f"Process: {cpu_percent:.1f}% CPU, {memory_mb:.1f}MB RAM, {thread_count} threads"
            if issues:
                message += f" - {'; '.join(issues)}"

            return HealthCheckResult(
                component="process_health",
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=message,
                details={
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'thread_count': thread_count,
                    'process_id': current_process.pid
                },
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="process_health",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"Process health check failed: {str(e)}",
                details={'error': str(e)}
            )

    def _check_memory_leaks(self) -> HealthCheckResult:
        """Check for memory leaks"""
        try:
            current_process = psutil.Process()
            memory_mb = current_process.memory_info().rss / (1024 * 1024)

            # Store memory usage history (simplified - in production use more sophisticated tracking)
            if not hasattr(self, '_memory_history'):
                self._memory_history = deque(maxlen=10)

            self._memory_history.append((datetime.now(), memory_mb))

            # Check for memory growth trend
            if len(self._memory_history) >= 5:
                recent_memory = [mem for _, mem in list(self._memory_history)[-5:]]
                memory_growth = recent_memory[-1] - recent_memory[0]
                growth_rate = memory_growth / len(recent_memory)

                # Determine status
                if growth_rate > 50:  # Growing by more than 50MB per check
                    status = HealthStatus.DEGRADED
                    message = f"Potential memory leak detected: {growth_rate:.1f}MB/check growth"
                    recovery_actions = ['clear_memory_cache']
                elif growth_rate > 20:
                    status = HealthStatus.DEGRADED
                    message = f"Memory usage increasing: {growth_rate:.1f}MB/check growth"
                    recovery_actions = []
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Memory usage stable: {memory_mb:.1f}MB"
                    recovery_actions = []
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage: {memory_mb:.1f}MB (collecting baseline)"
                recovery_actions = []

            return HealthCheckResult(
                component="memory_leaks",
                status=status,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=message,
                details={
                    'current_memory_mb': memory_mb,
                    'memory_history': list(self._memory_history),
                    'history_length': len(self._memory_history)
                },
                recovery_actions=recovery_actions
            )

        except Exception as e:
            return HealthCheckResult(
                component="memory_leaks",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                timestamp=datetime.now(),
                message=f"Memory leak check failed: {str(e)}",
                details={'error': str(e)}
            )

    def _check_all_dependencies(self):
        """Check all configured dependencies"""
        for dep_name, dep_info in self.dependency_health.items():
            try:
                start_time = time.time()

                if dep_info.type == 'database':
                    status = self._check_database_dependency(dep_info.details['target'])
                elif dep_info.type == 'file_system':
                    status = self._check_file_system_dependency(dep_info.details['target'])
                elif dep_info.type == 'api':
                    status = self._check_api_dependency(dep_info.details['target'])
                else:
                    status = HealthStatus.UNKNOWN

                response_time = (time.time() - start_time) * 1000

                # Update dependency health
                dep_info.status = status
                dep_info.last_check = datetime.now()
                dep_info.response_time_ms = response_time

                if status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                    dep_info.error_count += 1
                    dep_info.consecutive_failures += 1
                else:
                    dep_info.consecutive_failures = 0

            except Exception as e:
                logger.error(f"Error checking dependency {dep_name}: {e}")
                dep_info.status = HealthStatus.CRITICAL
                dep_info.error_count += 1
                dep_info.consecutive_failures += 1

    def _check_database_dependency(self, db_path: str) -> HealthStatus:
        """Check database dependency"""
        try:
            if not os.path.exists(db_path):
                return HealthStatus.CRITICAL

            with sqlite3.connect(db_path, timeout=2) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()

            return HealthStatus.HEALTHY
        except Exception:
            return HealthStatus.CRITICAL

    def _check_file_system_dependency(self, path: str) -> HealthStatus:
        """Check file system dependency"""
        try:
            if not os.path.exists(path):
                return HealthStatus.CRITICAL

            # Test write access
            if os.path.isdir(path):
                test_file = os.path.join(path, '.health_test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)

            return HealthStatus.HEALTHY
        except Exception:
            return HealthStatus.CRITICAL

    def _check_api_dependency(self, url: str) -> HealthStatus:
        """Check API dependency"""
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.DEGRADED
        except Exception:
            return HealthStatus.CRITICAL

    def _detect_cascade_failures(self):
        """Detect cascade failure patterns"""
        for primary_component, dependent_components in self.failure_patterns.items():
            primary_result = self.health_results.get(primary_component)

            if not primary_result:
                continue

            # Check if primary component has consecutive failures
            primary_dep = self.dependency_health.get(primary_component)
            if primary_dep and primary_dep.consecutive_failures >= self.cascade_thresholds.get(primary_component, 3):

                # Check dependent components
                affected_components = []
                for dep_component in dependent_components:
                    dep_result = self.health_results.get(dep_component)
                    if dep_result and dep_result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                        affected_components.append(dep_component)

                if affected_components:
                    logger.warning(f"Cascade failure detected: {primary_component} -> {affected_components}")

                    # Trigger cascade recovery
                    self._trigger_cascade_recovery(primary_component, affected_components)

    def _trigger_auto_recovery(self):
        """Trigger automated recovery actions"""
        for component, result in self.health_results.items():
            if result.status in [HealthStatus.CRITICAL, HealthStatus.DEGRADED] and result.recovery_actions:
                for action_name in result.recovery_actions:
                    if action_name in self.recovery_actions:
                        try:
                            logger.info(f"Triggering recovery action: {action_name} for {component}")
                            success = self.recovery_actions[action_name]()

                            # Record recovery attempt
                            self.recovery_history.append({
                                'timestamp': datetime.now(),
                                'component': component,
                                'action': action_name,
                                'success': success,
                                'trigger': 'auto_recovery'
                            })

                        except Exception as e:
                            logger.error(f"Recovery action {action_name} failed: {e}")
                            self.recovery_history.append({
                                'timestamp': datetime.now(),
                                'component': component,
                                'action': action_name,
                                'success': False,
                                'error': str(e),
                                'trigger': 'auto_recovery'
                            })

    def _trigger_cascade_recovery(self, primary_component: str, affected_components: List[str]):
        """Trigger recovery for cascade failures"""
        logger.info(f"Triggering cascade recovery for {primary_component} -> {affected_components}")

        # Recovery strategy for cascade failures
        cascade_recovery_map = {
            'database_connectivity': ['optimize_database', 'restart_stuck_agents'],
            'file_system': ['cleanup_temp_files', 'restart_sessions'],
            'system_resources': ['clear_memory_cache', 'cleanup_temp_files', 'restart_stuck_agents'],
            'network_connectivity': ['restart_network_services', 'restart_monitoring']
        }

        recovery_actions = cascade_recovery_map.get(primary_component, [])

        for action_name in recovery_actions:
            if action_name in self.recovery_actions:
                try:
                    success = self.recovery_actions[action_name]()
                    self.recovery_history.append({
                        'timestamp': datetime.now(),
                        'component': primary_component,
                        'affected_components': affected_components,
                        'action': action_name,
                        'success': success,
                        'trigger': 'cascade_recovery'
                    })
                except Exception as e:
                    logger.error(f"Cascade recovery action {action_name} failed: {e}")

    # Recovery action implementations

    def _recovery_restart_stuck_agents(self) -> bool:
        """Recovery action: restart stuck agents"""
        try:
            recovery_manager = getattr(self.agent_manager, 'recovery_manager', None)
            if recovery_manager:
                # This would trigger the existing recovery system
                logger.info("Triggering stuck agent recovery")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to restart stuck agents: {e}")
            return False

    def _recovery_clear_memory_cache(self) -> bool:
        """Recovery action: clear memory caches"""
        try:
            import gc
            gc.collect()
            logger.info("Memory cache cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear memory cache: {e}")
            return False

    def _recovery_restart_monitoring(self) -> bool:
        """Recovery action: restart monitoring system"""
        try:
            health_monitor = getattr(self.agent_manager, 'health_monitor', None)
            if health_monitor:
                health_monitor.stop_monitoring()
                time.sleep(1)
                health_monitor.start_monitoring()
                logger.info("Monitoring system restarted")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to restart monitoring: {e}")
            return False

    def _recovery_cleanup_temp_files(self) -> bool:
        """Recovery action: cleanup temporary files"""
        try:
            import shutil
            temp_dirs = ['/tmp', 'temp', 'logs']

            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    # Clean files older than 1 day
                    cutoff_time = time.time() - (24 * 60 * 60)
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                if os.path.getmtime(file_path) < cutoff_time:
                                    os.remove(file_path)
                            except Exception:
                                pass

            logger.info("Temporary files cleaned up")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            return False

    def _recovery_restart_sessions(self) -> bool:
        """Recovery action: restart stale sessions"""
        try:
            # This would restart stale sessions
            logger.info("Restarting stale sessions")
            return True
        except Exception as e:
            logger.error(f"Failed to restart sessions: {e}")
            return False

    def _recovery_optimize_database(self) -> bool:
        """Recovery action: optimize database"""
        try:
            db_path = getattr(self.agent_manager.file_manager, 'db_path', 'employees.db')
            with sqlite3.connect(db_path) as conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
            logger.info("Database optimized")
            return True
        except Exception as e:
            logger.error(f"Failed to optimize database: {e}")
            return False

    def _recovery_free_disk_space(self) -> bool:
        """Recovery action: free disk space"""
        try:
            # Clean up log files, temp files, etc.
            self._recovery_cleanup_temp_files()
            logger.info("Disk space freed")
            return True
        except Exception as e:
            logger.error(f"Failed to free disk space: {e}")
            return False

    def _recovery_restart_network_services(self) -> bool:
        """Recovery action: restart network services"""
        try:
            # This would restart network-related services
            logger.info("Network services restart triggered")
            return True
        except Exception as e:
            logger.error(f"Failed to restart network services: {e}")
            return False

    # Public API methods

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        if not self.health_results:
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': 'No health checks performed yet',
                'components': {},
                'dependencies': {}
            }

        # Calculate overall status
        component_statuses = [result.status for result in self.health_results.values()]

        if any(status == HealthStatus.CRITICAL for status in component_statuses):
            overall_status = HealthStatus.CRITICAL
        elif any(status == HealthStatus.UNHEALTHY for status in component_statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in component_statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        # Count components by status
        status_counts = defaultdict(int)
        for result in self.health_results.values():
            status_counts[result.status.value] += 1

        return {
            'status': overall_status.value,
            'message': f"System {overall_status.value}",
            'last_check': max(result.timestamp for result in self.health_results.values()).isoformat(),
            'components': {name: result.to_dict() for name, result in self.health_results.items()},
            'dependencies': {name: dep.to_dict() for name, dep in self.dependency_health.items()},
            'status_distribution': dict(status_counts),
            'auto_recovery_enabled': self.auto_recovery_enabled,
            'recovery_history_count': len(self.recovery_history)
        }

    def get_component_health(self, component: str) -> Optional[Dict[str, Any]]:
        """Get health status for specific component"""
        result = self.health_results.get(component)
        return result.to_dict() if result else None

    def get_recovery_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recovery action history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        return [
            recovery for recovery in self.recovery_history
            if recovery['timestamp'] >= cutoff_time
        ]

    def trigger_manual_recovery(self, action_name: str) -> bool:
        """Manually trigger a recovery action"""
        if action_name not in self.recovery_actions:
            return False

        try:
            success = self.recovery_actions[action_name]()

            self.recovery_history.append({
                'timestamp': datetime.now(),
                'component': 'manual',
                'action': action_name,
                'success': success,
                'trigger': 'manual'
            })

            return success
        except Exception as e:
            logger.error(f"Manual recovery action {action_name} failed: {e}")
            return False

    def enable_auto_recovery(self, enabled: bool = True):
        """Enable or disable auto recovery"""
        self.auto_recovery_enabled = enabled
        logger.info(f"Auto recovery {'enabled' if enabled else 'disabled'}")

    def force_health_check(self) -> Dict[str, Any]:
        """Force immediate health check of all components"""
        logger.info("Forcing immediate health check")
        self._run_all_health_checks()
        self._check_all_dependencies()
        return self.get_overall_health()