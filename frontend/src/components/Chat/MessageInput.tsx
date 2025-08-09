/**
 * Message input component with mention support and typing indicators.
 * Handles message composition, @mentions, and command detection.
 */

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { PaperAirplaneIcon, CommandLineIcon } from '@heroicons/react/24/outline';
import { useChatUsers } from '../../stores/chatStore';

interface MessageInputProps {
  onSendMessage: (text: string, replyTo?: number) => void;
  onTypingStart?: () => void;
  onTypingStop?: () => void;
  disabled?: boolean;
  replyTo?: number;
  className?: string;
}

export default function MessageInput({
  onSendMessage,
  onTypingStart,
  onTypingStop,
  disabled = false,
  replyTo,
  className = ''
}: MessageInputProps) {
  const [message, setMessage] = useState('');
  const [showMentions, setShowMentions] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mentionsRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const users = useChatUsers();

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  // Handle typing indicators
  useEffect(() => {
    if (message.trim() && !isTyping) {
      setIsTyping(true);
      onTypingStart?.();
    }

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout
    typingTimeoutRef.current = setTimeout(() => {
      if (isTyping) {
        setIsTyping(false);
        onTypingStop?.();
      }
    }, 1000);

    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, [message, isTyping, onTypingStart, onTypingStop]);

  // Detect @mentions
  useEffect(() => {
    const cursorPosition = textareaRef.current?.selectionStart || 0;
    const textBeforeCursor = message.substring(0, cursorPosition);
    const mentionMatch = textBeforeCursor.match(/@(\w*)$/);

    if (mentionMatch) {
      setMentionQuery(mentionMatch[1]);
      setShowMentions(true);
      setSelectedMentionIndex(0);
    } else {
      setShowMentions(false);
      setMentionQuery('');
    }
  }, [message]);

  // Filter users for mentions
  const filteredUsers = users.filter(user =>
    user.user_id.toLowerCase().includes(mentionQuery.toLowerCase()) &&
    user.is_online
  );

  // Handle message submission
  const handleSubmit = () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || disabled) return;

    onSendMessage(trimmedMessage, replyTo);
    setMessage('');
    
    // Stop typing indicator
    if (isTyping) {
      setIsTyping(false);
      onTypingStop?.();
    }
  };

  // Handle key press
  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (showMentions) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedMentionIndex(prev => 
          Math.min(prev + 1, filteredUsers.length - 1)
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedMentionIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Tab' || e.key === 'Enter') {
        e.preventDefault();
        if (filteredUsers[selectedMentionIndex]) {
          insertMention(filteredUsers[selectedMentionIndex].user_id);
        }
      } else if (e.key === 'Escape') {
        setShowMentions(false);
      }
      return;
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Insert mention into message
  const insertMention = (userId: string) => {
    const cursorPosition = textareaRef.current?.selectionStart || 0;
    const textBeforeCursor = message.substring(0, cursorPosition);
    const textAfterCursor = message.substring(cursorPosition);
    
    // Replace the partial mention with the complete one
    const beforeMention = textBeforeCursor.replace(/@\w*$/, '');
    const newMessage = `${beforeMention}@${userId} ${textAfterCursor}`;
    
    setMessage(newMessage);
    setShowMentions(false);
    
    // Focus back to textarea
    setTimeout(() => {
      if (textareaRef.current) {
        const newCursorPosition = beforeMention.length + userId.length + 2;
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(newCursorPosition, newCursorPosition);
      }
    }, 0);
  };

  // Detect if message is a command
  const isCommand = message.trim().startsWith('/');

  return (
    <div className={`relative bg-white ${className}`}>
      {/* Mentions dropdown */}
      {showMentions && filteredUsers.length > 0 && (
        <div 
          ref={mentionsRef}
          className="absolute bottom-full left-6 right-6 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto z-10"
        >
          <div className="p-2 text-xs text-gray-500 border-b border-gray-100">
            Mention someone
          </div>
          {filteredUsers.map((user, index) => (
            <button
              key={user.user_id}
              onClick={() => insertMention(user.user_id)}
              className={`w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center space-x-2 ${
                index === selectedMentionIndex ? 'bg-blue-50 text-blue-600' : 'text-gray-900'
              }`}
            >
              <div className={`w-2 h-2 rounded-full ${
                user.is_online ? 'bg-green-400' : 'bg-gray-300'
              }`} />
              <span className="font-medium">@{user.user_id}</span>
              <span className="text-sm text-gray-500">({user.role})</span>
            </button>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="p-4">
        <div className="flex items-end space-x-3">
          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={disabled ? 'Connecting...' : 'Type a message... Use @username to mention someone'}
              disabled={disabled}
              className={`w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                isCommand ? 'font-mono bg-gray-50' : ''
              } ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}`}
              rows={1}
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
            
            {/* Command indicator */}
            {isCommand && (
              <div className="absolute top-2 right-2 text-gray-400">
                <CommandLineIcon className="w-4 h-4" />
              </div>
            )}
          </div>

          {/* Send button */}
          <button
            onClick={handleSubmit}
            disabled={!message.trim() || disabled}
            className={`p-3 rounded-lg transition-colors ${
              message.trim() && !disabled
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Helper text */}
        <div className="mt-2 text-xs text-gray-500">
          {isCommand ? (
            <span className="flex items-center">
              <CommandLineIcon className="w-3 h-3 mr-1" />
              Command mode - type /help for available commands
            </span>
          ) : (
            <span>
              Press Enter to send, Shift+Enter for new line, @ to mention
            </span>
          )}
        </div>
      </div>
    </div>
  );
}