/**
 * Advanced mention autocomplete component with support for users, agents, and commands.
 * Provides keyboard navigation, visual indicators, and accessibility features.
 */

import React, { useEffect, useRef } from 'react';
import { 
  UserIcon, 
  ComputerDesktopIcon, 
  CommandLineIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { MentionSuggestion } from '../../hooks/useMentions';

interface MentionAutocompleteProps {
  suggestions: MentionSuggestion[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onClose: () => void;
  className?: string;
  maxHeight?: number;
}

export default function MentionAutocomplete({
  suggestions,
  selectedIndex,
  onSelect,
  onClose,
  className = '',
  maxHeight = 200
}: MentionAutocompleteProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const selectedItemRef = useRef<HTMLButtonElement>(null);

  // Scroll selected item into view
  useEffect(() => {
    if (selectedItemRef.current) {
      selectedItemRef.current.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth'
      });
    }
  }, [selectedIndex]);

  // Handle click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (listRef.current && !listRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  if (suggestions.length === 0) return null;

  const getIcon = (type: MentionSuggestion['type']) => {
    switch (type) {
      case 'user':
        return UserIcon;
      case 'agent':
        return ComputerDesktopIcon;
      case 'command':
        return CommandLineIcon;
      default:
        return UserIcon;
    }
  };

  const getTypeColor = (type: MentionSuggestion['type']) => {
    switch (type) {
      case 'user':
        return 'text-blue-600 bg-blue-50';
      case 'agent':
        return 'text-purple-600 bg-purple-50';
      case 'command':
        return 'text-green-600 bg-green-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getTypeLabel = (type: MentionSuggestion['type']) => {
    switch (type) {
      case 'user':
        return 'User';
      case 'agent':
        return 'AI Agent';
      case 'command':
        return 'Command';
      default:
        return 'Unknown';
    }
  };

  return (
    <div 
      ref={listRef}
      className={`absolute z-50 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden ${className}`}
      style={{ maxHeight }}
      role="listbox"
      aria-label="Mention suggestions"
    >
      {/* Header */}
      <div className="px-3 py-2 bg-gray-50 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-600">
            Suggestions ({suggestions.length})
          </span>
          <span className="text-xs text-gray-500">
            ↑↓ navigate • ↵ select • esc close
          </span>
        </div>
      </div>

      {/* Suggestions list */}
      <div className="max-h-48 overflow-y-auto">
        {suggestions.map((suggestion, index) => {
          const Icon = getIcon(suggestion.type);
          const isSelected = index === selectedIndex;
          const typeColor = getTypeColor(suggestion.type);
          
          return (
            <button
              key={`${suggestion.type}-${suggestion.id}`}
              ref={isSelected ? selectedItemRef : undefined}
              onClick={() => onSelect(index)}
              className={`w-full text-left px-3 py-2 flex items-center space-x-3 transition-colors ${
                isSelected 
                  ? 'bg-blue-50 text-blue-900 border-r-2 border-blue-500' 
                  : 'hover:bg-gray-50 text-gray-900'
              }`}
              role="option"
              aria-selected={isSelected}
              tabIndex={-1}
            >
              {/* Icon and online indicator */}
              <div className="relative flex-shrink-0">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${typeColor}`}>
                  <Icon className="w-4 h-4" />
                </div>
                
                {/* Online indicator for users and agents */}
                {(suggestion.type === 'user' || suggestion.type === 'agent') && suggestion.isOnline && (
                  <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 border-2 border-white rounded-full">
                    <CheckCircleIcon className="w-2 h-2 text-white" />
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-sm truncate">
                    {suggestion.display}
                  </span>
                  
                  {/* Type badge */}
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium ${
                    suggestion.type === 'user' 
                      ? 'bg-blue-100 text-blue-700'
                      : suggestion.type === 'agent'
                        ? 'bg-purple-100 text-purple-700'
                        : 'bg-green-100 text-green-700'
                  }`}>
                    {getTypeLabel(suggestion.type)}
                  </span>
                </div>
                
                {/* Role/description */}
                {suggestion.role && (
                  <div className="text-xs text-gray-500 truncate mt-0.5">
                    {suggestion.role}
                  </div>
                )}
              </div>

              {/* Status indicators */}
              <div className="flex-shrink-0 flex items-center space-x-1">
                {suggestion.type === 'user' && (
                  <div className={`w-2 h-2 rounded-full ${
                    suggestion.isOnline ? 'bg-green-400' : 'bg-gray-300'
                  }`} />
                )}
                
                {isSelected && (
                  <div className="text-blue-500">
                    <CheckCircleIcon className="w-4 h-4" />
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer with help text */}
      <div className="px-3 py-2 bg-gray-50 border-t border-gray-100">
        <div className="text-xs text-gray-500">
          {suggestions.length > 0 && (
            <>
              {suggestions.filter(s => s.type === 'user').length > 0 && (
                <span className="mr-3">👤 Users</span>
              )}
              {suggestions.filter(s => s.type === 'agent').length > 0 && (
                <span className="mr-3">🤖 AI Agents</span>
              )}
              {suggestions.filter(s => s.type === 'command').length > 0 && (
                <span>⌨️ Commands</span>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}