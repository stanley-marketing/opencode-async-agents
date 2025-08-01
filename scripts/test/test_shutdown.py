#!/usr/bin/env python3
"""
Test script to verify proper server shutdown
"""
import signal
import sys
import time
import threading
from src.server import OpencodeSlackServer

def test_shutdown():
    """Test that server shuts down properly"""
    print("🔧 Starting server shutdown test...")
    
    # Create server instance
    server = OpencodeSlackServer(host="localhost", port=8081)
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    
    print("🚀 Server started in background thread")
    
    # Give server time to initialize
    time.sleep(2)
    
    # Send shutdown signal
    print("🛑 Sending shutdown signal...")
    server.stop()
    
    # Wait a bit to see if shutdown completes
    time.sleep(3)
    
    print("✅ Shutdown test completed")

if __name__ == "__main__":
    test_shutdown()