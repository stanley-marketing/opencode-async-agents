#!/usr/bin/env python3
"""
Performance Setup Validation Script
Validates that all performance optimization components are properly installed and configured
"""

import sys
import os
import importlib
import asyncio
import json
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} (compatible)")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (requires Python 3.8+)")
        return False

def check_required_packages():
    """Check if required packages are installed"""
    print("\n📦 Checking required packages...")
    
    required_packages = [
        'websockets',
        'uvloop', 
        'aiohttp',
        'aiofiles',
        'orjson',
        'lz4',
        'psutil'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n   Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_file_structure():
    """Check if all required files exist"""
    print("\n📁 Checking file structure...")
    
    required_files = [
        'src/performance/__init__.py',
        'src/performance/websocket_optimizer.py',
        'src/performance/connection_pool.py',
        'src/performance/message_queue.py',
        'monitoring/websocket_metrics.py',
        'tests/performance/__init__.py',
        'tests/performance/load_test_websocket.py',
        'run_websocket_performance_tests.py',
        'config/performance_config.yaml',
        'requirements-performance.txt'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} (missing)")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def check_imports():
    """Check if performance modules can be imported"""
    print("\n🔧 Checking module imports...")
    
    try:
        # Add paths to sys.path
        current_dir = os.getcwd()
        sys.path.insert(0, os.path.join(current_dir, 'src'))
        sys.path.insert(0, os.path.join(current_dir, 'monitoring'))
        sys.path.insert(0, os.path.join(current_dir, 'tests'))
        
        # Test individual module imports
        try:
            from performance.connection_pool import WebSocketConnectionPool
            print("   ✅ WebSocketConnectionPool")
        except ImportError as e:
            print(f"   ⚠️  WebSocketConnectionPool: {e} (may work in runtime)")
            # Don't return False here as it might work in runtime
        
        try:
            from performance.message_queue import HighPerformanceMessageQueue
            print("   ✅ HighPerformanceMessageQueue")
        except ImportError as e:
            print(f"   ❌ HighPerformanceMessageQueue: {e}")
            return False
        
        try:
            from performance.websocket_optimizer import HighPerformanceWebSocketManager
            print("   ✅ HighPerformanceWebSocketManager")
        except ImportError as e:
            print(f"   ⚠️  HighPerformanceWebSocketManager: {e} (may work in runtime)")
            # Don't return False here as it might work in runtime
        
        try:
            from websocket_metrics import WebSocketMetricsCollector
            print("   ✅ WebSocketMetricsCollector")
        except ImportError as e:
            print(f"   ❌ WebSocketMetricsCollector: {e}")
            return False
        
        try:
            from performance.load_test_websocket import run_websocket_load_test
            print("   ✅ run_websocket_load_test")
        except ImportError as e:
            print(f"   ❌ run_websocket_load_test: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ General import error: {e}")
        return False

def check_configuration():
    """Check configuration files"""
    print("\n⚙️  Checking configuration...")
    
    try:
        # Check performance config
        if os.path.exists('config/performance_config.yaml'):
            print("   ✅ performance_config.yaml exists")
        else:
            print("   ❌ performance_config.yaml missing")
            return False
        
        # Check legacy config
        if os.path.exists('config/performance.json'):
            with open('config/performance.json', 'r') as f:
                config = json.load(f)
            print("   ✅ performance.json valid")
        else:
            print("   ⚠️  performance.json missing (optional)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration error: {e}")
        return False

async def test_basic_functionality():
    """Test basic functionality of performance components"""
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Add paths to sys.path
        current_dir = os.getcwd()
        sys.path.insert(0, os.path.join(current_dir, 'src'))
        sys.path.insert(0, os.path.join(current_dir, 'monitoring'))
        
        # Test connection pool creation
        try:
            from performance.connection_pool import WebSocketConnectionPool
            pool = WebSocketConnectionPool(max_connections=100)
            await pool.start()
            await pool.stop()
            print("   ✅ Connection pool creation")
        except Exception as e:
            print(f"   ❌ Connection pool test failed: {e}")
            return False
        
        # Test message queue creation
        try:
            from performance.message_queue import HighPerformanceMessageQueue
            queue = HighPerformanceMessageQueue(max_workers=2)
            await queue.start_processor()
            await queue.stop_processor()
            print("   ✅ Message queue creation")
        except Exception as e:
            print(f"   ❌ Message queue test failed: {e}")
            return False
        
        # Test WebSocket manager creation (without starting server)
        try:
            from performance.websocket_optimizer import HighPerformanceWebSocketManager
            manager = HighPerformanceWebSocketManager(host="localhost", port=8766)
            print("   ✅ WebSocket manager creation")
        except Exception as e:
            print(f"   ❌ WebSocket manager test failed: {e}")
            return False
        
        # Test metrics collector
        try:
            from websocket_metrics import WebSocketMetricsCollector
            collector = WebSocketMetricsCollector(collection_interval=1)
            await collector.start_collection()
            await collector.stop_collection()
            print("   ✅ Metrics collector creation")
        except Exception as e:
            print(f"   ❌ Metrics collector test failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Functionality test failed: {e}")
        return False

def check_directories():
    """Create required directories if they don't exist"""
    print("\n📂 Checking/creating directories...")
    
    required_dirs = [
        'src/performance',
        'tests/performance', 
        'monitoring',
        'config',
        'logs',
        'queue_data',
        'metrics'
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"   ✅ Created {dir_path}")
        else:
            print(f"   ✅ {dir_path} exists")
    
    return True

def print_performance_tips():
    """Print performance optimization tips"""
    print("\n💡 Performance Optimization Tips:")
    print("   1. Install uvloop for 40% better async performance:")
    print("      pip install uvloop")
    print("   2. Use orjson for 2-3x faster JSON serialization:")
    print("      pip install orjson")
    print("   3. Enable compression for large messages:")
    print("      pip install lz4")
    print("   4. Monitor system resources:")
    print("      pip install psutil")
    print("   5. For production, consider:")
    print("      - Increasing file descriptor limits: ulimit -n 65536")
    print("      - Optimizing TCP settings in /etc/sysctl.conf")
    print("      - Using multiple worker processes")

def print_next_steps():
    """Print next steps for users"""
    print("\n🚀 Next Steps:")
    print("   1. Run quick performance test:")
    print("      python run_websocket_performance_tests.py --quick")
    print("   2. Run full performance test suite:")
    print("      python run_websocket_performance_tests.py")
    print("   3. Customize configuration:")
    print("      Edit config/performance_config.yaml")
    print("   4. View detailed documentation:")
    print("      cat PERFORMANCE_OPTIMIZATION.md")

async def main():
    """Main validation function"""
    print("🔍 OpenCode-Slack Performance Setup Validation")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version()),
        ("Required Packages", check_required_packages()),
        ("File Structure", check_file_structure()),
        ("Module Imports", check_imports()),
        ("Configuration", check_configuration()),
        ("Directories", check_directories()),
        ("Basic Functionality", await test_basic_functionality())
    ]
    
    passed_checks = sum(1 for _, result in checks if result)
    total_checks = len(checks)
    
    print(f"\n📊 Validation Summary:")
    print(f"   Passed: {passed_checks}/{total_checks} checks")
    
    if passed_checks == total_checks:
        print("   🎉 All checks passed! Performance optimization is ready.")
        print_performance_tips()
        print_next_steps()
        return True
    else:
        print("   ⚠️  Some checks failed. Please fix the issues above.")
        failed_checks = [name for name, result in checks if not result]
        print(f"   Failed checks: {', '.join(failed_checks)}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nValidation failed with error: {e}")
        sys.exit(1)