# Proper Server Shutdown Instructions

## Normal Shutdown (Recommended)

To properly shut down the OpenCode-Slack server:

1. **Using Ctrl+C** (if running in foreground):
   ```bash
   ./run.sh server
   # Press Ctrl+C to stop immediately
   ```

2. **Using kill command** (if running in background):
   ```bash
   # Start server in background
   ./run.sh server & 
   # Get the process ID
   SERVER_PID=$!
   # Stop the server immediately
   kill $SERVER_PID
   ```

3. **Using SIGTERM for immediate shutdown**:
   ```bash
   # Find the server process
   ps aux | grep "src.server"
   # Stop the server immediately
   kill -TERM <process_id>
   ```

## Force Shutdown (If Needed)

If the server doesn't respond to normal signals:

```bash
# Find the server process
ps aux | grep "src.server"
# Kill it forcefully
kill -9 <process_id>
```

## What Happens During Shutdown

The server now shuts down immediately on any signal:
1. All threads are terminated immediately
2. No waiting for cleanup or graceful shutdown
3. Process exits with code 0

## Common Issues and Solutions

### Server Not Responding to Signals
If the server doesn't respond to Ctrl+C or kill commands:

1. Use `kill -9` for force termination
2. Check for any zombie processes with `ps aux | grep python`

### Telegram Conflicts
The system now automatically:
- Clears existing webhooks before starting polling
- Handles 409 conflict errors gracefully
- Resolves polling conflicts automatically