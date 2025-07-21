/**
 * TypeScript type definitions for DeepSearchAgents Web API v2
 * 
 * These types mirror the backend event models for type-safe
 * frontend development.
 */

/**
 * Event types enumeration
 */
export enum EventType {
  // Agent reasoning events
  AGENT_THOUGHT = "agent_thought",
  AGENT_PLANNING = "agent_planning",
  
  // Code generation and execution events
  CODE_GENERATED = "code_generated",
  CODE_EXECUTION_START = "code_execution_start",
  CODE_EXECUTION_OUTPUT = "code_execution_output",
  CODE_EXECUTION_COMPLETE = "code_execution_complete",
  CODE_EXECUTION_ERROR = "code_execution_error",
  
  // Tool interaction events
  TOOL_CALL_START = "tool_call_start",
  TOOL_CALL_OUTPUT = "tool_call_output",
  TOOL_CALL_COMPLETE = "tool_call_complete",
  TOOL_CALL_ERROR = "tool_call_error",
  
  // Task lifecycle events
  TASK_START = "task_start",
  TASK_COMPLETE = "task_complete",
  FINAL_ANSWER = "final_answer",
  
  // Streaming and metadata events
  STREAM_DELTA = "stream_delta",
  TOKEN_UPDATE = "token_update",
  STEP_SUMMARY = "step_summary",
  
  // Planning events (for ReAct mode)
  PLANNING = "planning"
}

/**
 * Base event interface
 */
export interface BaseEvent {
  event_id: string;
  event_type: EventType;
  timestamp: string; // ISO 8601 datetime string
  step_number?: number;
  session_id?: string;
  metadata: Record<string, any>;
}

/**
 * Agent thought/reasoning event
 */
export interface AgentThoughtEvent extends BaseEvent {
  event_type: EventType.AGENT_THOUGHT;
  content: string;
  streaming: boolean;
  complete: boolean;
  thought_type?: string;
}

/**
 * Planning step event
 */
export interface PlanningEvent extends BaseEvent {
  event_type: EventType.PLANNING;
  plan: string;
  plan_number?: number;
}

/**
 * Code generation event
 */
export interface CodeGeneratedEvent extends BaseEvent {
  event_type: EventType.CODE_GENERATED;
  code: string;
  language: string;
  purpose: string;
  tools_used: string[];
}

/**
 * Code execution start event
 */
export interface CodeExecutionStartEvent extends BaseEvent {
  event_type: EventType.CODE_EXECUTION_START;
  code_id: string;
}

/**
 * Code execution output event
 */
export interface CodeExecutionOutputEvent extends BaseEvent {
  event_type: EventType.CODE_EXECUTION_OUTPUT;
  code_id: string;
  output_type: "stdout" | "stderr" | "result" | "display";
  content: string;
  line_number?: number;
  mime_type?: string;
}

/**
 * Code execution complete event
 */
export interface CodeExecutionCompleteEvent extends BaseEvent {
  event_type: EventType.CODE_EXECUTION_COMPLETE;
  code_id: string;
  success: boolean;
  execution_time: number;
  result_summary?: string;
}

/**
 * Code execution error event
 */
export interface CodeExecutionErrorEvent extends BaseEvent {
  event_type: EventType.CODE_EXECUTION_ERROR;
  code_id: string;
  error_type: string;
  error_message: string;
  traceback?: string;
}

/**
 * Tool call start event
 */
export interface ToolCallStartEvent extends BaseEvent {
  event_type: EventType.TOOL_CALL_START;
  tool_name: string;
  tool_arguments: Record<string, any>;
  tool_id: string;
  parent_code_id?: string;
}

/**
 * Tool call output event
 */
export interface ToolCallOutputEvent extends BaseEvent {
  event_type: EventType.TOOL_CALL_OUTPUT;
  tool_id: string;
  output: any;
  output_type: string;
}

/**
 * Tool call complete event
 */
export interface ToolCallCompleteEvent extends BaseEvent {
  event_type: EventType.TOOL_CALL_COMPLETE;
  tool_id: string;
  tool_name: string;
  success: boolean;
  execution_time: number;
}

/**
 * Tool call error event
 */
