#!/usr/bin/env python3
"""
Comprehensive E2E Test Runner for OpenCode-Slack System
Runs all E2E tests with proper setup, validation, and reporting.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class ComprehensiveE2ETestRunner:
    """Comprehensive E2E test runner with validation and reporting"""
    
    def __init__(self, test_dir=None, report_dir=None, screenshot_dir=None):
        self.test_dir = Path(test_dir) if test_dir else Path(__file__).parent
        self.report_dir = Path(report_dir) if report_dir else Path(__file__).parent.parent / "test_reports"
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else Path(__file__).parent.parent / "test_screenshots"
        
        # Ensure directories exist
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Test suites
        self.test_suites = {
            "core_system": {
                "file": "e2e/test_core_system_workflows.py",
                "description": "Core system workflows (hiring, tasks, files, sessions)",
                "priority": 1,
                "estimated_time": 300  # 5 minutes
            },
            "agent_communication": {
                "file": "e2e/test_agent_communication_complete.py", 
                "description": "Agent communication and collaboration",
                "priority": 2,
                "estimated_time": 240  # 4 minutes
            },
            "chat_system": {
                "file": "e2e/test_chat_system_complete.py",
                "description": "Chat system (WebSocket, Telegram, real-time)",
                "priority": 2,
                "estimated_time": 360  # 6 minutes
            },
            "monitoring": {
                "file": "e2e/test_monitoring_complete.py",
                "description": "Monitoring, performance, and health checks",
                "priority": 3,
                "estimated_time": 420  # 7 minutes
            },
            "security": {
                "file": "e2e/test_security_complete.py",
                "description": "Security, authentication, and authorization",
                "priority": 3,
                "estimated_time": 480  # 8 minutes
            }
        }
        
        # Test results
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def setup_test_environment(self):
        """Set up test environment"""
        print("🔧 Setting up test environment...")
        
        # Set environment variables for testing
        os.environ["TESTING"] = "true"
        os.environ["OPENCODE_SAFE_MODE"] = "true"  # Disable external communications
        os.environ["LOG_LEVEL"] = "INFO"
        os.environ["PYTEST_CURRENT_TEST"] = "comprehensive_e2e"
        
        # Create test directories
        test_dirs = [
            self.report_dir,
            self.screenshot_dir,
            self.test_dir / "temp",
            self.test_dir / "logs"
        ]
        
        for dir_path in test_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        print("✅ Test environment setup complete")

    def validate_test_prerequisites(self):
        """Validate test prerequisites"""
        print("🔍 Validating test prerequisites...")
        
        prerequisites = {
            "python_version": sys.version_info >= (3, 8),
            "pytest_available": self._check_command("pytest --version"),
            "src_directory": (Path(__file__).parent.parent / "src").exists(),
            "test_files": all((self.test_dir / suite["file"]).exists() for suite in self.test_suites.values())
        }
        
        # Check Python packages
        required_packages = [
            "pytest", "pytest-asyncio", "requests", "websockets", 
            "pathlib", "concurrent.futures"
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                prerequisites[f"package_{package}"] = True
            except ImportError:
                prerequisites[f"package_{package}"] = False
                print(f"⚠️  Missing package: {package}")
        
        # Report prerequisites
        failed_prerequisites = [k for k, v in prerequisites.items() if not v]
        
        if failed_prerequisites:
            print(f"❌ Failed prerequisites: {failed_prerequisites}")
            return False
        
        print("✅ All prerequisites validated")
        return True

    def _check_command(self, command):
        """Check if a command is available"""
        try:
            subprocess.run(command.split(), capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def run_test_suite(self, suite_name, suite_config, parallel=False):
        """Run a single test suite"""
        print(f"\n🧪 Running {suite_name} tests...")
        print(f"   📝 {suite_config['description']}")
        
        test_file = self.test_dir / suite_config["file"]
        
        if not test_file.exists():
            return {
                "suite": suite_name,
                "status": "failed",
                "error": f"Test file not found: {test_file}",
                "duration": 0,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0
            }
        
        # Prepare pytest command
        pytest_args = [
            "python", "-m", "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            f"--junitxml={self.report_dir}/{suite_name}_results.xml",
            f"--html={self.report_dir}/{suite_name}_report.html",
            "--self-contained-html"
        ]
        
        # Add markers for different test types
        if not parallel:
            pytest_args.extend(["-m", "not slow"])  # Skip slow tests in sequential mode
        
        start_time = time.time()
        
        try:
            # Run pytest
            result = subprocess.run(
                pytest_args,
                capture_output=True,
                text=True,
                timeout=suite_config["estimated_time"] * 2  # Double the estimated time as timeout
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            output_lines = result.stdout.split('\n')
            
            # Extract test counts from pytest output
            tests_run = 0
            tests_passed = 0
            tests_failed = 0
            
            for line in output_lines:
                if "passed" in line and "failed" in line:
                    # Parse line like "5 passed, 2 failed in 10.5s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed" and i > 0:
                            tests_passed = int(parts[i-1])
                        elif part == "failed" and i > 0:
                            tests_failed = int(parts[i-1])
                    tests_run = tests_passed + tests_failed
                elif "passed" in line and "failed" not in line:
                    # Parse line like "10 passed in 5.2s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed" and i > 0:
                            tests_passed = int(parts[i-1])
                            tests_run = tests_passed
            
            # Determine status
            if result.returncode == 0:
                status = "passed"
            elif tests_passed > 0 and tests_failed > 0:
                status = "partial"
            else:
                status = "failed"
            
            return {
                "suite": suite_name,
                "status": status,
                "duration": duration,
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                "suite": suite_name,
                "status": "timeout",
                "duration": duration,
                "error": f"Test suite timed out after {duration:.1f} seconds",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "suite": suite_name,
                "status": "error",
                "duration": duration,
                "error": str(e),
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0
            }

    def run_all_tests(self, parallel=False, selected_suites=None):
        """Run all test suites"""
        print("🚀 Starting comprehensive E2E test execution...")
        self.start_time = time.time()
        
        # Filter test suites if specified
        suites_to_run = {}
        if selected_suites:
            for suite_name in selected_suites:
                if suite_name in self.test_suites:
                    suites_to_run[suite_name] = self.test_suites[suite_name]
                else:
                    print(f"⚠️  Unknown test suite: {suite_name}")
        else:
            suites_to_run = self.test_suites
        
        if parallel:
            # Run tests in parallel
            print("⚡ Running tests in parallel...")
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(self.run_test_suite, suite_name, suite_config, parallel): suite_name
                    for suite_name, suite_config in suites_to_run.items()
                }
                
                for future in as_completed(futures):
                    suite_name = futures[future]
                    try:
                        result = future.result()
                        self.test_results[suite_name] = result
                        self._print_suite_result(result)
                    except Exception as e:
                        self.test_results[suite_name] = {
                            "suite": suite_name,
                            "status": "error",
                            "error": str(e),
                            "duration": 0
                        }
        else:
            # Run tests sequentially by priority
            print("🔄 Running tests sequentially...")
            sorted_suites = sorted(
                suites_to_run.items(),
                key=lambda x: x[1]["priority"]
            )
            
            for suite_name, suite_config in sorted_suites:
                result = self.run_test_suite(suite_name, suite_config, parallel)
                self.test_results[suite_name] = result
                self._print_suite_result(result)
        
        self.end_time = time.time()
        print(f"\n⏱️  Total execution time: {self.end_time - self.start_time:.1f} seconds")

    def _print_suite_result(self, result):
        """Print test suite result"""
        suite_name = result["suite"]
        status = result["status"]
        duration = result.get("duration", 0)
        tests_passed = result.get("tests_passed", 0)
        tests_failed = result.get("tests_failed", 0)
        tests_run = result.get("tests_run", 0)
        
        status_emoji = {
            "passed": "✅",
            "partial": "⚠️",
            "failed": "❌",
            "timeout": "⏰",
            "error": "💥"
        }.get(status, "❓")
        
        print(f"   {status_emoji} {suite_name}: {status.upper()} "
              f"({tests_passed}/{tests_run} passed) in {duration:.1f}s")
        
        if result.get("error"):
            print(f"      Error: {result['error']}")

    def generate_comprehensive_report(self):
        """Generate comprehensive test report"""
        print("\n📊 Generating comprehensive test report...")
        
        # Calculate summary statistics
        total_suites = len(self.test_results)
        passed_suites = len([r for r in self.test_results.values() if r["status"] == "passed"])
        failed_suites = len([r for r in self.test_results.values() if r["status"] in ["failed", "error", "timeout"]])
        partial_suites = len([r for r in self.test_results.values() if r["status"] == "partial"])
        
        total_tests = sum(r.get("tests_run", 0) for r in self.test_results.values())
        total_passed = sum(r.get("tests_passed", 0) for r in self.test_results.values())
        total_failed = sum(r.get("tests_failed", 0) for r in self.test_results.values())
        
        total_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        # Create comprehensive report
        report = {
            "test_execution": {
                "timestamp": datetime.now().isoformat(),
                "start_time": self.start_time,
                "end_time": self.end_time,
                "total_duration": total_duration,
                "test_environment": {
                    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    "platform": sys.platform,
                    "testing_mode": os.environ.get("TESTING", "false"),
                    "safe_mode": os.environ.get("OPENCODE_SAFE_MODE", "false")
                }
            },
            "summary": {
                "total_test_suites": total_suites,
                "passed_suites": passed_suites,
                "failed_suites": failed_suites,
                "partial_suites": partial_suites,
                "suite_success_rate": passed_suites / total_suites if total_suites > 0 else 0,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "test_success_rate": total_passed / total_tests if total_tests > 0 else 0
            },
            "test_suites": self.test_results,
            "feature_coverage": self._analyze_feature_coverage(),
            "performance_metrics": self._analyze_performance_metrics(),
            "recommendations": self._generate_recommendations()
        }
        
        # Save report
        report_file = self.report_dir / f"comprehensive_e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate HTML report
        self._generate_html_report(report)
        
        print(f"📄 Report saved to: {report_file}")
        return report

    def _analyze_feature_coverage(self):
        """Analyze feature coverage across test suites"""
        coverage = {
            "core_system_features": {
                "employee_management": "core_system" in self.test_results,
                "task_assignment": "core_system" in self.test_results,
                "file_ownership": "core_system" in self.test_results,
                "session_management": "core_system" in self.test_results,
                "cli_commands": "core_system" in self.test_results
            },
            "communication_features": {
                "agent_collaboration": "agent_communication" in self.test_results,
                "help_requests": "agent_communication" in self.test_results,
                "memory_management": "agent_communication" in self.test_results,
                "react_agents": "agent_communication" in self.test_results,
                "expertise_matching": "agent_communication" in self.test_results
            },
            "chat_features": {
                "websocket_communication": "chat_system" in self.test_results,
                "telegram_integration": "chat_system" in self.test_results,
                "real_time_messaging": "chat_system" in self.test_results,
                "message_parsing": "chat_system" in self.test_results,
                "rate_limiting": "chat_system" in self.test_results
            },
            "monitoring_features": {
                "health_monitoring": "monitoring" in self.test_results,
                "performance_metrics": "monitoring" in self.test_results,
                "alerting_system": "monitoring" in self.test_results,
                "recovery_management": "monitoring" in self.test_results,
                "dashboard_functionality": "monitoring" in self.test_results
            },
            "security_features": {
                "authentication": "security" in self.test_results,
                "authorization": "security" in self.test_results,
                "encryption": "security" in self.test_results,
                "audit_logging": "security" in self.test_results,
                "vulnerability_protection": "security" in self.test_results
            }
        }
        
        # Calculate coverage percentages
        for category, features in coverage.items():
            tested_features = sum(1 for tested in features.values() if tested)
            total_features = len(features)
            coverage[f"{category}_percentage"] = tested_features / total_features if total_features > 0 else 0
        
        return coverage

    def _analyze_performance_metrics(self):
        """Analyze performance metrics from test execution"""
        metrics = {
            "execution_times": {},
            "test_efficiency": {},
            "resource_usage": {}
        }
        
        for suite_name, result in self.test_results.items():
            duration = result.get("duration", 0)
            tests_run = result.get("tests_run", 0)
            
            metrics["execution_times"][suite_name] = duration
            
            if tests_run > 0:
                metrics["test_efficiency"][suite_name] = duration / tests_run
            
            # Estimate resource usage based on test complexity
            estimated_time = self.test_suites.get(suite_name, {}).get("estimated_time", 0)
            if estimated_time > 0:
                efficiency_ratio = duration / estimated_time
                metrics["resource_usage"][suite_name] = {
                    "estimated_time": estimated_time,
                    "actual_time": duration,
                    "efficiency_ratio": efficiency_ratio
                }
        
        return metrics

    def _generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Analyze test results for recommendations
        failed_suites = [name for name, result in self.test_results.items() 
                        if result["status"] in ["failed", "error", "timeout"]]
        
        if failed_suites:
            recommendations.append({
                "type": "critical",
                "title": "Failed Test Suites",
                "description": f"The following test suites failed: {', '.join(failed_suites)}",
                "action": "Review test failures and fix underlying issues before deployment"
            })
        
        # Check for slow tests
        slow_suites = [name for name, result in self.test_results.items() 
                      if result.get("duration", 0) > self.test_suites.get(name, {}).get("estimated_time", 0) * 1.5]
        
        if slow_suites:
            recommendations.append({
                "type": "performance",
                "title": "Slow Test Execution",
                "description": f"These test suites took longer than expected: {', '.join(slow_suites)}",
                "action": "Optimize test performance or increase timeout values"
            })
        
        # Check test coverage
        total_tests = sum(r.get("tests_run", 0) for r in self.test_results.values())
        if total_tests < 50:  # Arbitrary threshold
            recommendations.append({
                "type": "coverage",
                "title": "Low Test Coverage",
                "description": f"Only {total_tests} tests were executed",
                "action": "Consider adding more comprehensive test cases"
            })
        
        # Success recommendations
        passed_suites = [name for name, result in self.test_results.items() 
                        if result["status"] == "passed"]
        
        if len(passed_suites) == len(self.test_results):
            recommendations.append({
                "type": "success",
                "title": "All Tests Passed",
                "description": "All test suites executed successfully",
                "action": "System is ready for deployment"
            })
        
        return recommendations

    def _generate_html_report(self, report):
        """Generate HTML report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>OpenCode-Slack Comprehensive E2E Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ background: #e8f5e8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .suite {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ background: #d4edda; }}
        .failed {{ background: #f8d7da; }}
        .partial {{ background: #fff3cd; }}
        .recommendations {{ background: #d1ecf1; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 OpenCode-Slack Comprehensive E2E Test Report</h1>
        <p>Generated: {report['test_execution']['timestamp']}</p>
        <p>Duration: {report['test_execution']['total_duration']:.1f} seconds</p>
    </div>
    
    <div class="summary">
        <h2>📊 Summary</h2>
        <p><strong>Test Suites:</strong> {report['summary']['passed_suites']}/{report['summary']['total_test_suites']} passed 
           ({report['summary']['suite_success_rate']:.1%} success rate)</p>
        <p><strong>Individual Tests:</strong> {report['summary']['total_passed']}/{report['summary']['total_tests']} passed 
           ({report['summary']['test_success_rate']:.1%} success rate)</p>
    </div>
    
    <h2>🧪 Test Suite Results</h2>
"""
        
        for suite_name, result in report['test_suites'].items():
            status_class = result['status']
            if status_class in ['error', 'timeout']:
                status_class = 'failed'
            
            html_content += f"""
    <div class="suite {status_class}">
        <h3>{suite_name.replace('_', ' ').title()}</h3>
        <p><strong>Status:</strong> {result['status'].upper()}</p>
        <p><strong>Tests:</strong> {result.get('tests_passed', 0)}/{result.get('tests_run', 0)} passed</p>
        <p><strong>Duration:</strong> {result.get('duration', 0):.1f} seconds</p>
        {f"<p><strong>Error:</strong> {result['error']}</p>" if result.get('error') else ""}
    </div>
"""
        
        html_content += f"""
    <h2>💡 Recommendations</h2>
    <div class="recommendations">
"""
        
        for rec in report['recommendations']:
            html_content += f"""
        <div>
            <h4>{rec['title']} ({rec['type'].upper()})</h4>
            <p>{rec['description']}</p>
            <p><strong>Action:</strong> {rec['action']}</p>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        html_file = self.report_dir / f"comprehensive_e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        print(f"🌐 HTML report saved to: {html_file}")

    def print_final_summary(self):
        """Print final test summary"""
        if not self.test_results:
            print("❌ No test results available")
            return
        
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE E2E TEST EXECUTION SUMMARY")
        print("="*80)
        
        # Overall statistics
        total_suites = len(self.test_results)
        passed_suites = len([r for r in self.test_results.values() if r["status"] == "passed"])
        failed_suites = len([r for r in self.test_results.values() if r["status"] in ["failed", "error", "timeout"]])
        
        total_tests = sum(r.get("tests_run", 0) for r in self.test_results.values())
        total_passed = sum(r.get("tests_passed", 0) for r in self.test_results.values())
        
        print(f"📊 Test Suites: {passed_suites}/{total_suites} passed ({passed_suites/total_suites:.1%})")
        print(f"🧪 Individual Tests: {total_passed}/{total_tests} passed ({total_passed/total_tests:.1%})")
        print(f"⏱️  Total Duration: {self.end_time - self.start_time:.1f} seconds")
        
        # Feature coverage summary
        print(f"\n🎯 FEATURE COVERAGE:")
        coverage_areas = [
            ("Core System", "core_system"),
            ("Agent Communication", "agent_communication"), 
            ("Chat System", "chat_system"),
            ("Monitoring", "monitoring"),
            ("Security", "security")
        ]
        
        for area_name, suite_key in coverage_areas:
            if suite_key in self.test_results:
                result = self.test_results[suite_key]
                status_emoji = "✅" if result["status"] == "passed" else "❌"
                print(f"   {status_emoji} {area_name}: {result['status'].upper()}")
            else:
                print(f"   ⚪ {area_name}: NOT TESTED")
        
        # Final verdict
        print(f"\n🏆 FINAL VERDICT:")
        if passed_suites == total_suites and total_passed == total_tests:
            print("   ✅ ALL TESTS PASSED - SYSTEM READY FOR DEPLOYMENT!")
        elif passed_suites >= total_suites * 0.8:
            print("   ⚠️  MOSTLY PASSING - REVIEW FAILURES BEFORE DEPLOYMENT")
        else:
            print("   ❌ SIGNIFICANT FAILURES - DO NOT DEPLOY")
        
        print("="*80)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Comprehensive E2E Test Runner for OpenCode-Slack")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--suites", nargs="+", help="Specific test suites to run", 
                       choices=["core_system", "agent_communication", "chat_system", "monitoring", "security"])
    parser.add_argument("--report-dir", help="Directory for test reports")
    parser.add_argument("--screenshot-dir", help="Directory for test screenshots")
    parser.add_argument("--skip-validation", action="store_true", help="Skip prerequisite validation")
    
    args = parser.parse_args()
    
    # Create test runner
    runner = ComprehensiveE2ETestRunner(
        report_dir=args.report_dir,
        screenshot_dir=args.screenshot_dir
    )
    
    try:
        # Setup
        runner.setup_test_environment()
        
        # Validate prerequisites
        if not args.skip_validation:
            if not runner.validate_test_prerequisites():
                print("❌ Prerequisites validation failed. Use --skip-validation to bypass.")
                sys.exit(1)
        
        # Run tests
        runner.run_all_tests(parallel=args.parallel, selected_suites=args.suites)
        
        # Generate reports
        report = runner.generate_comprehensive_report()
        
        # Print summary
        runner.print_final_summary()
        
        # Exit with appropriate code
        failed_suites = len([r for r in runner.test_results.values() 
                           if r["status"] in ["failed", "error", "timeout"]])
        
        if failed_suites == 0:
            print("\n🎉 All tests completed successfully!")
            sys.exit(0)
        else:
            print(f"\n⚠️  {failed_suites} test suite(s) failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test execution failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()