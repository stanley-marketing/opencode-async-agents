"""
Tools for the ReAct agent to interact with the project and coding system
"""

import os
import json
from typing import Dict, Any, List
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class StartTaskInput(BaseModel):
    """Input for start_task tool"""
    task_description: str = Field(description="Description of the coding task to start")
    priority: str = Field(default="medium", description="Priority level: high, medium, or low")


class StartTaskTool(BaseTool):
    """Tool to start a coding task"""
    name: str = "start_task"
    description: str = "Start a new coding task. Use this when the user requests implementation or coding work."
    args_schema: type[BaseModel] = StartTaskInput
    
    def _run(self, task_description: str, priority: str = "medium") -> str:
        """Start a coding task"""
        try:
            # In a real implementation, this would interface with your task management system
            # For now, we'll simulate starting a task
            task_id = f"task_{hash(task_description) % 10000}"
            
            # Log the task start
            task_info = {
                "task_id": task_id,
                "description": task_description,
                "priority": priority,
                "status": "started",
                "assigned_to": "coding_agent"
            }
            
            return f"✅ Started coding task: {task_description}\nTask ID: {task_id}\nPriority: {priority}\nAssigned to coding agent for implementation."
            
        except Exception as e:
            return f"❌ Error starting task: {str(e)}"


class LookAtProjectInput(BaseModel):
    """Input for look_at_project tool"""
    file_path: str = Field(description="Path to the file to examine")
    lines_limit: int = Field(default=50, description="Maximum number of lines to read")


class LookAtProjectTool(BaseTool):
    """Tool to examine project files"""
    name: str = "look_at_project"
    description: str = "Read and examine files in the project. Use this to understand code structure or check specific files."
    args_schema: type[BaseModel] = LookAtProjectInput
    
    def _run(self, file_path: str, lines_limit: int = 50) -> str:
        """Read a project file"""
        try:
            # Ensure we're working within the project directory
            project_root = "/home/eladbenhaim/dev/opencode-slack"
            full_path = os.path.join(project_root, file_path.lstrip('/'))
            
            if not os.path.exists(full_path):
                return f"❌ File not found: {file_path}"
            
            if not full_path.startswith(project_root):
                return f"❌ Access denied: File outside project directory"
            
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if len(lines) > lines_limit:
                content = ''.join(lines[:lines_limit])
                content += f"\n... (truncated, showing first {lines_limit} lines of {len(lines)} total)"
            else:
                content = ''.join(lines)
            
            return f"📄 Contents of {file_path}:\n\n{content}"
            
        except Exception as e:
            return f"❌ Error reading file {file_path}: {str(e)}"


class CheckProgressInput(BaseModel):
    """Input for check_progress tool"""
    task_id: str = Field(default="", description="Specific task ID to check (optional)")


class CheckProgressTool(BaseTool):
    """Tool to check progress on tasks"""
    name: str = "check_progress"
    description: str = "Check the progress of coding tasks and project status. Use this to understand current work status."
    args_schema: type[BaseModel] = CheckProgressInput
    
    def _run(self, task_id: str = "") -> str:
        """Check progress on tasks"""
        try:
            # In a real implementation, this would check actual task progress
            # For now, we'll simulate progress checking
            
            if task_id:
                # Check specific task
                progress_info = {
                    "task_id": task_id,
                    "status": "in_progress",
                    "completion": "45%",
                    "current_step": "Implementing core functionality",
                    "estimated_completion": "2 hours"
                }
                
                return f"📊 Progress for task {task_id}:\n" \
                       f"Status: {progress_info['status']}\n" \
                       f"Completion: {progress_info['completion']}\n" \
                       f"Current step: {progress_info['current_step']}\n" \
                       f"Estimated completion: {progress_info['estimated_completion']}"
            else:
                # Check overall progress
                overall_progress = {
                    "active_tasks": 2,
                    "completed_tasks": 5,
                    "pending_tasks": 1,
                    "current_focus": "User authentication system"
                }
                
                return f"📈 Overall Project Progress:\n" \
                       f"Active tasks: {overall_progress['active_tasks']}\n" \
                       f"Completed tasks: {overall_progress['completed_tasks']}\n" \
                       f"Pending tasks: {overall_progress['pending_tasks']}\n" \
                       f"Current focus: {overall_progress['current_focus']}"
                        
        except Exception as e:
            return f"❌ Error checking progress: {str(e)}"


class StoreMemoryInput(BaseModel):
    """Input for store_memory tool"""
    information: str = Field(description="The important information to store")
    topic: str = Field(description="The topic or category for this information")
    source: str = Field(default="conversation", description="Source of the information")

class StoreMemoryTool(BaseTool):
    """Tool to store important information in memory"""
    name: str = "store_memory"
    description: str = "Store important information from conversations for future reference. Use this when you identify important team updates or completed work."
    args_schema: type[BaseModel] = StoreMemoryInput
    
    def _run(self, information: str, topic: str, source: str = "conversation") -> str:
        """Store information in memory"""
        try:
            # In a real implementation, this would interface with the memory manager
            # For now, we'll simulate storing memory
            return f"✅ Stored in memory under '{topic}': {information[:100]}... (source: {source})"
        except Exception as e:
            return f"❌ Error storing memory: {str(e)}"


def get_agent_tools() -> List[BaseTool]:
    """Get all available tools for the ReAct agent"""
    return [
        StartTaskTool(),
        LookAtProjectTool(),
        CheckProgressTool(),
        StoreMemoryTool()
    ]