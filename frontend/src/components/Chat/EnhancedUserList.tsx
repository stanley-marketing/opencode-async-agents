/**
 * Enhanced user list component with presence indicators and real-time status.
 * Shows online users, typing indicators, and detailed user information.
 */

import React, { useState, useMemo } from 'react';
import { User } from '../../types/chat';
import { 
  UserIcon, 
  ComputerDesktopIcon,
  MagnifyingGlassIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';
import PresenceIndicator from '../advanced/PresenceIndicator';

interface EnhancedUserListProps {
  users: User[];
  typingUsers?: Set<string>;
  currentUserId?: string;
  onUserClick?: (user: User) => void;
  showSearch?: boolean;
  showSections?: boolean;
  className?: string;
}

interface UserSection {
  title: string;
  users: User[];
  icon: React.ComponentType<any>;
  color: string;
  defaultExpanded: boolean;
}

export default function EnhancedUserList({
  users,
  typingUsers = new Set(),
  currentUserId,
  onUserClick,
  showSearch = true,
  showSections = true,
  className = ''
}: EnhancedUserListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['Online', 'AI Agents'])
  );

  // Filter users based on search query
  const filteredUsers = useMemo(() => {
    if (!searchQuery.trim()) return users;
    
    const query = searchQuery.toLowerCase();
    return users.filter(user => 
      user.user_id.toLowerCase().includes(query) ||
      user.role.toLowerCase().includes(query)
    );
  }, [users, searchQuery]);

  // Organize users into sections
  const userSections = useMemo((): UserSection[] => {
    const onlineUsers = filteredUsers.filter(user => user.is_online && !user.role.includes('bot'));
    const offlineUsers = filteredUsers.filter(user => !user.is_online && !user.role.includes('bot'));
    const agents = filteredUsers.filter(user => user.role.includes('bot') || user.role === 'AI Agent');

    const sections: UserSection[] = [];

    if (onlineUsers.length > 0) {
      sections.push({
        title: 'Online',
        users: onlineUsers.sort((a, b) => a.user_id.localeCompare(b.user_id)),
        icon: UserIcon,
        color: 'text-green-600',
        defaultExpanded: true
      });
    }

    if (agents.length > 0) {
      sections.push({
        title: 'AI Agents',
        users: agents.sort((a, b) => a.user_id.localeCompare(b.user_id)),
        icon: ComputerDesktopIcon,
        color: 'text-purple-600',
        defaultExpanded: true
      });
    }

    if (offlineUsers.length > 0) {
      sections.push({
        title: 'Offline',
        users: offlineUsers.sort((a, b) => a.user_id.localeCompare(b.user_id)),
        icon: UserIcon,
        color: 'text-gray-400',
        defaultExpanded: false
      });
    }

    return sections;
  }, [filteredUsers]);

  // Toggle section expansion
  const toggleSection = (sectionTitle: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionTitle)) {
        newSet.delete(sectionTitle);
      } else {
        newSet.add(sectionTitle);
      }
      return newSet;
    });
  };

  // Get user status
  const getUserStatus = (user: User) => {
    if (typingUsers.has(user.user_id)) return 'typing';
    if (user.is_online) return 'online';
    return 'offline';
  };

  // Render individual user
  const renderUser = (user: User) => {
    const isCurrentUser = user.user_id === currentUserId;
    const isTyping = typingUsers.has(user.user_id);
    const status = getUserStatus(user);

    return (
      <button
        key={user.user_id}
        onClick={() => onUserClick?.(user)}
        className={`w-full text-left p-3 rounded-lg transition-all duration-200 hover:bg-gray-50 ${
          isCurrentUser ? 'bg-blue-50 border border-blue-200' : ''
        }`}
        title={`${user.user_id} (${user.role})`}
      >
        <div className="flex items-center space-x-3">
          {/* User presence indicator */}
          <PresenceIndicator
            user={user}
            status={status as any}
            isTyping={isTyping}
            size="md"
            showLabel={false}
          />

          {/* User info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <span className={`font-medium text-sm truncate ${
                isCurrentUser ? 'text-blue-700' : 'text-gray-900'
              }`}>
                {user.user_id.replace('-bot', '')}
                {isCurrentUser && (
                  <span className="ml-1 text-xs text-blue-500">(you)</span>
                )}
              </span>
              
              {user.role.includes('bot') && (
                <span className="text-xs bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded-full">
                  AI
                </span>
              )}
            </div>
            
            <div className="text-xs text-gray-500 truncate">
              {user.role}
            </div>
            
            {/* Activity status */}
            {isTyping ? (
              <div className="text-xs text-blue-600 flex items-center mt-1">
                <div className="flex space-x-1 mr-2">
                  <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" />
                  <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                typing...
              </div>
            ) : user.is_online ? (
              <div className="text-xs text-green-600 mt-1">
                Active now
              </div>
            ) : (
              <div className="text-xs text-gray-400 mt-1">
                Last seen {new Date(user.last_activity).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </div>
            )}
          </div>

          {/* Message count badge */}
          {user.message_count > 0 && (
            <div className="flex-shrink-0">
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-600">
                {user.message_count}
              </span>
            </div>
          )}
        </div>
      </button>
    );
  };

  // Render section
  const renderSection = (section: UserSection) => {
    const isExpanded = expandedSections.has(section.title);
    const SectionIcon = section.icon;

    return (
      <div key={section.title} className="mb-4">
        {/* Section header */}
        <button
          onClick={() => toggleSection(section.title)}
          className="w-full flex items-center justify-between p-2 text-left hover:bg-gray-50 rounded-lg transition-colors"
        >
          <div className="flex items-center space-x-2">
            <SectionIcon className={`w-4 h-4 ${section.color}`} />
            <span className="font-medium text-sm text-gray-700">
              {section.title}
            </span>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
              {section.users.length}
            </span>
          </div>
          
          {isExpanded ? (
            <ChevronDownIcon className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRightIcon className="w-4 h-4 text-gray-400" />
          )}
        </button>

        {/* Section content */}
        {isExpanded && (
          <div className="mt-2 space-y-1">
            {section.users.map(renderUser)}
          </div>
        )}
      </div>
    );
  };

  const totalUsers = users.length;
  const onlineCount = users.filter(u => u.is_online).length;

  return (
    <div className={`h-full flex flex-col bg-white ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-900">
            Team ({totalUsers})
          </h2>
          <button
            className="text-gray-400 hover:text-gray-600 p-1 rounded"
            title="Settings"
          >
            <Cog6ToothIcon className="w-4 h-4" />
          </button>
        </div>
        
        {/* Status summary */}
        <div className="text-sm text-gray-500 mb-3">
          <span className="inline-flex items-center">
            <div className="w-2 h-2 bg-green-400 rounded-full mr-1" />
            {onlineCount} online
          </span>
          {typingUsers.size > 0 && (
            <span className="ml-3 inline-flex items-center">
              <div className="w-2 h-2 bg-blue-400 rounded-full mr-1 animate-pulse" />
              {typingUsers.size} typing
            </span>
          )}
        </div>

        {/* Search */}
        {showSearch && (
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        )}
      </div>

      {/* User list */}
      <div className="flex-1 overflow-y-auto p-4">
        {showSections ? (
          <div>
            {userSections.map(renderSection)}
          </div>
        ) : (
          <div className="space-y-1">
            {filteredUsers.map(renderUser)}
          </div>
        )}

        {filteredUsers.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <UserIcon className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p className="text-sm">
              {searchQuery ? 'No users found' : 'No users online'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}