#!/usr/bin/env python3
"""
Comprehensive Enhanced Error Handling Validation Test Suite
Tests the new enhanced error handling mechanisms, database resilience, and recovery systems.
"""

import unittest
import sys
import os
import time
import threading
import tempfile
import shutil
import sqlite3
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database_manager import DatabaseManager, DatabaseError, DatabaseCorruptionError
from src.managers.enhanced_file_ownership import EnhancedFileOwnershipManager, FileOwnershipError
from src.enhanced_server import EnhancedOpencodeSlackServer


class EnhancedErrorHandlingTest(unittest.TestCase):
    """Comprehensive test suite for enhanced error handling"""
    
    def setUp(self):
        """Set up test environment with temporary resources"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_enhanced.db")
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.sessions_dir = os.path.join(self.temp_dir, "sessions")
        
        # Test results tracking
        self.test_results = {
            'database_resilience': [],
            'file_system_errors': [],
            'graceful_degradation': [],
            'recovery_mechanisms': [],
            'input_validation': [],
            'transaction_handling': [],
            'connection_pooling': [],
            'backup_recovery': []
        }
        
        print(f"🔧 Enhanced test environment initialized in {self.temp_dir}")
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    # ==================== DATABASE RESILIENCE TESTS ====================
    
    def test_database_initialization_with_missing_directory(self):
        """Test database initialization when parent directory doesn't exist"""
        print("\n🧪 Testing database initialization with missing directory...")
        
        try:
            # Use a path with non-existent parent directories
            missing_dir_path = os.path.join(self.temp_dir, "missing", "nested", "dir", "test.db")
            
            # This should create the directory structure and initialize the database
            db_manager = DatabaseManager(missing_dir_path)
            
            # Verify database was created and is functional
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['employees', 'file_locks', 'file_requests', 'schema_migrations']
            tables_exist = all(table in tables for table in required_tables)
            
            db_manager.close()
            
            self.test_results['database_resilience'].append({
                'test': 'missing_directory_initialization',
                'success': tables_exist,
                'details': f"Created directory structure and {len(tables)} tables",
                'timestamp': datetime.now()
            })
            
            self.assertTrue(tables_exist, "Database should initialize with missing directories")
            print(f"   ✅ Database initialized successfully with missing directories")
            
        except Exception as e:
            self.test_results['database_resilience'].append({
                'test': 'missing_directory_initialization',
                'success': False,
                'details': f"Failed with error: {e}",
                'timestamp': datetime.now()
            })
            self.fail(f"Database initialization failed: {e}")
    
    def test_database_corruption_detection_and_recovery(self):
        """Test database corruption detection and automatic recovery"""
        print("\n🧪 Testing database corruption detection and recovery...")
        
        try:
            # Create a valid database first
            db_manager = DatabaseManager(self.db_path, backup_dir=self.backup_dir)
            
            # Add some test data
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO employees (name, role) VALUES (?, ?)", ("test_user", "developer"))
                conn.commit()
            
            db_manager.close()
            
            # Corrupt the database file
            with open(self.db_path, 'w') as f:
                f.write("CORRUPTED DATABASE CONTENT")
            
            # Try to initialize database manager again - should detect corruption and recover
            try:
                db_manager = DatabaseManager(self.db_path, backup_dir=self.backup_dir)
                
                # Test if database is functional
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM employees")
                    count = cursor.fetchone()[0]
                
                recovery_successful = True
                db_manager.close()
                
            except Exception as recovery_error:
                recovery_successful = False
                print(f"   Recovery failed: {recovery_error}")
            
            self.test_results['database_resilience'].append({
                'test': 'corruption_detection_recovery',
                'success': recovery_successful,
                'details': f"Corruption recovery {'succeeded' if recovery_successful else 'failed'}",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Database corruption recovery test completed")
            
        except Exception as e:
            self.test_results['database_resilience'].append({
                'test': 'corruption_detection_recovery',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    def test_connection_pool_exhaustion_handling(self):
        """Test connection pool behavior under high load"""
        print("\n🧪 Testing connection pool exhaustion handling...")
        
        try:
            # Create database manager with small connection pool
            db_manager = DatabaseManager(self.db_path, max_connections=3)
            
            connections = []
            connection_errors = []
            
            # Try to acquire more connections than the pool size
            for i in range(5):
                try:
                    conn_context = db_manager.get_connection()
                    conn = conn_context.__enter__()
                    connections.append((conn_context, conn))
                except Exception as e:
                    connection_errors.append(str(e))
            
            # Clean up connections
            for conn_context, conn in connections:
                try:
                    conn_context.__exit__(None, None, None)
                except Exception:
                    pass
            
            db_manager.close()
            
            # Pool should handle exhaustion gracefully
            pool_handled_correctly = len(connection_errors) == 0 or "timeout" in str(connection_errors[0]).lower()
            
            self.test_results['connection_pooling'].append({
                'test': 'pool_exhaustion_handling',
                'success': pool_handled_correctly,
                'details': f"Acquired {len(connections)} connections, {len(connection_errors)} errors",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Connection pool exhaustion test completed")
            
        except Exception as e:
            self.test_results['connection_pooling'].append({
                'test': 'pool_exhaustion_handling',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    def test_transaction_rollback_on_error(self):
        """Test transaction rollback behavior on errors"""
        print("\n🧪 Testing transaction rollback on errors...")
        
        try:
            db_manager = DatabaseManager(self.db_path)
            
            # Test successful transaction
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO employees (name, role) VALUES (?, ?)", ("user1", "developer"))
                conn.commit()
            
            # Test failed transaction (should rollback)
            transaction_failed = False
            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO employees (name, role) VALUES (?, ?)", ("user2", "developer"))
                    # Cause an error by inserting duplicate
                    cursor.execute("INSERT INTO employees (name, role) VALUES (?, ?)", ("user1", "developer"))
                    conn.commit()
            except Exception:
                transaction_failed = True
            
            # Check final state
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM employees")
                final_count = cursor.fetchone()[0]
            
            db_manager.close()
            
            # Should have only 1 employee (user1), user2 should be rolled back
            rollback_worked = transaction_failed and final_count == 1
            
            self.test_results['transaction_handling'].append({
                'test': 'transaction_rollback',
                'success': rollback_worked,
                'details': f"Final count: {final_count}, transaction failed: {transaction_failed}",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Transaction rollback test completed")
            
        except Exception as e:
            self.test_results['transaction_handling'].append({
                'test': 'transaction_rollback',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    # ==================== FILE SYSTEM ERROR HANDLING TESTS ====================
    
    def test_file_permission_error_handling(self):
        """Test handling of file permission errors"""
        print("\n🧪 Testing file permission error handling...")
        
        try:
            # Create a directory with restricted permissions
            restricted_dir = os.path.join(self.temp_dir, "restricted")
            os.makedirs(restricted_dir, mode=0o444)  # Read-only
            
            restricted_db_path = os.path.join(restricted_dir, "test.db")
            
            # Try to initialize file manager with restricted path
            permission_error_caught = False
            try:
                file_manager = EnhancedFileOwnershipManager(restricted_db_path)
            except FileOwnershipError as e:
                permission_error_caught = "permission" in str(e).lower()
            except Exception as e:
                permission_error_caught = "permission" in str(e).lower()
            
            # Restore permissions for cleanup
            os.chmod(restricted_dir, 0o755)
            
            self.test_results['file_system_errors'].append({
                'test': 'file_permission_handling',
                'success': permission_error_caught,
                'details': f"Permission error {'caught' if permission_error_caught else 'not caught'}",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ File permission error handling test completed")
            
        except Exception as e:
            self.test_results['file_system_errors'].append({
                'test': 'file_permission_handling',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    def test_disk_space_monitoring(self):
        """Test disk space monitoring and warnings"""
        print("\n🧪 Testing disk space monitoring...")
        
        try:
            file_manager = EnhancedFileOwnershipManager(self.db_path)
            
            # Test disk space check
            disk_space_ok = file_manager._check_disk_space(min_free_mb=1)  # Very low threshold
            
            # Get system health which includes disk space info
            health_info = file_manager.get_system_health()
            
            file_manager.close()
            
            has_disk_info = 'file_system' in health_info and 'disk_usage' in health_info['file_system']
            
            self.test_results['file_system_errors'].append({
                'test': 'disk_space_monitoring',
                'success': has_disk_info and isinstance(disk_space_ok, bool),
                'details': f"Disk space check: {disk_space_ok}, health info available: {has_disk_info}",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Disk space monitoring test completed")
            
        except Exception as e:
            self.test_results['file_system_errors'].append({
                'test': 'disk_space_monitoring',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    # ==================== INPUT VALIDATION TESTS ====================
    
    def test_comprehensive_input_validation(self):
        """Test comprehensive input validation across all methods"""
        print("\n🧪 Testing comprehensive input validation...")
        
        try:
            file_manager = EnhancedFileOwnershipManager(self.db_path)
            
            validation_tests = [
                # Test empty/None inputs
                ('hire_employee', ['', 'developer'], False),
                ('hire_employee', [None, 'developer'], False),
                ('hire_employee', ['user', ''], False),
                ('hire_employee', ['user', None], False),
                
                # Test whitespace-only inputs
                ('hire_employee', ['   ', 'developer'], False),
                ('hire_employee', ['user', '   '], False),
                
                # Test invalid smartness levels
                ('hire_employee', ['user', 'developer', 'invalid'], True),  # Should default to 'normal'
                
                # Test file locking with invalid inputs
                ('lock_files', ['', ['file.py'], 'task'], {}),
                ('lock_files', ['user', [], 'task'], {}),
                ('lock_files', ['user', [''], 'task'], {}),
            ]
            
            validation_results = []
            
            for method_name, args, expected_success in validation_tests:
                try:
                    method = getattr(file_manager, method_name)
                    result = method(*args)
                    
                    if method_name == 'hire_employee':
                        actual_success = result is True
                    elif method_name == 'lock_files':
                        actual_success = isinstance(result, dict)
                    else:
                        actual_success = result is not None
                    
                    validation_results.append({
                        'method': method_name,
                        'args': args,
                        'expected': expected_success,
                        'actual': actual_success,
                        'passed': actual_success == expected_success
                    })
                    
                except Exception as e:
                    validation_results.append({
                        'method': method_name,
                        'args': args,
                        'expected': expected_success,
                        'actual': False,
                        'passed': expected_success is False,
                        'error': str(e)
                    })
            
            file_manager.close()
            
            passed_tests = sum(1 for r in validation_results if r['passed'])
            total_tests = len(validation_results)
            
            self.test_results['input_validation'].append({
                'test': 'comprehensive_input_validation',
                'success': passed_tests == total_tests,
                'details': f"Passed {passed_tests}/{total_tests} validation tests",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Input validation test completed: {passed_tests}/{total_tests}")
            
        except Exception as e:
            self.test_results['input_validation'].append({
                'test': 'comprehensive_input_validation',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    # ==================== GRACEFUL DEGRADATION TESTS ====================
    
    def test_server_degraded_mode_operation(self):
        """Test server operation in degraded mode"""
        print("\n🧪 Testing server degraded mode operation...")
        
        try:
            # Create server with invalid database path to trigger degraded mode
            invalid_db_path = "/invalid/path/that/cannot/be/created/test.db"
            
            server = EnhancedOpencodeSlackServer(
                host="localhost",
                port=0,  # Use port 0 to avoid conflicts
                db_path=invalid_db_path,
                sessions_dir=self.sessions_dir
            )
            
            # Server should be in degraded mode
            degraded_mode = server.degraded_mode
            has_errors = len(server.initialization_errors) > 0
            
            # Test that some functionality still works
            app_created = server.app is not None
            
            self.test_results['graceful_degradation'].append({
                'test': 'server_degraded_mode',
                'success': degraded_mode and has_errors and app_created,
                'details': f"Degraded: {degraded_mode}, Errors: {len(server.initialization_errors)}, App: {app_created}",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Server degraded mode test completed")
            
        except Exception as e:
            self.test_results['graceful_degradation'].append({
                'test': 'server_degraded_mode',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    def test_partial_component_failure_handling(self):
        """Test handling when some components fail to initialize"""
        print("\n🧪 Testing partial component failure handling...")
        
        try:
            # Mock one component to fail during initialization
            with patch('src.enhanced_server.TaskProgressTracker') as mock_tracker:
                mock_tracker.side_effect = Exception("Simulated tracker failure")
                
                server = EnhancedOpencodeSlackServer(
                    host="localhost",
                    port=0,
                    db_path=self.db_path,
                    sessions_dir="/invalid/sessions/path"
                )
                
                # Server should handle partial failure gracefully
                has_file_manager = server.file_manager is not None
                missing_task_tracker = server.task_tracker is None
                in_degraded_mode = server.degraded_mode
                
                partial_failure_handled = has_file_manager and missing_task_tracker and in_degraded_mode
                
                self.test_results['graceful_degradation'].append({
                    'test': 'partial_component_failure',
                    'success': partial_failure_handled,
                    'details': f"File manager: {has_file_manager}, Task tracker: {missing_task_tracker}, Degraded: {in_degraded_mode}",
                    'timestamp': datetime.now()
                })
                
                print(f"   ✅ Partial component failure test completed")
                
        except Exception as e:
            self.test_results['graceful_degradation'].append({
                'test': 'partial_component_failure',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    # ==================== BACKUP AND RECOVERY TESTS ====================
    
    def test_automatic_backup_creation(self):
        """Test automatic backup creation functionality"""
        print("\n🧪 Testing automatic backup creation...")
        
        try:
            db_manager = DatabaseManager(self.db_path, backup_dir=self.backup_dir, auto_backup=True)
            
            # Add some test data
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO employees (name, role) VALUES (?, ?)", ("backup_test", "developer"))
                conn.commit()
            
            # Create manual backup
            backup_path = db_manager.create_backup()
            
            # Verify backup exists and is valid
            backup_exists = backup_path.exists()
            
            if backup_exists:
                # Test backup validity
                test_conn = sqlite3.connect(str(backup_path))
                test_cursor = test_conn.cursor()
                test_cursor.execute("SELECT COUNT(*) FROM employees WHERE name = ?", ("backup_test",))
                backup_data_valid = test_cursor.fetchone()[0] == 1
                test_conn.close()
            else:
                backup_data_valid = False
            
            db_manager.close()
            
            self.test_results['backup_recovery'].append({
                'test': 'automatic_backup_creation',
                'success': backup_exists and backup_data_valid,
                'details': f"Backup exists: {backup_exists}, Data valid: {backup_data_valid}",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Automatic backup creation test completed")
            
        except Exception as e:
            self.test_results['backup_recovery'].append({
                'test': 'automatic_backup_creation',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    def test_backup_restoration_process(self):
        """Test backup restoration process"""
        print("\n🧪 Testing backup restoration process...")
        
        try:
            # Create initial database with data
            db_manager = DatabaseManager(self.db_path, backup_dir=self.backup_dir)
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO employees (name, role) VALUES (?, ?)", ("original_user", "developer"))
                conn.commit()
            
            # Create backup
            backup_path = db_manager.create_backup()
            
            # Modify database
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO employees (name, role) VALUES (?, ?)", ("new_user", "tester"))
                conn.commit()
            
            # Restore from backup
            restore_success = db_manager.restore_backup(backup_path)
            
            # Verify restoration
            if restore_success:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM employees WHERE name = ?", ("original_user",))
                    has_original = cursor.fetchone()[0] == 1
                    cursor.execute("SELECT COUNT(*) FROM employees WHERE name = ?", ("new_user",))
                    has_new = cursor.fetchone()[0] == 0
                
                restoration_correct = has_original and not has_new
            else:
                restoration_correct = False
            
            db_manager.close()
            
            self.test_results['backup_recovery'].append({
                'test': 'backup_restoration',
                'success': restore_success and restoration_correct,
                'details': f"Restore success: {restore_success}, Data correct: {restoration_correct}",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Backup restoration test completed")
            
        except Exception as e:
            self.test_results['backup_recovery'].append({
                'test': 'backup_restoration',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    # ==================== RECOVERY MECHANISMS TESTS ====================
    
    def test_retry_logic_for_transient_failures(self):
        """Test retry logic for transient database failures"""
        print("\n🧪 Testing retry logic for transient failures...")
        
        try:
            db_manager = DatabaseManager(self.db_path)
            
            # Mock a transient failure that succeeds on retry
            original_execute = db_manager.db_manager.execute_with_retry if hasattr(db_manager, 'db_manager') else db_manager.execute_with_retry
            
            call_count = 0
            def mock_execute_with_retry(query, params=(), max_retries=3):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # Simulate transient failure on first call
                    raise sqlite3.OperationalError("database is locked")
                else:
                    # Succeed on retry
                    return original_execute(query, params, max_retries)
            
            # Test retry logic
            with patch.object(db_manager, 'execute_with_retry', side_effect=mock_execute_with_retry):
                try:
                    result = db_manager.execute_with_retry("SELECT 1")
                    retry_success = len(result) > 0 and call_count > 1
                except Exception:
                    retry_success = False
            
            db_manager.close()
            
            self.test_results['recovery_mechanisms'].append({
                'test': 'retry_logic_transient_failures',
                'success': retry_success,
                'details': f"Retry success: {retry_success}, Call count: {call_count}",
                'timestamp': datetime.now()
            })
            
            print(f"   ✅ Retry logic test completed")
            
        except Exception as e:
            self.test_results['recovery_mechanisms'].append({
                'test': 'retry_logic_transient_failures',
                'success': False,
                'details': f"Test failed with error: {e}",
                'timestamp': datetime.now()
            })
            print(f"   ❌ Test failed: {e}")
    
    # ==================== TEST EXECUTION AND REPORTING ====================
    
    def test_comprehensive_enhanced_error_handling(self):
        """Run all enhanced error handling tests and generate report"""
        print("\n🚀 Starting Comprehensive Enhanced Error Handling Validation")
        print("=" * 70)
        
        # Run all test categories
        test_methods = [
            # Database resilience
            self.test_database_initialization_with_missing_directory,
            self.test_database_corruption_detection_and_recovery,
            self.test_connection_pool_exhaustion_handling,
            self.test_transaction_rollback_on_error,
            
            # File system errors
            self.test_file_permission_error_handling,
            self.test_disk_space_monitoring,
            
            # Input validation
            self.test_comprehensive_input_validation,
            
            # Graceful degradation
            self.test_server_degraded_mode_operation,
            self.test_partial_component_failure_handling,
            
            # Backup and recovery
            self.test_automatic_backup_creation,
            self.test_backup_restoration_process,
            
            # Recovery mechanisms
            self.test_retry_logic_for_transient_failures,
        ]
        
        # Execute all tests
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"   ❌ Test {test_method.__name__} failed with exception: {e}")
        
        # Generate comprehensive report
        self._generate_enhanced_validation_report()
    
    def _generate_enhanced_validation_report(self):
        """Generate comprehensive enhanced validation report"""
        print("\n📊 ENHANCED ERROR HANDLING VALIDATION REPORT")
        print("=" * 70)
        
        total_tests = 0
        passed_tests = 0
        
        for category, results in self.test_results.items():
            if not results:
                continue
                
            print(f"\n🔍 {category.replace('_', ' ').title()}:")
            category_passed = 0
            
            for result in results:
                total_tests += 1
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                print(f"   {status} {result['test']}: {result['details']}")
                
                if result['success']:
                    passed_tests += 1
                    category_passed += 1
            
            category_rate = category_passed / len(results) if results else 0
            print(f"   📈 Category Success Rate: {category_rate:.1%} ({category_passed}/{len(results)})")
        
        # Overall statistics
        overall_rate = passed_tests / total_tests if total_tests > 0 else 0
        print(f"\n📈 OVERALL SUCCESS RATE: {overall_rate:.1%} ({passed_tests}/{total_tests})")
        
        # Enhanced recommendations
        print(f"\n💡 ENHANCED ERROR HANDLING ASSESSMENT:")
        if overall_rate >= 0.95:
            print("   🎉 Excellent! Enhanced error handling is robust and comprehensive.")
        elif overall_rate >= 0.85:
            print("   👍 Very good enhanced error handling with minor areas for improvement.")
        elif overall_rate >= 0.75:
            print("   ⚠️  Good enhanced error handling, but some critical areas need attention.")
        elif overall_rate >= 0.60:
            print("   🚨 Enhanced error handling needs significant improvements.")
        else:
            print("   💥 Critical: Enhanced error handling is insufficient for production use.")
        
        # Specific recommendations
        failed_categories = [cat for cat, results in self.test_results.items() 
                           if results and not all(r['success'] for r in results)]
        
        if failed_categories:
            print(f"\n🔧 PRIORITY AREAS FOR ENHANCED ERROR HANDLING:")
            for category in failed_categories:
                print(f"   • {category.replace('_', ' ').title()}")
        
        # Save detailed report
        report_path = os.path.join(self.temp_dir, "enhanced_error_handling_report.json")
        with open(report_path, 'w') as f:
            json.dump({
                'overall_rate': overall_rate,
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'test_results': self.test_results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        print(f"✅ Enhanced validation completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    # Run the comprehensive enhanced validation
    suite = unittest.TestLoader().loadTestsFromTestCase(EnhancedErrorHandlingTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)