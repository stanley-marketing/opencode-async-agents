#!/bin/bash
# Demo script for opencode-slack CLI server

echo "=== opencode-slack CLI Demo ==="
echo "This demo shows how to use the CLI server"
echo

# Create a demo script
cat > demo_commands.txt << 'EOF'
hire sarah developer
hire dev-2 developer
hire analyst-1 analyst
employees
lock sarah src/auth.py,src/user.py implement user authentication
lock dev-2 src/api.py implement API endpoints
lock analyst-1 docs/requirements.md analyze user requirements
files
request dev-2 src/auth.py need auth module for API integration
files
progress
release sarah src/user.py
files
fire analyst-1
employees
quit
EOF

echo "Running demo commands..."
echo

# Run the demo
cat demo_commands.txt | python3 src/cli_server.py

echo
echo "=== Demo Complete ==="
echo "You can run the CLI server interactively with:"
echo "  python3 src/cli_server.py"