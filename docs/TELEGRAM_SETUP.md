# Telegram Bot Setup Guide

This guide will help you set up a Telegram bot for the opencode-slack chat system.

## Step 1: Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Start a chat with BotFather and send `/newbot`
3. Follow the prompts:
   - Choose a name for your bot (e.g., "OpenCode Team Bot")
   - Choose a username (must end in 'bot', e.g., "opencode_team_bot")
4. BotFather will give you a bot token. **Save this token securely!**

## Step 2: Create a Group Chat

1. Create a new group in Telegram
2. Add your bot to the group:
   - Go to group settings → Add Members
   - Search for your bot's username and add it
3. Make your bot an admin:
   - Go to group settings → Administrators
   - Add your bot as an administrator
   - Give it permissions to send messages and read message history

## Step 3: Get the Chat ID

1. Add your bot to the group and send a test message in the group
2. Visit this URL in your browser (replace `YOUR_BOT_TOKEN` with your actual token):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
3. Look for the `"chat":{"id":` field in the response. The number after `"id":` is your chat ID
4. **Save this chat ID!**

## Step 4: Configure Environment Variables

Create a `.env` file in your project root with:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Optional: Webhook URL for production (leave empty for polling)
TELEGRAM_WEBHOOK_URL=
```

## Step 5: Test the Setup

Run this test script to verify your setup:

```python
import os
from src.chat.telegram_manager import TelegramManager
from src.chat.chat_config import config

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test connection
manager = TelegramManager()

if manager.is_connected():
    print("✅ Bot is connected!")
    
    # Test sending a message
    success = manager.send_message("🤖 OpenCode team chat is now active!", "system")
    if success:
        print("✅ Test message sent successfully!")
    else:
        print("❌ Failed to send test message")
else:
    print("❌ Bot connection failed. Check your token and configuration.")
```

## Step 6: Start the Chat System

Once configured, you can start the chat system:

```python
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager

# Initialize components
file_manager = FileOwnershipManager()
telegram_manager = TelegramManager()
agent_manager = AgentManager(file_manager, telegram_manager)

# Start polling for messages
telegram_manager.start_polling()

print("🚀 Chat system is running!")
print("Try mentioning an employee in the Telegram group: @elad please add a gradient to the HTML file")
```

## Troubleshooting

### Bot Not Responding
- Check that the bot token is correct
- Verify the bot is added to the group and has admin permissions
- Make sure the chat ID is correct (negative number for groups)

### Permission Errors
- Ensure the bot has "Send Messages" permission in the group
- Check that the bot can read message history

### Connection Issues
- Verify your internet connection
- Check if Telegram API is accessible from your network
- Try using polling instead of webhooks for testing

## Security Notes

- Keep your bot token secret and never commit it to version control
- Use environment variables or secure configuration management
- Consider using webhooks instead of polling for production deployments
- Regularly rotate your bot token if needed

## Next Steps

Once the bot is set up and working:

1. Hire some employees using the CLI: `hire elad FS-developer`
2. Test the chat system by mentioning employees in the Telegram group
3. Watch as communication agents respond and coordinate with worker agents
4. Use the CLI `chat-status` command to monitor the system