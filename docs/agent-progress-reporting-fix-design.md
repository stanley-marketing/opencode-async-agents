# Coding Design Document: Fix Agent Progress Reporting System

## Problem Statement

The current agent progress reporting system is broken because:

1. **Hardcoded Fictional Data**: The `CheckProgressTool` returns hardcoded fictional progress data (45%, "Implementing core functionality") instead of real progress information.

2. **Wrong Architecture**: The working agent is supposed to update its own progress, but the monitoring agent should be responsible for tracking and updating progress by observing the working agent's activities.

3. **Disconnected Systems**: The monitoring system exists but is not properly integrated with the progress reporting tools that agents use.

## Current Architecture Issues

### What's Broken:
- `CheckProgressTool._run()` in `src/agents/agent_tools.py` returns hardcoded data
- Working agents are expected to self-report progress (unreliable)
- No connection between monitoring system and progress reporting tools
- Task progress files exist but aren't being used by the progress checking system

### What Works:
- `TaskProgressTracker` can read/write progress files
- `AgentHealthMonitor` can observe agent status
- Session directories and file structure exist
- Monitoring system framework is in place

## Proposed Solution Architecture

### High-Level Design Changes

#### 1. **Monitoring Agent Responsibility**
- The monitoring agent should be the **single source of truth** for progress tracking
- It should observe working agents and update their progress files automatically
- It should infer progress from agent activities, not rely on self-reporting

#### 2. **Progress Inference System**
- Monitor agent conversations and activities
- Parse agent responses to understand what they're working on
- Track file modifications and code changes
- Estimate progress based on observable activities

#### 3. **Real-Time Progress Updates**
- Monitoring agent continuously updates `sessions/{agent_name}/current_task.md`
- Updates include:
  - Current work description (inferred from recent activities)
  - File status percentages (based on file modifications)
  - Overall progress estimation
  - Last activity timestamp

#### 4. **Tool Integration**
- `CheckProgressTool` reads from actual progress files instead of returning hardcoded data
- Tools get access to `TaskProgressTracker` instance
- Progress queries return real data from monitoring system

## Implementation Tasks

### Task 1: Refactor CheckProgressTool
**Objective**: Make the tool read real progress data instead of returning hardcoded values

**Changes Needed**:
- Remove hardcoded progress data from `CheckProgressTool._run()`
- Inject `TaskProgressTracker` instance into the tool
- Read actual progress from `sessions/{agent_name}/current_task.md`
- Return "No active task" when no progress file exists
- Handle errors gracefully when files are missing or corrupted

### Task 2: Enhance Monitoring Agent Progress Tracking
**Objective**: Make the monitoring agent responsible for updating progress files

**Changes Needed**:
- Extend `AgentHealthMonitor` to track agent activities
- Add activity parsing logic to infer what agents are working on
- Implement automatic progress file updates based on observations
- Track conversation patterns to understand current work
- Monitor file system changes to detect code modifications

### Task 3: Activity Inference Engine
**Objective**: Build system to infer progress from observable agent behavior

**Components Needed**:
- **Conversation Parser**: Analyze agent messages to understand current work
- **File Activity Monitor**: Track file modifications and relate them to tasks
- **Progress Estimator**: Calculate completion percentages based on activities
- **Work Description Generator**: Create human-readable descriptions of current work

### Task 4: Progress File Management
**Objective**: Ensure progress files are properly maintained by monitoring system

**Changes Needed**:
- Monitoring agent creates progress files when tasks are assigned
- Regular updates to "Current Work" section based on observations
- File status tracking based on actual file modifications
- Cleanup of completed/abandoned tasks

### Task 5: Tool Dependency Injection
**Objective**: Provide tools with access to real system components

**Changes Needed**:
- Modify tool initialization to accept `TaskProgressTracker` instance
- Update `get_agent_tools()` to inject dependencies
- Ensure tools can access monitoring system data
- Handle cases where monitoring system is unavailable

### Task 6: Error Handling and Fallbacks
**Objective**: Ensure system works gracefully when components fail

**Fallback Strategies**:
- Return "No progress data available" when monitoring is down
- Handle missing or corrupted progress files
- Provide basic status when full monitoring isn't available
- Log errors without breaking agent functionality

## Data Flow Design

### Current (Broken) Flow:
```
User asks about progress → Agent uses CheckProgressTool → Returns hardcoded 45%
```

### Proposed Flow:
```
1. Working agent performs activities (coding, responding, etc.)
2. Monitoring agent observes activities
3. Monitoring agent updates progress file with inferred progress
4. User asks about progress
5. Agent uses CheckProgressTool
6. Tool reads actual progress file
7. Returns real progress data
```

## File Structure Changes

### Progress File Format Enhancement:
```markdown
# Current Task: {task_description}

## Assigned: {timestamp}
## Last Updated: {timestamp} (by monitoring system)

## Current Work:
{inferred_from_recent_activities}

## File Status:
- src/file1.py: 75% complete (last modified 2 minutes ago)
- src/file2.py: 30% complete (in progress)

## Recent Activities:
- {timestamp}: Agent responded about authentication
- {timestamp}: Modified src/auth.py
- {timestamp}: Discussed database schema

## Overall Progress: 52%
```

## Success Criteria

1. **Accurate Progress Reporting**: `CheckProgressTool` returns real progress data based on actual agent activities
2. **Automatic Updates**: Progress files are updated by monitoring system without agent self-reporting
3. **Activity Correlation**: Progress reflects actual work being done (file changes, conversations, etc.)
4. **Error Resilience**: System handles missing files, monitoring failures, and edge cases gracefully
5. **Real-time Updates**: Progress information is current and reflects recent activities

## Risk Mitigation

### Potential Issues:
- **Inference Accuracy**: Monitoring might misinterpret agent activities
- **Performance Impact**: Continuous monitoring could affect system performance
- **File Conflicts**: Multiple systems writing to progress files simultaneously

### Mitigation Strategies:
- Start with simple activity patterns and improve over time
- Implement efficient monitoring with configurable intervals
- Use file locking and atomic writes for progress updates
- Provide manual override capabilities for incorrect inferences

## Testing Strategy

1. **Unit Tests**: Test individual components (progress parsing, activity inference)
2. **Integration Tests**: Test monitoring system with real agent activities
3. **End-to-End Tests**: Verify complete flow from activity to progress reporting
4. **Error Scenario Tests**: Test behavior when components fail or files are missing
5. **Performance Tests**: Ensure monitoring doesn't impact system responsiveness

## Implementation Priority

### Phase 1 (Critical Fix):
- Task 1: Refactor CheckProgressTool to read real data
- Task 5: Basic dependency injection for tools

### Phase 2 (Core Functionality):
- Task 2: Basic monitoring agent progress tracking
- Task 4: Progress file management

### Phase 3 (Advanced Features):
- Task 3: Activity inference engine
- Task 6: Comprehensive error handling

This design document provides the roadmap for fixing the agent progress reporting system by implementing proper monitoring-based progress tracking instead of the current hardcoded approach.