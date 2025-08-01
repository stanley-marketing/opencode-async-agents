#!/usr/bin/env python3
"""
Kill All OpenCode-Slack Servers
Comprehensive script to stop all running server instances.
"""

import subprocess
import sys
import time
import signal
import os

def find_server_processes():
    """Find all OpenCode-Slack server processes"""
    processes = []
    
    try:
        # Method 1: Using pgrep
        result = subprocess.run(['pgrep', '-f', 'server.py'], capture_output=True, text=True)
        if result.stdout.strip():
            pids = [int(pid) for pid in result.stdout.strip().split('\n')]
            processes.extend(pids)
    except (FileNotFoundError, ValueError):
        pass
    
    try:
        # Method 2: Using pgrep for src.server
        result = subprocess.run(['pgrep', '-f', 'src.server'], capture_output=True, text=True)
        if result.stdout.strip():
            pids = [int(pid) for pid in result.stdout.strip().split('\n')]
            processes.extend(pids)
    except (FileNotFoundError, ValueError):
        pass
    
    try:
        # Method 3: Using ps and grep
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if ('server.py' in line or 'src.server' in line or 'opencode-slack' in line) and 'grep' not in line:
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        if pid not in processes:
                            processes.append(pid)
                    except (ValueError, IndexError):
                        continue
    except:
        pass
    
    # Remove duplicates and current process
    current_pid = os.getpid()
    processes = list(set(processes))
    if current_pid in processes:
        processes.remove(current_pid)
    
    return processes

def get_process_info(pid):
    """Get information about a process"""
    try:
        result = subprocess.run(['ps', '-p', str(pid), '-o', 'pid,ppid,cmd'], 
                              capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            return lines[1]  # Skip header
    except:
        pass
    return f"PID {pid} (info unavailable)"

def kill_process(pid, force=False):
    """Kill a specific process"""
    try:
        if force:
            os.kill(pid, signal.SIGKILL)
            return "KILLED"
        else:
            os.kill(pid, signal.SIGTERM)
            return "TERMINATED"
    except ProcessLookupError:
        return "NOT_FOUND"
    except PermissionError:
        return "PERMISSION_DENIED"
    except Exception as e:
        return f"ERROR: {e}"

def kill_by_port(ports):
    """Kill processes using specific ports"""
    killed_ports = []
    
    for port in ports:
        try:
            # Find process using the port
            result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                  capture_output=True, text=True)
            if result.stdout.strip():
                pids = [int(pid) for pid in result.stdout.strip().split('\n')]
                for pid in pids:
                    status = kill_process(pid, force=True)
                    if status in ["KILLED", "TERMINATED"]:
                        killed_ports.append(port)
                        print(f"   ✅ Killed process {pid} using port {port}")
        except (FileNotFoundError, ValueError, subprocess.CalledProcessError):
            continue
    
    return killed_ports

def main():
    """Main cleanup function"""
    print("🔪 OpenCode-Slack Server Killer")
    print("=" * 40)
    
    # Step 1: Find all server processes
    print("🔍 Finding server processes...")
    processes = find_server_processes()
    
    if not processes:
        print("   ✅ No server processes found")
    else:
        print(f"   📋 Found {len(processes)} server processes:")
        for pid in processes:
            info = get_process_info(pid)
            print(f"      {info}")
    
    # Step 2: Kill processes gracefully first
    if processes:
        print(f"\n🔄 Attempting graceful shutdown of {len(processes)} processes...")
        terminated = []
        
        for pid in processes:
            status = kill_process(pid, force=False)
            if status == "TERMINATED":
                terminated.append(pid)
                print(f"   ✅ Terminated process {pid}")
            elif status == "NOT_FOUND":
                print(f"   ℹ️  Process {pid} already gone")
            else:
                print(f"   ⚠️  Could not terminate process {pid}: {status}")
        
        # Wait for graceful shutdown
        if terminated:
            print("   ⏳ Waiting 3 seconds for graceful shutdown...")
            time.sleep(3)
    
    # Step 3: Check what's still running and force kill
    remaining = find_server_processes()
    if remaining:
        print(f"\n🔪 Force killing {len(remaining)} remaining processes...")
        for pid in remaining:
            status = kill_process(pid, force=True)
            if status == "KILLED":
                print(f"   ✅ Force killed process {pid}")
            elif status == "NOT_FOUND":
                print(f"   ℹ️  Process {pid} already gone")
            else:
                print(f"   ❌ Could not kill process {pid}: {status}")
    
    # Step 4: Kill by common ports
    print(f"\n🔌 Checking common ports...")
    common_ports = [8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090]
    killed_ports = kill_by_port(common_ports)
    
    if killed_ports:
        print(f"   ✅ Freed ports: {', '.join(map(str, killed_ports))}")
    else:
        print(f"   ✅ No processes found on common ports")
    
    # Step 5: Final check
    print(f"\n🔍 Final verification...")
    final_check = find_server_processes()
    
    if not final_check:
        print("   🎉 All server processes successfully killed!")
        print("\n✅ Cleanup complete! You can now start fresh servers.")
    else:
        print(f"   ⚠️  {len(final_check)} processes still running:")
        for pid in final_check:
            info = get_process_info(pid)
            print(f"      {info}")
        print("\n💡 You may need to:")
        print("   • Run this script with sudo")
        print("   • Manually kill remaining processes")
        print("   • Restart your system")
    
    # Step 6: Clear Telegram webhook as bonus
    print(f"\n🧹 Bonus: Clearing Telegram webhook...")
    try:
        # Try to import and clear webhook
        sys.path.insert(0, '.')
        from fix_telegram_conflict import load_bot_token, clear_webhook
        
        bot_token = load_bot_token()
        if bot_token:
            if clear_webhook(bot_token):
                print("   ✅ Telegram webhook cleared")
            else:
                print("   ⚠️  Could not clear webhook")
        else:
            print("   ℹ️  No bot token found")
    except Exception as e:
        print(f"   ℹ️  Could not clear webhook: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)