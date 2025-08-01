"""
Agent Recovery Manager for the OpenCode-Slack system.
Handles automatic recovery of stuck or unresponsive agents.
"""

import logging
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta

from src.agents.agent_manager import AgentManager
from src.utils.opencode_wrapper import OpencodeSessionManager

logger = logging.getLogger(__name__)


class AgentRecoveryManager:
    """Manages recovery of stuck or unresponsive agents"""
    
    def __init__(self, agent_manager: AgentManager, session_manager: OpencodeSessionManager):
        """
        Initialize the agent recovery manager
        
        Args:
            agent_manager: The agent manager instance
            session_manager: The opencode session manager instance
        """
        self.agent_manager = agent_manager
        self.session_manager = session_manager
        self.recovery_actions: Dict[str, List[Dict[str, Any]]] = {}
        self.escalation_callback: Optional[Callable] = None
        
        logger.info("AgentRecoveryManager initialized")
    
    def set_escalation_callback(self, callback: Callable):
        """
        Set callback function for escalation when automatic recovery fails
        
        Args:
            callback: Function to call when escalation is needed
        """
        self.escalation_callback = callback
        logger.info("Escalation callback set")
    
    def handle_agent_anomaly(self, agent_name: str, anomalies: List[str], status_record: Dict[str, Any]):
        """
        Handle detected agent anomalies
        
        Args:
            agent_name: Name of the agent with anomalies
            anomalies: List of detected anomalies
            status_record: Current status record of the agent
        """
        logger.info(f"Handling anomalies for agent {agent_name}: {anomalies}")
        
        # Record the recovery attempt
        if agent_name not in self.recovery_actions:
            self.recovery_actions[agent_name] = []
        
        recovery_record = {
            'timestamp': datetime.now(),
            'anomalies': anomalies,
            'action_taken': None,
            'success': False,
            'notes': ''
        }
        
        # Try different recovery actions based on anomalies
        if "STUCK_STATE" in anomalies or "WORKER_STUCK" in anomalies:
            success = self._restart_stuck_agent(agent_name)
            recovery_record['action_taken'] = 'RESTART_AGENT'
            recovery_record['success'] = success
            recovery_record['notes'] = 'Agent restarted due to stuck state' if success else 'Agent restart failed'
            
        elif "PROGRESS_STAGNANT" in anomalies:
            success = self._notify_agent_to_continue(agent_name, status_record)
            recovery_record['action_taken'] = 'NOTIFY_CONTINUE'
            recovery_record['success'] = success
            recovery_record['notes'] = 'Agent notified to continue work' if success else 'Notification failed'
        
        # If recovery failed, escalate
        if not recovery_record['success'] and self.escalation_callback:
            try:
                self.escalation_callback(agent_name, anomalies, recovery_record)
                recovery_record['notes'] += '; Escalated to operator'
            except Exception as e:
                logger.error(f"Error in escalation callback for {agent_name}: {e}")
        
        # Store recovery record
        self.recovery_actions[agent_name].append(recovery_record)
        
        # Keep only last 5 recovery records per agent
        if len(self.recovery_actions[agent_name]) > 5:
            self.recovery_actions[agent_name] = self.recovery_actions[agent_name][-5:]
        
        logger.info(f"Recovery action for {agent_name}: {recovery_record}")
    
    def _restart_stuck_agent(self, agent_name: str) -> bool:
        """
        Restart a stuck agent
        
        Args:
            agent_name: Name of the agent to restart
            
        Returns:
            True if restart was successful, False otherwise
        """
        try:
            logger.info(f"Attempting to restart agent {agent_name}")
            
            # Stop current session if active
            active_sessions = self.session_manager.get_active_sessions()
            if agent_name in active_sessions:
                logger.info(f"Stopping active session for {agent_name}")
                self.session_manager.stop_employee_task(agent_name)
                time.sleep(1)  # Brief pause to ensure session is stopped
            
            # Restart the agent's task if it had one
            agent_status = self.agent_manager.get_agent_status(agent_name)
            if agent_status and agent_status.get('current_task'):
                task_description = agent_status['current_task']
                logger.info(f"Restarting task for {agent_name}: {task_description}")
                
                # Start new session with same task
                session_id = self.session_manager.start_employee_task(
                    agent_name, task_description
                )
                
                if session_id:
                    logger.info(f"Successfully restarted agent {agent_name} with new session {session_id}")
                    return True
                else:
                    logger.error(f"Failed to start new session for agent {agent_name}")
                    return False
            else:
                logger.info(f"No active task for agent {agent_name}, marking as recovered")
                return True
                
        except Exception as e:
            logger.error(f"Error restarting agent {agent_name}: {e}")
            return False
    
    def _notify_agent_to_continue(self, agent_name: str, status_record: Dict[str, Any]) -> bool:
        """
        Notify an agent to continue its work
        
        Args:
            agent_name: Name of the agent to notify
            status_record: Current status record of the agent
            
        Returns:
            True if notification was successful, False otherwise
        """
        try:
            logger.info(f"Notifying agent {agent_name} to continue work")
            
            # Get the agent instance
            agent = self.agent_manager.agents.get(agent_name)
            if not agent:
                logger.error(f"Agent {agent_name} not found")
                return False
            
            # Get current task information
            current_task = status_record['status'].get('current_task')
            task_progress = status_record.get('task_progress', {})
            
            if current_task:
                # Create a notification message
                progress_info = task_progress.get('current_work', 'unknown progress')
                notification_message = (
                    f"Hey {agent_name}, I noticed you might be stuck. "
                    f"Your task is: {current_task}. "
                    f"Current progress: {progress_info}. "
                    f"Please continue with your work or let me know if you need help."
                )
                
                # TODO: Actually send this message through the chat system
                # For now, we'll just log it
                logger.info(f"Notification message for {agent_name}: {notification_message}")
                
                # Update agent's last response time to prevent immediate re-detection
                agent.last_response_time = datetime.now()
                
                return True
            else:
                logger.warning(f"No current task found for agent {agent_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error notifying agent {agent_name}: {e}")
            return False
    
    def get_recovery_history(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get recovery history for agents
        
        Args:
            agent_name: Specific agent name to get history for, or None for all
            
        Returns:
            Dictionary with recovery history information
        """
        if agent_name:
            return {agent_name: self.recovery_actions.get(agent_name, [])}
        else:
            return self.recovery_actions
    
    def get_recovery_summary(self) -> Dict[str, Any]:
        """
        Get a summary of recovery actions taken
        
        Returns:
            Dictionary with recovery summary information
        """
        summary = {
            'total_recovery_attempts': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'escalations': 0,
            'agent_recovery_counts': {}
        }
        
        try:
            for agent_name, actions in self.recovery_actions.items():
                summary['agent_recovery_counts'][agent_name] = len(actions)
                summary['total_recovery_attempts'] += len(actions)
                
                for action in actions:
                    if action['success']:
                        summary['successful_recoveries'] += 1
                    else:
                        summary['failed_recoveries'] += 1
                    
                    if 'Escalated' in action.get('notes', ''):
                        summary['escalations'] += 1
                        
        except Exception as e:
            logger.error(f"Error generating recovery summary: {e}")
            summary['error'] = str(e)
        
        return summary