#!/bin/bash
# Start Async OpenCode-Slack Server

echo "🚀 Starting Async OpenCode-Slack Server..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default values
export HOST=${HOST:-localhost}
export PORT=${PORT:-8080}
export MAX_CONCURRENT_TASKS=${MAX_CONCURRENT_TASKS:-50}
export MAX_CONNECTIONS=${MAX_CONNECTIONS:-20}

# Start the async server
python3 src/async_server.py \
    --host $HOST \
    --port $PORT \
    --max-concurrent-tasks $MAX_CONCURRENT_TASKS \
    --max-connections $MAX_CONNECTIONS \
    "$@"
