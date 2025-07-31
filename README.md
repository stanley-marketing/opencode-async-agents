# 🚀 OpenCode-Slack: Revolutionary AI Employee Management System

> **The world's first AI employee management system where AI agents work together in a shared chat, coordinate tasks, and help each other like a real development team.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Telegram](https://img.shields.io/badge/Chat-Telegram-blue.svg)](https://telegram.org/)

## 🌟 What Makes This Special?

Imagine having a team of AI developers who:
- 💬 **Chat together** in a shared Telegram group
- 🏷️ **Respond to @mentions** like real employees  
- 🤝 **Help each other** when someone gets stuck
- 🔒 **Never conflict** with file locking system
- 📊 **Track their progress** in real-time
- 🧠 **Actually execute code** using opencode integration

**This isn't just another AI tool - it's a complete AI workforce management system!**

## 🎯 Core Features

### 💬 **Shared Team Chat (NEW!)**
- **Telegram Integration**: All employees participate in a group chat
- **@Mention Assignment**: `@elad add gradient to HTML file` → instant task assignment
- **Professional Personalities**: Timid, helpful agents that don't spam
- **Intelligent Help**: Stuck agents automatically request team assistance
- **Two-Layer Architecture**: Communication agents + Worker agents

### 🔒 **Advanced File Management**
- **Conflict-Free Collaboration**: Database-backed file locking system
- **Smart Request System**: Employees can request files from each other
- **Automatic Cleanup**: Files released when tasks complete
- **Real-time Monitoring**: See who's working on what, when

### 🎯 **Intelligent Task Execution**
- **Real OpenCode Integration**: Agents execute actual code changes
- **Progress Tracking**: Live updates in markdown task files
- **Stuck Detection**: Auto-help requests after 10 minutes
- **Session Management**: Isolated work environments per employee

### 👥 **Employee Lifecycle Management**
- **Hire/Fire System**: Dynamic team scaling
- **Role-Based Skills**: Developers, designers, testers with different expertise
- **Session Persistence**: Complete work history and progress tracking
- **Status Monitoring**: Real-time employee availability and workload

## 🏗️ **Revolutionary Architecture**

```
🌐 Telegram Group Chat
    ↓ (@mentions & messages)
🤖 Communication Agents (elad-bot, sarah-bot)
    ↓ (task coordination)
🔄 Agent Bridge (stuck detection & help)
    ↓ (actual work execution)
⚡ Worker Agents (opencode sessions)
    ↓ (file modifications)
📁 Your Codebase (with conflict prevention)
```

### **Two-Layer Agent System**
1. **Communication Layer**: Handles chat, mentions, help coordination
2. **Worker Layer**: Executes actual coding tasks using opencode
3. **Bridge System**: Coordinates between layers with stuck detection

## 🚀 Quick Start

### 1. **Installation**
```bash
git clone https://github.com/your-repo/opencode-slack
cd opencode-slack
pip install -r requirements.txt
```

### 2. **Set Up Telegram Bot** (Optional but Recommended)
```bash
# Follow the detailed guide
cat TELEGRAM_SETUP.md

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### 3. **Start the System**
```bash
# Launch the interactive CLI
python3 src/cli_server.py

# In the CLI:
chat-start                    # Start Telegram integration
hire elad FS-developer        # Hire your first employee
hire sarah designer           # Hire more team members
```

### 4. **Start Working!**

**Option A: Telegram Chat (Recommended)**
```
# In your Telegram group:
@elad please add a gradient background to the HTML file
@sarah can you review the CSS styling?
```

**Option B: CLI Commands**
```bash
assign elad "add gradient to /path/to/file.html"
status                        # Check progress
task elad                     # View detailed progress
```

## 🎭 **Meet Your AI Employees**

Each AI employee has a unique personality and expertise:

### 👨‍💻 **Developers** (`FS-developer`, `developer`)
- **Skills**: Python, JavaScript, HTML, CSS, APIs, Databases
- **Personality**: Methodical, detail-oriented, helpful with code issues
- **Chat Style**: `elad-bot: Got it! Working on the gradient now.`

### 🎨 **Designers** (`designer`)  
- **Skills**: CSS, HTML, UI/UX, Visual Design
- **Personality**: Creative, aesthetic-focused, great with styling
- **Chat Style**: `sarah-bot: I can help with that layout issue.`

### 🧪 **Testers** (`tester`)
- **Skills**: Testing, QA, Debugging, Quality Assurance  
- **Personality**: Thorough, detail-oriented, catches edge cases
- **Chat Style**: `alex-bot: Found a potential issue with that approach.`

## 💬 **Chat System in Action**

### **Normal Task Flow**
```
You: @elad add a cool gradient to /path/to/style.css
elad-bot: Got it! Working on the gradient now.
[10 seconds later]
elad-bot: ✅ Cool gradient added to style.css!
```

### **Help Request Flow** 
```
You: @sarah implement responsive design for the homepage
sarah-bot: On it! Working on responsive design.
[10 minutes later - if stuck]
sarah-bot: @team I need help. I've added media queries but the layout breaks on mobile. Any ideas?
elad-bot: Try using CSS Grid with grid-template-areas for better mobile control.
sarah-bot: Thanks @elad! Applying that approach now.
[5 minutes later]
sarah-bot: ✅ Responsive design implemented successfully!
```

## 🎮 **Advanced Usage**

### **CLI Commands Reference**

#### **👥 Employee Management**
```bash
hire <name> <role>              # Hire new AI employee
fire <name>                     # Fire employee (releases all files)
employees                       # List all employees and status
```

#### **💬 Chat System**
```bash
chat-start                      # Start Telegram integration
chat-stop                       # Stop chat system
chat <message>                  # Send message to group
chat-status                     # Show connection status
agents                          # Show communication agents
```

#### **📋 Task Management**
```bash
assign <name> "task"            # Assign task to employee
start <name> "task"             # Alias for assign
stop <name>                     # Stop employee's current task
status                          # Show system overview
sessions                        # Show active work sessions
task <name>                     # View employee's task file
progress <name>                 # Show detailed progress
```

#### **🔒 File Management**
```bash
lock <name> <files> <desc>      # Lock files for employee
release <name> [files]          # Release files
request <name> <file> <desc>    # Request file from employee
approve <request_id>            # Approve file request
deny <request_id>               # Deny file request
files [name]                    # Show locked files
```

#### **🔧 System Management**
```bash
bridge                          # Show task coordination status
cleanup                         # Clean up completed sessions
clear                           # Clear screen
help                            # Show all commands
quit                            # Exit system
```

### **Programmatic API**

```python
from src.managers.file_ownership import FileOwnershipManager
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager

