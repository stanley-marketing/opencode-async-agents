#!/usr/bin/env python3
"""
Comprehensive API Endpoint 500 Error Fixes for OpenCode-Slack System
Addresses critical issues identified in Phase 3 validation:
1. Employee Management API fixes
2. Monitoring endpoints JSON serialization fixes
3. Method signature compatibility fixes
4. Production monitoring integration fixes
"""

import json
import logging
import sys
import os
from pathlib import Path
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger(__name__)


class JSONSerializationFixer:
    """Fixes JSON serialization issues for monitoring endpoints"""
    
    @staticmethod
    def serialize_enum(obj):
        """Convert enum to serializable format"""
        if isinstance(obj, Enum):
            return obj.value
        return obj
    
    @staticmethod
    def serialize_datetime(obj):
        """Convert datetime to serializable format"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    @staticmethod
    def serialize_complex_object(obj):
        """Convert complex objects to serializable format"""
        if hasattr(obj, '__dict__'):
            result = {}
            for key, value in obj.__dict__.items():
                if isinstance(value, Enum):
                    result[key] = value.value
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, list):
                    result[key] = [JSONSerializationFixer.serialize_complex_object(item) for item in value]
                elif isinstance(value, dict):
                    result[key] = {k: JSONSerializationFixer.serialize_complex_object(v) for k, v in value.items()}
                elif hasattr(value, '__dict__'):
                    result[key] = JSONSerializationFixer.serialize_complex_object(value)
                else:
                    result[key] = value
            return result
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, list):
            return [JSONSerializationFixer.serialize_complex_object(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: JSONSerializationFixer.serialize_complex_object(v) for k, v in obj.items()}
        else:
            return obj


class MonitoringEndpointFixer:
    """Fixes monitoring endpoint 500 errors"""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.serializer = JSONSerializationFixer()
    
    def fix_monitoring_health_endpoint(self):
        """Fix /monitoring/health endpoint JSON serialization"""
        
        def get_monitoring_health_fixed():
            """Get agent health monitoring status with proper JSON serialization"""
            try:
                if hasattr(self.server, 'production_monitoring') and self.server.production_monitoring:
                    # Use production monitoring system
                    try:
                        system_status = self.server.production_monitoring.get_system_status()
                        health_data = system_status.get('health', {})
                        
                        # Serialize the health data properly
                        serialized_health = self.serializer.serialize_complex_object(health_data)
                        
                        return {'status': 'success', 'health': serialized_health}, 200
                    except Exception as e:
                        logger.error(f"Error getting production health status: {e}")
                        return {'error': f'Production monitoring error: {str(e)}'}, 500
                elif self.server.health_monitor:
                    # Fallback to basic monitoring
                    health_summary = self.server.health_monitor.get_agent_health_summary()
                    serialized_health = self.serializer.serialize_complex_object(health_summary)
                    return {'status': 'success', 'health': serialized_health}, 200
                else:
                    return {'error': 'Monitoring system not available'}, 400
            except Exception as e:
                logger.error(f"Unexpected error in monitoring health endpoint: {e}")
                return {'error': f'Internal server error: {str(e)}'}, 500
        
        return get_monitoring_health_fixed
    
    def fix_monitoring_recovery_endpoint(self):
        """Fix /monitoring/recovery endpoint JSON serialization"""
        
        def get_monitoring_recovery_fixed():
            """Get agent recovery status with proper JSON serialization"""
            try:
                if hasattr(self.server, 'production_monitoring') and self.server.production_monitoring:
                    # Use production monitoring system
                    try:
                        recovery_history = self.server.production_monitoring.health_checker.get_recovery_history(24)
                        recovery_summary = self.server.production_monitoring.health_checker.get_overall_health()
                        
                        # Serialize the recovery data properly
                        serialized_data = {
                            'recovery_history': self.serializer.serialize_complex_object(recovery_history),
                            'recovery_summary': self.serializer.serialize_complex_object(recovery_summary)
                        }
                        
                        return {'status': 'success', 'data': serialized_data}, 200
                    except Exception as e:
                        logger.error(f"Error getting production recovery status: {e}")
                        return {'error': f'Production monitoring error: {str(e)}'}, 500
                elif self.server.recovery_manager:
                    # Fallback to basic monitoring
                    recovery_summary = self.server.recovery_manager.get_recovery_summary()
                    serialized_recovery = self.serializer.serialize_complex_object(recovery_summary)
                    return {'status': 'success', 'recovery': serialized_recovery}, 200
                else:
                    return {'error': 'Recovery system not available'}, 400
            except Exception as e:
                logger.error(f"Unexpected error in monitoring recovery endpoint: {e}")
                return {'error': f'Internal server error: {str(e)}'}, 500
        
        return get_monitoring_recovery_fixed
    
    def fix_production_status_endpoint(self):
        """Fix /monitoring/production/status endpoint JSON serialization"""
        
        def get_production_monitoring_status_fixed():
            """Get comprehensive production monitoring status with proper JSON serialization"""
            try:
                if hasattr(self.server, 'production_monitoring') and self.server.production_monitoring:
                    try:
                        system_status = self.server.production_monitoring.get_system_status()
                        serialized_status = self.serializer.serialize_complex_object(system_status)
                        return {'status': 'success', 'data': serialized_status}, 200
                    except Exception as e:
                        logger.error(f"Error getting production monitoring status: {e}")
                        return {'error': f'Production monitoring error: {str(e)}'}, 500
                else:
                    return {'error': 'Production monitoring not available'}, 404
            except Exception as e:
                logger.error(f"Unexpected error in production status endpoint: {e}")
                return {'error': f'Internal server error: {str(e)}'}, 500
        
        return get_production_monitoring_status_fixed
    
    def fix_production_alerts_endpoint(self):
        """Fix /monitoring/production/alerts endpoint JSON serialization"""
        
        def get_production_alerts_fixed():
            """Get production alerts with proper JSON serialization"""
            try:
                if hasattr(self.server, 'production_monitoring') and self.server.production_monitoring:
                    try:
                        active_alerts = self.server.production_monitoring.alerting_system.get_active_alerts()
                        alert_history = self.server.production_monitoring.alerting_system.get_alert_history(24)
                        alert_stats = self.server.production_monitoring.alerting_system.get_alerting_statistics()
                        
                        # Serialize the alert data properly
                        serialized_data = {
                            'active_alerts': self.serializer.serialize_complex_object(active_alerts),
                            'alert_history': self.serializer.serialize_complex_object(alert_history),
                            'statistics': self.serializer.serialize_complex_object(alert_stats)
                        }
                        
                        return {'status': 'success', 'data': serialized_data}, 200
                    except Exception as e:
                        logger.error(f"Error getting production alerts: {e}")
                        return {'error': f'Production alerts error: {str(e)}'}, 500
                else:
                    return {'error': 'Production monitoring not available'}, 404
            except Exception as e:
                logger.error(f"Unexpected error in production alerts endpoint: {e}")
                return {'error': f'Internal server error: {str(e)}'}, 500
        
        return get_production_alerts_fixed


class EmployeeManagementFixer:
    """Fixes employee management API 500 errors"""
    
    def __init__(self, server_instance):
        self.server = server_instance
    
    def fix_employee_creation_endpoint(self):
        """Fix POST /employees endpoint method signature issues"""
        
        def hire_employee_fixed():
            """Hire a new employee with proper error handling"""
            try:
                from flask import request, jsonify
                
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'JSON data required'}), 400
                
                name = data.get('name')
                role = data.get('role')
                smartness = data.get('smartness', 'normal')
                
                if not name or not role:
                    return jsonify({'error': 'Name and role are required'}), 400
                
                # Validate input
                if len(name) > 100:
                    return jsonify({'error': 'Name too long (max 100 characters)'}), 400
                
                if len(role) > 100:
                    return jsonify({'error': 'Role too long (max 100 characters)'}), 400
                
                # Attempt to hire employee
                success = self.server.file_manager.hire_employee(name, role, smartness)
                if success:
                    try:
                        # CRITICAL FIX: Create communication agent with proper error handling
                        expertise = self.server.agent_manager._get_expertise_for_role(role)
                        agent = self.server.agent_manager.create_agent(name, role, expertise)
                        
                        # Ensure agent has proper task tracker reference
                        if hasattr(self.server.agent_manager, 'task_tracker') and self.server.agent_manager.task_tracker:
                            agent.task_tracker = self.server.agent_manager.task_tracker
                        
                        # Sync agents to ensure consistency
                        self.server.agent_manager.sync_agents_with_employees()
                        
                        return jsonify({
                            'status': 'success',
                            'message': f'Successfully hired {name} as {role} with {smartness} smartness',
                            'employee': {
                                'name': name,
                                'role': role,
                                'smartness': smartness
                            }
                        }), 201
                    except Exception as agent_error:
                        logger.error(f"Error creating agent for {name}: {agent_error}")
                        # Employee was hired but agent creation failed - still return success
                        return jsonify({
                            'status': 'partial_success',
                            'message': f'Successfully hired {name} as {role}, but agent creation had issues',
                            'warning': str(agent_error),
                            'employee': {
                                'name': name,
                                'role': role,
                                'smartness': smartness
                            }
                        }), 201
                else:
                    return jsonify({'error': f'Failed to hire {name}. Employee may already exist.'}), 400
            except Exception as e:
                logger.error(f"Unexpected error in employee creation: {e}")
                return jsonify({'error': f'Internal server error: {str(e)}'}), 500
        
        return hire_employee_fixed


class MonitoringSystemHookFixer:
    """Fixes monitoring system method hook compatibility issues"""
    
    def __init__(self, production_monitoring_system):
        self.monitoring_system = production_monitoring_system
    
    def fix_method_hooks(self):
        """Fix method signature compatibility in monitoring hooks"""
        
        # Fix the agent creation hook
        if hasattr(self.monitoring_system.agent_manager, 'create_agent'):
            original_create_agent = self.monitoring_system.agent_manager.create_agent
            
            def hooked_create_agent_fixed(*args, **kwargs):
                try:
                    result = original_create_agent(*args, **kwargs)
                    # Record agent creation metric safely
                    if self.monitoring_system.metrics_collector:
                        import time
                        self.monitoring_system.metrics_collector.record_task_assignment(f"agent_creation_{int(time.time())}")
                    return result
                except Exception as e:
                    logger.error(f"Error in agent creation hook: {e}")
                    # Still call original method even if monitoring fails
                    return original_create_agent(*args, **kwargs)
            
            self.monitoring_system.agent_manager.create_agent = hooked_create_agent_fixed
        
        # Fix the session stop hook with proper argument handling
        if hasattr(self.monitoring_system.session_manager, 'stop_employee_task'):
            original_stop_task = self.monitoring_system.session_manager.stop_employee_task
            
            def hooked_stop_task_fixed(*args, **kwargs):
                try:
                    import time
                    start_time = time.time()
                    
                    # Call original method with proper arguments
                    result = original_stop_task(*args, **kwargs)
                    
                    completion_time = (time.time() - start_time) * 1000
                    
                    # Record task completion metric safely
                    if self.monitoring_system.metrics_collector:
                        self.monitoring_system.metrics_collector.record_task_completion(
                            f"task_completion_{int(time.time())}", 
                            completion_time
                        )
                    return result
                except Exception as e:
                    logger.error(f"Error in task stop hook: {e}")
                    # Still call original method even if monitoring fails
                    return original_stop_task(*args, **kwargs)
            
            self.monitoring_system.session_manager.stop_employee_task = hooked_stop_task_fixed


def apply_comprehensive_api_fixes(server_instance):
    """Apply all API endpoint fixes to the server instance"""
    
    logger.info("🔧 Applying comprehensive API endpoint fixes...")
    
    try:
        # Fix monitoring endpoints
        monitoring_fixer = MonitoringEndpointFixer(server_instance)
        
        # Replace the problematic monitoring endpoints with fixed versions
        if hasattr(server_instance, 'app'):
            app = server_instance.app
            
            # Fix monitoring health endpoint
            @app.route('/monitoring/health', methods=['GET'])
            def get_monitoring_health():
                result, status_code = monitoring_fixer.fix_monitoring_health_endpoint()()
                from flask import jsonify
                return jsonify(result), status_code
            
            # Fix monitoring recovery endpoint
            @app.route('/monitoring/recovery', methods=['GET'])
            def get_monitoring_recovery():
                result, status_code = monitoring_fixer.fix_monitoring_recovery_endpoint()()
                from flask import jsonify
                return jsonify(result), status_code
            
            # Fix production status endpoint
            @app.route('/monitoring/production/status', methods=['GET'])
            def get_production_monitoring_status():
                result, status_code = monitoring_fixer.fix_production_status_endpoint()()
                from flask import jsonify
                return jsonify(result), status_code
            
            # Fix production alerts endpoint
            @app.route('/monitoring/production/alerts', methods=['GET'])
            def get_production_alerts():
                result, status_code = monitoring_fixer.fix_production_alerts_endpoint()()
                from flask import jsonify
                return jsonify(result), status_code
            
            # Fix employee creation endpoint
            employee_fixer = EmployeeManagementFixer(server_instance)
            
            @app.route('/employees', methods=['POST'])
            def hire_employee():
                return employee_fixer.fix_employee_creation_endpoint()()
            
            logger.info("✅ Successfully applied endpoint fixes")
        
        # Fix monitoring system hooks if production monitoring is available
        if hasattr(server_instance, 'production_monitoring') and server_instance.production_monitoring:
            hook_fixer = MonitoringSystemHookFixer(server_instance.production_monitoring)
            hook_fixer.fix_method_hooks()
            logger.info("✅ Successfully applied monitoring system hook fixes")
        
        logger.info("🎉 All API endpoint fixes applied successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error applying API fixes: {e}")
        return False


if __name__ == "__main__":
    print("🔧 API Endpoint Fixes for OpenCode-Slack System")
    print("This module provides comprehensive fixes for 500 errors in:")
    print("1. Employee Management API (POST /employees)")
    print("2. Monitoring endpoints (/monitoring/health, /monitoring/recovery)")
    print("3. Production monitoring endpoints (/monitoring/production/*)")
    print("4. Method signature compatibility issues")
    print("\nTo apply fixes, import and call apply_comprehensive_api_fixes(server_instance)")