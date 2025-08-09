#!/bin/bash

# OpenCode-Slack Phase 2 Comprehensive Stress Testing Suite
# Validates all performance optimizations under extreme load conditions

set -e

echo "🔥 OpenCode-Slack Phase 2 Comprehensive Stress Testing Suite"
echo "=============================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    exit 1
fi

print_success "Python 3 found: $(python3 --version)"

# Check if required packages are installed
print_status "Checking required packages..."

REQUIRED_PACKAGES=("aiohttp" "psutil" "fastapi" "uvicorn")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    print_warning "Missing packages: ${MISSING_PACKAGES[*]}"
    print_status "Installing missing packages..."
    pip3 install "${MISSING_PACKAGES[@]}"
fi

print_success "All required packages are available"

# Check if async server is available
if [ ! -f "src/async_server.py" ]; then
    print_warning "Async server not found. Using fallback server configuration."
    
    # Create a simple fallback server if needed
    if [ ! -f "src/server.py" ]; then
        print_error "No server implementation found. Please ensure server files exist."
        exit 1
    fi
fi

# Function to check if server is running
check_server() {
    local url="$1"
    local max_attempts=30
    local attempt=1
    
    print_status "Checking if server is running at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url/health" > /dev/null 2>&1; then
            print_success "Server is responding at $url"
            return 0
        fi
        
        if [ $attempt -eq 1 ]; then
            print_status "Waiting for server to start..."
        fi
        
        sleep 2
        ((attempt++))
    done
    
    print_error "Server is not responding at $url after $max_attempts attempts"
    return 1
}

# Function to start server in background
start_server() {
    print_status "Starting OpenCode-Slack async server..."
    
    # Set performance environment variables
    export MAX_CONCURRENT_TASKS=100
    export MAX_DB_CONNECTIONS=50
    export ENABLE_WAL_MODE=true
    export BATCH_SIZE=100
    export CACHE_TTL_SECONDS=30
    export MAX_API_REQUESTS_PER_MINUTE=200
    
    # Try to start async server
    if [ -f "src/async_server.py" ]; then
        print_status "Starting optimized async server..."
        python3 src/async_server.py --host 0.0.0.0 --port 8080 &
        SERVER_PID=$!
    elif [ -f "src/server.py" ]; then
        print_status "Starting fallback server..."
        python3 src/server.py &
        SERVER_PID=$!
    else
        print_error "No server implementation found"
        exit 1
    fi
    
    # Wait for server to start
    sleep 5
    
    # Check if server is running
    if ! check_server "http://localhost:8080"; then
        print_error "Failed to start server"
        if [ ! -z "$SERVER_PID" ]; then
            kill $SERVER_PID 2>/dev/null || true
        fi
        exit 1
    fi
    
    print_success "Server started successfully (PID: $SERVER_PID)"
}

# Function to stop server
stop_server() {
    if [ ! -z "$SERVER_PID" ]; then
        print_status "Stopping server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
        print_success "Server stopped"
    fi
}

# Function to run stress tests
run_stress_tests() {
    print_status "Running comprehensive stress tests..."
    
    # Create logs directory
    mkdir -p logs
    
    # Run the comprehensive stress test
    if python3 run_comprehensive_stress_test.py; then
        print_success "Stress tests completed successfully!"
        return 0
    else
        print_error "Stress tests failed!"
        return 1
    fi
}

