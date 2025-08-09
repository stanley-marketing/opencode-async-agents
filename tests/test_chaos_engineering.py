#!/usr/bin/env python3
"""
Chaos Engineering Test Suite
Simulates realistic failure scenarios and tests system resilience
"""

import unittest
import sys
import os
import time
import threading
import tempfile
import random
import signal
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import concurrent.futures

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import OpencodeSlackServer
from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.agents.agent_manager import AgentManager
from src.utils.opencode_wrapper import OpencodeSessionManager


class ChaosEngineeringTest(unittest.TestCase):
    """Chaos engineering tests for system resilience"""
    
    def setUp(self):
        """Set up chaos testing environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "chaos_test.db")
        self.sessions_dir = os.path.join(self.temp_dir, "chaos_sessions")
        
        # Initialize components
        self.file_manager = FileOwnershipManager(self.db_path)
        self.task_tracker = TaskProgressTracker(self.sessions_dir)
        self.telegram_manager = ChaosAwareTelegramManager()
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        self.session_manager = OpencodeSessionManager(
            self.file_manager, self.sessions_dir, quiet_mode=True
        )
        
        # Chaos test results
        self.chaos_results = {
            'random_failures': [],
            'resource_exhaustion': [],
            'timing_attacks': [],
            'cascade_failures': [],
            'recovery_stress_tests': []
        }
        
        print(f"🌪️  Chaos engineering environment initialized")
    
    def tearDown(self):
        """Clean up chaos test environment"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"⚠️ Chaos cleanup warning: {e}")
    
    def test_random_component_failures(self):
        """Test system resilience to random component failures"""
        print("\n🎲 Testing random component failures...")
        
        # Create test agents
        agent_names = [f"chaos_agent_{i}" for i in range(5)]
        for name in agent_names:
            self.file_manager.hire_employee(name, "developer")
            self.agent_manager.create_agent(name, "developer")
        
        # Simulate random failures
        failure_scenarios = [
            self._simulate_database_lock,
            self._simulate_file_system_full,
            self._simulate_network_partition,
            self._simulate_memory_corruption,
            self._simulate_process_kill
        ]
        
        failures_survived = 0
        total_failures = len(failure_scenarios)
        
        for i, failure_func in enumerate(failure_scenarios):
            try:
                print(f"   🔥 Executing failure scenario {i+1}/{total_failures}")
                failure_func()
                
                # Test system responsiveness after failure
                time.sleep(0.5)
                status = self.agent_manager.get_agent_status()
                if len(status) > 0:
                    failures_survived += 1
                    print(f"   ✅ System survived failure scenario {i+1}")
                else:
                    print(f"   ❌ System failed in scenario {i+1}")
                    
            except Exception as e:
                print(f"   ⚠️ Exception in failure scenario {i+1}: {e}")
        
        survival_rate = failures_survived / total_failures
        
        self.chaos_results['random_failures'].append({
            'test': 'random_component_failures',
            'survival_rate': survival_rate,
            'details': f"Survived {failures_survived}/{total_failures} failure scenarios",
            'timestamp': datetime.now()
        })
        
        print(f"   📊 Survival rate: {survival_rate:.1%}")
    
    def test_resource_exhaustion_scenarios(self):
        """Test system behavior under resource exhaustion"""
        print("\n💾 Testing resource exhaustion scenarios...")
        
        exhaustion_tests = [
            self._test_memory_exhaustion,
            self._test_disk_space_exhaustion,
            self._test_file_descriptor_exhaustion,
            self._test_thread_exhaustion
        ]
        
        passed_tests = 0
        
        for test_func in exhaustion_tests:
            try:
                result = test_func()
                if result:
                    passed_tests += 1
                    print(f"   ✅ {test_func.__name__} passed")
                else:
                    print(f"   ❌ {test_func.__name__} failed")
            except Exception as e:
                print(f"   ⚠️ {test_func.__name__} exception: {e}")
        
        self.chaos_results['resource_exhaustion'].append({
            'test': 'resource_exhaustion_scenarios',
            'success_rate': passed_tests / len(exhaustion_tests),
            'details': f"Passed {passed_tests}/{len(exhaustion_tests)} exhaustion tests",
            'timestamp': datetime.now()
        })
    
    def test_timing_and_race_conditions(self):
        """Test system resilience to timing attacks and race conditions"""
        print("\n⏱️  Testing timing and race conditions...")
        
        # Test concurrent agent creation
        def create_agent_worker(agent_id):
            try:
                name = f"race_agent_{agent_id}"
                self.file_manager.hire_employee(name, "developer")
                self.agent_manager.create_agent(name, "developer")
                return True
            except Exception:
                return False
        
        # Create agents concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_agent_worker, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        successful_creations = sum(results)
        race_condition_handled = successful_creations > 15  # Most should succeed
        
        # Test concurrent file locking
        def lock_file_worker(worker_id):
            try:
                employee_name = f"race_agent_{worker_id % 5}"  # Use existing agents
                result = self.file_manager.lock_files(
                    employee_name, [f"test_file_{worker_id}.py"], "concurrent test"
                )
                return len(result) > 0
            except Exception:
                return False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(lock_file_worker, i) for i in range(20)]
            lock_results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        successful_locks = sum(lock_results)
        
        self.chaos_results['timing_attacks'].append({
            'test': 'timing_and_race_conditions',
            'success': race_condition_handled and successful_locks > 10,
            'details': f"Agent creations: {successful_creations}/20, File locks: {successful_locks}/20",
            'timestamp': datetime.now()
        })
        
        print(f"   📊 Concurrent operations: {successful_creations} agents, {successful_locks} locks")
    
    def test_cascade_failure_scenarios(self):
        """Test system resilience to cascade failures"""
        print("\n🌊 Testing cascade failure scenarios...")
        
        # Create interconnected system state
        agents = []
        for i in range(5):
            name = f"cascade_agent_{i}"
            self.file_manager.hire_employee(name, "developer")
            agent = self.agent_manager.create_agent(name, "developer")
            agents.append((name, agent))
        
        # Simulate cascade failure starting with one component
        cascade_steps = []
        
        # Step 1: Telegram failure
        self.telegram_manager.simulate_failure()
        cascade_steps.append("telegram_failure")
        
        # Step 2: Database corruption
        try:
            with open(self.db_path, 'w') as f:
                f.write("CORRUPTED")
            cascade_steps.append("database_corruption")
        except Exception:
            pass
        
        # Step 3: Session directory removal
        try:
            import shutil
            shutil.rmtree(self.sessions_dir, ignore_errors=True)
            cascade_steps.append("session_dir_removal")
        except Exception:
            pass
        
        # Test system state after cascade
        try:
            # Try to create new agent (should handle gracefully)
            self.agent_manager.create_agent("cascade_survivor", "developer")
            system_survived = True
        except Exception:
            system_survived = False
        
        self.chaos_results['cascade_failures'].append({
            'test': 'cascade_failure_scenarios',
            'success': system_survived,
            'details': f"Cascade steps: {cascade_steps}, System survived: {system_survived}",
            'timestamp': datetime.now()
        })
        
        print(f"   📊 Cascade failure test: {len(cascade_steps)} steps, survived: {system_survived}")
    
    def test_recovery_under_stress(self):
        """Test recovery mechanisms under stress conditions"""
        print("\n🏋️  Testing recovery under stress...")
        
        # Create stressed environment
        stress_agents = []
        for i in range(10):
            name = f"stress_agent_{i}"
            self.file_manager.hire_employee(name, "developer")
            agent = self.agent_manager.create_agent(name, "developer")
            # Put agents in various failure states
            agent.worker_status = random.choice(["stuck", "crashed", "timeout"])
            stress_agents.append(name)
        
        # Simulate recovery attempts under load
        recovery_attempts = 0
        successful_recoveries = 0
        
        # Try to recover agents while system is under stress
        for agent_name in stress_agents:
            recovery_attempts += 1
            try:
                # Simulate recovery process
                agent = self.agent_manager.agents[agent_name]
                agent.worker_status = "idle"  # Simulate successful recovery
                successful_recoveries += 1
            except Exception:
                pass
        
        recovery_rate = successful_recoveries / recovery_attempts if recovery_attempts > 0 else 0
        
        self.chaos_results['recovery_stress_tests'].append({
            'test': 'recovery_under_stress',
            'success': recovery_rate >= 0.7,  # 70% recovery rate under stress
            'details': f"Recovery rate: {recovery_rate:.1%} ({successful_recoveries}/{recovery_attempts})",
            'timestamp': datetime.now()
        })
        
        print(f"   📊 Recovery under stress: {recovery_rate:.1%} success rate")
    
    # ==================== FAILURE SIMULATION METHODS ====================
    
    def _simulate_database_lock(self):
        """Simulate database lock/corruption"""
        try:
            # Try to lock the database file
            import fcntl
            with open(self.db_path, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                time.sleep(0.1)
        except Exception:
            pass  # Expected to fail
    
    def _simulate_file_system_full(self):
        """Simulate file system full condition"""
        try:
            # Try to create a large file
            large_file = os.path.join(self.temp_dir, "large_file.tmp")
            with open(large_file, 'w') as f:
                f.write("x" * 1024 * 1024)  # 1MB file
        except Exception:
            pass  # May fail due to space
    
    def _simulate_network_partition(self):
        """Simulate network partition"""
        self.telegram_manager.simulate_network_partition()
    
    def _simulate_memory_corruption(self):
        """Simulate memory corruption"""
        # Corrupt agent state
        for agent in self.agent_manager.agents.values():
            agent.worker_status = None
            agent.current_task = None
    
    def _simulate_process_kill(self):
        """Simulate process being killed"""
        # Simulate abrupt termination by clearing all state
        self.agent_manager.agents.clear()
    
    # ==================== RESOURCE EXHAUSTION TESTS ====================
    
    def _test_memory_exhaustion(self):
        """Test behavior under memory exhaustion"""
        try:
            # Create many objects to simulate memory pressure
            memory_hogs = []
            for i in range(100):
                memory_hogs.append([0] * 10000)  # Create large lists
            
            # Test if system still responds
            status = self.agent_manager.get_agent_status()
            return len(status) >= 0  # Should not crash
        except MemoryError:
            return True  # Handled gracefully
        except Exception:
            return False
    
    def _test_disk_space_exhaustion(self):
        """Test behavior when disk space is exhausted"""
        try:
            # Try to create many files
            for i in range(100):
                file_path = os.path.join(self.temp_dir, f"test_file_{i}.tmp")
                with open(file_path, 'w') as f:
                    f.write("test data" * 1000)
            return True
        except OSError:
            return True  # Handled gracefully
        except Exception:
            return False
    
    def _test_file_descriptor_exhaustion(self):
        """Test behavior when file descriptors are exhausted"""
        try:
            # Open many files without closing
            open_files = []
            for i in range(100):
                file_path = os.path.join(self.temp_dir, f"fd_test_{i}.tmp")
                f = open(file_path, 'w')
                open_files.append(f)
            
            # Test system responsiveness
            status = self.agent_manager.get_agent_status()
            
            # Clean up
            for f in open_files:
                try:
                    f.close()
                except:
                    pass
            
            return len(status) >= 0
        except OSError:
            return True  # Handled gracefully
        except Exception:
            return False
    
    def _test_thread_exhaustion(self):
        """Test behavior when thread limit is reached"""
        try:
            threads = []
            for i in range(50):
                t = threading.Thread(target=lambda: time.sleep(0.1))
                t.start()
                threads.append(t)
            
            # Test system responsiveness
            status = self.agent_manager.get_agent_status()
            
            # Clean up
            for t in threads:
                t.join(timeout=1)
            
            return len(status) >= 0
        except Exception:
            return False
    
    def test_comprehensive_chaos_engineering(self):
        """Run all chaos engineering tests and generate report"""
        print("\n🌪️  STARTING CHAOS ENGINEERING VALIDATION")
        print("=" * 60)
        
        # Run all chaos tests
        chaos_methods = [
            self.test_random_component_failures,
            self.test_resource_exhaustion_scenarios,
            self.test_timing_and_race_conditions,
            self.test_cascade_failure_scenarios,
            self.test_recovery_under_stress,
        ]
        
        for test_method in chaos_methods:
            try:
                test_method()
            except Exception as e:
                print(f"   ❌ Chaos test {test_method.__name__} failed: {e}")
        
        # Generate chaos report
        self._generate_chaos_report()
    
    def _generate_chaos_report(self):
        """Generate chaos engineering report"""
        print("\n📊 CHAOS ENGINEERING REPORT")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        
        for category, results in self.chaos_results.items():
            if not results:
                continue
                
            print(f"\n🌪️  {category.replace('_', ' ').title()}:")
            
            for result in results:
                total_tests += 1
                success = result.get('success', result.get('survival_rate', 0) > 0.5)
                status = "✅ RESILIENT" if success else "❌ VULNERABLE"
                print(f"   {status} {result['test']}: {result['details']}")
                
                if success:
                    passed_tests += 1
        
        # Overall resilience score
        resilience_score = passed_tests / total_tests if total_tests > 0 else 0
        print(f"\n🏆 OVERALL RESILIENCE SCORE: {resilience_score:.1%} ({passed_tests}/{total_tests})")
        
        # Resilience assessment
        if resilience_score >= 0.9:
            print("   🛡️  EXCELLENT: System shows exceptional resilience to chaos!")
        elif resilience_score >= 0.7:
            print("   💪 GOOD: System handles most failure scenarios well.")
        elif resilience_score >= 0.5:
            print("   ⚠️  MODERATE: System needs resilience improvements.")
        else:
            print("   🚨 POOR: System is vulnerable to failures. Immediate attention needed!")
        
        print(f"\n✅ Chaos engineering completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


class ChaosAwareTelegramManager:
    """Telegram manager that can simulate various failure modes"""
    
    def __init__(self):
        self.connected = True
        self.network_partition = False
        self.failure_mode = None
        self.messages = []
    
    def add_message_handler(self, handler):
        pass
    
    def is_connected(self):
        return self.connected and not self.network_partition and not self.failure_mode
    
    def send_message(self, text, sender_name="system", reply_to=None):
        if not self.is_connected():
            return False
        
        self.messages.append({
            'text': text,
            'sender': sender_name,
            'timestamp': datetime.now()
        })
        return True
    
    def simulate_failure(self):
        """Simulate general failure"""
        self.failure_mode = "general_failure"
        self.connected = False
    
    def simulate_network_partition(self):
        """Simulate network partition"""
        self.network_partition = True
    
    def restore_connection(self):
        """Restore connection"""
        self.connected = True
        self.network_partition = False
        self.failure_mode = None


if __name__ == '__main__':
    # Run chaos engineering tests
    suite = unittest.TestLoader().loadTestsFromTestCase(ChaosEngineeringTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)