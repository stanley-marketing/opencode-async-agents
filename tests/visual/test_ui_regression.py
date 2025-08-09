"""
Visual Regression Testing Suite
Tests UI components and captures screenshots for visual validation.
"""

import asyncio
import json
import pytest
import time
import threading
import os
import hashlib
from datetime import datetime
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

# Screenshot configuration
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / "test_screenshots"
BASELINE_DIR = SCREENSHOT_DIR / "baseline"
CURRENT_DIR = SCREENSHOT_DIR / "current"
DIFF_DIR = SCREENSHOT_DIR / "diff"

# Ensure directories exist
for dir_path in [SCREENSHOT_DIR, BASELINE_DIR, CURRENT_DIR, DIFF_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


@pytest.fixture
async def websocket_server():
    """Start WebSocket server for testing"""
    manager = WebSocketManager(host="localhost", port=8769)
    
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
    """Set up agent system for UI testing"""
    file_manager = FileOwnershipManager(":memory:")
    agent_manager = AgentManager(file_manager, websocket_server)
    
    # Create test agents
    agent_manager.create_agent("alice", "developer", ["python", "react"])
    agent_manager.create_agent("bob", "designer", ["ui", "css"])
    
    yield agent_manager


@pytest.fixture
async def browser_context():
    """Create browser context for testing"""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            device_scale_factor=1
        )
        yield context
        await context.close()
        await browser.close()


@pytest.fixture
async def page(browser_context):
    """Create page for testing"""
    if not browser_context:
        pytest.skip("Browser context not available")
    
    page = await browser_context.new_page()
    yield page
    await page.close()


