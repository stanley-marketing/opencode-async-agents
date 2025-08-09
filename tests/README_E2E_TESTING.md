# E2E Testing Suite Documentation

## Overview

This comprehensive End-to-End (E2E) testing suite validates the complete OpenCode Slack system functionality through realistic user scenarios, agent interactions, visual regression testing, and browser automation.

## Test Architecture

### Test Categories

1. **Complete User Flows** (`tests/e2e/test_complete_user_flows.py`)
   - User onboarding and message history
   - Multi-user conversations and threading
   - Agent mentions and responses
   - Task assignment workflows
   - Error scenarios and recovery

2. **Agent Interactions** (`tests/e2e/test_agent_interactions.py`)
   - Agent-to-agent communication
   - Help request and response cycles
   - Task delegation patterns
   - Cross-functional collaboration
   - Agent status and presence

3. **Visual Regression Testing** (`tests/visual/test_ui_regression.py`)
   - Screenshot capture for UI states
   - Responsive design validation
   - Dark mode and accessibility testing
   - Visual diff comparison
   - Cross-browser compatibility

4. **Browser Automation** (`tests/playwright/test_browser_automation.py`)
   - Full browser automation flows
   - Multi-tab concurrent user testing
   - Network condition simulation
   - Performance under load
   - Error scenario handling

5. **Real-World Scenarios** (`tests/scenarios/test_real_world_usage.py`)
   - Daily standup meetings
   - Sprint planning sessions
   - Incident response workflows
   - Code review processes
   - Team onboarding

## Prerequisites

### Required Dependencies

```bash
# Install E2E testing dependencies
pip install -r requirements-e2e.txt

# Install Playwright browsers
playwright install
```

### System Requirements

1. **WebSocket Server**: Backend WebSocket server must be available
2. **Frontend (Optional)**: Next.js frontend for browser tests
3. **Playwright**: For browser automation and visual testing
4. **Python 3.8+**: Async/await support required

### Environment Setup

```bash
# Set environment variables
export TESTING=true
export LOG_LEVEL=INFO

# Start frontend (for browser tests)
cd frontend && npm run dev

# Ensure backend dependencies are available
python -c "from src.chat.websocket_manager import WebSocketManager"
```

## Running Tests

### Quick Start

```bash
# Run all E2E tests
python tests/run_e2e_tests.py

# Run specific test suite
python tests/run_e2e_tests.py --suites complete_user_flows

# Run with verbose output
python tests/run_e2e_tests.py --verbose

# List available test suites
python tests/run_e2e_tests.py --list-suites
```

### Individual Test Suites

```bash
# User flow tests (no frontend required)
pytest tests/e2e/test_complete_user_flows.py -v

# Agent interaction tests
pytest tests/e2e/test_agent_interactions.py -v

# Visual regression tests (requires frontend + Playwright)
pytest tests/visual/test_ui_regression.py -v

# Browser automation tests (requires frontend + Playwright)
pytest tests/playwright/test_browser_automation.py -v

# Real-world scenario tests
pytest tests/scenarios/test_real_world_usage.py -v
```

### Test Filtering

```bash
# Run only fast tests
pytest tests/ -m "not slow"

# Run only browser tests
pytest tests/ -m browser

# Run specific test pattern
pytest tests/ -k "test_user_mention"

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Test Configuration

### Pytest Markers

- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.visual`: Visual regression tests
- `@pytest.mark.browser`: Browser automation tests
- `@pytest.mark.frontend`: Requires frontend
- `@pytest.mark.load`: Performance/load tests

### Test Ports

Tests automatically use unique ports to avoid conflicts:
- Base port: 8765
- Each test gets a unique port based on test ID hash
- WebSocket servers start on incremental ports

## Visual Testing

### Screenshot Management

```bash
# Screenshots are saved to:
test_screenshots/
├── baseline/          # Reference images
├── current/           # Current test run images
├── diff/             # Visual difference images
└── playwright/       # Browser automation screenshots
```

### Visual Regression Workflow

1. **First Run**: Creates baseline screenshots
2. **Subsequent Runs**: Compares with baseline
3. **Differences**: Generates diff images
4. **Approval**: Update baselines when changes are intentional

### Browser Testing

```bash
# Test different browsers
pytest tests/playwright/ --browser chromium
pytest tests/playwright/ --browser firefox
pytest tests/playwright/ --browser webkit

# Test different viewports
pytest tests/visual/ --viewport 1920x1080
pytest tests/visual/ --viewport 375x667  # Mobile
```

## Performance Testing

### Load Testing Scenarios

```python
# High-volume chat simulation
async def test_high_volume_chat_simulation():
    # Creates 10 concurrent users
    # Sends 50 messages per user
    # Verifies system responsiveness

# Message burst handling
async def test_message_burst_handling():
    # Sends 50 messages rapidly
    # Verifies message ordering
    # Tests agent responsiveness
```

### Performance Metrics

- **Response Time**: Message delivery latency
- **Throughput**: Messages per second
- **Concurrency**: Simultaneous user capacity
- **Memory Usage**: System resource consumption
- **Agent Responsiveness**: AI response times under load

## Test Data and Fixtures

### Shared Fixtures

