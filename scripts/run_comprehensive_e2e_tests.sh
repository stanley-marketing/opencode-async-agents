#!/bin/bash

# 🚀 OpenCode-Slack Comprehensive E2E Test Runner
# Quick start script for running comprehensive end-to-end tests

set -e  # Exit on any error

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    REQUIRED_VERSION="3.8"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        print_success "Python $PYTHON_VERSION detected"
    else
        print_error "Python $PYTHON_VERSION detected, but Python 3.8+ is required"
        exit 1
    fi
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing test dependencies..."
    
    # Check if pip is available
    if ! command_exists pip && ! command_exists pip3; then
        print_error "pip not found. Please install pip"
        exit 1
    fi
    
    PIP_CMD="pip3"
    if ! command_exists pip3; then
        PIP_CMD="pip"
    fi
    
    # Install required packages
    $PIP_CMD install pytest pytest-asyncio pytest-html pytest-cov requests websockets || {
        print_warning "Some dependencies may have failed to install"
        print_warning "Continuing with available packages..."
    }
    
    # Install project dependencies if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        print_status "Installing project dependencies..."
        $PIP_CMD install -r requirements.txt || {
            print_warning "Some project dependencies may have failed to install"
        }
    fi
}

# Function to validate setup
validate_setup() {
    print_status "Validating E2E test setup..."
    
    if [ -f "tests/validate_comprehensive_e2e_setup.py" ]; then
        $PYTHON_CMD tests/validate_comprehensive_e2e_setup.py || {
            print_error "Setup validation failed"
            print_status "Please address the validation issues and try again"
            exit 1
        }
    else
        print_warning "Validation script not found, skipping validation"
    fi
}

# Function to run tests
run_tests() {
    print_status "Running comprehensive E2E tests..."
    
    # Prepare arguments
    ARGS=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --parallel)
                ARGS="$ARGS --parallel"
                shift
                ;;
            --suites)
                ARGS="$ARGS --suites"
                shift
                while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
                    ARGS="$ARGS $1"
                    shift
                done
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                ARGS="$ARGS $1"
                shift
                ;;
        esac
    done
    
    # Run the comprehensive test runner
    if [ -f "tests/run_comprehensive_e2e_tests.py" ]; then
        $PYTHON_CMD tests/run_comprehensive_e2e_tests.py $ARGS
    else
        print_error "Test runner script not found: tests/run_comprehensive_e2e_tests.py"
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "🚀 OpenCode-Slack Comprehensive E2E Test Runner"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --parallel              Run tests in parallel (faster but more resource intensive)"
    echo "  --suites SUITE1 SUITE2  Run specific test suites only"
    echo "  --skip-deps            Skip dependency installation"
    echo "  --skip-validation      Skip setup validation"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Available test suites:"
    echo "  core_system           Core system workflows (hiring, tasks, files, sessions)"
    echo "  agent_communication   Agent communication and collaboration"
    echo "  chat_system          Chat system (WebSocket, Telegram, real-time)"
    echo "  monitoring           Monitoring, performance, and health checks"
    echo "  security             Security, authentication, and authorization"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests sequentially"
    echo "  $0 --parallel                        # Run all tests in parallel"
    echo "  $0 --suites core_system              # Run only core system tests"
    echo "  $0 --suites core_system monitoring   # Run core system and monitoring tests"
    echo ""
    echo "Reports will be generated in:"
    echo "  test_reports/          # Test execution reports"
    echo "  test_screenshots/      # Visual evidence and screenshots"
}

# Function to show results
show_results() {
    print_status "Test execution completed!"
    
    # Check if reports were generated
    if [ -d "test_reports" ]; then
        print_success "Test reports available in: test_reports/"
        
        # List recent reports
        RECENT_REPORTS=$(find test_reports -name "*.html" -o -name "*.json" | head -5)
        if [ ! -z "$RECENT_REPORTS" ]; then
            print_status "Recent reports:"
            echo "$RECENT_REPORTS" | while read -r report; do
                echo "  📄 $report"
            done
        fi
    fi
    
    if [ -d "test_screenshots" ]; then
        print_success "Visual evidence available in: test_screenshots/"
    fi
    
    print_status "For detailed results, check the generated reports"
}

# Main execution
main() {
    echo "🚀 OpenCode-Slack Comprehensive E2E Test Runner"
    echo "================================================"
    
    # Parse skip flags
    SKIP_DEPS=false
    SKIP_VALIDATION=false
    
    for arg in "$@"; do
        case $arg in
            --skip-deps)
                SKIP_DEPS=true
                ;;
            --skip-validation)
                SKIP_VALIDATION=true
                ;;
        esac
    done
    
    # Check prerequisites
    check_python_version
    
    # Install dependencies unless skipped
    if [ "$SKIP_DEPS" = false ]; then
        install_dependencies
    else
        print_warning "Skipping dependency installation"
    fi
    
    # Validate setup unless skipped
    if [ "$SKIP_VALIDATION" = false ]; then
        validate_setup
    else
        print_warning "Skipping setup validation"
    fi
    
    # Set up environment
    export TESTING=true
    export OPENCODE_SAFE_MODE=true
    export LOG_LEVEL=INFO
    
    print_status "Environment configured for testing"
    
    # Run tests
    if run_tests "$@"; then
        print_success "All tests completed successfully!"
        show_results
        exit 0
    else
        print_error "Some tests failed"
        show_results
        exit 1
    fi
}

# Handle Ctrl+C gracefully
trap 'print_warning "Test execution interrupted by user"; exit 130' INT

# Run main function with all arguments
main "$@"