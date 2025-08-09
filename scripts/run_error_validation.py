#!/usr/bin/env python3
"""
Comprehensive Error Handling Validation Runner
Executes all error handling and resilience tests
"""

import sys
import os
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_validation_suite():
    """Run the complete error handling validation suite"""
    
    print("🚀 OPENCODE-SLACK ERROR HANDLING VALIDATION")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test suite configuration
    test_suites = [
        {
            'name': 'Core Error Handling Validation',
            'module': 'tests.test_error_handling_validation',
            'description': 'Tests agent recovery, network failures, timeouts, and error reporting'
        },
        {
            'name': 'Chaos Engineering Tests',
            'module': 'tests.test_chaos_engineering', 
            'description': 'Tests system resilience under random failures and resource exhaustion'
        },
        {
            'name': 'Agent Monitoring System',
            'module': 'tests.test_agent_monitoring',
            'description': 'Tests monitoring and recovery system functionality'
        },
        {
            'name': 'Server Integration Tests',
            'module': 'tests.test_server_comprehensive',
            'description': 'Tests server-level error handling and recovery'
        }
    ]
    
    results = []
    total_start_time = time.time()
    
    for i, suite in enumerate(test_suites, 1):
        print(f"📋 Running Test Suite {i}/{len(test_suites)}: {suite['name']}")
        print(f"   {suite['description']}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Run the test suite
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                '-v', '--tb=short',
                f"{suite['module']}"
            ], 
            capture_output=True, 
            text=True,
            cwd=Path(__file__).parent.parent
            )
            
            duration = time.time() - start_time
            
            # Parse results
            success = result.returncode == 0
            output_lines = result.stdout.split('\n') if result.stdout else []
            error_lines = result.stderr.split('\n') if result.stderr else []
            
            # Extract test statistics
            passed = len([line for line in output_lines if 'PASSED' in line])
            failed = len([line for line in output_lines if 'FAILED' in line])
            errors = len([line for line in output_lines if 'ERROR' in line])
            
            suite_result = {
                'name': suite['name'],
                'success': success,
                'duration': duration,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'output': result.stdout,
                'stderr': result.stderr
            }
            
            results.append(suite_result)
            
            # Print summary
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"   {status} - Duration: {duration:.2f}s")
            print(f"   Tests: {passed} passed, {failed} failed, {errors} errors")
            
            if not success and result.stderr:
                print(f"   Errors: {result.stderr[:200]}...")
            
        except Exception as e:
            duration = time.time() - start_time
            suite_result = {
                'name': suite['name'],
                'success': False,
                'duration': duration,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'output': '',
                'stderr': str(e)
            }
            results.append(suite_result)
            print(f"   ❌ EXCEPTION - {e}")
        
        print()
    
    # Generate comprehensive report
    total_duration = time.time() - total_start_time
    generate_final_report(results, total_duration)
    
    # Return overall success
    overall_success = all(r['success'] for r in results)
    return overall_success

