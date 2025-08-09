"""
Message parser for Telegram chat integration.
Handles @mentions, commands, and message analysis.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ParsedMessage:
    """Represents a parsed chat message"""
    
    message_id: int
    text: str
    sender: str
    timestamp: datetime
    mentions: List[str]
    is_command: bool
    command: Optional[str] = None
    command_args: List[str] = None
    reply_to: Optional[int] = None
    
    def __post_init__(self):
        if self.command_args is None:
            self.command_args = []

class MessageParser:
    """Parses Telegram messages for mentions, commands, and context"""
    
    def __init__(self):
        # Regex patterns for parsing
        self.mention_pattern = re.compile(r'@(\w+(?:-bot)?)')
        self.command_pattern = re.compile(r'^/(\w+)(?:\s+(.*))?')
        
    def parse_message(self, message_data: Dict) -> ParsedMessage:
        """Parse a Telegram message into structured data"""
        
        # Extract basic message info
        message_id = message_data.get('message_id', 0)
        text = message_data.get('text', '')
        sender = self._extract_sender(message_data)
        timestamp = datetime.fromtimestamp(message_data.get('date', 0))
        reply_to = message_data.get('reply_to_message', {}).get('message_id')
        
        # Parse mentions
        mentions = self._extract_mentions(text)
        
        # Parse commands
        is_command, command, command_args = self._extract_command(text)
        
        return ParsedMessage(
            message_id=message_id,
            text=text,
            sender=sender,
            timestamp=timestamp,
            mentions=mentions,
            is_command=is_command,
            command=command,
            command_args=command_args,
            reply_to=reply_to
        )
    
    def _extract_sender(self, message_data: Dict) -> str:
        """Extract sender information from message data"""
        from_data = message_data.get('from', {})
        
        # Try username first, then first name, then ID
        username = from_data.get('username')
        if username:
            return username
            
        first_name = from_data.get('first_name', '')
        last_name = from_data.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip()
        
        if full_name:
            return full_name
            
        return str(from_data.get('id', 'unknown'))
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract @mentions from message text"""
        matches = self.mention_pattern.findall(text)
        # Remove -bot suffix for internal processing
        return [match.replace('-bot', '') for match in matches]
    
    def _extract_command(self, text: str) -> Tuple[bool, Optional[str], List[str]]:
        """Extract command and arguments from message text"""
        match = self.command_pattern.match(text.strip())
        
        if not match:
            return False, None, []
        
        command = match.group(1)
        args_text = match.group(2) or ''
        args = args_text.split() if args_text else []
        
        return True, command, args
    
    def is_help_request(self, text: str) -> bool:
        """Check if message is asking for help"""
        help_keywords = [
            'help', 'stuck', 'problem', 'issue', 'error', 
            'how to', 'any ideas', 'suggestions', 'advice'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in help_keywords)
    
    def is_task_assignment(self, text: str, mentions: List[str]) -> bool:
        """Check if message is assigning a task to someone"""
        if not mentions:
            return False
            
        task_keywords = [
            'please', 'can you', 'could you', 'add', 'create', 
            'fix', 'update', 'implement', 'make', 'do'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in task_keywords)
    
    def extract_task_description(self, text: str, mentioned_employee: str) -> str:
        """Extract task description from a message"""
        # Remove the mention from the text
        mention_pattern = f"@{mentioned_employee}(-bot)?"
        clean_text = re.sub(mention_pattern, '', text, flags=re.IGNORECASE).strip()
        
        # Remove common prefixes (more comprehensive list)
        prefixes_to_remove = [
            'so,', 'so', 'please', 'can you', 'could you', 'would you', 
            'i need you to', 'i want you to', 'i would like you to',
            'hey,', 'hi,', 'hello,'
        ]
        
        # Keep removing prefixes until no more match
        changed = True
        while changed:
            changed = False
            for prefix in prefixes_to_remove:
                if clean_text.lower().startswith(prefix.lower()):
                    clean_text = clean_text[len(prefix):].strip()
                    # Remove comma or space after prefix
                    if clean_text.startswith(','):
                        clean_text = clean_text[1:].strip()
                    changed = True
                    break
        
        # Remove common suffixes
        suffixes_to_remove = ['thanks', 'thank you', 'pls', 'plz', '?']
        for suffix in suffixes_to_remove:
            if clean_text.lower().endswith(suffix.lower()):
                clean_text = clean_text[:-len(suffix)].strip()
        
        # Handle follow-up phrases like "then" or "start then"
        if clean_text.lower() in ['then', 'start then', 'go ahead', 'proceed']:
            return f"Continue with previous request: {clean_text}"
        
        # If we still have a generic request, try to extract the core
        if any(word in clean_text.lower() for word in ['look at', 'check', 'review', 'examine', 'coverage']):
            # This is likely a request to examine something
            return clean_text
        
        # If we have something very short, use the original message
        if len(clean_text) < 10 and len(text) > len(clean_text):
            return text[:100] + "..." if len(text) > 100 else text
            
        return clean_text