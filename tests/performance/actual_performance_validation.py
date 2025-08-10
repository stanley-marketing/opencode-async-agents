"""
Actual performance validation tests for the OpenCode-Slack system.
Tests real system performance under load with actual components.
"""

import time
import threading
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.managers.file_ownership import FileOwnershipManager
from src.agents.agent_manager import AgentManager
from src.utils.opencode_wrapper import OpencodeSessionManager
from unittest.mock import MagicMock


class TestActualPerformanceValidation:
    """Test actual system performance under real load"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self, tmp_path):
        """Set up test environment"""
        self.test_dir = tmp_path
        self.db_path = self.test_dir / "performance_test.db"
        self.sessions_dir = self.test_dir / "performance_sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Mock communication manager
        self.mock_comm_manager = MagicMock()
        self.mock_comm_manager.send_message.return_value = True
        self.mock_comm_manager.is_connected.return_value = True
        
        yield

    def test_employee_creation_performance(self):
        """Test performance of creating many employees"""
        file_manager = FileOwnershipManager(str(self.db_path))
        
        start_time = time.time()
        
        # Create 100 employees
        for i in range(100):
            success = file_manager.hire_employee(f"employee_{i}", "developer", "normal")
            assert success
        
        creation_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert creation_time < 10.0  # 10 seconds for 100 employees
        
        # Verify all employees were created
        employees = file_manager.list_employees()
        assert len(employees) == 100
        
        print(f"✅ Created 100 employees in {creation_time:.2f} seconds")

    def test_file_locking_performance(self):
        """Test performance of file locking operations"""
        file_manager = FileOwnershipManager(str(self.db_path))
        
        # Create employees first
        for i in range(20):
            file_manager.hire_employee(f"dev_{i}", "developer", "normal")
        
        start_time = time.time()
        
        # Perform 100 file locking operations
        for i in range(20):
            employee_name = f"dev_{i}"
            files = [f"file_{i}_{j}.py" for j in range(5)]
            result = file_manager.lock_files(employee_name, files, f"Work by {employee_name}")
            assert len(result) == 5  # Should lock all 5 files
        
        locking_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert locking_time < 5.0  # 5 seconds for 100 file locks
        
        # Verify files were locked
        all_locked = file_manager.get_all_locked_files()
        assert len(all_locked) == 100  # 20 employees * 5 files each
        
        print(f"✅ Locked 100 files in {locking_time:.2f} seconds")

    def test_agent_creation_performance(self):
        """Test performance of creating many agents"""
        file_manager = FileOwnershipManager(str(self.db_path))
        agent_manager = AgentManager(file_manager, self.mock_comm_manager)
        
        # Create employees first
        for i in range(50):
            file_manager.hire_employee(f"agent_{i}", "developer", "smart")
        
        start_time = time.time()
        
        # Create agents for all employees
        for i in range(50):
            agent = agent_manager.create_agent(f"agent_{i}", "developer", ["python", "testing"])
            assert agent is not None
        
        agent_creation_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert agent_creation_time < 30.0  # 30 seconds for 50 agents
        
        # Verify all agents were created
        assert len(agent_manager.agents) == 50
        
        print(f"✅ Created 50 agents in {agent_creation_time:.2f} seconds")

    def test_concurrent_operations_performance(self):
        """Test performance under concurrent operations"""
        file_manager = FileOwnershipManager(str(self.db_path))
        
        # Create employees
        for i in range(10):
            file_manager.hire_employee(f"concurrent_{i}", "developer", "normal")
        
        results = {}
        errors = []
        
        def concurrent_file_operations(employee_id):
            try:
                employee_name = f"concurrent_{employee_id}"
                start = time.time()
                
                # Lock files
                files = [f"concurrent_file_{employee_id}_{j}.py" for j in range(3)]
                lock_result = file_manager.lock_files(employee_name, files, f"Concurrent work {employee_id}")
                
                # Simulate some work
                time.sleep(0.1)
                
                # Release files
                release_result = file_manager.release_files(employee_name)
                
                end = time.time()
                results[employee_id] = end - start
                
            except Exception as e:
                errors.append(f"Employee {employee_id}: {e}")
        
        start_time = time.time()
        
        # Start concurrent operations
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_file_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert total_time < 5.0  # 5 seconds for 10 concurrent operations
        assert len(errors) == 0  # No errors should occur
        assert len(results) == 10  # All operations should complete
        
        avg_operation_time = sum(results.values()) / len(results)
        print(f"✅ 10 concurrent operations completed in {total_time:.2f} seconds")
        print(f"✅ Average operation time: {avg_operation_time:.3f} seconds")

    def test_memory_usage_performance(self):
        """Test memory usage under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        file_manager = FileOwnershipManager(str(self.db_path))
        agent_manager = AgentManager(file_manager, self.mock_comm_manager)
        
        # Create many employees and agents
        for i in range(30):
            file_manager.hire_employee(f"memory_test_{i}", "developer", "smart")
            agent_manager.create_agent(f"memory_test_{i}", "developer", ["python"])
        
        # Perform many operations
        for i in range(30):
            employee_name = f"memory_test_{i}"
            files = [f"memory_file_{i}_{j}.py" for j in range(5)]
            file_manager.lock_files(employee_name, files, f"Memory test {i}")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 100  # Less than 100MB increase
        
        print(f"✅ Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB (+{memory_increase:.1f}MB)")

    def test_database_performance(self):
        """Test database performance under load"""
        file_manager = FileOwnershipManager(str(self.db_path))
        
        # Create employees
        for i in range(20):
            file_manager.hire_employee(f"db_test_{i}", "developer", "normal")
        
        start_time = time.time()
        
        # Perform many database operations
        for iteration in range(10):
            # Lock files for all employees
            for i in range(20):
                employee_name = f"db_test_{i}"
                files = [f"db_file_{iteration}_{i}_{j}.py" for j in range(3)]
                file_manager.lock_files(employee_name, files, f"DB test {iteration}")
            
            # Query all locked files
            all_locked = file_manager.get_all_locked_files()
            assert len(all_locked) == 20 * 3  # 20 employees * 3 files each
            
            # Release all files
            for i in range(20):
                employee_name = f"db_test_{i}"
                file_manager.release_files(employee_name)
        
        db_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert db_time < 10.0  # 10 seconds for 200 lock/release cycles
        
        print(f"✅ Database operations completed in {db_time:.2f} seconds")

    def test_system_scalability(self):
        """Test overall system scalability"""
        file_manager = FileOwnershipManager(str(self.db_path))
        agent_manager = AgentManager(file_manager, self.mock_comm_manager)
        
        start_time = time.time()
        
        # Simulate a realistic workload
        num_employees = 25
        
        # 1. Hire employees
        for i in range(num_employees):
            file_manager.hire_employee(f"scale_test_{i}", "developer", "smart")
        
        # 2. Create agents
        for i in range(num_employees):
            agent_manager.create_agent(f"scale_test_{i}", "developer", ["python", "javascript"])
        
        # 3. Simulate work assignments
        for i in range(num_employees):
            employee_name = f"scale_test_{i}"
            files = [f"scale_file_{i}_{j}.py" for j in range(4)]
            file_manager.lock_files(employee_name, files, f"Scale test work {i}")
        
        # 4. Check system status
        employees = file_manager.list_employees()
        locked_files = file_manager.get_all_locked_files()
        agent_status = agent_manager.get_agent_status()
        chat_stats = agent_manager.get_chat_statistics()
        
        total_time = time.time() - start_time
        
        # Verify system state
        assert len(employees) == num_employees
        assert len(locked_files) == num_employees * 4
        assert len(agent_status) == num_employees
        assert chat_stats['total_agents'] == num_employees
        
        # Should complete within reasonable time
        assert total_time < 15.0  # 15 seconds for full system setup
        
        print(f"✅ Full system scalability test completed in {total_time:.2f} seconds")
        print(f"✅ System handled {num_employees} employees with {len(locked_files)} locked files")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])