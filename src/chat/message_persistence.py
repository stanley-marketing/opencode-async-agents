"""
Message Persistence Module
Handles chat history storage, message replay, and conversation threading.
"""

import asyncio
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class PersistedMessage:
    """Represents a persisted chat message"""
    id: int
    message_id: str
    conversation_id: str
    sender: str
    text: str
    message_type: str  # 'chat_message', 'system', 'agent_response', etc.
    timestamp: datetime
    reply_to: Optional[str] = None
    mentions: List[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['mentions'] = self.mentions or []
        data['metadata'] = self.metadata or {}
        return data
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersistedMessage':
        """Create from dictionary"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class Conversation:
    """Represents a conversation thread"""
    id: str
    title: str
    participants: List[str]
    created_at: datetime
    last_activity: datetime
    message_count: int
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        data['metadata'] = self.metadata or {}
        return data


class MessagePersistence:
    """
    Handles persistent storage of chat messages and conversation history.
    Provides message replay, search, and conversation threading capabilities.
    """
    
    def __init__(self, db_path: str = "chat_history.db", max_messages: int = 10000):
        """
        Initialize message persistence.
        
        Args:
            db_path: Path to SQLite database file
            max_messages: Maximum messages to keep (for cleanup)
        """
        self.db_path = Path(db_path)
        self.max_messages = max_messages
        self.db_lock = threading.RLock()
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # In-memory cache for recent messages
        self.message_cache: Dict[str, PersistedMessage] = {}
        self.conversation_cache: Dict[str, Conversation] = {}
        self.cache_size = 1000
        
        logger.info(f"Message persistence initialized with database: {self.db_path}")
        
    def _init_database(self):
        """Initialize the SQLite database schema"""
        try:
            with self._get_connection() as conn:
                # Messages table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_id TEXT UNIQUE NOT NULL,
                        conversation_id TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        text TEXT NOT NULL,
                        message_type TEXT NOT NULL DEFAULT 'chat_message',
                        timestamp DATETIME NOT NULL,
                        reply_to TEXT,
                        mentions TEXT,  -- JSON array
                        metadata TEXT,  -- JSON object
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Conversations table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        participants TEXT NOT NULL,  -- JSON array
                        created_at DATETIME NOT NULL,
                        last_activity DATETIME NOT NULL,
                        message_count INTEGER DEFAULT 0,
                        metadata TEXT,  -- JSON object
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Indexes for performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_reply_to ON messages(reply_to)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_conversations_last_activity ON conversations(last_activity)')
                
                conn.commit()
                
            logger.info("Database schema initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
            
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper locking"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
                
    async def store_message(self, message_id: str, conversation_id: str, sender: str, 
                          text: str, message_type: str = 'chat_message',
                          reply_to: Optional[str] = None, mentions: List[str] = None,
                          metadata: Dict[str, Any] = None) -> bool:
        """
        Store a message in the database.
        
        Args:
            message_id: Unique message identifier
            conversation_id: Conversation identifier
            sender: Message sender
            text: Message text
            message_type: Type of message
            reply_to: ID of message being replied to
            mentions: List of mentioned users
            metadata: Additional metadata
            
        Returns:
            True if stored successfully
        """
        try:
            timestamp = datetime.now()
            mentions_json = json.dumps(mentions or [])
            metadata_json = json.dumps(metadata or {})
            
            # Store in database
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO messages 
                    (message_id, conversation_id, sender, text, message_type, 
                     timestamp, reply_to, mentions, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (message_id, conversation_id, sender, text, message_type,
                      timestamp, reply_to, mentions_json, metadata_json))
                
                # Update conversation
                await self._update_conversation(conn, conversation_id, sender, timestamp)
                
                conn.commit()
                
            # Update cache
            message = PersistedMessage(
                id=0,  # Will be set by database
                message_id=message_id,
                conversation_id=conversation_id,
                sender=sender,
                text=text,
                message_type=message_type,
                timestamp=timestamp,
                reply_to=reply_to,
                mentions=mentions or [],
                metadata=metadata or {}
            )
            
            self._update_cache(message)
            
            logger.debug(f"Stored message {message_id} from {sender}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store message {message_id}: {e}")
            return False
            
    async def _update_conversation(self, conn, conversation_id: str, sender: str, timestamp: datetime):
        """Update conversation metadata"""
        try:
            # Check if conversation exists
            result = conn.execute(
                'SELECT participants, message_count FROM conversations WHERE id = ?',
                (conversation_id,)
            ).fetchone()
            
            if result:
                # Update existing conversation
                participants = json.loads(result['participants'])
                if sender not in participants:
                    participants.append(sender)
                    
                conn.execute('''
                    UPDATE conversations 
                    SET participants = ?, last_activity = ?, message_count = message_count + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (json.dumps(participants), timestamp, conversation_id))
                
            else:
                # Create new conversation
                title = f"Conversation {conversation_id}"
                participants = [sender]
                
                conn.execute('''
                    INSERT INTO conversations 
                    (id, title, participants, created_at, last_activity, message_count, metadata)
                    VALUES (?, ?, ?, ?, ?, 1, '{}')
                ''', (conversation_id, title, json.dumps(participants), timestamp, timestamp))
                
        except Exception as e:
            logger.error(f"Failed to update conversation {conversation_id}: {e}")
            
    def _update_cache(self, message: PersistedMessage):
        """Update in-memory cache"""
        self.message_cache[message.message_id] = message
        
        # Limit cache size
        if len(self.message_cache) > self.cache_size:
            # Remove oldest entries
            sorted_messages = sorted(
                self.message_cache.items(),
                key=lambda x: x[1].timestamp
            )
            
            for i in range(len(sorted_messages) - self.cache_size):
                del self.message_cache[sorted_messages[i][0]]
                
    async def get_message(self, message_id: str) -> Optional[PersistedMessage]:
        """Get a specific message by ID"""
        # Check cache first
        if message_id in self.message_cache:
            return self.message_cache[message_id]
            
        try:
            with self._get_connection() as conn:
                result = conn.execute('''
                    SELECT * FROM messages WHERE message_id = ?
                ''', (message_id,)).fetchone()
                
                if result:
                    message = self._row_to_message(result)
                    self._update_cache(message)
                    return message
                    
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            
        return None
        
    async def get_conversation_messages(self, conversation_id: str, limit: int = 100,
                                      offset: int = 0, since: Optional[datetime] = None) -> List[PersistedMessage]:
        """
        Get messages from a conversation.
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            since: Only return messages after this timestamp
            
        Returns:
            List of messages
        """
        try:
            with self._get_connection() as conn:
                query = '''
                    SELECT * FROM messages 
                    WHERE conversation_id = ?
                '''
                params = [conversation_id]
                
                if since:
                    query += ' AND timestamp > ?'
                    params.append(since)
                    
                query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
                params.extend([limit, offset])
                
                results = conn.execute(query, params).fetchall()
                
                messages = []
                for row in results:
                    message = self._row_to_message(row)
                    messages.append(message)
                    self._update_cache(message)
                    
                # Return in chronological order
                return list(reversed(messages))
                
        except Exception as e:
            logger.error(f"Failed to get conversation messages: {e}")
            return []
            
    async def get_recent_messages(self, limit: int = 50) -> List[PersistedMessage]:
        """Get recent messages across all conversations"""
        try:
            with self._get_connection() as conn:
                results = conn.execute('''
                    SELECT * FROM messages 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,)).fetchall()
                
                messages = []
                for row in results:
                    message = self._row_to_message(row)
                    messages.append(message)
                    self._update_cache(message)
                    
                return list(reversed(messages))
                
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []
            
    async def search_messages(self, query: str, conversation_id: Optional[str] = None,
                            sender: Optional[str] = None, limit: int = 50) -> List[PersistedMessage]:
        """
        Search messages by text content.
        
        Args:
            query: Search query
            conversation_id: Limit to specific conversation
            sender: Limit to specific sender
            limit: Maximum results
            
        Returns:
            List of matching messages
        """
        try:
            with self._get_connection() as conn:
                sql = '''
                    SELECT * FROM messages 
                    WHERE text LIKE ?
                '''
                params = [f'%{query}%']
                
                if conversation_id:
                    sql += ' AND conversation_id = ?'
                    params.append(conversation_id)
                    
                if sender:
                    sql += ' AND sender = ?'
                    params.append(sender)
                    
                sql += ' ORDER BY timestamp DESC LIMIT ?'
                params.append(limit)
                
                results = conn.execute(sql, params).fetchall()
                
                messages = []
                for row in results:
                    message = self._row_to_message(row)
                    messages.append(message)
                    
                return messages
                
        except Exception as e:
            logger.error(f"Failed to search messages: {e}")
            return []
            
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation metadata"""
        # Check cache first
        if conversation_id in self.conversation_cache:
            return self.conversation_cache[conversation_id]
            
        try:
            with self._get_connection() as conn:
                result = conn.execute('''
                    SELECT * FROM conversations WHERE id = ?
                ''', (conversation_id,)).fetchone()
                
                if result:
                    conversation = self._row_to_conversation(result)
                    self.conversation_cache[conversation_id] = conversation
                    return conversation
                    
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            
        return None
        
    async def get_conversations(self, limit: int = 50) -> List[Conversation]:
        """Get list of conversations ordered by last activity"""
        try:
            with self._get_connection() as conn:
                results = conn.execute('''
                    SELECT * FROM conversations 
                    ORDER BY last_activity DESC 
                    LIMIT ?
                ''', (limit,)).fetchall()
                
                conversations = []
                for row in results:
                    conversation = self._row_to_conversation(row)
                    conversations.append(conversation)
                    self.conversation_cache[conversation.id] = conversation
                    
                return conversations
                
        except Exception as e:
            logger.error(f"Failed to get conversations: {e}")
            return []
            
    def _row_to_message(self, row) -> PersistedMessage:
        """Convert database row to PersistedMessage"""
        return PersistedMessage(
            id=row['id'],
            message_id=row['message_id'],
            conversation_id=row['conversation_id'],
            sender=row['sender'],
            text=row['text'],
            message_type=row['message_type'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            reply_to=row['reply_to'],
            mentions=json.loads(row['mentions']) if row['mentions'] else [],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )
        
    def _row_to_conversation(self, row) -> Conversation:
        """Convert database row to Conversation"""
        return Conversation(
            id=row['id'],
            title=row['title'],
            participants=json.loads(row['participants']),
            created_at=datetime.fromisoformat(row['created_at']),
            last_activity=datetime.fromisoformat(row['last_activity']),
            message_count=row['message_count'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )
        
    async def cleanup_old_messages(self, days_to_keep: int = 30):
        """Clean up old messages to prevent database growth"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self._get_connection() as conn:
                # Delete old messages
                result = conn.execute('''
                    DELETE FROM messages 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                
                deleted_count = result.rowcount
                
                # Update conversation message counts
                conn.execute('''
                    UPDATE conversations 
                    SET message_count = (
                        SELECT COUNT(*) FROM messages 
                        WHERE messages.conversation_id = conversations.id
                    )
                ''')
                
                # Delete empty conversations
                conn.execute('''
                    DELETE FROM conversations 
                    WHERE message_count = 0
                ''')
                
                conn.commit()
                
            logger.info(f"Cleaned up {deleted_count} old messages")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old messages: {e}")
            
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self._get_connection() as conn:
                # Message statistics
                message_stats = conn.execute('''
                    SELECT 
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT sender) as unique_senders,
                        COUNT(DISTINCT conversation_id) as total_conversations,
                        MIN(timestamp) as oldest_message,
                        MAX(timestamp) as newest_message
                    FROM messages
                ''').fetchone()
                
                # Conversation statistics
                conv_stats = conn.execute('''
                    SELECT 
                        AVG(message_count) as avg_messages_per_conversation,
                        MAX(message_count) as max_messages_in_conversation
                    FROM conversations
                ''').fetchone()
                
                return {
                    'total_messages': message_stats['total_messages'],
                    'unique_senders': message_stats['unique_senders'],
                    'total_conversations': message_stats['total_conversations'],
                    'oldest_message': message_stats['oldest_message'],
                    'newest_message': message_stats['newest_message'],
                    'avg_messages_per_conversation': conv_stats['avg_messages_per_conversation'],
                    'max_messages_in_conversation': conv_stats['max_messages_in_conversation'],
                    'cache_size': len(self.message_cache),
                    'database_path': str(self.db_path)
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


# Global persistence instance
_persistence = None


def get_message_persistence() -> MessagePersistence:
    """Get the global message persistence instance"""
    global _persistence
    
    if _persistence is None:
        db_path = os.environ.get('OPENCODE_CHAT_DB', 'chat_history.db')
        max_messages = int(os.environ.get('OPENCODE_MAX_MESSAGES', 10000))
        _persistence = MessagePersistence(db_path, max_messages)
        
    return _persistence


def create_message_persistence(db_path: str = "chat_history.db", 
                             max_messages: int = 10000) -> MessagePersistence:
    """Create a new message persistence instance"""
    return MessagePersistence(db_path, max_messages)