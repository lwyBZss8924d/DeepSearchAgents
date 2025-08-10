// DSAgentRunMessage type definitions matching backend
export interface DSAgentRunMessage {
  message_id?: string;
  role: "user" | "assistant";
  content: string;
  session_id?: string;
  step_number?: number;
  metadata?: {
    component?: "chat" | "webide" | "terminal";
    message_type?: string;
    step_type?: string;
    planning_type?: "initial" | "update";
    status?: string;
    streaming?: boolean;
    is_delta?: boolean;
    stream_id?: string;
    tool_name?: string;
    title?: string;
    code?: string;
    language?: string;
    image_path?: string;
    mime_type?: string;
    is_final_answer?: boolean;
    has_structured_data?: boolean;
    answer_title?: string;
    answer_sources?: string[];
    error?: boolean;
    error_type?: string;
  };
  timestamp?: number;
  
  // Additional fields for compatibility with existing Message type
  id?: string;
  action?: any;
  files?: string[];
  fileContents?: { [filename: string]: string };
  isHidden?: boolean;
}

// Export type alias for backward compatibility
export type AgentMessage = DSAgentRunMessage;