#!/usr/bin/env python3
"""
Comprehensive Stress Testing Suite for OpenCode-Slack Phase 2 Optimizations
Tests all performance optimizations under extreme load conditions to validate production readiness.

This suite validates:
1. Maximum capacity testing (100+ users, 50+ agents, 200+ tasks, 1000+ msg/min)
2. Performance optimization validation under stress
3. System resilience and graceful degradation
4. Concurrency stress testing with maximum loads
5. Communication stress testing (120+ msg/s)
6. Integration stress testing
7. Production load simulation
8. Failure scenario testing
"""

import asyncio
import aiohttp
import time
import json
import logging
import statistics
import concurrent.futures
import threading
import psutil
import random
import subprocess
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import signal

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stress_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class StressTestConfig:
    """Configuration for stress testing parameters"""
    # Server configuration
    async_server_url: str = "http://localhost:8080"
    sync_server_url: str = "http://localhost:8081"
    
    # Maximum capacity targets (Phase 2 goals)
    max_concurrent_users: int = 100
    max_concurrent_agents: int = 50
    max_concurrent_tasks: int = 200
    max_message_throughput: int = 1000  # messages per minute
    max_realtime_messages: int = 120    # messages per second
    
    # Test duration settings
    sustained_load_duration: int = 10   # minutes
    burst_test_duration: int = 2        # minutes
    
    # Stress test thresholds
    acceptable_error_rate: float = 5.0  # percent
    acceptable_response_time: float = 2.0  # seconds
    memory_limit_gb: float = 8.0
    cpu_limit_percent: float = 80.0

@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read: float
    disk_io_write: float
    network_sent: float
    network_recv: float
    timestamp: float

class ResourceMonitor:
    """Monitors system resources during stress testing"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self._lock = threading.Lock()
        
    def start_monitoring(self):
        """Start resource monitoring"""
        self.monitoring = True
        self.metrics = []
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        
    def stop_monitoring(self) -> List[PerformanceMetrics]:
        """Stop monitoring and return collected metrics"""
        self.monitoring = False
        time.sleep(1)  # Allow final collection
        with self._lock:
            return self.metrics.copy()
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                cpu = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                net_io = psutil.net_io_counters()
                
                metric = PerformanceMetrics(
                    cpu_percent=cpu,
                    memory_mb=memory.used / (1024 * 1024),
                    memory_percent=memory.percent,
                    disk_io_read=disk_io.read_bytes if disk_io else 0,
                    disk_io_write=disk_io.write_bytes if disk_io else 0,
                    network_sent=net_io.bytes_sent if net_io else 0,
                    network_recv=net_io.bytes_recv if net_io else 0,
                    timestamp=time.time()
                )
                
                with self._lock:
                    self.metrics.append(metric)
                    
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                
            time.sleep(1)

class ComprehensiveStressTester:
    """Comprehensive stress testing suite for OpenCode-Slack Phase 2 optimizations"""
    
    def __init__(self, config: StressTestConfig = None):
        self.config = config or StressTestConfig()
        self.resource_monitor = ResourceMonitor()
        self.test_results = []
        self.session = None
        self.test_employees = []
        self.test_start_time = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=50)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] {level}: {message}")
        getattr(logger, level.lower())(message)

    async def cleanup_test_data(self):
        """Clean up all test data"""
        try:
            # Get all employees
            async with self.session.get(f"{self.config.async_server_url}/employees") as response:
                if response.status == 200:
                    data = await response.json()
                    employees = data.get('employees', [])
                    
                    # Delete test employees
                    for employee in employees:
                        name = employee.get('name', '')
                        if any(prefix in name for prefix in ['stress_', 'test_', 'load_', 'perf_', 'scale_']):
                            try:
                                async with self.session.delete(
                                    f"{self.config.async_server_url}/employees/{name}"
                                ) as del_response:
                                    pass
                            except Exception as e:
                                logger.debug(f"Error deleting employee {name}: {e}")
                                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    # Helper methods for API operations
    async def _create_employee(self, name: str, role: str) -> bool:
        """Create an employee via API"""
        try:
            async with self.session.post(
                f"{self.config.async_server_url}/employees",
                json={"name": name, "role": role},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Failed to create employee {name}: {e}")
            return False

    async def _assign_task(self, employee_name: str, task: str) -> bool:
        """Assign task to employee via API"""
        try:
            async with self.session.post(
                f"{self.config.async_server_url}/tasks",
                json={"name": employee_name, "task": task},
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Failed to assign task to {employee_name}: {e}")
            return False

    async def _get_status(self) -> bool:
        """Get system status via API"""
        try:
            async with self.session.get(
                f"{self.config.async_server_url}/status",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Failed to get status: {e}")
            return False

    async def _get_employees(self) -> bool:
        """Get employees list via API"""
        try:
            async with self.session.get(
                f"{self.config.async_server_url}/employees",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Failed to get employees: {e}")
            return False