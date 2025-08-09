#!/usr/bin/env python3
"""
Start Async Server for Stress Testing
Starts the optimized async server with performance configurations
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def start_async_server():
    """Start the async server for stress testing"""
    print("🚀 Starting OpenCode-Slack Async Server for Stress Testing")
    print("=" * 60)
    
    # Check if async server exists
    async_server_path = Path(__file__).parent / "src" / "async_server.py"
    if not async_server_path.exists():
        print(f"❌ Async server not found at {async_server_path}")
        print("Please ensure the async server is implemented.")
        return 1
    
    # Set environment variables for optimal performance
    os.environ['MAX_CONCURRENT_TASKS'] = '100'
    os.environ['MAX_DB_CONNECTIONS'] = '50'
    os.environ['ENABLE_WAL_MODE'] = 'true'
    os.environ['BATCH_SIZE'] = '100'
    os.environ['CACHE_TTL_SECONDS'] = '30'
    os.environ['MAX_API_REQUESTS_PER_MINUTE'] = '200'
    
    print("✅ Performance environment variables set:")
    print(f"   MAX_CONCURRENT_TASKS: {os.environ['MAX_CONCURRENT_TASKS']}")
    print(f"   MAX_DB_CONNECTIONS: {os.environ['MAX_DB_CONNECTIONS']}")
    print(f"   ENABLE_WAL_MODE: {os.environ['ENABLE_WAL_MODE']}")
    print(f"   BATCH_SIZE: {os.environ['BATCH_SIZE']}")
    print(f"   CACHE_TTL_SECONDS: {os.environ['CACHE_TTL_SECONDS']}")
    print(f"   MAX_API_REQUESTS_PER_MINUTE: {os.environ['MAX_API_REQUESTS_PER_MINUTE']}")
    print()
    
    try:
        # Import and start the async server
        from src.async_server import main as async_server_main
        
        print("🔥 Starting async server on http://localhost:8080")
        print("Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # Run the async server
        asyncio.run(async_server_main())
        
    except ImportError as e:
        print(f"❌ Failed to import async server: {e}")
        print("Falling back to basic server startup...")
        
        # Fallback: try to run the server directly
        import subprocess
        try:
            subprocess.run([
                sys.executable, 
                str(async_server_path),
                "--host", "0.0.0.0",
                "--port", "8080",
                "--max-concurrent-tasks", "100"
            ])
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return 1
    
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return 0
    
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        return 1

if __name__ == "__main__":
    exit(start_async_server())