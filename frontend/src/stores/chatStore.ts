/**
 * Zustand store for managing chat state.
 * Handles messages, users, typing indicators, and connection state.
 */

import { create } from 'zustand';
import { ChatMessage, User, ChatState, TypingIndicator } from '../types/chat';

interface ChatActions {
  // Message actions
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: number, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  
  // User actions
  addUser: (user: User) => void;
  removeUser: (userId: string) => void;
  updateUser: (userId: string, updates: Partial<User>) => void;
  setUsers: (users: User[]) => void;
  
  // Typing actions
  setUserTyping: (userId: string, isTyping: boolean) => void;
  clearTyping: () => void;
  
  // Connection actions
  setConnectionStatus: (status: ChatState['connectionState']['status']) => void;
  setConnectionError: (error: string | undefined) => void;
  setReconnectAttempts: (attempts: number) => void;
  setLastConnected: (date: Date | undefined) => void;
  
  // Current user actions
  setCurrentUser: (user: { user_id: string; role: string } | undefined) => void;
  
  // Utility actions
  reset: () => void;
}

type ChatStore = ChatState & ChatActions;

const initialState: ChatState = {
  messages: [],
  users: [],
  typingUsers: new Set(),
  connectionState: {
    status: 'disconnected',
    reconnectAttempts: 0
  },
  currentUser: undefined
};

export const useChatStore = create<ChatStore>((set, get) => ({
  ...initialState,

  // Message actions
  addMessage: (message: ChatMessage) => {
    set((state) => ({
      messages: [...state.messages, message].sort((a, b) => a.id - b.id)
    }));
  },

  updateMessage: (id: number, updates: Partial<ChatMessage>) => {
    set((state) => ({
      messages: state.messages.map(msg => 
        msg.id === id ? { ...msg, ...updates } : msg
      )
    }));
  },

  clearMessages: () => {
    set({ messages: [] });
  },

  // User actions
  addUser: (user: User) => {
    set((state) => {
      const existingUserIndex = state.users.findIndex(u => u.user_id === user.user_id);
      
      if (existingUserIndex >= 0) {
        // Update existing user
        const updatedUsers = [...state.users];
        updatedUsers[existingUserIndex] = { ...updatedUsers[existingUserIndex], ...user };
        return { users: updatedUsers };
      } else {
        // Add new user
        return { users: [...state.users, user] };
      }
    });
  },

  removeUser: (userId: string) => {
    set((state) => ({
      users: state.users.filter(user => user.user_id !== userId),
      typingUsers: new Set([...state.typingUsers].filter(id => id !== userId))
    }));
  },

  updateUser: (userId: string, updates: Partial<User>) => {
    set((state) => ({
      users: state.users.map(user =>
        user.user_id === userId ? { ...user, ...updates } : user
      )
    }));
  },

  setUsers: (users: User[]) => {
    set({ users });
  },

  // Typing actions
  setUserTyping: (userId: string, isTyping: boolean) => {
    set((state) => {
      const newTypingUsers = new Set(state.typingUsers);
      
      if (isTyping) {
        newTypingUsers.add(userId);
      } else {
        newTypingUsers.delete(userId);
      }
      
      return { typingUsers: newTypingUsers };
    });
  },

  clearTyping: () => {
    set({ typingUsers: new Set() });
  },

  // Connection actions
  setConnectionStatus: (status: ChatState['connectionState']['status']) => {
    set((state) => ({
      connectionState: {
        ...state.connectionState,
        status
      }
    }));
  },

  setConnectionError: (error: string | undefined) => {
    set((state) => ({
      connectionState: {
        ...state.connectionState,
        error
      }
    }));
  },

  setReconnectAttempts: (attempts: number) => {
    set((state) => ({
      connectionState: {
        ...state.connectionState,
        reconnectAttempts: attempts
      }
    }));
  },

  setLastConnected: (date: Date | undefined) => {
    set((state) => ({
      connectionState: {
        ...state.connectionState,
        lastConnected: date
      }
    }));
  },

  // Current user actions
  setCurrentUser: (user: { user_id: string; role: string } | undefined) => {
    set({ currentUser: user });
  },

  // Utility actions
  reset: () => {
    set(initialState);
  }
}));

// Selectors for common use cases
export const useChatMessages = () => useChatStore(state => state.messages);
export const useChatUsers = () => useChatStore(state => state.users);
export const useOnlineUsers = () => useChatStore(state => state.users.filter(user => user.is_online));
export const useTypingUsers = () => useChatStore(state => state.typingUsers);
export const useConnectionState = () => useChatStore(state => state.connectionState);
export const useCurrentUser = () => useChatStore(state => state.currentUser);
export const useIsConnected = () => useChatStore(state => state.connectionState.status === 'connected');

// Action selectors
export const useChatActions = () => useChatStore(state => ({
  addMessage: state.addMessage,
  updateMessage: state.updateMessage,
  clearMessages: state.clearMessages,
  addUser: state.addUser,
  removeUser: state.removeUser,
  updateUser: state.updateUser,
  setUsers: state.setUsers,
  setUserTyping: state.setUserTyping,
  clearTyping: state.clearTyping,
  setConnectionStatus: state.setConnectionStatus,
  setConnectionError: state.setConnectionError,
  setReconnectAttempts: state.setReconnectAttempts,
  setLastConnected: state.setLastConnected,
  setCurrentUser: state.setCurrentUser,
  reset: state.reset
}));