#!/usr/bin/env python3
"""
Validation script to ensure project cleanup was successful and all functionality is preserved.
"""

import os
import sys
import importlib.util

def check_file_exists(path, description):
    """Check if a file exists and report status."""
    if os.path.exists(path):
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} - NOT FOUND")
        return False

def check_directory_exists(path, description):
    """Check if a directory exists and report status."""
    if os.path.isdir(path):
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} - NOT FOUND")
        return False

def check_import(module_name, description):
    """Check if a module can be imported."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, f"src/{module_name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"✅ {description}: {module_name}")
        return True
    except Exception as e:
        print(f"❌ {description}: {module_name} - ERROR: {e}")
        return False

def main():
    """Run validation checks."""
    print("🧹 OpenCode-Slack Project Cleanup Validation")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 0
    
    # Essential files check
    print("\n📁 Essential Files Check:")
    essential_files = [
        ("README.md", "Main documentation"),
        ("LICENSE", "License file"),
        (".env", "Environment configuration"),
        ("employees.db", "Employee database"),
        ("requirements.txt", "Requirements symlink"),
        ("quick_start.sh", "Quick start symlink"),
    ]
    
    for file_path, description in essential_files:
        total_checks += 1
        if check_file_exists(file_path, description):
            checks_passed += 1
    
    # Directory structure check
    print("\n📂 Directory Structure Check:")
    directories = [
        ("src", "Source code"),
        ("config", "Configuration files"),
        ("docs", "Documentation"),
        ("tests", "Test suites"),
        ("scripts", "Scripts"),
        ("archive", "Archived files"),
        ("frontend", "Frontend code"),
    ]
    
    for dir_path, description in directories:
        total_checks += 1
        if check_directory_exists(dir_path, description):
            checks_passed += 1
    
    # Configuration organization check
    print("\n⚙️ Configuration Organization Check:")
    config_items = [
        ("config/requirements", "Requirements directory"),
        ("config/deployment", "Deployment configs"),
        ("config/environments", "Environment configs"),
        ("config/requirements/requirements.txt", "Main requirements file"),
    ]
    
    for item_path, description in config_items:
        total_checks += 1
        if os.path.exists(item_path):
            print(f"✅ {description}: {item_path}")
            checks_passed += 1
        else:
            print(f"❌ {description}: {item_path} - NOT FOUND")
    
    # Archive organization check
    print("\n🗂️ Archive Organization Check:")
    archive_items = [
        ("archive/reports", "Archived reports"),
        ("archive/temp-files", "Temporary files"),
        ("archive/old-sessions-full", "Old sessions"),
    ]
    
    for item_path, description in archive_items:
        total_checks += 1
        if check_directory_exists(item_path, description):
            checks_passed += 1
    
    # Core functionality check
    print("\n🔧 Core Functionality Check:")
    
    # Add current directory to Python path for imports
    import sys
    if '.' not in sys.path:
        sys.path.insert(0, '.')
    
    try:
        # Test main imports
        import src.cli_server
        print("✅ Main CLI server imports successfully")
        checks_passed += 1
    except Exception as e:
        print(f"❌ Main CLI server import failed: {e}")
    total_checks += 1
    
    try:
        from src.managers.file_ownership import FileOwnershipManager
        print("✅ File ownership manager imports successfully")
        checks_passed += 1
    except Exception as e:
        print(f"❌ File ownership manager import failed: {e}")
    total_checks += 1
    
    # Root directory cleanliness check
    print("\n🧹 Root Directory Cleanliness Check:")
    root_files = [f for f in os.listdir('.') if os.path.isfile(f)]
    print(f"📊 Root directory files count: {len(root_files)}")
    
    if len(root_files) <= 15:
        print("✅ Root directory is clean (≤15 essential files)")
        checks_passed += 1
    else:
        print("⚠️ Root directory has more than 15 files")
    total_checks += 1
    
    # Final results
    print("\n" + "=" * 50)
    print(f"🎯 Validation Results: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("🎉 ALL CHECKS PASSED! Project cleanup was successful!")
        return 0
    else:
        print("⚠️ Some checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())