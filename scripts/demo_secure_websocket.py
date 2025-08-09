#!/usr/bin/env python3
"""
Demonstration script for secure WebSocket implementation.
Shows how to use the secure WebSocket manager with all security features enabled.
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from security.websocket_integration import SecureWebSocketManager
from config.secure_config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecureWebSocketDemo:
    """Demonstration of secure WebSocket functionality"""
    
    def __init__(self):
        self.config = get_config()
        self.secure_manager = None
        
    def setup_security_handlers(self):
        """Setup custom security event handlers"""
        
        def security_event_handler(event):
            """Handle security events"""
            logger.info(f"Security Event: {event['event_type']} from {event['source_ip']}")
            
            # Handle critical events
            if event['level'] == 'critical':
                logger.critical(f"CRITICAL SECURITY EVENT: {event}")
                # In production, this would trigger alerts
                
            # Handle authentication events
            if event['event_type'] in ['auth_success', 'auth_failure']:
                logger.info(f"Authentication: {event['event_type']} for user {event.get('user_id', 'unknown')}")
        
        def message_handler(parsed_message):
            """Handle parsed messages with security context"""
            logger.info(f"Secure message from {parsed_message.sender}: {parsed_message.text[:50]}...")
            
            # Process commands securely
            if parsed_message.is_command:
                logger.info(f"Secure command: {parsed_message.command} with args {parsed_message.command_args}")
        
        # Register handlers
        self.secure_manager.add_security_event_handler(security_event_handler)
        self.secure_manager.add_message_handler(message_handler)
    
    def start_secure_server(self):
        """Start the secure WebSocket server"""
        try:
            # Create secure WebSocket manager
            self.secure_manager = SecureWebSocketManager(
                host="localhost",
                port=8765,
                config=self.config
            )
            
            # Setup security handlers
            self.setup_security_handlers()
            
            logger.info("Starting secure WebSocket server...")
            
            # Start the server
            self.secure_manager.start_polling()
            
            # Display server information
            self.display_server_info()
            
            # Monitor security status
            self.monitor_security_status()
            
        except Exception as e:
            logger.error(f"Failed to start secure server: {e}")
            raise
    
    def display_server_info(self):
        """Display server information and security status"""
        print("\n" + "="*60)
        print("SECURE WEBSOCKET SERVER STARTED")
        print("="*60)
        print(f"Host: localhost")
        print(f"Port: 8765")
        print(f"WebSocket URL: ws://localhost:8765")
        print(f"Started at: {datetime.now().isoformat()}")
        
        # Get security status
        security_status = self.secure_manager.get_security_status()
        
        print("\nSECURITY STATUS:")
        print(f"  Authentication Methods: {security_status['authentication_methods']}")
        print(f"  Rate Limiting: Enabled")
        print(f"  Input Validation: Enabled")
        print(f"  Audit Logging: Enabled")
        print(f"  CSRF Protection: Enabled")
        
        print("\nSUPPORTED FEATURES:")
        print("  ✓ JWT Authentication")
        print("  ✓ API Key Authentication")
        print("  ✓ Session Management")
        print("  ✓ Role-Based Access Control")
        print("  ✓ Message Validation & Sanitization")
        print("  ✓ XSS Protection")
        print("  ✓ Rate Limiting")
        print("  ✓ Audit Logging")
        print("  ✓ Real-time Security Monitoring")
        
        print("\nCLIENT CONNECTION EXAMPLES:")
        print("  JavaScript:")
        print("    const ws = new WebSocket('ws://localhost:8765');")
        print("    ws.onopen = () => {")
        print("      ws.send(JSON.stringify({")
        print("        type: 'auth',")
        print("        method: 'jwt',")
        print("        token: 'your_jwt_token'")
        print("      }));")
        print("    };")
        
        print("\n  Python:")
        print("    import websockets")
        print("    import json")
        print("    async with websockets.connect('ws://localhost:8765') as ws:")
        print("      await ws.send(json.dumps({")
        print("        'type': 'auth',")
        print("        'method': 'jwt',")
        print("        'token': 'your_jwt_token'")
        print("      }))")
        
        print("\nSECURITY TESTING:")
        print("  Run security tests with:")
        print("    python scripts/security_testing.py --host localhost --port 8765")
        
        print("\n" + "="*60)
    
    def monitor_security_status(self):
        """Monitor and display security status periodically"""
        import threading
        import time
        
        def security_monitor():
            while self.secure_manager.is_running:
                try:
                    time.sleep(30)  # Check every 30 seconds
                    
                    # Get current security status
                    status = self.secure_manager.get_security_status()
                    
                    # Log security metrics
                    logger.info(f"Security Status - Active Connections: {status['active_connections']}, "
                              f"Security Events: {status['security_events_recent']}, "
                              f"Blocked IPs: {status['security']['blocked_ips']}")
                    
                    # Check for security alerts
                    if status['security']['blocked_ips'] > 0:
                        logger.warning(f"Security Alert: {status['security']['blocked_ips']} IPs currently blocked")
                    
                except Exception as e:
                    logger.error(f"Security monitoring error: {e}")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=security_monitor, daemon=True)
        monitor_thread.start()
        logger.info("Security monitoring started")
    
    def stop_server(self):
        """Stop the secure WebSocket server"""
        if self.secure_manager:
            logger.info("Stopping secure WebSocket server...")
            self.secure_manager.stop_polling()
            logger.info("Secure WebSocket server stopped")

def create_demo_users():
    """Create demo users for testing"""
    from security.auth import auth_manager
    
    # Create demo users with different roles
    demo_users = [
        {'username': 'admin_user', 'password': 'SecureAdmin123!', 'roles': ['admin'], 'permissions': ['*']},
        {'username': 'mod_user', 'password': 'SecureMod123!', 'roles': ['moderator'], 'permissions': ['chat.*', 'tasks.read', 'tasks.create']},
        {'username': 'regular_user', 'password': 'SecureUser123!', 'roles': ['user'], 'permissions': ['chat.send', 'chat.read', 'tasks.read']},
        {'username': 'guest_user', 'password': 'SecureGuest123!', 'roles': ['guest'], 'permissions': ['chat.read']}
    ]
    
    for user_data in demo_users:
        success = auth_manager.create_user(
            user_data['username'],
            user_data['password'],
            user_data['roles'],
            user_data['permissions']
        )
        if success:
            logger.info(f"Created demo user: {user_data['username']} with role {user_data['roles'][0]}")
        else:
            logger.info(f"Demo user already exists: {user_data['username']}")
    
    # Create demo API keys
    api_keys = [
        {'name': 'admin_api_key', 'permissions': ['*']},
        {'name': 'monitoring_api_key', 'permissions': ['monitoring.read', 'chat.read']},
        {'name': 'chat_bot_key', 'permissions': ['chat.send', 'chat.read']}
    ]
    
    for key_data in api_keys:
        try:
            api_key = auth_manager.generate_api_key(
                key_data['name'],
                key_data['permissions']
            )
            logger.info(f"Created API key '{key_data['name']}': {api_key}")
        except Exception as e:
            logger.debug(f"API key creation failed (may already exist): {e}")

def generate_demo_jwt_tokens():
    """Generate demo JWT tokens for testing"""
    from security.auth import auth_manager
    
    demo_users = ['admin_user', 'mod_user', 'regular_user', 'guest_user']
    
    print("\nDEMO JWT TOKENS:")
    print("-" * 40)
    
    for username in demo_users:
        try:
            token = auth_manager.generate_jwt_token(username)
            print(f"{username}: {token}")
        except Exception as e:
            logger.debug(f"Token generation failed for {username}: {e}")

def main():
    """Main function"""
    import signal
    
    # Create demo instance
    demo = SecureWebSocketDemo()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        demo.stop_server()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create demo users and API keys
        logger.info("Setting up demo users and API keys...")
        create_demo_users()
        
        # Generate demo JWT tokens
        generate_demo_jwt_tokens()
        
        # Start secure server
        demo.start_secure_server()
        
        # Keep server running
        logger.info("Secure WebSocket server is running. Press Ctrl+C to stop.")
        
        # Keep the main thread alive
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass
            
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        sys.exit(1)
    finally:
        demo.stop_server()

if __name__ == '__main__':
    main()