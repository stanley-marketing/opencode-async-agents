/**
 * Enhanced message item component with threading, presence, and accessibility features.
 * Supports reply-to functionality, mention highlighting, and real-time status indicators.
 */

import React, { useState, useMemo } from 'react';
import { format } from 'date-fns';
import { ChatMessage } from '../../types/chat';
import { 
  ChatBubbleLeftIcon, 
  CommandLineIcon,
  UserIcon,
  ComputerDesktopIcon,
  EllipsisHorizontalIcon,
  HeartIcon,
  FaceSmileIcon
} from '@heroicons/react/24/outline';
import { HeartIcon as HeartIconSolid } from '@heroicons/react/24/solid';
import PresenceIndicator from '../advanced/PresenceIndicator';
import MessageThread from '../advanced/MessageThread';

interface EnhancedMessageItemProps {
  message: ChatMessage;
  isOwn: boolean;
  isConsecutive?: boolean;
  allMessages?: ChatMessage[];
  currentUserId?: string;
  onReply?: (message: ChatMessage) => void;
  onMentionClick?: (mention: string) => void;
  onReaction?: (messageId: number, reaction: string) => void;
  showThread?: boolean;
  className?: string;
}

interface MessageReaction {
  emoji: string;
  count: number;
  users: string[];
  hasReacted: boolean;
}

export default function EnhancedMessageItem({
  message,
  isOwn,
  isConsecutive = false,
  allMessages = [],
  currentUserId,
  onReply,
  onMentionClick,
  onReaction,
  showThread = true,
  className = ''
}: EnhancedMessageItemProps) {
  const [showActions, setShowActions] = useState(false);
  const [showReactions, setShowReactions] = useState(false);

  // Mock reactions data (in real app, this would come from props or store)
  const reactions: MessageReaction[] = [
    { emoji: '❤️', count: 2, users: ['user1', 'user2'], hasReacted: false },
    { emoji: '👍', count: 1, users: ['user3'], hasReacted: isOwn }
  ];

  // Get replies to this message
  const replies = useMemo(() => {
    return allMessages.filter(msg => msg.reply_to === message.id);
  }, [allMessages, message.id]);

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
        const isMentioningCurrentUser = mention === currentUserId || mention === currentUserId?.replace('-bot', '');
        
        return (
          <button
            key={index}
            onClick={() => onMentionClick?.(mention)}
            className={`font-medium px-1 rounded transition-colors ${
              isMentioningCurrentUser
                ? 'text-blue-800 bg-blue-200 hover:bg-blue-300'
                : 'text-blue-600 bg-blue-50 hover:bg-blue-100'
            }`}
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

  // Handle reaction
  const handleReaction = (emoji: string) => {
    onReaction?.(message.id, emoji);
    setShowReactions(false);
  };

  const senderInfo = getSenderInfo();
  const SenderIcon = senderInfo.icon;
  const hasReplies = replies.length > 0;

  return (
    <div className={`group relative ${isConsecutive ? 'mt-1' : 'mt-4'} ${className}`}>
      <div
        className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
        onMouseEnter={() => setShowActions(true)}
        onMouseLeave={() => setShowActions(false)}
      >
        <div className={`flex max-w-3xl ${isOwn ? 'flex-row-reverse' : 'flex-row'}`}>
          {/* Avatar with presence */}
          {!isConsecutive && (
            <div className={`flex-shrink-0 ${isOwn ? 'ml-3' : 'mr-3'}`}>
              <div className="relative">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  senderInfo.isBot 
                    ? 'bg-purple-100 text-purple-600' 
                    : isOwn 
                      ? 'bg-blue-100 text-blue-600'
                      : 'bg-gray-100 text-gray-600'
                }`}>
                  <SenderIcon className="w-4 h-4" />
                </div>
                
                {/* Online indicator for non-bot users */}
                {!senderInfo.isBot && (
                  <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 border-2 border-white rounded-full" />
                )}
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
              <div className={`inline-block px-4 py-2 rounded-lg max-w-full relative ${
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

              {/* Message reactions */}
              {reactions.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {reactions.map((reaction, index) => (
                    <button
                      key={index}
                      onClick={() => handleReaction(reaction.emoji)}
                      className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs transition-colors ${
                        reaction.hasReacted
                          ? 'bg-blue-100 text-blue-700 border border-blue-200'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
                      }`}
                      title={`${reaction.users.join(', ')} reacted with ${reaction.emoji}`}
                    >
                      <span>{reaction.emoji}</span>
                      <span>{reaction.count}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Message actions */}
              {showActions && (
                <div className={`absolute top-0 ${isOwn ? 'left-0 -translate-x-full' : 'right-0 translate-x-full'} 
                  flex items-center space-x-1 bg-white border border-gray-200 rounded-lg shadow-sm px-2 py-1 z-10`}>
                  
                  {/* Reply button */}
                  {onReply && (
                    <button
                      onClick={() => onReply(message)}
                      className="text-gray-400 hover:text-blue-600 p-1 rounded transition-colors"
                      title="Reply"
                    >
                      <ChatBubbleLeftIcon className="w-4 h-4" />
                    </button>
                  )}
                  
                  {/* Reaction button */}
                  <div className="relative">
                    <button
                      onClick={() => setShowReactions(!showReactions)}
                      className="text-gray-400 hover:text-yellow-600 p-1 rounded transition-colors"
                      title="Add reaction"
                    >
                      <FaceSmileIcon className="w-4 h-4" />
                    </button>
                    
                    {/* Reaction picker */}
                    {showReactions && (
                      <div className="absolute bottom-full mb-2 left-0 bg-white border border-gray-200 rounded-lg shadow-lg p-2 flex space-x-1 z-20">
                        {['❤️', '👍', '👎', '😂', '😮', '😢', '🎉'].map(emoji => (
                          <button
                            key={emoji}
                            onClick={() => handleReaction(emoji)}
                            className="hover:bg-gray-100 p-1 rounded text-lg"
                            title={`React with ${emoji}`}
                          >
                            {emoji}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {/* More actions */}
                  <button
                    className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors"
                    title="More actions"
                  >
                    <EllipsisHorizontalIcon className="w-4 h-4" />
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

            {/* Thread replies */}
            {showThread && hasReplies && (
              <div className="mt-3">
                <MessageThread
                  message={message}
                  replies={replies}
                  allMessages={allMessages}
                  currentUserId={currentUserId}
                  onReply={onReply}
                  onMentionClick={onMentionClick}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}