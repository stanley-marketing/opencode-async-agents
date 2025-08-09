"""
Agent Health Monitor for the OpenCode-Slack system.
Monitors agent status and detects anomalies like stuck states or infinite loops.
"""

from datetime import datetime, timedelta
from src.agents.agent_manager import AgentManager
from src.trackers.task_progress import TaskProgressTracker
from typing import Dict, List, Optional, Callable, Any
import logging
import threading
import time

logger = logging.getLogger(__name__)


class AgentHealthMonitor:
    """Monitors agent health and detects anomalies"""

    def __init__(self, agent_manager: AgentManager, task_tracker: TaskProgressTracker,
                 polling_interval: int = 30):
        """
        Initialize the agent health monitor

        Args:
            agent_manager: The agent manager instance to monitor
            task_tracker: The task progress tracker instance
            polling_interval: How often to check agent status in seconds (default: 30)
        """
        self.agent_manager = agent_manager
        self.task_tracker = task_tracker
        self.polling_interval = polling_interval
        self.is_running = False
        self.monitor_thread = None
        self.anomaly_callback = None
        self.agent_history: Dict[str, List[Dict[str, Any]]] = {}

        logger.info(f"AgentHealthMonitor initialized with {polling_interval}s polling interval")

    def start_monitoring(self, anomaly_callback: Optional[Callable] = None):
        """
        Start the monitoring service

        Args:
            anomaly_callback: Function to call when anomalies are detected
        """
        if self.is_running:
            logger.warning("Health monitor is already running")
            return

        self.anomaly_callback = anomaly_callback
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("Agent health monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring service"""
        if not self.is_running:
            logger.warning("Health monitor is not running")
            return

        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)  # Wait up to 5 seconds for thread to finish

        logger.info("Agent health monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting monitoring loop")

        while self.is_running:
            try:
                self._check_agent_health()
                time.sleep(self.polling_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.polling_interval)  # Continue monitoring even if error occurs

    def _check_agent_health(self):
        """Check the health of all agents"""
        try:
            # Get current agent statuses
            agent_statuses = self.agent_manager.get_agent_status()

            # Check each agent
            for agent_name, status in agent_statuses.items():
                self._check_single_agent_health(agent_name, status)

            logger.debug(f"Health check completed for {len(agent_statuses)} agents")

        except Exception as e:
            logger.error(f"Error checking agent health: {e}")

    def _check_single_agent_health(self, agent_name: str, status: Dict[str, Any]):
        """
        Check the health of a single agent

        Args:
            agent_name: Name of the agent
            status: Current status of the agent
        """
        # Validate status
        if not status or not isinstance(status, dict):
            logger.warning(f"Invalid status received for agent {agent_name}: {status}")
            return

        # Record current status in history
        if agent_name not in self.agent_history:
            self.agent_history[agent_name] = []

        status_record = {
            'timestamp': datetime.now(),
            'status': status,
            'task_progress': self.task_tracker.get_task_progress(agent_name)
        }

        self.agent_history[agent_name].append(status_record)

        # Keep only last 10 status records to prevent memory issues
        if len(self.agent_history[agent_name]) > 10:
            self.agent_history[agent_name] = self.agent_history[agent_name][-10:]

        # Check for anomalies
        anomalies = self._detect_anomalies(agent_name, status_record)

        if anomalies:
            logger.warning(f"Anomalies detected for agent {agent_name}: {anomalies}")

            # Call anomaly callback if provided
            if self.anomaly_callback:
                try:
                    self.anomaly_callback(agent_name, anomalies, status_record)
                except Exception as e:
                    logger.error(f"Error in anomaly callback for {agent_name}: {e}")

    def _detect_anomalies(self, agent_name: str, status_record: Dict[str, Any]) -> List[str]:
        """
        Detect anomalies in agent behavior

        Args:
            agent_name: Name of the agent
            status_record: Current status record

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Check if status is None or invalid
        status = status_record.get('status')
        if not status or not isinstance(status, dict):
            logger.warning(f"Invalid status for agent {agent_name}: {status}")
            return anomalies

        # Check if agent is stuck (same status for too long)
        if self._is_agent_stuck(agent_name, status_record):
            anomalies.append("STUCK_STATE")

        # Check if agent is not making progress on task
        if self._is_progress_stagnant(agent_name, status_record):
            anomalies.append("PROGRESS_STAGNANT")

        # Check if agent is in error state
        worker_status = status.get('worker_status', 'idle')
        if worker_status == 'stuck':
            anomalies.append("WORKER_STUCK")

        return anomalies

    def _is_agent_stuck(self, agent_name: str, status_record: Dict[str, Any]) -> bool:
        """
        Check if agent is stuck in the same state

        Args:
            agent_name: Name of the agent
            status_record: Current status record

        Returns:
            True if agent appears to be stuck
        """
        history = self.agent_history.get(agent_name, [])

        if len(history) < 3:
            return False  # Not enough history to determine if stuck

        # Check if last 3 statuses are identical
        last_status = history[-1].get('status')
        if not last_status or not isinstance(last_status, dict):
            return False  # Invalid status, can't determine if stuck

        for i in range(-2, -4, -1):
            if i < -len(history):
                break
            old_status = history[i].get('status')
            if not old_status or not isinstance(old_status, dict) or old_status != last_status:
                return False

        # If we get here, agent has been in same state for at least 3 checks
        time_diff = history[-1]['timestamp'] - history[-3]['timestamp']
        if time_diff > timedelta(minutes=2):  # Stuck for more than 2 minutes
            return True

        return False

    def _is_progress_stagnant(self, agent_name: str, status_record: Dict[str, Any]) -> bool:
        """
        Check if agent is not making progress on its task

        Args:
            agent_name: Name of the agent
            status_record: Current status record

        Returns:
            True if agent progress appears stagnant
        """
        task_progress = status_record.get('task_progress')
        if not task_progress:
            return False  # No task in progress

        history = self.agent_history.get(agent_name, [])
        if len(history) < 4:
            return False  # Not enough history to determine progress stagnation

        # Check if progress percentage hasn't changed in last 4 checks
        last_progress = task_progress.get('overall_progress', 0)
        for i in range(-2, -5, -1):
            if i < -len(history):
                break
            old_progress = history[i].get('task_progress', {}).get('overall_progress', 0)
            if old_progress != last_progress:
                return False  # Progress has changed, not stagnant

        # If we get here, progress hasn't changed for at least 4 checks
        time_diff = history[-1]['timestamp'] - history[-4]['timestamp']
        if time_diff > timedelta(minutes=5):  # No progress for more than 5 minutes
            return True

        return False

    def get_agent_health_summary(self) -> Dict[str, Any]:
        """
        Get a summary of agent health status

        Returns:
            Dictionary with health summary information
        """
        summary = {
            'total_agents': 0,
            'healthy_agents': 0,
            'stuck_agents': 0,
            'stagnant_agents': 0,
            'error_agents': 0,
            'agent_details': {}
        }

        try:
            agent_statuses = self.agent_manager.get_agent_status()
            summary['total_agents'] = len(agent_statuses)

            for agent_name, status in agent_statuses.items():
                worker_status = status.get('worker_status', 'idle')
                task_progress = self.task_tracker.get_task_progress(agent_name)

                agent_info = {
                    'worker_status': worker_status,
                    'current_task': status.get('current_task', 'None'),
                    'overall_progress': task_progress.get('overall_progress', 0) if task_progress else 0,
                    'health_status': 'HEALTHY'
                }

                # Determine health status
                if worker_status == 'stuck':
                    agent_info['health_status'] = 'ERROR'
                    summary['error_agents'] += 1
                elif self._is_agent_stuck(agent_name, {'status': status, 'timestamp': datetime.now(), 'task_progress': task_progress}):
                    agent_info['health_status'] = 'STUCK'
                    summary['stuck_agents'] += 1
                elif self._is_progress_stagnant(agent_name, {'status': status, 'timestamp': datetime.now(), 'task_progress': task_progress}):
                    agent_info['health_status'] = 'STAGNANT'
                    summary['stagnant_agents'] += 1
                else:
                    summary['healthy_agents'] += 1

                summary['agent_details'][agent_name] = agent_info

        except Exception as e:
            logger.error(f"Error generating health summary: {e}")
            summary['error'] = str(e)

        return summary