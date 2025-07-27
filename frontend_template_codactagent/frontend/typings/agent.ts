export enum TAB {
  BROWSER = "browser",
  CODE = "code",
  TERMINAL = "terminal",
}

export const AVAILABLE_MODELS = [
  "claude-sonnet-4@20250514",
  "claude-opus-4@20250514",
  "claude-3-7-sonnet@20250219",
  "gemini-2.5-pro-preview-05-06",
  "gpt-4.1",
];

export enum WebSocketConnectionState {
  CONNECTING = "connecting",
  CONNECTED = "connected",
  DISCONNECTED = "disconnected",
}

export type Source = {
  title: string;
  url: string;
};

export enum AgentEvent {
  AGENT_INITIALIZED = "agent_initialized",
  USER_MESSAGE = "user_message",
  CONNECTION_ESTABLISHED = "connection_established",
  WORKSPACE_INFO = "workspace_info",
  PROCESSING = "processing",
  AGENT_THINKING = "agent_thinking",
  TOOL_CALL = "tool_call",
  TOOL_RESULT = "tool_result",
  AGENT_RESPONSE = "agent_response",
  STREAM_COMPLETE = "stream_complete",
  ERROR = "error",
  SYSTEM = "system",
  PONG = "pong",
  UPLOAD_SUCCESS = "upload_success",
  BROWSER_USE = "browser_use",
  FILE_EDIT = "file_edit",
  PROMPT_GENERATED = "prompt_generated",
}

export enum TOOL {
  SEQUENTIAL_THINKING = "sequential_thinking",
  MESSAGE_USER = "message_user",
  STR_REPLACE_EDITOR = "str_replace_editor",
  BROWSER_USE = "browser_use",
  PRESENTATION = "presentation",
  WEB_SEARCH = "web_search",
  IMAGE_SEARCH = "image_search",
  VISIT = "visit_webpage",
  SHELL_EXEC = "shell_exec",
  SHELL_KILL_PROCESS = "shell_kill_process",
  SHELL_VIEW = "shell_view",
  SHELL_WRITE_TO_PROCESS = "shell_write_to_process",
  SHELL_WAIT = "shell_wait",
  BASH = "bash",
  FULLSTACK_PROJECT_INIT = "fullstack_project_init",
  COMPLETE = "complete",
  STATIC_DEPLOY = "static_deploy",
  REGISTER_DEPLOYMENT = "register_deployment",
  PDF_TEXT_EXTRACT = "pdf_text_extract",
  AUDIO_TRANSCRIBE = "audio_transcribe",
  GENERATE_AUDIO_RESPONSE = "generate_audio_response",
  VIDEO_GENERATE = "generate_video_from_text",
  VIDEO_GENERATE_FROM_IMAGE = "generate_video_from_image",
  LONG_VIDEO_GENERATE = "generate_long_video_from_text",
  LONG_VIDEO_GENERATE_FROM_IMAGE = "generate_long_video_from_image",
  IMAGE_GENERATE = "generate_image_from_text",
  DEEP_RESEARCH = "deep_research",
  LIST_HTML_LINKS = "list_html_links",
  RETURN_CONTROL_TO_USER = "return_control_to_user",
  SLIDE_DECK_INIT = "slide_deck_init",
  SLIDE_DECK_COMPLETE = "slide_deck_complete",
  DISPLAY_IMAGE = "display_image",
  REVIEWER_AGENT = "reviewer_agent",

  GET_DATABASE_CONNECTION = "get_database_connection",
  GET_OPENAI_KEY = "get_openai_api_key",
  // browser tools
  BROWSER_VIEW = "browser_view",
  BROWSER_NAVIGATION = "browser_navigation",
  BROWSER_RESTART = "browser_restart",
  BROWSER_WAIT = "browser_wait",
  BROWSER_SCROLL_DOWN = "browser_scroll_down",
  BROWSER_SCROLL_UP = "browser_scroll_up",
  BROWSER_CLICK = "browser_click",
  BROWSER_ENTER_TEXT = "browser_enter_text",
  BROWSER_PRESS_KEY = "browser_press_key",
  BROWSER_GET_SELECT_OPTIONS = "browser_get_select_options",
  BROWSER_SELECT_DROPDOWN_OPTION = "browser_select_dropdown_option",
  BROWSER_SWITCH_TAB = "browser_switch_tab",
  BROWSER_OPEN_NEW_TAB = "browser_open_new_tab",
  BROWSER_VIEW_INTERACTIVE_ELEMENTS = "browser_view_interactive_elements",
}

export type ActionStep = {
  type: TOOL;
  data: {
    isResult?: boolean;
    tool_name?: string;
    tool_input?: {
      description?: string;
      action?: string;
      text?: string;
      thought?: string;
      path?: string;
      file_text?: string;
      file_path?: string;
      command?: string;
      url?: string;
      query?: string;
      file?: string;
      instruction?: string;
      output_filename?: string;
      key?: string;
      session_id?: string;
      seconds?: number;
      input?: string;
      enter?: boolean;
      framework?: string;
      database_type?: string;
    };
    result?: string | Record<string, unknown>;
    query?: string;
    content?: string;
    path?: string;
  };
};

export interface Message {
  id: string;
  role: "user" | "assistant";
  content?: string;
  timestamp: number;
  action?: ActionStep;
  files?: string[]; // File names
  fileContents?: { [filename: string]: string }; // Base64 content of files
  isHidden?: boolean;
}

export interface ISession {
  id: string;
  workspace_dir: string;
  created_at: string;
  device_id: string;
  name: string;
}

export interface IEvent {
  id: string;
  event_type: AgentEvent;
  event_payload: {
    type: AgentEvent;
    content: Record<string, unknown>;
  };
  timestamp: string;
  workspace_dir: string;
}

export interface ToolSettings {
  deep_research: boolean;
  pdf: boolean;
  media_generation: boolean;
  audio_generation: boolean;
  browser: boolean;
  thinking_tokens: number;
  enable_reviewer: boolean;
}
export interface GooglePickerResponse {
  action: string;
  docs?: Array<GoogleDocument>;
}

export interface GoogleDocument {
  id: string;
  name: string;
  thumbnailUrl: string;
  mimeType: string;
}

export interface LLMConfig {
  api_key?: string;
  model?: string;
  base_url?: string;
  max_retries?: string;
  temperature?: string;
  vertex_region?: string;
  vertex_project_id?: string;
  api_type?: string;
  cot_model?: boolean;
  azure_endpoint?: string;
  azure_api_version?: string;
}

export interface IModel {
  model_name: string;
  provider: string;
}
