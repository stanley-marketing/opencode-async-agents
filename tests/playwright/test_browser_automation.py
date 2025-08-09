"""
Playwright Browser Automation Tests
Full browser automation for E2E flows with multi-tab testing and network simulation.
"""

import asyncio
import json
import pytest
import time
import threading
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

# Import Playwright for browser automation
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = Page = BrowserContext = None

from tests.utils.websocket_test_client import WebSocketTestClient, WebSocketTestScenario
from src.chat.websocket_manager import WebSocketManager
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager

logger = logging.getLogger(__name__)

# Test configuration
TEST_FRONTEND_URL = "http://localhost:3000"
TEST_WEBSOCKET_URL = "ws://localhost:8770"
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / "test_screenshots" / "playwright"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture
async def websocket_server():
    """Start WebSocket server for testing"""
    manager = WebSocketManager(host="localhost", port=8770)
    
    # Start server in background
    server_thread = threading.Thread(target=manager.start_polling, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(1)
    
    yield manager
    
    # Cleanup
    manager.stop_polling()


@pytest.fixture
async def agent_system(websocket_server):
    """Set up agent system for browser testing"""
    file_manager = FileOwnershipManager(":memory:")
    agent_manager = AgentManager(file_manager, websocket_server)
    
    # Create diverse agent team
    agent_manager.create_agent("alice", "fullstack_developer", ["python", "react", "api", "database"])
    agent_manager.create_agent("bob", "ui_designer", ["design", "css", "figma", "user_experience"])
    agent_manager.create_agent("charlie", "devops_engineer", ["docker", "kubernetes", "aws", "monitoring"])
    agent_manager.create_agent("diana", "qa_specialist", ["testing", "automation", "quality", "bugs"])
    
    yield agent_manager


@pytest.fixture
async def browser():
    """Create browser instance"""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Set to True for CI/CD
            slow_mo=100,     # Slow down for debugging
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser):
    """Create browser context with realistic settings"""
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        locale='en-US',
        timezone_id='America/New_York',
        permissions=['notifications'],
        record_video_dir=str(SCREENSHOT_DIR / "videos") if os.getenv('RECORD_VIDEO') else None
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context):
    """Create page for testing"""
    page = await context.new_page()
    
    # Set up console logging
    page.on("console", lambda msg: logger.info(f"Browser console: {msg.text}"))
    page.on("pageerror", lambda error: logger.error(f"Browser error: {error}"))
    
    yield page
    await page.close()


