/**
 * Individual message item component.
 * Handles message display, mentions, commands, and interactions.
 */

import React, { useState } from 'react';
import { format } from 'date-fns';
import { ChatMessage } from '../../types/chat';
import { 
  ChatBubbleLeftIcon, 
  CommandLineIcon,
  UserIcon,
  ComputerDesktopIcon
} from '@heroicons/react/24/outline';

interface MessageItemProps {
  message: ChatMessage;
  isOwn: boolean;
  isConsecutive?: boolean;
  onReply?: (message: ChatMessage) => void;
  onMentionClick?: (mention: string) => void;
}

export default function MessageItem({
  message,
  isOwn,
  isConsecutive = false,
  onReply,
  onMentionClick
}: MessageItemProps) {
  const [showActions, setShowActions] = useState(false);

  // Format timestamp
  const formatTime = (timestamp: string) => {
    return format(new Date(timestamp), 'HH:mm');
  };

  // Parse message text for mentions and formatting
  const parseMessageText = (text: string) => {
    // Split by mentions and format them
    const parts = text.split(/(@\w+(?:-bot)?)/g);
    
    return parts.map((part, index) => {
      if (part.match(/^@\w+(?:-bot)?$/)) {
        const mention = part.substring(1); // Remove @
        return (
          <button
            key={index}
            onClick={() => onMentionClick?.(mention)}
            className="text-blue-600 hover:text-blue-800 font-medium bg-blue-50 px-1 rounded"
          >
            {part}
          </button>
        );
      }
      return part;
    });
  };

  // Get sender display info
  const getSenderInfo = () => {
    const isBot = message.is_bot_message || message.sender.endsWith('-bot');
    const displayName = message.sender.replace('-bot', '');
    
    return {
      name: displayName,
      isBot,
      icon: isBot ? ComputerDesktopIcon : UserIcon
    };
  };

  const senderInfo = getSenderInfo();
  const SenderIcon = senderInfo.icon;

  return (
    <div
      className={`group relative ${isConsecutive ? 'mt-1' : 'mt-4'}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}>
        <div className={`flex max-w-3xl ${isOwn ? 'flex-row-reverse' : 'flex-row'}`}>
          {/* Avatar */}
          {!isConsecutive && (
            <div className={`flex-shrink-0 ${isOwn ? 'ml-3' : 'mr-3'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                senderInfo.isBot 
                  ? 'bg-purple-100 text-purple-600' 
                  : isOwn 
                    ? 'bg-blue-100 text-blue-600'
                    : 'bg-gray-100 text-gray-600'
              }`}>
                <SenderIcon className="w-4 h-4" />
              </div>
            </div>
          )}

          {/* Message content */}
          <div className={`flex-1 ${isConsecutive && !isOwn ? 'ml-11' : ''} ${isConsecutive && isOwn ? 'mr-11' : ''}`}>
            {/* Sender name and timestamp */}
            {!isConsecutive && (
              <div className={`flex items-center mb-1 ${isOwn ? 'justify-end' : 'justify-start'}`}>
                <span className={`text-sm font-medium ${
                  senderInfo.isBot ? 'text-purple-600' : 'text-gray-900'
                }`}>
                  {senderInfo.name}
                  {senderInfo.isBot && (
                    <span className="ml-1 text-xs bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded-full">
                      AI
                    </span>
                  )}
                </span>
                <span className="ml-2 text-xs text-gray-500">
                  {formatTime(message.timestamp)}
                </span>
              </div>
            )}

            {/* Message bubble */}
            <div className={`relative ${isOwn ? 'text-right' : 'text-left'}`}>
              <div className={`inline-block px-4 py-2 rounded-lg max-w-full ${
                message.is_command
                  ? 'bg-gray-100 border border-gray-200 font-mono text-sm'
                  : isOwn
                    ? 'bg-blue-600 text-white'
                    : senderInfo.isBot
                      ? 'bg-purple-50 border border-purple-200 text-purple-900'
                      : 'bg-white border border-gray-200 text-gray-900'
              }`}>
                {/* Command indicator */}
                {message.is_command && (
                  <div className="flex items-center mb-1 text-gray-500">
                    <CommandLineIcon className="w-4 h-4 mr-1" />
                    <span className="text-xs">Command: {message.command}</span>
                  </div>
                )}

                {/* Reply indicator */}
                {message.reply_to && (
                  <div className={`text-xs mb-2 opacity-75 ${
                    isOwn ? 'text-blue-200' : 'text-gray-500'
                  }`}>
                    <ChatBubbleLeftIcon className="w-3 h-3 inline mr-1" />
                    Replying to message
                  </div>
                )}

                {/* Message text */}
                <div className="whitespace-pre-wrap break-words">
                  {parseMessageText(message.text)}
                </div>

                {/* Command arguments */}
                {message.is_command && message.command_args && message.command_args.length > 0 && (
                  <div className="mt-2 text-xs text-gray-600">
                    <div>Arguments:</div>
                    <ul className="list-disc list-inside ml-2">
                      {message.command_args.map((arg, index) => (
                        <li key={index}>{arg}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Message actions */}
              {showActions && onReply && (
                <div className={`absolute top-0 ${isOwn ? 'left-0 -translate-x-full' : 'right-0 translate-x-full'} 
                  flex items-center space-x-1 bg-white border border-gray-200 rounded-lg shadow-sm px-2 py-1`}>
                  <button
                    onClick={() => onReply(message)}
                    className="text-gray-400 hover:text-gray-600 p-1 rounded"
                    title="Reply"
                  >
                    <ChatBubbleLeftIcon className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Consecutive message timestamp */}
            {isConsecutive && (
              <div className={`text-xs text-gray-400 mt-1 ${isOwn ? 'text-right' : 'text-left'}`}>
                {formatTime(message.timestamp)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}