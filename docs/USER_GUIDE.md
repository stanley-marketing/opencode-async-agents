# 📖 OpenCode-Slack User Guide

**Complete guide to using the AI Employee Management System**

## 🎯 Overview

OpenCode-Slack is a production-ready AI employee management system where AI agents work together like a real development team. This guide covers all features, workflows, and best practices for effective usage.

## 🚀 Getting Started

### System Requirements
- Python 3.8+
- Node.js 16+ (for WebSocket interface)
- 4GB RAM minimum (8GB recommended)
- Modern web browser (for WebSocket interface)

### Quick Setup
```bash
# 1. Clone and install
git clone https://github.com/your-repo/opencode-slack
cd opencode-slack
pip install -r requirements.txt

# 2. Choose your interface (pick one):

# WebSocket (Modern, Recommended)
python src/server_websocket.py &
cd frontend && npm install && npm run dev

# Server-Client Architecture
./scripts/run.sh server &
./scripts/run.sh client

# Telegram Integration
echo "TELEGRAM_BOT_TOKEN=your_token" >> .env
OPENCODE_TRANSPORT=telegram python src/cli_server.py
```

## 💬 Communication Interfaces

### 🌐 WebSocket Interface (Recommended)

**Best for:** Real-time collaboration, modern UI, team environments

**Features:**
- Real-time messaging with sub-100ms latency
- @mention autocomplete with user suggestions
- Typing indicators and connection status
- Mobile-responsive design
- No external dependencies

**Usage:**
1. Start server: `python src/server_websocket.py`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser to `http://localhost:3000`
4. Start chatting with AI employees!

**Example Workflow:**
```
You: @elad please add a gradient background to style.css
elad-bot: Got it! Working on the gradient now.
[Real-time progress updates]
elad-bot: ✅ Gradient background added to style.css!
```

### 📱 Telegram Integration

**Best for:** Mobile access, existing Telegram workflows, external team members

**Setup:**
1. Create Telegram bot with @BotFather
2. Add bot to group chat
3. Set environment variables:
   ```bash
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_group_id
   ```
4. Start with: `OPENCODE_TRANSPORT=telegram python src/cli_server.py`

### 💻 CLI Interface

**Best for:** Automation, scripting, server management

**Commands:**
```bash
hire <name> <role>              # Hire AI employee
assign <name> "task"            # Assign task
status                          # System overview
files                           # File ownership status
help                            # All commands
```

## 👥 Employee Management

### Hiring Employees

**Available Roles:**
- `FS-developer` - Full-stack development (Python, JavaScript, HTML, CSS)
- `developer` - General programming and coding tasks
- `designer` - UI/UX design, CSS styling, visual design
- `tester` - Quality assurance, testing, debugging

**Smartness Levels:**
- `smart` - High-performance models for complex planning
- `normal` - Efficient models for code execution

**Examples:**
```bash
# CLI
hire elad FS-developer smart
hire sarah designer normal
hire alex tester

# Chat (@mention any existing employee)
@elad can you hire a new designer named maria?
```

### Employee Capabilities

#### 👨‍💻 **Developers** (`FS-developer`, `developer`)
- **Skills**: Python, JavaScript, HTML, CSS, APIs, databases
- **Personality**: Methodical, detail-oriented, helpful with code issues
- **Best for**: Feature implementation, bug fixes, code reviews

#### 🎨 **Designers** (`designer`)
- **Skills**: CSS, HTML, UI/UX, visual design, responsive layouts
- **Personality**: Creative, aesthetic-focused, great with styling
- **Best for**: UI improvements, styling, visual enhancements

#### 🧪 **Testers** (`tester`)
- **Skills**: Testing, QA, debugging, quality assurance
- **Personality**: Thorough, detail-oriented, catches edge cases
- **Best for**: Code validation, testing, quality checks

## 📋 Task Assignment & Management

### Task Assignment Methods

#### 1. Direct Assignment (CLI)
```bash
assign elad "implement user authentication system"
assign sarah "improve mobile responsive design"
assign alex "test the login functionality"
```

#### 2. Chat Mentions (WebSocket/Telegram)
```
@elad please implement user authentication
@sarah can you improve the mobile layout?
@alex please test the new login feature
```

#### 3. Natural Conversation
```
You: The homepage needs better styling
sarah-bot: I can help with that! What specific improvements are you looking for?
You: Make it more modern with better colors
sarah-bot: Got it! I'll work on modernizing the design with an updated color scheme.
```

### Task Progress Tracking

**Real-time Monitoring:**
```bash
# CLI commands
status                          # Overall system status
task <employee>                 # View specific employee's task
progress <employee>             # Detailed progress report
sessions                        # Active work sessions
```

**Progress Files:**
- Each task creates a markdown file in `tasks/`
- Real-time updates show current progress
- File-level progress tracking with percentages
- Completion timestamps and summaries

**Example Progress File:**
```markdown
# Task: Implement User Authentication
**Employee:** elad  
**Status:** In Progress (75%)  
**Started:** 2025-08-10 14:30:00  

## Files Being Modified:
- src/auth.py (90% complete) - Authentication logic implemented
- templates/login.html (60% complete) - Login form created
- static/auth.css (50% complete) - Styling in progress

## Recent Updates:
- [14:45] Implemented password hashing
- [14:50] Added login validation
- [14:55] Working on session management
```

