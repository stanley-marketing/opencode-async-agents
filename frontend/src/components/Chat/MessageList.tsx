/**
 * Message list component for displaying chat messages.
 * Handles message rendering, scrolling, and reply functionality.
 */

import React, { useEffect, useRef, useState } from 'react';
import { format, isToday, isYesterday } from 'date-fns';
import { ChatMessage } from '../../types/chat';
import MessageItem from './MessageItem';

interface MessageListProps {
  messages: ChatMessage[];
  currentUserId?: string;
  className?: string;
}

export default function MessageList({
  messages,
  currentUserId,
  className = ''
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [replyToMessage, setReplyToMessage] = useState<ChatMessage | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (shouldAutoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, shouldAutoScroll]);

  // Check if user is near bottom to determine auto-scroll behavior
  const handleScroll = () => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setShouldAutoScroll(isNearBottom);
  };

  // Group messages by date
  const groupMessagesByDate = (messages: ChatMessage[]) => {
    const groups: { [key: string]: ChatMessage[] } = {};
    
    messages.forEach(message => {
      const date = new Date(message.timestamp);
      const dateKey = format(date, 'yyyy-MM-dd');
      
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      groups[dateKey].push(message);
    });
    
    return groups;
  };

  // Format date for display
  const formatDateHeader = (dateString: string) => {
    const date = new Date(dateString);
    
    if (isToday(date)) {
      return 'Today';
    } else if (isYesterday(date)) {
      return 'Yesterday';
    } else {
      return format(date, 'MMMM d, yyyy');
    }
  };

  // Handle reply to message
  const handleReplyToMessage = (message: ChatMessage) => {
    setReplyToMessage(message);
    // Focus on message input (would need to be passed as prop or use context)
  };

  // Handle mention click
  const handleMentionClick = (mention: string) => {
    // Scroll to user in sidebar or highlight them
    console.log('Mention clicked:', mention);
  };

  const messageGroups = groupMessagesByDate(messages);
  const sortedDates = Object.keys(messageGroups).sort();

  if (messages.length === 0) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center text-gray-500">
          <div className="text-6xl mb-4">💬</div>
          <h3 className="text-lg font-medium mb-2">No messages yet</h3>
          <p className="text-sm">
            Start a conversation with your AI agents or team members
          </p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`flex-1 overflow-y-auto px-6 py-4 space-y-4 ${className}`}
      onScroll={handleScroll}
    >
      {sortedDates.map(dateKey => (
        <div key={dateKey}>
          {/* Date separator */}
          <div className="flex items-center justify-center my-6">
            <div className="flex-1 border-t border-gray-200"></div>
            <div className="px-4 text-sm text-gray-500 bg-gray-50 rounded-full">
              {formatDateHeader(dateKey)}
            </div>
            <div className="flex-1 border-t border-gray-200"></div>
          </div>

          {/* Messages for this date */}
          <div className="space-y-4">
            {messageGroups[dateKey].map((message, index) => {
              const prevMessage = index > 0 ? messageGroups[dateKey][index - 1] : null;
              const isConsecutive = prevMessage && 
                prevMessage.sender === message.sender &&
                new Date(message.timestamp).getTime() - new Date(prevMessage.timestamp).getTime() < 300000; // 5 minutes

              return (
                <MessageItem
                  key={message.id}
                  message={message}
                  isOwn={message.sender === currentUserId}
                  isConsecutive={isConsecutive}
                  onReply={handleReplyToMessage}
                  onMentionClick={handleMentionClick}
                />
              );
            })}
          </div>
        </div>
      ))}

      {/* Reply preview */}
      {replyToMessage && (
        <div className="sticky bottom-0 bg-blue-50 border border-blue-200 rounded-lg p-3 mx-4 mb-2">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="text-sm text-blue-600 font-medium">
                Replying to {replyToMessage.sender}
              </div>
              <div className="text-sm text-gray-600 truncate">
                {replyToMessage.text}
              </div>
            </div>
            <button
              onClick={() => setReplyToMessage(null)}
              className="ml-2 text-blue-400 hover:text-blue-600"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  );
}