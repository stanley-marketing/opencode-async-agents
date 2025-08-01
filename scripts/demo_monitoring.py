#!/usr/bin/env python3
"""
Demo script for the agent monitoring system
"""

import sys
from pathlib import Path
import time

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def demo_monitoring_system():
    """Demonstrate the agent monitoring system"""
    print("=== Agent Monitoring System Demo ===")
    print()
    
    # Try to import monitoring components
    try:
        from src.monitoring.agent_health_monitor import AgentHealthMonitor
        from src.monitoring.agent_recovery_manager import AgentRecoveryManager
        from src.monitoring.monitoring_dashboard import MonitoringDashboard
        print("✅ Monitoring system components imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import monitoring system: {e}")
        return
    
    # Show what the monitoring system can do
    print("\n🔍 What the monitoring system provides:")
    print("  1. Real-time agent health monitoring")
    print("  2. Automatic detection of stuck or looping agents")
    print("  3. Automatic recovery of problematic agents")
    print("  4. Interactive dashboard for monitoring status")
    print("  5. Detailed logging and alerting")
    
    print("\n🚀 How it works:")
    print("  1. AgentHealthMonitor periodically checks agent status")
    print("  2. Detects anomalies like stuck states or stagnant progress")
    print("  3. AgentRecoveryManager automatically restarts stuck agents")
    print("  4. MonitoringDashboard provides real-time visibility")
    
    print("\n📊 Example API endpoints:")
    print("  GET /monitoring/health     - Get agent health status")
    print("  GET /monitoring/recovery   - Get recovery statistics")
    print("  GET /monitoring/agents/:name - Get specific agent details")
    
    print("\n🔧 To use the monitoring system:")
    print("  1. Start the server: python src/server.py")
    print("  2. Monitor agents through the dashboard or API")
    print("  3. View monitoring data in real-time")
    
    print("\n🎯 Benefits:")
    print("  • Proactive detection of agent issues")
    print("  • Automatic recovery reduces manual intervention")
    print("  • Real-time visibility into agent performance")
    print("  • Detailed logging for debugging and analysis")

if __name__ == "__main__":
    demo_monitoring_system()