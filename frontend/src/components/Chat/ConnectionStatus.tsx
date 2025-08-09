/**
 * Connection status indicator component.
 * Shows WebSocket connection state and provides reconnection controls.
 */

import React from 'react';
import { useConnectionState } from '../../stores/chatStore';
import { 
  WifiIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  XCircleIcon
} from '@heroicons/react/24/outline';

interface ConnectionStatusProps {
  onReconnect?: () => void;
  className?: string;
}

export default function ConnectionStatus({
  onReconnect,
  className = ''
}: ConnectionStatusProps) {
  const connectionState = useConnectionState();

  const getStatusInfo = () => {
    switch (connectionState.status) {
      case 'connected':
        return {
          icon: WifiIcon,
          text: 'Connected',
          color: 'text-green-600 bg-green-50 border-green-200',
          iconColor: 'text-green-500'
        };
      case 'connecting':
        return {
          icon: ArrowPathIcon,
          text: 'Connecting...',
          color: 'text-yellow-600 bg-yellow-50 border-yellow-200',
          iconColor: 'text-yellow-500',
          animate: true
        };
      case 'disconnected':
        return {
          icon: XCircleIcon,
          text: 'Disconnected',
          color: 'text-gray-600 bg-gray-50 border-gray-200',
          iconColor: 'text-gray-500'
        };
      case 'error':
        return {
          icon: ExclamationTriangleIcon,
          text: 'Connection Error',
          color: 'text-red-600 bg-red-50 border-red-200',
          iconColor: 'text-red-500'
        };
      default:
        return {
          icon: XCircleIcon,
          text: 'Unknown',
          color: 'text-gray-600 bg-gray-50 border-gray-200',
          iconColor: 'text-gray-500'
        };
    }
  };

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;

  const formatLastConnected = () => {
    if (!connectionState.lastConnected) return null;
    
    const now = new Date();
    const lastConnected = connectionState.lastConnected;
    const diffInMinutes = (now.getTime() - lastConnected.getTime()) / (1000 * 60);
    
    if (diffInMinutes < 1) {
      return 'Just now';
    } else if (diffInMinutes < 60) {
      return `${Math.floor(diffInMinutes)}m ago`;
    } else {
      const hours = Math.floor(diffInMinutes / 60);
      return `${hours}h ago`;
    }
  };

  const showReconnectButton = connectionState.status === 'disconnected' || connectionState.status === 'error';
  const showReconnectAttempts = connectionState.reconnectAttempts > 0;

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      {/* Status indicator */}
      <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border ${statusInfo.color}`}>
        <StatusIcon 
          className={`w-4 h-4 ${statusInfo.iconColor} ${
            statusInfo.animate ? 'animate-spin' : ''
          }`} 
        />
        <span className="text-sm font-medium">{statusInfo.text}</span>
      </div>

      {/* Additional info */}
      {connectionState.status === 'connected' && connectionState.lastConnected && (
        <span className="text-xs text-gray-500">
          Connected {formatLastConnected()}
        </span>
      )}

      {/* Reconnect attempts */}
      {showReconnectAttempts && (
        <span className="text-xs text-gray-500">
          Attempt {connectionState.reconnectAttempts}
        </span>
      )}

      {/* Error message */}
      {connectionState.error && (
        <span className="text-xs text-red-600 max-w-xs truncate" title={connectionState.error}>
          {connectionState.error}
        </span>
      )}

      {/* Reconnect button */}
      {showReconnectButton && onReconnect && (
        <button
          onClick={onReconnect}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium px-2 py-1 rounded border border-blue-200 hover:bg-blue-50 transition-colors"
        >
          Reconnect
        </button>
      )}
    </div>
  );
}