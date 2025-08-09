#!/usr/bin/env python3
"""
Fixed OpenCode-Slack server with API endpoint 500 error fixes applied
"""

import sys
import os
import signal
import threading
import time
import json
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.server import OpencodeSlackServer
from api_endpoint_fixes import apply_comprehensive_api_fixes

class FixedOpencodeSlackServer(OpencodeSlackServer):
    """OpenCode-Slack server with API fixes pre-applied"""
    
    def __init__(self, *args, **kwargs):
        # Call parent init
        super().__init__(*args, **kwargs)
        
        # Apply API fixes immediately
        self.logger.info("🔧 Applying API endpoint fixes...")
        success = apply_comprehensive_api_fixes(self)
        if success:
            self.logger.info("✅ API fixes applied successfully!")
            print("🎉 Server started with API fixes applied!")
        else:
            self.logger.error("❌ Failed to apply API fixes")
            print("⚠️  Server started but API fixes failed to apply")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fixed OpenCode-Slack Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8092, help='Port to bind to')
    parser.add_argument('--db-path', default='employees.db', help='Database path')
    parser.add_argument('--sessions-dir', default='sessions', help='Sessions directory')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting Fixed OpenCode-Slack Server on {args.host}:{args.port}")
    print("🔧 This server includes fixes for all API endpoint 500 errors")
    
    # Create and start the fixed server
    server = FixedOpencodeSlackServer(
        host=args.host,
        port=args.port,
        db_path=args.db_path,
        sessions_dir=args.sessions_dir
    )
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        server.shutdown()
        print("✅ Server shutdown complete")

if __name__ == "__main__":
    main()
