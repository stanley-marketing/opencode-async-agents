#!/usr/bin/env python3
"""
Interactive task assignment script.
Simply tell employees what to do and they'll handle the rest!
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from task_assigner import TaskAssigner

def interactive_task_assignment():
    """Interactive task assignment system"""
    print("=== AI Employee Task Assignment System ===")
    print("Simply tell your AI employees what to do!\n")
    
    assigner = TaskAssigner()
    
    # Hire some employees to start with
    print("Hiring initial employees...")
    assigner.file_manager.hire_employee("sarah", "senior-developer")
    assigner.file_manager.hire_employee("dev-2", "developer")
    assigner.file_manager.hire_employee("analyst-1", "analyst")
    print("✅ Hired sarah (senior-developer), dev-2 (developer), analyst-1 (analyst)\n")
    
    while True:
        try:
            print("\nOptions:")
            print("1. Assign task to employee")
            print("2. List employees and their work")
            print("3. Check task progress")
            print("4. Mark task as complete")
            print("5. Hire new employee")
            print("6. Exit")
            
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == "1":
                print("\nAssign a task:")
                employee = input("Employee name: ").strip()
                task = input("Task description: ").strip()
                if employee and task:
                    assigner.assign_task(employee, task)
                else:
                    print("❌ Please provide both employee name and task description")
            
            elif choice == "2":
                print()
                assigner.list_employees_working()
            
            elif choice == "3":
                employee = input("Employee name (or press Enter for all): ").strip()
                print()
                if employee:
                    assigner.check_task_progress(employee)
                else:
                    assigner.check_task_progress()
            
            elif choice == "4":
                print("\nMark task as complete:")
                employee = input("Employee name: ").strip()
                file_path = input("File path: ").strip()
                if employee and file_path:
                    assigner.complete_task(employee, file_path)
                else:
                    print("❌ Please provide employee name and file path")
            
            elif choice == "5":
                print("\nHire new employee:")
                name = input("Employee name: ").strip()
                role = input("Role: ").strip()
                if name and role:
                    if assigner.file_manager.hire_employee(name, role):
                        print(f"✅ Hired {name} as {role}")
                    else:
                        print(f"❌ Failed to hire {name}")
                else:
                    print("❌ Please provide name and role")
            
            elif choice == "6":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid option. Please select 1-6")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def quick_demo():
    """Quick demo of the task assignment system"""
    print("=== Quick Demo ===")
    assigner = TaskAssigner()
    
    # Hire employees
    assigner.file_manager.hire_employee("sarah", "developer")
    assigner.file_manager.hire_employee("dev-2", "developer")
    
    print("\n1. Assigning task to sarah:")
    assigner.assign_task("sarah", "Implement user authentication system")
    
    print("2. Assigning task to dev-2:")
    assigner.assign_task("dev-2", "Create API endpoints for user management")
    
    print("3. Checking what employees are working on:")
    assigner.list_employees_working()
    
    print("\n✅ Demo complete! You can now run the interactive version:")
    print("   python3 assign_tasks.py")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        quick_demo()
    else:
        interactive_task_assignment()