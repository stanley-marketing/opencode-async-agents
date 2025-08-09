/**
 * Typing indicator component.
 * Shows which users are currently typing.
 */

import React from 'react';
import { User } from '../../types/chat';

interface TypingIndicatorProps {
  typingUsers: string[];
  users: User[];
  className?: string;
}

export default function TypingIndicator({
  typingUsers,
  users,
  className = ''
}: TypingIndicatorProps) {
  if (typingUsers.length === 0) {
    return null;
  }

  // Get user display names
  const getDisplayName = (userId: string) => {
    const user = users.find(u => u.user_id === userId);
    return user ? user.user_id.replace('-bot', '') : userId;
  };

  // Format typing text
  const formatTypingText = () => {
    const displayNames = typingUsers.map(getDisplayName);
    
    if (displayNames.length === 1) {
      return `${displayNames[0]} is typing...`;
    } else if (displayNames.length === 2) {
      return `${displayNames[0]} and ${displayNames[1]} are typing...`;
    } else if (displayNames.length === 3) {
      return `${displayNames[0]}, ${displayNames[1]}, and ${displayNames[2]} are typing...`;
    } else {
      return `${displayNames[0]}, ${displayNames[1]}, and ${displayNames.length - 2} others are typing...`;
    }
  };

  return (
    <div className={`flex items-center space-x-2 text-sm text-gray-500 ${className}`}>
      {/* Animated dots */}
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
      </div>
      
      {/* Typing text */}
      <span className="italic">
        {formatTypingText()}
      </span>
    </div>
  );
}