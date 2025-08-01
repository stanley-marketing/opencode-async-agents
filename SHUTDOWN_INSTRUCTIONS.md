# Proper Server Shutdown Instructions

## Normal Shutdown (Recommended)

To properly shut down the OpenCode-Slack server:

1. **Using Ctrl+C** (if running in foreground):
   ```bash
   ./run.sh server
   # Press Ctrl+C to stop gracefully
   ```

2. **Using kill command** (if running in background):
   ```bash
   # Start server in background
   ./run.sh server & 
   # Get the process ID
   SERVER_PID=$!
   # Stop the server
   kill $SERVER_PID
   ```

## Force Shutdown (If Normal Shutdown Fails)

If the server hangs during shutdown:

```bash
# Find the server process
ps aux | grep "src.server"
# Kill it forcefully
kill -9 <process_id>
```

## What Happens During Proper Shutdown

1. Telegram polling is stopped and waits for the thread to finish (up to 10 seconds)
2. All active tasks are stopped
3. The Flask server is shut down
4. The process exits cleanly

## Common Issues and Solutions

### Server Hangs on Shutdown
This is now fixed in the latest version. If you still experience hanging:

1. Check for any ongoing Telegram API calls
2. Ensure no infinite loops in agent tasks
3. Use the force shutdown method above

### Telegram Conflicts
The system now automatically:
- Clears existing webhooks before starting polling
- Handles 409 conflict errors gracefully
- Resolves polling conflicts automatically