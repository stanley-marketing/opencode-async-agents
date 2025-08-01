#!/usr/bin/env python3
"""
Test script for the Telegram chat integration system.
Run this to test the basic functionality.
"""

import os
import sys
import time
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

def test_configuration():
    """Test if the system is properly configured"""
    print("🔧 Testing Configuration...")
    
    from src.chat.chat_config import config
    
    if config.is_configured():
        print("✅ Configuration is valid")
        print(f"   Bot Token: {'*' * 20}{config.bot_token[-10:] if config.bot_token else 'None'}")
        print(f"   Chat ID: {config.chat_id}")
        return True
    else:
        print("❌ Configuration is missing")
        print("   Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        print("   See TELEGRAM_SETUP.md for instructions")
        return False

def test_telegram_connection():
    """Test Telegram bot connection"""
    print("\n🌐 Testing Telegram Connection...")
    
    from src.chat.telegram_manager import TelegramManager
    
    manager = TelegramManager()
    
    if manager.is_connected():
        print("✅ Telegram bot is connected")
        
        # Get chat info
        chat_info = manager.get_chat_info()
        if chat_info:
            print(f"   Chat Title: {chat_info.get('title', 'Unknown')}")
            print(f"   Chat Type: {chat_info.get('type', 'Unknown')}")
        
        return True
    else:
        print("❌ Telegram bot connection failed")
        return False

def test_message_sending():
    """Test sending a message"""
    print("\n💬 Testing Message Sending...")
    
    from src.chat.telegram_manager import TelegramManager
    
    manager = TelegramManager()
    
    test_message = "🧪 Test message from opencode-slack system"
    success = manager.send_message(test_message, "system")
    
    if success:
        print("✅ Test message sent successfully")
        return True
    else:
        print("❌ Failed to send test message")
        return False

def test_agent_creation():
    """Test creating communication agents"""
    print("\n👥 Testing Agent Creation...")
    
    from src.managers.file_ownership import FileOwnershipManager
    from src.chat.telegram_manager import TelegramManager
    from src.agents.agent_manager import AgentManager
    
    file_manager = FileOwnershipManager()
    telegram_manager = TelegramManager()
    agent_manager = AgentManager(file_manager, telegram_manager)
    
    # Create a test agent
    agent = agent_manager.create_agent("test-employee", "developer", ["python", "javascript"])
    
    if agent:
        print("✅ Communication agent created successfully")
        print(f"   Employee: {agent.employee_name}")
        print(f"   Role: {agent.role}")
        print(f"   Expertise: {', '.join(agent.expertise)}")
        
        # Clean up
        agent_manager.remove_agent("test-employee")
        return True
    else:
        print("❌ Failed to create communication agent")
        return False

def test_message_parsing():
    """Test message parsing functionality"""
    print("\n📝 Testing Message Parsing...")
    
    from src.chat.message_parser import MessageParser
    from datetime import datetime
    
    parser = MessageParser()
    
    # Test message data
    test_message_data = {
        'message_id': 123,
        'text': '@elad please add a gradient background to the HTML file',
        'from': {'username': 'testuser', 'first_name': 'Test', 'last_name': 'User'},
        'date': int(datetime.now().timestamp())
    }
    
    parsed = parser.parse_message(test_message_data)
    
    print(f"✅ Message parsed successfully")
    print(f"   Text: {parsed.text}")
    print(f"   Mentions: {parsed.mentions}")
    print(f"   Is Task Assignment: {parser.is_task_assignment(parsed.text, parsed.mentions)}")
    
    if parsed.mentions and 'elad' in parsed.mentions:
        task_desc = parser.extract_task_description(parsed.text, 'elad')
        print(f"   Extracted Task: {task_desc}")
    
    return True

def main():
    """Run all tests"""
    print("🧪 OPENCODE-SLACK TELEGRAM INTEGRATION TEST")
    print("=" * 50)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("📄 Environment variables loaded")
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment")
    
    tests = [
        ("Configuration", test_configuration),
        ("Telegram Connection", test_telegram_connection),
        ("Message Sending", test_message_sending),
        ("Agent Creation", test_agent_creation),
        ("Message Parsing", test_message_parsing),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"💥 {test_name} test crashed: {e}")
    
    print(f"\n📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
        print("\nNext steps:")
        print("1. Start the CLI: python3 src/cli_server.py")
        print("2. Run: chat-start")
        print("3. Hire some employees: hire elad FS-developer")
        print("4. Test in Telegram: @elad please add a gradient to the HTML file")
    else:
        print("⚠️  Some tests failed. Please check the configuration and setup.")
        print("See TELEGRAM_SETUP.md for detailed instructions.")

if __name__ == "__main__":
    main()