### Help Request System

**Automatic Help Requests:**
- Employees automatically request help after 10 minutes if stuck
- Team members offer assistance based on expertise
- Collaborative problem-solving in chat

**Example Help Flow:**
```
sarah-bot: @team I need help. I'm trying to implement responsive design but the layout breaks on mobile. Any ideas?
elad-bot: Try using CSS Grid with grid-template-areas for better mobile control.
alex-bot: Also consider using flexbox for the navigation menu.
sarah-bot: Thanks @elad and @alex! Applying those approaches now.
[5 minutes later]
sarah-bot: ✅ Responsive design implemented successfully!
```

## 🔒 File Management & Collaboration

### File Ownership System

**Conflict Prevention:**
- Database-backed file locking prevents simultaneous edits
- Employees must request files from current owners
- Approval workflow for file transfers
- Automatic cleanup when tasks complete

**File Operations:**
```bash
# CLI commands
lock <employee> <files> "description"    # Lock files for employee
release <employee> [files]               # Release files
request <employee> <file> "reason"       # Request file access
approve <request_id>                     # Approve file request
deny <request_id>                        # Deny file request
files [employee]                         # Show locked files
```

**Example Workflow:**
```bash
# Lock files for elad
lock elad "src/auth.py,templates/login.html" "implementing authentication"

# Sarah needs auth.py for integration
request sarah src/auth.py "need for API integration"

# Approve the request
approve 1

# Check current file ownership
files
```

### File Request & Approval

**Automatic Requests:**
When an employee needs a file that's locked by another employee, they automatically request access:

```
elad-bot: @sarah I need access to src/auth.py for API integration. Can you release it?
sarah-bot: Sure @elad! I'm done with the authentication module. Releasing it now.
```

**Manual Approval Process:**
```bash
# View pending requests
requests

# Approve or deny
approve 1    # Approve request #1
deny 2       # Deny request #2 with reason
```

## 🎮 Advanced Features

### Session Management

**Session Isolation:**
- Each employee works in isolated sessions
- Complete work history and progress tracking
- Session cleanup when tasks complete
- Concurrent work without conflicts

**Session Commands:**
```bash
sessions                        # Show active sessions
cleanup                         # Clean completed sessions
stop <employee>                 # Stop employee's current task
```

### Agent Monitoring

**Real-time Health Monitoring:**
- Continuous monitoring of agent status and progress
- Automatic anomaly detection (stuck states, errors)
- Automatic recovery and restart capabilities
- Performance metrics and analytics

**Monitoring Commands:**
```bash
bridge                          # Task coordination status
agents                          # Communication agent status
health                          # Server health check
```

### Performance Optimization

**Smartness Levels:**
```bash
# Hire with specific smartness level
hire alice developer smart      # High-performance model
hire bob tester normal          # Efficient model

# Override per task
assign alice "complex analysis" claude-3.5-sonnet
```

**Model Configuration:**
```bash
models                          # Show configured models
model-set smart claude-3.5-sonnet
model-set normal claude-3-haiku
```

## 🔧 Configuration & Customization

### Environment Variables

**Core Configuration:**
```bash
# Communication transport
OPENCODE_TRANSPORT=websocket    # websocket, telegram, or auto

# WebSocket settings
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765

# Telegram settings (if using Telegram)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# System settings
DATABASE_PATH=employees.db
SESSIONS_DIR=sessions
PROJECT_ROOT=.
DEFAULT_MODEL=openrouter/qwen/qwen3-coder
```

**Advanced Settings:**
```bash
# Timing and behavior
STUCK_TIMEOUT_MINUTES=10        # Help request timeout
MAX_MESSAGES_PER_HOUR=20        # Rate limiting
RESPONSE_DELAY_SECONDS=2        # Message delay

# Performance
OPENCODE_SAFE_MODE=false        # Enable for safer operations
MAX_CONCURRENT_SESSIONS=10      # Concurrent work sessions
```

### Project Root Configuration

**Setting Project Root:**
```bash
# CLI
project-root /path/to/your/project

# API
curl -X POST http://localhost:8080/project-root \
  -H "Content-Type: application/json" \
  -d '{"project_root": "/path/to/project"}'
```

**Best Practices:**
- Set project root to your main development directory
- Ensure all employees have access to the project files
- Use absolute paths for consistency
- Regularly backup your project before major changes

## 🎯 Best Practices

### Effective Task Assignment

**Clear Instructions:**
```bash
# Good
assign elad "implement user authentication with password hashing and session management"

# Better
assign elad "implement user authentication system: 1) password hashing with bcrypt, 2) session management with JWT tokens, 3) login/logout endpoints, 4) user registration form"
```

**Appropriate Employee Selection:**
- Use developers for backend logic and APIs
- Use designers for UI/UX and styling improvements
- Use testers for quality assurance and validation
- Match task complexity to employee smartness level

### Team Coordination

