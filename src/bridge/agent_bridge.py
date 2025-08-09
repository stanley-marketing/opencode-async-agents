"""
Agent bridge for connecting communication and worker agents.
Handles task assignment, progress updates, and help coordination.
"""

import logging
import threading
import time
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta

from src.utils.opencode_wrapper import OpencodeSessionManager
from src.agents.agent_manager import AgentManager

logger = logging.getLogger(__name__)

class AgentBridge:
    """Bridges communication agents with worker agents"""
    
    def __init__(self, session_manager: OpencodeSessionManager, agent_manager: AgentManager):
        self.session_manager = session_manager
        self.agent_manager = agent_manager
        
        # Task tracking
        self.active_tasks: Dict[str, Dict] = {}  # employee_name -> task_info
        self.stuck_timers: Dict[str, threading.Timer] = {}
        
        # Set up callbacks
        self._setup_agent_callbacks()
        
        logger.info("Agent bridge initialized")
    
    def _setup_agent_callbacks(self):
        """Set up callbacks between communication and worker agents"""
        
        # Update agent manager callbacks
        for employee_name, comm_agent in self.agent_manager.agents.items():
            self._setup_agent_callback(employee_name, comm_agent)
    
    def _setup_agent_callback(self, employee_name: str, comm_agent):
        """Set up callback for a specific agent"""
        # Use default argument trick to capture employee_name properly
        comm_agent.on_task_assigned = (lambda emp: lambda task: self.assign_task_to_worker(emp, task))(employee_name)
        comm_agent.on_help_received = (lambda emp: lambda help_text: self.provide_help_to_worker(emp, help_text))(employee_name)
    
    def assign_task_to_worker(self, employee_name: str, task_description: str) -> bool:
        """Assign a task from communication agent to worker agent"""
        
        logger.info(f"Assigning task to worker {employee_name}: {task_description}")
        
        # CRITICAL FIX: Ensure employee exists in file manager
        employees = self.session_manager.file_manager.list_employees()
        employee_names = [emp['name'] for emp in employees]
        
        if employee_name not in employee_names:
            logger.error(f"Employee {employee_name} not found in file manager")
            return False
        
        # Check if employee is available
        if not self.agent_manager.is_agent_available(employee_name):
            logger.warning(f"Employee {employee_name} is not available for new tasks")
            return False
        
        # CRITICAL FIX: Ensure agent exists for this employee
        if employee_name not in self.agent_manager.agents:
            logger.warning(f"No agent found for {employee_name}, creating one")
            employee_info = next(emp for emp in employees if emp['name'] == employee_name)
            expertise = self.agent_manager._get_expertise_for_role(employee_info['role'])
            self.agent_manager.create_agent(employee_name, employee_info['role'], expertise)
        
        # Start the worker session
        session_id = self.session_manager.start_employee_task(
            employee_name, task_description, model=None, mode="build"
        )
        
        if not session_id:
            logger.error(f"Failed to start worker session for {employee_name}")
            return False
        
        # Track the task
        task_info = {
            'session_id': session_id,
            'task_description': task_description,
            'started_at': datetime.now(),
            'status': 'working',
            'progress': '',
        }
        
        self.active_tasks[employee_name] = task_info
        
        # Set up stuck detection timer
        self._setup_stuck_timer(employee_name)
        
        logger.info(f"Task assigned successfully to {employee_name}")
        return True
    
    def _setup_stuck_timer(self, employee_name: str):
        """Set up a timer to detect if worker gets stuck"""
        
        # Cancel existing timer if any
        if employee_name in self.stuck_timers:
            self.stuck_timers[employee_name].cancel()
        
        # Create new timer (10 minutes)
        timer = threading.Timer(600.0, self._handle_worker_stuck, args=[employee_name])
        timer.daemon = True
        timer.start()
        
        self.stuck_timers[employee_name] = timer
        logger.debug(f"Stuck timer set for {employee_name}")
    
    def _handle_worker_stuck(self, employee_name: str):
        """Handle when a worker appears to be stuck"""
        
        if employee_name not in self.active_tasks:
            return
        
        task_info = self.active_tasks[employee_name]
        
        # Check if task is still active
        active_sessions = self.session_manager.get_active_sessions()
        if employee_name not in active_sessions:
            # Task completed, clean up
            self._cleanup_task(employee_name)
            return
        
        session_info = active_sessions[employee_name]
        if not session_info['is_running']:
            # Task completed, clean up
            self._cleanup_task(employee_name)
            return
        
        logger.warning(f"Worker {employee_name} appears stuck on task: {task_info['task_description']}")
        
        # Get progress summary from task tracker
        progress = self.session_manager.task_tracker.get_task_progress(employee_name)
        progress_summary = self._summarize_progress(progress) if progress else "No progress information available"
        
        # Request help through communication agent
        success = self.agent_manager.request_help_for_agent(
            employee_name, 
            task_info['task_description'],
            progress_summary,
            "Taking longer than expected"
        )
        
        if success:
            task_info['status'] = 'stuck'
            task_info['stuck_at'] = datetime.now()
            logger.info(f"Help requested for stuck worker {employee_name}")
        else:
            logger.error(f"Failed to request help for {employee_name}")
    
    def _summarize_progress(self, progress: Dict) -> str:
        """Summarize worker progress for help requests"""
        
        if not progress:
            return "No progress data available"
        
        summary_parts = []
        
        # Overall progress
        if progress.get('overall_progress', 0) > 0:
            summary_parts.append(f"{progress['overall_progress']}% complete")
        
        # Files being worked on
        if progress.get('still_working_on'):
            files = ', '.join(progress['still_working_on'][:3])  # First 3 files
            summary_parts.append(f"working on {files}")
        
        # Current work
        if progress.get('current_work'):
            current = progress['current_work'][:100]  # First 100 chars
            summary_parts.append(f"currently: {current}")
        
        return '; '.join(summary_parts) if summary_parts else "Started task but no specific progress recorded"
    
    def provide_help_to_worker(self, employee_name: str, help_text: str):
        """Provide help text to a stuck worker"""
        
        if employee_name not in self.active_tasks:
            logger.warning(f"No active task found for {employee_name}")
            return
        
        logger.info(f"Providing help to worker {employee_name}")
        
        # Update task tracker with help received
        self.session_manager.task_tracker.update_current_work(
            employee_name, 
            f"📬 Received help from team: {help_text[:100]}..."
        )
        
        # Reset stuck timer - give more time after receiving help
        self._setup_stuck_timer(employee_name)
        
        # Update task status
        task_info = self.active_tasks[employee_name]
        task_info['status'] = 'working'
        task_info['help_received'] = help_text
        task_info['help_received_at'] = datetime.now()
    
    def check_task_completion(self):
        """Check for completed tasks and notify communication agents"""
        
        active_sessions = self.session_manager.get_active_sessions()
        completed_employees = []
        
        for employee_name, task_info in self.active_tasks.items():
            # Check if session is no longer active (completed)
            if employee_name not in active_sessions:
                completed_employees.append(employee_name)
                continue
            
            session_info = active_sessions[employee_name]
            if not session_info['is_running']:
                completed_employees.append(employee_name)
        
        # Handle completed tasks
        for employee_name in completed_employees:
            self._handle_task_completion(employee_name)
    
    def _handle_task_completion(self, employee_name: str):
        """Handle when a worker completes a task"""
        
        if employee_name not in self.active_tasks:
            return
        
        task_info = self.active_tasks[employee_name]
        task_description = task_info['task_description']
        
        logger.info(f"Task completed by {employee_name}: {task_description}")
        
        # Notify communication agent
        success = self.agent_manager.notify_task_completion(employee_name, task_description)
        
        if success:
            logger.info(f"Task completion announced for {employee_name}")
        else:
            logger.error(f"Failed to announce completion for {employee_name}")
        
        # Clean up
        self._cleanup_task(employee_name)
    
    def _cleanup_task(self, employee_name: str):
        """Clean up task tracking for an employee"""
        
        # Cancel stuck timer
        if employee_name in self.stuck_timers:
            self.stuck_timers[employee_name].cancel()
            del self.stuck_timers[employee_name]
        
        # Remove task tracking
        if employee_name in self.active_tasks:
            del self.active_tasks[employee_name]
        
        logger.debug(f"Task cleanup completed for {employee_name}")
    
    def get_bridge_status(self) -> Dict:
        """Get status of the bridge system"""
        
        return {
            'active_tasks': len(self.active_tasks),
            'stuck_timers': len(self.stuck_timers),
            'tasks': {
                name: {
                    'task': info['task_description'][:50] + '...' if len(info['task_description']) > 50 else info['task_description'],
                    'status': info['status'],
                    'started_at': info['started_at'].isoformat(),
                    'duration_minutes': (datetime.now() - info['started_at']).total_seconds() / 60,
                }
                for name, info in self.active_tasks.items()
            }
        }
    
    def start_monitoring(self):
        """Start background monitoring for task completion"""
        
        def monitor_loop():
            while True:
                try:
                    self.check_task_completion()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(60)  # Wait longer on error
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        logger.info("Bridge monitoring started")
    
    def stop_all_tasks(self):
        """Stop all active tasks and clean up"""
        
        for employee_name in list(self.active_tasks.keys()):
            self.session_manager.stop_employee_task(employee_name)
            self._cleanup_task(employee_name)
        
        logger.info("All tasks stopped and cleaned up")