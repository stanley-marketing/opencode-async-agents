#!/usr/bin/env python3
"""
Telegram Bot Conflict Resolver
Helps diagnose and fix 409 Conflict errors with Telegram bots.
"""

import requests
import sys
import os
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

def check_webhook_status(bot_token):
    """Check current webhook status"""
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('ok'):
            return data.get('result', {})
        else:
            print(f"❌ Error getting webhook info: {data}")
            return None
    except Exception as e:
        print(f"❌ Error checking webhook: {e}")
        return None

def clear_webhook(bot_token):
    """Clear any existing webhook"""
    url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        response = requests.post(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('ok'):
            print("✅ Webhook cleared successfully")
            return True
        else:
            print(f"❌ Error clearing webhook: {data}")
            return False
    except Exception as e:
        print(f"❌ Error clearing webhook: {e}")
        return False

def get_bot_info(bot_token):
    """Get bot information"""
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('ok'):
            return data.get('result', {})
        else:
            print(f"❌ Error getting bot info: {data}")
            return None
    except Exception as e:
        print(f"❌ Error getting bot info: {e}")
        return None

def main():
    """Main function"""
    print("🔧 Telegram Bot Conflict Resolver")
    print("=" * 40)
    
    # Load bot token
    bot_token = load_bot_token()
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        print("   Please set it in your .env file or environment variables")
        return
    
    print(f"🤖 Bot Token: {bot_token[:10]}...{bot_token[-10:]}")
    
    # Get bot info
    print("\n1. 📋 Checking Bot Information...")
    bot_info = get_bot_info(bot_token)
    if bot_info:
        print(f"   ✅ Bot Username: @{bot_info.get('username', 'unknown')}")
        print(f"   ✅ Bot Name: {bot_info.get('first_name', 'unknown')}")
        print(f"   ✅ Can Join Groups: {bot_info.get('can_join_groups', False)}")
        print(f"   ✅ Can Read All Messages: {bot_info.get('can_read_all_group_messages', False)}")
    else:
        print("   ❌ Failed to get bot information")
        return
    
    # Check webhook status
    print("\n2. 🔍 Checking Webhook Status...")
    webhook_info = check_webhook_status(bot_token)
    if webhook_info:
        webhook_url = webhook_info.get('url', '')
        pending_updates = webhook_info.get('pending_update_count', 0)
        
        if webhook_url:
            print(f"   ⚠️  Webhook is SET: {webhook_url}")
            print(f"   📊 Pending Updates: {pending_updates}")
            
            if webhook_info.get('last_error_date'):
                print(f"   ❌ Last Error: {webhook_info.get('last_error_message', 'Unknown')}")
            
            print("\n   🔧 This webhook can cause 409 Conflict errors with polling!")
            
            # Ask user if they want to clear it
            response = input("\n   Clear webhook to enable polling? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                print("\n3. 🧹 Clearing Webhook...")
                if clear_webhook(bot_token):
                    print("   ✅ Webhook cleared! You can now use polling.")
                else:
                    print("   ❌ Failed to clear webhook")
            else:
                print("\n   ℹ️  Webhook left unchanged")
        else:
            print("   ✅ No webhook set - polling should work fine")
            print(f"   📊 Pending Updates: {pending_updates}")
    else:
        print("   ❌ Failed to check webhook status")
        return
    
    print("\n4. 🧪 Testing Bot Connection...")
    # Test a simple API call
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates?limit=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print("   ✅ Bot connection test successful!")
            else:
                print(f"   ❌ Bot API error: {data}")
        elif response.status_code == 409:
            print("   ⚠️  409 Conflict detected - another instance may be polling")
            print("   💡 Try stopping all other instances of your bot")
        else:
            print(f"   ❌ HTTP Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Connection test failed: {e}")
    
    print("\n🎉 Diagnosis Complete!")
    print("\n💡 Tips to avoid 409 Conflicts:")
    print("   • Only run one instance of your bot at a time")
    print("   • Clear webhooks before using polling")
    print("   • Use proper shutdown handling in your code")
    print("   • Check for zombie processes if conflicts persist")

if __name__ == "__main__":
    main()