# SPDX-License-Identifier: MIT
from datetime import datetime
from pathlib import Path
from src.config.config import Config
from src.config.logging_config import logger
from typing import List, Dict, Optional
import json
import logging
import os
import sqlite3

class FileOwnershipManager:
    def __init__(self, db_path: str = "employees.db"):
        self.db_path = db_path
        self.project_root = Path(Config.PROJECT_ROOT).resolve()
        self.init_database()
        logger.info(f"FileOwnershipManager initialized with database: {db_path}")
        logger.info(f"Project root directory: {self.project_root}")

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
                smartness TEXT DEFAULT 'normal', -- smart | normal
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

    def hire_employee(self, name: str, role: str, smartness: str = "normal") -> bool:
        """Hire a new employee"""
        logger.info(f"Attempting to hire employee: {name} as {role} with {smartness} smartness")

        # Validate smartness level
        if smartness not in ["smart", "normal"]:
            smartness = "normal"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO employees (name, role, smartness) VALUES (?, ?, ?)",
                (name, role, smartness)
            )
            conn.commit()
            logger.info(f"Successfully hired employee: {name} as {role} with {smartness} smartness")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Employee {name} already exists")
            return False
        finally:
            conn.close()

    def employee_exists(self, name: str) -> bool:
        """Check if an employee exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT 1 FROM employees WHERE name = ?", (name,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def fire_employee(self, name: str, task_tracker=None) -> bool:
        """Fire an employee and release all their files"""
        logger.info(f"Firing employee: {name}")

        # Check if employee exists first
        if not self.employee_exists(name):
            logger.info(f"Employee {name} does not exist, nothing to fire")
            return False

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

            # Clean up session data if task tracker is provided
            if task_tracker:
                task_tracker.cleanup_employee_session(name)

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

        # Resolve file paths relative to project root
        resolved_file_paths = [self._resolve_file_path(fp) for fp in file_paths]
        logger.info(f"Resolved file paths: {resolved_file_paths}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        result = {}

        for original_path, file_path in zip(file_paths, resolved_file_paths):
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
                    result[original_path] = "already_locked"
                else:
                    result[original_path] = f"locked_by_{locked_by}"
                    logger.info(f"File {file_path} already locked by {locked_by}")
            else:
                # Lock the file
                cursor.execute(
                    "INSERT INTO file_locks (file_path, employee_name, task_description) VALUES (?, ?, ?)",
                    (file_path, employee_name, task_description)
                )
                result[original_path] = "locked"
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

        # Resolve file paths relative to project root
        resolved_file_paths = [self._resolve_file_path(fp) for fp in file_paths]
        logger.info(f"Resolved file paths for release: {resolved_file_paths}")

        released = []
        for original_path, file_path in zip(file_paths, resolved_file_paths):
            cursor.execute(
                "UPDATE file_locks SET status = 'released' WHERE file_path = ? AND employee_name = ? AND status = 'locked'",
                (file_path, employee_name)
            )
            if cursor.rowcount > 0:
                released.append(original_path)
                logger.info(f"Released file {file_path} for {employee_name}")

        conn.commit()
        conn.close()
        return released

    def get_file_owner(self, file_path: str) -> Optional[str]:
        """Get the owner of a locked file"""
        # Resolve file path relative to project root
        resolved_path = self._resolve_file_path(file_path)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT employee_name FROM file_locks WHERE file_path = ? AND status = 'locked'",
            (resolved_path,)
        )
        result = cursor.fetchone()

        conn.close()

        if result:
            return result[0]
        return None

    def get_employee_info(self, employee_name: str) -> Optional[Dict]:
        """Get employee information including smartness level"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, role, smartness, hired_at
            FROM employees
            WHERE name = ?
        """, (employee_name,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'name': row[0],
                'role': row[1],
                'smartness': row[2],
                'hired_at': row[3]
            }
        return None

    def get_employee_info(self, employee_name: str) -> Optional[Dict]:
        """Get employee information including smartness level"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, role, smartness, hired_at
            FROM employees
            WHERE name = ?
        """, (employee_name,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'name': row[0],
                'role': row[1],
                'smartness': row[2],
                'hired_at': row[3]
            }
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
            file_path = row[0]
            # Convert to relative path for display
            try:
                relative_path = os.path.relpath(file_path, self.project_root)
            except ValueError:
                # If we can't make it relative, use the full path
                relative_path = file_path

            files.append({
                'file_path': relative_path,
                'task_description': row[1],
                'locked_at': row[2]
            })

        conn.close()
        return files

    def list_employees(self) -> List[Dict]:
        """List all employees"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name, role, smartness, hired_at FROM employees ORDER BY name")

        employees = []
        for row in cursor.fetchall():
            employees.append({
                'name': row[0],
                'role': row[1],
                'smartness': row[2],
                'hired_at': row[3]
            })

        conn.close()
        return employees

    def request_file(self, requester: str, file_path: str, reason: str) -> str:
        """Request a file from another employee"""
        # Resolve file path relative to project root
        resolved_path = self._resolve_file_path(file_path)
        logger.info(f"Employee {requester} requesting file {file_path} (resolved: {resolved_path}): {reason}")

        owner = self.get_file_owner(file_path)  # This will use the resolved path internally
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
                # Convert back to relative path for return value
                try:
                    relative_path = os.path.relpath(file_path, self.project_root)
                    ready_files.append(relative_path)
                except ValueError:
                    # If we can't make it relative, return the full path
                    ready_files.append(file_path)

        # Release ready files
        for file_path in ready_files:
            resolved_path = self._resolve_file_path(file_path)
            cursor.execute(
                "UPDATE file_locks SET status = 'released' WHERE file_path = ? AND employee_name = ? AND status = 'locked'",
                (resolved_path, employee_name)
            )
            logger.info(f"Released ready file {resolved_path} for {employee_name}")

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
        resolved_path = self._resolve_file_path(file_path)

        # Release file from current owner
        cursor.execute(
            "UPDATE file_locks SET status = 'released' WHERE file_path = ? AND employee_name = ? AND status = 'locked'",
            (resolved_path, owner)
        )

        # Lock file for requester
        cursor.execute(
            "INSERT INTO file_locks (file_path, employee_name, task_description, status) VALUES (?, ?, ?, 'locked')",
            (resolved_path, requester, f"Approved request #{request_id}")
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
            file_path = row[0]
            # Convert to relative path for display
            try:
                relative_path = os.path.relpath(file_path, self.project_root)
            except ValueError:
                # If we can't make it relative, use the full path
                relative_path = file_path

            files.append({
                'file_path': relative_path,
                'employee_name': row[1],
                'task_description': row[2],
                'locked_at': row[3]
            })

        conn.close()
        return files

    def set_project_root(self, project_root: str) -> bool:
        """Set the project root directory"""
        try:
            # Validate and resolve the path
            root_path = Path(project_root).resolve()

            # Ensure directory exists
            root_path.mkdir(parents=True, exist_ok=True)

            # Update configuration
            self.project_root = root_path

            # Update environment variable for persistence
            os.environ['PROJECT_ROOT'] = str(root_path)

            logger.info(f"Project root directory updated to: {root_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to set project root directory: {e}")
            return False

    def get_project_root(self) -> str:
        """Get the current project root directory"""
        return str(self.project_root)

    def _resolve_file_path(self, file_path: str) -> str:
        """Resolve a file path relative to the project root"""
        # If file_path is already absolute, return as is
        if os.path.isabs(file_path):
            return file_path

        # Otherwise, resolve relative to project root
        return str(self.project_root / file_path)