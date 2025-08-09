/**
 * Enhanced chat interface with advanced features including threading, mentions, and responsive design.
 * Integrates all the new advanced components for a complete chat experience.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useChatStore, useChatActions, useIsConnected } from '../../stores/chatStore';
import { ChatMessage } from '../../types/chat';
import MessageList from './MessageList';
import EnhancedMessageInput from './EnhancedMessageInput';
import EnhancedUserList from './EnhancedUserList';
import ConnectionStatus from './ConnectionStatus';
import EnhancedTypingIndicator from '../advanced/TypingIndicator';
import { 
  Bars3Icon,
  XMarkIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline';

interface EnhancedChatInterfaceProps {
  websocketUrl: string;
  userId: string;
  userRole: string;
  agentNames?: string[];
  availableCommands?: string[];
  className?: string;
}

export default function EnhancedChatInterface({
  websocketUrl,
  userId,
  userRole,
  agentNames = ['analyst', 'developer', 'designer', 'tester', 'architect'],
  availableCommands = ['help', 'status', 'clear', 'users', 'agents', 'tasks'],
  className = ''
}: EnhancedChatInterfaceProps) {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [replyToMessage, setReplyToMessage] = useState<ChatMessage | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageListRef = useRef<HTMLDivElement>(null);
  
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

  // Detect mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

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
      
      // Auto-scroll to bottom on new messages
      setTimeout(() => {
        if (messageListRef.current) {
          messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
        }
      }, 100);
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
  const handleSendMessage = useCallback((text: string, replyTo?: number) => {
    if (!isConnected) {
      console.warn('Cannot send message: not connected');
      return;
    }

    sendMessage(text, replyTo || replyToMessage?.id);
    
    // Clear reply state after sending
    if (replyToMessage) {
      setReplyToMessage(null);
    }
  }, [isConnected, sendMessage, replyToMessage]);

  // Handle typing indicators
  const handleTypingStart = useCallback(() => {
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
  }, [isConnected, sendTyping]);

  const handleTypingStop = useCallback(() => {
    if (!isConnected) return;

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
    
    sendTyping(false);
  }, [isConnected, sendTyping]);

  // Handle reply to message
  const handleReply = useCallback((message: ChatMessage) => {
    setReplyToMessage(message);
    // Focus input on mobile
    if (isMobile) {
      setIsSidebarOpen(false);
    }
  }, [isMobile]);

  // Handle mention click
  const handleMentionClick = useCallback((mention: string) => {
    // Could implement user profile popup or direct message
    console.log('Mention clicked:', mention);
  }, []);

  // Handle user click in sidebar
  const handleUserClick = useCallback((user: any) => {
    // Could implement direct message or user profile
    console.log('User clicked:', user);
  }, []);

  // Handle reaction to message
  const handleReaction = useCallback((messageId: number, reaction: string) => {
    // In a real app, this would send a reaction to the server
    console.log('Reaction:', messageId, reaction);
  }, []);

  // Close sidebar on mobile when clicking outside
  const handleSidebarClose = useCallback(() => {
    if (isMobile) {
      setIsSidebarOpen(false);
    }
  }, [isMobile]);

  // Cleanup typing timeout on unmount
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className={`flex h-full bg-gray-50 relative ${className}`}>
      {/* Mobile sidebar overlay */}
      {isMobile && isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={handleSidebarClose}
        />
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-4 py-3 md:px-6 md:py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {/* Mobile menu button */}
              {isMobile && (
                <button
                  onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                  className="p-2 text-gray-500 hover:text-gray-700 rounded-lg"
                  aria-label="Toggle sidebar"
                >
                  <Bars3Icon className="w-5 h-5" />
                </button>
              )}
              
              <div>
                <h1 className="text-lg md:text-xl font-semibold text-gray-900 flex items-center">
                  <ChatBubbleLeftRightIcon className="w-5 h-5 mr-2 text-blue-600" />
                  OpenCode Team Chat
                </h1>
                <p className="text-xs md:text-sm text-gray-500">
                  Real-time communication with AI agents
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <ConnectionStatus />
              
              {/* Mobile user count */}
              {isMobile && (
                <button
                  onClick={() => setIsSidebarOpen(true)}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  {users.filter(u => u.is_online).length} online
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Messages area */}
        <div className="flex-1 flex flex-col min-h-0">
          <div 
            ref={messageListRef}
            className="flex-1 overflow-y-auto px-4 py-4 md:px-6"
          >
            <MessageList 
              messages={messages}
              currentUserId={currentUser?.user_id}
              onReply={handleReply}
              onMentionClick={handleMentionClick}
              onReaction={handleReaction}
              allMessages={messages}
              className="space-y-4"
            />
          </div>
          
          {/* Typing indicator */}
          {typingUsers.size > 0 && (
            <EnhancedTypingIndicator 
              typingUsers={Array.from(typingUsers)}
              users={users}
              className="border-t border-gray-100"
            />
          )}
          
          {/* Message input */}
          <EnhancedMessageInput
            onSendMessage={handleSendMessage}
            onTypingStart={handleTypingStart}
            onTypingStop={handleTypingStop}
            disabled={!isConnected}
            replyTo={replyToMessage?.id}
            replyToMessage={replyToMessage}
            onCancelReply={() => setReplyToMessage(null)}
            agentNames={agentNames}
            availableCommands={availableCommands}
            className="border-t border-gray-200"
          />
        </div>
      </div>

      {/* Sidebar */}
      <div className={`${
        isMobile 
          ? `fixed top-0 right-0 bottom-0 w-80 max-w-[80vw] bg-white shadow-xl transform transition-transform duration-300 z-50 ${
              isSidebarOpen ? 'translate-x-0' : 'translate-x-full'
            }`
          : 'w-80 bg-white border-l border-gray-200'
      }`}>
        {/* Mobile sidebar header */}
        {isMobile && (
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900">Team</h2>
            <button
              onClick={() => setIsSidebarOpen(false)}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg"
              aria-label="Close sidebar"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        )}
        
        <EnhancedUserList 
          users={users}
          typingUsers={typingUsers}
          currentUserId={currentUser?.user_id}
          onUserClick={handleUserClick}
          className="h-full"
        />
      </div>
    </div>
  );
}