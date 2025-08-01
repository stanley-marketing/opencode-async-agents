#!/usr/bin/env python3
"""
Demo script to show the ReAct agent functionality
"""

import os
from dotenv import load_dotenv
from src.agents.react_agent import ReActAgent

# Load environment variables
load_dotenv()

def main():
    """Demonstrate the ReAct agent functionality"""
    
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in .env file")
        print("Please add your OpenAI API key to the .env file to run this demo")
        return
    
    print("🤖 Initializing ReAct Agent...")
    
    # Create the ReAct agent
    agent = ReActAgent(
        employee_name="john",
        role="developer", 
        expertise=["python", "javascript", "api"]
    )
    
    print("✅ Agent initialized successfully!")
    print(f"Agent: {agent.employee_name} ({agent.role})")
    print(f"Expertise: {', '.join(agent.expertise)}")
    print(f"Available tools: {[tool.name for tool in agent.tools]}")
    print()
    
    # Demo messages
    demo_messages = [
        "Hello! Can you help me with a Python project?",
        "Please start a task to implement user authentication",
        "Can you check the progress on our current tasks?",
        "Show me the contents of src/main.py"
    ]
    
    print("🎯 Demo Messages:")
    print("=" * 50)
    
    for i, message in enumerate(demo_messages, 1):
        print(f"\n{i}. User: {message}")
        print("   Agent: Processing...")
        
        try:
            response = agent.handle_message(message)
            print(f"   Agent: {response}")
        except Exception as e:
            print(f"   Agent: Error - {str(e)}")
        
        print("-" * 30)
    
    print("\n✨ Demo completed!")
    print("\nThe ReAct agent can:")
    print("• Start coding tasks using the start_task tool")
    print("• Examine project files using the look_at_project tool") 
    print("• Check progress using the check_progress tool")
    print("• Respond intelligently to user questions")
    print("• Maintain context about the developer's role and expertise")

if __name__ == "__main__":
    main()