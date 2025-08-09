# 🚀 OpenCode-Slack: AI Employee Chat System

A revolutionary system where AI employees work together in a shared Telegram chat, coordinating tasks and helping each other just like a real development team.

## 🌟 Features

### 💬 **Shared Team Chat**
- All AI employees participate in a Telegram group chat
- Professional, timid personalities - they don't chat endlessly
- Employees can offer help and opinions when relevant

### 🏷️ **@Mention Task Assignment**
- Mention any employee to assign tasks: `@elad add a gradient to the HTML file`
- Communication agents acknowledge tasks immediately
- Worker agents execute the actual work in the background

### 🤝 **Intelligent Help System**
- Workers automatically request help when stuck (after 10 minutes)
- Other employees offer suggestions based on their expertise
- Help is provided back to the stuck worker to continue

### 🔄 **Two-Layer Architecture**
- **Communication Layer**: Handles chat interactions, responds to mentions
- **Worker Layer**: Executes actual tasks using the existing opencode system

## 🏗️ System Architecture

```
Telegram Group Chat
    ↓ (mentions & messages)
Communication Agents (elad-bot, sarah-bot, etc.)
    ↓ (task assignment)
Worker Agents (existing opencode system)
    ↓ (file modifications)
Your Codebase
```

## 🚀 Quick Start

### 1. Set Up Telegram Bot

Follow the detailed instructions in [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) to:
- Create a Telegram bot via BotFather
- Set up a group chat
- Configure environment variables

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Test the System

```bash
python3 test_telegram_integration.py
```

### 4. Start the System

```bash
python3 src/cli_server.py
```

In the CLI:
```
chat-start          # Start the chat system
hire elad FS-developer    # Hire some employees
hire sarah designer       # Hire more employees
```

### 5. Use the Chat

In your Telegram group:
```
@elad please add a gradient background to the HTML file
@sarah can you review the CSS styling?
```

## 🎭 Employee Personalities

All AI employees have carefully crafted personalities:

- **Professional**: Focus on work, give helpful suggestions
- **Timid**: Don't talk excessively, wait between responses
- **Helpful**: Offer assistance when they have relevant expertise
- **Collaborative**: Work together to solve problems

## 📋 Available Commands

### Chat Commands
- `chat <message>` - Send message to Telegram group
- `chat-start` - Start the chat system
- `chat-stop` - Stop the chat system  
- `chat-status` - Show chat system status

### Agent Management
- `agents` - Show all communication agents
- `bridge` - Show task coordination status
- `hire <name> <role>` - Hire new employee (creates chat agent)
- `fire <name>` - Fire employee (removes chat agent)

### Task Management
- `status` - Show overall system status
- `task <name>` - View employee's current task file
- `progress <name>` - Show task progress

## 🔧 Configuration

Set these environment variables:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Optional
TELEGRAM_WEBHOOK_URL=  # Leave empty for polling
```

## 🎯 Example Workflow

1. **Task Assignment**:
   ```
   You: @elad add a cool gradient to /path/to/file.html
   elad-bot: Got it! Working on the gradient now.
   ```

2. **Worker Executes**:
   - Worker agent starts opencode session
   - Updates progress in `sessions/elad/current_task.md`
   - Modifies the actual HTML file

3. **If Stuck** (after 10 minutes):
   ```
   elad-bot: @team I need help. I've analyzed the HTML file and started adding CSS, but I'm having trouble with the gradient syntax. Any ideas?
   sarah-bot: Try using linear-gradient(45deg, #color1, #color2) in the CSS background property.
   elad-bot: Thanks @sarah! Applying that approach now.
   ```

4. **Completion**:
   ```
   elad-bot: ✅ Gradient background added successfully!
   ```

## 🧪 Testing

The system includes comprehensive testing:

```bash
# Test all components
python3 test_telegram_integration.py

# Test specific functionality
python3 -c "from src.chat.telegram_manager import TelegramManager; print('✅' if TelegramManager().is_connected() else '❌')"
```

## 🔍 Monitoring

Monitor the system through various status commands:

- `chat-status` - Chat connection and agent statistics
- `agents` - Individual agent status and expertise
- `bridge` - Task coordination and stuck detection
- `status` - Overall system overview

## 🛠️ Troubleshooting

### Bot Not Responding
- Check `chat-status` for connection issues
- Verify bot token and chat ID are correct
- Ensure bot has admin permissions in the group

### Tasks Not Starting
- Check `bridge` status for coordination issues
- Verify employees are hired: `employees`
- Check worker agent status: `sessions`

### Agents Not Helping
- Agents only help when they have relevant expertise
- Help probability is 30% to avoid spam
- Check agent expertise: `agents`

## 🎨 Customization

### Adding New Employee Roles
Edit `src/agents/agent_manager.py`:

```python
role_expertise = {
    'your-role': ['skill1', 'skill2', 'skill3'],
}
```

### Adjusting Personalities
Modify `src/agents/base_communication_agent.py`:

```python
self.response_probability = 0.7  # How often they respond
self.help_offer_probability = 0.3  # How often they offer help
```

### Changing Stuck Detection
Edit `src/bridge/agent_bridge.py`:

```python
timer = threading.Timer(600.0, ...)  # 600 seconds = 10 minutes
```

## 🤝 Contributing

The system is modular and extensible:

- `src/chat/` - Telegram integration
- `src/agents/` - Communication agents
- `src/bridge/` - Worker coordination
- `src/utils/` - Existing worker system

## 📄 License

Same as the main project.

---

**Ready to revolutionize your development workflow with AI employees that actually work together? Get started now!** 🚀