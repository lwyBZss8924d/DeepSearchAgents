// Configuration types for DeepSearchAgents

export type AgentMode = 'react' | 'codact';

export type VerbosityLevel = 0 | 1 | 2;

export type ExecutorType = 'local' | 'lambda';

export type RerankerType = 'jina-reranker-m0' | 'jina-reranker-v1-base-en' | 'jina-reranker-v1-turbo-en';

export type LogFormat = 'minimal' | 'detailed';

export interface ModelConfig {
  orchestrator_id: string;
  search_id: string;
  reranker_type?: RerankerType;
}

export interface ToolSpecificConfig {
  rerank_texts?: {
    default_model: RerankerType;
  };
  search_links?: {
    num_results: number;
    location: string;
  };
  read_url?: {
    reader_model: string;
  };
  chunk_text?: {
    chunk_size: number;
    chunk_overlap: number;
  };
}

export interface ToolsConfig {
  hub_collections: string[];
  trust_remote_code: boolean;
  mcp_servers: any[];
  specific: ToolSpecificConfig;
}

export interface AgentCommonConfig {
  verbose_tool_callbacks: boolean;
}

export interface ReactAgentConfig {
  max_steps: number;
  planning_interval: number;
  verbosity_level: VerbosityLevel;
}

export interface CodeActAgentConfig {
  executor_type: ExecutorType;
  max_steps: number;
  planning_interval: number;
  verbosity_level: VerbosityLevel;
  executor_kwargs: Record<string, any>;
  additional_authorized_imports: string[];
}

export interface AgentsConfig {
  common: AgentCommonConfig;
  react: ReactAgentConfig;
  codact: CodeActAgentConfig;
}

export interface ServiceConfig {
  host: string;
  port: number;
  version: string;
  deepsearch_agent_mode: AgentMode;
}

export interface LoggingConfig {
  litellm_level: string;
  filter_repeated_logs: boolean;
  filter_cost_calculator: boolean;
  filter_token_counter: boolean;
  enable_token_counting: boolean;
  log_tokens: boolean;
  format: LogFormat;
}

export interface DeepSearchConfig {
  debug: boolean;
  models: ModelConfig;
  tools: ToolsConfig;
  agents: AgentsConfig;
  service: ServiceConfig;
  logging: LoggingConfig;
}

// User preferences for the frontend
export interface UserPreferences {
  selectedAgentMode: AgentMode;
  agentConfig: Partial<ReactAgentConfig & CodeActAgentConfig>;
  modelConfig: Partial<ModelConfig>;
  toolConfig: Partial<ToolSpecificConfig>;
  theme: 'light' | 'dark' | 'system';
  autoSave: boolean;
}

// Configuration update request
export interface ConfigUpdateRequest {
  agent_type: AgentMode;
  config: Partial<DeepSearchConfig>;
}

// Available models and options
export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  description?: string;
}

export interface AgentModeOption {
  value: AgentMode;
  label: string;
  description: string;
  icon: string;
}


