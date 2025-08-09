# OpenCode-Slack User Guide

Welcome to OpenCode-Slack! This guide will help you get the most out of your AI employee management system.

## 🎯 Quick Start

### Your First AI Employee

1. **Start the System**
   ```bash
   # Terminal 1: Start server
   ./scripts/run.sh server
   
   # Terminal 2: Start client
   ./scripts/run.sh client
   ```

2. **Hire Your First Employee**
   ```bash
   hire elad FS-developer
   ```

3. **Assign a Task**
   ```bash
   assign elad "create a simple HTML page with a gradient background"
   ```

4. **Check Progress**
   ```bash
   status
   task elad
   ```

## 👥 Managing AI Employees

### Employee Types

OpenCode-Slack supports different types of AI employees:

#### 👨‍💻 **Developers** (`FS-developer`, `developer`)
- **Skills**: Python, JavaScript, HTML, CSS, APIs, Databases
- **Best for**: Code implementation, bug fixes, feature development
- **Personality**: Methodical, detail-oriented, helpful with technical issues

#### 🎨 **Designers** (`designer`)
- **Skills**: CSS, HTML, UI/UX, Visual Design
- **Best for**: Styling, layouts, user interface improvements
- **Personality**: Creative, aesthetic-focused, great with visual elements

#### 🧪 **Testers** (`tester`)
- **Skills**: Testing, QA, Debugging, Quality Assurance
- **Best for**: Finding bugs, testing features, quality validation
- **Personality**: Thorough, detail-oriented, catches edge cases

### Hiring Employees

```bash
# Basic hiring
hire <name> <role>

# Examples
hire alice developer
hire sarah designer
hire bob tester

# Hire with specific intelligence level
hire elad FS-developer smart    # Uses high-performance AI model
hire sarah designer normal      # Uses standard AI model
```

### Managing Your Team

```bash
# View all employees
status

# View specific employee details
task <name>

# Fire an employee
fire <name>

# View active sessions
sessions
```

## 🎯 Task Management

### Assigning Tasks

```bash
# Basic task assignment
assign <name> "task description"

# Examples
assign elad "add a login form to the homepage"
assign sarah "improve the CSS styling for mobile devices"
assign bob "test the new authentication system"

# Assign with specific AI model
assign elad "complex refactoring task" claude-3.5-sonnet
```

### Task Best Practices

1. **Be Specific**: Clear, detailed descriptions work best
   ```bash
   # Good
   assign elad "add a responsive navigation menu with dropdown for mobile"
   
   # Less effective
   assign elad "fix the menu"
   ```

2. **Break Down Complex Tasks**: Large tasks work better when split
   ```bash
   assign alice "create user registration form"
   assign alice "add form validation"
   assign alice "connect form to database"
   ```

3. **Use Appropriate Employee Types**: Match tasks to skills
   ```bash
   assign sarah "improve button styling"     # Designer for UI
   assign elad "implement API endpoint"      # Developer for backend
   assign bob "test the new feature"         # Tester for QA
   ```

### Monitoring Progress

```bash
# Quick status overview
status

# Detailed task progress
task <name>

# View task file directly
cat sessions/<name>/task.md

# Check file locks
files
```

## 💬 Chat System Integration

### Telegram Setup

For the full collaborative experience, integrate with Telegram:

1. **Set up Telegram Bot** (see [setup guide](../setup/TELEGRAM_SETUP.md))
2. **Start Chat System**
   ```bash
   chat-start
   ```

### Using Chat Commands

In your Telegram group:

```
# Assign tasks with @mentions
@elad please add a gradient background to the CSS file
@sarah can you review the mobile layout?

# Check status
/status

# Get help
@team I need help with this CSS issue
```

### Chat Best Practices

1. **Use @mentions**: Direct tasks to specific employees
2. **Be conversational**: Natural language works well
3. **Ask for help**: Use `@team` when stuck
4. **Be patient**: AI employees will respond when they complete tasks

## 🔒 File Management

### Understanding File Locks

OpenCode-Slack prevents conflicts by locking files during work:

```bash
# View locked files
files

# Lock files manually
lock elad "src/auth.py,src/models.py" "implementing authentication"

# Release files
release elad src/auth.py

# Request files from another employee
request elad src/auth.py "need to integrate with API"
```

