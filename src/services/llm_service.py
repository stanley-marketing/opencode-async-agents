"""
LLM Service for handling AI agent communication
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Load environment variables from .env file
load_dotenv()


class LLMService:
    """Service for handling LLM interactions"""
    
    def __init__(self, model_name: str = "o4-mini"):
        """Initialize LLM service with OpenAI"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.llm = ChatOpenAI(
            model=model_name,
            openai_api_key=self.api_key,
            temperature=1
        )
    
    def generate_response(self, 
                         user_message: str, 
                         system_context: str = None,
                         **kwargs) -> str:
        """Generate a response using the LLM"""
        messages = []
        
        if system_context:
            messages.append(SystemMessage(content=system_context))
        
        messages.append(HumanMessage(content=user_message))
        
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": self.llm.model_name,
            "max_tokens": getattr(self.llm, 'max_tokens', None)
        }