export type AgentType = 'react' | 'codact';

export interface AgentConfig {
  type: AgentType;
  model: string;
  temperature: number;
  maxTokens: number;
  tools: string[];
}

export interface AgentStep {
  id: string;
  type: 'thought' | 'action' | 'observation' | 'final_answer';
  content: string;
  timestamp: Date;
  toolName?: string;
  toolInput?: any;
  toolOutput?: any;
  error?: string;
}

export interface AgentExecution {
  id: string;
  query: string;
  config: AgentConfig;
  steps: AgentStep[];
  status: 'running' | 'completed' | 'error' | 'cancelled';
  startTime: Date;
  endTime?: Date;
  finalAnswer?: string;
  error?: string;
}

export interface StreamingResponse {
  type: 'step' | 'final_answer' | 'error' | 'status';
  data: AgentStep | string | { status: string };
}

export interface SearchResult {
  id: string;
  title: string;
  url: string;
  snippet: string;
  score?: number;
}

