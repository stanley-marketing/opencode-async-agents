"""
Memory Manager for Communication Agents
Handles short-term memory storage and retrieval for individual agents.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import json
import logging
import os

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages short-term memory for communication agents"""

    def __init__(self, employee_name: str, sessions_dir: str = "sessions"):
        """Initialize memory manager for an employee"""
        self.employee_name = employee_name
        self.sessions_dir = sessions_dir
        self.memory_dir = os.path.join(sessions_dir, employee_name, "memory")

        # Create memory directory
        os.makedirs(self.memory_dir, exist_ok=True)

        # Memory storage
        self.conversation_memory = self._load_conversation_memory()
        self.important_info = self._load_important_info()

        logger.info(f"Memory manager initialized for {employee_name}")

    def _load_conversation_memory(self) -> List[Dict]:
        """Load conversation memory from file"""
        memory_file = os.path.join(self.memory_dir, "conversations.json")
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load conversation memory: {e}")
                return []
        return []

    def _load_important_info(self) -> Dict:
        """Load important information from file"""
        info_file = os.path.join(self.memory_dir, "important_info.json")
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load important info: {e}")
                return {}
        return {}

    def save_memory(self):
        """Save memory to files"""
        try:
            # Save conversations
            memory_file = os.path.join(self.memory_dir, "conversations.json")
            with open(memory_file, 'w') as f:
                json.dump(self.conversation_memory, f, indent=2, default=str)

            # Save important info
            info_file = os.path.join(self.memory_dir, "important_info.json")
            with open(info_file, 'w') as f:
                json.dump(self.important_info, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Could not save memory: {e}")

    def add_conversation(self, sender: str, message: str, timestamp: datetime = None):
        """Add a conversation to memory"""
        if timestamp is None:
            timestamp = datetime.now()

        conversation_entry = {
            "sender": sender,
            "message": message,
            "timestamp": timestamp.isoformat(),
            "processed": False
        }

        self.conversation_memory.append(conversation_entry)

        # Keep only last 50 conversations to prevent memory bloat
        if len(self.conversation_memory) > 50:
            self.conversation_memory = self.conversation_memory[-50:]

        self.save_memory()

    def summarize_conversation(self, sender: str, message: str, context: str = None) -> str:
        """Create a summary of a conversation for memory storage"""
        # This would be handled by the ReAct agent in practice
        # For now, we'll create a simple summary
        summary = f"{sender}: {message[:100]}"
        if context:
            summary = f"{context} - {summary}"
        return summary

    def store_important_information(self, topic: str, information: str, source: str = "conversation"):
        """Store important information in memory"""
        if topic not in self.important_info:
            self.important_info[topic] = []

        info_entry = {
            "information": information,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "relevance_score": 0.5  # Will be updated by ReAct agent
        }

        self.important_info[topic].append(info_entry)

        # Keep only last 20 entries per topic
        if len(self.important_info[topic]) > 20:
            self.important_info[topic] = self.important_info[topic][-20:]

        self.save_memory()

    def get_relevant_memory(self, context: str = None) -> Dict:
        """Get relevant memory for current context"""
        return {
            "recent_conversations": self.conversation_memory[-10:],  # Last 10 conversations
            "important_info": self.important_info,
            "unprocessed_count": len([c for c in self.conversation_memory if not c.get('processed', True)])
        }

    def mark_conversation_processed(self, index: int):
        """Mark a conversation as processed"""
        if 0 <= index < len(self.conversation_memory):
            self.conversation_memory[index]['processed'] = True
            self.save_memory()

    def get_memory_summary(self) -> str:
        """Get a summary of current memory state for agent context"""
        summary_parts = []

        # Add conversation count
        unprocessed = len([c for c in self.conversation_memory if not c.get('processed', True)])
        summary_parts.append(f"Memory contains {len(self.conversation_memory)} recent conversations ({unprocessed} unprocessed)")

        # Add important info topics
        if self.important_info:
            topics = list(self.important_info.keys())
            summary_parts.append(f"Tracking {len(topics)} important topics: {', '.join(topics[:5])}")

        return "; ".join(summary_parts)