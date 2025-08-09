"""
E2E Test Setup Validation
Validates that the E2E test environment is properly configured.
"""

import sys
import importlib
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

def check_python_version() -> Tuple[bool, str]:
    """Check Python version compatibility"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        return True, f"✓ Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)"

def check_required_packages() -> Dict[str, Tuple[bool, str]]:
    """Check if required packages are installed"""
    required_packages = {
        "pytest": "pytest",
        "pytest-asyncio": "pytest_asyncio", 
        "websockets": "websockets",
        "aiohttp": "aiohttp",
        "playwright": "playwright",
        "PIL": "PIL"  # Pillow
    }
    
    results = {}
    for package_name, import_name in required_packages.items():
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, '__version__', 'unknown')
            results[package_name] = (True, f"✓ {package_name} {version}")
        except ImportError:
            results[package_name] = (False, f"✗ {package_name} not installed")
    
    return results

def check_test_files() -> Dict[str, Tuple[bool, str]]:
    """Check if test files exist and are valid"""
    test_files = {
        "Complete User Flows": "tests/e2e/test_complete_user_flows.py",
        "Agent Interactions": "tests/e2e/test_agent_interactions.py", 
        "Visual Regression": "tests/visual/test_ui_regression.py",
        "Browser Automation": "tests/playwright/test_browser_automation.py",
        "Real-World Scenarios": "tests/scenarios/test_real_world_usage.py",
        "Test Runner": "tests/run_e2e_tests.py",
        "Test Config": "tests/conftest.py"
    }
    
    results = {}
    base_path = Path(__file__).parent.parent
    
    for name, file_path in test_files.items():
        full_path = base_path / file_path
        if full_path.exists():
            # Check if file has content
            size = full_path.stat().st_size
            if size > 100:  # Minimum reasonable file size
                results[name] = (True, f"✓ {file_path} ({size} bytes)")
            else:
                results[name] = (False, f"✗ {file_path} (too small: {size} bytes)")
        else:
            results[name] = (False, f"✗ {file_path} (not found)")
    
    return results

def check_directories() -> Dict[str, Tuple[bool, str]]:
    """Check if required directories exist"""
    base_path = Path(__file__).parent.parent
    directories = {
        "E2E Tests": "tests/e2e",
        "Visual Tests": "tests/visual", 
        "Playwright Tests": "tests/playwright",
        "Scenario Tests": "tests/scenarios",
        "Test Utils": "tests/utils",
        "Screenshots": "test_screenshots",
        "Reports": "test_reports"
    }
    
    results = {}
    for name, dir_path in directories.items():
        full_path = base_path / dir_path
        if full_path.exists() and full_path.is_dir():
            file_count = len(list(full_path.glob("*")))
            results[name] = (True, f"✓ {dir_path} ({file_count} files)")
        else:
            results[name] = (False, f"✗ {dir_path} (not found)")
    
    return results

def check_src_imports() -> Dict[str, Tuple[bool, str]]:
    """Check if source code imports work"""
    imports = {
        "WebSocket Manager": "src.chat.websocket_manager.WebSocketManager",
        "Agent Manager": "src.agents.agent_manager.AgentManager", 
        "Message Parser": "src.chat.message_parser.MessageParser",
        "File Ownership": "src.managers.file_ownership.FileOwnershipManager"
    }
    
    results = {}
    # Add src to path temporarily
    base_path = Path(__file__).parent.parent
    src_path = str(base_path / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    for name, import_path in imports.items():
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            getattr(module, class_name)
            results[name] = (True, f"✓ {import_path}")
        except (ImportError, AttributeError) as e:
            results[name] = (False, f"✗ {import_path} ({str(e)[:50]}...)")
    
    return results

def check_frontend_availability() -> Tuple[bool, str]:
    """Check if frontend is available (optional)"""
    try:
        import requests
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            return True, "✓ Frontend available at localhost:3000"
        else:
            return False, f"✗ Frontend returned status {response.status_code}"
    except Exception as e:
        return False, f"✗ Frontend not available ({str(e)[:50]}...)"

def check_playwright_browsers() -> Dict[str, Tuple[bool, str]]:
    """Check if Playwright browsers are installed"""
    browsers = ["chromium", "firefox", "webkit"]
    results = {}
    
    for browser in browsers:
        try:
            result = subprocess.run(
                ["playwright", "install", "--dry-run", browser],
                capture_output=True,
                text=True,
                timeout=10
            )
            if "is already installed" in result.stdout or result.returncode == 0:
                results[browser] = (True, f"✓ {browser} browser installed")
            else:
                results[browser] = (False, f"✗ {browser} browser not installed")
        except Exception as e:
            results[browser] = (False, f"✗ {browser} check failed ({str(e)[:30]}...)")
    
    return results

def run_validation():
    """Run complete validation and generate report"""
    print("E2E Test Environment Validation")
    print("=" * 50)
    
    # Check Python version
    python_ok, python_msg = check_python_version()
    print(f"\nPython Version:")
    print(f"  {python_msg}")
    
    # Check required packages
    print(f"\nRequired Packages:")
    package_results = check_required_packages()
    all_packages_ok = True
    for package, (ok, msg) in package_results.items():
        print(f"  {msg}")
        if not ok:
            all_packages_ok = False
    
    # Check test files
    print(f"\nTest Files:")
    file_results = check_test_files()
    all_files_ok = True
    for name, (ok, msg) in file_results.items():
        print(f"  {msg}")
        if not ok:
            all_files_ok = False
    
    # Check directories
    print(f"\nDirectories:")
    dir_results = check_directories()
    all_dirs_ok = True
    for name, (ok, msg) in dir_results.items():
        print(f"  {msg}")
        if not ok:
            all_dirs_ok = False
    
    # Check source imports
    print(f"\nSource Code Imports:")
    import_results = check_src_imports()
    all_imports_ok = True
    for name, (ok, msg) in import_results.items():
        print(f"  {msg}")
        if not ok:
            all_imports_ok = False
    
    # Check optional components
    print(f"\nOptional Components:")
    
    # Frontend
    frontend_ok, frontend_msg = check_frontend_availability()
    print(f"  {frontend_msg}")
    
    # Playwright browsers
    browser_results = check_playwright_browsers()
    browsers_ok = True
    for browser, (ok, msg) in browser_results.items():
        print(f"  {msg}")
        if not ok:
            browsers_ok = False
    
    # Summary
    print(f"\nValidation Summary:")
    print(f"=" * 50)
    
    core_components = [
        ("Python Version", python_ok),
        ("Required Packages", all_packages_ok),
        ("Test Files", all_files_ok), 
        ("Directories", all_dirs_ok),
        ("Source Imports", all_imports_ok)
    ]
    
    optional_components = [
        ("Frontend", frontend_ok),
        ("Playwright Browsers", browsers_ok)
    ]
    
    core_ok = all(ok for _, ok in core_components)
    
    for name, ok in core_components:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")
    
    print(f"\nOptional Components:")
    for name, ok in optional_components:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")
    
    # Recommendations
    print(f"\nRecommendations:")
    print(f"=" * 50)
    
    if core_ok:
        print("✓ Core E2E testing environment is ready!")
        print("  You can run: python tests/run_e2e_tests.py --suites complete_user_flows agent_interactions")
    else:
        print("✗ Core components missing. Please install missing dependencies:")
        if not all_packages_ok:
            print("  pip install -r requirements-e2e.txt")
        if not all_imports_ok:
            print("  Check that src/ directory structure is correct")
    
    if not frontend_ok:
        print("⚠ Frontend not available - browser tests will be skipped")
        print("  To enable: cd frontend && npm run dev")
    
    if not browsers_ok:
        print("⚠ Playwright browsers not installed - visual tests will be skipped")
        print("  To install: playwright install")
    
    print(f"\nNext Steps:")
    if core_ok:
        print("1. Run basic tests: pytest tests/e2e/test_complete_user_flows.py -v")
        print("2. Run full suite: python tests/run_e2e_tests.py")
        if frontend_ok and browsers_ok:
            print("3. Run visual tests: pytest tests/visual/ -v")
    else:
        print("1. Install missing dependencies")
        print("2. Fix import issues")
        print("3. Re-run validation: python tests/validate_e2e_setup.py")
    
    return core_ok

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)