# Function to generate summary report
generate_summary() {
    print_status "Generating test summary..."
    
    # Find the latest test report
    LATEST_REPORT=$(ls -t comprehensive_stress_test_report_*.json 2>/dev/null | head -n1)
    
    if [ -z "$LATEST_REPORT" ]; then
        print_warning "No test report found"
        return 1
    fi
    
    print_success "Latest test report: $LATEST_REPORT"
    
    # Extract key metrics using Python
    python3 -c "
import json
import sys

try:
    with open('$LATEST_REPORT', 'r') as f:
        report = json.load(f)
    
    print('\\n🎯 PHASE 2 STRESS TEST SUMMARY')
    print('=' * 50)
    
    # Overall performance
    overall = report.get('overall_performance', {})
    print(f'📈 Performance Grade: {overall.get(\"performance_grade\", \"N/A\")}')
    print(f'📊 Success Rate: {overall.get(\"overall_success_rate\", 0):.1f}%')
    print(f'🚀 Peak Throughput: {overall.get(\"peak_throughput\", 0):.1f} ops/sec')
    print(f'⏱️  Avg Response Time: {overall.get(\"avg_response_time\", 0):.3f}s')
    print(f'💻 Peak CPU: {overall.get(\"peak_cpu_usage\", 0):.1f}%')
    print(f'🧠 Peak Memory: {overall.get(\"peak_memory_usage_mb\", 0):.1f} MB')
    
    # Phase 2 validation
    validation = report.get('phase_2_validation', {})
    capacity = validation.get('maximum_capacity_achieved', {})
    optimizations = validation.get('performance_optimizations_validated', {})
    
    print('\\n🎯 PHASE 2 CAPACITY VALIDATION')
    print('-' * 30)
    print(f'👥 User Capacity (10x): {\"✅\" if capacity.get(\"user_capacity_10x\") else \"❌\"}')
    print(f'🤖 Agent Capacity (5x): {\"✅\" if capacity.get(\"agent_capacity_5x\") else \"❌\"}')
    print(f'📋 Task Capacity (4x): {\"✅\" if capacity.get(\"task_capacity_4x\") else \"❌\"}')
    print(f'💬 Message Throughput: {\"✅\" if capacity.get(\"message_throughput_1000\") else \"❌\"}')
    
    print('\\n⚡ OPTIMIZATION VALIDATION')
    print('-' * 30)
    print(f'🔄 Async LLM Processing: {\"✅\" if optimizations.get(\"async_llm_processing\") else \"❌\"}')
    print(f'🗄️  Database Optimization: {\"✅\" if optimizations.get(\"database_optimization\") else \"❌\"}')
    print(f'🌐 HTTP Optimization: {\"✅\" if optimizations.get(\"http_optimization\") else \"❌\"}')
    
    # Production readiness
    readiness = report.get('production_readiness', {})
    print('\\n🏭 PRODUCTION READINESS')
    print('-' * 30)
    print(f'📊 Readiness Level: {readiness.get(\"readiness_level\", \"Unknown\")}')
    print(f'✅ Criteria Met: {readiness.get(\"criteria_met\", 0)}/{readiness.get(\"total_criteria\", 0)} ({readiness.get(\"readiness_percentage\", 0):.1f}%)')
    print(f'🚀 Enterprise Ready: {\"✅\" if readiness.get(\"overall_ready\") else \"❌\"}')
    
    # Bottlenecks
    bottlenecks = report.get('bottlenecks_identified', [])
    if bottlenecks:
        print('\\n🔍 BOTTLENECKS IDENTIFIED')
        print('-' * 30)
        for bottleneck in bottlenecks[:3]:  # Show top 3
            print(f'   • {bottleneck.get(\"component\", \"Unknown\")}: {bottleneck.get(\"severity\", \"Unknown\")} severity')
    
    # Recommendations
    recommendations = report.get('recommendations', {})
    immediate = recommendations.get('immediate_actions', [])
    if immediate:
        print('\\n⚠️  IMMEDIATE ACTIONS REQUIRED')
        print('-' * 30)
        for action in immediate[:3]:  # Show top 3
            print(f'   • {action}')
    
    print('\\n' + '=' * 50)
    
except Exception as e:
    print(f'Error reading report: {e}')
    sys.exit(1)
"
}

# Main execution
main() {
    print_status "Starting Phase 2 comprehensive stress testing..."
    
    # Trap to ensure cleanup
    trap 'stop_server; exit 1' INT TERM
    
    # Start server
    start_server
    
    # Run stress tests
    if run_stress_tests; then
        print_success "All stress tests completed successfully!"
        
        # Generate summary
        generate_summary
        
        # Stop server
        stop_server
        
        print_success "Phase 2 stress testing completed!"
        print_status "Check the generated JSON report for detailed results."
        
        return 0
    else
        print_error "Stress tests failed!"
        stop_server
        return 1
    fi
}

# Check if we're being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi