# Project Root Isolation - Brownfield Enhancement PRD

## Intro Project Analysis and Context

### Existing Project Overview

**Analysis Source**: IDE-based fresh analysis

**Current Project State**: The opencode-slack project is an AI employee management system that bridges Slack communication with AI-powered development agents. It features file ownership management, task progress tracking, and integration with opencode for actual code execution. The system currently operates in a single working directory context.

### Available Documentation Analysis

**Available Documentation**:
- [x] Tech Stack Documentation
- [x] Source Tree/Architecture
- [x] API Documentation
- [x] Technical Debt Documentation

### Enhancement Scope Definition

**Enhancement Type**:
- [x] New Feature Addition
- [x] Major Feature Modification

**Enhancement Description**: Adding configurable project root directories with file system isolation to enable multi-project support and enhanced security. This enhancement allows the system to work with different project directories while constraining all file operations within the configured project root.

**Impact Assessment**: Moderate Impact (some existing code changes)

### Goals and Background Context

**Goals**:
- Enable multiple server instances to work on different projects simultaneously
- Provide configurable project root directories for isolation
- Ensure all file operations are constrained within the project root
- Maintain backward compatibility with existing functionality

**Background Context**: The current system operates in a single working directory, which limits its ability to handle multiple projects simultaneously. By adding project root isolation, we can run multiple instances of the system for different projects while ensuring file operations are properly constrained within each project's directory structure.

### Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|---------|
| Initial draft | 2025-08-01 | 1.0 | Project root isolation enhancement | BMad System |

## Requirements

### Functional

FR1: System shall support configurable project root directory via environment variable
FR2: System shall support configurable project root directory via REST API
FR3: System shall support configurable project root directory via CLI commands
FR4: All file operations shall be resolved relative to the configured project root
FR5: System shall prevent file operations outside the project root directory
FR6: File paths in database and API responses shall be stored as relative paths

### Non Functional

NFR1: Project root configuration changes shall take effect immediately without system restart
NFR2: File path resolution shall have minimal performance impact (<5ms overhead)
NFR3: System shall maintain backward compatibility with existing relative file paths
NFR4: Security shall be enhanced by constraining all file operations within project root

### Compatibility Requirements

CR1: Existing APIs remain unchanged
CR2: Database schema changes are backward compatible
CR3: UI changes follow existing patterns
CR4: Performance impact is minimal

## Technical Constraints and Integration Requirements

### Existing Technology Stack

**Languages**: Python 3.x
**Frameworks**: Flask, SQLite
**Database**: SQLite
**Infrastructure**: Local development environment
**External Dependencies**: opencode, Telegram API

### Integration Approach

**Database Integration Strategy**: Store file paths as relative paths, resolve against project root at runtime
**API Integration Strategy**: Add new endpoints for project root management while maintaining existing API contracts
**Frontend Integration Strategy**: CLI commands for project root configuration
**Testing Integration Strategy**: Integration tests for file path resolution and project root constraints

### Code Organization and Standards

**File Structure Approach**: Configuration in src/config/, file management in src/managers/
**Naming Conventions**: project_root for configuration, _resolve_file_path for resolution methods
**Coding Standards**: Follow existing Python conventions and error handling patterns
**Documentation Standards**: Update existing API documentation and CLI help text

### Deployment and Operations

**Build Process Integration**: No changes required to build process
**Deployment Strategy**: Configuration via environment variables
**Monitoring and Logging**: Log project root changes and file path resolution
**Configuration Management**: Environment variables for default configuration

### Risk Assessment and Mitigation

**Technical Risks**: Incorrect file path resolution could break existing functionality
**Integration Risks**: Path resolution changes could affect existing file locking and progress tracking
**Deployment Risks**: Misconfigured project root could prevent system from starting
**Mitigation Strategies**: Comprehensive testing, backward compatibility checks, clear error messages

## Epic and Story Structure

**Epic Structure Decision**: Single epic for project root isolation because this is a cohesive enhancement focused on a single cross-cutting concern (file path management) that affects multiple system components but represents one logical feature addition.

## Epic 1: Project Root Isolation

**Epic Goal**: Implement configurable project root directories with file system isolation to enable multi-project support and enhanced security while maintaining backward compatibility with existing functionality.

**Integration Requirements**: Integration with existing file ownership management, task progress tracking, and opencode session management systems

### Story 1.1 Implement project root configuration with environment variable and API support

As a system administrator,
I want to configure the project root directory via environment variables and API,
so that I can control where the system operates on the file system.

**Acceptance Criteria**:
1. System reads PROJECT_ROOT environment variable on startup
2. Default project root is current working directory if not configured
3. API endpoint exists to get current project root configuration
4. API endpoint exists to set project root configuration at runtime
5. Configuration changes take effect immediately

**Integration Verification**:
IV1: Existing functionality continues to work with default project root
IV2: All existing API endpoints continue to function correctly
IV3: Performance is not significantly impacted by configuration management

### Story 1.2 Create file path resolution system that resolves relative paths against project root

As a system component,
I want to resolve all file paths relative to the configured project root,
so that all file operations are properly constrained within the project directory.

**Acceptance Criteria**:
1. All file operations use resolved absolute paths based on project root
2. File paths stored in database are relative paths
3. API responses return relative paths for consistency
4. File operations outside project root are prevented with appropriate error handling
5. Path resolution works correctly on different operating systems

**Integration Verification**:
IV1: File locking continues to work correctly with resolved paths
IV2: Task progress tracking continues to work with resolved paths
IV3: Existing relative paths continue to work as before

### Story 1.3 Add REST API endpoints and CLI commands for project root management

As a system user,
I want to manage project root configuration through REST API and CLI commands,
so that I can easily configure the system for different projects.

**Acceptance Criteria**:
1. GET /project-root endpoint returns current project root configuration
2. POST /project-root endpoint sets project root configuration
3. CLI command "project-root" shows current project root
4. CLI command "project-root <path>" sets project root configuration
5. All commands provide clear error messages for invalid paths

**Integration Verification**:
IV1: Existing CLI commands continue to work correctly
IV2: All existing REST API endpoints continue to function correctly
IV3: Performance is not significantly impacted by new API endpoints

## Checklist Results Report

Before running the checklist and drafting the prompts, offer to output the full updated PRD. If outputting it, confirm with the user that you will be proceeding to run the checklist and produce the report. Once the user confirms, execute the pm-checklist and populate the results in this section.

## Next Steps

### UX Expert Prompt
This section will contain the prompt for the UX Expert, keep it short and to the point to initiate create architecture mode using this document as input.

### Architect Prompt
This section will contain the prompt for the Architect, keep it short and to the point to initiate create architecture mode using this document as input.