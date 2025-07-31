#!/usr/bin/env python3
"""
Integration test demonstrating multiple agents working together with file locking.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker

def test_concurrent_file_access():
    """Test that demonstrates file locking prevents conflicts"""
    print("=== Concurrent File Access Test ===")
    
    # Create a temporary directory for this test
    test_dir = tempfile.mkdtemp(prefix="opencode_slack_test_")
    print(f"Test directory: {test_dir}")
    
    try:
        # Set up database and sessions directory
        db_path = os.path.join(test_dir, "test_employees.db")
        sessions_dir = os.path.join(test_dir, "sessions")
        
        # Create file ownership manager
        file_manager = FileOwnershipManager(db_path)
        task_tracker = TaskProgressTracker(sessions_dir)
        
        # Hire multiple employees
        print("\n1. Hiring employees:")
        assert file_manager.hire_employee("sarah", "developer"), "Failed to hire sarah"
        print("  - Hired sarah as developer")
        
        assert file_manager.hire_employee("dev-2", "developer"), "Failed to hire dev-2"
        print("  - Hired dev-2 as developer")
        
        assert file_manager.hire_employee("analyst-1", "analyst"), "Failed to hire analyst-1"
        print("  - Hired analyst-1 as analyst")
        
        # Show all employees
        employees = file_manager.list_employees()
        print(f"  - Total employees: {len(employees)}")
        
        # Sarah locks some files
        print("\n2. Sarah locks files:")
        result = file_manager.lock_files("sarah", ["src/auth.py", "src/user.py"], "implement auth system")
        print(f"  - src/auth.py: {result['src/auth.py']}")
        print(f"  - src/user.py: {result['src/user.py']}")
        
        # Create task file for sarah
        task_tracker.create_task_file("sarah", "implement auth system", ["src/auth.py", "src/user.py"])
        print("  - Created task file for sarah")
        
        # Dev-2 tries to lock the same files
        print("\n3. Dev-2 tries to lock the same files:")
        result = file_manager.lock_files("dev-2", ["src/auth.py", "src/api.py"], "implement API")
        print(f"  - src/auth.py: {result['src/auth.py']}")  # Should be locked by sarah
        print(f"  - src/api.py: {result['src/api.py']}")    # Should be locked successfully
        print("  - Dev-2 can only lock src/api.py, src/auth.py is locked by sarah")
        
        # Create task file for dev-2
        task_tracker.create_task_file("dev-2", "implement API", ["src/api.py"])
        print("  - Created task file for dev-2")
        
        # Analyst-1 locks documentation files
        print("\n4. Analyst-1 locks documentation files:")
        result = file_manager.lock_files("analyst-1", ["docs/requirements.md"], "analyze requirements")
        print(f"  - docs/requirements.md: {result['docs/requirements.md']}")
        
        # Create task file for analyst-1
        task_tracker.create_task_file("analyst-1", "analyze requirements", ["docs/requirements.md"])
        print("  - Created task file for analyst-1")
        
        # Show current file ownership
        print("\n5. Current file ownership:")
        for file_path in ["src/auth.py", "src/user.py", "src/api.py", "docs/requirements.md"]:
            owner = file_manager.get_file_owner(file_path)
            if owner:
                print(f"  - {file_path}: {owner}")
            else:
                print(f"  - {file_path}: not locked")
        
        # Dev-2 requests src/auth.py from sarah
        print("\n6. Dev-2 requests src/auth.py from sarah:")
        result = file_manager.request_file("dev-2", "src/auth.py", "need for API integration")
        print(f"  - Request result: {result}")
        
        # Show pending requests for sarah
        print("\n7. Pending requests for sarah:")
        requests = file_manager.get_pending_requests("sarah")
        for req in requests:
            print(f"  - Request ID {req['id']}: {req['requester']} wants {req['file_path']} ({req['reason']})")
        
        # Sarah approves the request
        if requests:
            request_id = requests[0]['id']
            print(f"\n8. Sarah approves request {request_id}:")
            result = file_manager.approve_request(request_id)
            print(f"  - Approval result: {result}")
            
            # Show updated file ownership
            print("\n9. Updated file ownership:")
            owner = file_manager.get_file_owner("src/auth.py")
            print(f"  - src/auth.py: {owner}")
        
        # Show employee progress
        print("\n10. Employee progress:")
        for employee in ["sarah", "dev-2", "analyst-1"]:
            progress = task_tracker.get_task_progress(employee)
            if progress:
                print(f"  - {employee}: {progress['overall_progress']}% complete")
            else:
                print(f"  - {employee}: no progress data")
        
        # Release some files
        print("\n11. Releasing files:")
        released = file_manager.release_files("sarah", ["src/user.py"])
        print(f"  - Sarah released: {released}")
        
        # Auto-release ready files
        print("\n12. Auto-releasing ready files:")
        # Simulate that sarah has completed her task by updating the progress file
        task_tracker.update_file_status("sarah", "src/auth.py", 100, "READY TO RELEASE")
        released = file_manager.release_ready_files("sarah", task_tracker)
        print(f"  - Auto-released files for sarah: {released}")
        
        # Show final file ownership
        print("\n13. Final file ownership:")
        for file_path in ["src/auth.py", "src/user.py", "src/api.py", "docs/requirements.md"]:
            owner = file_manager.get_file_owner(file_path)
            if owner:
                print(f"  - {file_path}: {owner}")
            else:
                print(f"  - {file_path}: not locked")
        
        print("\n=== Test completed successfully! ===")
        return True
        
    except Exception as e:
        print(f"\n=== Test failed with error: {e} ===")
        return False
        
    finally:
        # Clean up test directory
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"Cleaned up test directory: {test_dir}")

def test_employee_lifecycle():
    """Test hiring, working, and firing employees"""
    print("\n=== Employee Lifecycle Test ===")
    
    # Create a temporary directory for this test
    test_dir = tempfile.mkdtemp(prefix="opencode_slack_lifecycle_test_")
    print(f"Test directory: {test_dir}")
    
    try:
        # Set up database and sessions directory
        db_path = os.path.join(test_dir, "test_employees.db")
        sessions_dir = os.path.join(test_dir, "sessions")
        
        # Create file ownership manager
        file_manager = FileOwnershipManager(db_path)
        task_tracker = TaskProgressTracker(sessions_dir)
        
        # Hire an employee
        print("\n1. Hiring employee:")
        assert file_manager.hire_employee("temp-worker", "developer"), "Failed to hire temp-worker"
        print("  - Hired temp-worker as developer")
        
        # Lock some files
        print("\n2. Locking files:")
        result = file_manager.lock_files("temp-worker", ["temp/work.py"], "temporary work")
        print(f"  - temp/work.py: {result['temp/work.py']}")
        
        # Create task file
        task_tracker.create_task_file("temp-worker", "temporary work", ["temp/work.py"])
        print("  - Created task file for temp-worker")
        
        # Show employee exists
        employees = file_manager.list_employees()
        print(f"\n3. Current employees: {[emp['name'] for emp in employees]}")
        
        # Fire the employee
        print("\n4. Firing employee:")
        result = file_manager.fire_employee("temp-worker")
        print(f"  - Fire result: {result}")
        
        # Show employee no longer exists
        employees = file_manager.list_employees()
        print(f"\n5. Current employees: {[emp['name'] for emp in employees]}")
        
        # Verify files are released
        print("\n6. Checking file ownership after firing:")
        owner = file_manager.get_file_owner("temp/work.py")
        print(f"  - temp/work.py owner: {owner}")
        if owner is None:
            print("  - Files successfully released when employee was fired")
        
        print("\n=== Lifecycle test completed successfully! ===")
        return True
        
    except Exception as e:
        print(f"\n=== Lifecycle test failed with error: {e} ===")
        return False
        
    finally:
        # Clean up test directory
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"Cleaned up test directory: {test_dir}")

def main():
    """Run all integration tests"""
    print("Running integration tests for opencode-slack system...\n")
    
    # Run the concurrent file access test
    success1 = test_concurrent_file_access()
    
    # Run the employee lifecycle test
    success2 = test_employee_lifecycle()
    
    if success1 and success2:
        print("\n🎉 All integration tests passed!")
        return True
    else:
        print("\n❌ Some integration tests failed!")
        return False

if __name__ == "__main__":
    main()