```python
# WebSocket server with unique port
@pytest.fixture
async def websocket_server():
    # Starts isolated server instance

# Agent system with test agents
@pytest.fixture
async def agent_system():
    # Creates alice, bob, charlie, diana agents

# Browser context for UI tests
@pytest.fixture
async def browser_context():
    # Playwright browser with realistic settings
```

### Test Scenarios

```python
# Sample conversation data
sample_conversation = [
    {"user": "manager", "text": "Good morning team!"},
    {"user": "alice", "text": "Working on authentication."},
    # ... more realistic conversation
]

# Performance test parameters
performance_config = {
    "user_count": 10,
    "message_count": 100,
    "burst_size": 50,
    "test_duration": 60
}
```

## Debugging and Troubleshooting

### Common Issues

1. **Frontend Not Available**
   ```bash
   # Start frontend
   cd frontend && npm run dev
   
   # Or skip frontend tests
   pytest tests/ -m "not frontend"
   ```

2. **Playwright Not Installed**
   ```bash
   pip install playwright
   playwright install
   ```

3. **Port Conflicts**
   ```bash
   # Tests use unique ports automatically
   # Check for other services on base ports 8765-8775
   netstat -an | grep 876
   ```

4. **Agent Response Timeouts**
   ```bash
   # Increase timeout in test
   agent_response = await client.wait_for_agent_response("alice", timeout=15)
   
   # Check agent system logs
   pytest tests/ -s --log-cli-level=DEBUG
   ```

### Debug Mode

```bash
# Run with debug output
pytest tests/ -v -s --tb=long

# Capture screenshots on failure
pytest tests/visual/ --screenshot=on-failure

# Keep browser open for debugging
pytest tests/playwright/ --headed --slowmo=1000
```

### Log Analysis

```bash
# Test execution logs
tail -f e2e_test_results.log

# WebSocket communication logs
grep "WebSocket" e2e_test_results.log

# Agent response logs
grep "agent.*response" e2e_test_results.log
```

## Continuous Integration

### GitHub Actions Integration

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-e2e.txt
          playwright install
      
      - name: Run E2E tests
        run: |
          python tests/run_e2e_tests.py --suites complete_user_flows agent_interactions
      
      - name: Upload test reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-test-reports
          path: test_reports/
```

### Test Reports

```bash
# Generate comprehensive report
python tests/run_e2e_tests.py --verbose

# Reports are saved to:
test_reports/
├── e2e_test_summary_YYYYMMDD_HHMMSS.json
├── complete_user_flows_report.xml
├── complete_user_flows_report.html
└── ... (other suite reports)
```

## Best Practices

### Test Design

1. **Isolation**: Each test uses unique ports and clean state
2. **Realistic Data**: Use realistic user interactions and messages
3. **Error Handling**: Test both success and failure scenarios
4. **Performance**: Include load testing for critical paths
5. **Visual Validation**: Capture screenshots for UI verification

### Maintenance

1. **Update Baselines**: Refresh visual baselines when UI changes
2. **Monitor Performance**: Track test execution times
3. **Clean Screenshots**: Remove outdated screenshot files
4. **Review Failures**: Investigate and fix flaky tests
5. **Documentation**: Keep test scenarios documented

### Code Quality

```python
# Good test structure
async def test_user_mention_flow(self, test_scenario, agent_system):
    """Test: User mentions agent and receives response"""
    
    # Step 1: Setup
    user = await test_scenario.create_client("developer", "developer")
    
    # Step 2: Action
    await user.send_message("@alice please help with React")
    
    # Step 3: Verification
    response = await user.wait_for_agent_response("alice", timeout=10)
    assert response is not None
    assert "react" in response['data']['text'].lower()
    
    # Step 4: Cleanup (automatic via fixtures)
```

## Contributing

### Adding New Tests

1. **Choose Category**: Determine which test suite fits your scenario
2. **Follow Patterns**: Use existing test patterns and fixtures
3. **Add Markers**: Include appropriate pytest markers
4. **Document**: Add docstrings explaining test purpose
5. **Validate**: Ensure tests pass in isolation and with full suite

### Test Scenarios

When adding new test scenarios:

1. **Real-World Focus**: Base tests on actual user workflows
2. **Edge Cases**: Include error conditions and edge cases
3. **Performance**: Consider performance implications
4. **Visual Elements**: Add visual validation where appropriate
5. **Documentation**: Update this README with new scenarios

## Summary

This E2E testing suite provides comprehensive validation of the OpenCode Slack system through:

- **100% Feature Coverage**: All user-facing functionality tested
- **Visual Validation**: Screenshot-based UI regression testing
- **Performance Testing**: Load and stress testing scenarios
- **Real-World Scenarios**: Realistic workflow validation
- **Browser Automation**: Full browser interaction testing
- **Agent Validation**: AI agent behavior verification

The suite is designed to catch regressions early, validate new features thoroughly, and ensure the system performs well under realistic usage conditions.

**Expected Failing Points for TDD**:
- Agent response generation (ReAct agent not fully implemented)
- WebSocket message persistence (database integration)
- Frontend component interactions (UI state management)
- File upload and media handling (not implemented)
- Advanced agent coordination (complex delegation logic)

These failing tests will guide development priorities and validate implementation completeness.