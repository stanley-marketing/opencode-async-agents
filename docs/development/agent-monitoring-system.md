# Agent Monitoring System

## Overview

The Agent Monitoring System is a comprehensive solution for monitoring and managing AI agents in the OpenCode-Slack system. It provides real-time health monitoring, automatic detection of stuck or looping agents, and automatic recovery mechanisms to ensure reliable agent performance.

## Features

### 1. Real-time Health Monitoring
- Continuous monitoring of agent status and progress
- Detection of anomalies like stuck states or stagnant progress
- Configurable polling intervals for monitoring frequency

### 2. Automatic Anomaly Detection
- Stuck state detection (agents that remain in the same state too long)
- Progress stagnation detection (agents not making progress on tasks)
- Error state detection (agents in error or stuck states)

### 3. Automatic Recovery System
- Automatic restart of stuck agents
- Notification system to prompt agents to continue work
- Escalation mechanisms for unresolved issues

### 4. Monitoring Dashboard
- Real-time CLI dashboard for monitoring agent status
- Detailed agent information and health metrics
- Recovery history and statistics

### 5. API Integration
- REST API endpoints for monitoring data
- Health status and recovery statistics
- Agent-specific monitoring details

## Components

### AgentHealthMonitor
Monitors agent health and detects anomalies in agent behavior.

Key features:
- Periodic polling of agent status
- Anomaly detection algorithms
- Health status reporting
- Integration with AgentManager and TaskProgressTracker

### AgentRecoveryManager
Manages recovery of stuck or unresponsive agents.

Key features:
- Automatic restart of stuck agents
- Notification system for continuing work
- Escalation callbacks for unresolved issues
- Recovery action logging and tracking

### MonitoringDashboard
CLI dashboard for real-time monitoring of agent status.

Key features:
- Interactive dashboard interface
- Health summary and detailed agent information
- Recovery statistics and history
- Manual intervention capabilities

## Implementation

The monitoring system is implemented as three main components:

1. **AgentHealthMonitor** - Monitors agent health status
2. **AgentRecoveryManager** - Handles automatic recovery of problematic agents
3. **MonitoringDashboard** - Provides CLI interface for monitoring

## API Endpoints

The monitoring system provides the following REST API endpoints:

- `GET /monitoring/health` - Get agent health status
- `GET /monitoring/recovery` - Get recovery statistics
- `GET /monitoring/agents/<agent_name>` - Get specific agent details

## Usage

### Starting the Server with Monitoring
```bash
python src/server.py
```

The monitoring system is automatically initialized and started when the server starts.

### Using the CLI Dashboard
```bash
python src/cli_server.py
# Then use the 'monitor' command
opencode-slack> monitor
```

### Accessing Monitoring Data via API
```bash
# Get health status
curl http://localhost:8080/monitoring/health

# Get recovery statistics
curl http://localhost:8080/monitoring/recovery

# Get specific agent details
curl http://localhost:8080/monitoring/agents/agent-name
```

## Benefits

1. **Proactive Issue Detection** - Automatically detects when agents become stuck or unresponsive
2. **Automatic Recovery** - Reduces manual intervention with automatic restart and notification
3. **Real-time Visibility** - Provides real-time dashboard and API access to monitoring data
4. **Detailed Logging** - Comprehensive logging for debugging and analysis
5. **Configurable Monitoring** - Adjustable polling intervals and detection thresholds

## Configuration

The monitoring system can be configured through the following parameters:

- **Polling Interval** - How often to check agent status (default: 30 seconds)
- **Stuck Threshold** - How long an agent can remain in the same state before being considered stuck
- **Progress Stagnation Threshold** - How long an agent can have no progress before being considered stagnant

## Future Enhancements

Planned improvements for the monitoring system:

1. Web-based dashboard for monitoring
2. Email/SMS alerting for critical issues
3. Historical analytics and trend analysis
4. Integration with external monitoring systems
5. Machine learning-based anomaly detection