# SPDX-License-Identifier: MIT
"""
ReAct Agent using LangChain structured output for intelligent task handling and project interaction
"""

from ..services.llm_service import LLMService
from .agent_tools import get_agent_tools
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union, List
import logging
import os

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class AgentAction(BaseModel):
    """Structured output for agent actions"""
    action: str = Field(description="The action to take, must be one of the available tool names")
    action_input: str = Field(description="The input to pass to the action")
    reasoning: str = Field(description="Brief reasoning for why this action is needed")


class AgentResponse(BaseModel):
    """Structured output for agent responses"""
    response: str = Field(description="Direct response to the user's question or request")
    reasoning: str = Field(description="Brief reasoning for the response")


class AgentOutput(BaseModel):
    """Union of possible agent outputs"""
    output: Union[AgentAction, AgentResponse] = Field(description="Either an action to take or a direct response")


class ReActAgent:
    """ReAct agent using structured output for handling user questions and project tasks"""

    def __init__(self,
                 employee_name: str,
                 role: str,
                 expertise: list,
                 project_context: str = None,
                 memory_manager = None,
                 task_tracker = None):
        """Initialize the ReAct agent"""
        self.employee_name = employee_name
        self.role = role
        self.expertise = expertise
        self.project_context = project_context or self._get_default_project_context()
        self.memory_manager = memory_manager
        self.task_tracker = task_tracker

        # Initialize LLM service
        self.llm_service = LLMService()

        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model="o4-mini",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=1
        )

        # Get tools
        self.tools = get_agent_tools(task_tracker=self.task_tracker)

        # Create structured output LLM
        self.structured_llm = self.llm.with_structured_output(AgentOutput)

        # Create different prompts for different modes
        self.forward_prompt = self._create_react_prompt("forward")
        self.backward_prompt = self._create_react_prompt("backward")
        self.status_prompt = self._create_react_prompt("status")

        # Create different agents for different modes
        self.forward_agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.forward_prompt
        )

        self.backward_agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.backward_prompt
        )

        self.status_agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.status_prompt
        )

        # Create agent executors for different modes
        self.forward_executor = AgentExecutor(
            agent=self.forward_agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,  # Reduced to prevent infinite loops
            max_execution_time=30,  # 30 second timeout
            early_stopping_method="force"  # Force stop when max_iterations reached
        )

        self.backward_executor = AgentExecutor(
            agent=self.backward_agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=2,  # Reduced to prevent infinite loops
            max_execution_time=20,  # 20 second timeout
            early_stopping_method="force"  # Force stop when max_iterations reached
        )

        self.status_executor = AgentExecutor(
            agent=self.status_agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=2,  # Reduced to prevent infinite loops
            max_execution_time=15,  # 15 second timeout
            early_stopping_method="force"  # Force stop when max_iterations reached
        )

    def _get_shared_prompt_components(self):
        """Get shared prompt components used across different modes"""
        # Get memory context if available
        memory_context = "No recent conversations"
        if self.memory_manager:
            memory_summary = self.memory_manager.get_memory_summary()
            memory_context = f"Recent Memory Summary: {memory_summary}"

        # Get conversation history if available
        conversation_history = "No recent conversations"
        if self.memory_manager:
            memory_data = self.memory_manager.get_relevant_memory()
            if memory_data.get("recent_conversations"):
                conv_lines = []
                for conv in memory_data["recent_conversations"]:
                    conv_lines.append(f"{conv['timestamp']}: {conv['sender']}: {conv['message']}")
                conversation_history = "\n".join(conv_lines)

        return {
            "employee_name": self.employee_name,
            "role": self.role,
            "expertise": ", ".join(self.expertise),
            "project_context": self.project_context,
            "memory_context": memory_context,
            "conversation_history": conversation_history,
            "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools]),
            "tool_names": ", ".join([tool.name for tool in self.tools])
        }

    def _create_react_prompt(self, mode: str = "forward") -> ChatPromptTemplate:
        """Create the ReAct prompt template for different modes"""

        shared_base = """You are {employee_name}, a {role} with expertise in {expertise}.

Project Context:
{project_context}

Memory Context:
{memory_context}

Conversation History:
{conversation_history}

Available Tools:
{tools}

You must respond in one of two ways:
1. If you need to use a tool: Provide an AgentAction with action, action_input, and reasoning
2. If you have the final answer: Provide an AgentResponse with response and reasoning

IMPORTANT: Choose ONE approach - either use a tool OR provide a direct response, never both."""

        if mode == "forward":
            mode_specific = """
Your Role and Behavior (FORWARD MODE - Handling User Requests):
- You are a thoughtful, intelligent developer working on the opencode-slack project
- Always think deeply about the user's intent, even for simple greetings
- You are the ONLY component that generates responses - never use static templates
- Distinguish between different types of requests:
  * Coverage requests ("check coverage", "coverage report") -> Use start_task tool to start coverage analysis
  * Code/file questions -> Use look_at_project tool
  * Progress inquiries -> Use check_progress tool
  * Implementation tasks -> Use start_task tool for actual development work
  * General conversation -> Respond naturally based on context
- Be professional but friendly and engaging in your responses
- Keep responses concise but informative (2-3 sentences max)
- Always provide clear, actionable responses
- Generate dynamic, contextual responses rather than templated ones
- When starting a task, always inform the user that you're working on it and will report back when finished
- If a user asks for something that requires work to be done, start the task rather than just explaining what needs to be done

Conversation Context Guidelines:
- Always consider the recent conversation history when responding
- If someone asks "what did I just ask you?", refer to the conversation history
- Follow-up messages should be understood in context of previous messages
- "Could you please start then?" should be interpreted as continuing previous request"""

        elif mode == "backward":
            mode_specific = """
Your Role and Behavior (BACKWARD MODE - Analyzing Task Results):
- You are analyzing the output/results from a completed task
- Your job is to read through the task output and summarize what actually happened
- Focus on the RESULTS and OUTCOMES, not just that the task finished
- Look for:
  * What was accomplished
  * Key findings or data discovered
  * Any issues or errors encountered
  * Actionable insights or next steps
- Present findings in a clear, organized way
- Be specific about numbers, percentages, file names, etc. when available
- If the task failed, explain what went wrong and suggest solutions

Task Output Analysis Guidelines:
- Read through the last several lines of task output to understand what happened
- Extract meaningful results, not just status messages
- Summarize technical findings in an accessible way
- Highlight important discoveries or issues
- Provide context about what the results mean"""

        elif mode == "status":
            mode_specific = """
Your Role and Behavior (STATUS MODE - Explaining Current Work):
- You are explaining what work is currently in progress
- Your job is to check the current status and explain it to the user
- Focus on:
  * What task is currently running
  * What stage/step the task is at
  * How much progress has been made
  * Estimated time remaining if available
- Be brief but informative
- Reassure the user that work is progressing
- If the task seems stuck, acknowledge it and suggest next steps

Current Status Guidelines:
- Use check_progress tool to get current status
- Explain the current work in simple terms
- Give a realistic timeline if possible
- If multiple tasks are running, prioritize the most relevant one"""

        template = shared_base + mode_specific

        # Get shared components
        shared_components = self._get_shared_prompt_components()

        # Format the system message with shared components
        system_message = template.format(**shared_components)

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])

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

    def handle_message(self, message: str, context: Dict[str, Any] = None, mode: str = "forward") -> str:
        """Handle a user message using the ReAct agent in different modes"""
        try:
            # Add any additional context
            if context:
                enhanced_message = f"Context: {context}\n\nUser Message: {message}"
            else:
                enhanced_message = message

            # Choose the appropriate executor based on mode
            if mode == "forward":
                executor = self.forward_executor
            elif mode == "backward":
                executor = self.backward_executor
            elif mode == "status":
                executor = self.status_executor
            else:
                executor = self.forward_executor  # Default to forward

            # Execute the agent
            result = executor.invoke({"input": enhanced_message})

            output = result.get("output", "I couldn't process that request.")

            # Ensure we have a meaningful response
            if not output or not output.strip():
                return "I'm here and ready to help! Could you please provide more details about what you'd like me to do?"

            # Clean up verbose output if needed
            if "Agent stopped due to iteration limit" in output or "Agent stopped due to iteration limit or time limit" in output:
                # Check if the agent started a task (check the full output first)
                if "started coding task" in output.lower() or "task id:" in output.lower():
                    # Provide a proper final answer for task initiation
                    return f"I've started working on generating the coverage report. I'll analyze the test suite and report back with the current coverage metrics when it's complete."

                # Extract just the meaningful part before the limit message
                lines = output.split('\n')
                meaningful_lines = []
                for line in lines:
                    if line.startswith("Agent stopped due to iteration limit") or line.startswith("Agent stopped due to iteration limit or time limit"):
                        break
                    if line.strip():
                        meaningful_lines.append(line.strip())
                if meaningful_lines:
                    response = '\n'.join(meaningful_lines)
                    # Ensure response is not empty
                    if response.strip():
                        return response

            # Check if the output indicates a task was started
            if "started coding task" in output.lower() or "task id:" in output.lower():
                return f"I've started working on this task. I'll report back with the results when it's complete."

            # Ensure response is not just a copy of the input
            if output.strip().lower() == message.strip().lower():
                return f"I understand you're asking about: {message[:50]}... How specifically can I help with this?"

            return output

        except Exception as e:
            logger.warning(f"ReAct agent error for {self.employee_name} in {mode} mode: {str(e)}")
            # Check if this is a tool validation error
            if "Invalid tool" in str(e) or "not a valid tool" in str(e):
                # Provide a more specific fallback response for tool errors
                return "I'm having trouble with that request. Could you please rephrase it or ask me to do something specific like 'check progress', 'look at a file', or 'start a task'?"
            # Check if this is a parsing error or iteration limit
            elif "parsing" in str(e).lower() or "iteration" in str(e).lower() or "timeout" in str(e).lower():
                # Extract any meaningful output from the error
                error_str = str(e)
                if "Final Answer:" in error_str:
                    # Try to extract the final answer from the error
                    try:
                        final_answer_start = error_str.find("Final Answer:")
                        if final_answer_start != -1:
                            final_answer = error_str[final_answer_start:].split('\n')[0]
                            return final_answer.replace("Final Answer:", "").strip()
                    except:
                        pass
                return "I encountered a processing issue. Let me try a simpler approach to help you."
            # Provide a fallback response
            return "I'm here and ready to help! Could you please rephrase your request or provide more details about what you'd like me to do?"

    def analyze_task_results(self, task_output: str, task_description: str | None = None) -> str:
        """Analyze task results and provide a summary (backward mode)"""
        analysis_prompt = (
            "Task has completed. Here is the output from the task execution:\n\n"
            f"{task_output}\n\n"
        )
        if task_description:
            analysis_prompt += f"The original user request was: \"{task_description}\".\n\n"
        analysis_prompt += (
            "First, answer the user directly with the specific result they asked for (e.g. the exact coverage percentage). "
            "Then provide a concise summary of:\n"
            "1. What was accomplished\n"
            "2. Key findings or results\n"
            "3. Any issues encountered\n"
            "4. Next steps or recommendations"
        )
        try:
            return self.handle_message(analysis_prompt, mode="backward")
        except Exception as e:
            # Fallback: try to extract coverage percentage ourselves
            import re, logging
            logger.warning(f"ReAct agent LLM analysis failed, using fallback: {e}")
            match = re.search(r"TOTAL.*?(\d+)%", task_output)
            if match:
                percent = match.group(1)
                return (
                    f"Test coverage is {percent}%.\n"
                    "I gathered this by directly parsing the pytest coverage output."
                )
            return "Task completed but could not determine coverage from output."

    def explain_current_status(self, employee_name: str) -> str:
        """Explain what the agent is currently working on (status mode)"""
        status_prompt = f"The user is asking what {employee_name} is currently working on. Please check the current status and explain what's happening."
        return self.handle_message(status_prompt, mode="status")

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
        self.forward_prompt = self._create_react_prompt("forward")
        # Recreate the agent
        self.forward_agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.forward_prompt
        )
        # Recreate agent executor
        self.forward_executor = AgentExecutor(
            agent=self.forward_agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,
            max_execution_time=30,
            early_stopping_method="force"
        )