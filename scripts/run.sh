#!/bin/bash
# OpenCode-Slack System Launcher
# Usage: 
#   ./run.sh server [options]  - Start the server
#   ./run.sh client [options]  - Start the client
#   ./run.sh help              - Show this help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

show_help() {
    echo "🔥 OpenCode-Slack System Launcher"
    echo ""
    echo "Usage:"
    echo "  ./run.sh server [options]  - Start the opencode-slack server"
    echo "  ./run.sh client [options]  - Start the CLI client"
    echo "  ./run.sh help              - Show this help"
    echo ""
    echo "Server options:"
    echo "  --host HOST                - Host to bind to (default: localhost)"
    echo "  --port PORT                - Port to bind to (default: 8080)"
    echo "  --db-path PATH             - Database path (default: employees.db)"
    echo "  --sessions-dir DIR         - Sessions directory (default: sessions)"
    echo ""
    echo "Client options:"
    echo "  --server URL               - Server URL (default: http://localhost:8080)"
    echo ""
    echo "Examples:"
    echo "  ./run.sh server                                    # Start server on localhost:8080"
    echo "  ./run.sh server --host 0.0.0.0 --port 9000       # Start server on all interfaces, port 9000"
    echo "  ./run.sh client                                    # Connect to localhost:8080"
    echo "  ./run.sh client --server http://remote:9000       # Connect to remote server"
    echo ""
    echo "🚀 Quick Start:"
    echo "  1. Terminal 1: ./run.sh server"
    echo "  2. Terminal 2: ./run.sh client"
    echo "  3. In client: hire john developer"
    echo "  4. In client: assign john 'create hello world app'"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is required but not installed"
        exit 1
    fi
}

install_deps() {
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
}

start_server() {
    echo "🚀 Starting OpenCode-Slack Server..."
    python3 -m src.server "$@"
}

start_client() {
    echo "🔗 Starting OpenCode-Slack Client..."
    python3 -m src.client "$@"
}

main() {
    check_python
    
    if [ $# -eq 0 ]; then
        show_help
        exit 1
    fi
    
    case "$1" in
        server)
            shift
            start_server "$@"
            ;;
        client)
            shift
            start_client "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        install-deps)
            install_deps
            ;;
        *)
            echo "❌ Unknown command: $1"
            echo "Use './run.sh help' for usage information"
            exit 1
            ;;
    esac
}

main "$@"