def generate_final_report(results, total_duration):
    """Generate final validation report"""
    
    print("📊 FINAL ERROR HANDLING VALIDATION REPORT")
    print("=" * 60)
    
    # Overall statistics
    total_suites = len(results)
    passed_suites = sum(1 for r in results if r['success'])
    total_tests = sum(r['passed'] + r['failed'] + r['errors'] for r in results)
    total_passed = sum(r['passed'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    total_errors = sum(r['errors'] for r in results)
    
    print(f"\n📈 OVERALL STATISTICS:")
    print(f"   Test Suites: {passed_suites}/{total_suites} passed ({passed_suites/total_suites:.1%})")
    print(f"   Individual Tests: {total_passed}/{total_tests} passed ({total_passed/total_tests:.1%})")
    print(f"   Total Duration: {total_duration:.2f} seconds")
    print(f"   Failed Tests: {total_failed}")
    print(f"   Error Tests: {total_errors}")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"   {status} {result['name']}")
        print(f"      Duration: {result['duration']:.2f}s")
        print(f"      Tests: {result['passed']} passed, {result['failed']} failed, {result['errors']} errors")
        
        if not result['success'] and result['stderr']:
            print(f"      Error: {result['stderr'][:100]}...")
    
    # Error handling assessment
    print(f"\n🛡️  ERROR HANDLING ASSESSMENT:")
    
    overall_score = total_passed / total_tests if total_tests > 0 else 0
    
    if overall_score >= 0.95:
        assessment = "🏆 EXCEPTIONAL"
        recommendation = "Outstanding error handling! System demonstrates excellent resilience."
    elif overall_score >= 0.85:
        assessment = "🥇 EXCELLENT" 
        recommendation = "Very strong error handling with minor areas for improvement."
    elif overall_score >= 0.75:
        assessment = "🥈 GOOD"
        recommendation = "Good error handling foundation. Consider strengthening weak areas."
    elif overall_score >= 0.60:
        assessment = "🥉 MODERATE"
        recommendation = "Moderate error handling. Significant improvements recommended."
    else:
        assessment = "🚨 POOR"
        recommendation = "Poor error handling. Immediate attention required for system reliability."
    
    print(f"   Overall Score: {overall_score:.1%}")
    print(f"   Assessment: {assessment}")
    print(f"   Recommendation: {recommendation}")
    
    # Key areas analysis
    print(f"\n🔍 KEY AREAS ANALYSIS:")
    
    failed_suites = [r for r in results if not r['success']]
    if failed_suites:
        print(f"   ⚠️  Areas Needing Attention:")
        for suite in failed_suites:
            print(f"      • {suite['name']}")
    else:
        print(f"   ✅ All test suites passed successfully!")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if total_failed > 0:
        print(f"   🔧 Fix {total_failed} failing tests to improve system reliability")
    
    if total_errors > 0:
        print(f"   🐛 Investigate {total_errors} test errors for potential system issues")
    
    if overall_score < 0.8:
        print(f"   📈 Focus on improving error handling in critical system components")
        print(f"   🔄 Implement additional recovery mechanisms")
        print(f"   📝 Enhance error logging and monitoring")
    
    if overall_score >= 0.9:
        print(f"   🎯 Consider implementing additional chaos engineering tests")
        print(f"   📊 Set up continuous resilience monitoring")
    
    # Save detailed report
    save_detailed_report(results, total_duration, overall_score)
    
    print(f"\n✅ Validation completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def save_detailed_report(results, total_duration, overall_score):
    """Save detailed report to file"""
    
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'total_duration': total_duration,
        'overall_score': overall_score,
        'summary': {
            'total_suites': len(results),
            'passed_suites': sum(1 for r in results if r['success']),
            'total_tests': sum(r['passed'] + r['failed'] + r['errors'] for r in results),
            'total_passed': sum(r['passed'] for r in results),
            'total_failed': sum(r['failed'] for r in results),
            'total_errors': sum(r['errors'] for r in results)
        },
        'detailed_results': results
    }
    
    # Save to reports directory
    reports_dir = Path(__file__).parent.parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    
    report_file = reports_dir / f"error_handling_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        print(f"\n📄 Detailed report saved to: {report_file}")
    except Exception as e:
        print(f"\n⚠️ Could not save detailed report: {e}")

def run_specific_test(test_name):
    """Run a specific test suite"""
    
    test_mapping = {
        'error': 'tests.test_error_handling_validation',
        'chaos': 'tests.test_chaos_engineering',
        'monitoring': 'tests.test_agent_monitoring',
        'server': 'tests.test_server_comprehensive'
    }
    
    if test_name not in test_mapping:
        print(f"❌ Unknown test: {test_name}")
        print(f"Available tests: {', '.join(test_mapping.keys())}")
        return False
    
    module = test_mapping[test_name]
    print(f"🧪 Running specific test: {test_name}")
    print(f"Module: {module}")
    print("-" * 40)
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            '-v', '--tb=long',
            module
        ], cwd=Path(__file__).parent.parent)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

def main():
    """Main function"""
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1].lower()
        success = run_specific_test(test_name)
    else:
        # Run full validation suite
        success = run_validation_suite()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()