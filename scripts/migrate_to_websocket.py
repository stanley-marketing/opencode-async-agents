#!/usr/bin/env python3
"""
Migration script to transition from Telegram to WebSocket communication.
Provides safe migration with rollback capabilities.
"""

import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chat.communication_manager import CommunicationManager
from src.config.logging_config import setup_logging

logger = logging.getLogger(__name__)


class WebSocketMigrationManager:
    """Manages the migration from Telegram to WebSocket communication"""
    
    def __init__(self, backup_dir: str = "migration_backup"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.migration_log = []
        
    def log_step(self, step: str, status: str = "INFO", details: str = ""):
        """Log migration step"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'status': status,
            'details': details
        }
        self.migration_log.append(entry)
        logger.info(f"[{status}] {step}: {details}")
        
    def backup_configuration(self) -> bool:
        """Backup current configuration"""
        try:
            self.log_step("Backup Configuration", "START")
            
            # Backup environment files
            env_files = ['.env', '.env.local', '.env.production']
            for env_file in env_files:
                env_path = Path(env_file)
                if env_path.exists():
                    backup_path = self.backup_dir / f"{env_file}.backup"
                    shutil.copy2(env_path, backup_path)
                    self.log_step("Backup Configuration", "INFO", f"Backed up {env_file}")
                    
            # Backup server configuration
            config_files = [
                'config/config.yaml',
                'src/chat/chat_config.py'
            ]
            
            for config_file in config_files:
                config_path = Path(config_file)
                if config_path.exists():
                    backup_path = self.backup_dir / config_path.name
                    shutil.copy2(config_path, backup_path)
                    self.log_step("Backup Configuration", "INFO", f"Backed up {config_file}")
                    
            self.log_step("Backup Configuration", "SUCCESS", "Configuration backup completed")
            return True
            
        except Exception as e:
            self.log_step("Backup Configuration", "ERROR", str(e))
            return False
            
    def test_websocket_connectivity(self, host: str = "localhost", port: int = 8765) -> bool:
        """Test WebSocket server connectivity"""
        try:
            self.log_step("Test WebSocket", "START", f"Testing connection to {host}:{port}")
            
            # Create WebSocket manager
            comm_manager = CommunicationManager(
                transport_type='websocket',
                host=host,
                port=port
            )
            
            # Start server
            comm_manager.start_polling()
            time.sleep(2)  # Give server time to start
            
            # Check if server is running
            if comm_manager.is_connected():
                self.log_step("Test WebSocket", "SUCCESS", "WebSocket server is running")
                comm_manager.stop_polling()
                return True
            else:
                self.log_step("Test WebSocket", "ERROR", "WebSocket server failed to start")
                return False
                
        except Exception as e:
            self.log_step("Test WebSocket", "ERROR", str(e))
            return False
            
    def update_environment_variables(self, websocket_host: str, websocket_port: int) -> bool:
        """Update environment variables for WebSocket"""
        try:
            self.log_step("Update Environment", "START")
            
            # Read current .env file
            env_path = Path('.env')
            env_content = {}
            
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_content[key.strip()] = value.strip()
                            
            # Update WebSocket configuration
            env_content['OPENCODE_TRANSPORT'] = 'websocket'
            env_content['WEBSOCKET_HOST'] = websocket_host
            env_content['WEBSOCKET_PORT'] = str(websocket_port)
            env_content['OPENCODE_SAFE_MODE'] = 'false'
            
            # Write updated .env file
            with open(env_path, 'w') as f:
                f.write("# OpenCode-Slack Configuration\n")
                f.write("# Updated for WebSocket transport\n\n")
                
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
                    
            self.log_step("Update Environment", "SUCCESS", "Environment variables updated")
            return True
            
        except Exception as e:
            self.log_step("Update Environment", "ERROR", str(e))
            return False
            
    def test_agent_communication(self) -> bool:
        """Test agent communication with WebSocket"""
        try:
            self.log_step("Test Agent Communication", "START")
            
            # Import test modules
            from tests.test_websocket_integration import WebSocketTestClient
            import asyncio
            
            async def test_communication():
                # Start WebSocket server
                comm_manager = CommunicationManager(transport_type='websocket')
                comm_manager.start_polling()
                
                await asyncio.sleep(1)  # Wait for server to start
                
                # Create test client
                client = WebSocketTestClient("ws://localhost:8765", "test_user", "developer")
                
                try:
                    # Test connection
                    connected = await client.connect()
                    if not connected:
                        return False
                        
                    # Test message sending
                    await client.send_message("Test message")
                    message = await client.wait_for_message(timeout=5)
                    
                    if message and message.get('type') == 'chat_message':
                        return True
                    else:
                        return False
                        
                finally:
                    await client.disconnect()
                    comm_manager.stop_polling()
                    
            # Run async test
            result = asyncio.run(test_communication())
            
            if result:
                self.log_step("Test Agent Communication", "SUCCESS", "Agent communication working")
            else:
                self.log_step("Test Agent Communication", "ERROR", "Agent communication failed")
                
            return result
            
        except Exception as e:
            self.log_step("Test Agent Communication", "ERROR", str(e))
            return False
            
    def update_server_startup_scripts(self) -> bool:
        """Update server startup scripts to use WebSocket"""
        try:
            self.log_step("Update Startup Scripts", "START")
            
            # Update start_async_server.sh
            startup_script = Path("start_async_server.sh")
            if startup_script.exists():
                with open(startup_script, 'r') as f:
                    content = f.read()
                    
                # Replace server command
                content = content.replace(
                    'python src/enhanced_server.py',
                    'python src/server_websocket.py'
                )
                
                with open(startup_script, 'w') as f:
                    f.write(content)
                    
                self.log_step("Update Startup Scripts", "INFO", "Updated start_async_server.sh")
                
            # Update docker-compose.yml if it exists
            docker_compose = Path("docker-compose.yml")
            if docker_compose.exists():
                with open(docker_compose, 'r') as f:
                    content = f.read()
                    
                # Add WebSocket port mapping
                if 'ports:' in content and '8765:8765' not in content:
                    content = content.replace(
                        '- "8080:8080"',
                        '- "8080:8080"\n      - "8765:8765"'
                    )
                    
                with open(docker_compose, 'w') as f:
                    f.write(content)
                    
                self.log_step("Update Startup Scripts", "INFO", "Updated docker-compose.yml")
                
            self.log_step("Update Startup Scripts", "SUCCESS", "Startup scripts updated")
            return True
            
        except Exception as e:
            self.log_step("Update Startup Scripts", "ERROR", str(e))
            return False
            
    def create_frontend_config(self, websocket_host: str, websocket_port: int) -> bool:
        """Create frontend configuration for WebSocket"""
        try:
            self.log_step("Create Frontend Config", "START")
            
            # Create frontend directory if it doesn't exist
            frontend_dir = Path("frontend")
            frontend_dir.mkdir(exist_ok=True)
            
            # Create Next.js configuration
            next_config = {
                "env": {
                    "WEBSOCKET_URL": f"ws://{websocket_host}:{websocket_port}",
                    "API_URL": f"http://{websocket_host}:8080"
                }
            }
            
            with open(frontend_dir / "next.config.js", 'w') as f:
                f.write(f"""/** @type {{import('next').NextConfig}} */
const nextConfig = {{
  env: {json.dumps(next_config['env'], indent=4)}
}}

module.exports = nextConfig
""")
            
            # Create environment file for frontend
            with open(frontend_dir / ".env.local", 'w') as f:
                f.write(f"NEXT_PUBLIC_WEBSOCKET_URL=ws://{websocket_host}:{websocket_port}\n")
                f.write(f"NEXT_PUBLIC_API_URL=http://{websocket_host}:8080\n")
                
            self.log_step("Create Frontend Config", "SUCCESS", "Frontend configuration created")
            return True
            
        except Exception as e:
            self.log_step("Create Frontend Config", "ERROR", str(e))
            return False
            
    def rollback_migration(self) -> bool:
        """Rollback migration to previous state"""
        try:
            self.log_step("Rollback Migration", "START")
            
            # Restore backed up files
            backup_files = list(self.backup_dir.glob("*"))
            
            for backup_file in backup_files:
                if backup_file.name.endswith('.backup'):
                    original_name = backup_file.name.replace('.backup', '')
                    original_path = Path(original_name)
                    
                    shutil.copy2(backup_file, original_path)
                    self.log_step("Rollback Migration", "INFO", f"Restored {original_name}")
                    
            self.log_step("Rollback Migration", "SUCCESS", "Migration rollback completed")
            return True
            
        except Exception as e:
            self.log_step("Rollback Migration", "ERROR", str(e))
            return False
            
    def save_migration_log(self):
        """Save migration log to file"""
        log_file = self.backup_dir / f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(log_file, 'w') as f:
            json.dump(self.migration_log, f, indent=2)
            
        logger.info(f"Migration log saved to {log_file}")
        
    def run_migration(self, websocket_host: str = "localhost", websocket_port: int = 8765, 
                     test_mode: bool = False) -> bool:
        """Run complete migration process"""
        try:
            logger.info("Starting WebSocket migration process...")
            
            # Step 1: Backup current configuration
            if not self.backup_configuration():
                logger.error("Failed to backup configuration")
                return False
                
            # Step 2: Test WebSocket connectivity
            if not self.test_websocket_connectivity(websocket_host, websocket_port):
                logger.error("WebSocket connectivity test failed")
                if not test_mode:
                    self.rollback_migration()
                return False
                
            # Step 3: Update environment variables
            if not self.update_environment_variables(websocket_host, websocket_port):
                logger.error("Failed to update environment variables")
                if not test_mode:
                    self.rollback_migration()
                return False
                
            # Step 4: Test agent communication
            if not self.test_agent_communication():
                logger.error("Agent communication test failed")
                if not test_mode:
                    self.rollback_migration()
                return False
                
            # Step 5: Update startup scripts
            if not self.update_server_startup_scripts():
                logger.error("Failed to update startup scripts")
                if not test_mode:
                    self.rollback_migration()
                return False
                
            # Step 6: Create frontend configuration
            if not self.create_frontend_config(websocket_host, websocket_port):
                logger.error("Failed to create frontend configuration")
                if not test_mode:
                    self.rollback_migration()
                return False
                
            logger.info("WebSocket migration completed successfully!")
            self.log_step("Migration Complete", "SUCCESS", "All migration steps completed")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.log_step("Migration Failed", "ERROR", str(e))
            
            if not test_mode:
                self.rollback_migration()
                
            return False
            
        finally:
            self.save_migration_log()


def main():
    """Main migration script"""
    parser = argparse.ArgumentParser(description='Migrate from Telegram to WebSocket communication')
    parser.add_argument('--host', default='localhost', help='WebSocket host (default: localhost)')
    parser.add_argument('--port', type=int, default=8765, help='WebSocket port (default: 8765)')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode (no rollback on failure)')
    parser.add_argument('--rollback', action='store_true', help='Rollback previous migration')
    parser.add_argument('--backup-dir', default='migration_backup', help='Backup directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(cli_mode=True)
    logging.getLogger().setLevel(log_level)
    
    # Create migration manager
    migration_manager = WebSocketMigrationManager(args.backup_dir)
    
    try:
        if args.rollback:
            # Rollback migration
            logger.info("Rolling back migration...")
            success = migration_manager.rollback_migration()
            
            if success:
                logger.info("Migration rollback completed successfully")
                sys.exit(0)
            else:
                logger.error("Migration rollback failed")
                sys.exit(1)
        else:
            # Run migration
            success = migration_manager.run_migration(
                websocket_host=args.host,
                websocket_port=args.port,
                test_mode=args.test_mode
            )
            
            if success:
                logger.info("Migration completed successfully!")
                logger.info(f"WebSocket server will run on {args.host}:{args.port}")
                logger.info("You can now start the server with: python src/server_websocket.py")
                logger.info("Frontend can connect to: ws://{args.host}:{args.port}")
                sys.exit(0)
            else:
                logger.error("Migration failed")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()