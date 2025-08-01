#!/usr/bin/env python3
"""
Quick test to check if environment variables are loading correctly.
"""

import os
from pathlib import Path

def test_env_loading():
    print("🔍 ENVIRONMENT VARIABLE TEST")
    print("=" * 40)
    
    # Try to load .env file
    try:
        from dotenv import load_dotenv
        
        # Check for .env file in project root
        project_root = Path(__file__).parent
        env_path = project_root / '.env'
        
        print(f"📁 Project root: {project_root}")
        print(f"📄 Looking for .env at: {env_path}")
        print(f"📄 .env exists: {env_path.exists()}")
        
        if env_path.exists():
            # Show .env file contents (without sensitive data)
            with open(env_path, 'r') as f:
                content = f.read()
                print(f"📄 .env file contents:")
                for line in content.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        key = line.split('=')[0]
                        print(f"   {key}=***")
            
            # Load the .env file
            load_dotenv(env_path)
            print("✅ .env file loaded successfully")
        else:
            print("❌ .env file not found")
            print("💡 Create it with:")
            print("   echo 'TELEGRAM_BOT_TOKEN=your_token' > .env")
            print("   echo 'TELEGRAM_CHAT_ID=your_chat_id' >> .env")
        
    except ImportError:
        print("❌ python-dotenv not installed")
        print("💡 Install with: pip install python-dotenv")
        return False
    
    # Check environment variables
    print("\n🔧 ENVIRONMENT VARIABLES:")
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    print(f"🤖 TELEGRAM_BOT_TOKEN: {'✅ Set' if bot_token else '❌ Missing'}")
    if bot_token:
        print(f"   Value: {bot_token[:10]}...{bot_token[-10:] if len(bot_token) > 20 else bot_token}")
    
    print(f"💬 TELEGRAM_CHAT_ID: {'✅ Set' if chat_id else '❌ Missing'}")
    if chat_id:
        print(f"   Value: {chat_id}")
    
    # Test the chat config
    print("\n⚙️ TESTING CHAT CONFIG:")
    try:
        from src.chat.chat_config import config
        print(f"✅ Chat config loaded")
        print(f"🔧 Is configured: {config.is_configured()}")
        print(f"🤖 Bot token set: {'Yes' if config.bot_token else 'No'}")
        print(f"💬 Chat ID set: {'Yes' if config.chat_id else 'No'}")
    except Exception as e:
        print(f"❌ Error loading chat config: {e}")
    
    return bot_token and chat_id

if __name__ == "__main__":
    success = test_env_loading()
    
    if success:
        print("\n🎉 Environment is configured correctly!")
        print("💡 Now run: python3 src/cli_server.py")
        print("   Then: chat-status")
    else:
        print("\n❌ Environment needs configuration")
        print("💡 Follow these steps:")
        print("   1. Create .env file in project root")
        print("   2. Add your bot token and chat ID")
        print("   3. Run this test again")