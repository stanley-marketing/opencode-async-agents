/**
 * Hook for handling @mention functionality in chat messages.
 * Provides autocomplete, filtering, and mention detection capabilities.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { User } from '../types/chat';

export interface MentionSuggestion {
  id: string;
  display: string;
  type: 'user' | 'agent' | 'command';
  role?: string;
  isOnline?: boolean;
}

interface UseMentionsOptions {
  users: User[];
  agentNames?: string[];
  commands?: string[];
  maxSuggestions?: number;
}

interface UseMentionsReturn {
  suggestions: MentionSuggestion[];
  isShowingSuggestions: boolean;
  selectedIndex: number;
  mentionQuery: string;
  mentionStartPos: number;
  handleTextChange: (text: string, cursorPos: number) => void;
  selectSuggestion: (index: number) => string;
  navigateSuggestions: (direction: 'up' | 'down') => void;
  hideSuggestions: () => void;
  insertMention: (text: string, mention: string, startPos: number, endPos: number) => string;
}

export function useMentions({
  users,
  agentNames = [],
  commands = [],
  maxSuggestions = 10
}: UseMentionsOptions): UseMentionsReturn {
  const [isShowingSuggestions, setIsShowingSuggestions] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionStartPos, setMentionStartPos] = useState(-1);
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Generate all possible mention suggestions
  const allSuggestions = useMemo(() => {
    const suggestions: MentionSuggestion[] = [];

    // Add users
    users.forEach(user => {
      suggestions.push({
        id: user.user_id,
        display: `@${user.user_id}`,
        type: 'user',
        role: user.role,
        isOnline: user.is_online
      });
    });

    // Add agent names
    agentNames.forEach(agent => {
      suggestions.push({
        id: agent,
        display: `@${agent}`,
        type: 'agent',
        role: 'AI Agent',
        isOnline: true
      });
    });

    // Add commands (when typing /)
    commands.forEach(command => {
      suggestions.push({
        id: command,
        display: `/${command}`,
        type: 'command',
        role: 'Command',
        isOnline: true
      });
    });

    return suggestions;
  }, [users, agentNames, commands]);

  // Filter suggestions based on query
  const suggestions = useMemo(() => {
    if (!mentionQuery) return [];

    const filtered = allSuggestions.filter(suggestion => {
      const query = mentionQuery.toLowerCase();
      return (
        suggestion.id.toLowerCase().includes(query) ||
        suggestion.display.toLowerCase().includes(query)
      );
    });

    // Sort by relevance (exact matches first, then online users, then alphabetical)
    filtered.sort((a, b) => {
      const aExact = a.id.toLowerCase() === mentionQuery.toLowerCase();
      const bExact = b.id.toLowerCase() === mentionQuery.toLowerCase();
      
      if (aExact && !bExact) return -1;
      if (!aExact && bExact) return 1;
      
      const aOnline = a.isOnline ?? false;
      const bOnline = b.isOnline ?? false;
      
      if (aOnline && !bOnline) return -1;
      if (!aOnline && bOnline) return 1;
      
      return a.display.localeCompare(b.display);
    });

    return filtered.slice(0, maxSuggestions);
  }, [allSuggestions, mentionQuery, maxSuggestions]);

  // Handle text change and detect mentions
  const handleTextChange = useCallback((text: string, cursorPos: number) => {
    // Look for @ or / mentions before cursor
    const textBeforeCursor = text.substring(0, cursorPos);
    
    // Check for @ mentions
    const atMentionMatch = textBeforeCursor.match(/@(\w*)$/);
    if (atMentionMatch) {
      setMentionQuery(atMentionMatch[1]);
      setMentionStartPos(cursorPos - atMentionMatch[0].length);
      setIsShowingSuggestions(true);
      setSelectedIndex(0);
      return;
    }

    // Check for / commands (only at start of message or after whitespace)
    const commandMatch = textBeforeCursor.match(/(?:^|\s)\/(\w*)$/);
    if (commandMatch) {
      setMentionQuery(commandMatch[1]);
      setMentionStartPos(cursorPos - commandMatch[1].length - 1);
      setIsShowingSuggestions(true);
      setSelectedIndex(0);
      return;
    }

    // No mention found
    setIsShowingSuggestions(false);
    setMentionQuery('');
    setMentionStartPos(-1);
  }, []);

  // Select a suggestion by index
  const selectSuggestion = useCallback((index: number): string => {
    if (index < 0 || index >= suggestions.length) return '';
    
    const suggestion = suggestions[index];
    setIsShowingSuggestions(false);
    setMentionQuery('');
    setMentionStartPos(-1);
    
    return suggestion.display;
  }, [suggestions]);

  // Navigate suggestions with arrow keys
  const navigateSuggestions = useCallback((direction: 'up' | 'down') => {
    if (!isShowingSuggestions || suggestions.length === 0) return;

    setSelectedIndex(prev => {
      if (direction === 'down') {
        return Math.min(prev + 1, suggestions.length - 1);
      } else {
        return Math.max(prev - 1, 0);
      }
    });
  }, [isShowingSuggestions, suggestions.length]);

  // Hide suggestions
  const hideSuggestions = useCallback(() => {
    setIsShowingSuggestions(false);
    setMentionQuery('');
    setMentionStartPos(-1);
    setSelectedIndex(0);
  }, []);

  // Insert mention into text
  const insertMention = useCallback((
    text: string, 
    mention: string, 
    startPos: number, 
    endPos: number
  ): string => {
    const before = text.substring(0, startPos);
    const after = text.substring(endPos);
    return `${before}${mention} ${after}`;
  }, []);

  // Reset selected index when suggestions change
  useEffect(() => {
    setSelectedIndex(0);
  }, [suggestions]);

  return {
    suggestions,
    isShowingSuggestions: isShowingSuggestions && suggestions.length > 0,
    selectedIndex,
    mentionQuery,
    mentionStartPos,
    handleTextChange,
    selectSuggestion,
    navigateSuggestions,
    hideSuggestions,
    insertMention
  };
}