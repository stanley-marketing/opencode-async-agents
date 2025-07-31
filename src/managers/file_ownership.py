import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
import json

# Set up logging
from src.config.logging_config import logger

class FileOwnershipManager:
    def __init__(self, db_path: str = "employees.db"):
        self.db_path = db_path
        self.init_database()
        logger.info(f"FileOwnershipManager initialized with database: {db_path}")
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create employees table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                hired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create file_locks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                employee_name TEXT NOT NULL,
                task_description TEXT,
                status TEXT DEFAULT 'locked', -- locked, released, requested
                locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_name) REFERENCES employees (name)
            )
        ''')
        
        # Create file_requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                requester TEXT NOT NULL,
                owner TEXT NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending', -- pending, approved, denied
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (requester) REFERENCES employees (name),
                FOREIGN KEY (owner) REFERENCES employees (name)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_locks_path ON file_locks(file_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_locks_employee ON file_locks(employee_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_locks_status ON file_locks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_requests_file ON file_requests(file_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_requests_status ON file_requests(status)')
        
        conn.commit()
        conn.close()
    
    def hire_employee(self, name: str, role: str) -> bool:
        """Hire a new employee"""
        logger.info(f"Attempting to hire employee: {name} as {role}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO employees (name, role) VALUES (?, ?)",
                (name, role)
            )
            conn.commit()
            logger.info(f"Successfully hired employee: {name}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Employee {name} already exists")
            return False
        finally:
            conn.close()
    
    def fire_employee(self, name: str) -> bool:
        """Fire an employee and release all their files"""
        logger.info(f"Firing employee: {name}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Release all locked files
            cursor.execute(
                "UPDATE file_locks SET status = 'released' WHERE employee_name = ? AND status = 'locked'",
                (name,)
            )
            
            # Remove employee from database
            cursor.execute("DELETE FROM employees WHERE name = ?", (name,))
            
            # Deny all pending requests from this employee
            cursor.execute(
                "UPDATE file_requests SET status = 'denied' WHERE requester = ? AND status = 'pending'",
                (name,)
            )
            
            conn.commit()
            logger.info(f"Successfully fired employee: {name}")
            return True
        except Exception as e:
            logger.error(f"Error firing employee {name}: {e}")
            return False
        finally:
            conn.close()
    
    def lock_files(self, employee_name: str, file_paths: List[str], task_description: str) -> Dict[str, str]:
        """Lock files for an employee. Returns dict of {file_path: status}"""
        logger.info(f"Employee {employee_name} attempting to lock files: {file_paths}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        result = {}
        
        for file_path in file_paths:
            # Check if file is already locked
            cursor.execute(
                "SELECT employee_name FROM file_locks WHERE file_path = ? AND status = 'locked'",
                (file_path,)
            )
            existing_lock = cursor.fetchone()
            
            if existing_lock:
                # File is already locked by someone else
                locked_by = existing_lock[0]
                if locked_by == employee_name:
                    result[file_path] = "already_locked"
                else:
                    result[file_path] = f"locked_by_{locked_by}"
                    logger.info(f"File {file_path} already locked by {locked_by}")
            else:
                # Lock the file
                cursor.execute(
                    "INSERT INTO file_locks (file_path, employee_name, task_description) VALUES (?, ?, ?)",
                    (file_path, employee_name, task_description)
                )
                result[file_path] = "locked"
                logger.info(f"File {file_path} locked by {employee_name}")
        
        conn.commit()
        conn.close()
        return result
    
    def release_files(self, employee_name: str, file_paths: List[str] = None) -> List[str]:
        """Release files locked by an employee. If file_paths is None, release all."""
        logger.info(f"Employee {employee_name} attempting to release files: {file_paths}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if file_paths is None:
            # Release all files for this employee
            cursor.execute(
                "UPDATE file_locks SET status = 'released' WHERE employee_name = ? AND status = 'locked'",
                (employee_name,)
            )
            conn.commit()
            conn.close()
            logger.info(f"Released all files for {employee_name}")
            return []
        
        released = []
        for file_path in file_paths:
            cursor.execute(
                "UPDATE file_locks SET status = 'released' WHERE file_path = ? AND employee_name = ? AND status = 'locked'",
                (file_path, employee_name)
            )
            if cursor.rowcount > 0:
                released.append(file_path)
                logger.info(f"Released file {file_path} for {employee_name}")
        
        conn.commit()
        conn.close()
        return released
    
    def get_file_owner(self, file_path: str) -> Optional[str]:
        """Get the owner of a locked file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT employee_name FROM file_locks WHERE file_path = ? AND status = 'locked'",
            (file_path,)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
    
    def get_employee_files(self, employee_name: str) -> List[Dict]:
        """Get all files locked by an employee"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path, task_description, locked_at
            FROM file_locks 
            WHERE employee_name = ? AND status = 'locked'
        """, (employee_name,))
        
        files = []
        for row in cursor.fetchall():
            files.append({
                'file_path': row[0],
                'task_description': row[1],
                'locked_at': row[2]
            })
        
        conn.close()
        return files
    
    def list_employees(self) -> List[Dict]:
        """List all employees"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, role, hired_at FROM employees ORDER BY name")
        
        employees = []
        for row in cursor.fetchall():
            employees.append({
                'name': row[0],
                'role': row[1],
                'hired_at': row[2]
            })
        
        conn.close()
        return employees
    
    def request_file(self, requester: str, file_path: str, reason: str) -> str:
        """Request a file from another employee"""
        logger.info(f"Employee {requester} requesting file {file_path}: {reason}")
        
        owner = self.get_file_owner(file_path)
        if not owner:
            return "file_not_locked"
        
        if owner == requester:
            return "already_owner"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if request already exists
        cursor.execute(
            "SELECT id FROM file_requests WHERE file_path = ? AND requester = ? AND owner = ? AND status = 'pending'",
            (file_path, requester, owner)
        )
        
        if cursor.fetchone():
            conn.close()
            return "request_already_exists"
        
        # Create request
        cursor.execute(
            "INSERT INTO file_requests (file_path, requester, owner, reason) VALUES (?, ?, ?, ?)",
            (file_path, requester, owner, reason)
        )
        
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"File request #{request_id} created: {requester} wants {file_path} from {owner}")
        return f"request_sent_to_{owner}"
    
    def get_pending_requests(self, owner: str = None) -> List[Dict]:
        """Get pending file requests for an owner, or all pending requests if no owner specified"""
        if owner:
            logger.info(f"Getting pending requests for owner: {owner}")
            query = '''
                SELECT id, file_path, requester, reason, requested_at, owner
                FROM file_requests 
                WHERE owner = ? AND status = 'pending'
            '''
            params = (owner,)
        else:
            logger.info("Getting all pending requests")
            query = '''
                SELECT id, file_path, requester, reason, requested_at, owner
                FROM file_requests 
                WHERE status = 'pending'
            '''
            params = ()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(query, params)
        
        requests = []
        for row in cursor.fetchall():
            requests.append({
                'id': row[0],
                'file_path': row[1],
                'requesting_employee': row[2],
                'task_description': row[3],
                'requested_at': row[4],
                'locked_by_employee': row[5]
            })
        
        conn.close()
        logger.info(f"Found {len(requests)} pending requests")
        return requests
    
    def release_ready_files(self, employee_name: str, task_progress_tracker) -> List[str]:
        """Release files that are marked as ready to release"""
        logger.info(f"Checking for ready files for {employee_name}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get files that are ready to release
        cursor.execute("""
            SELECT file_path FROM file_locks 
            WHERE employee_name = ? AND status = 'locked'
        """, (employee_name,))
        
        ready_files = []
        for row in cursor.fetchall():
            file_path = row[0]
            progress = task_progress_tracker.get_task_progress(employee_name)
            if progress and file_path in progress.get('ready_to_release', []):
                ready_files.append(file_path)
        
        # Release ready files
        for file_path in ready_files:
            cursor.execute(
                "UPDATE file_locks SET status = 'released' WHERE file_path = ? AND employee_name = ? AND status = 'locked'",
                (file_path, employee_name)
            )
            logger.info(f"Released ready file {file_path} for {employee_name}")
        
        conn.commit()
        conn.close()
        return ready_files
    
    def approve_request(self, request_id: int) -> bool:
        """Approve a file request"""
        logger.info(f"Approving request #{request_id}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get request details
        cursor.execute(
            "SELECT file_path, requester, owner FROM file_requests WHERE id = ? AND status = 'pending'",
            (request_id,)
        )
        request = cursor.fetchone()
        
        if not request:
            logger.warning(f"Request #{request_id} not found or not pending")
            conn.close()
            return False
        
        file_path, requester, owner = request
        
        # Release file from current owner
        cursor.execute(
            "UPDATE file_locks SET status = 'released' WHERE file_path = ? AND employee_name = ? AND status = 'locked'",
            (file_path, owner)
        )
        
        # Lock file for requester
        cursor.execute(
            "INSERT INTO file_locks (file_path, employee_name, task_description, status) VALUES (?, ?, ?, 'locked')",
            (file_path, requester, f"Approved request #{request_id}")
        )
        
        # Update request status
        cursor.execute(
            "UPDATE file_requests SET status = 'approved' WHERE id = ?",
            (request_id,)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Approved request #{request_id}: {owner} -> {requester} for {file_path}")
        return True
    
    def deny_request(self, request_id: int) -> bool:
        """Deny a file request"""
        logger.info(f"Denying request #{request_id}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update request status
        cursor.execute(
            "UPDATE file_requests SET status = 'denied' WHERE id = ? AND status = 'pending'",
            (request_id,)
        )
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logger.info(f"Denied request #{request_id}")
            return True
        else:
            logger.warning(f"Request #{request_id} not found or not pending")
            return False

    def get_all_locked_files(self) -> List[Dict]:
        """Get all currently locked files with owner information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path, employee_name, task_description, locked_at
            FROM file_locks 
            WHERE status = 'locked'
            ORDER BY locked_at DESC
        """)
        
        files = []
        for row in cursor.fetchall():
            files.append({
                'file_path': row[0],
                'employee_name': row[1],
                'task_description': row[2],
                'locked_at': row[3]
            })
        
        conn.close()
        return files