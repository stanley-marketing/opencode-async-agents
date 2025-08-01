# opencode Integration - Brownfield Enhancement

## Epic Goal

Implement real opencode command execution and process management to make the opencode-slack system actually execute real opencode commands and provide real value.

## Epic Description

**Existing System Context:**

- Current relevant functionality: File ownership system with SQLite database, task progress tracking with markdown files, CLI server for local testing
- Technology stack: Python 3.x, SQLite, subprocess management
- Integration points: FileOwnershipManager, TaskProgressTracker, CLI Server

**Enhancement Details:**

- What's being added/changed: Integration of actual opencode process execution with subprocess management and output parsing
- How it integrates: opencode commands will be executed when tasks are assigned to employees, with results used to update file ownership and progress tracking
- Success criteria: Employees can be assigned tasks that actually run opencode, file locking works based on actual opencode file operations, progress tracking shows real work completion

## Stories

1. **Story 1:** Create opencode wrapper class that can execute commands with subprocess management
2. **Story 2:** Integrate opencode commands with task assignment and file locking
3. **Story 3:** Implement progress tracking based on actual opencode output

## Compatibility Requirements

- [x] Existing APIs remain unchanged
- [x] Database schema changes are backward compatible
- [x] UI changes follow existing patterns
- [x] Performance impact is minimal

## Risk Mitigation

- **Primary Risk:** opencode process failures could leave system in inconsistent state
- **Mitigation:** Implement comprehensive error handling and timeout mechanisms
- **Rollback Plan:** Revert to file-based task tracking if opencode integration fails

## Definition of Done

- [ ] All stories completed with acceptance criteria met
- [ ] Existing functionality verified through testing
- [ ] Integration points working correctly
- [ ] Documentation updated appropriately
- [ ] No regression in existing features