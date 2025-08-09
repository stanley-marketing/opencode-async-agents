/**
 * Enhanced typing indicator component with user names and avatars.
 * Shows who is currently typing with smooth animations and user context.
 */

import React, { useEffect, useState } from 'react';
import { 
  UserIcon, 
  ComputerDesktopIcon,
  EllipsisHorizontalIcon 
} from '@heroicons/react/24/outline';
import { User } from '../../types/chat';

interface TypingIndicatorProps {
  typingUsers: string[];
  users: User[];
  maxDisplayUsers?: number;
  showAvatars?: boolean;
  showAnimation?: boolean;
  className?: string;
}

interface TypingUser {
  user_id: string;
  displayName: string;
  isBot: boolean;
  role: string;
}

export default function TypingIndicator({
  typingUsers,
  users,
  maxDisplayUsers = 3,
  showAvatars = true,
  showAnimation = true,
  className = ''
}: TypingIndicatorProps) {
  const [visibleUsers, setVisibleUsers] = useState<TypingUser[]>([]);
  const [animationPhase, setAnimationPhase] = useState(0);

  // Process typing users and get their info
  useEffect(() => {
    const typingUserInfo = typingUsers
      .map(userId => {
        const user = users.find(u => u.user_id === userId);
        const isBot = user?.role === 'AI Agent' || userId.endsWith('-bot');
        const displayName = userId.replace('-bot', '');
        
        return {
          user_id: userId,
          displayName,
          isBot,
          role: user?.role || 'User'
        };
      })
      .slice(0, maxDisplayUsers);

    setVisibleUsers(typingUserInfo);
  }, [typingUsers, users, maxDisplayUsers]);

  // Animate typing dots
  useEffect(() => {
    if (!showAnimation || visibleUsers.length === 0) return;

    const interval = setInterval(() => {
      setAnimationPhase(prev => (prev + 1) % 4);
    }, 500);

    return () => clearInterval(interval);
  }, [showAnimation, visibleUsers.length]);

  if (visibleUsers.length === 0) return null;

  // Generate typing text
  const getTypingText = () => {
    const displayedCount = visibleUsers.length;
    const totalCount = typingUsers.length;
    const hiddenCount = totalCount - displayedCount;

    if (displayedCount === 1) {
      return `${visibleUsers[0].displayName} is typing`;
    } else if (displayedCount === 2) {
      return `${visibleUsers[0].displayName} and ${visibleUsers[1].displayName} are typing`;
    } else if (displayedCount === 3 && hiddenCount === 0) {
      return `${visibleUsers[0].displayName}, ${visibleUsers[1].displayName}, and ${visibleUsers[2].displayName} are typing`;
    } else {
      const names = visibleUsers.slice(0, 2).map(u => u.displayName).join(', ');
      const remaining = hiddenCount + (displayedCount > 2 ? displayedCount - 2 : 0);
      return `${names} and ${remaining} other${remaining === 1 ? '' : 's'} are typing`;
    }
  };

  // Render typing dots animation
  const renderTypingDots = () => {
    if (!showAnimation) return '...';

    return (
      <span className="inline-flex space-x-1 ml-1">
        {[0, 1, 2].map(index => (
          <span
            key={index}
            className={`w-1 h-1 bg-gray-400 rounded-full transition-opacity duration-300 ${
              animationPhase === index || animationPhase === 3 ? 'opacity-100' : 'opacity-30'
            }`}
            style={{
              animationDelay: `${index * 150}ms`
            }}
          />
        ))}
      </span>
    );
  };

  return (
    <div className={`flex items-center space-x-2 px-4 py-2 bg-gray-50 border-t border-gray-100 ${className}`}>
      {/* User avatars */}
      {showAvatars && (
        <div className="flex -space-x-2">
          {visibleUsers.map((user, index) => {
            const Icon = user.isBot ? ComputerDesktopIcon : UserIcon;
            
            return (
              <div
                key={user.user_id}
                className={`relative w-6 h-6 rounded-full border-2 border-white flex items-center justify-center ${
                  user.isBot 
                    ? 'bg-purple-100 text-purple-600' 
                    : 'bg-blue-100 text-blue-600'
                }`}
                style={{ zIndex: visibleUsers.length - index }}
                title={`${user.displayName} (${user.role})`}
              >
                <Icon className="w-3 h-3" />
                
                {/* Typing indicator dot */}
                <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              </div>
            );
          })}
          
          {/* Show count if more users are typing */}
          {typingUsers.length > maxDisplayUsers && (
            <div className="w-6 h-6 rounded-full border-2 border-white bg-gray-200 text-gray-600 flex items-center justify-center text-xs font-medium">
              +{typingUsers.length - maxDisplayUsers}
            </div>
          )}
        </div>
      )}

      {/* Typing text and animation */}
      <div className="flex items-center text-sm text-gray-600">
        <EllipsisHorizontalIcon className="w-4 h-4 mr-1 text-gray-400" />
        <span>{getTypingText()}</span>
        {renderTypingDots()}
      </div>

      {/* Pulse animation background */}
      {showAnimation && (
        <div className="absolute inset-0 bg-blue-50 opacity-20 animate-pulse pointer-events-none" />
      )}
    </div>
  );
}

// Simplified typing indicator for minimal use cases
export function SimpleTypingIndicator({ 
  isTyping, 
  className = '' 
}: { 
  isTyping: boolean; 
  className?: string; 
}) {
  const [dots, setDots] = useState('');

  useEffect(() => {
    if (!isTyping) {
      setDots('');
      return;
    }

    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '';
        return prev + '.';
      });
    }, 500);

    return () => clearInterval(interval);
  }, [isTyping]);

  if (!isTyping) return null;

  return (
    <div className={`flex items-center space-x-2 text-sm text-gray-500 ${className}`}>
      <div className="flex space-x-1">
        <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span>Typing{dots}</span>
    </div>
  );
}

// Typing indicator for individual messages
export function MessageTypingIndicator({ 
  userName, 
  isBot = false,
  className = '' 
}: { 
  userName: string; 
  isBot?: boolean;
  className?: string; 
}) {
  return (
    <div className={`flex items-center space-x-2 px-4 py-2 ${className}`}>
      {/* Avatar */}
      <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
        isBot ? 'bg-purple-100 text-purple-600' : 'bg-gray-100 text-gray-600'
      }`}>
        {isBot ? (
          <ComputerDesktopIcon className="w-3 h-3" />
        ) : (
          <UserIcon className="w-3 h-3" />
        )}
      </div>

      {/* Typing bubble */}
      <div className="bg-gray-200 rounded-lg px-3 py-2 flex items-center space-x-1">
        <span className="text-sm text-gray-600">{userName.replace('-bot', '')} is typing</span>
        <div className="flex space-x-1">
          <div className="w-1 h-1 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-1 h-1 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-1 h-1 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}