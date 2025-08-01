#!/usr/bin/env python3
"""
Complete Telegram Bot Cleanup and Test Script
Ensures clean state and tests the bot functionality.
"""

import requests
import sys
import os
import time
import subprocess
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

def load_bot_token():
    """Load bot token from environment"""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()
    except ImportError:
        pass
    
    return os.environ.get('TELEGRAM_BOT_TOKEN')

def kill_existing_processes():
    """Kill any existing opencode-slack processes"""
    print("🔍 Checking for existing processes...")
    
    try:
        # Find processes
        result = subprocess.run(['pgrep', '-f', 'server.py'], capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"   Found {len(pids)} server processes")
            
            for pid in pids:
                try:
                    subprocess.run(['kill', '-TERM', pid], check=True)
                    print(f"   ✅ Terminated process {pid}")
                except subprocess.CalledProcessError:
                    print(f"   ⚠️  Could not terminate process {pid}")
            
            # Wait a moment for processes to shut down
            time.sleep(2)
        else:
            print("   ✅ No existing server processes found")
    
    except FileNotFoundError:
        # pgrep not available, try ps
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            server_lines = [line for line in lines if 'server.py' in line and 'grep' not in line]
            
            if server_lines:
                print(f"   Found {len(server_lines)} potential server processes")
                for line in server_lines:
                    print(f"   📋 {line}")
            else:
                print("   ✅ No server processes found")
        except:
            print("   ⚠️  Could not check for existing processes")

def clear_webhook(bot_token):
    """Clear any existing webhook"""
    print("🧹 Clearing webhook...")
    url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        response = requests.post(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('ok'):
            print("   ✅ Webhook cleared successfully")
            return True
        else:
            print(f"   ❌ Error clearing webhook: {data}")
            return False
    except Exception as e:
        print(f"   ❌ Error clearing webhook: {e}")
        return False

def test_bot_polling(bot_token):
    """Test if bot polling works without conflicts"""
    print("🧪 Testing bot polling...")
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {'limit': 1, 'timeout': 1}
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print("   ✅ Polling test successful!")
                return True
            else:
                print(f"   ❌ API error: {data}")
                return False
        elif response.status_code == 409:
            print("   ❌ 409 Conflict - another instance is still polling")
            print("   💡 Wait a few minutes or restart your system")
            return False
        else:
            print(f"   ❌ HTTP Error {response.status_code}")
            return False
    
    except Exception as e:
        print(f"   ❌ Polling test failed: {e}")
        return False

def start_test_server():
    """Start a test server to verify everything works"""
    print("🚀 Starting test server...")
    
    try:
        # Start server in background
        process = subprocess.Popen([
            'python3', '-m', 'src.server', '--port', '8089'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(3)
        
        # Test health endpoint
        try:
            response = requests.get('http://localhost:8089/health', timeout=5)
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ Server started successfully")
                print(f"   📊 Status: {health['status']}")
                print(f"   💬 Chat: {'✅ Enabled' if health['chat_enabled'] else '❌ Disabled'}")
                print(f"   👥 Agents: {health['total_agents']}")
                
                # Test chat debug endpoint
                try:
                    debug_response = requests.get('http://localhost:8089/chat/debug', timeout=5)
                    if debug_response.status_code == 200:
                        debug_data = debug_response.json()
                        print(f"   🔍 Polling: {'✅ Active' if debug_data.get('polling') else '❌ Inactive'}")
                        
                        webhook_info = debug_data.get('webhook_info', {})
                        if webhook_info.get('url'):
                            print(f"   ⚠️  Webhook still set: {webhook_info['url']}")
                        else:
                            print(f"   ✅ No webhook conflicts")
                except:
                    print("   ⚠️  Could not get debug info")
                
                success = True
            else:
                print(f"   ❌ Server health check failed: {response.status_code}")
                success = False
        except:
            print("   ❌ Could not connect to server")
            success = False
        
        # Stop the test server
        try:
            process.terminate()
            process.wait(timeout=5)
            print("   🛑 Test server stopped")
        except subprocess.TimeoutExpired:
            process.kill()
            print("   🔪 Test server killed")
        
        return success
    
    except Exception as e:
        print(f"   ❌ Error starting test server: {e}")
        return False

def main():
    """Main function"""
    print("🔧 Complete Telegram Bot Cleanup and Test")
    print("=" * 50)
    
    # Load bot token
    bot_token = load_bot_token()
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found")
        return
    
    print(f"🤖 Bot Token: {bot_token[:10]}...{bot_token[-10:]}")
    
    # Step 1: Kill existing processes
    kill_existing_processes()
    
    # Step 2: Clear webhook
    clear_webhook(bot_token)
    
    # Step 3: Wait a moment for everything to settle
    print("⏳ Waiting for cleanup to complete...")
    time.sleep(3)
    
    # Step 4: Test polling
    if test_bot_polling(bot_token):
        print("✅ Bot polling is working!")
    else:
        print("❌ Bot polling still has issues")
        print("\n💡 Troubleshooting steps:")
        print("   1. Wait 5-10 minutes for Telegram to clear conflicts")
        print("   2. Check if any other bot instances are running")
        print("   3. Restart your system if conflicts persist")
        print("   4. Contact @BotFather if issues continue")
        return
    
    # Step 5: Test full server
    if start_test_server():
        print("\n🎉 SUCCESS! Everything is working correctly!")
        print("\n🚀 You can now start your server:")
        print("   ./run.sh server")
        print("   ./run.sh client")
    else:
        print("\n❌ Server test failed")
        print("   Check the logs for more details")

if __name__ == "__main__":
    main()