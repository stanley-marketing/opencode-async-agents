"""
Monitoring Dashboard for the OpenCode-Slack system.
Provides real-time view of agent status and health metrics.
"""

import logging
from typing import Dict, Any, Optional
import json
from datetime import datetime

from src.monitoring.agent_health_monitor import AgentHealthMonitor
from src.monitoring.agent_recovery_manager import AgentRecoveryManager

logger = logging.getLogger(__name__)


class MonitoringDashboard:
    """CLI dashboard for monitoring agent status and health"""
    
    def __init__(self, health_monitor: AgentHealthMonitor, recovery_manager: AgentRecoveryManager):
        """
        Initialize the monitoring dashboard
        
        Args:
            health_monitor: The agent health monitor instance
            recovery_manager: The agent recovery manager instance
        """
        self.health_monitor = health_monitor
        self.recovery_manager = recovery_manager
        
        logger.info("MonitoringDashboard initialized")
    
    def display_health_summary(self):
        """Display a summary of agent health status"""
        print("\n" + "="*80)
        print("AGENT HEALTH MONITORING DASHBOARD")
        print("="*80)
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # Get health summary
            health_summary = self.health_monitor.get_agent_health_summary()
            
            if 'error' in health_summary:
                print(f"ERROR: {health_summary['error']}")
                return
            
            # Display overall statistics
            print("OVERALL STATUS:")
            print(f"  Total Agents:     {health_summary['total_agents']}")
            print(f"  Healthy Agents:   {health_summary['healthy_agents']}")
            print(f"  Stuck Agents:      {health_summary['stuck_agents']}")
            print(f"  Stagnant Agents:   {health_summary['stagnant_agents']}")
            print(f"  Error Agents:      {health_summary['error_agents']}")
            print()
            
            # Display individual agent details
            print("AGENT DETAILS:")
            for agent_name, details in health_summary['agent_details'].items():
                health_indicator = "✓"  # Healthy
                if details['health_status'] == 'ERROR':
                    health_indicator = "✗"
                elif details['health_status'] == 'STUCK':
                    health_indicator = "⊘"
                elif details['health_status'] == 'STAGNANT':
                    health_indicator = "◐"
                
                print(f"  {health_indicator} {agent_name:<15} | "
                      f"Status: {details['worker_status']:<8} | "
                      f"Progress: {details['overall_progress']:>3}% | "
                      f"Task: {details['current_task'][:30]}{'...' if len(details['current_task']) > 30 else ''}")
            
            print()
            
            # Display recent recovery actions if any
            recovery_summary = self.recovery_manager.get_recovery_summary()
            if recovery_summary['total_recovery_attempts'] > 0:
                print("RECENT RECOVERY ACTIONS:")
                print(f"  Total Attempts:    {recovery_summary['total_recovery_attempts']}")
                print(f"  Successful:        {recovery_summary['successful_recoveries']}")
                print(f"  Failed:            {recovery_summary['failed_recoveries']}")
                print(f"  Escalations:       {recovery_summary['escalations']}")
                print()
                
        except Exception as e:
            print(f"ERROR displaying health summary: {e}")
            logger.error(f"Error displaying health summary: {e}")
    
    def display_agent_details(self, agent_name: str):
        """
        Display detailed information for a specific agent
        
        Args:
            agent_name: Name of the agent to display details for
        """
        print(f"\nAGENT DETAILS: {agent_name}")
        print("-" * 50)
        
        try:
            # Get agent status
            agent_status = self.health_monitor.agent_manager.get_agent_status(agent_name)
            if not agent_status:
                print(f"No status found for agent {agent_name}")
                return
            
            # Display basic status
            print(f"Role: {agent_status.get('role', 'Unknown')}")
            print(f"Worker Status: {agent_status.get('worker_status', 'Unknown')}")
            print(f"Current Task: {agent_status.get('current_task', 'None')}")
            print()
            
            # Display expertise
            expertise = agent_status.get('expertise', [])
            if expertise:
                print("Expertise:")
                for skill in expertise[:5]:  # Show first 5 skills
                    print(f"  - {skill}")
                if len(expertise) > 5:
                    print(f"  ... and {len(expertise) - 5} more")
                print()
            
            # Display recent activity
            last_response = agent_status.get('last_response')
            if last_response:
                print(f"Last Response: {last_response}")
                print()
            
            # Display task progress if available
            task_progress = self.health_monitor.task_tracker.get_task_progress(agent_name)
            if task_progress:
                print("TASK PROGRESS:")
                print(f"  Overall Progress: {task_progress.get('overall_progress', 0)}%")
                print(f"  Current Work: {task_progress.get('current_work', 'Unknown')[:50]}...")
                print()
                
                # Display file status
                file_status = task_progress.get('file_status', {})
                if file_status:
                    print("FILE STATUS:")
                    for file_path, status_info in list(file_status.items())[:5]:
                        print(f"  {file_path}: {status_info.get('status', 'Unknown')}")
                    if len(file_status) > 5:
                        print(f"  ... and {len(file_status) - 5} more files")
                    print()
            
            # Display recovery history
            recovery_history = self.recovery_manager.get_recovery_history(agent_name)
            actions = recovery_history.get(agent_name, [])
            if actions:
                print("RECOVERY HISTORY:")
                for action in actions[-3:]:  # Show last 3 actions
                    timestamp = action.get('timestamp', 'Unknown')
                    if isinstance(timestamp, datetime):
                        timestamp = timestamp.strftime('%H:%M:%S')
                    anomalies = ', '.join(action.get('anomalies', []))
                    success = "✓" if action.get('success', False) else "✗"
                    print(f"  [{timestamp}] {success} {anomalies} -> {action.get('action_taken', 'Unknown')}")
                print()
                
        except Exception as e:
            print(f"ERROR displaying agent details: {e}")
            logger.error(f"Error displaying agent details for {agent_name}: {e}")
    
    def display_system_statistics(self):
        """Display overall system statistics"""
        print("\nSYSTEM STATISTICS")
        print("-" * 50)
        
        try:
            # Get chat statistics
            chat_stats = self.health_monitor.agent_manager.get_chat_statistics()
            
            print("CHAT STATISTICS:")
            print(f"  Total Agents:      {chat_stats.get('total_agents', 0)}")
            print(f"  Working Agents:    {chat_stats.get('working_agents', 0)}")
            print(f"  Stuck Agents:      {chat_stats.get('stuck_agents', 0)}")
            print(f"  Idle Agents:       {chat_stats.get('idle_agents', 0)}")
            print(f"  Pending Help:      {chat_stats.get('pending_help_requests', 0)}")
            print(f"  Chat Connected:     {'Yes' if chat_stats.get('chat_connected', False) else 'No'}")
            print()
            
            # Get recovery summary
            recovery_summary = self.recovery_manager.get_recovery_summary()
            print("RECOVERY STATISTICS:")
            print(f"  Total Attempts:    {recovery_summary['total_recovery_attempts']}")
            print(f"  Successful:        {recovery_summary['successful_recoveries']}")
            print(f"  Failed:            {recovery_summary['failed_recoveries']}")
            print(f"  Escalations:       {recovery_summary['escalations']}")
            print()
            
        except Exception as e:
            print(f"ERROR displaying system statistics: {e}")
            logger.error(f"Error displaying system statistics: {e}")
    
    def display_help(self):
        """Display help information"""
        print("\nMONITORING DASHBOARD COMMANDS:")
        print("-" * 40)
        print("  summary     - Display agent health summary")
        print("  details <agent> - Display detailed info for specific agent")
        print("  stats       - Display system statistics")
        print("  help        - Display this help message")
        print("  quit        - Exit the dashboard")
        print()
    
    def run_interactive_dashboard(self):
        """Run the interactive dashboard CLI"""
        print("Agent Monitoring Dashboard")
        print("Type 'help' for available commands")
        
        while True:
            try:
                command = input("\nmonitor> ").strip().lower()
                
                if command == 'quit' or command == 'exit':
                    print("Exiting monitoring dashboard...")
                    break
                elif command == 'summary' or command == '':
                    self.display_health_summary()
                elif command.startswith('details '):
                    agent_name = command[8:].strip()
                    if agent_name:
                        self.display_agent_details(agent_name)
                    else:
                        print("Please specify an agent name")
                elif command == 'stats':
                    self.display_system_statistics()
                elif command == 'help':
                    self.display_help()
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\n\nExiting monitoring dashboard...")
                break
            except Exception as e:
                print(f"Error: {e}")
                logger.error(f"Error in interactive dashboard: {e}")