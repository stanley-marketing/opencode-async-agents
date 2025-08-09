/**
 * Enhanced message input component with advanced mention support and accessibility.
 * Integrates with the new mention autocomplete system and provides better UX.
 */

import React, { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react';
import { PaperAirplaneIcon, CommandLineIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { useChatUsers } from '../../stores/chatStore';
import { useMentions } from '../../hooks/useMentions';
import MentionAutocomplete from '../advanced/MentionAutocomplete';
import { ChatMessage } from '../../types/chat';

interface EnhancedMessageInputProps {
  onSendMessage: (text: string, replyTo?: number) => void;
  onTypingStart?: () => void;
  onTypingStop?: () => void;
  disabled?: boolean;
  replyTo?: number;
  replyToMessage?: ChatMessage;
  onCancelReply?: () => void;
  agentNames?: string[];
  availableCommands?: string[];
  className?: string;
}

export default function EnhancedMessageInput({
  onSendMessage,
  onTypingStart,
  onTypingStop,
  disabled = false,
  replyTo,
  replyToMessage,
  onCancelReply,
  agentNames = [],
  availableCommands = ['help', 'status', 'clear', 'users'],
  className = ''
}: EnhancedMessageInputProps) {
  const [message, setMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [cursorPosition, setCursorPosition] = useState(0);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const users = useChatUsers();

  // Initialize mentions hook
  const {
    suggestions,
    isShowingSuggestions,
    selectedIndex,
    mentionQuery,
    mentionStartPos,
    handleTextChange,
    selectSuggestion,
    navigateSuggestions,
    hideSuggestions,
    insertMention
  } = useMentions({
    users,
    agentNames,
    commands: availableCommands,
    maxSuggestions: 8
  });

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
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

  // Handle text changes and cursor position
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;
    const newCursorPos = e.target.selectionStart || 0;
    
    setMessage(newText);
    setCursorPosition(newCursorPos);
    
    // Update mentions
    handleTextChange(newText, newCursorPos);
  }, [handleTextChange]);

  // Handle cursor position changes
  const handleSelectionChange = useCallback(() => {
    if (textareaRef.current) {
      const newCursorPos = textareaRef.current.selectionStart || 0;
      setCursorPosition(newCursorPos);
      handleTextChange(message, newCursorPos);
    }
  }, [message, handleTextChange]);

  // Handle message submission
  const handleSubmit = useCallback(() => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || disabled) return;

    onSendMessage(trimmedMessage, replyTo);
    setMessage('');
    hideSuggestions();
    
    // Stop typing indicator
    if (isTyping) {
      setIsTyping(false);
      onTypingStop?.();
    }

    // Focus back to input
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 0);
  }, [message, disabled, onSendMessage, replyTo, hideSuggestions, isTyping, onTypingStop]);

  // Handle key press events
  const handleKeyPress = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle mention autocomplete navigation
    if (isShowingSuggestions) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          navigateSuggestions('down');
          break;
        case 'ArrowUp':
          e.preventDefault();
          navigateSuggestions('up');
          break;
        case 'Tab':
        case 'Enter':
          if (!e.shiftKey) {
            e.preventDefault();
            const selectedMention = selectSuggestion(selectedIndex);
            if (selectedMention) {
              const newMessage = insertMention(
                message,
                selectedMention,
                mentionStartPos,
                cursorPosition
              );
              setMessage(newMessage);
              
              // Set cursor position after mention
              setTimeout(() => {
                if (textareaRef.current) {
                  const newPos = mentionStartPos + selectedMention.length + 1;
                  textareaRef.current.setSelectionRange(newPos, newPos);
                  setCursorPosition(newPos);
                }
              }, 0);
            }
          }
          break;
        case 'Escape':
          e.preventDefault();
          hideSuggestions();
          break;
      }
      return;
    }

    // Handle normal input
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [
    isShowingSuggestions,
    navigateSuggestions,
    selectSuggestion,
    selectedIndex,
    insertMention,
    message,
    mentionStartPos,
    cursorPosition,
    hideSuggestions,
    handleSubmit
  ]);

  // Handle mention selection from autocomplete
  const handleMentionSelect = useCallback((index: number) => {
    const selectedMention = selectSuggestion(index);
    if (selectedMention) {
      const newMessage = insertMention(
        message,
        selectedMention,
        mentionStartPos,
        cursorPosition
      );
      setMessage(newMessage);
      
      // Set cursor position after mention
      setTimeout(() => {
        if (textareaRef.current) {
          const newPos = mentionStartPos + selectedMention.length + 1;
          textareaRef.current.setSelectionRange(newPos, newPos);
          setCursorPosition(newPos);
          textareaRef.current.focus();
        }
      }, 0);
    }
  }, [selectSuggestion, insertMention, message, mentionStartPos, cursorPosition]);

  // Detect if message is a command
  const isCommand = message.trim().startsWith('/');

  // Get placeholder text
  const getPlaceholder = () => {
    if (disabled) return 'Connecting...';
    if (replyToMessage) return `Reply to ${replyToMessage.sender}...`;
    return 'Type a message... Use @username to mention someone or /command for commands';
  };

  return (
    <div className={`relative bg-white ${className}`}>
      {/* Reply indicator */}
      {replyToMessage && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-100 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm">
            <span className="text-blue-600 font-medium">
              Replying to {replyToMessage.sender}
            </span>
            <span className="text-gray-500 truncate max-w-xs">
              {replyToMessage.text}
            </span>
          </div>
          {onCancelReply && (
            <button
              onClick={onCancelReply}
              className="text-gray-400 hover:text-gray-600 p-1"
              aria-label="Cancel reply"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      {/* Mention autocomplete */}
      {isShowingSuggestions && (
        <MentionAutocomplete
          suggestions={suggestions}
          selectedIndex={selectedIndex}
          onSelect={handleMentionSelect}
          onClose={hideSuggestions}
          className="absolute bottom-full left-4 right-4 mb-2"
        />
      )}

      {/* Input area */}
      <div className="p-4">
        <div className="flex items-end space-x-3">
          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={handleInputChange}
              onKeyDown={handleKeyPress}
              onSelect={handleSelectionChange}
              onBlur={handleSelectionChange}
              placeholder={getPlaceholder()}
              disabled={disabled}
              className={`w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors ${
                isCommand ? 'font-mono bg-gray-50' : ''
              } ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}`}
              rows={1}
              style={{ minHeight: '48px', maxHeight: '120px' }}
              aria-label="Message input"
              aria-describedby={isShowingSuggestions ? 'mention-suggestions' : undefined}
            />
            
            {/* Command indicator */}
            {isCommand && (
              <div className="absolute top-2 right-2 text-gray-400" title="Command mode">
                <CommandLineIcon className="w-4 h-4" />
              </div>
            )}

            {/* Character count for long messages */}
            {message.length > 1000 && (
              <div className="absolute bottom-1 right-2 text-xs text-gray-400">
                {message.length}/2000
              </div>
            )}
          </div>

          {/* Send button */}
          <button
            onClick={handleSubmit}
            disabled={!message.trim() || disabled}
            className={`p-3 rounded-lg transition-all duration-200 ${
              message.trim() && !disabled
                ? 'bg-blue-600 text-white hover:bg-blue-700 transform hover:scale-105'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
            aria-label="Send message"
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Helper text */}
        <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
          <span>
            {isCommand ? (
              <span className="flex items-center">
                <CommandLineIcon className="w-3 h-3 mr-1" />
                Command mode - type /help for available commands
              </span>
            ) : (
              <span>
                Press Enter to send, Shift+Enter for new line, @ to mention, / for commands
              </span>
            )}
          </span>
          
          {isTyping && (
            <span className="text-blue-500 flex items-center">
              <span className="w-1 h-1 bg-blue-500 rounded-full animate-pulse mr-1" />
              Typing...
            </span>
          )}
        </div>
      </div>
    </div>
  );
}