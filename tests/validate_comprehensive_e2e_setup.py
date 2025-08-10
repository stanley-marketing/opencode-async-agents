#!/usr/bin/env python3
"""
Comprehensive E2E Test Setup Validation Script
Validates that all E2E tests are properly configured and ready to run.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class E2ETestValidator:
    """Validates comprehensive E2E test setup"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = Path(__file__).parent
        self.validation_results = {}
        
    def validate_project_structure(self):
        """Validate project structure for E2E testing"""
        print("🔍 Validating project structure...")
        
        required_paths = {
            "src_directory": self.project_root / "src",
            "tests_directory": self.test_dir,
            "e2e_directory": self.test_dir / "e2e",
            "conftest_file": self.test_dir / "conftest.py",
            "requirements_file": self.project_root / "requirements.txt"
        }
        
        structure_results = {}
        
        for name, path in required_paths.items():
            exists = path.exists()
            structure_results[name] = {
                "path": str(path),
                "exists": exists,
                "type": "directory" if path.is_dir() else "file" if exists else "missing"
            }
            
            status = "✅" if exists else "❌"
            print(f"   {status} {name}: {path}")
        
        self.validation_results["project_structure"] = structure_results
        return all(result["exists"] for result in structure_results.values())

    def validate_test_files(self):
        """Validate E2E test files"""
        print("\n🧪 Validating E2E test files...")
        
        expected_test_files = {
            "core_system_tests": "e2e/test_core_system_workflows.py",
            "agent_communication_tests": "e2e/test_agent_communication_complete.py",
            "chat_system_tests": "e2e/test_chat_system_complete.py",
            "monitoring_tests": "e2e/test_monitoring_complete.py",
            "security_tests": "e2e/test_security_complete.py"
        }
        
        test_file_results = {}
        
        for test_name, file_path in expected_test_files.items():
            full_path = self.test_dir / file_path
            exists = full_path.exists()
            
            if exists:
                # Check file content
                content = full_path.read_text()
                has_test_class = "class Test" in content
                has_test_methods = "def test_" in content
                line_count = len(content.split('\n'))
                
                test_file_results[test_name] = {
                    "path": str(full_path),
                    "exists": True,
                    "has_test_class": has_test_class,
                    "has_test_methods": has_test_methods,
                    "line_count": line_count,
                    "status": "complete" if has_test_class and has_test_methods else "incomplete"
                }
            else:
                test_file_results[test_name] = {
                    "path": str(full_path),
                    "exists": False,
                    "status": "missing"
                }
            
            status = "✅" if exists and test_file_results[test_name]["status"] == "complete" else "❌"
            print(f"   {status} {test_name}: {file_path}")
            
            if exists:
                result = test_file_results[test_name]
                print(f"      📊 {result['line_count']} lines, "
                      f"Classes: {'✅' if result['has_test_class'] else '❌'}, "
                      f"Methods: {'✅' if result['has_test_methods'] else '❌'}")
        
        self.validation_results["test_files"] = test_file_results
        return all(result["status"] == "complete" for result in test_file_results.values())

    def validate_dependencies(self):
        """Validate test dependencies"""
        print("\n📦 Validating test dependencies...")
        
        required_packages = [
            "pytest",
            "pytest-asyncio", 
            "pytest-cov",
            "requests",
            "websockets",
            "pathlib",
            "concurrent.futures",
            "threading",
            "asyncio",
            "json",
            "time"
        ]
        
        dependency_results = {}
        
        for package in required_packages:
            try:
                # Try to import the package
                if package == "pytest-asyncio":
                    import pytest_asyncio
                elif package == "pytest-cov":
                    import pytest_cov
                elif package == "concurrent.futures":
                    import concurrent.futures
                else:
                    __import__(package)
                
                dependency_results[package] = {
                    "available": True,
                    "status": "installed"
                }
                print(f"   ✅ {package}")
                
            except ImportError:
                dependency_results[package] = {
                    "available": False,
                    "status": "missing"
                }
                print(f"   ❌ {package} - NOT INSTALLED")
        
        self.validation_results["dependencies"] = dependency_results
        
        missing_packages = [pkg for pkg, result in dependency_results.items() 
                          if not result["available"]]
        
        if missing_packages:
            print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
            print("   Install with: pip install " + " ".join(missing_packages))
        
        return len(missing_packages) == 0

    def validate_source_code_availability(self):
        """Validate source code components are available"""
        print("\n🔧 Validating source code components...")
        
        required_components = {
            "server": "src/server.py",
            "client": "src/client.py", 
            "file_ownership": "src/managers/file_ownership.py",
            "agent_manager": "src/agents/agent_manager.py",
            "communication_manager": "src/chat/communication_manager.py",
            "task_tracker": "src/trackers/task_progress.py",
            "session_manager": "src/utils/opencode_wrapper.py"
        }
        
        component_results = {}
        
        for component_name, file_path in required_components.items():
            full_path = self.project_root / file_path
            exists = full_path.exists()
            
            if exists:
                content = full_path.read_text()
                has_class = "class " in content
                line_count = len(content.split('\n'))
                
                component_results[component_name] = {
                    "path": str(full_path),
                    "exists": True,
                    "has_class": has_class,
                    "line_count": line_count,
                    "status": "available"
                }
            else:
                component_results[component_name] = {
                    "path": str(full_path),
                    "exists": False,
                    "status": "missing"
                }
            
            status = "✅" if exists else "❌"
            print(f"   {status} {component_name}: {file_path}")
        
        self.validation_results["source_components"] = component_results
        return all(result["exists"] for result in component_results.values())

    def validate_test_configuration(self):
        """Validate test configuration"""
        print("\n⚙️  Validating test configuration...")
        
        config_results = {}
        
        # Check conftest.py
        conftest_path = self.test_dir / "conftest.py"
        if conftest_path.exists():
            content = conftest_path.read_text()
            has_fixtures = "@pytest.fixture" in content
            has_markers = "pytest.mark" in content
            has_config = "pytest_configure" in content
            
            config_results["conftest"] = {
                "exists": True,
                "has_fixtures": has_fixtures,
                "has_markers": has_markers,
                "has_config": has_config,
                "status": "configured"
            }
            
            print(f"   ✅ conftest.py: Fixtures: {'✅' if has_fixtures else '❌'}, "
                  f"Markers: {'✅' if has_markers else '❌'}, "
                  f"Config: {'✅' if has_config else '❌'}")
        else:
            config_results["conftest"] = {
                "exists": False,
                "status": "missing"
            }
            print("   ❌ conftest.py: MISSING")
        
        # Check pytest configuration
        pytest_ini_path = self.project_root / "pytest.ini"
        pyproject_toml_path = self.project_root / "pyproject.toml"
        
        has_pytest_config = pytest_ini_path.exists() or pyproject_toml_path.exists()
        config_results["pytest_config"] = {
            "pytest_ini": pytest_ini_path.exists(),
            "pyproject_toml": pyproject_toml_path.exists(),
            "has_config": has_pytest_config
        }
        
        status = "✅" if has_pytest_config else "⚠️"
        print(f"   {status} pytest configuration: {'Available' if has_pytest_config else 'Optional'}")
        
        self.validation_results["test_configuration"] = config_results
        return True  # Configuration is optional

    def validate_test_runner(self):
        """Validate test runner script"""
        print("\n🏃 Validating test runner...")
        
        runner_path = self.test_dir / "run_comprehensive_e2e_tests.py"
        runner_results = {}
        
        if runner_path.exists():
            content = runner_path.read_text()
            has_main = "def main(" in content
            has_runner_class = "class ComprehensiveE2ETestRunner" in content
            has_argparse = "argparse" in content
            is_executable = os.access(runner_path, os.X_OK)
            
            runner_results = {
                "exists": True,
                "has_main": has_main,
                "has_runner_class": has_runner_class,
                "has_argparse": has_argparse,
                "is_executable": is_executable,
                "status": "ready"
            }
            
            print(f"   ✅ Test runner: Main: {'✅' if has_main else '❌'}, "
                  f"Class: {'✅' if has_runner_class else '❌'}, "
                  f"Args: {'✅' if has_argparse else '❌'}")
        else:
            runner_results = {
                "exists": False,
                "status": "missing"
            }
            print("   ❌ Test runner: MISSING")
        
        self.validation_results["test_runner"] = runner_results
        return runner_results.get("exists", False)

    def validate_environment_setup(self):
        """Validate environment setup"""
        print("\n🌍 Validating environment setup...")
        
        env_results = {
            "python_version": {
                "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "compatible": sys.version_info >= (3, 8),
                "status": "compatible" if sys.version_info >= (3, 8) else "incompatible"
            },
            "pytest_available": self._check_command("pytest --version"),
            "git_available": self._check_command("git --version"),
            "working_directory": {
                "path": str(Path.cwd()),
                "is_project_root": Path.cwd() == self.project_root or Path.cwd() == self.test_dir
            }
        }
        
        # Check Python version
        python_status = "✅" if env_results["python_version"]["compatible"] else "❌"
        print(f"   {python_status} Python {env_results['python_version']['version']}")
        
        # Check pytest
        pytest_status = "✅" if env_results["pytest_available"]["available"] else "❌"
        print(f"   {pytest_status} pytest: {env_results['pytest_available']['status']}")
        
        # Check git
        git_status = "✅" if env_results["git_available"]["available"] else "⚠️"
        print(f"   {git_status} git: {env_results['git_available']['status']}")
        
        # Check working directory
        wd_status = "✅" if env_results["working_directory"]["is_project_root"] else "⚠️"
        print(f"   {wd_status} Working directory: {env_results['working_directory']['path']}")
        
        self.validation_results["environment"] = env_results
        return (env_results["python_version"]["compatible"] and 
                env_results["pytest_available"]["available"])

    def _check_command(self, command):
        """Check if a command is available"""
        try:
            result = subprocess.run(command.split(), capture_output=True, check=True)
            return {
                "available": True,
                "status": "available",
                "output": result.stdout.decode().strip()
            }
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                "available": False,
                "status": "not_available"
            }

    def run_sample_test(self):
        """Run a sample test to verify setup"""
        print("\n🧪 Running sample test validation...")
        
        # Create a simple test file
        sample_test_content = '''
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def test_sample_validation():
    """Sample test to validate E2E setup"""
    assert True

def test_imports():
    """Test that we can import required modules"""
    import json
    import time
    import threading
    assert True

@pytest.mark.asyncio
async def test_async_support():
    """Test async support"""
    import asyncio
    await asyncio.sleep(0.01)
    assert True
'''
        
        sample_test_path = self.test_dir / "test_sample_validation.py"
        
        try:
            # Write sample test
            with open(sample_test_path, 'w') as f:
                f.write(sample_test_content)
            
            # Run sample test
            result = subprocess.run([
                "python", "-m", "pytest", 
                str(sample_test_path), 
                "-v", "--tb=short"
            ], capture_output=True, text=True, timeout=30)
            
            success = result.returncode == 0
            
            sample_results = {
                "test_created": True,
                "test_executed": True,
                "success": success,
                "returncode": result.returncode,
                "output": result.stdout,
                "errors": result.stderr
            }
            
            status = "✅" if success else "❌"
            print(f"   {status} Sample test execution: {'PASSED' if success else 'FAILED'}")
            
            if not success:
                print(f"      Error: {result.stderr}")
            
            # Clean up
            sample_test_path.unlink()
            
        except Exception as e:
            sample_results = {
                "test_created": False,
                "test_executed": False,
                "success": False,
                "error": str(e)
            }
            print(f"   ❌ Sample test execution: FAILED - {e}")
        
        self.validation_results["sample_test"] = sample_results
        return sample_results.get("success", False)

    def generate_validation_report(self):
        """Generate validation report"""
        print("\n📊 Generating validation report...")
        
        # Calculate overall status
        validation_checks = [
            self.validation_results.get("project_structure", {}).get("status", False),
            self.validation_results.get("test_files", {}).get("status", False),
            self.validation_results.get("dependencies", {}).get("status", False),
            self.validation_results.get("source_components", {}).get("status", False),
            self.validation_results.get("test_runner", {}).get("status", False),
            self.validation_results.get("environment", {}).get("status", False),
            self.validation_results.get("sample_test", {}).get("success", False)
        ]
        
        # Count successful validations
        successful_checks = sum(1 for check in validation_checks if check)
        total_checks = len(validation_checks)
        
        overall_status = "ready" if successful_checks == total_checks else "needs_attention"
        
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "success_rate": successful_checks / total_checks,
            "successful_checks": successful_checks,
            "total_checks": total_checks,
            "validation_results": self.validation_results,
            "recommendations": self._generate_validation_recommendations()
        }
        
        # Save report
        report_path = self.test_dir / f"e2e_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Validation report saved: {report_path}")
        return report

    def _generate_validation_recommendations(self):
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Check for missing dependencies
        deps = self.validation_results.get("dependencies", {})
        missing_deps = [pkg for pkg, result in deps.items() 
                       if not result.get("available", False)]
        
        if missing_deps:
            recommendations.append({
                "type": "critical",
                "title": "Missing Dependencies",
                "description": f"Install missing packages: {', '.join(missing_deps)}",
                "action": f"pip install {' '.join(missing_deps)}"
            })
        
        # Check for missing test files
        test_files = self.validation_results.get("test_files", {})
        missing_tests = [name for name, result in test_files.items() 
                        if not result.get("exists", False)]
        
        if missing_tests:
            recommendations.append({
                "type": "critical", 
                "title": "Missing Test Files",
                "description": f"Create missing test files: {', '.join(missing_tests)}",
                "action": "Run the comprehensive E2E test creation script"
            })
        
        # Check environment
        env = self.validation_results.get("environment", {})
        if not env.get("python_version", {}).get("compatible", False):
            recommendations.append({
                "type": "critical",
                "title": "Python Version",
                "description": "Python 3.8+ required for E2E tests",
                "action": "Upgrade Python to version 3.8 or higher"
            })
        
        # Success case
        if not recommendations:
            recommendations.append({
                "type": "success",
                "title": "Validation Complete",
                "description": "All E2E test components are properly configured",
                "action": "Ready to run comprehensive E2E tests"
            })
        
        return recommendations

    def print_validation_summary(self):
        """Print validation summary"""
        print("\n" + "="*80)
        print("🎯 E2E TEST SETUP VALIDATION SUMMARY")
        print("="*80)
        
        # Overall status
        overall_status = "READY" if all([
            all(result.get("exists", False) for result in self.validation_results.get("project_structure", {}).values()),
            all(result.get("status") == "complete" for result in self.validation_results.get("test_files", {}).values()),
            all(result.get("available", False) for result in self.validation_results.get("dependencies", {}).values()),
            self.validation_results.get("sample_test", {}).get("success", False)
        ]) else "NEEDS ATTENTION"
        
        status_emoji = "✅" if overall_status == "READY" else "⚠️"
        print(f"{status_emoji} Overall Status: {overall_status}")
        
        # Component status
        components = [
            ("Project Structure", "project_structure"),
            ("Test Files", "test_files"),
            ("Dependencies", "dependencies"),
            ("Source Components", "source_components"),
            ("Test Runner", "test_runner"),
            ("Environment", "environment"),
            ("Sample Test", "sample_test")
        ]
        
        print(f"\n📋 Component Status:")
        for component_name, key in components:
            if key in self.validation_results:
                if key == "sample_test":
                    status = "✅" if self.validation_results[key].get("success", False) else "❌"
                elif key in ["project_structure", "source_components"]:
                    status = "✅" if all(r.get("exists", False) for r in self.validation_results[key].values()) else "❌"
                elif key == "test_files":
                    status = "✅" if all(r.get("status") == "complete" for r in self.validation_results[key].values()) else "❌"
                elif key == "dependencies":
                    status = "✅" if all(r.get("available", False) for r in self.validation_results[key].values()) else "❌"
                else:
                    status = "✅" if self.validation_results[key].get("exists", False) else "❌"
                
                print(f"   {status} {component_name}")
            else:
                print(f"   ❓ {component_name}: Not checked")
        
        # Next steps
        print(f"\n🚀 Next Steps:")
        if overall_status == "READY":
            print("   1. Run comprehensive E2E tests: python tests/run_comprehensive_e2e_tests.py")
            print("   2. Review test results and reports")
            print("   3. Address any test failures before deployment")
        else:
            print("   1. Address validation issues listed above")
            print("   2. Re-run validation: python tests/validate_comprehensive_e2e_setup.py")
            print("   3. Proceed with E2E testing once validation passes")
        
        print("="*80)


def main():
    """Main validation function"""
    print("🔍 OpenCode-Slack Comprehensive E2E Test Setup Validation")
    print("="*60)
    
    validator = E2ETestValidator()
    
    try:
        # Run all validations
        validations = [
            validator.validate_project_structure(),
            validator.validate_test_files(),
            validator.validate_dependencies(),
            validator.validate_source_code_availability(),
            validator.validate_test_configuration(),
            validator.validate_test_runner(),
            validator.validate_environment_setup(),
            validator.run_sample_test()
        ]
        
        # Generate report
        report = validator.generate_validation_report()
        
        # Print summary
        validator.print_validation_summary()
        
        # Exit with appropriate code
        if all(validations):
            print("\n🎉 Validation completed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️  Validation completed with issues")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()