#!/usr/bin/env python3
"""
Enhanced Database Manager with comprehensive error handling and resilience features.
Provides database initialization, migration, backup, recovery, and connection pooling.
"""

import sqlite3
import os
import shutil
import time
import threading
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from contextlib import contextmanager
import json
import hashlib

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database-related errors"""
    pass


class DatabaseCorruptionError(DatabaseError):
    """Exception raised when database corruption is detected"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails"""
    pass


class DatabaseMigrationError(DatabaseError):
    """Exception raised when database migration fails"""
    pass


class ConnectionPool:
    """Thread-safe connection pool for SQLite database"""
    
    def __init__(self, db_path: str, max_connections: int = 10, timeout: float = 30.0):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool = []
        self._pool_lock = threading.Lock()
        self._active_connections = 0
        
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool"""
        conn = None
        try:
            conn = self._acquire_connection()
            yield conn
        finally:
            if conn:
                self._release_connection(conn)
    
    def _acquire_connection(self) -> sqlite3.Connection:
        """Acquire a connection from the pool"""
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            with self._pool_lock:
                if self._pool:
                    return self._pool.pop()
                elif self._active_connections < self.max_connections:
                    try:
                        conn = sqlite3.connect(
                            self.db_path,
                            timeout=self.timeout,
                            check_same_thread=False
                        )
                        # Test the connection with a simple query first
                        conn.execute("SELECT 1")
                        
                        # Configure connection if it's working
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute("PRAGMA synchronous=NORMAL")
                        conn.execute("PRAGMA cache_size=10000")
                        conn.execute("PRAGMA temp_store=MEMORY")
                        self._active_connections += 1
                        return conn
                    except sqlite3.DatabaseError as e:
                        logger.error(f"Failed to create database connection: {e}")
                        raise DatabaseCorruptionError(f"Database corruption detected: {e}")
                    except sqlite3.Error as e:
                        logger.error(f"Failed to create database connection: {e}")
                        raise DatabaseConnectionError(f"Failed to create connection: {e}")
            
            time.sleep(0.1)  # Wait before retrying
        
        raise DatabaseConnectionError("Connection pool timeout")
    
    def _release_connection(self, conn: sqlite3.Connection):
        """Release a connection back to the pool"""
        try:
            # Rollback any uncommitted transactions
            conn.rollback()
            
            with self._pool_lock:
                if len(self._pool) < self.max_connections:
                    self._pool.append(conn)
                else:
                    conn.close()
                    self._active_connections -= 1
        except sqlite3.Error as e:
            logger.warning(f"Error releasing connection: {e}")
            with self._pool_lock:
                self._active_connections -= 1
    
    def close_all(self):
        """Close all connections in the pool"""
        with self._pool_lock:
            for conn in self._pool:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            self._pool.clear()
            self._active_connections = 0


class DatabaseManager:
    """Enhanced database manager with comprehensive error handling and resilience"""
    
    # Database schema version
    SCHEMA_VERSION = 1
    
    # Schema definitions
    SCHEMA_DEFINITIONS = {
        1: {
            'employees': '''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL,
                    smartness TEXT DEFAULT 'normal' CHECK (smartness IN ('smart', 'normal')),
                    hired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'file_locks': '''
                CREATE TABLE IF NOT EXISTS file_locks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    employee_name TEXT NOT NULL,
                    task_description TEXT,
                    status TEXT DEFAULT 'locked' CHECK (status IN ('locked', 'released', 'requested')),
                    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    released_at TIMESTAMP NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (employee_name) REFERENCES employees (name) ON DELETE CASCADE
                )
            ''',
            'file_requests': '''
                CREATE TABLE IF NOT EXISTS file_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    requester TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'denied', 'expired')),
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (requester) REFERENCES employees (name) ON DELETE CASCADE,
                    FOREIGN KEY (owner) REFERENCES employees (name) ON DELETE CASCADE
                )
            ''',
            'schema_migrations': '''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    checksum TEXT
                )
            ''',
            'system_health': '''
                CREATE TABLE IF NOT EXISTS system_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('healthy', 'degraded', 'failed')),
                    message TEXT,
                    details TEXT DEFAULT '{}',
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
        }
    }
    
    # Index definitions
    INDEX_DEFINITIONS = {
        1: [
            'CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(name)',
            'CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role)',
            'CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status)',
            'CREATE INDEX IF NOT EXISTS idx_file_locks_path ON file_locks(file_path)',
            'CREATE INDEX IF NOT EXISTS idx_file_locks_employee ON file_locks(employee_name)',
            'CREATE INDEX IF NOT EXISTS idx_file_locks_status ON file_locks(status)',
            'CREATE INDEX IF NOT EXISTS idx_file_requests_file ON file_requests(file_path)',
            'CREATE INDEX IF NOT EXISTS idx_file_requests_status ON file_requests(status)',
            'CREATE INDEX IF NOT EXISTS idx_file_requests_requester ON file_requests(requester)',
            'CREATE INDEX IF NOT EXISTS idx_file_requests_owner ON file_requests(owner)',
            'CREATE INDEX IF NOT EXISTS idx_system_health_component ON system_health(component)',
            'CREATE INDEX IF NOT EXISTS idx_system_health_status ON system_health(status)',
            'CREATE INDEX IF NOT EXISTS idx_system_health_recorded_at ON system_health(recorded_at)'
        ]
    }
    
    def __init__(self, db_path: str, backup_dir: Optional[str] = None, 
                 max_connections: int = 10, auto_backup: bool = True):
        self.db_path = Path(db_path).resolve()
        self.backup_dir = Path(backup_dir or self.db_path.parent / "backups")
        self.auto_backup = auto_backup
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize connection pool
        self.connection_pool = ConnectionPool(str(self.db_path), max_connections)
        
        # Initialize database
        self._initialize_database()
        
        logger.info(f"DatabaseManager initialized: {self.db_path}")
    
    def _initialize_database(self):
        """Initialize database with proper error handling and recovery"""
        try:
            # Check if database file exists and is valid
            if self.db_path.exists():
                if not self._validate_database():
                    logger.warning("Database validation failed, attempting recovery")
                    if not self._recover_database():
                        logger.error("Database recovery failed, creating new database")
                        self._create_new_database()
                else:
                    logger.info("Database validation successful")
            else:
                logger.info("Database file not found, creating new database")
                self._create_new_database()
            
            # Run migrations
            self._run_migrations()
            
            # Create indexes
            self._create_indexes()
            
            # Record successful initialization
            try:
                self._record_health_status("database", "healthy", "Database initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to record health status: {e}")
            
        except DatabaseCorruptionError as e:
            logger.error(f"Database corruption detected: {e}")
            try:
                self._create_new_database()
                self._run_migrations()
                self._create_indexes()
                logger.info("Successfully created new database after corruption")
            except Exception as recovery_error:
                logger.error(f"Failed to create new database after corruption: {recovery_error}")
                raise DatabaseError(f"Failed to initialize database after corruption: {recovery_error}")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            try:
                self._record_health_status("database", "failed", f"Initialization failed: {e}")
            except Exception:
                pass  # Don't fail if we can't record health status
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    def _validate_database(self) -> bool:
        """Validate database integrity"""
        try:
            # First check if file exists and is not empty
            if not self.db_path.exists():
                logger.error("Database file does not exist")
                return False
            
            if self.db_path.stat().st_size == 0:
                logger.error("Database file is empty")
                return False
            
            # Try to open with basic sqlite3 connection first
            try:
                test_conn = sqlite3.connect(str(self.db_path), timeout=5)
                test_cursor = test_conn.cursor()
                
                # Check database integrity
                test_cursor.execute("PRAGMA integrity_check")
                result = test_cursor.fetchone()
                if result[0] != "ok":
                    logger.error(f"Database integrity check failed: {result[0]}")
                    test_conn.close()
                    return False
                
                # Check if required tables exist
                test_cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('employees', 'file_locks', 'file_requests')
                """)
                tables = [row[0] for row in test_cursor.fetchall()]
                required_tables = ['employees', 'file_locks', 'file_requests']
                
                test_conn.close()
                
                if not all(table in tables for table in required_tables):
                    logger.error(f"Missing required tables. Found: {tables}, Required: {required_tables}")
                    return False
                
                return True
                
            except sqlite3.DatabaseError as e:
                logger.error(f"Database file is corrupted: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Database validation error: {e}")
            return False
    
    def _recover_database(self) -> bool:
        """Attempt to recover corrupted database"""
        try:
            logger.info("Attempting database recovery")
            
            # Create backup of corrupted database
            corrupted_backup = self.backup_dir / f"corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            try:
                shutil.copy2(self.db_path, corrupted_backup)
                logger.info(f"Corrupted database backed up to: {corrupted_backup}")
            except Exception as e:
                logger.warning(f"Failed to backup corrupted database: {e}")
            
            # For severely corrupted databases, just recreate
            try:
                # Remove corrupted database
                if self.db_path.exists():
                    self.db_path.unlink()
                
                # Create new database
                self._create_new_database()
                
                logger.info("Database recovery successful - created new database")
                return True
                
            except Exception as e:
                logger.error(f"Database recovery process failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Database recovery failed: {e}")
            return False
    
    def _create_new_database(self):
        """Create a new database with proper schema"""
        try:
            # Remove existing file if it exists
            if self.db_path.exists():
                backup_path = self.backup_dir / f"replaced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.move(self.db_path, backup_path)
                logger.info(f"Existing database moved to: {backup_path}")
            
            # Create new database
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create all tables for current schema version
                for table_name, table_sql in self.SCHEMA_DEFINITIONS[self.SCHEMA_VERSION].items():
                    cursor.execute(table_sql)
                
                conn.commit()
                logger.info("New database created successfully")
                
        except Exception as e:
            logger.error(f"Failed to create new database: {e}")
            raise DatabaseError(f"Failed to create new database: {e}")
    
    def _run_migrations(self):
        """Run database migrations"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current schema version
                try:
                    cursor.execute("SELECT MAX(version) FROM schema_migrations")
                    result = cursor.fetchone()
                    current_version = result[0] if result[0] is not None else 0
                except sqlite3.OperationalError:
                    # schema_migrations table doesn't exist
                    current_version = 0
                
                # Run migrations for versions higher than current
                for version in range(current_version + 1, self.SCHEMA_VERSION + 1):
                    logger.info(f"Running migration to version {version}")
                    
                    # Create tables for this version
                    if version in self.SCHEMA_DEFINITIONS:
                        for table_name, table_sql in self.SCHEMA_DEFINITIONS[version].items():
                            cursor.execute(table_sql)
                    
                    # Record migration
                    migration_checksum = self._calculate_schema_checksum(version)
                    cursor.execute("""
                        INSERT INTO schema_migrations (version, description, checksum)
                        VALUES (?, ?, ?)
                    """, (version, f"Migration to version {version}", migration_checksum))
                
                conn.commit()
                logger.info(f"Migrations completed. Current version: {self.SCHEMA_VERSION}")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise DatabaseMigrationError(f"Migration failed: {e}")
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create indexes for current schema version
                if self.SCHEMA_VERSION in self.INDEX_DEFINITIONS:
                    for index_sql in self.INDEX_DEFINITIONS[self.SCHEMA_VERSION]:
                        cursor.execute(index_sql)
                
                conn.commit()
                logger.info("Database indexes created successfully")
                
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            # Don't raise exception for index creation failures
    
    def _calculate_schema_checksum(self, version: int) -> str:
        """Calculate checksum for schema version"""
        schema_content = ""
        if version in self.SCHEMA_DEFINITIONS:
            for table_sql in self.SCHEMA_DEFINITIONS[version].values():
                schema_content += table_sql
        
        return hashlib.md5(schema_content.encode()).hexdigest()
    
    def _record_health_status(self, component: str, status: str, message: str, details: Dict = None):
        """Record system health status"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO system_health (component, status, message, details)
                    VALUES (?, ?, ?, ?)
                """, (component, status, message, json.dumps(details or {})))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to record health status: {e}")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic transaction handling"""
        with self.connection_pool.get_connection() as conn:
            try:
                yield conn
            except Exception as e:
                conn.rollback()
                logger.error(f"Database transaction failed: {e}")
                raise
    
    def execute_with_retry(self, query: str, params: tuple = (), max_retries: int = 3) -> Any:
        """Execute query with retry logic for transient failures"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    
                    if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                        conn.commit()
                        return cursor.rowcount
                    else:
                        return cursor.fetchall()
                        
            except sqlite3.OperationalError as e:
                last_exception = e
                if "database is locked" in str(e).lower():
                    logger.warning(f"Database locked, retrying ({attempt + 1}/{max_retries})")
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
            except Exception as e:
                last_exception = e
                logger.error(f"Query execution failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.1 * (attempt + 1))
        
        raise last_exception
    
    def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """Create database backup"""
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            backup_path = self.backup_dir / backup_name
            
            # Use SQLite backup API for consistent backup
            with sqlite3.connect(str(self.db_path)) as source:
                with sqlite3.connect(str(backup_path)) as backup:
                    source.backup(backup)
            
            logger.info(f"Database backup created: {backup_path}")
            
            # Clean up old backups (keep last 10)
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise DatabaseError(f"Backup creation failed: {e}")
    
    def restore_backup(self, backup_path: Path) -> bool:
        """Restore database from backup"""
        try:
            if not backup_path.exists():
                raise DatabaseError(f"Backup file not found: {backup_path}")
            
            # Validate backup before restoring
            temp_conn = sqlite3.connect(str(backup_path))
            cursor = temp_conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            temp_conn.close()
            
            if result[0] != "ok":
                raise DatabaseError(f"Backup file is corrupted: {result[0]}")
            
            # Create backup of current database
            current_backup = self.create_backup(f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # Close all connections
            self.connection_pool.close_all()
            
            # Replace current database with backup
            shutil.copy2(backup_path, self.db_path)
            
            # Reinitialize connection pool
            self.connection_pool = ConnectionPool(str(self.db_path))
            
            # Validate restored database
            if self._validate_database():
                logger.info(f"Database restored from backup: {backup_path}")
                self._record_health_status("database", "healthy", f"Restored from backup: {backup_path}")
                return True
            else:
                # Restore failed, revert to previous backup
                shutil.copy2(current_backup, self.db_path)
                self.connection_pool = ConnectionPool(str(self.db_path))
                raise DatabaseError("Restored database validation failed")
                
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            self._record_health_status("database", "failed", f"Restore failed: {e}")
            return False
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """Clean up old backup files"""
        try:
            backup_files = list(self.backup_dir.glob("backup_*.db"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for backup_file in backup_files[keep_count:]:
                backup_file.unlink()
                logger.debug(f"Removed old backup: {backup_file}")
                
        except Exception as e:
            logger.warning(f"Backup cleanup failed: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive database health status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get database size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                # Get table counts
                table_counts = {}
                for table in ['employees', 'file_locks', 'file_requests']:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = cursor.fetchone()[0]
                
                # Get recent health records
                cursor.execute("""
                    SELECT component, status, message, recorded_at
                    FROM system_health
                    ORDER BY recorded_at DESC
                    LIMIT 10
                """)
                recent_health = [
                    {
                        'component': row[0],
                        'status': row[1],
                        'message': row[2],
                        'recorded_at': row[3]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Get schema version
                cursor.execute("SELECT MAX(version) FROM schema_migrations")
                schema_version = cursor.fetchone()[0] or 0
                
                return {
                    'status': 'healthy',
                    'db_path': str(self.db_path),
                    'db_size_bytes': db_size,
                    'schema_version': schema_version,
                    'table_counts': table_counts,
                    'connection_pool_active': self.connection_pool._active_connections,
                    'recent_health': recent_health,
                    'backup_dir': str(self.backup_dir),
                    'last_checked': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Health status check failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'last_checked': datetime.now().isoformat()
            }
    
    def vacuum_database(self):
        """Vacuum database to reclaim space and optimize performance"""
        try:
            logger.info("Starting database vacuum operation")
            
            with self.get_connection() as conn:
                # Get database size before vacuum
                cursor = conn.cursor()
                cursor.execute("PRAGMA page_count")
                pages_before = cursor.fetchone()[0]
                
                # Perform vacuum
                conn.execute("VACUUM")
                
                # Get database size after vacuum
                cursor.execute("PRAGMA page_count")
                pages_after = cursor.fetchone()[0]
                
                pages_freed = pages_before - pages_after
                logger.info(f"Database vacuum completed. Pages freed: {pages_freed}")
                
                self._record_health_status(
                    "database", "healthy", 
                    f"Vacuum completed, freed {pages_freed} pages"
                )
                
        except Exception as e:
            logger.error(f"Database vacuum failed: {e}")
            self._record_health_status("database", "degraded", f"Vacuum failed: {e}")
    
    def close(self):
        """Close database manager and all connections"""
        try:
            self.connection_pool.close_all()
            logger.info("Database manager closed")
        except Exception as e:
            logger.error(f"Error closing database manager: {e}")