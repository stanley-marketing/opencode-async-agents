/**
 * Type definitions for the chat system.
 * Mirrors the ParsedMessage structure from the Python backend.
 */

export interface ChatMessage {
  id: number;
  text: string;
  sender: string;
  timestamp: string; // ISO string
  mentions: string[];
  is_command: boolean;
  command?: string;
  command_args?: string[];
  reply_to?: number;
  is_bot_message?: boolean;
}

export interface User {
  user_id: string;
  role: string;
  connected_at: string;
  last_activity: string;
  message_count: number;
  is_online: boolean;
}

export interface TypingIndicator {
  user_id: string;
  is_typing: boolean;
}

export interface WebSocketMessage {
  type: 'auth' | 'auth_success' | 'chat_message' | 'user_status' | 'typing' | 'ping' | 'pong' | 'error';
  data?: any;
  message?: string;
  user_id?: string;
  role?: string;
  server_time?: string;
}

export interface ConnectionState {
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  error?: string;
  reconnectAttempts: number;
  lastConnected?: Date;
}

export interface ChatState {
  messages: ChatMessage[];
  users: User[];
  typingUsers: Set<string>;
  connectionState: ConnectionState;
  currentUser?: {
    user_id: string;
    role: string;
  };
}

export interface Employee {
  name: string;
  role: string;
  smartness: string;
}

export interface TaskAssignment {
  name: string;
  task: string;
  model?: string;
  mode?: string;
}

export interface ServerStatus {
  status: string;
  degraded_mode: boolean;
  initialization_errors: string[];
  components: {
    file_manager: boolean;
    task_tracker: boolean;
    session_manager: boolean;
    communication_system: boolean;
    monitoring_system: boolean;
  };
  chat_enabled: boolean;
  active_sessions: number;
  total_agents: number;
  communication?: {
    type: string;
    connected: boolean;
    host?: string;
    port?: number;
    connected_users?: User[];
  };
}

export interface CommunicationStats {
  transport_type: string;
  connected: boolean;
  is_running?: boolean;
  host?: string;
  port?: number;
  connected_users?: number;
  total_messages?: number;
  uptime_seconds?: number;
}

// Enhanced types for advanced features
export interface MessageReaction {
  emoji: string;
  count: number;
  users: string[];
  hasReacted: boolean;
}

export interface MessageThread {
  parentId: number;
  replies: ChatMessage[];
  totalReplies: number;
  lastReplyAt: string;
}

export interface UserPresence {
  user_id: string;
  status: 'online' | 'away' | 'busy' | 'offline' | 'typing';
  last_seen?: string;
  activity?: string;
}

export interface MentionData {
  user_id: string;
  display_name: string;
  start_pos: number;
  end_pos: number;
}

export interface CommandData {
  command: string;
  args: string[];
  description?: string;
  usage?: string;
}

export interface ChatSettings {
  theme: 'light' | 'dark' | 'auto';
  notifications: boolean;
  sounds: boolean;
  showTypingIndicators: boolean;
  showPresenceIndicators: boolean;
  compactMode: boolean;
  fontSize: 'small' | 'medium' | 'large';
}

export interface ChatMetrics {
  totalMessages: number;
  activeUsers: number;
  averageResponseTime: number;
  messagesPerHour: number;
  topUsers: Array<{
    user_id: string;
    message_count: number;
  }>;
}