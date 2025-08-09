/**
 * Main chat interface component.
 * Provides real-time messaging with agent communication capabilities.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useChatStore, useChatActions, useIsConnected } from '../../stores/chatStore';
import { ChatMessage } from '../../types/chat';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import UserList from './UserList';
import ConnectionStatus from './ConnectionStatus';
import TypingIndicator from './TypingIndicator';

interface ChatInterfaceProps {
  websocketUrl: string;
  userId: string;
  userRole: string;
  className?: string;
}

export default function ChatInterface({
  websocketUrl,
  userId,
  userRole,
  className = ''
}: ChatInterfaceProps) {
  const [isInitialized, setIsInitialized] = useState(false);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const { messages, users, typingUsers, currentUser } = useChatStore();
  const {
    addMessage,
    addUser,
    removeUser,
    setUserTyping,
    setCurrentUser,
    setConnectionStatus,
    setConnectionError,
    setReconnectAttempts,
    setLastConnected
  } = useChatActions();
  
  const isConnected = useIsConnected();

  // WebSocket connection and message handling
  const {
    connectionState,
    sendMessage,
    sendTyping,
    connect,
    disconnect
  } = useWebSocket({
    url: websocketUrl,
    userId,
    userRole,
    onMessage: (message: ChatMessage) => {
      addMessage(message);
    },
    onUserStatusChange: (user, status) => {
      if (status === 'connected') {
        addUser({ ...user, is_online: true });
      } else {
        removeUser(user.user_id);
      }
    },
    onTypingChange: (typing) => {
      setUserTyping(typing.user_id, typing.is_typing);
      
      // Clear typing indicator after 3 seconds
      if (typing.is_typing) {
        setTimeout(() => {
          setUserTyping(typing.user_id, false);
        }, 3000);
      }
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
      setConnectionError(error);
    }
  });

  // Sync connection state with store
  useEffect(() => {
    setConnectionStatus(connectionState.status);
    setConnectionError(connectionState.error);
    setReconnectAttempts(connectionState.reconnectAttempts);
    setLastConnected(connectionState.lastConnected);
  }, [connectionState, setConnectionStatus, setConnectionError, setReconnectAttempts, setLastConnected]);

  // Set current user
  useEffect(() => {
    setCurrentUser({ user_id: userId, role: userRole });
  }, [userId, userRole, setCurrentUser]);

  // Auto-connect on mount
  useEffect(() => {
    if (!isInitialized) {
      connect();
      setIsInitialized(true);
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, isInitialized]);

  // Handle message sending
  const handleSendMessage = (text: string, replyTo?: number) => {
    if (!isConnected) {
      console.warn('Cannot send message: not connected');
      return;
    }

    sendMessage(text, replyTo);
  };

  // Handle typing indicators
  const handleTypingStart = () => {
    if (!isConnected) return;

    sendTyping(true);
    
    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    // Set timeout to stop typing indicator
    typingTimeoutRef.current = setTimeout(() => {
      sendTyping(false);
    }, 1000);
  };

  const handleTypingStop = () => {
    if (!isConnected) return;

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
    
    sendTyping(false);
  };

  // Cleanup typing timeout on unmount
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className={`flex h-full bg-gray-50 ${className}`}>
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                OpenCode Team Chat
              </h1>
              <p className="text-sm text-gray-500">
                Real-time communication with AI agents
              </p>
            </div>
            <ConnectionStatus />
          </div>
        </div>

        {/* Messages area */}
        <div className="flex-1 flex flex-col min-h-0">
          <MessageList 
            messages={messages}
            currentUserId={currentUser?.user_id}
            className="flex-1"
          />
          
          {/* Typing indicator */}
          {typingUsers.size > 0 && (
            <TypingIndicator 
              typingUsers={Array.from(typingUsers)}
              users={users}
              className="px-6 py-2"
            />
          )}
          
          {/* Message input */}
          <MessageInput
            onSendMessage={handleSendMessage}
            onTypingStart={handleTypingStart}
            onTypingStop={handleTypingStop}
            disabled={!isConnected}
            className="border-t border-gray-200"
          />
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-80 bg-white border-l border-gray-200">
        <UserList 
          users={users}
          currentUserId={currentUser?.user_id}
          className="h-full"
        />
      </div>
    </div>
  );
}