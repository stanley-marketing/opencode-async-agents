/**
 * Message threading component for reply-to functionality.
 * Displays threaded conversations with visual indicators and navigation.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { format } from 'date-fns';
import { 
  ChatBubbleLeftIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ArrowUturnLeftIcon,
  UserIcon,
  ComputerDesktopIcon
} from '@heroicons/react/24/outline';
import { ChatMessage } from '../../types/chat';

interface MessageThreadProps {
  message: ChatMessage;
  replies: ChatMessage[];
  allMessages: ChatMessage[];
  currentUserId?: string;
  onReply?: (message: ChatMessage) => void;
  onMentionClick?: (mention: string) => void;
  className?: string;
  maxDepth?: number;
}

interface ThreadNode {
  message: ChatMessage;
  replies: ThreadNode[];
  depth: number;
}

export default function MessageThread({
  message,
  replies,
  allMessages,
  currentUserId,
  onReply,
  onMentionClick,
  className = '',
  maxDepth = 3
}: MessageThreadProps) {
  const [expandedThreads, setExpandedThreads] = useState<Set<number>>(new Set());
  const [showAllReplies, setShowAllReplies] = useState(false);

  // Build thread tree structure
  const threadTree = useMemo(() => {
    const buildTree = (parentId: number, depth: number = 0): ThreadNode[] => {
      if (depth >= maxDepth) return [];
      
      const directReplies = allMessages.filter(msg => msg.reply_to === parentId);
      
      return directReplies.map(reply => ({
        message: reply,
        replies: buildTree(reply.id, depth + 1),
        depth
      }));
    };

    return buildTree(message.id);
  }, [message.id, allMessages, maxDepth]);

  // Count total replies in thread
  const totalReplies = useMemo(() => {
    const countReplies = (nodes: ThreadNode[]): number => {
      return nodes.reduce((count, node) => {
        return count + 1 + countReplies(node.replies);
      }, 0);
    };
    
    return countReplies(threadTree);
  }, [threadTree]);

  // Toggle thread expansion
  const toggleThread = (messageId: number) => {
    setExpandedThreads(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageId)) {
        newSet.delete(messageId);
      } else {
        newSet.add(messageId);
      }
      return newSet;
    });
  };

  // Parse message text for mentions
  const parseMessageText = (text: string) => {
    const parts = text.split(/(@\w+(?:-bot)?)/g);
    
    return parts.map((part, index) => {
      if (part.match(/^@\w+(?:-bot)?$/)) {
        const mention = part.substring(1);
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

  // Get sender info
  const getSenderInfo = (msg: ChatMessage) => {
    const isBot = msg.is_bot_message || msg.sender.endsWith('-bot');
    const displayName = msg.sender.replace('-bot', '');
    const isOwn = msg.sender === currentUserId;
    
    return {
      name: displayName,
      isBot,
      isOwn,
      icon: isBot ? ComputerDesktopIcon : UserIcon
    };
  };

  // Render a single thread node
  const renderThreadNode = (node: ThreadNode, isLast: boolean = false) => {
    const senderInfo = getSenderInfo(node.message);
    const SenderIcon = senderInfo.icon;
    const isExpanded = expandedThreads.has(node.message.id);
    const hasReplies = node.replies.length > 0;

    return (
      <div key={node.message.id} className="relative">
        {/* Thread line connector */}
        {node.depth > 0 && (
          <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />
        )}
        
        {/* Message container */}
        <div className={`flex space-x-3 ${node.depth > 0 ? 'ml-8' : ''}`}>
          {/* Avatar */}
          <div className="flex-shrink-0">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              senderInfo.isBot 
                ? 'bg-purple-100 text-purple-600' 
                : senderInfo.isOwn 
                  ? 'bg-blue-100 text-blue-600'
                  : 'bg-gray-100 text-gray-600'
            }`}>
              <SenderIcon className="w-4 h-4" />
            </div>
          </div>

          {/* Message content */}
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center space-x-2 mb-1">
              <span className={`text-sm font-medium ${
                senderInfo.isBot ? 'text-purple-600' : 'text-gray-900'
              }`}>
                {senderInfo.name}
              </span>
              
              {senderInfo.isBot && (
                <span className="text-xs bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded-full">
                  AI
                </span>
              )}
              
              <span className="text-xs text-gray-500">
                {format(new Date(node.message.timestamp), 'HH:mm')}
              </span>
              
              {node.depth > 0 && (
                <div className="flex items-center text-xs text-gray-400">
                  <ArrowUturnLeftIcon className="w-3 h-3 mr-1" />
                  Reply
                </div>
              )}
            </div>

            {/* Message bubble */}
            <div className={`inline-block px-3 py-2 rounded-lg max-w-full ${
              node.message.is_command
                ? 'bg-gray-100 border border-gray-200 font-mono text-sm'
                : senderInfo.isOwn
                  ? 'bg-blue-600 text-white'
                  : senderInfo.isBot
                    ? 'bg-purple-50 border border-purple-200 text-purple-900'
                    : 'bg-white border border-gray-200 text-gray-900'
            }`}>
              <div className="whitespace-pre-wrap break-words text-sm">
                {parseMessageText(node.message.text)}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center space-x-2 mt-1">
              {hasReplies && (
                <button
                  onClick={() => toggleThread(node.message.id)}
                  className="flex items-center space-x-1 text-xs text-gray-500 hover:text-gray-700"
                >
                  {isExpanded ? (
                    <ChevronDownIcon className="w-3 h-3" />
                  ) : (
                    <ChevronRightIcon className="w-3 h-3" />
                  )}
                  <span>{node.replies.length} {node.replies.length === 1 ? 'reply' : 'replies'}</span>
                </button>
              )}
              
              {onReply && (
                <button
                  onClick={() => onReply(node.message)}
                  className="flex items-center space-x-1 text-xs text-gray-500 hover:text-blue-600"
                >
                  <ChatBubbleLeftIcon className="w-3 h-3" />
                  <span>Reply</span>
                </button>
              )}
            </div>

            {/* Nested replies */}
            {hasReplies && isExpanded && (
              <div className="mt-3 space-y-3">
                {node.replies.map((reply, index) => 
                  renderThreadNode(reply, index === node.replies.length - 1)
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  if (totalReplies === 0) return null;

  return (
    <div className={`bg-gray-50 border border-gray-200 rounded-lg p-4 ${className}`}>
      {/* Thread header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <ChatBubbleLeftIcon className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">
            {totalReplies} {totalReplies === 1 ? 'Reply' : 'Replies'}
          </span>
        </div>
        
        {totalReplies > 3 && (
          <button
            onClick={() => setShowAllReplies(!showAllReplies)}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            {showAllReplies ? 'Show less' : 'Show all replies'}
          </button>
        )}
      </div>

      {/* Thread content */}
      <div className="space-y-4">
        {(showAllReplies ? threadTree : threadTree.slice(0, 3)).map((node, index) => 
          renderThreadNode(node, index === threadTree.length - 1)
        )}
        
        {!showAllReplies && totalReplies > 3 && (
          <div className="text-center">
            <button
              onClick={() => setShowAllReplies(true)}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Show {totalReplies - 3} more {totalReplies - 3 === 1 ? 'reply' : 'replies'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}