class VisualTestHelper:
    """Helper class for visual testing operations"""
    
    @staticmethod
    async def take_screenshot(page: Page, name: str, full_page: bool = True) -> Path:
        """Take screenshot and save to current directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = CURRENT_DIR / filename
        
        await page.screenshot(path=str(filepath), full_page=full_page)
        logger.info(f"Screenshot saved: {filepath}")
        return filepath
    
    @staticmethod
    async def take_element_screenshot(page: Page, selector: str, name: str) -> Path:
        """Take screenshot of specific element"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_element_{timestamp}.png"
        filepath = CURRENT_DIR / filename
        
        element = await page.wait_for_selector(selector)
        await element.screenshot(path=str(filepath))
        logger.info(f"Element screenshot saved: {filepath}")
        return filepath
    
    @staticmethod
    def compare_screenshots(baseline_path: Path, current_path: Path, threshold: float = 0.1) -> bool:
        """Compare two screenshots (simplified comparison)"""
        # This is a simplified comparison - in production, use proper image diff tools
        try:
            baseline_size = baseline_path.stat().st_size if baseline_path.exists() else 0
            current_size = current_path.stat().st_size
            
            if baseline_size == 0:
                logger.warning(f"No baseline found for {baseline_path}")
                return True  # First run, accept current as baseline
            
            size_diff = abs(baseline_size - current_size) / max(baseline_size, current_size)
            return size_diff <= threshold
        except Exception as e:
            logger.error(f"Screenshot comparison failed: {e}")
            return False
    
    @staticmethod
    async def wait_for_chat_message(page: Page, text: str, timeout: int = 10000) -> bool:
        """Wait for specific chat message to appear"""
        try:
            await page.wait_for_function(
                f"document.body.innerText.includes('{text}')",
                timeout=timeout
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    async def simulate_typing(page: Page, selector: str, text: str, delay: int = 100):
        """Simulate realistic typing"""
        await page.click(selector)
        await page.type(selector, text, delay=delay)


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestChatInterfaceVisuals:
    """Test chat interface visual components"""
    
    async def test_empty_chat_interface(self, page, websocket_server, agent_system):
        """Test: Empty chat interface initial state"""
        
        # Navigate to chat interface (assuming it's served locally)
        # Note: This assumes frontend is running on localhost:3000
        try:
            await page.goto("http://localhost:3000")
            await page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available at localhost:3000")
        
        # Wait for chat interface to load
        await page.wait_for_selector('[data-testid="chat-interface"]', timeout=10000)
        
        # Take screenshot of empty state
        screenshot_path = await VisualTestHelper.take_screenshot(page, "empty_chat_interface")
        
        # Verify key UI elements are present
        assert await page.is_visible('[data-testid="message-list"]')
        assert await page.is_visible('[data-testid="message-input"]')
        assert await page.is_visible('[data-testid="user-list"]')
        assert await page.is_visible('[data-testid="connection-status"]')
        
        # Take component screenshots
        await VisualTestHelper.take_element_screenshot(page, '[data-testid="message-list"]', "message_list_empty")
        await VisualTestHelper.take_element_screenshot(page, '[data-testid="message-input"]', "message_input")
        await VisualTestHelper.take_element_screenshot(page, '[data-testid="user-list"]', "user_list_empty")
    
    async def test_chat_with_messages(self, page, websocket_server, agent_system):
        """Test: Chat interface with messages"""
        
        try:
            await page.goto("http://localhost:3000")
            await page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for chat interface
        await page.wait_for_selector('[data-testid="chat-interface"]', timeout=10000)
        
        # Simulate sending messages
        message_input = '[data-testid="message-input"] input'
        await page.wait_for_selector(message_input)
        
        # Send first message
        await VisualTestHelper.simulate_typing(page, message_input, "Hello team!")
        await page.press(message_input, "Enter")
        
        # Wait for message to appear
        await VisualTestHelper.wait_for_chat_message(page, "Hello team!")
        
        # Send agent mention
        await VisualTestHelper.simulate_typing(page, message_input, "@alice please help with testing")
        await page.press(message_input, "Enter")
        
        # Wait for agent response
        await asyncio.sleep(3)  # Give agent time to respond
        
        # Take screenshot with messages
        await VisualTestHelper.take_screenshot(page, "chat_with_messages")
        
        # Take screenshot of message list
        await VisualTestHelper.take_element_screenshot(page, '[data-testid="message-list"]', "message_list_with_content")
    
    async def test_typing_indicators(self, page, websocket_server, agent_system):
        """Test: Typing indicators visual state"""
        
        try:
            await page.goto("http://localhost:3000")
            await page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for chat interface
        await page.wait_for_selector('[data-testid="chat-interface"]', timeout=10000)
        
        # Start typing to trigger typing indicator
        message_input = '[data-testid="message-input"] input'
        await page.click(message_input)
        await page.type(message_input, "I am typing a message...")
        
        # Wait for typing indicator to appear
        await asyncio.sleep(1)
        
        # Take screenshot with typing indicator
        await VisualTestHelper.take_screenshot(page, "typing_indicator_active")
        
        # Clear input and wait for typing to stop
        await page.fill(message_input, "")
        await asyncio.sleep(2)
        
        # Take screenshot without typing indicator
        await VisualTestHelper.take_screenshot(page, "typing_indicator_inactive")
    
    async def test_connection_status_states(self, page, websocket_server, agent_system):
        """Test: Different connection status visual states"""
        
        try:
            await page.goto("http://localhost:3000")
            await page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for connection
        await page.wait_for_selector('[data-testid="connection-status"]', timeout=10000)
        
        # Take screenshot of connected state
        await VisualTestHelper.take_element_screenshot(page, '[data-testid="connection-status"]', "connection_connected")
        
        # Simulate connection issues by blocking network
        await page.route("ws://localhost:8769", lambda route: route.abort())
        
        # Wait for disconnected state
        await asyncio.sleep(3)
        
        # Take screenshot of disconnected state
        await VisualTestHelper.take_element_screenshot(page, '[data-testid="connection-status"]', "connection_disconnected")
    
    async def test_user_list_states(self, page, websocket_server, agent_system):
        """Test: User list with different user states"""
        
        try:
            await page.goto("http://localhost:3000")
            await page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for user list
        await page.wait_for_selector('[data-testid="user-list"]', timeout=10000)
        
        # Take screenshot of initial user list
        await VisualTestHelper.take_element_screenshot(page, '[data-testid="user-list"]', "user_list_initial")
        
        # Simulate multiple users joining (this would require multiple browser contexts)
        # For now, just take screenshot of current state
        await asyncio.sleep(2)
        
        # Take screenshot after potential user updates
        await VisualTestHelper.take_element_screenshot(page, '[data-testid="user-list"]', "user_list_updated")


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestResponsiveDesign:
    """Test responsive design across different screen sizes"""
    
    async def test_mobile_layout(self, browser_context, websocket_server, agent_system):
        """Test: Mobile responsive layout"""
        
        # Create mobile viewport
        mobile_page = await browser_context.new_page()
        await mobile_page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        
        try:
            await mobile_page.goto("http://localhost:3000")
            await mobile_page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for chat interface
        await mobile_page.wait_for_selector('[data-testid="chat-interface"]', timeout=10000)
        
        # Take mobile screenshot
        await VisualTestHelper.take_screenshot(mobile_page, "mobile_layout")
        
        # Test mobile-specific interactions
        await mobile_page.tap('[data-testid="message-input"] input')
        await VisualTestHelper.take_screenshot(mobile_page, "mobile_keyboard_active")
        
        await mobile_page.close()
    
    async def test_tablet_layout(self, browser_context, websocket_server, agent_system):
        """Test: Tablet responsive layout"""
        
        # Create tablet viewport
        tablet_page = await browser_context.new_page()
        await tablet_page.set_viewport_size({"width": 768, "height": 1024})  # iPad
        
        try:
            await tablet_page.goto("http://localhost:3000")
            await tablet_page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for chat interface
        await tablet_page.wait_for_selector('[data-testid="chat-interface"]', timeout=10000)
        
        # Take tablet screenshot
        await VisualTestHelper.take_screenshot(tablet_page, "tablet_layout")
        
        # Test tablet-specific layout
        await VisualTestHelper.take_element_screenshot(tablet_page, '[data-testid="user-list"]', "tablet_user_list")
        
        await tablet_page.close()
    
    async def test_desktop_layout(self, page, websocket_server, agent_system):
        """Test: Desktop layout at different resolutions"""
        
        # Test standard desktop resolution
        await page.set_viewport_size({"width": 1920, "height": 1080})
        
        try:
            await page.goto("http://localhost:3000")
            await page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for chat interface
        await page.wait_for_selector('[data-testid="chat-interface"]', timeout=10000)
        
        # Take desktop screenshot
        await VisualTestHelper.take_screenshot(page, "desktop_1920x1080")
        
        # Test ultrawide resolution
        await page.set_viewport_size({"width": 2560, "height": 1440})
        await asyncio.sleep(1)  # Allow layout to adjust
        
        await VisualTestHelper.take_screenshot(page, "desktop_2560x1440")


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestDarkModeVisuals:
    """Test dark mode visual states"""
    
    async def test_dark_mode_toggle(self, page, websocket_server, agent_system):
        """Test: Dark mode toggle and visual changes"""
        
        try:
            await page.goto("http://localhost:3000")
            await page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for chat interface
        await page.wait_for_selector('[data-testid="chat-interface"]', timeout=10000)
        
        # Take light mode screenshot
        await VisualTestHelper.take_screenshot(page, "light_mode")
        
        # Toggle to dark mode (if available)
        dark_mode_toggle = '[data-testid="dark-mode-toggle"]'
        if await page.is_visible(dark_mode_toggle):
            await page.click(dark_mode_toggle)
            await asyncio.sleep(1)  # Allow transition
            
            # Take dark mode screenshot
            await VisualTestHelper.take_screenshot(page, "dark_mode")
            
            # Test specific components in dark mode
            await VisualTestHelper.take_element_screenshot(page, '[data-testid="message-list"]', "dark_mode_messages")
            await VisualTestHelper.take_element_screenshot(page, '[data-testid="user-list"]', "dark_mode_users")


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestAccessibilityVisuals:
    """Test accessibility features and high contrast modes"""
    
    async def test_high_contrast_mode(self, browser_context, websocket_server, agent_system):
        """Test: High contrast accessibility mode"""
        
        # Create page with high contrast preference
        page = await browser_context.new_page()
        await page.emulate_media(color_scheme="dark", reduced_motion="reduce")
        
        try:
            await page.goto("http://localhost:3000")
            await page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for chat interface
        await page.wait_for_selector('[data-testid="chat-interface"]', timeout=10000)
        
        # Take high contrast screenshot
        await VisualTestHelper.take_screenshot(page, "high_contrast_mode")
        
        await page.close()
    
    async def test_focus_states(self, page, websocket_server, agent_system):
        """Test: Keyboard focus visual states"""
        
        try:
            await page.goto("http://localhost:3000")
            await page.wait_for_load_state("networkidle")
        except Exception:
            pytest.skip("Frontend not available")
        
        # Wait for chat interface
        await page.wait_for_selector('[data-testid="chat-interface"]', timeout=10000)
        
        # Test tab navigation and focus states
        await page.keyboard.press("Tab")
        await VisualTestHelper.take_screenshot(page, "focus_state_1")
        
        await page.keyboard.press("Tab")
        await VisualTestHelper.take_screenshot(page, "focus_state_2")
        
        await page.keyboard.press("Tab")
        await VisualTestHelper.take_screenshot(page, "focus_state_3")


class TestVisualRegression:
    """Test visual regression by comparing with baseline images"""
    
    def test_compare_screenshots(self):
        """Compare current screenshots with baseline"""
        
        if not CURRENT_DIR.exists() or not list(CURRENT_DIR.glob("*.png")):
            pytest.skip("No current screenshots to compare")
        
        comparison_results = []
        
        for current_screenshot in CURRENT_DIR.glob("*.png"):
            # Find corresponding baseline
            baseline_name = current_screenshot.name.replace(
                current_screenshot.name.split("_")[-1], "baseline.png"
            )
            baseline_path = BASELINE_DIR / baseline_name
            
            # Compare screenshots
            is_similar = VisualTestHelper.compare_screenshots(
                baseline_path, current_screenshot, threshold=0.1
            )
            
            comparison_results.append({
                "name": current_screenshot.name,
                "similar": is_similar,
                "baseline_exists": baseline_path.exists()
            })
        
        # Log results
        for result in comparison_results:
            if result["baseline_exists"] and not result["similar"]:
                logger.warning(f"Visual regression detected: {result['name']}")
            elif not result["baseline_exists"]:
                logger.info(f"New baseline needed: {result['name']}")
        
        # Fail if any regressions detected
        regressions = [r for r in comparison_results 
                      if r["baseline_exists"] and not r["similar"]]
        
        if regressions:
            regression_names = [r["name"] for r in regressions]
            pytest.fail(f"Visual regressions detected: {regression_names}")


if __name__ == "__main__":
    # Run visual tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])