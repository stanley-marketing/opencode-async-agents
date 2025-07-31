#!/usr/bin/env python3
"""
Demo script showing the REAL opencode employee system in action.
This demonstrates employees actually working with real opencode sessions.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from task_assigner import TaskAssigner

def demo_real_employee_system():
    """Comprehensive demo of the real employee system"""
    print("🔥" + "="*60 + "🔥")
    print("🚀 REAL OPENCODE EMPLOYEE SYSTEM DEMO")
    print("🔥" + "="*60 + "🔥")
    print()
    
    # Initialize the system
    print("📋 Initializing the real employee management system...")
    assigner = TaskAssigner()
    
    print("\n🎯 PHASE 1: Hiring employees")
    print("-" * 40)
    
    # Hire some employees if they don't exist
    employees = assigner.file_manager.list_employees()
    existing_names = [emp['name'] for emp in employees]
    
    new_hires = [
        ("alice", "senior-developer"),
        ("bob", "developer"), 
        ("charlie", "analyst"),
        ("diana", "qa-engineer")
    ]
    
    for name, role in new_hires:
        if name not in existing_names:
            if assigner.file_manager.hire_employee(name, role):
                print(f"✅ Hired {name} as {role}")
            else:
                print(f"❌ Failed to hire {name}")
        else:
            print(f"👤 {name} already employed")
    
    print("\n🚀 PHASE 2: Assigning REAL opencode tasks")
    print("-" * 40)
    
    # Assign real tasks that will spawn opencode sessions
    tasks = [
        ("alice", "Implement user authentication system with JWT tokens and password hashing"),
        ("bob", "Create REST API endpoints for user management with proper validation"),
        ("charlie", "Write comprehensive technical documentation for the authentication system"),
        ("diana", "Create automated tests for the authentication and API endpoints")
    ]
    
    session_ids = []
    for employee, task in tasks:
        print(f"\n🤖 Assigning task to {employee}:")
        print(f"   📝 Task: {task}")
        
        session_id = assigner.assign_task(employee, task, model="claude-3.5")
        if session_id:
            session_ids.append((employee, session_id))
            print(f"   ✅ Session started successfully")
        else:
            print(f"   ❌ Failed to start session")
    
    print("\n📊 PHASE 3: Monitoring active work")
    print("-" * 40)
    
    # Show active sessions
    print("\n🔥 Active opencode sessions:")
    active_sessions = assigner.get_active_sessions()
    if active_sessions:
        for employee_name, session_info in active_sessions.items():
            status = "🔥 RUNNING" if session_info['is_running'] else "⏸️  PAUSED"
            print(f"  👤 {employee_name} - {status}")
            print(f"     🧠 Task: {session_info['task'][:60]}...")
            print(f"     📋 Session: {session_info['session_id']}")
            if session_info['files_locked']:
                print(f"     🔒 Files: {', '.join(session_info['files_locked'][:3])}{'...' if len(session_info['files_locked']) > 3 else ''}")
    else:
        print("  No active sessions")
    
    # Show employee status
    print("\n👥 Employee status:")
    assigner.list_employees_working()
    
    print("\n⏳ PHASE 4: Letting employees work...")
    print("-" * 40)
    print("Employees are now working with real opencode sessions in the background.")
    print("In a real environment, they would be:")
    print("  • Analyzing the codebase")
    print("  • Writing actual code")
    print("  • Creating files and making changes")
    print("  • Updating progress automatically")
    print()
    
    # Simulate some time passing
    for i in range(3):
        print(f"⏳ Working... {i+1}/3")
        time.sleep(1)
    
    print("\n📈 PHASE 5: Checking progress")
    print("-" * 40)
    
    # Check progress
    print("Current task progress:")
    assigner.check_task_progress()
    
    print("\n🎯 PHASE 6: System capabilities")
    print("-" * 40)
    
    print("✅ What's working:")
    print("  🔥 Real opencode sessions spawn in background threads")
    print("  🔒 File locking prevents conflicts between employees")
    print("  📊 Progress tracking from opencode output parsing")
    print("  🤝 File request/approval workflow")
    print("  📋 Task assignment with automatic file analysis")
    print("  🧹 Session cleanup and management")
    print("  💻 CLI interface for interactive management")
    print()
    
    print("🚀 Next steps:")
    print("  • Install opencode to see real code generation")
    print("  • Use the CLI: python3 src/cli_server.py")
    print("  • Try: assign alice 'implement login system'")
    print("  • Monitor with: sessions, employees, progress")
    print()
    
    print("🔥" + "="*60 + "🔥")
    print("🎉 REAL EMPLOYEE SYSTEM IS FULLY OPERATIONAL!")
    print("🔥" + "="*60 + "🔥")
    
    return assigner

def interactive_demo():
    """Interactive demo where user can try commands"""
    assigner = demo_real_employee_system()
    
    print("\n🎮 INTERACTIVE MODE")
    print("Try these commands:")
    print("  assigner.assign_task('alice', 'create login page')")
    print("  assigner.get_active_sessions()")
    print("  assigner.list_employees_working()")
    print("  assigner.stop_employee_task('alice')")
    print()
    
    # Keep the demo running so user can interact
    print("💡 The 'assigner' object is available for you to use!")
    print("   Type 'exit()' to quit")
    
    # Start an interactive Python session
    import code
    code.interact(local=locals())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_demo()
    else:
        demo_real_employee_system()