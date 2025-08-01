#!/usr/bin/env python3
"""
Script to test proper server start/stop control
"""
import threading
import time
import signal
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.server import OpencodeSlackServer

class ServerController:
    def __init__(self):
        self.server = None
        self.server_thread = None
    
    def start_server(self):
        """Start the server in a background thread"""
        print("🔧 Initializing server...")
        self.server = OpencodeSlackServer(host="localhost", port=8082)
        
        print("🚀 Starting server...")
        self.server_thread = threading.Thread(target=self.server.start)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Give server time to start
        time.sleep(2)
        print("✅ Server started")
    
    def stop_server(self):
        """Stop the server gracefully"""
        if self.server:
            print("🛑 Stopping server...")
            self.server.stop()
            print("✅ Server stop command sent")
    
    def wait_for_server(self, timeout=10):
        """Wait for server thread to finish"""
        if self.server_thread:
            self.server_thread.join(timeout=timeout)
            if self.server_thread.is_alive():
                print("⚠️  Server thread still running after timeout")
            else:
                print("✅ Server thread finished")

def signal_handler(signum, frame):
    print(f"\nReceived signal {signum}")
    sys.exit(0)

def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    controller = ServerController()
    
    try:
        # Start server
        controller.start_server()
        
        # Wait a few seconds
        time.sleep(5)
        
        # Stop server
        controller.stop_server()
        
        # Wait for shutdown
        time.sleep(2)
        
        print("✅ Test completed successfully")
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        controller.stop_server()
        time.sleep(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        controller.stop_server()

if __name__ == "__main__":
    main()