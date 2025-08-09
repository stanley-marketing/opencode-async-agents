/**
 * User presence indicator component showing online/offline/typing status.
 * Provides real-time visual feedback for user activity and availability.
 */

import React, { useEffect, useState } from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import { 
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  EllipsisHorizontalIcon,
  UserIcon,
  ComputerDesktopIcon
} from '@heroicons/react/24/outline';
import { User } from '../../types/chat';

export type PresenceStatus = 'online' | 'away' | 'busy' | 'offline' | 'typing';

interface PresenceIndicatorProps {
  user: User;
  status?: PresenceStatus;
  isTyping?: boolean;
  showLabel?: boolean;
  showLastSeen?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onClick?: () => void;
}

interface PresenceConfig {
  color: string;
  bgColor: string;
  icon: React.ComponentType<any>;
  label: string;
  pulse?: boolean;
}

const PRESENCE_CONFIG: Record<PresenceStatus, PresenceConfig> = {
  online: {
    color: 'text-green-600',
    bgColor: 'bg-green-500',
    icon: CheckCircleIcon,
    label: 'Online',
    pulse: false
  },
  away: {
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-500',
    icon: ClockIcon,
    label: 'Away',
    pulse: false
  },
  busy: {
    color: 'text-red-600',
    bgColor: 'bg-red-500',
    icon: XCircleIcon,
    label: 'Busy',
    pulse: false
  },
  offline: {
    color: 'text-gray-400',
    bgColor: 'bg-gray-400',
    icon: XCircleIcon,
    label: 'Offline',
    pulse: false
  },
  typing: {
    color: 'text-blue-600',
    bgColor: 'bg-blue-500',
    icon: EllipsisHorizontalIcon,
    label: 'Typing...',
    pulse: true
  }
};

const SIZE_CONFIG = {
  sm: {
    indicator: 'w-2 h-2',
    avatar: 'w-6 h-6',
    icon: 'w-3 h-3',
    text: 'text-xs'
  },
  md: {
    indicator: 'w-3 h-3',
    avatar: 'w-8 h-8',
    icon: 'w-4 h-4',
    text: 'text-sm'
  },
  lg: {
    indicator: 'w-4 h-4',
    avatar: 'w-10 h-10',
    icon: 'w-5 h-5',
    text: 'text-base'
  }
};

export default function PresenceIndicator({
  user,
  status,
  isTyping = false,
  showLabel = false,
  showLastSeen = false,
  size = 'md',
  className = '',
  onClick
}: PresenceIndicatorProps) {
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update current time every minute for relative timestamps
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  // Determine actual status
  const actualStatus: PresenceStatus = isTyping 
    ? 'typing' 
    : status || (user.is_online ? 'online' : 'offline');

  const config = PRESENCE_CONFIG[actualStatus];
  const sizeConfig = SIZE_CONFIG[size];
  const isBot = user.role === 'AI Agent' || user.user_id.endsWith('-bot');
  const displayName = user.user_id.replace('-bot', '');

  // Format last activity
  const getLastSeenText = () => {
    if (!user.last_activity) return 'Never';
    
    const lastActivity = new Date(user.last_activity);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - lastActivity.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    
    return formatDistanceToNow(lastActivity, { addSuffix: true });
  };

  const Component = onClick ? 'button' : 'div';

  return (
    <Component
      onClick={onClick}
      className={`flex items-center space-x-2 ${onClick ? 'hover:bg-gray-50 rounded-lg p-1 transition-colors' : ''} ${className}`}
    >
      {/* Avatar with presence indicator */}
      <div className="relative flex-shrink-0">
        <div className={`${sizeConfig.avatar} rounded-full flex items-center justify-center ${
          isBot 
            ? 'bg-purple-100 text-purple-600' 
            : 'bg-gray-100 text-gray-600'
        }`}>
          {isBot ? (
            <ComputerDesktopIcon className={sizeConfig.icon} />
          ) : (
            <UserIcon className={sizeConfig.icon} />
          )}
        </div>
        
        {/* Presence dot */}
        <div className={`absolute -bottom-0.5 -right-0.5 ${sizeConfig.indicator} rounded-full border-2 border-white ${config.bgColor} ${
          config.pulse ? 'animate-pulse' : ''
        }`} />
      </div>

      {/* User info */}
      {(showLabel || showLastSeen) && (
        <div className="flex-1 min-w-0">
          {showLabel && (
            <div className="flex items-center space-x-2">
              <span className={`font-medium ${sizeConfig.text} text-gray-900 truncate`}>
                {displayName}
              </span>
              
              {isBot && (
                <span className="text-xs bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded-full">
                  AI
                </span>
              )}
              
              <span className={`${sizeConfig.text} ${config.color} flex items-center space-x-1`}>
                <config.icon className="w-3 h-3" />
                <span>{config.label}</span>
              </span>
            </div>
          )}
          
          {showLastSeen && actualStatus !== 'online' && actualStatus !== 'typing' && (
            <div className={`${sizeConfig.text} text-gray-500 truncate`}>
              Last seen {getLastSeenText()}
            </div>
          )}
          
          {showLastSeen && actualStatus === 'online' && user.connected_at && (
            <div className={`${sizeConfig.text} text-gray-500 truncate`}>
              Online since {format(new Date(user.connected_at), 'HH:mm')}
            </div>
          )}
        </div>
      )}

      {/* Typing animation */}
      {isTyping && (
        <div className="flex space-x-1">
          <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      )}
    </Component>
  );
}

// Utility component for just the presence dot
export function PresenceDot({ 
  status, 
  isTyping = false, 
  size = 'md',
  className = '' 
}: {
  status: PresenceStatus;
  isTyping?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const actualStatus = isTyping ? 'typing' : status;
  const config = PRESENCE_CONFIG[actualStatus];
  const sizeConfig = SIZE_CONFIG[size];

  return (
    <div 
      className={`${sizeConfig.indicator} rounded-full ${config.bgColor} ${
        config.pulse ? 'animate-pulse' : ''
      } ${className}`}
      title={config.label}
    />
  );
}

// Utility component for status text only
export function PresenceText({ 
  status, 
  isTyping = false, 
  size = 'md',
  className = '' 
}: {
  status: PresenceStatus;
  isTyping?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const actualStatus = isTyping ? 'typing' : status;
  const config = PRESENCE_CONFIG[actualStatus];
  const sizeConfig = SIZE_CONFIG[size];

  return (
    <span className={`${sizeConfig.text} ${config.color} flex items-center space-x-1 ${className}`}>
      <config.icon className="w-3 h-3" />
      <span>{config.label}</span>
    </span>
  );
}