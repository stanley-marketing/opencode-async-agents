#!/usr/bin/env python3
"""
Test script for the new static employee types feature.
This script demonstrates how to hire specialized employees from different fields.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.file_ownership import FileOwnershipManager
from src.agents.agent_manager import AgentManager
from src.chat.telegram_manager import TelegramManager

def list_available_employee_types():
    """List all available employee types from the .bmad-core/employee-types directory"""
    employee_types_dir = Path(__file__).parent.parent / ".bmad-core" / "employee-types"
    
    if not employee_types_dir.exists():
        print("Employee types directory not found!")
        return
    
    print("Available Employee Types:")
    print("=" * 40)
    
    for category in employee_types_dir.iterdir():
        if category.is_dir():
            print(f"\n{category.name.upper()}:")
            for employee_type in category.iterdir():
                if employee_type.suffix == ".md":
                    # Remove .md extension and display the name
                    name = employee_type.stem.replace("-", " ").title()
                    print(f"  - {name} ({employee_type.name})")

def load_employee_prompt(category, employee_type):
    """Load and display the employee prompt"""
    employee_types_dir = Path(__file__).parent.parent / ".bmad-core" / "employee-types"
    prompt_file = employee_types_dir / category / f"{employee_type}.md"
    
    if not prompt_file.exists():
        print(f"Employee type {employee_type} not found in {category}!")
        return
    
    print(f"\nEmployee Prompt for {employee_type.replace('-', ' ').title()}:")
    print("=" * 60)
    
    with open(prompt_file, "r") as f:
        content = f.read()
        print(content[:1000] + "..." if len(content) > 1000 else content)

def main():
    """Main function to demonstrate the new feature"""
    print("🧪 Testing Static Employee Types Feature")
    print("=" * 50)
    
    # List available employee types
    list_available_employee_types()
    
    # Example of loading an employee prompt
    print("\n" + "=" * 50)
    load_employee_prompt("engineering", "frontend-developer")
    
    print("\n" + "=" * 50)
    print("✅ Test completed successfully!")

if __name__ == "__main__":
    main()