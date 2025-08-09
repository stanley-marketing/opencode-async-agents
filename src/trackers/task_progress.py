from datetime import datetime
from src.config.logging_config import logger
from typing import Dict, List, Optional
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import json
import logging
import os

class TaskProgressTracker:
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = sessions_dir
        os.makedirs(sessions_dir, exist_ok=True)
        logger.info(f"TaskProgressTracker initialized with sessions directory: {sessions_dir}")

    def create_task_file(self, employee_name: str, task_description: str, files_needed: List[str]) -> str:
        """Create a new task progress file for an employee"""
        logger.info(f"Creating task file for {employee_name}: {task_description}")

        session_dir = os.path.join(self.sessions_dir, employee_name)
        os.makedirs(session_dir, exist_ok=True)

        task_file = os.path.join(session_dir, "current_task.md")

        # Create initial task file content
        content = f"""# Current Task: {task_description}

## Assigned: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Files Needed:
{chr(10).join(f'- {file} (not started)' for file in files_needed)}

## Progress:
- [ ] Task started
- [ ] Files analyzed
- [ ] Implementation in progress
- [ ] Testing completed
- [ ] Ready for review

## File Status:
{chr(10).join(f'- {file}: 0% complete (not started)' for file in files_needed)}

## Current Work:
Starting task analysis...

## Next Steps:
1. Analyze required files
2. Plan implementation approach
3. Begin coding

## Notes:
Task assigned at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        with open(task_file, 'w') as f:
            f.write(content)

        logger.info(f"Task file created for {employee_name} at {task_file}")
        return task_file

    def get_task_progress(self, employee_name: str) -> Optional[Dict]:
        """Parse the current task file and extract progress information"""
        logger.info(f"Getting task progress for {employee_name}")

        task_file = os.path.join(self.sessions_dir, employee_name, "current_task.md")

        if not os.path.exists(task_file):
            logger.info(f"No task file found for {employee_name}")
            return None

        with open(task_file, 'r') as f:
            content = f.read()

        # Parse the task file to extract structured information
        progress = {
            'employee': employee_name,
            'task_file': task_file,
            'last_updated': datetime.fromtimestamp(os.path.getmtime(task_file)).isoformat(),
            'file_status': {},
            'overall_progress': 0,
            'ready_to_release': [],
            'still_working_on': [],
            'task_description': '',
            'current_work': ''
        }

        lines = content.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()

            # Extract task description from title
            if line.startswith('# Current Task:'):
                progress['task_description'] = line.replace('# Current Task:', '').strip()

            # Track sections
            elif line.startswith('## File Status:'):
                current_section = 'file_status'
            elif line.startswith('## Current Work:'):
                current_section = 'current_work'
            elif line.startswith('##'):
                current_section = None

            # Parse file status
            elif current_section == 'file_status' and line and not line.startswith('##'):
                # Handle both formats:
                # Format 1: "- src/auth.py: 80% complete (JWT function in progress)"
                # Format 2: "45% complete" (simple format)
                if line.startswith('- ') and ':' in line:
                    # Format 1: Detailed file status
                    file_part = line[2:].split(':')[0].strip()
                    status_part = line.split(':', 1)[1].strip()

                    # Extract percentage
                    percentage = 0
                    if '% complete' in status_part:
                        try:
                            percentage = int(status_part.split('%')[0].strip())
                        except:
                            percentage = 0

                    progress['file_status'][file_part] = {
                        'percentage': percentage,
                        'status': status_part
                    }

                    # Categorize files
                    if percentage >= 100 or 'READY TO RELEASE' in status_part.upper():
                        progress['ready_to_release'].append(file_part)
                    elif percentage > 0:
                        progress['still_working_on'].append(file_part)
                elif '% complete' in line and not line.startswith('-'):
                    # Format 2: Simple overall status
                    try:
                        percentage = int(line.split('%')[0].strip())
                        # Create a dummy file entry for overall progress
                        progress['file_status']['overall_task'] = {
                            'percentage': percentage,
                            'status': line
                        }
                        # Categorize based on percentage
                        if percentage >= 100:
                            progress['ready_to_release'].append('overall_task')
                        elif percentage > 0:
                            progress['still_working_on'].append('overall_task')
                    except:
                        pass  # Ignore if we can't parse the percentage

            # Extract current work
            elif current_section == 'current_work' and line and not line.startswith('#'):
                if progress['current_work']:
                    progress['current_work'] += '\n' + line
                else:
                    progress['current_work'] = line

        # Calculate overall progress
        if progress['file_status']:
            total_percentage = sum(file['percentage'] for file in progress['file_status'].values())
            progress['overall_progress'] = total_percentage // len(progress['file_status'])

        logger.info(f"Retrieved task progress for {employee_name}: {progress['overall_progress']}% complete")
        return progress

    def update_file_status(self, employee_name: str, file_path: str, percentage: int, status_note: str = ""):
        """Update the status of a specific file in the task progress"""
        logger.info(f"Updating file status for {employee_name}: {file_path} - {percentage}%")

        task_file = os.path.join(self.sessions_dir, employee_name, "current_task.md")

        if not os.path.exists(task_file):
            logger.warning(f"No task file found for {employee_name}")
            return False

        with open(task_file, 'r') as f:
            content = f.read()

        lines = content.split('\n')
        updated_lines = []
        in_file_status = False
        file_updated = False

        for line in lines:
            if line.strip().startswith('## File Status:'):
                in_file_status = True
                updated_lines.append(line)
            elif line.strip().startswith('##') and in_file_status:
                in_file_status = False
                updated_lines.append(line)
            elif in_file_status and line.strip().startswith(f'- {file_path}:'):
                # Update this file's status
                status_text = f"{percentage}% complete"
                if status_note:
                    status_text += f" ({status_note})"
                if percentage >= 100:
                    status_text += " (READY TO RELEASE)"

                updated_lines.append(f'- {file_path}: {status_text}')
                file_updated = True
            else:
                updated_lines.append(line)

        if file_updated:
            with open(task_file, 'w') as f:
                f.write('\n'.join(updated_lines))
            logger.info(f"File status updated for {employee_name}: {file_path}")
            return True

        logger.warning(f"File {file_path} not found in task file for {employee_name}")
        return False

    def mark_task_complete(self, employee_name: str):
        """Mark the entire task as complete"""
        logger.info(f"Marking task complete for {employee_name}")

        task_file = os.path.join(self.sessions_dir, employee_name, "current_task.md")

        if not os.path.exists(task_file):
            logger.warning(f"No task file found for {employee_name}")
            return False

        # Archive the completed task
        completed_dir = os.path.join(self.sessions_dir, employee_name, "completed_tasks")
        os.makedirs(completed_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archived_file = os.path.join(completed_dir, f"task_{timestamp}.md")

        # Move current task to completed
        os.rename(task_file, archived_file)

        logger.info(f"Task marked complete for {employee_name} and archived to {archived_file}")
        return True

    def cleanup_employee_session(self, employee_name: str):
        """Clean up all session data for an employee (used when firing)"""
        import shutil
        logger.info(f"Cleaning up session data for {employee_name}")

        employee_session_dir = os.path.join(self.sessions_dir, employee_name)

        if os.path.exists(employee_session_dir):
            try:
                shutil.rmtree(employee_session_dir)
                logger.info(f"Session directory removed for {employee_name}")
                return True
            except Exception as e:
                logger.error(f"Error removing session directory for {employee_name}: {e}")
                return False
        else:
            logger.info(f"No session directory found for {employee_name}")
            return True

    def get_last_completed_task_output(self, employee_name: str) -> Optional[str]:
        """Return the text content of the most recently completed task file for an employee."""
        completed_dir = os.path.join(self.sessions_dir, employee_name, "completed_tasks")
        if not os.path.exists(completed_dir):
            return None
        # Find latest file by modification time
        files = [os.path.join(completed_dir, f) for f in os.listdir(completed_dir) if f.endswith('.md')]
        if not files:
            return None
        latest_file = max(files, key=os.path.getmtime)
        try:
            with open(latest_file, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading completed task file {latest_file}: {e}")
            return None

    def get_all_progress(self) -> Dict[str, Dict]:
        """Get progress for all employees"""
        logger.info("Getting progress for all employees")

        all_progress = {}

        if not os.path.exists(self.sessions_dir):
            logger.info("Sessions directory does not exist")
            return all_progress

        for employee_dir in os.listdir(self.sessions_dir):
            employee_path = os.path.join(self.sessions_dir, employee_dir)
            if os.path.isdir(employee_path):
                progress = self.get_task_progress(employee_dir)
                if progress:
                    all_progress[employee_dir] = progress

        logger.info(f"Retrieved progress for {len(all_progress)} employees")
        return all_progress

    def update_current_work(self, employee_name: str, work_description: str):
        """Update the current work section of the task file"""
        logger.info(f"Updating current work for {employee_name}: {work_description}")

        task_file = os.path.join(self.sessions_dir, employee_name, "current_task.md")

        if not os.path.exists(task_file):
            logger.warning(f"No task file found for {employee_name}")
            return False

        with open(task_file, 'r') as f:
            content = f.read()

        lines = content.split('\n')
        updated_lines = []
        in_current_work = False
        work_updated = False

        for line in lines:
            if line.strip().startswith('## Current Work:'):
                in_current_work = True
                updated_lines.append(line)
                updated_lines.append(f"{work_description}")
                updated_lines.append(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                work_updated = True
            elif line.strip().startswith('##') and in_current_work:
                in_current_work = False
                updated_lines.append(line)
            elif not in_current_work:
                updated_lines.append(line)
            # Skip old current work content when in_current_work is True

        if work_updated:
            with open(task_file, 'w') as f:
                f.write('\n'.join(updated_lines))
            logger.info(f"Current work updated for {employee_name}")
            return True

        logger.warning(f"Could not update current work for {employee_name}")
        return False

    def suggest_file_releases(self, employee_name: str) -> List[str]:
        """Suggest files that can be released based on progress"""
        logger.info(f"Suggesting file releases for {employee_name}")

        progress = self.get_task_progress(employee_name)
        if not progress:
            logger.info(f"No progress found for {employee_name}")
            return []

        releases = progress.get('ready_to_release', [])
        logger.info(f"Suggested releases for {employee_name}: {releases}")
        return releases

class ProgressFileWatcher(FileSystemEventHandler):
    """Watch for changes in task progress files"""

    def __init__(self, callback_func):
        self.callback_func = callback_func
        logger.info("ProgressFileWatcher initialized")

    def on_modified(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith('current_task.md'):
            # Extract employee name from path
            path_parts = event.src_path.split(os.sep)
            if 'sessions' in path_parts:
                sessions_index = path_parts.index('sessions')
                if sessions_index + 1 < len(path_parts):
                    employee_name = path_parts[sessions_index + 1]
                    logger.info(f"Task file modified for {employee_name}")
                    self.callback_func(employee_name, event.src_path)