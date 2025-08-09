/**
 * User list component showing online users and their status.
 * Displays agents, developers, and other team members.
 */

import React from 'react';
import { User } from '../../types/chat';
import { 
  UserIcon, 
  ComputerDesktopIcon,
  ClockIcon,
  ChatBubbleLeftIcon
} from '@heroicons/react/24/outline';
import { format, formatDistanceToNow } from 'date-fns';

interface UserListProps {
  users: User[];
  currentUserId?: string;
  className?: string;
}

export default function UserList({
  users,
  currentUserId,
  className = ''
}: UserListProps) {
  // Separate users by type
  const agents = users.filter(user => user.role.includes('bot') || user.role === 'agent');
  const humans = users.filter(user => !user.role.includes('bot') && user.role !== 'agent');
  
  // Sort users by online status and activity
  const sortUsers = (userList: User[]) => {
    return userList.sort((a, b) => {
      // Online users first
      if (a.is_online !== b.is_online) {
        return a.is_online ? -1 : 1;
      }
      
      // Then by last activity
      return new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime();
    });
  };

  const sortedAgents = sortUsers(agents);
  const sortedHumans = sortUsers(humans);

  const formatLastActivity = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMinutes = (now.getTime() - date.getTime()) / (1000 * 60);
    
    if (diffInMinutes < 1) {
      return 'Just now';
    } else if (diffInMinutes < 60) {
      return `${Math.floor(diffInMinutes)}m ago`;
    } else {
      return formatDistanceToNow(date, { addSuffix: true });
    }
  };

  const getRoleColor = (role: string) => {
    const roleColors = {
      'developer': 'text-blue-600 bg-blue-50',
      'designer': 'text-purple-600 bg-purple-50',
      'tester': 'text-green-600 bg-green-50',
      'manager': 'text-orange-600 bg-orange-50',
      'devops': 'text-red-600 bg-red-50',
      'agent': 'text-indigo-600 bg-indigo-50',
      'bot': 'text-indigo-600 bg-indigo-50'
    };
    
    const normalizedRole = role.toLowerCase().replace('-bot', '');
    return roleColors[normalizedRole] || 'text-gray-600 bg-gray-50';
  };

  const UserItem = ({ user, isAgent = false }: { user: User; isAgent?: boolean }) => {
    const isCurrentUser = user.user_id === currentUserId;
    const displayName = user.user_id.replace('-bot', '');
    const roleColor = getRoleColor(user.role);
    
    return (
      <div className={`p-3 rounded-lg transition-colors ${
        isCurrentUser ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50'
      }`}>
        <div className="flex items-center space-x-3">
          {/* Avatar */}
          <div className="relative">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              isAgent ? 'bg-indigo-100 text-indigo-600' : 'bg-gray-100 text-gray-600'
            }`}>
              {isAgent ? (
                <ComputerDesktopIcon className="w-5 h-5" />
              ) : (
                <UserIcon className="w-5 h-5" />
              )}
            </div>
            
            {/* Online status indicator */}
            <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white ${
              user.is_online ? 'bg-green-400' : 'bg-gray-300'
            }`} />
          </div>

          {/* User info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <span className={`font-medium truncate ${
                isCurrentUser ? 'text-blue-900' : 'text-gray-900'
              }`}>
                {displayName}
                {isCurrentUser && (
                  <span className="ml-1 text-xs text-blue-600">(you)</span>
                )}
              </span>
              
              {isAgent && (
                <span className="text-xs bg-indigo-100 text-indigo-600 px-1.5 py-0.5 rounded-full">
                  AI
                </span>
              )}
            </div>
            
            {/* Role */}
            <div className="flex items-center space-x-2 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded-full ${roleColor}`}>
                {user.role.replace('-bot', '')}
              </span>
            </div>
            
            {/* Activity info */}
            <div className="flex items-center space-x-2 mt-1 text-xs text-gray-500">
              <ClockIcon className="w-3 h-3" />
              <span>{formatLastActivity(user.last_activity)}</span>
              
              {user.message_count > 0 && (
                <>
                  <span>•</span>
                  <ChatBubbleLeftIcon className="w-3 h-3" />
                  <span>{user.message_count} messages</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (users.length === 0) {
    return (
      <div className={`flex flex-col h-full ${className}`}>
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Team Members</h2>
        </div>
        
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center text-gray-500">
            <UserIcon className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-sm">No one is online</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full bg-white ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Team Members</h2>
        <p className="text-sm text-gray-500">
          {users.filter(u => u.is_online).length} online
        </p>
      </div>

      {/* User lists */}
      <div className="flex-1 overflow-y-auto">
        {/* AI Agents */}
        {sortedAgents.length > 0 && (
          <div className="p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
              <ComputerDesktopIcon className="w-4 h-4 mr-2" />
              AI Agents ({sortedAgents.length})
            </h3>
            <div className="space-y-2">
              {sortedAgents.map(user => (
                <UserItem key={user.user_id} user={user} isAgent={true} />
              ))}
            </div>
          </div>
        )}

        {/* Human Users */}
        {sortedHumans.length > 0 && (
          <div className="p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
              <UserIcon className="w-4 h-4 mr-2" />
              Team Members ({sortedHumans.length})
            </h3>
            <div className="space-y-2">
              {sortedHumans.map(user => (
                <UserItem key={user.user_id} user={user} isAgent={false} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer with connection info */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="text-xs text-gray-500 text-center">
          <div className="flex items-center justify-center space-x-1">
            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
            <span>Connected to OpenCode Chat</span>
          </div>
        </div>
      </div>
    </div>
  );
}