# SPDX-License-Identifier: MIT
"""
Security audit logging system for WebSocket communications.
Provides comprehensive logging, monitoring, and alerting for security events.
"""

import asyncio
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import hashlib
import gzip

from ..config.secure_config import get_config

logger = logging.getLogger(__name__)

class SecurityEventLevel(Enum):
    """Security event severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class SecurityAuditLogger:
    """
    Comprehensive security audit logging system with:
    - Structured logging for security events
    - Real-time monitoring and alerting
    - Log rotation and compression
    - Compliance reporting
    - Anomaly detection
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        
        # Logging configuration
        self.log_dir = Path(self.config.get('SECURITY_LOG_DIR', 'logs/security'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_log_size = self.config.get_int('MAX_SECURITY_LOG_SIZE', 100 * 1024 * 1024)  # 100MB
        self.max_log_files = self.config.get_int('MAX_SECURITY_LOG_FILES', 10)
        self.log_rotation_interval = self.config.get_int('LOG_ROTATION_HOURS', 24)
        
        # Initialize log files
        self.audit_log_file = self.log_dir / 'security_audit.log'
        self.alert_log_file = self.log_dir / 'security_alerts.log'
        self.compliance_log_file = self.log_dir / 'compliance.log'
        
        # Event tracking
        self.event_buffer: deque = deque(maxlen=10000)
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.ip_events: Dict[str, List[Dict]] = defaultdict(list)
        self.user_events: Dict[str, List[Dict]] = defaultdict(list)
        
        # Anomaly detection
        self.baseline_metrics = {
            'auth_failures_per_hour': 10,
            'rate_limit_violations_per_hour': 50,
            'invalid_messages_per_hour': 20,
            'new_ips_per_hour': 100
        }
        
        self.anomaly_thresholds = {
            'auth_failures': 50,  # per hour
            'rate_limit_violations': 200,
            'invalid_messages': 100,
            'suspicious_patterns': 20
        }
        
        # Alert configuration
        self.alert_cooldown = {}  # Prevent spam alerts
        self.alert_cooldown_period = 300  # 5 minutes
        
        # Compliance tracking
        self.compliance_events = {
            'data_access', 'data_modification', 'admin_actions',
            'authentication', 'authorization_failures', 'system_changes'
        }
        
        # Background tasks
        self.cleanup_task = None
        self.monitoring_task = None
        self.is_running = False
        
        # Thread safety
        self.lock = threading.RLock()
        
        self._setup_logging()
        self._start_background_tasks()
        
        logger.info("Security audit logger initialized")
    
    def log_security_event(self, event_type: str, source_ip: str, details: Dict = None,
                          level: SecurityEventLevel = SecurityEventLevel.INFO,
                          user_id: str = None):
        """
        Log a security event with comprehensive metadata.
        
        Args:
            event_type: Type of security event
            source_ip: Source IP address
            details: Additional event details
            level: Event severity level
            user_id: Associated user ID if applicable
        """
        with self.lock:
            timestamp = datetime.utcnow()
            
            # Create event record
            event = {
                'timestamp': timestamp.isoformat(),
                'event_type': event_type,
                'level': level.value,
                'source_ip': source_ip,
                'user_id': user_id,
                'details': details or {},
                'event_id': self._generate_event_id(event_type, timestamp),
                'session_id': details.get('session_id') if details else None
            }
            
            # Add to buffer
            self.event_buffer.append(event)
            
            # Update counters
            self.event_counts[event_type] += 1
            
            # Track by IP and user
            self.ip_events[source_ip].append({
                'timestamp': timestamp,
                'event_type': event_type,
                'level': level.value
            })
            
            if user_id:
                self.user_events[user_id].append({
                    'timestamp': timestamp,
                    'event_type': event_type,
                    'level': level.value,
                    'source_ip': source_ip
                })
            
            # Write to audit log
            self._write_audit_log(event)
            
            # Check for compliance events
            if event_type in self.compliance_events:
                self._write_compliance_log(event)
            
            # Check for alerts
            if level in [SecurityEventLevel.CRITICAL, SecurityEventLevel.EMERGENCY]:
                self._trigger_alert(event)
            
            # Anomaly detection
            self._check_anomalies(event_type, source_ip, user_id)
    
    def log_authentication_event(self, success: bool, user_id: str, source_ip: str,
                                method: str, details: Dict = None):
        """Log authentication events"""
        event_type = 'auth_success' if success else 'auth_failure'
        level = SecurityEventLevel.INFO if success else SecurityEventLevel.WARNING
        
        auth_details = {
            'method': method,
            'success': success,
            **(details or {})
        }
        
        self.log_security_event(event_type, source_ip, auth_details, level, user_id)
    
    def log_authorization_event(self, success: bool, user_id: str, source_ip: str,
                               resource: str, action: str, details: Dict = None):
        """Log authorization events"""
        event_type = 'authz_success' if success else 'authz_failure'
        level = SecurityEventLevel.INFO if success else SecurityEventLevel.WARNING
        
        authz_details = {
            'resource': resource,
            'action': action,
            'success': success,
            **(details or {})
        }
        
        self.log_security_event(event_type, source_ip, authz_details, level, user_id)
    
    def log_data_access(self, user_id: str, source_ip: str, resource: str,
                       action: str, details: Dict = None):
        """Log data access for compliance"""
        access_details = {
            'resource': resource,
            'action': action,
            'compliance_event': True,
            **(details or {})
        }
        
        self.log_security_event('data_access', source_ip, access_details,
                               SecurityEventLevel.INFO, user_id)
    
    def log_admin_action(self, user_id: str, source_ip: str, action: str,
                        target: str = None, details: Dict = None):
        """Log administrative actions"""
        admin_details = {
            'action': action,
            'target': target,
            'compliance_event': True,
            **(details or {})
        }
        
        self.log_security_event('admin_action', source_ip, admin_details,
                               SecurityEventLevel.WARNING, user_id)
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security event summary for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_events = [
            event for event in self.event_buffer
            if datetime.fromisoformat(event['timestamp']) > cutoff_time
        ]
        
        # Count events by type
        event_type_counts = defaultdict(int)
        level_counts = defaultdict(int)
        ip_counts = defaultdict(int)
        user_counts = defaultdict(int)
        
        for event in recent_events:
            event_type_counts[event['event_type']] += 1
            level_counts[event['level']] += 1
            ip_counts[event['source_ip']] += 1
            if event['user_id']:
                user_counts[event['user_id']] += 1
        
        # Top offenders
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'time_period_hours': hours,
            'total_events': len(recent_events),
            'events_by_type': dict(event_type_counts),
            'events_by_level': dict(level_counts),
            'top_source_ips': top_ips,
            'top_users': top_users,
            'unique_ips': len(ip_counts),
            'unique_users': len(user_counts)
        }
    
    def get_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report for date range"""
        compliance_events = [
            event for event in self.event_buffer
            if (start_date <= datetime.fromisoformat(event['timestamp']) <= end_date and
                event['details'].get('compliance_event', False))
        ]
        
        # Group by event type
        events_by_type = defaultdict(list)
        for event in compliance_events:
            events_by_type[event['event_type']].append(event)
        
        # User activity summary
        user_activity = defaultdict(lambda: {
            'data_access_count': 0,
            'admin_actions': 0,
            'auth_events': 0,
            'first_activity': None,
            'last_activity': None
        })
        
        for event in compliance_events:
            user_id = event.get('user_id')
            if user_id:
                activity = user_activity[user_id]
                timestamp = datetime.fromisoformat(event['timestamp'])
                
                if event['event_type'] == 'data_access':
                    activity['data_access_count'] += 1
                elif event['event_type'] == 'admin_action':
                    activity['admin_actions'] += 1
                elif 'auth' in event['event_type']:
                    activity['auth_events'] += 1
                
                if not activity['first_activity'] or timestamp < activity['first_activity']:
                    activity['first_activity'] = timestamp
                if not activity['last_activity'] or timestamp > activity['last_activity']:
                    activity['last_activity'] = timestamp
        
        return {
            'report_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_compliance_events': len(compliance_events),
            'events_by_type': {k: len(v) for k, v in events_by_type.items()},
            'user_activity': {
                user_id: {
                    **activity,
                    'first_activity': activity['first_activity'].isoformat() if activity['first_activity'] else None,
                    'last_activity': activity['last_activity'].isoformat() if activity['last_activity'] else None
                }
                for user_id, activity in user_activity.items()
            },
            'unique_users': len(user_activity)
        }
    
    def search_events(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict]:
        """Search security events with filters"""
        results = []
        
        for event in reversed(self.event_buffer):  # Most recent first
            if len(results) >= limit:
                break
            
            # Apply filters
            match = True
            
            if 'event_type' in filters and event['event_type'] != filters['event_type']:
                match = False
            
            if 'level' in filters and event['level'] != filters['level']:
                match = False
            
            if 'source_ip' in filters and event['source_ip'] != filters['source_ip']:
                match = False
            
            if 'user_id' in filters and event['user_id'] != filters['user_id']:
                match = False
            
            if 'start_time' in filters:
                event_time = datetime.fromisoformat(event['timestamp'])
                if event_time < filters['start_time']:
                    match = False
            
            if 'end_time' in filters:
                event_time = datetime.fromisoformat(event['timestamp'])
                if event_time > filters['end_time']:
                    match = False
            
            if match:
                results.append(event)
        
        return results
    
    def _setup_logging(self):
        """Setup structured logging"""
        # Create formatters
        audit_formatter = logging.Formatter(
            '%(asctime)s - SECURITY_AUDIT - %(levelname)s - %(message)s'
        )
        
        # Setup audit log handler
        audit_handler = logging.FileHandler(self.audit_log_file)
        audit_handler.setFormatter(audit_formatter)
        audit_handler.setLevel(logging.INFO)
        
        # Create security logger
        self.security_logger = logging.getLogger('security_audit')
        self.security_logger.setLevel(logging.INFO)
        self.security_logger.addHandler(audit_handler)
        self.security_logger.propagate = False
    
    def _write_audit_log(self, event: Dict):
        """Write event to audit log"""
        try:
            log_entry = json.dumps(event, separators=(',', ':'))
            self.security_logger.info(log_entry)
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def _write_compliance_log(self, event: Dict):
        """Write compliance event to separate log"""
        try:
            with open(self.compliance_log_file, 'a') as f:
                log_entry = json.dumps(event, separators=(',', ':'))
                f.write(f"{log_entry}\n")
        except Exception as e:
            logger.error(f"Failed to write compliance log: {e}")
    
    def _trigger_alert(self, event: Dict):
        """Trigger security alert"""
        alert_key = f"{event['event_type']}:{event['source_ip']}"
        current_time = time.time()
        
        # Check cooldown
        if (alert_key in self.alert_cooldown and
            current_time - self.alert_cooldown[alert_key] < self.alert_cooldown_period):
            return
        
        self.alert_cooldown[alert_key] = current_time
        
        # Create alert
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'alert_type': 'security_event',
            'severity': event['level'],
            'event': event,
            'alert_id': self._generate_event_id('alert', datetime.utcnow())
        }
        
        # Write to alert log
        try:
            with open(self.alert_log_file, 'a') as f:
                alert_entry = json.dumps(alert, separators=(',', ':'))
                f.write(f"{alert_entry}\n")
        except Exception as e:
            logger.error(f"Failed to write alert log: {e}")
        
        # Log to main logger
        logger.critical(f"SECURITY ALERT: {event['event_type']} from {event['source_ip']}")
    
    def _check_anomalies(self, event_type: str, source_ip: str, user_id: str):
        """Check for anomalous patterns"""
        current_time = datetime.utcnow()
        hour_ago = current_time - timedelta(hours=1)
        
        # Count recent events of this type from this IP
        recent_events = [
            event for event in self.ip_events[source_ip]
            if (event['timestamp'] > hour_ago and event['event_type'] == event_type)
        ]
        
        # Check thresholds
        threshold = self.anomaly_thresholds.get(event_type, 100)
        if len(recent_events) > threshold:
            self.log_security_event(
                'anomaly_detected',
                source_ip,
                {
                    'anomaly_type': 'high_frequency',
                    'event_type': event_type,
                    'count': len(recent_events),
                    'threshold': threshold
                },
                SecurityEventLevel.CRITICAL,
                user_id
            )
    
    def _generate_event_id(self, event_type: str, timestamp: datetime) -> str:
        """Generate unique event ID"""
        data = f"{event_type}:{timestamp.isoformat()}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _start_background_tasks(self):
        """Start background monitoring and cleanup tasks"""
        self.is_running = True
        
        def cleanup_worker():
            while self.is_running:
                try:
                    self._cleanup_old_data()
                    self._rotate_logs()
                    time.sleep(3600)  # Run every hour
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
        
        self.cleanup_task = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_task.start()
    
    def _cleanup_old_data(self):
        """Clean up old tracking data"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Clean IP events
        for ip in list(self.ip_events.keys()):
            self.ip_events[ip] = [
                event for event in self.ip_events[ip]
                if event['timestamp'] > cutoff_time
            ]
            if not self.ip_events[ip]:
                del self.ip_events[ip]
        
        # Clean user events
        for user_id in list(self.user_events.keys()):
            self.user_events[user_id] = [
                event for event in self.user_events[user_id]
                if event['timestamp'] > cutoff_time
            ]
            if not self.user_events[user_id]:
                del self.user_events[user_id]
    
    def _rotate_logs(self):
        """Rotate log files if they exceed size limit"""
        for log_file in [self.audit_log_file, self.alert_log_file, self.compliance_log_file]:
            if log_file.exists() and log_file.stat().st_size > self.max_log_size:
                # Compress and rotate
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                rotated_file = log_file.with_suffix(f'.{timestamp}.gz')
                
                with open(log_file, 'rb') as f_in:
                    with gzip.open(rotated_file, 'wb') as f_out:
                        f_out.writelines(f_in)
                
                # Clear original file
                log_file.write_text('')
                
                # Clean up old rotated files
                self._cleanup_old_logs(log_file)
    
    def _cleanup_old_logs(self, base_log_file: Path):
        """Clean up old rotated log files"""
        pattern = f"{base_log_file.stem}.*.gz"
        rotated_files = sorted(
            self.log_dir.glob(pattern),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # Keep only the most recent files
        for old_file in rotated_files[self.max_log_files:]:
            old_file.unlink()
    
    def stop(self):
        """Stop background tasks"""
        self.is_running = False
        if self.cleanup_task and self.cleanup_task.is_alive():
            self.cleanup_task.join(timeout=5)