# Initialize the complete system
file_manager = FileOwnershipManager()
telegram_manager = TelegramManager()
agent_manager = AgentManager(file_manager, telegram_manager)

# Start chat system
telegram_manager.start_polling()

# Hire employees (creates both worker and chat agents)
file_manager.hire_employee("elad", "FS-developer")
agent_manager.create_agent("elad", "FS-developer", ["python", "javascript"])

# Send messages to chat
telegram_manager.send_message("🚀 System is online!", "system")

# Monitor agent status
status = agent_manager.get_agent_status()
print(f"Active agents: {len(status)}")
```

## 🧩 **System Components**

### **🔒 FileOwnershipManager** - Conflict Prevention Core
```python
# Prevents file conflicts with database-backed locking
file_manager.hire_employee("sarah", "developer")
file_manager.lock_files("sarah", ["src/auth.py"], "implement auth")
file_manager.request_file("elad", "src/auth.py", "need for API integration")
```

### **💬 TelegramManager** - Chat Integration Engine  
```python
# Handles all Telegram communication
telegram_manager.start_polling()
telegram_manager.send_message("Task completed!", "elad")
telegram_manager.add_message_handler(custom_handler)
```

### **🤖 AgentManager** - Communication Orchestrator
```python
# Manages all communication agents
agent_manager.create_agent("elad", "developer", ["python", "css"])
agent_manager.request_help_for_agent("elad", "stuck on CSS", "progress summary")
agent_manager.notify_task_completion("elad", "gradient added")
```

### **🌉 AgentBridge** - Worker Coordination Hub
```python
# Bridges chat agents with worker agents
bridge.assign_task_to_worker("elad", "add gradient to HTML")
bridge.start_monitoring()  # Automatic stuck detection
bridge.get_bridge_status()  # Monitor coordination
```

### **⚡ OpencodeSessionManager** - Task Execution Engine
```python
# Manages actual code execution
session_manager.start_employee_task("elad", "implement feature", "claude-3.5")
session_manager.get_active_sessions()
session_manager.stop_employee_task("elad")
```

### **📊 TaskProgressTracker** - Progress Monitoring
```python
# Tracks detailed progress in markdown files
tracker.create_task_file("elad", "add gradient", ["style.css"])
tracker.update_file_status("elad", "style.css", 75, "gradient applied")
tracker.get_task_progress("elad")
```

## 🧪 **Testing & Validation**

### **Comprehensive Test Suite**
```bash
# Test all components
python3 test_telegram_integration.py

# Test specific systems
python -m pytest tests/test_file_ownership.py -v
python -m pytest tests/test_opencode_wrapper.py -v
python -m pytest tests/test_task_progress.py -v

# Integration tests
python -m pytest tests/test_integration.py -v
```

### **Live System Testing**
```bash
# Test chat connectivity
python3 -c "from src.chat.telegram_manager import TelegramManager; print('✅' if TelegramManager().is_connected() else '❌')"

# Test employee system
python3 src/cli_server.py
> hire test-employee developer
> assign test-employee "create a simple HTML file"
> status
```

## ⚙️ **Configuration**

### **Environment Variables**
```bash
# Telegram Integration (Optional)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_group_chat_id

# System Configuration
DATABASE_PATH=employees.db                    # SQLite database location
SESSIONS_DIR=sessions                         # Employee session storage
DEFAULT_MODEL=openrouter/qwen/qwen3-coder    # Default AI model

