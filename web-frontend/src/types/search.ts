import { AgentExecution, AgentConfig } from './agent';

export interface SearchSession {
  id: string;
  query: string;
  config: AgentConfig;
  execution?: AgentExecution;
  createdAt: Date;
  updatedAt: Date;
}

export interface SearchHistory {
  sessions: SearchSession[];
  totalCount: number;
}

export interface SearchFilters {
  agentType?: 'react' | 'codact';
  dateRange?: {
    start: Date;
    end: Date;
  };
  status?: 'completed' | 'error' | 'running';
  query?: string;
}

