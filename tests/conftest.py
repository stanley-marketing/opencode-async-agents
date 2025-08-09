"""
Pytest configuration and shared fixtures for E2E testing.
"""

import asyncio
import pytest
import logging
import os
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress noisy loggers during testing
logging.getLogger('websockets').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)


def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    
    # Register custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "visual: marks tests as visual regression tests"
    )
    config.addinivalue_line(
        "markers", "browser: marks tests that require browser automation"
    )
    config.addinivalue_line(
        "markers", "frontend: marks tests that require frontend to be running"
    )
    config.addinivalue_line(
        "markers", "load: marks tests as load/performance tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    
    for item in items:
        # Add markers based on test file location
        if "test_visual" in str(item.fspath):
            item.add_marker(pytest.mark.visual)
        
        if "test_browser" in str(item.fspath) or "playwright" in str(item.fspath):
            item.add_marker(pytest.mark.browser)
            item.add_marker(pytest.mark.frontend)
        
        if "test_real_world" in str(item.fspath) or "scenarios" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.integration)
        
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # Add slow marker to tests that take longer
        if any(keyword in item.name.lower() for keyword in ['load', 'performance', 'stress', 'concurrent']):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.load)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture"""
    return {
        "websocket_host": "localhost",
        "websocket_port_base": 8765,  # Tests will use incremental ports
        "frontend_url": "http://localhost:3000",
        "test_timeout": 30,
        "screenshot_dir": Path(__file__).parent.parent / "test_screenshots",
        "report_dir": Path(__file__).parent.parent / "test_reports"
    }


@pytest.fixture
def test_port(request):
    """Generate unique port for each test to avoid conflicts"""
    # Use test node ID hash to generate consistent but unique ports
    import hashlib
    test_id = request.node.nodeid
    port_offset = int(hashlib.md5(test_id.encode()).hexdigest()[:4], 16) % 1000
    return 8765 + port_offset


@pytest.fixture(autouse=True)
async def setup_test_environment(test_config):
    """Set up test environment before each test"""
    
    # Ensure test directories exist
    test_config["screenshot_dir"].mkdir(parents=True, exist_ok=True)
    test_config["report_dir"].mkdir(parents=True, exist_ok=True)
    
    # Set environment variables for tests
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "INFO"
    
    yield
    
    # Cleanup after test
    # Any cleanup code can go here


@pytest.fixture
async def mock_agent_responses():
    """Fixture to provide mock agent responses for testing"""
    return {
        "alice": [
            "I'll help you with that Python task!",
            "Let me work on the API implementation.",
            "I've completed the backend changes.",
            "The tests are passing now."
        ],
        "bob": [
            "I'll design the UI components for this.",
            "The mockups are ready for review.",
            "I've updated the CSS styles.",
            "The responsive design is complete."
        ],
        "charlie": [
            "I'll handle the deployment setup.",
            "The Docker configuration is ready.",
            "The staging environment is up.",
            "Production deployment successful."
        ]
    }


@pytest.fixture
def sample_conversation():
    """Fixture providing sample conversation data"""
    return [
        {"user": "manager", "text": "Good morning team! Let's start the daily standup."},
        {"user": "alice", "text": "I'm working on the authentication system."},
        {"user": "bob", "text": "I'm designing the user dashboard."},
        {"user": "manager", "text": "@alice how's the progress on the API?"},
        {"user": "alice", "text": "The API is 80% complete. Should be done today."},
        {"user": "manager", "text": "@bob when will the designs be ready?"},
        {"user": "bob", "text": "Designs will be ready by end of day."}
    ]


@pytest.fixture
def performance_test_data():
    """Fixture providing data for performance tests"""
    return {
        "user_count": 10,
        "message_count": 100,
        "burst_size": 50,
        "concurrent_operations": 20,
        "test_duration": 60  # seconds
    }


# Skip conditions for different test types
def pytest_runtest_setup(item):
    """Set up individual test runs with skip conditions"""
    
    # Skip browser tests if Playwright not available
    if item.get_closest_marker("browser"):
        try:
            import playwright
        except ImportError:
            pytest.skip("Playwright not available")
    
    # Skip frontend tests if frontend not running
    if item.get_closest_marker("frontend"):
        try:
            import requests
            response = requests.get("http://localhost:3000", timeout=5)
            if response.status_code != 200:
                pytest.skip("Frontend not available at localhost:3000")
        except Exception:
            pytest.skip("Frontend not available at localhost:3000")
    
    # Skip load tests in CI unless explicitly requested
    if item.get_closest_marker("load") and os.getenv("CI") and not os.getenv("RUN_LOAD_TESTS"):
        pytest.skip("Load tests skipped in CI (set RUN_LOAD_TESTS=1 to enable)")


# Custom assertion helpers
class TestAssertions:
    """Custom assertion helpers for E2E tests"""
    
    @staticmethod
    def assert_message_received(messages, expected_text, sender=None):
        """Assert that a message with expected text was received"""
        matching_messages = [
            msg for msg in messages
            if expected_text in msg.get('data', {}).get('text', '')
            and (sender is None or msg.get('data', {}).get('sender') == sender)
        ]
        assert len(matching_messages) > 0, f"Expected message '{expected_text}' not found"
        return matching_messages[0]
    
    @staticmethod
    def assert_agent_responded(messages, agent_name):
        """Assert that a specific agent responded"""
        agent_messages = [
            msg for msg in messages
            if msg.get('data', {}).get('sender') == f"{agent_name}-bot"
        ]
        assert len(agent_messages) > 0, f"Agent '{agent_name}' did not respond"
        return agent_messages
    
    @staticmethod
    def assert_response_time(start_time, end_time, max_seconds):
        """Assert that response time is within acceptable limits"""
        response_time = end_time - start_time
        assert response_time <= max_seconds, f"Response time {response_time:.2f}s exceeded {max_seconds}s"


@pytest.fixture
def test_assertions():
    """Provide test assertion helpers"""
    return TestAssertions


# Pytest plugins configuration
pytest_plugins = [
    "pytest_asyncio",
    "pytest_html",
    "pytest_cov"
]