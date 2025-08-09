#!/usr/bin/env python3
"""
Apply API endpoint fixes to the running OpenCode-Slack server
This script patches the running server to fix all 500 errors
"""

import sys
import os
import logging
import importlib.util
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def patch_running_server():
    """Patch the running server with API fixes"""
    
    try:
        # Import the server module
        from src.server import OpencodeSlackServer
        
        # Import our fixes
        from api_endpoint_fixes import apply_comprehensive_api_fixes
        
        # Find the running server instance
        # We'll need to monkey-patch the class to apply fixes to new instances
        original_init = OpencodeSlackServer.__init__
        
        def patched_init(self, *args, **kwargs):
            # Call original init
            original_init(self, *args, **kwargs)
            
            # Apply our fixes
            logger.info("🔧 Applying API endpoint fixes to server instance...")
            success = apply_comprehensive_api_fixes(self)
            if success:
                logger.info("✅ API fixes applied successfully!")
            else:
                logger.error("❌ Failed to apply API fixes")
        
        # Monkey patch the class
        OpencodeSlackServer.__init__ = patched_init
        
        logger.info("🎉 Server class patched successfully! New server instances will have fixes applied.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error patching server: {e}")
        return False

def create_fixed_server_script():
    """Create a new server script with fixes pre-applied"""
    
    fixed_server_content = '''#!/usr/bin/env python3
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
        print("\\n🛑 Shutting down server...")
        server.shutdown()
        print("✅ Server shutdown complete")

if __name__ == "__main__":
    main()
'''
    
    try:
        with open('fixed_server.py', 'w') as f:
            f.write(fixed_server_content)
        
        # Make it executable
        os.chmod('fixed_server.py', 0o755)
        
        logger.info("✅ Created fixed_server.py with API fixes pre-applied")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating fixed server script: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoints to verify fixes"""
    
    import requests
    import time
    
    # Test endpoints
    base_url = "http://localhost:8091"
    
    test_cases = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'url': f'{base_url}/health',
            'expected_status': 200
        },
        {
            'name': 'Employee Creation',
            'method': 'POST',
            'url': f'{base_url}/employees',
            'data': {'name': f'test_fixed_user_{int(time.time())}', 'role': 'developer', 'smartness': 'normal'},
            'expected_status': 201
        },
        {
            'name': 'Monitoring Health',
            'method': 'GET',
            'url': f'{base_url}/monitoring/health',
            'expected_status': 200
        },
        {
            'name': 'Monitoring Recovery',
            'method': 'GET',
            'url': f'{base_url}/monitoring/recovery',
            'expected_status': 200
        },
        {
            'name': 'Production Status',
            'method': 'GET',
            'url': f'{base_url}/monitoring/production/status',
            'expected_status': 200
        },
        {
            'name': 'Production Alerts',
            'method': 'GET',
            'url': f'{base_url}/monitoring/production/alerts',
            'expected_status': 200
        }
    ]
    
    results = []
    
    for test in test_cases:
        try:
            if test['method'] == 'GET':
                response = requests.get(test['url'], timeout=10)
            elif test['method'] == 'POST':
                response = requests.post(test['url'], json=test['data'], timeout=10)
            
            success = response.status_code == test['expected_status']
            
            results.append({
                'name': test['name'],
                'status_code': response.status_code,
                'expected': test['expected_status'],
                'success': success,
                'response': response.text[:200] if not success else 'OK'
            })
            
            logger.info(f"{'✅' if success else '❌'} {test['name']}: {response.status_code}")
            
        except Exception as e:
            results.append({
                'name': test['name'],
                'status_code': 'ERROR',
                'expected': test['expected_status'],
                'success': False,
                'response': str(e)
            })
            logger.error(f"❌ {test['name']}: {e}")
    
    return results

if __name__ == "__main__":
    print("🔧 OpenCode-Slack API Endpoint Fixes")
    print("=====================================")
    
    # Create the fixed server script
    print("\\n1. Creating fixed server script...")
    if create_fixed_server_script():
        print("✅ Fixed server script created: fixed_server.py")
        print("   You can start it with: python3 fixed_server.py --port 8092")
    else:
        print("❌ Failed to create fixed server script")
    
    # Test current endpoints
    print("\\n2. Testing current API endpoints...")
    results = test_api_endpoints()
    
    print("\\n📊 Test Results:")
    print("================")
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} {result['name']}: {result['status_code']} (expected {result['expected']})")
        if not result['success'] and result['response']:
            print(f"    Error: {result['response']}")
    
    print(f"\\n📈 Summary: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed < total:
        print("\\n🔧 To fix the remaining issues:")
        print("1. Stop the current server")
        print("2. Start the fixed server: python3 fixed_server.py --port 8092")
        print("3. Test endpoints on the new port")
    else:
        print("\\n🎉 All endpoints are working correctly!")