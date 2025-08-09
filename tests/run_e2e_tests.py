"""
E2E Test Runner
Comprehensive test runner for all E2E test suites with reporting and screenshots.
"""

import asyncio
import subprocess
import sys
import os
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('e2e_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_SUITES = {
    "complete_user_flows": {
        "path": "tests/e2e/test_complete_user_flows.py",
        "description": "Complete user journey and interaction flows",
        "timeout": 300,
        "requires_frontend": False
    },
    "agent_interactions": {
        "path": "tests/e2e/test_agent_interactions.py", 
        "description": "Agent-to-agent communication and collaboration",
        "timeout": 300,
        "requires_frontend": False
    },
    "visual_regression": {
        "path": "tests/visual/test_ui_regression.py",
        "description": "Visual regression testing with screenshots",
        "timeout": 600,
        "requires_frontend": True,
        "requires_playwright": True
    },
    "browser_automation": {
        "path": "tests/playwright/test_browser_automation.py",
        "description": "Full browser automation and multi-tab testing",
        "timeout": 900,
        "requires_frontend": True,
        "requires_playwright": True
    },
    "real_world_scenarios": {
        "path": "tests/scenarios/test_real_world_usage.py",
        "description": "Real-world usage patterns and workflows",
        "timeout": 600,
        "requires_frontend": False
    }
}

REPORT_DIR = Path("test_reports")
SCREENSHOT_DIR = Path("test_screenshots")

# Ensure directories exist
REPORT_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)


