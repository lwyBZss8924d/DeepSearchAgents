/**
 * Agent Status Types and Configuration
 * 
 * Defines detailed agent status types and mapping configuration
 * for synchronizing backend events with frontend display states
 */

import type { AgentState } from '@/components/ds/DSAgentStateBadge';

// Detailed agent status types matching backend states
export type DetailedAgentStatus = 
  | 'standby'
  | 'initial_planning' 
  | 'update_planning'
  | 'thinking'
  | 'coding'
  | 'actions_running'
  | 'writing'
  | 'working'
  | 'loading'  // For gaps between streaming events
  | 'error';

// ASCII animation types for different states
export type AnimationType = 
  | 'dots'
  | 'pulse'
  | 'terminal'
  | 'arrows'
  | 'classic'
  | 'brackets'
  | 'divining'
  | 'blueprint'
  | 'thought'
  | 'compilation'
  | 'gears'
  | 'typewriter'
  | 'wheel'
  | 'none';

// Status configuration for display
export interface StatusDisplayConfig {
  text: string;
  icon: string;
  animated: boolean;
  animationType: AnimationType;
  agentState: AgentState;
}

// Complete status configuration mapping
export const statusConfig: Record<DetailedAgentStatus, StatusDisplayConfig> = {
  standby: { 
    text: 'Standby', 
    icon: '◊', 
    animated: false,
    animationType: 'none',
    agentState: 'thinking'
  },
  initial_planning: { 
    text: 'Initial Planning...', 
    icon: '◆', 
    animated: true,
    animationType: 'blueprint',
    agentState: 'planning'
  },
  update_planning: { 
    text: 'Update Planning...', 
    icon: '◆', 
    animated: true,
    animationType: 'blueprint',
    agentState: 'planning'
  },
  thinking: { 
    text: 'Thinking...', 
    icon: '◊', 
    animated: true,
    animationType: 'thought',
    agentState: 'thinking'
  },
  coding: { 
    text: 'Coding...', 
    icon: '▶', 
    animated: true,
    animationType: 'compilation',
    agentState: 'coding'
  },
  actions_running: { 
    text: 'Actions Running...', 
    icon: '■', 
    animated: true,
    animationType: 'gears',
    agentState: 'running'
  },
  writing: { 
    text: 'Writing...', 
    icon: '✓', 
    animated: true,
    animationType: 'typewriter',
    agentState: 'final'
  },
  working: { 
    text: 'Working...', 
    icon: '◊', 
    animated: true,
    animationType: 'wheel',
    agentState: 'working'
  },
  loading: { 
    text: 'Divining...', 
    icon: '✻', 
    animated: true,
    animationType: 'divining',
    agentState: 'thinking'
  },
  error: { 
    text: 'Error', 
    icon: '✗', 
    animated: false,
    animationType: 'none',
    agentState: 'error'
  }
};

// Backend metadata to frontend status mapping
export function mapBackendToFrontendStatus(
  metadata: Record<string, any>,
  isGenerating: boolean = false,
  currentStatus?: DetailedAgentStatus
): DetailedAgentStatus {
  const { 
    step_type, 
    message_type, 
    planning_type, 
    agent_status,
    status,
    is_final_answer,
    error 
  } = metadata;

  // Check for explicit agent_status from backend
  if (agent_status) {
    return agent_status as DetailedAgentStatus;
  }

  // Error state
  if (error || status === 'error') {
    return 'error';
  }

  // Final answer state
  if (is_final_answer || step_type === 'final_answer') {
    return 'writing';
  }

  // Planning states
  if (step_type === 'planning') {
    if (planning_type === 'initial') {
      return 'initial_planning';
    } else if (planning_type === 'update') {
      return 'update_planning';
    }
    return 'initial_planning'; // default planning
  }

  // Action states
  if (step_type === 'action') {
    // Action thought messages should always show as thinking
    if (message_type === 'action_thought' || metadata.is_raw_thought) {
      return 'thinking';
    }
    if (message_type === 'tool_invocation') {
      // Check for specific tools
      if (metadata.tool_name === 'python_interpreter') {
        return 'coding';
      }
      return 'actions_running';
    }
    if (message_type === 'execution_logs') {
      return 'actions_running';
    }
    // Default action state when content suggests thinking
    if (metadata.thoughts_content || (typeof metadata.content === 'string' && metadata.content.includes('Thinking'))) {
      return 'thinking';
    }
  }

  // Generic working state
  if (status === 'streaming' || status === 'thinking' || status === 'processing') {
    return 'working';
  }

  // Check if this is a structural message that shouldn't change status
  const isStructuralMessage = 
    message_type === 'separator' || 
    message_type === 'action_footer' || 
    message_type === 'planning_footer' ||
    (status === 'done' && !is_final_answer);

  // If this is a structural message and we have a current status, preserve it
  if (isStructuralMessage && currentStatus && currentStatus !== 'standby') {
    return currentStatus;
  }

  // If agent is generating but no specific status, show loading
  if (isGenerating) {
    return 'loading';
  }

  // Default to standby only when agent is truly idle
  return 'standby';
}

// Check if status should show animation
export function shouldAnimate(
  status: DetailedAgentStatus, 
  isStreaming: boolean
): boolean {
  // Always animate if streaming
  if (isStreaming) {
    return true;
  }
  
  // Use configuration for non-streaming states
  return statusConfig[status].animated;
}

// Get display configuration for status
export function getStatusDisplay(
  status: DetailedAgentStatus,
  isStreaming: boolean
): StatusDisplayConfig {
  const config = statusConfig[status];
  
  // Override animation based on streaming state
  return {
    ...config,
    animated: shouldAnimate(status, isStreaming)
  };
}