### File Lock Best Practices

1. **Let the system handle locks**: Usually automatic
2. **Release when done**: Files auto-release when tasks complete
3. **Request politely**: Use descriptive reasons for file requests
4. **Avoid conflicts**: Check `files` before starting related work

## 🎮 Advanced Features

### Smartness Levels

Configure different AI models for different needs:

```bash
# View available models
models

# Set models for smartness levels
model-set smart claude-3.5-sonnet      # High-performance for complex tasks
model-set normal openrouter/qwen/qwen3-coder  # Efficient for routine work

# Hire with specific smartness
hire genius developer smart
hire worker developer normal
```

### Project Root Management

Set the working directory for your team:

```bash
# View current project root
project-root

# Set new project root
project-root /path/to/your/project

# All employees will work in this directory
```

### Session Management

Monitor and manage work sessions:

```bash
# View active sessions
sessions

# Stop an employee's current task
stop <name>

# Clean up completed sessions
cleanup

# View session details
cat sessions/<name>/task.md
```

## 🔧 System Management

### Health Monitoring

```bash
# Check system health
health

# View bridge status (coordination between chat and workers)
bridge

# Monitor agent status
agents
```

### Configuration

```bash
# View current configuration
cat .env

# Key settings to adjust:
STUCK_TIMEOUT_MINUTES=10        # How long before requesting help
MAX_MESSAGES_PER_HOUR=20        # Chat rate limiting
RESPONSE_DELAY_SECONDS=2        # Delay between messages
```

## 🧪 Testing Your Setup

### Basic Functionality Test

```bash
# 1. Hire a test employee
hire test-employee developer

# 2. Assign a simple task
assign test-employee "create a simple HTML file with hello world"

# 3. Monitor progress
status
task test-employee

# 4. Check results
ls sessions/test-employee/

# 5. Clean up
fire test-employee
```

### Chat Integration Test

```bash
# 1. Start chat system
chat-start

# 2. Send test message in Telegram
@test-employee create a simple CSS file

# 3. Check response in chat
# 4. Verify task completion
```

## 🎯 Common Workflows

### Feature Development Workflow

```bash
# 1. Hire development team
hire lead FS-developer smart
hire frontend designer
hire tester tester

# 2. Plan the feature
assign lead "analyze requirements for user authentication system"

# 3. Implement components
assign lead "implement backend authentication API"
assign frontend "create login and registration forms"

# 4. Test and refine
assign tester "test authentication system thoroughly"
assign frontend "fix any UI issues found in testing"
```

### Bug Fix Workflow

```bash
# 1. Assign investigation
assign developer "investigate login bug reported by users"

# 2. Implement fix
assign developer "fix the login validation issue"

# 3. Test fix
assign tester "verify login bug is fixed and no regressions"
```

### Code Review Workflow

```bash
# 1. Request review
assign senior-dev "review the authentication implementation"

# 2. Address feedback
assign junior-dev "address code review comments"

# 3. Final validation
assign tester "test updated code after review changes"
```

## 🆘 Troubleshooting

### Common Issues

1. **Employee Not Responding**
   ```bash
   # Check if stuck
   task <name>
   
   # Stop and restart
   stop <name>
   assign <name> "continue previous task"
   ```

2. **File Conflicts**
   ```bash
   # Check locks
   files
   
   # Release if needed
   release <name> <file>
   ```

3. **Chat Not Working**
   ```bash
   # Check chat status
   chat-status
   
   # Restart chat system
   chat-stop
   chat-start
   ```

### Getting Help

1. **Check system status**: `status` and `health`
2. **Review logs**: Check session directories for error logs
3. **Restart components**: Stop and restart stuck employees
4. **Consult documentation**: See [development guide](../development/AGENTS.md)

## 📚 Next Steps

- **Explore Advanced Features**: Check the [API documentation](../api/README.md)
- **Customize Your Setup**: Review [configuration options](../setup/README.md)
- **Join the Community**: Contribute to the project on GitHub
- **Share Your Experience**: Help improve the documentation

---

*Happy managing! Your AI team is ready to help you build amazing things.*