#!/usr/bin/env python3
"""
Enhanced File Ownership Manager with comprehensive error handling and resilience.
Built on top of the robust DatabaseManager for improved reliability.
"""

from datetime import datetime, timedelta
from pathlib import Path
from src.config.config import Config
from src.config.logging_config import logger
from src.database.database_manager import DatabaseManager, DatabaseError
from typing import List, Dict, Optional, Set
import json
import logging
import os

class FileOwnershipError(Exception):
    """Base exception for file ownership errors"""
    pass


class FilePermissionError(FileOwnershipError):
    """Exception raised for file permission issues"""
    pass


class FileLockError(FileOwnershipError):
    """Exception raised for file locking issues"""
    pass


class EnhancedFileOwnershipManager:
    """Enhanced file ownership manager with comprehensive error handling"""

    def __init__(self, db_path: str = "employees.db", backup_dir: Optional[str] = None):
        self.project_root = Path(Config.PROJECT_ROOT).resolve()

        try:
            # Initialize enhanced database manager
            self.db_manager = DatabaseManager(
                db_path=db_path,
                backup_dir=backup_dir,
                auto_backup=True
            )

            # Initialize file system monitoring
            self._initialize_file_system_monitoring()

            logger.info(f"Enhanced FileOwnershipManager initialized")
            logger.info(f"Database: {db_path}")
            logger.info(f"Project root: {self.project_root}")

        except Exception as e:
            logger.error(f"Failed to initialize FileOwnershipManager: {e}")
            raise FileOwnershipError(f"Initialization failed: {e}")

    def _initialize_file_system_monitoring(self):
        """Initialize file system monitoring and validation"""
        try:
            # Ensure project root exists and is accessible
            if not self.project_root.exists():
                logger.warning(f"Project root does not exist, creating: {self.project_root}")
                self.project_root.mkdir(parents=True, exist_ok=True)

            # Check write permissions
            test_file = self.project_root / ".opencode_test_write"
            try:
                test_file.write_text("test")
                test_file.unlink()
                logger.debug("Project root write permissions verified")
            except Exception as e:
                logger.error(f"Project root write permission check failed: {e}")
                raise FilePermissionError(f"No write access to project root: {e}")

            # Check disk space
            self._check_disk_space()

        except Exception as e:
            logger.error(f"File system monitoring initialization failed: {e}")
            # Don't raise exception here, allow degraded operation

    def _check_disk_space(self, min_free_mb: int = 100):
        """Check available disk space"""
        try:
            stat = os.statvfs(self.project_root)
            free_bytes = stat.f_bavail * stat.f_frsize
            free_mb = free_bytes / (1024 * 1024)

            if free_mb < min_free_mb:
                logger.warning(f"Low disk space: {free_mb:.1f}MB available")
                return False

            logger.debug(f"Disk space check passed: {free_mb:.1f}MB available")
            return True

        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return False

    def hire_employee(self, name: str, role: str, smartness: str = "normal") -> bool:
        """Hire a new employee with comprehensive error handling"""
        try:
            logger.info(f"Attempting to hire employee: {name} as {role} with {smartness} smartness")

            # Validate inputs
            if not name or not name.strip():
                raise ValueError("Employee name cannot be empty")

            if not role or not role.strip():
                raise ValueError("Employee role cannot be empty")

            if smartness not in ["smart", "normal"]:
                logger.warning(f"Invalid smartness level '{smartness}', defaulting to 'normal'")
                smartness = "normal"

            # Sanitize inputs
            name = name.strip()
            role = role.strip()

            # Check if employee already exists
            if self.employee_exists(name):
                logger.warning(f"Employee {name} already exists")
                return False

            # Insert employee with retry logic
            query = """
                INSERT INTO employees (name, role, smartness, status, metadata)
                VALUES (?, ?, ?, 'active', ?)
            """
            metadata = json.dumps({
                'hired_by': 'system',
                'hire_reason': 'manual_hire',
                'initial_role': role
            })

            rows_affected = self.db_manager.execute_with_retry(
                query, (name, role, smartness, metadata)
            )

            if rows_affected > 0:
                logger.info(f"Successfully hired employee: {name} as {role}")

                # Create employee workspace if needed
                self._create_employee_workspace(name)

                return True
            else:
                logger.error(f"Failed to hire employee {name}: No rows affected")
                return False

        except ValueError as e:
            logger.error(f"Invalid input for hiring {name}: {e}")
            return False
        except DatabaseError as e:
            logger.error(f"Database error hiring {name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error hiring {name}: {e}")
            return False

    def _create_employee_workspace(self, name: str):
        """Create workspace directory for employee"""
        try:
            workspace_dir = self.project_root / "workspaces" / name
            workspace_dir.mkdir(parents=True, exist_ok=True)

            # Create basic workspace structure
            (workspace_dir / "tasks").mkdir(exist_ok=True)
            (workspace_dir / "logs").mkdir(exist_ok=True)

            logger.debug(f"Created workspace for employee: {name}")

        except Exception as e:
            logger.warning(f"Failed to create workspace for {name}: {e}")
            # Don't fail the hire process for workspace creation issues

    def employee_exists(self, name: str) -> bool:
        """Check if an employee exists with error handling"""
        try:
            if not name or not name.strip():
                return False

            query = "SELECT 1 FROM employees WHERE name = ? AND status = 'active'"
            result = self.db_manager.execute_with_retry(query, (name.strip(),))
            return len(result) > 0

        except Exception as e:
            logger.error(f"Error checking if employee {name} exists: {e}")
            return False

    def fire_employee(self, name: str, task_tracker=None) -> bool:
        """Fire an employee with comprehensive cleanup"""
        try:
            logger.info(f"Firing employee: {name}")

            if not name or not name.strip():
                logger.error("Employee name cannot be empty")
                return False

            name = name.strip()

            # Check if employee exists
            if not self.employee_exists(name):
                logger.info(f"Employee {name} does not exist or is already inactive")
                return False

            # Start transaction for atomic operation
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Release all locked files
                cursor.execute("""
                    UPDATE file_locks
                    SET status = 'released', released_at = CURRENT_TIMESTAMP
                    WHERE employee_name = ? AND status = 'locked'
                """, (name,))

                released_files = cursor.rowcount
                logger.info(f"Released {released_files} locked files for {name}")

                # Mark employee as inactive instead of deleting
                cursor.execute("""
                    UPDATE employees
                    SET status = 'inactive', updated_at = CURRENT_TIMESTAMP
                    WHERE name = ?
                """, (name,))

                # Deny all pending requests from this employee
                cursor.execute("""
                    UPDATE file_requests
                    SET status = 'denied', resolved_at = CURRENT_TIMESTAMP
                    WHERE requester = ? AND status = 'pending'
                """, (name,))

                denied_requests = cursor.rowcount
                logger.info(f"Denied {denied_requests} pending requests for {name}")

                conn.commit()

            # Clean up session data if task tracker is provided
            if task_tracker:
                try:
                    task_tracker.cleanup_employee_session(name)
                except Exception as e:
                    logger.warning(f"Failed to cleanup session for {name}: {e}")

            # Clean up workspace
            self._cleanup_employee_workspace(name)

            logger.info(f"Successfully fired employee: {name}")
            return True

        except DatabaseError as e:
            logger.error(f"Database error firing employee {name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error firing employee {name}: {e}")
            return False

    def _cleanup_employee_workspace(self, name: str):
        """Clean up employee workspace"""
        try:
            workspace_dir = self.project_root / "workspaces" / name
            if workspace_dir.exists():
                # Archive workspace instead of deleting
                archive_dir = self.project_root / "archived_workspaces"
                archive_dir.mkdir(exist_ok=True)

                archive_path = archive_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                workspace_dir.rename(archive_path)

                logger.info(f"Archived workspace for {name} to {archive_path}")

        except Exception as e:
            logger.warning(f"Failed to cleanup workspace for {name}: {e}")

    def lock_files(self, employee_name: str, file_paths: List[str], task_description: str) -> Dict[str, str]:
        """Lock files for an employee with comprehensive error handling"""
        try:
            logger.info(f"Employee {employee_name} attempting to lock files: {file_paths}")

            # Validate inputs
            if not employee_name or not employee_name.strip():
                raise ValueError("Employee name cannot be empty")

            if not file_paths:
                raise ValueError("File paths list cannot be empty")

            if not task_description or not task_description.strip():
                task_description = "No description provided"

            employee_name = employee_name.strip()
            task_description = task_description.strip()

            # Check if employee exists
            if not self.employee_exists(employee_name):
                raise ValueError(f"Employee {employee_name} does not exist")

            # Resolve and validate file paths
            resolved_paths = []
            validation_errors = []

            for file_path in file_paths:
                try:
                    resolved_path = self._resolve_and_validate_file_path(file_path)
                    resolved_paths.append((file_path, resolved_path))
                except Exception as e:
                    validation_errors.append(f"{file_path}: {e}")

            if validation_errors:
                logger.warning(f"File path validation errors: {validation_errors}")

            # Check disk space before locking
            if not self._check_disk_space():
                logger.warning("Low disk space detected during file locking")

            result = {}

            # Process each file with individual error handling
            for original_path, resolved_path in resolved_paths:
                try:
                    lock_result = self._lock_single_file(
                        employee_name, original_path, resolved_path, task_description
                    )
                    result[original_path] = lock_result

                except Exception as e:
                    logger.error(f"Failed to lock file {original_path}: {e}")
                    result[original_path] = f"error: {e}"

            # Add validation errors to result
            for error in validation_errors:
                file_path = error.split(":")[0]
                result[file_path] = f"validation_error: {error}"

            logger.info(f"File locking completed for {employee_name}: {result}")
            return result

        except ValueError as e:
            logger.error(f"Invalid input for file locking: {e}")
            return {path: f"input_error: {e}" for path in file_paths}
        except Exception as e:
            logger.error(f"Unexpected error in file locking: {e}")
            return {path: f"system_error: {e}" for path in file_paths}

    def _resolve_and_validate_file_path(self, file_path: str) -> str:
        """Resolve and validate a file path"""
        if not file_path or not file_path.strip():
            raise ValueError("File path cannot be empty")

        file_path = file_path.strip()

        # Resolve path relative to project root
        if os.path.isabs(file_path):
            resolved_path = Path(file_path)
        else:
            resolved_path = self.project_root / file_path

        resolved_path = resolved_path.resolve()

        # Security check: ensure path is within project root
        try:
            resolved_path.relative_to(self.project_root)
        except ValueError:
            raise ValueError(f"File path outside project root: {file_path}")

        # Check if parent directory exists
        if not resolved_path.parent.exists():
            logger.warning(f"Parent directory does not exist: {resolved_path.parent}")
            # Create parent directory if possible
            try:
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created parent directory: {resolved_path.parent}")
            except Exception as e:
                raise ValueError(f"Cannot create parent directory: {e}")

        return str(resolved_path)

    def _lock_single_file(self, employee_name: str, original_path: str,
                         resolved_path: str, task_description: str) -> str:
        """Lock a single file with error handling"""
        try:
            # Check if file is already locked
            query = """
                SELECT employee_name FROM file_locks
                WHERE file_path = ? AND status = 'locked'
            """
            result = self.db_manager.execute_with_retry(query, (resolved_path,))

            if result:
                locked_by = result[0][0]
                if locked_by == employee_name:
                    return "already_locked"
                else:
                    return f"locked_by_{locked_by}"

            # Lock the file
            lock_query = """
                INSERT INTO file_locks (file_path, employee_name, task_description, metadata)
                VALUES (?, ?, ?, ?)
            """
            metadata = json.dumps({
                'original_path': original_path,
                'lock_reason': 'task_assignment',
                'lock_timestamp': datetime.now().isoformat()
            })

            rows_affected = self.db_manager.execute_with_retry(
                lock_query, (resolved_path, employee_name, task_description, metadata)
            )

            if rows_affected > 0:
                logger.info(f"File {resolved_path} locked by {employee_name}")
                return "locked"
            else:
                return "lock_failed"

        except DatabaseError as e:
            logger.error(f"Database error locking file {resolved_path}: {e}")
            return f"database_error: {e}"
        except Exception as e:
            logger.error(f"Unexpected error locking file {resolved_path}: {e}")
            return f"error: {e}"

    def release_files(self, employee_name: str, file_paths: List[str] = None) -> List[str]:
        """Release files with comprehensive error handling"""
        try:
            logger.info(f"Employee {employee_name} attempting to release files: {file_paths}")

            if not employee_name or not employee_name.strip():
                logger.error("Employee name cannot be empty")
                return []

            employee_name = employee_name.strip()

            if file_paths is None:
                # Release all files for this employee
                return self._release_all_files(employee_name)
            else:
                # Release specific files
                return self._release_specific_files(employee_name, file_paths)

        except Exception as e:
            logger.error(f"Unexpected error releasing files for {employee_name}: {e}")
            return []

    def _release_all_files(self, employee_name: str) -> List[str]:
        """Release all files for an employee"""
        try:
            query = """
                UPDATE file_locks
                SET status = 'released', released_at = CURRENT_TIMESTAMP
                WHERE employee_name = ? AND status = 'locked'
            """

            rows_affected = self.db_manager.execute_with_retry(query, (employee_name,))

            if rows_affected > 0:
                logger.info(f"Released all {rows_affected} files for {employee_name}")

            return []  # Return empty list as we don't track specific files

        except Exception as e:
            logger.error(f"Error releasing all files for {employee_name}: {e}")
            return []

    def _release_specific_files(self, employee_name: str, file_paths: List[str]) -> List[str]:
        """Release specific files for an employee"""
        released = []

        for file_path in file_paths:
            try:
                resolved_path = self._resolve_and_validate_file_path(file_path)

                query = """
                    UPDATE file_locks
                    SET status = 'released', released_at = CURRENT_TIMESTAMP
                    WHERE file_path = ? AND employee_name = ? AND status = 'locked'
                """

                rows_affected = self.db_manager.execute_with_retry(
                    query, (resolved_path, employee_name)
                )

                if rows_affected > 0:
                    released.append(file_path)
                    logger.info(f"Released file {resolved_path} for {employee_name}")
                else:
                    logger.warning(f"File {file_path} was not locked by {employee_name}")

            except Exception as e:
                logger.error(f"Error releasing file {file_path} for {employee_name}: {e}")

        return released

    def get_file_owner(self, file_path: str) -> Optional[str]:
        """Get the owner of a locked file with error handling"""
        try:
            if not file_path or not file_path.strip():
                return None

            resolved_path = self._resolve_and_validate_file_path(file_path)

            query = """
                SELECT employee_name FROM file_locks
                WHERE file_path = ? AND status = 'locked'
            """

            result = self.db_manager.execute_with_retry(query, (resolved_path,))

            if result:
                return result[0][0]

            return None

        except Exception as e:
            logger.error(f"Error getting file owner for {file_path}: {e}")
            return None

    def list_employees(self) -> List[Dict]:
        """List all active employees with error handling"""
        try:
            query = """
                SELECT name, role, smartness, hired_at, status, metadata
                FROM employees
                WHERE status = 'active'
                ORDER BY name
            """

            result = self.db_manager.execute_with_retry(query)

            employees = []
            for row in result:
                try:
                    metadata = json.loads(row[5]) if row[5] else {}
                except json.JSONDecodeError:
                    metadata = {}

                employees.append({
                    'name': row[0],
                    'role': row[1],
                    'smartness': row[2],
                    'hired_at': row[3],
                    'status': row[4],
                    'metadata': metadata
                })

            return employees

        except Exception as e:
            logger.error(f"Error listing employees: {e}")
            return []

    def get_all_locked_files(self) -> List[Dict]:
        """Get all currently locked files with error handling"""
        try:
            query = """
                SELECT file_path, employee_name, task_description, locked_at, metadata
                FROM file_locks
                WHERE status = 'locked'
                ORDER BY locked_at DESC
            """

            result = self.db_manager.execute_with_retry(query)

            files = []
            for row in result:
                try:
                    file_path = row[0]
                    # Convert to relative path for display
                    try:
                        relative_path = os.path.relpath(file_path, self.project_root)
                    except ValueError:
                        relative_path = file_path

                    metadata = json.loads(row[4]) if row[4] else {}

                    files.append({
                        'file_path': relative_path,
                        'employee_name': row[1],
                        'task_description': row[2],
                        'locked_at': row[3],
                        'metadata': metadata
                    })

                except Exception as e:
                    logger.warning(f"Error processing locked file record: {e}")
                    continue

            return files

        except Exception as e:
            logger.error(f"Error getting locked files: {e}")
            return []

    def get_system_health(self) -> Dict:
        """Get comprehensive system health information"""
        try:
            health_info = {
                'database': self.db_manager.get_health_status(),
                'file_system': self._get_file_system_health(),
                'project_root': str(self.project_root),
                'last_checked': datetime.now().isoformat()
            }

            # Determine overall health status
            db_healthy = health_info['database'].get('status') == 'healthy'
            fs_healthy = health_info['file_system'].get('status') == 'healthy'

            if db_healthy and fs_healthy:
                health_info['overall_status'] = 'healthy'
            elif db_healthy or fs_healthy:
                health_info['overall_status'] = 'degraded'
            else:
                health_info['overall_status'] = 'failed'

            return health_info

        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                'overall_status': 'failed',
                'error': str(e),
                'last_checked': datetime.now().isoformat()
            }

    def _get_file_system_health(self) -> Dict:
        """Get file system health information"""
        try:
            # Check project root accessibility
            root_accessible = self.project_root.exists() and os.access(self.project_root, os.R_OK | os.W_OK)

            # Check disk space
            disk_space_ok = self._check_disk_space()

            # Get disk usage statistics
            stat = os.statvfs(self.project_root)
            total_bytes = stat.f_blocks * stat.f_frsize
            free_bytes = stat.f_bavail * stat.f_frsize
            used_bytes = total_bytes - free_bytes

            status = 'healthy'
            if not root_accessible:
                status = 'failed'
            elif not disk_space_ok:
                status = 'degraded'

            return {
                'status': status,
                'project_root_accessible': root_accessible,
                'disk_space_ok': disk_space_ok,
                'disk_usage': {
                    'total_mb': total_bytes / (1024 * 1024),
                    'used_mb': used_bytes / (1024 * 1024),
                    'free_mb': free_bytes / (1024 * 1024),
                    'usage_percent': (used_bytes / total_bytes) * 100
                }
            }

        except Exception as e:
            logger.error(f"File system health check failed: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }

    def create_backup(self) -> bool:
        """Create a backup of the database"""
        try:
            backup_path = self.db_manager.create_backup()
            logger.info(f"Database backup created: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False

    def vacuum_database(self) -> bool:
        """Vacuum the database to optimize performance"""
        try:
            self.db_manager.vacuum_database()
            return True
        except Exception as e:
            logger.error(f"Database vacuum failed: {e}")
            return False

    def close(self):
        """Close the file ownership manager"""
        try:
            self.db_manager.close()
            logger.info("Enhanced FileOwnershipManager closed")
        except Exception as e:
            logger.error(f"Error closing FileOwnershipManager: {e}")

    # Legacy compatibility methods
    def get_employee_info(self, employee_name: str) -> Optional[Dict]:
        """Get employee information (legacy compatibility)"""
        try:
            employees = self.list_employees()
            for emp in employees:
                if emp['name'] == employee_name:
                    return {
                        'name': emp['name'],
                        'role': emp['role'],
                        'smartness': emp['smartness'],
                        'hired_at': emp['hired_at']
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting employee info for {employee_name}: {e}")
            return None

    def set_project_root(self, project_root: str) -> bool:
        """Set the project root directory (legacy compatibility)"""
        try:
            root_path = Path(project_root).resolve()
            root_path.mkdir(parents=True, exist_ok=True)

            self.project_root = root_path
            os.environ['PROJECT_ROOT'] = str(root_path)

            logger.info(f"Project root updated to: {root_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to set project root: {e}")
            return False

    def get_project_root(self) -> str:
        """Get the current project root directory (legacy compatibility)"""
        return str(self.project_root)