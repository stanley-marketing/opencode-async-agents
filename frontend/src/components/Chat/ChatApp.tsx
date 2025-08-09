/**
 * Complete chat application integrating all advanced features.
 * This is the main entry point that demonstrates how to use all the new components together.
 */

import React from 'react';
import { AccessibilityProvider } from '../advanced/AccessibilityProvider';
import EnhancedChatInterface from './EnhancedChatInterface';
import '../../../styles/responsive.css';
import '../../../styles/accessibility.css';

interface ChatAppProps {
  websocketUrl?: string;
  userId?: string;
  userRole?: string;
  agentNames?: string[];
  availableCommands?: string[];
  className?: string;
}

export default function ChatApp({
  websocketUrl = 'ws://localhost:8000/ws',
  userId = 'user-' + Math.random().toString(36).substr(2, 9),
  userRole = 'developer',
  agentNames = [
    'analyst',
    'developer', 
    'designer',
    'tester',
    'architect',
    'devops',
    'product-manager',
    'security-expert',
    'data-scientist',
    'ui-ux-designer'
  ],
  availableCommands = [
    'help',
    'status', 
    'clear',
    'users',
    'agents',
    'tasks',
    'metrics',
    'settings',
    'export',
    'search'
  ],
  className = ''
}: ChatAppProps) {
  return (
    <AccessibilityProvider>
      <div className={`h-screen w-full ${className}`}>
        {/* Skip navigation for keyboard users */}
        <a 
          href="#main-chat"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-blue-600 text-white px-4 py-2 rounded-lg z-50"
        >
          Skip to main chat
        </a>
        
        {/* Main chat interface */}
        <main id="main-chat" className="h-full">
          <EnhancedChatInterface
            websocketUrl={websocketUrl}
            userId={userId}
            userRole={userRole}
            agentNames={agentNames}
            availableCommands={availableCommands}
            className="h-full"
          />
        </main>
      </div>
    </AccessibilityProvider>
  );
}

// Example usage component showing different configurations
export function ChatAppExamples() {
  return (
    <div className="space-y-8 p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">
        OpenCode Chat Interface Examples
      </h1>
      
      {/* Basic chat */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-800">Basic Chat</h2>
        <div className="h-96 border border-gray-300 rounded-lg overflow-hidden">
          <ChatApp />
        </div>
      </section>
      
      {/* Developer-focused chat */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-800">Developer Chat</h2>
        <div className="h-96 border border-gray-300 rounded-lg overflow-hidden">
          <ChatApp
            userId="dev-alice"
            userRole="senior-developer"
            agentNames={['code-reviewer', 'debugger', 'architect', 'tester']}
            availableCommands={['deploy', 'test', 'review', 'debug', 'docs']}
          />
        </div>
      </section>
      
      {/* Design team chat */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-800">Design Team Chat</h2>
        <div className="h-96 border border-gray-300 rounded-lg overflow-hidden">
          <ChatApp
            userId="designer-bob"
            userRole="ui-designer"
            agentNames={['design-critic', 'accessibility-expert', 'brand-guardian']}
            availableCommands={['prototype', 'feedback', 'assets', 'guidelines']}
          />
        </div>
      </section>
    </div>
  );
}

// Configuration helper for different team types
export const ChatConfigurations = {
  development: {
    agentNames: [
      'code-reviewer',
      'debugger', 
      'architect',
      'performance-optimizer',
      'security-scanner',
      'test-generator'
    ],
    availableCommands: [
      'deploy',
      'test',
      'review',
      'debug',
      'optimize',
      'security-scan',
      'docs',
      'refactor'
    ]
  },
  
  design: {
    agentNames: [
      'design-critic',
      'accessibility-expert',
      'brand-guardian',
      'user-researcher',
      'prototype-builder'
    ],
    availableCommands: [
      'prototype',
      'feedback',
      'assets',
      'guidelines',
      'accessibility-check',
      'user-test'
    ]
  },
  
  product: {
    agentNames: [
      'market-analyst',
      'user-advocate',
      'feature-prioritizer',
      'metrics-tracker',
      'roadmap-planner'
    ],
    availableCommands: [
      'metrics',
      'roadmap',
      'features',
      'user-feedback',
      'market-analysis',
      'prioritize'
    ]
  },
  
  qa: {
    agentNames: [
      'test-planner',
      'bug-hunter',
      'automation-expert',
      'performance-tester',
      'security-tester'
    ],
    availableCommands: [
      'test-plan',
      'bug-report',
      'automate',
      'performance-test',
      'security-test',
      'coverage'
    ]
  }
};

// Hook for easy configuration
export function useChatConfiguration(teamType: keyof typeof ChatConfigurations) {
  return ChatConfigurations[teamType];
}