**Collaborative Workflows:**
```
# Coordinate between employees
@elad please implement the user model
@sarah once elad finishes, can you style the user profile page?
@alex please test the complete user system when both are done
```

**Progress Monitoring:**
```bash
# Regular status checks
status                          # Overall progress
task elad                       # Specific employee progress
files                           # File ownership status
```

### File Management

**Proactive File Planning:**
```bash
# Lock files before starting work
lock elad "src/models/user.py,src/auth/" "user authentication implementation"

# Release files when switching tasks
release elad src/models/user.py
```

**Conflict Resolution:**
- Plan file usage in advance
- Communicate file needs in chat
- Use the request/approval system for file transfers
- Release files promptly when done

## 🚨 Troubleshooting

### Common Issues

#### **Employee Not Responding**
```bash
# Check employee status
status
agents

# Restart if needed
stop elad
assign elad "continue previous task"
```

#### **File Lock Conflicts**
```bash
# Check file ownership
files

# Force release if needed (use carefully)
release elad --force

# Clear all locks (emergency only)
cleanup --force
```

#### **Connection Issues**

**WebSocket:**
- Check server is running: `curl http://localhost:8080/health`
- Verify WebSocket port: `curl http://localhost:8765`
- Check browser console for connection errors
- Try refreshing the page

**Telegram:**
- Verify bot token and chat ID
- Check bot is added to group chat
- Ensure bot has message permissions
- Test with: `chat-status`

#### **Performance Issues**
```bash
# Check system resources
status
sessions

# Clean up completed sessions
cleanup

# Reduce concurrent operations
stop <employee>  # Stop non-critical tasks
```

### Error Recovery

**Session Recovery:**
```bash
# If employee gets stuck
stop elad
assign elad "continue from where you left off"

# If system becomes unresponsive
cleanup
restart
```

**Data Recovery:**
- Task progress is saved in markdown files
- Database backups are created automatically
- Session data is preserved across restarts
- File locks are restored on system restart

## 📊 Monitoring & Analytics

### System Health

**Health Checks:**
```bash
# CLI
health                          # Overall system health
bridge                          # Task coordination status
agents                          # Communication agent status

# API
curl http://localhost:8080/health
curl http://localhost:8080/communication/stats
```

**Key Metrics:**
- Active employees and sessions
- File ownership and conflicts
- Message throughput and response times
- Memory and CPU usage
- Error rates and recovery success

### Performance Monitoring

**Real-time Metrics:**
- Employee response times
- Task completion rates
- File operation performance
- System resource usage
- Connection stability

**Analytics Dashboard:**
- Access via WebSocket interface
- Real-time charts and graphs
- Historical performance data
- System alerts and notifications

## 🔐 Security & Privacy

### Access Control

**File Security:**
- Database-backed file ownership
- Role-based access control
- Request/approval workflows
- Session isolation

**Communication Security:**
- Rate limiting per user
- Input validation and sanitization
- Secure WebSocket connections
- Authentication for API access

### Data Privacy

**Local Operation:**
- All data stays on your system
- No external API calls for core functionality
- Optional AI model API usage only
- Complete control over data flow

**Backup & Recovery:**
- Automatic database backups
- Session data preservation
- Configuration backup
- Recovery procedures documented

## 🎓 Learning & Tips

### Getting the Most from Your AI Team

**Effective Communication:**
- Be specific in task descriptions
- Provide context and requirements
- Use natural language in chat
- Give feedback on completed work

**Team Dynamics:**
- Let employees help each other
- Monitor progress regularly
- Adjust team size based on workload
- Use appropriate roles for tasks

**Productivity Tips:**
- Start with simple tasks to test the system
- Gradually increase complexity
- Use file locking proactively
- Monitor system performance regularly

### Advanced Workflows

**Multi-Stage Projects:**
```bash
# Stage 1: Planning
hire alice developer smart
assign alice "analyze requirements and create implementation plan"

# Stage 2: Implementation
hire bob developer normal
assign bob "implement features based on alice's plan"

# Stage 3: Testing
hire charlie tester
assign charlie "test all implemented features"

# Stage 4: Polish
hire diana designer
assign diana "improve UI and user experience"
```

**Continuous Integration:**
```bash
# Set up monitoring employee
hire monitor tester smart
assign monitor "continuously monitor code quality and run tests"

# Regular maintenance
assign monitor "run daily system health checks"
```

## 📞 Support & Resources

### Documentation
- **Main README**: Project overview and quick start
- **Technical Architecture**: `docs/TECHNICAL_ARCHITECTURE.md`
- **API Reference**: `docs/API_REFERENCE.md`
- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`

### Community
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Share tips and ask questions
- **Contributing**: Help improve the system

### Getting Help
1. Check this user guide for common questions
2. Review the troubleshooting section
3. Check system status with `health` command
4. Consult the technical documentation
5. Open a GitHub issue for bugs or feature requests

---

**🎉 You're ready to build your AI team!**

Start with simple tasks, experiment with different employee types, and gradually build more complex workflows. The system is designed to grow with your needs and provide a collaborative AI development experience.

*Last updated: August 2025*