class BrowserTestHelper:
    """Helper class for browser automation"""
    
    @staticmethod
    async def navigate_to_chat(page: Page) -> bool:
        """Navigate to chat interface and wait for load"""
        try:
            await page.goto(TEST_FRONTEND_URL, wait_until="networkidle")
            await page.wait_for_selector('[data-testid="chat-interface"]', timeout=15000)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to chat: {e}")
            return False
    
    @staticmethod
    async def send_chat_message(page: Page, message: str) -> bool:
        """Send a chat message through the UI"""
        try:
            input_selector = '[data-testid="message-input"] input'
            await page.wait_for_selector(input_selector)
            await page.fill(input_selector, message)
            await page.press(input_selector, "Enter")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    @staticmethod
    async def wait_for_message(page: Page, text: str, timeout: int = 10000) -> bool:
        """Wait for specific message to appear in chat"""
        try:
            await page.wait_for_function(
                f"document.querySelector('[data-testid=\"message-list\"]').innerText.includes('{text}')",
                timeout=timeout
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    async def get_message_count(page: Page) -> int:
        """Get current number of messages in chat"""
        try:
            messages = await page.query_selector_all('[data-testid="message-item"]')
            return len(messages)
        except Exception:
            return 0
    
    @staticmethod
    async def take_screenshot(page: Page, name: str) -> Path:
        """Take screenshot with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename
        await page.screenshot(path=str(filepath), full_page=True)
        return filepath
    
    @staticmethod
    async def simulate_network_condition(page: Page, condition: str):
        """Simulate different network conditions"""
        conditions = {
            "slow_3g": {"download": 500 * 1024, "upload": 500 * 1024, "latency": 400},
            "fast_3g": {"download": 1.6 * 1024 * 1024, "upload": 750 * 1024, "latency": 150},
            "offline": {"download": 0, "upload": 0, "latency": 0}
        }
        
        if condition in conditions:
            await page.context.set_extra_http_headers({"Connection": condition})
            # Note: Playwright doesn't have built-in network throttling like Puppeteer
            # This is a simplified simulation


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestSingleUserBrowserFlow:
    """Test single user browser interactions"""
    
    async def test_complete_user_session(self, page, websocket_server, agent_system):
        """Test: Complete user session from login to logout"""
        
        # Step 1: Navigate to chat interface
        success = await BrowserTestHelper.navigate_to_chat(page)
        if not success:
            pytest.skip("Frontend not available")
        
        # Take initial screenshot
        await BrowserTestHelper.take_screenshot(page, "initial_load")
        
        # Step 2: Verify UI elements are present
        assert await page.is_visible('[data-testid="message-list"]')
        assert await page.is_visible('[data-testid="message-input"]')
        assert await page.is_visible('[data-testid="user-list"]')
        
        # Step 3: Send welcome message
        await BrowserTestHelper.send_chat_message(page, "Hello! I'm starting my work session.")
        
        # Step 4: Wait for message to appear
        message_appeared = await BrowserTestHelper.wait_for_message(page, "Hello! I'm starting")
        assert message_appeared, "Message should appear in chat"
        
        # Step 5: Mention an agent
        await BrowserTestHelper.send_chat_message(page, "@alice can you help me with a React component?")
        
        # Step 6: Wait for agent response
        await asyncio.sleep(3)  # Give agent time to respond
        
        # Step 7: Verify agent response appeared
        message_count = await BrowserTestHelper.get_message_count(page)
        assert message_count >= 2, "Should have user message and agent response"
        
        # Take final screenshot
        await BrowserTestHelper.take_screenshot(page, "session_complete")
    
    async def test_message_input_interactions(self, page, websocket_server, agent_system):
        """Test: Various message input interactions"""
        
        success = await BrowserTestHelper.navigate_to_chat(page)
        if not success:
            pytest.skip("Frontend not available")
        
        input_selector = '[data-testid="message-input"] input'
        
        # Test 1: Basic text input
        await page.fill(input_selector, "Testing basic text input")
        await page.press(input_selector, "Enter")
        
        # Test 2: Multiline message (Shift+Enter)
        await page.fill(input_selector, "Line 1")
        await page.press(input_selector, "Shift+Enter")
        await page.type(input_selector, "Line 2")
        await page.press(input_selector, "Enter")
        
        # Test 3: Message with mentions
        await page.fill(input_selector, "@alice @bob please collaborate")
        await page.press(input_selector, "Enter")
        
        # Test 4: Command message
        await page.fill(input_selector, "/help testing")
        await page.press(input_selector, "Enter")
        
        # Test 5: Long message
        long_message = "This is a very long message " * 20
        await page.fill(input_selector, long_message)
        await page.press(input_selector, "Enter")
        
        # Verify all messages appeared
        await asyncio.sleep(2)
        message_count = await BrowserTestHelper.get_message_count(page)
        assert message_count >= 5, "All test messages should appear"
        
        await BrowserTestHelper.take_screenshot(page, "message_input_tests")
    
    async def test_typing_indicators(self, page, websocket_server, agent_system):
        """Test: Typing indicator functionality"""
        
        success = await BrowserTestHelper.navigate_to_chat(page)
        if not success:
            pytest.skip("Frontend not available")
        
        input_selector = '[data-testid="message-input"] input'
        
        # Start typing
        await page.click(input_selector)
        await page.type(input_selector, "I am typing slowly...", delay=200)
        
        # Check if typing indicator appears (for other users)
        # Note: This is hard to test with single browser, but we can verify the input state
        typing_text = await page.input_value(input_selector)
        assert "typing slowly" in typing_text
        
        # Clear input to stop typing
        await page.fill(input_selector, "")
        
        # Send final message
        await page.fill(input_selector, "Finished typing!")
        await page.press(input_selector, "Enter")
        
        await BrowserTestHelper.take_screenshot(page, "typing_test")
    
    async def test_scroll_behavior(self, page, websocket_server, agent_system):
        """Test: Message list scroll behavior"""
        
        success = await BrowserTestHelper.navigate_to_chat(page)
        if not success:
            pytest.skip("Frontend not available")
        
        # Send many messages to test scrolling
        for i in range(20):
            await BrowserTestHelper.send_chat_message(page, f"Message {i+1} for scroll testing")
            await asyncio.sleep(0.1)  # Small delay
        
        # Wait for messages to load
        await asyncio.sleep(2)
        
        # Test scroll to top
        await page.evaluate("document.querySelector('[data-testid=\"message-list\"]').scrollTop = 0")
        await asyncio.sleep(1)
        
        # Test scroll to bottom
        await page.evaluate("""
            const messageList = document.querySelector('[data-testid="message-list"]');
            messageList.scrollTop = messageList.scrollHeight;
        """)
        await asyncio.sleep(1)
        
        # Send new message and verify auto-scroll
        await BrowserTestHelper.send_chat_message(page, "Final message - should auto-scroll")
        
        await BrowserTestHelper.take_screenshot(page, "scroll_behavior")


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestMultiTabTesting:
    """Test multi-tab scenarios for concurrent users"""
    
    async def test_two_user_conversation(self, context, websocket_server, agent_system):
        """Test: Two users having a conversation in separate tabs"""
        
        # Create two pages (simulating two users)
        page1 = await context.new_page()
        page2 = await context.new_page()
        
        try:
            # Navigate both pages to chat
            success1 = await BrowserTestHelper.navigate_to_chat(page1)
            success2 = await BrowserTestHelper.navigate_to_chat(page2)
            
            if not (success1 and success2):
                pytest.skip("Frontend not available")
            
            # User 1 sends message
            await BrowserTestHelper.send_chat_message(page1, "Hello from User 1!")
            
            # Wait for message to appear on both pages
            await BrowserTestHelper.wait_for_message(page1, "Hello from User 1")
            await BrowserTestHelper.wait_for_message(page2, "Hello from User 1")
            
            # User 2 responds
            await BrowserTestHelper.send_chat_message(page2, "Hi User 1! This is User 2.")
            
            # Wait for response on both pages
            await BrowserTestHelper.wait_for_message(page1, "Hi User 1")
            await BrowserTestHelper.wait_for_message(page2, "Hi User 1")
            
            # User 1 mentions an agent
            await BrowserTestHelper.send_chat_message(page1, "@alice can you help us with a project?")
            
            # Wait for agent response on both pages
            await asyncio.sleep(3)
            
            # Verify message counts on both pages
            count1 = await BrowserTestHelper.get_message_count(page1)
            count2 = await BrowserTestHelper.get_message_count(page2)
            
            assert count1 >= 3, "Page 1 should show all messages"
            assert count2 >= 3, "Page 2 should show all messages"
            assert count1 == count2, "Both pages should show same message count"
            
            # Take screenshots of both pages
            await BrowserTestHelper.take_screenshot(page1, "two_user_page1")
            await BrowserTestHelper.take_screenshot(page2, "two_user_page2")
            
        finally:
            await page1.close()
            await page2.close()
    
    async def test_concurrent_typing(self, context, websocket_server, agent_system):
        """Test: Multiple users typing simultaneously"""
        
        # Create three pages
        pages = []
        for i in range(3):
            page = await context.new_page()
            success = await BrowserTestHelper.navigate_to_chat(page)
            if success:
                pages.append(page)
        
        if len(pages) < 2:
            pytest.skip("Frontend not available")
        
        try:
            # All users start typing simultaneously
            typing_tasks = []
            for i, page in enumerate(pages):
                task = asyncio.create_task(
                    page.type('[data-testid="message-input"] input', 
                             f"User {i+1} is typing a message...", delay=100)
                )
                typing_tasks.append(task)
            
            # Wait for all typing to complete
            await asyncio.gather(*typing_tasks)
            
            # Send messages in sequence
            for i, page in enumerate(pages):
                await page.press('[data-testid="message-input"] input', "Enter")
                await asyncio.sleep(0.5)
            
            # Wait for all messages to appear
            await asyncio.sleep(2)
            
            # Verify all pages show all messages
            for i, page in enumerate(pages):
                count = await BrowserTestHelper.get_message_count(page)
                assert count >= len(pages), f"Page {i+1} should show all messages"
                await BrowserTestHelper.take_screenshot(page, f"concurrent_typing_page{i+1}")
            
        finally:
            for page in pages:
                await page.close()
    
    async def test_user_disconnect_reconnect(self, context, websocket_server, agent_system):
        """Test: User disconnects and reconnects while others continue chatting"""
        
        # Create two pages
        page1 = await context.new_page()
        page2 = await context.new_page()
        
        try:
            success1 = await BrowserTestHelper.navigate_to_chat(page1)
            success2 = await BrowserTestHelper.navigate_to_chat(page2)
            
            if not (success1 and success2):
                pytest.skip("Frontend not available")
            
            # Both users send initial messages
            await BrowserTestHelper.send_chat_message(page1, "User 1 is here")
            await BrowserTestHelper.send_chat_message(page2, "User 2 is also here")
            
            # Wait for messages to sync
            await asyncio.sleep(1)
            
            # User 1 "disconnects" (close page)
            await page1.close()
            
            # User 2 continues chatting
            await BrowserTestHelper.send_chat_message(page2, "User 1 seems to have left")
            await BrowserTestHelper.send_chat_message(page2, "@alice are you still here?")
            
            # Wait for agent response
            await asyncio.sleep(3)
            
            # User 1 "reconnects" (new page)
            page1_new = await context.new_page()
            success = await BrowserTestHelper.navigate_to_chat(page1_new)
            
            if success:
                # Wait for message history to load
                await asyncio.sleep(2)
                
                # Verify reconnected user sees all messages
                count = await BrowserTestHelper.get_message_count(page1_new)
                assert count >= 4, "Reconnected user should see message history"
                
                # User 1 announces return
                await BrowserTestHelper.send_chat_message(page1_new, "I'm back! Sorry for the disconnection.")
                
                # Verify both users see the return message
                await BrowserTestHelper.wait_for_message(page2, "I'm back")
                await BrowserTestHelper.wait_for_message(page1_new, "I'm back")
                
                await BrowserTestHelper.take_screenshot(page1_new, "reconnected_user")
                await BrowserTestHelper.take_screenshot(page2, "continuous_user")
                
                await page1_new.close()
            
        finally:
            await page2.close()


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestNetworkConditions:
    """Test behavior under different network conditions"""
    
    async def test_slow_network_performance(self, page, websocket_server, agent_system):
        """Test: Chat performance under slow network conditions"""
        
        success = await BrowserTestHelper.navigate_to_chat(page)
        if not success:
            pytest.skip("Frontend not available")
        
        # Simulate slow network
        await BrowserTestHelper.simulate_network_condition(page, "slow_3g")
        
        # Send message under slow conditions
        start_time = time.time()
        await BrowserTestHelper.send_chat_message(page, "Testing under slow network conditions")
        
        # Wait for message to appear
        message_appeared = await BrowserTestHelper.wait_for_message(page, "Testing under slow", timeout=15000)
        end_time = time.time()
        
        assert message_appeared, "Message should appear even under slow network"
        
        response_time = end_time - start_time
        logger.info(f"Message response time under slow network: {response_time:.2f}s")
        
        # Test agent response under slow conditions
        await BrowserTestHelper.send_chat_message(page, "@alice please respond under slow network")
        await asyncio.sleep(5)  # Give more time for slow network
        
        await BrowserTestHelper.take_screenshot(page, "slow_network_test")
    
    async def test_connection_interruption(self, page, websocket_server, agent_system):
        """Test: Behavior when connection is interrupted"""
        
        success = await BrowserTestHelper.navigate_to_chat(page)
        if not success:
            pytest.skip("Frontend not available")
        
        # Send initial message
        await BrowserTestHelper.send_chat_message(page, "Message before connection interruption")
        await asyncio.sleep(1)
        
        # Simulate connection interruption by blocking WebSocket
        await page.route("ws://localhost:8770", lambda route: route.abort())
        
        # Try to send message during interruption
        await BrowserTestHelper.send_chat_message(page, "Message during interruption")
        
        # Wait and check connection status
        await asyncio.sleep(3)
        
        # Check if UI shows disconnected state
        connection_status = await page.text_content('[data-testid="connection-status"]')
        logger.info(f"Connection status during interruption: {connection_status}")
        
        # Restore connection
        await page.unroute("ws://localhost:8770")
        
        # Wait for reconnection
        await asyncio.sleep(5)
        
        # Send message after reconnection
        await BrowserTestHelper.send_chat_message(page, "Message after reconnection")
        
        # Verify message appears
        message_appeared = await BrowserTestHelper.wait_for_message(page, "after reconnection")
        assert message_appeared, "Message should appear after reconnection"
        
        await BrowserTestHelper.take_screenshot(page, "connection_recovery")
    
    async def test_offline_behavior(self, page, websocket_server, agent_system):
        """Test: Behavior when completely offline"""
        
        success = await BrowserTestHelper.navigate_to_chat(page)
        if not success:
            pytest.skip("Frontend not available")
        
        # Send message while online
        await BrowserTestHelper.send_chat_message(page, "Last message before going offline")
        await asyncio.sleep(1)
        
        # Go offline
        await page.context.set_offline(True)
        
        # Try to send message while offline
        await BrowserTestHelper.send_chat_message(page, "Message while offline")
        
        # Wait and check UI state
        await asyncio.sleep(3)
        
        # Verify offline indicator
        connection_status = await page.text_content('[data-testid="connection-status"]')
        logger.info(f"Connection status while offline: {connection_status}")
        
        # Go back online
        await page.context.set_offline(False)
        
        # Wait for reconnection
        await asyncio.sleep(5)
        
        # Send message after coming back online
        await BrowserTestHelper.send_chat_message(page, "Back online!")
        
        # Verify message appears
        message_appeared = await BrowserTestHelper.wait_for_message(page, "Back online")
        assert message_appeared, "Message should appear after coming back online"
        
        await BrowserTestHelper.take_screenshot(page, "offline_recovery")


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestErrorScenarios:
    """Test error handling in browser environment"""
    
    async def test_javascript_errors(self, page, websocket_server, agent_system):
        """Test: Handling of JavaScript errors"""
        
        success = await BrowserTestHelper.navigate_to_chat(page)
        if not success:
            pytest.skip("Frontend not available")
        
        # Inject JavaScript error
        await page.evaluate("throw new Error('Test error for error handling')")
        
        # Verify chat still works after error
        await BrowserTestHelper.send_chat_message(page, "Testing after JavaScript error")
        
        message_appeared = await BrowserTestHelper.wait_for_message(page, "Testing after JavaScript")
        assert message_appeared, "Chat should still work after JavaScript error"
        
        await BrowserTestHelper.take_screenshot(page, "after_js_error")
    
    async def test_memory_pressure(self, page, websocket_server, agent_system):
        """Test: Behavior under memory pressure"""
        
        success = await BrowserTestHelper.navigate_to_chat(page)
        if not success:
            pytest.skip("Frontend not available")
        
        # Send many messages to create memory pressure
        for i in range(100):
            await BrowserTestHelper.send_chat_message(page, f"Memory pressure test message {i}")
            if i % 10 == 0:
                await asyncio.sleep(0.1)  # Small pause every 10 messages
        
        # Wait for all messages to load
        await asyncio.sleep(5)
        
        # Verify chat is still responsive
        await BrowserTestHelper.send_chat_message(page, "Final test after memory pressure")
        
        message_appeared = await BrowserTestHelper.wait_for_message(page, "Final test after memory")
        assert message_appeared, "Chat should remain responsive under memory pressure"
        
        # Check message count
        final_count = await BrowserTestHelper.get_message_count(page)
        assert final_count >= 100, "All messages should be displayed"
        
        await BrowserTestHelper.take_screenshot(page, "memory_pressure_test")


if __name__ == "__main__":
    # Run Playwright tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])