class E2ETestRunner:
    """Main test runner for E2E test suites"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
        self.frontend_available = False
        self.playwright_available = False
        
    async def check_prerequisites(self) -> Dict[str, bool]:
        """Check if prerequisites are available"""
        prerequisites = {
            "frontend": False,
            "playwright": False,
            "websocket_server": False
        }
        
        # Check if frontend is running
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:3000", timeout=5) as response:
                    if response.status == 200:
                        prerequisites["frontend"] = True
                        logger.info("✓ Frontend is available at localhost:3000")
                    else:
                        logger.warning("✗ Frontend returned non-200 status")
        except Exception as e:
            logger.warning(f"✗ Frontend not available: {e}")
        
        # Check if Playwright is installed
        try:
            from playwright.async_api import async_playwright
            prerequisites["playwright"] = True
            logger.info("✓ Playwright is available")
        except ImportError:
            logger.warning("✗ Playwright not available - install with: pip install playwright && playwright install")
        
        # Check if WebSocket server dependencies are available
        try:
            from src.chat.websocket_manager import WebSocketManager
            prerequisites["websocket_server"] = True
            logger.info("✓ WebSocket server dependencies available")
        except ImportError as e:
            logger.error(f"✗ WebSocket server dependencies missing: {e}")
        
        self.frontend_available = prerequisites["frontend"]
        self.playwright_available = prerequisites["playwright"]
        
        return prerequisites
    
    def should_run_suite(self, suite_name: str, suite_config: Dict, prerequisites: Dict[str, bool]) -> bool:
        """Determine if a test suite should be run based on prerequisites"""
        
        if suite_config.get("requires_frontend", False) and not prerequisites["frontend"]:
            logger.warning(f"Skipping {suite_name}: Frontend not available")
            return False
            
        if suite_config.get("requires_playwright", False) and not prerequisites["playwright"]:
            logger.warning(f"Skipping {suite_name}: Playwright not available")
            return False
            
        if not prerequisites["websocket_server"]:
            logger.error(f"Skipping {suite_name}: WebSocket server dependencies missing")
            return False
            
        return True
    
    async def run_test_suite(self, suite_name: str, suite_config: Dict, args: argparse.Namespace) -> Dict:
        """Run a single test suite"""
        logger.info(f"Running test suite: {suite_name}")
        logger.info(f"Description: {suite_config['description']}")
        
        start_time = time.time()
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            suite_config["path"],
            "-v",
            "--tb=short",
            f"--timeout={suite_config['timeout']}",
            "--capture=no" if args.verbose else "--capture=sys"
        ]
        
        # Add additional pytest arguments
        if args.markers:
            cmd.extend(["-m", args.markers])
            
        if args.keyword:
            cmd.extend(["-k", args.keyword])
            
        if args.maxfail:
            cmd.extend(["--maxfail", str(args.maxfail)])
        
        # Add JUnit XML report
        report_file = REPORT_DIR / f"{suite_name}_report.xml"
        cmd.extend(["--junitxml", str(report_file)])
        
        # Add HTML report if pytest-html is available
        try:
            import pytest_html
            html_report = REPORT_DIR / f"{suite_name}_report.html"
            cmd.extend(["--html", str(html_report), "--self-contained-html"])
        except ImportError:
            pass
        
        # Run the test suite
        try:
            logger.info(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=suite_config["timeout"] + 60  # Add buffer time
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse results
            suite_result = {
                "name": suite_name,
                "description": suite_config["description"],
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "report_file": str(report_file) if report_file.exists() else None
            }
            
            if suite_result["success"]:
                logger.info(f"✓ {suite_name} completed successfully in {duration:.2f}s")
            else:
                logger.error(f"✗ {suite_name} failed in {duration:.2f}s")
                if args.verbose:
                    logger.error(f"STDOUT:\n{result.stdout}")
                    logger.error(f"STDERR:\n{result.stderr}")
            
            return suite_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"✗ {suite_name} timed out after {suite_config['timeout']}s")
            return {
                "name": suite_name,
                "description": suite_config["description"],
                "duration": suite_config["timeout"],
                "return_code": -1,
                "stdout": "",
                "stderr": "Test suite timed out",
                "success": False,
                "report_file": None
            }
        except Exception as e:
            logger.error(f"✗ {suite_name} failed with exception: {e}")
            return {
                "name": suite_name,
                "description": suite_config["description"],
                "duration": 0,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "report_file": None
            }
    
    async def run_all_suites(self, args: argparse.Namespace) -> Dict:
        """Run all test suites"""
        self.start_time = datetime.now()
        logger.info(f"Starting E2E test run at {self.start_time}")
        
        # Check prerequisites
        prerequisites = await self.check_prerequisites()
        
        # Filter suites to run
        suites_to_run = {}
        if args.suites:
            # Run only specified suites
            for suite_name in args.suites:
                if suite_name in TEST_SUITES:
                    suites_to_run[suite_name] = TEST_SUITES[suite_name]
                else:
                    logger.warning(f"Unknown test suite: {suite_name}")
        else:
            # Run all suites that meet prerequisites
            for suite_name, suite_config in TEST_SUITES.items():
                if self.should_run_suite(suite_name, suite_config, prerequisites):
                    suites_to_run[suite_name] = suite_config
        
        if not suites_to_run:
            logger.error("No test suites to run!")
            return {"success": False, "results": []}
        
        logger.info(f"Running {len(suites_to_run)} test suites: {list(suites_to_run.keys())}")
        
        # Run test suites
        results = []
        for suite_name, suite_config in suites_to_run.items():
            if args.fail_fast and results and not results[-1]["success"]:
                logger.info(f"Skipping {suite_name} due to --fail-fast and previous failure")
                continue
                
            result = await self.run_test_suite(suite_name, suite_config, args)
            results.append(result)
        
        self.end_time = datetime.now()
        
        # Generate summary
        total_duration = sum(r["duration"] for r in results)
        successful_suites = [r for r in results if r["success"]]
        failed_suites = [r for r in results if not r["success"]]
        
        summary = {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_duration": total_duration,
            "total_suites": len(results),
            "successful_suites": len(successful_suites),
            "failed_suites": len(failed_suites),
            "success_rate": len(successful_suites) / len(results) if results else 0,
            "prerequisites": prerequisites,
            "results": results
        }
        
        return summary
    
    def generate_report(self, summary: Dict, args: argparse.Namespace):
        """Generate comprehensive test report"""
        
        # JSON report
        json_report_path = REPORT_DIR / f"e2e_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_report_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Console summary
        logger.info("\n" + "="*80)
        logger.info("E2E TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Start Time: {summary['start_time']}")
        logger.info(f"End Time: {summary['end_time']}")
        logger.info(f"Total Duration: {summary['total_duration']:.2f}s")
        logger.info(f"Total Suites: {summary['total_suites']}")
        logger.info(f"Successful: {summary['successful_suites']}")
        logger.info(f"Failed: {summary['failed_suites']}")
        logger.info(f"Success Rate: {summary['success_rate']:.1%}")
        
        logger.info("\nPREREQUISITES:")
        for prereq, available in summary['prerequisites'].items():
            status = "✓" if available else "✗"
            logger.info(f"  {status} {prereq}")
        
        logger.info("\nSUITE RESULTS:")
        for result in summary['results']:
            status = "✓" if result['success'] else "✗"
            logger.info(f"  {status} {result['name']} ({result['duration']:.2f}s)")
            if not result['success'] and args.verbose:
                logger.info(f"    Error: {result['stderr'][:200]}...")
        
        if summary['failed_suites'] > 0:
            logger.info("\nFAILED SUITES:")
            for result in summary['results']:
                if not result['success']:
                    logger.info(f"  - {result['name']}: {result['stderr'][:100]}...")
        
        logger.info(f"\nDetailed reports saved to: {REPORT_DIR}")
        logger.info(f"Screenshots saved to: {SCREENSHOT_DIR}")
        logger.info(f"JSON summary: {json_report_path}")
        logger.info("="*80)
        
        # Return exit code
        return 0 if summary['failed_suites'] == 0 else 1


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="E2E Test Runner for OpenCode Slack")
    
    parser.add_argument(
        "--suites", 
        nargs="+", 
        choices=list(TEST_SUITES.keys()),
        help="Specific test suites to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true", 
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--markers", "-m",
        help="Pytest markers to filter tests"
    )
    
    parser.add_argument(
        "--keyword", "-k",
        help="Pytest keyword expression to filter tests"
    )
    
    parser.add_argument(
        "--maxfail",
        type=int,
        help="Stop after N failures"
    )
    
    parser.add_argument(
        "--list-suites",
        action="store_true",
        help="List available test suites"
    )
    
    args = parser.parse_args()
    
    if args.list_suites:
        print("Available test suites:")
        for name, config in TEST_SUITES.items():
            print(f"  {name}: {config['description']}")
            print(f"    Path: {config['path']}")
            print(f"    Timeout: {config['timeout']}s")
            if config.get('requires_frontend'):
                print("    Requires: Frontend")
            if config.get('requires_playwright'):
                print("    Requires: Playwright")
            print()
        return 0
    
    # Run tests
    runner = E2ETestRunner()
    summary = await runner.run_all_suites(args)
    exit_code = runner.generate_report(summary, args)
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        sys.exit(1)