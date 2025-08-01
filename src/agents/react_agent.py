"""
ReAct Agent using LangChain for intelligent task handling and project interaction
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from .agent_tools import get_agent_tools
from ..services.llm_service import LLMService

# Load environment variables from .env file
load_dotenv()


class ReActAgent:
    """ReAct agent for handling user questions and project tasks"""
    
    def __init__(self, 
                 employee_name: str,
                 role: str,
                 expertise: list,
                 project_context: str = None,
                 memory_manager = None):
        """Initialize the ReAct agent"""
        self.employee_name = employee_name
        self.role = role
        self.expertise = expertise
        self.project_context = project_context or self._get_default_project_context()
        self.memory_manager = memory_manager
        
        # Initialize LLM service
        self.llm_service = LLMService()
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Get tools
        self.tools = get_agent_tools()
        
        # Create the ReAct prompt
        self.prompt = self._create_react_prompt()
        
        # Create the agent
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15  # Increased to allow deeper reasoning
        )
    
    def _create_react_prompt(self) -> PromptTemplate:
        """Create the ReAct prompt template"""
        template = """You are {employee_name}, a {role} with expertise in {expertise}.
Project Context:
{project_context}

Memory Context:
{memory_context}

Your Role and Behavior:
- You are a thoughtful, intelligent developer working on the opencode-slack project
- Always think deeply about the user's intent, even for simple greetings
- Distinguish between task assignments and explanation requests:
  * "Please create..." -> Use start_task tool
  * "Please explain..." -> Provide explanation, possibly using check_progress to give context
  * "What does that mean" -> Clarify the specific term or concept
- Be professional but friendly and engaging in your responses
- Keep responses concise but informative (2-3 sentences max)
- When users ask for implementation work, use the start_task tool
- When users ask about code or files, use the look_at_project tool
- When users ask about progress or status, use the check_progress tool
- When users ask for explanations, provide clear, helpful explanations
- Always provide clear, actionable responses

Memory Usage Guidelines:
- Review recent conversations to understand team context
- Store important information that affects your work
- Dismiss irrelevant messages with brief acknowledgments
- When someone reports completing work, note what they did for future reference

Examples of interpretation:
- "Hey" -> Might mean "Are you available?" - Check your status
- "What's up" -> Might mean "What are you working on?" - Check progress
- "How are you" -> Might mean "How is the project going?" - Check progress
- "Please explain..." -> Provide explanation of previous work or concepts
- "What does that mean" -> Clarify the specific term or concept

Clarification Guidance:
When asked to explain or clarify:
1. First understand what they're asking about (often the previous response)
2. Provide a clear, simple explanation
3. If relevant, use check_progress to give context about current work

Available Tools:
{tools}

Always use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
Thought: {agent_scratchpad}"""
        # Get memory context if available
        memory_context = "No recent conversations"
        if self.memory_manager:
            memory_summary = self.memory_manager.get_memory_summary()
            memory_context = f"Recent Memory Summary: {memory_summary}"
        
        return PromptTemplate(
            template=template,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "employee_name": self.employee_name,
                "role": self.role,
                "expertise": ", ".join(self.expertise),
                "project_context": self.project_context,
                "memory_context": memory_context,
                "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools]),
                "tool_names": ", ".join([tool.name for tool in self.tools])
            }
        )    
    def _get_default_project_context(self) -> str:
        """Get default project context"""
        return """
This is the opencode-slack project - a system that bridges Slack communication with AI-powered development agents.

Key Components:
- Communication agents that handle Slack messages and task assignments
- Task management and progress tracking
- Integration with coding agents for implementation work
- File ownership and project management utilities

The project uses Python with Flask for the web server, Slack SDK for Slack integration, and various AI/ML libraries for intelligent task handling.

Current focus areas include improving agent communication, task assignment workflows, and project file management.
"""
    
    def handle_message(self, message: str, context: Dict[str, Any] = None) -> str:
        """Handle a user message using the ReAct agent"""
        try:
            # Add any additional context
            if context:
                enhanced_message = f"Context: {context}\n\nUser Message: {message}"
            else:
                enhanced_message = message
            
            # Always execute the agent - let it figure out the best approach
            result = self.agent_executor.invoke({"input": enhanced_message})
            
            output = result.get("output", "I couldn't process that request.")
            
            # Clean up verbose output if needed
            if "Agent stopped due to iteration limit" in output:
                # Extract just the meaningful part before the limit message
                lines = output.split('\n')
                meaningful_lines = []
                for line in lines:
                    if line.startswith("Agent stopped due to iteration limit"):
                        break
                    if line.strip():
                        meaningful_lines.append(line.strip())
                if meaningful_lines:
                    return '\n'.join(meaningful_lines)
            
            return output
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent"""
        return {
            "employee_name": self.employee_name,
            "role": self.role,
            "expertise": self.expertise,
            "available_tools": [tool.name for tool in self.tools],
            "model_info": self.llm_service.get_model_info()
        }
    
    def update_project_context(self, new_context: str):
        """Update the project context"""
        self.project_context = new_context
        # Recreate the prompt with new context
        self.prompt = self._create_react_prompt()
        # Recreate the agent
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        # Recreate agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )