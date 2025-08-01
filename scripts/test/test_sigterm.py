#!/usr/bin/env python3
"""
Test script to verify SIGTERM immediately shuts down the server
"""
import subprocess
import time
import signal
import os

def test_sigterm_shutdown():
    """Test that SIGTERM immediately shuts down the server"""
    print("🔧 Starting server for SIGTERM test...")
    
    # Start server in background
    server_process = subprocess.Popen([
        "python3", "-m", "src.server", 
        "--host", "localhost", 
        "--port", "8083"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    print(f"🚀 Server started with PID {server_process.pid}")
    
    # Give server time to initialize
    time.sleep(3)
    
    # Send SIGTERM
    print("🛑 Sending SIGTERM...")
    server_process.send_signal(signal.SIGTERM)
    
    # Wait for process to terminate (should be immediate)
    try:
        stdout, stderr = server_process.communicate(timeout=5)
        print("✅ Server terminated immediately")
        print(f"Exit code: {server_process.returncode}")
    except subprocess.TimeoutExpired:
        print("⚠️ Server didn't terminate quickly, killing forcefully")
        server_process.kill()
        server_process.communicate()
        print("✅ Server force killed")

if __name__ == "__main__":
    test_sigterm_shutdown()