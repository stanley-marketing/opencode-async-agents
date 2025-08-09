from flask import Flask, request, jsonify
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from bot import SlackBot
from src.config.config import Config

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

bot = SlackBot()

@app.route('/slack/command', methods=['POST'])
def handle_slack_command():
    # Get the command and parameters from the request
    command = request.form.get('command', '').replace('/', '')
    text = request.form.get('text', '')
    user_name = request.form.get('user_name', 'unknown_user')
    
    # Parse the command
    if command == 'hire':
        # /hire employee_name role
        parts = text.split(' ', 1)
        if len(parts) < 2:
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'Usage: /hire employee_name role'
            })
        employee_name, role = parts[0], parts[1]
        response = bot.handle_hire_command(employee_name, role)
        
    elif command == 'fire':
        # /fire employee_name
        if not text:
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'Usage: /fire employee_name'
            })
        employee_name = text
        response = bot.handle_fire_command(employee_name)
        
    elif command == 'lock':
        # /lock files task_description
        # For simplicity, we'll assume files are comma-separated
        parts = text.split(' ', 1)
        if len(parts) < 2:
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'Usage: /lock file1,file2,... task description'
            })
        files_str, task_description = parts[0], parts[1]
        files = [f.strip() for f in files_str.split(',')]
        response = bot.handle_lock_command(user_name, files, task_description)
        
    elif command == 'release':
        # /release [files...]
        if not text:
            # Release all files
            response = bot.handle_release_command(user_name)
        else:
            # Release specific files
            files = [f.strip() for f in text.split(',')]
            response = bot.handle_release_command(user_name, files)
            
    elif command == 'auto-release':
        # /auto-release
        response = bot.handle_auto_release_command(user_name)
        
    elif command == 'progress':
        # /progress [employee_name]
        if not text:
            employee_name = user_name
        else:
            employee_name = text
        response = bot.handle_progress_command(employee_name)
        
    elif command == 'employees':
        # /employees
        response = bot.handle_employees_command()
        
    elif command == 'request':
        # /request file_path reason
        parts = text.split(' ', 1)
        if len(parts) < 2:
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'Usage: /request file_path reason'
            })
        file_path, reason = parts[0], parts[1]
        response = bot.handle_request_command(user_name, file_path, reason)
        
    elif command == 'requests':
        # /requests [owner]
        if not text:
            owner = user_name
        else:
            owner = text
        response = bot.handle_requests_command(owner)
        
    elif command == 'approve':
        # /approve request_id
        if not text:
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'Usage: /approve request_id'
            })
        try:
            request_id = int(text)
            response = bot.handle_approve_command(user_name, request_id)
        except ValueError:
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'Usage: /approve request_id (request_id must be a number)'
            })
            
    elif command == 'deny':
        # /deny request_id
        if not text:
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'Usage: /deny request_id'
            })
        try:
            request_id = int(text)
            response = bot.handle_deny_command(user_name, request_id)
        except ValueError:
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'Usage: /deny request_id (request_id must be a number)'
            })
            
    else:
        response = f"Unknown command: {command}. Available commands: hire, fire, lock, release, auto-release, progress, employees, request, requests, approve, deny"
    
    return jsonify({
        'response_type': 'ephemeral',
        'text': response
    })

if __name__ == '__main__':
    app.run(debug=True, port=3000)