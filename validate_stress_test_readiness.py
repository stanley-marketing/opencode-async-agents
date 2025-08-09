#!/usr/bin/env python3
"""
Validate Stress Test Readiness
Checks if the system is ready for comprehensive stress testing
"""

import asyncio
import aiohttp
import sys
import os
import subprocess
from pathlib import Path
import importlib.util

def check_python_packages():
    """Check if required Python packages are installed"""
    required_packages = [
        'aiohttp',
        'psutil', 
        'asyncio',
        'statistics',
        'json',
        'logging',
        'datetime',
        'pathlib',
        'typing',
        'dataclasses',
        'collections'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def check_server_files():
    """Check if server files exist"""
    server_files = [
        'src/server.py',
        'src/async_server.py',
        'src/main.py'
    ]
    
    existing_files = []
    for file_path in server_files:
        if Path(file_path).exists():
            existing_files.append(file_path)
    
    return existing_files

async def check_server_connectivity(url):
    """Check if server is running and responding"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
    except Exception:
        return False

def check_system_resources():
    """Check system resources"""
    try:
        import psutil
        
        # Get system info
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_cores': cpu_count,
            'total_memory_gb': round(memory.total / (1024**3), 2),
            'available_memory_gb': round(memory.available / (1024**3), 2),
            'memory_percent': memory.percent,
            'disk_free_gb': round(disk.free / (1024**3), 2),
            'disk_percent': (disk.used / disk.total) * 100
        }
    except Exception as e:
        return {'error': str(e)}

async def main():
    """Main validation function"""
    print("🔍 OpenCode-Slack Stress Test Readiness Validation")
    print("=" * 60)
    
    validation_passed = True
    
    # Check 1: Python packages
    print("1. Checking Python packages...")
    missing_packages = check_python_packages()
    if missing_packages:
        print(f"   ❌ Missing packages: {', '.join(missing_packages)}")
        print(f"   💡 Install with: pip install {' '.join(missing_packages)}")
        validation_passed = False
    else:
        print("   ✅ All required packages are installed")
    
    # Check 2: Server files
    print("\n2. Checking server files...")
    server_files = check_server_files()
    if not server_files:
        print("   ❌ No server files found")
        validation_passed = False
    else:
        print(f"   ✅ Found server files: {', '.join(server_files)}")
    
    # Check 3: System resources
    print("\n3. Checking system resources...")
    resources = check_system_resources()
    if 'error' in resources:
        print(f"   ❌ Error checking resources: {resources['error']}")
        validation_passed = False
    else:
        print(f"   📊 CPU Cores: {resources['cpu_cores']}")
        print(f"   🧠 Total Memory: {resources['total_memory_gb']} GB")
        print(f"   💾 Available Memory: {resources['available_memory_gb']} GB ({100-resources['memory_percent']:.1f}% free)")
        print(f"   💿 Disk Free: {resources['disk_free_gb']} GB ({100-resources['disk_percent']:.1f}% free)")
        
        # Check if resources are sufficient
        if resources['cpu_cores'] < 2:
            print("   ⚠️  Warning: Less than 2 CPU cores may limit performance")
        if resources['available_memory_gb'] < 2:
            print("   ⚠️  Warning: Less than 2GB available memory may cause issues")
            validation_passed = False
        if resources['disk_free_gb'] < 1:
            print("   ⚠️  Warning: Less than 1GB disk space may cause issues")
        
        if resources['cpu_cores'] >= 2 and resources['available_memory_gb'] >= 2:
            print("   ✅ System resources are sufficient for stress testing")
    
    # Check 4: Server connectivity (optional)
    print("\n4. Checking server connectivity...")
    server_running = await check_server_connectivity("http://localhost:8080")
    if server_running:
        print("   ✅ Server is running and responding at http://localhost:8080")
    else:
        print("   ℹ️  Server is not running (this is OK - it will be started during testing)")
    
    # Check 5: Test files
    print("\n5. Checking test files...")
    test_files = [
        'run_comprehensive_stress_test.py',
        'comprehensive_stress_test_suite.py'
    ]
    
    missing_test_files = []
    for test_file in test_files:
        if not Path(test_file).exists():
            missing_test_files.append(test_file)
    
    if missing_test_files:
        print(f"   ❌ Missing test files: {', '.join(missing_test_files)}")
        validation_passed = False
    else:
        print("   ✅ All test files are present")
    
    # Final validation result
    print("\n" + "=" * 60)
    if validation_passed:
        print("✅ VALIDATION PASSED - System is ready for stress testing!")
        print("\n🚀 To run stress tests:")
        print("   ./run_phase2_stress_tests.sh")
        print("   OR")
        print("   python3 run_comprehensive_stress_test.py")
        return 0
    else:
        print("❌ VALIDATION FAILED - Please fix the issues above before running stress tests")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))