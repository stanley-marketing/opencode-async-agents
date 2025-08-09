/**
 * WebSocket hook for real-time communication with the OpenCode-Slack server.
 * Provides connection management, message handling, and automatic reconnection.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { ChatMessage, WebSocketMessage, ConnectionState, User, TypingIndicator } from '../types/chat';

interface UseWebSocketOptions {
  url: string;
  userId: string;
  userRole: string;
  onMessage?: (message: ChatMessage) => void;
  onUserStatusChange?: (user: User, status: 'connected' | 'disconnected') => void;
  onTypingChange?: (typing: TypingIndicator) => void;
  onError?: (error: string) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UseWebSocketReturn {
  connectionState: ConnectionState;
  sendMessage: (text: string, replyTo?: number) => void;
  sendTyping: (isTyping: boolean) => void;
  connect: () => void;
  disconnect: () => void;
  isConnected: boolean;
}

export function useWebSocket({
  url,
  userId,
  userRole,
  onMessage,
  onUserStatusChange,
  onTypingChange,
  onError,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10
}: UseWebSocketOptions): UseWebSocketReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>({
    status: 'disconnected',
    reconnectAttempts: 0
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Interval | null>(null);
  const isManualDisconnect = useRef(false);

  const updateConnectionState = useCallback((updates: Partial<ConnectionState>) => {
    setConnectionState(prev => ({ ...prev, ...updates }));
  }, []);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const clearPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const startPingInterval = useCallback(() => {
    clearPingInterval();
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Ping every 30 seconds
  }, [clearPingInterval]);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const wsMessage: WebSocketMessage = JSON.parse(event.data);

      switch (wsMessage.type) {
        case 'auth_success':
          updateConnectionState({
            status: 'connected',
            error: undefined,
            reconnectAttempts: 0,
            lastConnected: new Date()
          });
          startPingInterval();
          break;

        case 'chat_message':
          if (wsMessage.data && onMessage) {
            const message: ChatMessage = {
              id: wsMessage.data.id,
              text: wsMessage.data.text,
              sender: wsMessage.data.sender,
              timestamp: wsMessage.data.timestamp,
              mentions: wsMessage.data.mentions || [],
              is_command: wsMessage.data.is_command || false,
              command: wsMessage.data.command,
              command_args: wsMessage.data.command_args || [],
              reply_to: wsMessage.data.reply_to,
              is_bot_message: wsMessage.data.is_bot_message || false
            };
            onMessage(message);
          }
          break;

        case 'user_status':
          if (wsMessage.data && onUserStatusChange) {
            const user: User = {
              user_id: wsMessage.data.user_id,
              role: wsMessage.data.role || 'user',
              connected_at: wsMessage.data.timestamp,
              last_activity: wsMessage.data.timestamp,
              message_count: 0,
              is_online: wsMessage.data.status === 'connected'
            };
            onUserStatusChange(user, wsMessage.data.status);
          }
          break;

        case 'typing':
          if (wsMessage.data && onTypingChange) {
            const typing: TypingIndicator = {
              user_id: wsMessage.data.user_id,
              is_typing: wsMessage.data.is_typing
            };
            onTypingChange(typing);
          }
          break;

        case 'pong':
          // Heartbeat response - connection is alive
          break;

        case 'error':
          const errorMessage = wsMessage.message || 'Unknown WebSocket error';
          updateConnectionState({
            status: 'error',
            error: errorMessage
          });
          onError?.(errorMessage);
          break;

        default:
          console.warn('Unknown WebSocket message type:', wsMessage.type);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      onError?.('Failed to parse server message');
    }
  }, [onMessage, onUserStatusChange, onTypingChange, onError, updateConnectionState, startPingInterval]);

  const handleOpen = useCallback(() => {
    console.log('WebSocket connected');
    
    // Send authentication message
    const authMessage: WebSocketMessage = {
      type: 'auth',
      user_id: userId,
      role: userRole
    };

    wsRef.current?.send(JSON.stringify(authMessage));
  }, [userId, userRole]);

  const handleClose = useCallback((event: CloseEvent) => {
    console.log('WebSocket disconnected:', event.code, event.reason);
    
    clearPingInterval();
    
    updateConnectionState({
      status: 'disconnected',
      error: event.reason || undefined
    });

    // Attempt reconnection if not manually disconnected
    if (!isManualDisconnect.current && connectionState.reconnectAttempts < maxReconnectAttempts) {
      const nextAttempt = connectionState.reconnectAttempts + 1;
      updateConnectionState({
        reconnectAttempts: nextAttempt
      });

      console.log(`Attempting to reconnect (${nextAttempt}/${maxReconnectAttempts})...`);
      
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, reconnectInterval);
    }
  }, [connectionState.reconnectAttempts, maxReconnectAttempts, reconnectInterval, clearPingInterval, updateConnectionState]);

  const handleError = useCallback((event: Event) => {
    console.error('WebSocket error:', event);
    
    updateConnectionState({
      status: 'error',
      error: 'Connection error'
    });
    
    onError?.('WebSocket connection error');
  }, [updateConnectionState, onError]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    clearReconnectTimeout();
    isManualDisconnect.current = false;

    updateConnectionState({
      status: 'connecting',
      error: undefined
    });

    try {
      wsRef.current = new WebSocket(url);
      wsRef.current.onopen = handleOpen;
      wsRef.current.onmessage = handleMessage;
      wsRef.current.onclose = handleClose;
      wsRef.current.onerror = handleError;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      updateConnectionState({
        status: 'error',
        error: 'Failed to create connection'
      });
      onError?.('Failed to create WebSocket connection');
    }
  }, [url, handleOpen, handleMessage, handleClose, handleError, clearReconnectTimeout, updateConnectionState, onError]);

  const disconnect = useCallback(() => {
    isManualDisconnect.current = true;
    clearReconnectTimeout();
    clearPingInterval();

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }

    updateConnectionState({
      status: 'disconnected',
      error: undefined,
      reconnectAttempts: 0
    });
  }, [clearReconnectTimeout, clearPingInterval, updateConnectionState]);

  const sendMessage = useCallback((text: string, replyTo?: number) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      onError?.('Not connected to server');
      return;
    }

    const message: WebSocketMessage = {
      type: 'chat_message',
      data: {
        text,
        reply_to: replyTo
      }
    };

    try {
      wsRef.current.send(JSON.stringify(message));
    } catch (error) {
      console.error('Failed to send message:', error);
      onError?.('Failed to send message');
    }
  }, [onError]);

  const sendTyping = useCallback((isTyping: boolean) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      return;
    }

    const message: WebSocketMessage = {
      type: 'typing',
      data: {
        is_typing: isTyping
      }
    };

    try {
      wsRef.current.send(JSON.stringify(message));
    } catch (error) {
      console.error('Failed to send typing indicator:', error);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  const isConnected = connectionState.status === 'connected';

  return {
    connectionState,
    sendMessage,
    sendTyping,
    connect,
    disconnect,
    isConnected
  };
}