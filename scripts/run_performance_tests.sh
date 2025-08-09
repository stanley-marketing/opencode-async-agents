#!/bin/bash
# Run Performance Optimization Tests

echo "🧪 Running Performance Optimization Tests..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set test configuration
export ASYNC_SERVER_URL=${ASYNC_SERVER_URL:-http://localhost:8080}

# Run the performance tests
python3 performance_optimization_test.py "$@"
