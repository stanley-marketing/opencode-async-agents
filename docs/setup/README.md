# OpenCode-Slack Setup Guide

This guide will help you set up OpenCode-Slack from scratch, including all dependencies and optional integrations.

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows (WSL recommended)
- **Memory**: Minimum 4GB RAM, 8GB recommended
- **Storage**: At least 2GB free space

### Required Dependencies
- `pip` (Python package manager)
- `git` (for cloning the repository)
- Internet connection (for AI model access)

## 🚀 Quick Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/opencode-slack
cd opencode-slack
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Basic Configuration
```bash
# Create configuration directory
mkdir -p ~/.opencode-slack

# Copy default configuration
cp config/default.env .env
```

### 4. Start the System
```bash
# Start server
./scripts/run.sh server

# In another terminal, start client
./scripts/run.sh client
```

## 🔧 Detailed Setup

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Core Configuration
PROJECT_ROOT=.                                    # Project root directory
DATABASE_PATH=employees.db                        # SQLite database location
SESSIONS_DIR=sessions                             # Employee session storage

# AI Model Configuration
DEFAULT_MODEL=openrouter/qwen/qwen3-coder        # Default AI model
SMART_MODEL=claude-3.5-sonnet                    # High-performance model
NORMAL_MODEL=openrouter/qwen/qwen3-coder         # Standard model

# System Settings
STUCK_TIMEOUT_MINUTES=10                          # Help request timeout
MAX_MESSAGES_PER_HOUR=20                          # Rate limiting
RESPONSE_DELAY_SECONDS=2                          # Message delay

# Server Configuration
SERVER_HOST=localhost                             # Server host
SERVER_PORT=8080                                  # Server port
```

### Optional: Telegram Integration

For the full chat experience, set up Telegram integration:

1. **Create a Telegram Bot**
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Follow the instructions to get your bot token

2. **Create a Group Chat**
   - Create a new Telegram group
   - Add your bot to the group
   - Make the bot an admin (optional but recommended)

3. **Get Chat ID**
   ```bash
   # Add to your .env file
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_group_chat_id
   ```

4. **Find Your Chat ID**
   ```bash
   # Send a message to your group, then run:
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"
   ```

For detailed Telegram setup, see [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md).

## 🏗️ Architecture Setup

### Server-Client Architecture

OpenCode-Slack uses a modern server-client architecture:

```
┌─────────────────┐    ┌─────────────────┐
│   CLI Client    │    │   Web Client    │
│                 │    │   (Future)      │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
          ┌─────────────────┐
          │  OpenCode       │
          │  Server         │
          │                 │
          │  ┌─────────────┐│
          │  │ REST API    ││
          │  ├─────────────┤│
          │  │ Agent Mgmt  ││
          │  ├─────────────┤│
          │  │ File System ││
          │  ├─────────────┤│
          │  │ Chat Bridge ││
          │  └─────────────┘│
          └─────────────────┘
```

### Component Setup

1. **Server Setup**
   ```bash
   # Start the server with custom configuration
   python3 -m src.server --host 0.0.0.0 --port 8080 --db-path /custom/path/employees.db
   ```

2. **Client Setup**
   ```bash
   # Connect to local server
   python3 -m src.client

   # Connect to remote server
   python3 -m src.client --server http://remote-server:8080
   ```

## 🔐 Security Setup

### Basic Security Configuration

1. **File Permissions**
   ```bash
   # Secure the database
   chmod 600 employees.db
   
   # Secure configuration
   chmod 600 .env
   ```

2. **Network Security**
   ```bash
   # For production, bind to specific interface
   SERVER_HOST=127.0.0.1  # Local only
   # or
   SERVER_HOST=0.0.0.0    # All interfaces (use with firewall)
   ```

3. **Environment Variables**
   ```bash
   # Never commit sensitive data
   echo ".env" >> .gitignore
   echo "*.db" >> .gitignore
   echo "sessions/" >> .gitignore
   ```

### Production Security

For production deployments:

1. **Use HTTPS**
   ```bash
   # Configure reverse proxy (nginx/apache)
   # Enable SSL/TLS certificates
   ```

2. **Authentication** (Future feature)
   ```bash
   # API key authentication
   API_KEY=your_secure_api_key
   
   # JWT tokens
   JWT_SECRET=your_jwt_secret
   ```

3. **Rate Limiting**
   ```bash
   # Configure rate limits
   RATE_LIMIT_REQUESTS=100
   RATE_LIMIT_WINDOW=60
   ```

## 🧪 Testing Setup

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
python3 -m pytest

# Run with coverage
python3 -m pytest --cov=src

# Run specific test categories
python3 -m pytest tests/test_integration.py -v
python3 -m pytest tests/test_server_client_integration.py -v
```

### Validation Scripts
```bash
# Run system validation
python3 scripts/test/validate_system.py

# Test Telegram integration
python3 scripts/test/test_telegram_integration.py

# Performance testing
python3 scripts/test/performance_test.py
```

## 🔧 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find process using port 8080
   lsof -i :8080
   
   # Kill the process or use different port
   ./scripts/run.sh server --port 8081
   ```

2. **Permission Denied**
   ```bash
   # Fix file permissions
   chmod +x scripts/run.sh
   
   # Fix Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

3. **Module Not Found**
   ```bash
   # Install missing dependencies
   pip install -r requirements.txt
   
   # Check Python path
   python3 -c "import sys; print(sys.path)"
   ```

4. **Database Issues**
   ```bash
   # Reset database
   rm employees.db
   
   # Clear sessions
   rm -rf sessions/
   ```

### Debug Mode

Enable debug logging:
```bash
# Set debug level
export LOG_LEVEL=DEBUG

# Run with verbose output
./scripts/run.sh server --debug
```

### Health Checks

Verify system health:
```bash
# Check server health
curl http://localhost:8080/health

# Check system status
curl http://localhost:8080/status

# Test employee management
curl -X POST http://localhost:8080/employees \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "role": "developer"}'
```

## 📚 Next Steps

After setup:

1. **Read the User Guide**: [user-guide/CHAT_SYSTEM_README.md](../user-guide/CHAT_SYSTEM_README.md)
2. **Explore the API**: [api/README.md](../api/README.md)
3. **Development Guide**: [development/AGENTS.md](../development/AGENTS.md)
4. **Join the Community**: Check the main README for community links

## 🆘 Getting Help

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting) above
2. Review the [main documentation](../../README.md)
3. Check existing [GitHub issues](https://github.com/your-repo/opencode-slack/issues)
4. Create a new issue with detailed information

---

*Setup complete! You're ready to start managing your AI employee team.*