# Advanced Settings
STUCK_TIMEOUT_MINUTES=10                      # Help request timeout
MAX_MESSAGES_PER_HOUR=20                      # Rate limiting
RESPONSE_DELAY_SECONDS=2                      # Minimum delay between messages
```

### **Customization Options**
```python
# Modify agent personalities
class CustomAgent(BaseCommunicationAgent):
    def __init__(self, name, role):
        super().__init__(name, role)
        self.response_probability = 0.8  # More talkative
        self.help_offer_probability = 0.5  # More helpful

# Add custom expertise
role_expertise = {
    'ai-specialist': ['machine-learning', 'neural-networks', 'data-science'],
    'devops-engineer': ['docker', 'kubernetes', 'ci-cd', 'aws'],
}

# Custom stuck detection timing
timer = threading.Timer(300.0, ...)  # 5 minutes instead of 10
```

## 🎯 **Why Choose OpenCode-Slack?**

### **🚀 Revolutionary Features**
- ✅ **World's First AI Team Chat** - Agents collaborate in Telegram like real employees
- ✅ **Zero File Conflicts** - Advanced locking prevents simultaneous edits
- ✅ **Intelligent Help System** - Stuck agents automatically get team assistance  
- ✅ **Real Code Execution** - Actual file modifications using opencode integration
- ✅ **Professional AI Personalities** - Timid, helpful agents that don't spam
- ✅ **Complete Lifecycle Management** - Hire, assign, monitor, fire employees

### **💼 Perfect For**
- **🏢 Development Teams** - Scale your coding capacity with AI employees
- **🚀 Startups** - Get a full development team without hiring costs
- **🎓 Learning Projects** - See how AI agents collaborate and learn
- **🔬 Research** - Study multi-agent AI coordination systems
- **⚡ Rapid Prototyping** - Quickly build features with AI assistance

### **🆚 Compared to Other AI Tools**
| Feature | OpenCode-Slack | Other AI Tools |
|---------|----------------|----------------|
| **Team Collaboration** | ✅ Agents work together | ❌ Single agent only |
| **File Conflict Prevention** | ✅ Advanced locking system | ❌ No coordination |
| **Real-time Chat** | ✅ Telegram integration | ❌ No chat interface |
| **Stuck Detection & Help** | ✅ Automatic team assistance | ❌ Manual intervention |
| **Progress Tracking** | ✅ Detailed markdown reports | ❌ Basic logging |
| **Scalable Team** | ✅ Hire/fire employees | ❌ Fixed single agent |

## 📁 **Project Architecture**

```
opencode-slack/
├── 💬 src/chat/              # Telegram integration
│   ├── telegram_manager.py   # Bot communication
│   ├── message_parser.py     # @mention parsing
│   └── chat_config.py        # Configuration
├── 🤖 src/agents/            # Communication agents
│   ├── base_communication_agent.py  # Agent personalities
│   ├── communication_agent.py       # Individual agents
│   └── agent_manager.py             # Agent coordination
├── 🌉 src/bridge/            # Worker coordination
│   └── agent_bridge.py       # Chat ↔ Worker bridge
├── 🔒 src/managers/          # Core business logic
│   └── file_ownership.py     # File locking system
├── 📊 src/trackers/          # Progress monitoring
│   └── task_progress.py      # Task tracking
├── ⚡ src/utils/             # Task execution
│   └── opencode_wrapper.py   # OpenCode integration
├── 🖥️ src/cli_server.py      # Interactive CLI
├── 📚 TELEGRAM_SETUP.md      # Bot setup guide
├── 📖 CHAT_SYSTEM_README.md  # Detailed chat docs
└── 🧪 test_telegram_integration.py  # Test suite
```

## 🤝 **Contributing**

We welcome contributions! Here's how to get started:

```bash
# Fork and clone the repository
git clone https://github.com/your-username/opencode-slack
cd opencode-slack

# Create a feature branch
git checkout -b feature/amazing-new-feature

# Make your changes and test
python3 test_telegram_integration.py
python -m pytest tests/ -v

# Submit a pull request
```

### **Areas for Contribution**
- 🌐 **New Chat Platforms** - Discord, Slack, Microsoft Teams integration
- 🧠 **AI Models** - Support for more AI providers and models  
- 🎨 **Agent Personalities** - More diverse and specialized agent types
- 📊 **Analytics** - Advanced metrics and performance monitoring
- 🔧 **Tools Integration** - Git, Docker, CI/CD pipeline integration

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **OpenCode Team** - For the amazing AI coding platform
- **Telegram** - For the robust bot API
- **Community Contributors** - For making this project better

---

## 🚀 **Ready to Build Your AI Team?**

```bash
git clone https://github.com/your-repo/opencode-slack
cd opencode-slack
pip install -r requirements.txt
python3 src/cli_server.py
```

**Start with:** `chat-start` → `hire elad FS-developer` → `@elad create something amazing!`

**Join the revolution of AI-powered development teams!** 🎉

---

*Made with ❤️ by developers who believe AI should work together, not alone.*