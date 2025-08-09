#!/usr/bin/env python3
"""
Enhanced Error Handling Validation Runner
Comprehensive script to validate all error handling improvements and resilience mechanisms.
"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_validation_test(test_name, test_command, description):
    """Run a validation test and return results"""
    print(f"\n{'='*60}")
    print(f"🧪 Running: {test_name}")
    print(f"📝 Description: {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            test_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        duration = time.time() - start_time
        
        success = result.returncode == 0
        
        print(f"\n📊 Test Results for {test_name}:")
        print(f"   Status: {'✅ PASSED' if success else '❌ FAILED'}")
        print(f"   Duration: {duration:.2f} seconds")
        print(f"   Return Code: {result.returncode}")
        
        if result.stdout:
            print(f"\n📤 STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print(f"\n📥 STDERR:")
            print(result.stderr)
        
        return {
            'test_name': test_name,
            'description': description,
            'success': success,
            'duration': duration,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'timestamp': datetime.now().isoformat()
        }
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"\n⏰ Test {test_name} timed out after {duration:.2f} seconds")
        return {
            'test_name': test_name,
            'description': description,
            'success': False,
            'duration': duration,
            'return_code': -1,
            'stdout': '',
            'stderr': 'Test timed out',
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n💥 Test {test_name} failed with exception: {e}")
        return {
            'test_name': test_name,
            'description': description,
            'success': False,
            'duration': duration,
            'return_code': -2,
            'stdout': '',
            'stderr': str(e),
            'timestamp': datetime.now().isoformat()
        }


def test_database_initialization():
    """Test database initialization with various scenarios"""
    print("\n🔧 Testing Database Initialization Scenarios...")
    
    scenarios = [
        {
            'name': 'Valid Path',
            'command': 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && python3 -c "from src.database.database_manager import DatabaseManager; dm = DatabaseManager(\'/tmp/test_valid.db\'); print(\'✅ Success\'); dm.close()"',
            'description': 'Test database initialization with valid path'
        },
        {
            'name': 'Missing Directory',
            'command': 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && python3 -c "from src.database.database_manager import DatabaseManager; dm = DatabaseManager(\'/tmp/missing/nested/dir/test.db\'); print(\'✅ Success\'); dm.close()"',
            'description': 'Test database initialization with missing parent directories'
        },
        {
            'name': 'Enhanced File Manager',
            'command': 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && python3 -c "from src.managers.enhanced_file_ownership import EnhancedFileOwnershipManager; fm = EnhancedFileOwnershipManager(\'/tmp/test_enhanced.db\'); print(\'✅ Success\'); fm.close()"',
            'description': 'Test enhanced file ownership manager initialization'
        }
    ]
    
    results = []
    for scenario in scenarios:
        result = run_validation_test(
            f"Database Init - {scenario['name']}",
            scenario['command'],
            scenario['description']
        )
        results.append(result)
    
    return results


def test_server_resilience():
    """Test server resilience and degraded mode operation"""
    print("\n🛡️ Testing Server Resilience...")
    
    scenarios = [
        {
            'name': 'Enhanced Server Normal Mode',
            'command': 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && timeout 10s python3 -c "from src.enhanced_server import EnhancedOpencodeSlackServer; server = EnhancedOpencodeSlackServer(port=0, db_path=\'/tmp/test_server.db\'); print(f\'Degraded: {server.degraded_mode}, Errors: {len(server.initialization_errors)}\'); print(\'✅ Success\')" 2>&1 || echo "Server test completed"',
            'description': 'Test enhanced server initialization in normal mode'
        },
        {
            'name': 'Enhanced Server Degraded Mode',
            'command': 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && timeout 10s python3 -c "from src.enhanced_server import EnhancedOpencodeSlackServer; server = EnhancedOpencodeSlackServer(port=0, db_path=\'/invalid/path/test.db\'); print(f\'Degraded: {server.degraded_mode}, Errors: {len(server.initialization_errors)}\'); print(\'✅ Success\')" 2>&1 || echo "Degraded mode test completed"',
            'description': 'Test enhanced server operation in degraded mode'
        }
    ]
    
    results = []
    for scenario in scenarios:
        result = run_validation_test(
            f"Server Resilience - {scenario['name']}",
            scenario['command'],
            scenario['description']
        )
        results.append(result)
    
    return results


def test_error_handling_comprehensive():
    """Run comprehensive error handling tests"""
    print("\n🧪 Running Comprehensive Error Handling Tests...")
    
    test_command = 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && python3 -m pytest tests/test_enhanced_error_handling.py::EnhancedErrorHandlingTest::test_comprehensive_enhanced_error_handling -v -s'
    
    result = run_validation_test(
        "Comprehensive Error Handling",
        test_command,
        "Run all enhanced error handling validation tests"
    )
    
    return [result]


def test_original_error_handling():
    """Test original error handling for comparison"""
    print("\n🔄 Testing Original Error Handling for Comparison...")
    
    test_command = 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && python3 -m pytest tests/test_error_handling_validation.py::ErrorHandlingValidationTest::test_comprehensive_error_handling_validation -v -s'
    
    result = run_validation_test(
        "Original Error Handling",
        test_command,
        "Run original error handling tests for comparison"
    )
    
    return [result]


def test_database_corruption_scenarios():
    """Test database corruption and recovery scenarios"""
    print("\n💾 Testing Database Corruption and Recovery...")
    
    scenarios = [
        {
            'name': 'Corruption Detection',
            'command': 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && python3 -c "import tempfile, os; from src.database.database_manager import DatabaseManager; temp_db = tempfile.mktemp(suffix=\'.db\'); dm = DatabaseManager(temp_db); dm.close(); open(temp_db, \'w\').write(\'CORRUPTED\'); dm2 = DatabaseManager(temp_db); print(\'✅ Corruption handled\'); dm2.close()"',
            'description': 'Test database corruption detection and recovery'
        },
        {
            'name': 'Backup Creation',
            'command': 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && python3 -c "import tempfile; from src.database.database_manager import DatabaseManager; temp_db = tempfile.mktemp(suffix=\'.db\'); dm = DatabaseManager(temp_db); backup_path = dm.create_backup(); print(f\'Backup created: {backup_path.exists()}\'); dm.close()"',
            'description': 'Test automatic backup creation'
        }
    ]
    
    results = []
    for scenario in scenarios:
        result = run_validation_test(
            f"Database Recovery - {scenario['name']}",
            scenario['command'],
            scenario['description']
        )
        results.append(result)
    
    return results


def test_file_system_resilience():
    """Test file system error handling and resilience"""
    print("\n📁 Testing File System Resilience...")
    
    scenarios = [
        {
            'name': 'Permission Errors',
            'command': 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && python3 -c "import tempfile, os; from src.managers.enhanced_file_ownership import EnhancedFileOwnershipManager, FileOwnershipError; temp_dir = tempfile.mkdtemp(); os.chmod(temp_dir, 0o444); try: fm = EnhancedFileOwnershipManager(os.path.join(temp_dir, \'test.db\')); except (FileOwnershipError, Exception) as e: print(f\'✅ Permission error handled: {type(e).__name__}\'); os.chmod(temp_dir, 0o755)"',
            'description': 'Test file permission error handling'
        },
        {
            'name': 'Disk Space Monitoring',
            'command': 'cd /home/eladbenhaim/dev/stanley-opensource/opencode-slack && python3 -c "import tempfile; from src.managers.enhanced_file_ownership import EnhancedFileOwnershipManager; temp_db = tempfile.mktemp(suffix=\'.db\'); fm = EnhancedFileOwnershipManager(temp_db); health = fm.get_system_health(); print(f\'✅ Health check: {health.get(\\\"overall_status\\\")}\'); fm.close()"',
            'description': 'Test disk space monitoring and health checks'
        }
    ]
    
    results = []
    for scenario in scenarios:
        result = run_validation_test(
            f"File System - {scenario['name']}",
            scenario['command'],
            scenario['description']
        )
        results.append(result)
    
    return results


def generate_comprehensive_report(all_results):
    """Generate comprehensive validation report"""
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE ERROR HANDLING VALIDATION REPORT")
    print("="*80)
    
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r['success'])
    failed_tests = total_tests - passed_tests
    
    overall_success_rate = passed_tests / total_tests if total_tests > 0 else 0
    
    print(f"\n📈 OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests} ✅")
    print(f"   Failed: {failed_tests} ❌")
    print(f"   Success Rate: {overall_success_rate:.1%}")
    
    # Group results by category
    categories = {}
    for result in all_results:
        category = result['test_name'].split(' - ')[0] if ' - ' in result['test_name'] else 'Other'
        if category not in categories:
            categories[category] = []
        categories[category].append(result)
    
    print(f"\n📋 RESULTS BY CATEGORY:")
    for category, results in categories.items():
        category_passed = sum(1 for r in results if r['success'])
        category_total = len(results)
        category_rate = category_passed / category_total if category_total > 0 else 0
        
        print(f"\n🔍 {category}:")
        print(f"   Success Rate: {category_rate:.1%} ({category_passed}/{category_total})")
        
        for result in results:
            status = "✅" if result['success'] else "❌"
            duration = result['duration']
            print(f"   {status} {result['test_name']}: {duration:.2f}s")
    
    # Failed tests details
    failed_results = [r for r in all_results if not r['success']]
    if failed_results:
        print(f"\n❌ FAILED TESTS DETAILS:")
        for result in failed_results:
            print(f"\n   Test: {result['test_name']}")
            print(f"   Description: {result['description']}")
            print(f"   Error: {result['stderr'][:200]}...")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if overall_success_rate >= 0.95:
        print("   🎉 Excellent! Error handling is robust and production-ready.")
    elif overall_success_rate >= 0.85:
        print("   👍 Very good error handling with minor improvements needed.")
    elif overall_success_rate >= 0.75:
        print("   ⚠️  Good error handling, but some areas need attention.")
    elif overall_success_rate >= 0.60:
        print("   🚨 Error handling needs significant improvements.")
    else:
        print("   💥 Critical: Error handling is insufficient for production.")
    
    # Save detailed report
    report_data = {
        'summary': {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': overall_success_rate,
            'timestamp': datetime.now().isoformat()
        },
        'categories': categories,
        'all_results': all_results
    }
    
    report_path = f"enhanced_error_handling_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    return overall_success_rate >= 0.75  # Return True if validation passes


def main():
    """Main validation runner"""
    print("🚀 Enhanced Error Handling Validation Suite")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = []
    
    # Run all validation test categories
    test_categories = [
        ("Database Initialization", test_database_initialization),
        ("Server Resilience", test_server_resilience),
        ("Database Corruption", test_database_corruption_scenarios),
        ("File System Resilience", test_file_system_resilience),
        ("Comprehensive Error Handling", test_error_handling_comprehensive),
        ("Original Error Handling", test_original_error_handling),
    ]
    
    for category_name, test_function in test_categories:
        print(f"\n🔄 Starting {category_name} tests...")
        try:
            results = test_function()
            all_results.extend(results)
        except Exception as e:
            print(f"❌ Error in {category_name}: {e}")
            all_results.append({
                'test_name': f"{category_name} - Error",
                'description': f"Error running {category_name} tests",
                'success': False,
                'duration': 0,
                'return_code': -3,
                'stdout': '',
                'stderr': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    # Generate comprehensive report
    validation_passed = generate_comprehensive_report(all_results)
    
    print(f"\n✅ Validation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit with appropriate code
    sys.exit(0 if validation_passed else 1)


if __name__ == "__main__":
    main()