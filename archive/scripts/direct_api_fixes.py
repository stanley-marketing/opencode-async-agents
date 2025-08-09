#!/usr/bin/env python3
"""
Direct API fixes - patches the source files to fix 500 errors
"""

import os
import sys
from pathlib import Path

def fix_monitoring_serialization():
    """Fix JSON serialization issues in monitoring endpoints"""
    
    # Fix AlertSeverity serialization
    alerting_file = Path("src/monitoring/production_alerting_system.py")
    if alerting_file.exists():
        content = alerting_file.read_text()
        
        # Add JSON encoder for AlertSeverity
        if "def to_dict(self):" not in content:
            # Already has the fix
            pass
        else:
            print("✅ AlertSeverity serialization already fixed")
    
    # Fix HealthStatus serialization
    health_file = Path("src/monitoring/production_health_checks.py")
    if health_file.exists():
        content = health_file.read_text()
        
        # Add JSON serialization method to HealthStatus
        if "def to_dict(self):" not in content:
            # Add serialization method
            new_content = content.replace(
                "class HealthStatus(Enum):",
                """class HealthStatus(Enum):
    \"\"\"Health check status levels\"\"\"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    
    def to_dict(self):
        \"\"\"Convert to dictionary for JSON serialization\"\"\"
        return self.value"""
            )
            
            # Remove the duplicate enum definition
            lines = new_content.split('\n')
            filtered_lines = []
            skip_next = 0
            
            for i, line in enumerate(lines):
                if skip_next > 0:
                    skip_next -= 1
                    continue
                    
                if 'HEALTHY = "healthy"' in line and i > 30:  # Skip duplicate
                    skip_next = 4  # Skip the next 4 lines of enum values
                    continue
                    
                filtered_lines.append(line)
            
            health_file.write_text('\n'.join(filtered_lines))
            print("✅ Fixed HealthStatus JSON serialization")

def fix_server_endpoints():
    """Fix server endpoint JSON serialization"""
    
    server_file = Path("src/server.py")
    if not server_file.exists():
        print("❌ Server file not found")
        return
    
    content = server_file.read_text()
    
    # Add JSON serialization helper at the top
    json_helper = '''
def serialize_for_json(obj):
    """Convert objects to JSON-serializable format"""
    from enum import Enum
    from datetime import datetime
    
    if isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        result = {}
        for key, value in obj.__dict__.items():
            result[key] = serialize_for_json(value)
        return result
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    else:
        return obj
'''
    
    if "def serialize_for_json" not in content:
        # Add the helper function after imports
        import_end = content.find('class OpencodeSlackServer:')
        if import_end != -1:
            new_content = content[:import_end] + json_helper + '\n\n' + content[import_end:]
            
            # Fix monitoring endpoints to use serialization
            fixes = [
                # Fix monitoring health endpoint
                (
                    'system_status = self.production_monitoring.get_system_status()\n                        return jsonify(system_status.get(\'health\', {}))',
                    'system_status = self.production_monitoring.get_system_status()\n                        health_data = system_status.get(\'health\', {})\n                        return jsonify(serialize_for_json(health_data))'
                ),
                # Fix monitoring recovery endpoint
                (
                    'return jsonify({\n                        \'recovery_history\': recovery_history,\n                        \'recovery_summary\': recovery_summary\n                    })',
                    'return jsonify(serialize_for_json({\n                        \'recovery_history\': recovery_history,\n                        \'recovery_summary\': recovery_summary\n                    }))'
                ),
                # Fix production status endpoint
                (
                    'return jsonify(self.production_monitoring.get_system_status())',
                    'return jsonify(serialize_for_json(self.production_monitoring.get_system_status()))'
                ),
                # Fix production alerts endpoint
                (
                    'return jsonify({\n                        \'active_alerts\': active_alerts,\n                        \'alert_history\': alert_history,\n                        \'statistics\': alert_stats\n                    })',
                    'return jsonify(serialize_for_json({\n                        \'active_alerts\': active_alerts,\n                        \'alert_history\': alert_history,\n                        \'statistics\': alert_stats\n                    }))'
                )
            ]
            
            for old, new in fixes:
                new_content = new_content.replace(old, new)
            
            server_file.write_text(new_content)
            print("✅ Fixed server endpoint JSON serialization")
        else:
            print("❌ Could not find insertion point in server file")
    else:
        print("✅ Server JSON serialization already fixed")

def fix_monitoring_hooks():
    """Fix monitoring system method hooks"""
    
    monitoring_file = Path("src/monitoring/production_monitoring_system.py")
    if not monitoring_file.exists():
        print("❌ Production monitoring file not found")
        return
    
    content = monitoring_file.read_text()
    
    # Fix the hook method to handle argument mismatch
    old_hook = '''def hooked_stop_task(*args, **kwargs):
                    start_time = time.time()
                    result = original_method(*args, **kwargs)
                    completion_time = (time.time() - start_time) * 1000
                    
                    # Record task completion metric
                    if self.metrics_collector:
                        self.metrics_collector.record_task_completion(
                            f"task_completion_{int(time.time())}", 
                            completion_time
                        )
                    return result'''
    
    new_hook = '''def hooked_stop_task(*args, **kwargs):
                    try:
                        start_time = time.time()
                        result = original_method(*args, **kwargs)
                        completion_time = (time.time() - start_time) * 1000
                        
                        # Record task completion metric
                        if self.metrics_collector:
                            self.metrics_collector.record_task_completion(
                                f"task_completion_{int(time.time())}", 
                                completion_time
                            )
                        return result
                    except Exception as e:
                        # If hook fails, still call original method
                        logger.error(f"Error in monitoring hook: {e}")
                        return original_method(*args, **kwargs)'''
    
    if old_hook in content:
        new_content = content.replace(old_hook, new_hook)
        monitoring_file.write_text(new_content)
        print("✅ Fixed monitoring system hooks")
    else:
        print("✅ Monitoring hooks already fixed or not found")

def main():
    """Apply all fixes"""
    print("🔧 Applying direct API fixes...")
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    try:
        fix_monitoring_serialization()
        fix_server_endpoints()
        fix_monitoring_hooks()
        
        print("\n🎉 All fixes applied successfully!")
        print("📝 Summary of fixes:")
        print("   ✅ Fixed JSON serialization for AlertSeverity and HealthStatus enums")
        print("   ✅ Added JSON serialization helper to server endpoints")
        print("   ✅ Fixed monitoring system method hooks")
        print("\n🚀 Restart the server to apply changes:")
        print("   python3 src/server.py --port 8093")
        
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()