export interface ToolCallErrorEvent extends BaseEvent {
  event_type: EventType.TOOL_CALL_ERROR;
  tool_id: string;
  tool_name: string;
  error_type: string;
  error_message: string;
}

/**
 * Task start event
 */
export interface TaskStartEvent extends BaseEvent {
  event_type: EventType.TASK_START;
  query: string;
  agent_type: string;
  max_steps?: number;
}

/**
 * Task complete event
 */
export interface TaskCompleteEvent extends BaseEvent {
  event_type: EventType.TASK_COMPLETE;
  success: boolean;
  total_steps: number;
  total_time: number;
  reason?: string;
}

/**
 * Final answer event
 */
export interface FinalAnswerEvent extends BaseEvent {
  event_type: EventType.FINAL_ANSWER;
  content: string;
  format: "markdown" | "html" | "plain";
  sources: string[];
  confidence?: number;
  summary?: string;
}

/**
 * Stream delta event
 */
export interface StreamDeltaEvent extends BaseEvent {
  event_type: EventType.STREAM_DELTA;
  delta_type: string;
  content: string;
  position?: number;
  parent_event_id?: string;
}

/**
 * Token update event
 */
export interface TokenUpdateEvent extends BaseEvent {
  event_type: EventType.TOKEN_UPDATE;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  model?: string;
  cost_estimate?: number;
}

/**
 * Step summary event
 */
export interface StepSummaryEvent extends BaseEvent {
  event_type: EventType.STEP_SUMMARY;
  step_type: string;
  duration: number;
  token_usage: Record<string, number>;
  tools_called: string[];
  success: boolean;
  summary: string;
}

/**
 * Union type for all events
 */
export type AgentEvent = 
  | AgentThoughtEvent
  | PlanningEvent
  | CodeGeneratedEvent
  | CodeExecutionStartEvent
  | CodeExecutionOutputEvent
  | CodeExecutionCompleteEvent
  | CodeExecutionErrorEvent
  | ToolCallStartEvent
  | ToolCallOutputEvent
  | ToolCallCompleteEvent
  | ToolCallErrorEvent
  | TaskStartEvent
  | TaskCompleteEvent
  | FinalAnswerEvent
  | StreamDeltaEvent
  | TokenUpdateEvent
  | StepSummaryEvent;

/**
 * WebSocket message types
 */
export interface WebSocketQuery {
  type: "query";
  query: string;
}

export interface WebSocketPing {
  type: "ping";
}

export interface WebSocketGetEvents {
  type: "get_events";
  event_type?: EventType;
  limit?: number;
}

export interface WebSocketGetState {
  type: "get_state";
}

export type WebSocketMessage = 
  | WebSocketQuery
  | WebSocketPing
  | WebSocketGetEvents
  | WebSocketGetState;

/**
 * WebSocket response types
 */
export interface WebSocketError {
  type: "error";
  message: string;
}

export interface WebSocketPong {
  type: "pong";
}

export interface WebSocketEvents {
  type: "events";
  events: AgentEvent[];
  total: number;
}

export interface WebSocketState {
  type: "state";
  state: SessionState;
}

export type WebSocketResponse = 
  | AgentEvent
  | WebSocketError
  | WebSocketPong
  | WebSocketEvents
  | WebSocketState;

/**
 * Session state
 */
export interface SessionState {
  session_id: string;
  state: "idle" | "processing" | "streaming" | "completed" | "error" | "expired";
  agent_type: string;
  current_task?: string;
  created_at: string;
  last_activity: string;
  total_events: number;
  total_steps: number;
  total_tokens: {
    input: number;
    output: number;
  };
}

/**
 * API request/response types
 */
export interface QueryRequest {
  query: string;
  agent_type?: "react" | "codact";
  max_steps?: number;
  stream?: boolean;
}

export interface QueryResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface SessionInfo {
  session_id: string;
  state: string;
  agent_type: string;
  current_task?: string;
  created_at: string;
  last_activity: string;
  total_events: number;
  total_steps: number;
  total_tokens: Record<string, number>;
}

export interface EventsResponse {
  events: AgentEvent[];
  total: number;
  session_id: string;
}