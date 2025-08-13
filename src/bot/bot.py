# SPDX-License-Identifier: MIT
from pathlib import Path
import logging
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from managers.file_ownership import FileOwnershipManager
from trackers.task_progress import TaskProgressTracker
from config.logging_config import logger

class SlackBot:
    def __init__(self):
        self.file_manager = FileOwnershipManager()
        self.task_tracker = TaskProgressTracker()
        logger.info("SlackBot initialized")

    def handle_hire_command(self, employee_name, role):
        """Handle the /hire command"""
        logger.info(f"Handling hire command for {employee_name} as {role}")

        if self.file_manager.hire_employee(employee_name, role):
            logger.info(f"Successfully hired {employee_name} as a {role}")
            return f"Successfully hired {employee_name} as a {role}!"
        else:
            logger.warning(f"Failed to hire {employee_name}. Employee may already exist.")
            return f"Failed to hire {employee_name}. Employee may already exist."

    def handle_fire_command(self, employee_name):
        """Handle the /fire command"""
        logger.info(f"Handling fire command for {employee_name}")

        if self.file_manager.fire_employee(employee_name):
            logger.info(f"Successfully fired {employee_name}")
            return f"Successfully fired {employee_name}."
        else:
            logger.warning(f"Failed to fire {employee_name}. Employee may not exist.")
            return f"Failed to fire {employee_name}. Employee may not exist."

    def handle_lock_command(self, employee_name, files, task_description):
        """Handle file locking command"""
        logger.info(f"Handling lock command for {employee_name}: {files}")

        result = self.file_manager.lock_files(employee_name, files, task_description)

        # Create a task file for tracking progress
        self.task_tracker.create_task_file(employee_name, task_description, files)

        response = f"Files locked for {employee_name}:\n"
        for file_path, status in result.items():
            response += f"- {file_path}: {status}\n"

        logger.info(f"Files locked for {employee_name}: {result}")
        return response

    def handle_release_command(self, employee_name, files=None):
        """Handle file releasing command"""
        logger.info(f"Handling release command for {employee_name}")

        if files is None:
            released = self.file_manager.release_files(employee_name)
            if released:
                logger.info(f"Released all files for {employee_name}: {released}")
                return f"Released all files for {employee_name}: {', '.join(released)}"
            else:
                logger.info(f"No files to release for {employee_name}")
                return f"No files to release for {employee_name}"
        else:
            released = self.file_manager.release_files(employee_name, files)
            if released:
                logger.info(f"Released files for {employee_name}: {released}")
                return f"Released files for {employee_name}: {', '.join(released)}"
            else:
                logger.info(f"No files released for {employee_name}")
                return f"No files released for {employee_name}"

    def handle_auto_release_command(self, employee_name):
        """Handle automatic file release based on task completion"""
        logger.info(f"Handling auto-release command for {employee_name}")

        released = self.file_manager.release_ready_files(employee_name, self.task_tracker)
        if released:
            logger.info(f"Auto-released files for {employee_name}: {released}")
            return f"Auto-released files for {employee_name}: {', '.join(released)}"
        else:
            logger.info(f"No files ready for release by {employee_name}")
            return f"No files ready for release by {employee_name}"

    def handle_progress_command(self, employee_name):
        """Handle progress checking command"""
        logger.info(f"Handling progress command for {employee_name}")

        progress = self.task_tracker.get_task_progress(employee_name)
        if not progress:
            logger.info(f"No progress found for {employee_name}")
            return f"No progress found for {employee_name}"

        response = f"Progress for {employee_name}:\n"
        response += f"Task: {progress['task_description']}\n"
        response += f"Overall Progress: {progress['overall_progress']}%\n"
        response += f"Files ready to release: {', '.join(progress['ready_to_release']) if progress['ready_to_release'] else 'None'}\n"
        response += f"Still working on: {', '.join(progress['still_working_on']) if progress['still_working_on'] else 'None'}\n"

        logger.info(f"Progress for {employee_name}: {progress['overall_progress']}%")
        return response

    def handle_employees_command(self):
        """Handle listing all employees"""
        logger.info("Handling employees command")

        employees = self.file_manager.list_employees()
        if not employees:
            logger.info("No employees found")
            return "No employees found."

        response = "Employees:\n"
        for employee in employees:
            response += f"- {employee['name']} ({employee['role']})\n"

        logger.info(f"Found {len(employees)} employees")
        return response

    def handle_request_command(self, requester, file_path, reason):
        """Handle file request command"""
        logger.info(f"Handling request command: {requester} wants {file_path}")

        result = self.file_manager.request_file(requester, file_path, reason)

        if result == "file_not_locked":
            logger.info(f"File {file_path} is not currently locked by anyone")
            return f"File {file_path} is not currently locked by anyone."
        elif result == "already_owner":
            logger.info(f"{requester} already owns {file_path}")
            return f"You already own {file_path}."
        elif result.startswith("request_sent_to_"):
            owner = result.replace("request_sent_to_", "")
            logger.info(f"File request sent to {owner} for {file_path}")
            return f"File request sent to {owner} for {file_path}. Reason: {reason}"
        else:
            logger.error(f"Unexpected error requesting {file_path}: {result}")
            return f"Unexpected error requesting {file_path}."

    def handle_requests_command(self, owner):
        """Handle listing pending requests for an owner"""
        logger.info(f"Handling requests command for {owner}")

        requests = self.file_manager.get_pending_requests(owner)
        if not requests:
            logger.info(f"No pending requests for {owner}")
            return f"No pending requests for {owner}."

        response = f"Pending requests for {owner}:\n"
        for req in requests:
            response += f"- Request ID {req['id']}: {req['requester']} wants {req['file_path']} ({req['reason']})\n"

        logger.info(f"Found {len(requests)} pending requests for {owner}")
        return response

    def handle_approve_command(self, owner, request_id):
        """Handle approving a file request"""
        logger.info(f"Handling approve command: {owner} approving request {request_id}")

        # Verify that the owner is the one approving
        employees = self.file_manager.list_employees()
        employee_names = [emp['name'] for emp in employees]
        if owner not in employee_names:
            logger.warning(f"{owner} is not an employee")
            return f"You are not an employee. Please hire yourself first."

        # Approve the request
        if self.file_manager.approve_request(request_id):
            logger.info(f"Request {request_id} approved successfully")
            return f"Request {request_id} approved successfully!"
        else:
            logger.warning(f"Failed to approve request {request_id}")
            return f"Failed to approve request {request_id}. It may not exist or already be processed."

    def handle_deny_command(self, owner, request_id):
        """Handle denying a file request"""
        logger.info(f"Handling deny command: {owner} denying request {request_id}")

        # Verify that the owner is the one denying
        employees = self.file_manager.list_employees()
        employee_names = [emp['name'] for emp in employees]
        if owner not in employee_names:
            logger.warning(f"{owner} is not an employee")
            return f"You are not an employee. Please hire yourself first."

        # Deny the request
        if self.file_manager.deny_request(request_id):
            logger.info(f"Request {request_id} denied successfully")
            return f"Request {request_id} denied successfully!"
        else:
            logger.warning(f"Failed to deny request {request_id}")
            return f"Failed to deny request {request_id}. It may not exist or already be processed."

# Simple demo function
if __name__ == "__main__":
    bot = SlackBot()

    # Demo the functionality
    print("=== Slack Bot Demo ===")
    print(bot.handle_hire_command("sarah", "developer"))
    print(bot.handle_hire_command("dev-2", "developer"))
    print(bot.handle_lock_command("sarah", ["src/auth.py", "src/user.py"], "implement auth feature"))
    print(bot.handle_request_command("dev-2", "src/auth.py", "need to add validation"))
    print(bot.handle_requests_command("sarah"))
    # In a real scenario, we would get the request ID from the requests command
    # For demo purposes, we'll simulate approving a request
    print("Note: In practice, you would get the request ID from the requests command and then approve it.")
    print(bot.handle_progress_command("sarah"))
    print(bot.handle_auto_release_command("sarah"))
    print(bot.handle_employees_command())
    print(bot.handle_fire_command("sarah"))