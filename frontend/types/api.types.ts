// API types for DeepSearchAgents v2 API

export interface DSAgentRunMessage {
  role: 'user' | 'assistant';
  content: string;
  metadata: {
    streaming?: boolean;
    status?: string;
    title?: string;
    tool_name?: string;
    tool_call_id?: string;
    is_final_answer?: boolean;
    code?: string;
    output?: string;
    [key: string]: any;
  };
  message_id: string;
  timestamp: string;
  session_id?: string;
  step_number?: number;
}

export interface CreateSessionRequest {
  agent_type: 'react' | 'codact';
  max_steps?: number;
}

export interface CreateSessionResponse {
  session_id: string;
  agent_type: string;
  websocket_url: string;
}

export interface SessionState {
  session_id: string;
  agent_type: string;
  state: 'idle' | 'processing' | 'completed' | 'error' | 'expired';
  created_at: string;
  last_activity: string;
  message_count: number;
}

export type WebSocketMessage = 
  | { type: 'query'; query: string }
  | { type: 'ping' }
  | { type: 'get_messages'; limit?: number }
  | { type: 'get_state' };

export type WebSocketResponse =
  | DSAgentRunMessage
  | { type: 'pong' }
  | { type: 'error'; message: string; error_code?: string }
  | { type: 'state'; state: SessionState };