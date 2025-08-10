#!/bin/bash
# Quick Start OpenCode-Slack with Optimizations

echo "🚀 Quick Start OpenCode-Slack with Performance Optimizations"
echo "============================================================"

# Check if server is already running
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "⚠️  Server already running on port 8080"
    echo "   Use 'curl http://localhost:8080/health' to check status"
    exit 1
fi

# Start the async server in background
echo "🔧 Starting async server..."
./start_async_server.sh &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ Server started successfully!"
        break
    fi
    sleep 1
done

# Check if server started
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "❌ Server failed to start"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo ""
echo "🎉 OpenCode-Slack is now running with performance optimizations!"
echo ""
echo "📊 Server Status: http://localhost:8080/health"
echo "📈 Performance Metrics: http://localhost:8080/performance"
echo "📚 API Documentation: http://localhost:8080/docs"
echo ""
echo "🧪 To run performance tests:"
echo "   ./run_performance_tests.sh"
echo ""
echo "🛑 To stop the server:"
echo "   kill $SERVER_PID"
echo ""
echo "Server PID: $SERVER_PID"
