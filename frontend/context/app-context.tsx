"use client";

import { createContext, useContext, useReducer, ReactNode } from "react";
import { DSAgentRunMessage } from "@/types/api.types";

// Define the state interface - simplified for v2 API
interface AppState {
  // Session management
  sessionId: string | null;
  agentType: 'react' | 'codact';
  
  // Messages
  messages: DSAgentRunMessage[];
  
  // UI state
  activeTab: 'browser' | 'code';
  currentStep: number;
  maxStep: number;
  
  // Connection state
  isConnected: boolean;
  isGenerating: boolean;
  isCompleted: boolean;
  
  // Current input
  currentQuestion: string;
  
  // Agent task status
  agentTaskStatus: string;
  agentTaskState: 'planning' | 'thinking' | 'coding' | 'running' | 'final' | 'working' | null;
  isStreaming: boolean;
  
  // Current agent status - single source of truth
  currentAgentStatus: string; // 'standby' | 'initial_planning' | 'update_planning' | 'thinking' | 'coding' | 'actions_running' | 'writing' | 'working'
  
  // Agent timing
  agentStartTime: number | null; // Timestamp when agent started running
}

// Define action types - simplified for v2 API
export type AppAction =
  | { type: 'SET_SESSION_ID'; payload: string | null }
  | { type: 'SET_AGENT_TYPE'; payload: 'react' | 'codact' }
  | { type: 'SET_MESSAGES'; payload: DSAgentRunMessage[] }
  | { type: 'ADD_MESSAGE'; payload: DSAgentRunMessage }
  | { type: 'UPDATE_MESSAGE'; payload: DSAgentRunMessage }
  | { type: 'SET_ACTIVE_TAB'; payload: 'browser' | 'code' }
  | { type: 'SET_CURRENT_STEP'; payload: number }
  | { type: 'SET_MAX_STEP'; payload: number }
  | { type: 'SET_CONNECTION_STATUS'; payload: boolean }
  | { type: 'SET_GENERATING'; payload: boolean }
  | { type: 'SET_COMPLETED'; payload: boolean }
  | { type: 'SET_CURRENT_QUESTION'; payload: string }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'RESET_STATE' }
  | { type: 'SET_AGENT_TASK_STATUS'; payload: string }
  | { type: 'SET_AGENT_TASK_STATE'; payload: 'planning' | 'thinking' | 'coding' | 'running' | 'final' | 'working' | null }
  | { type: 'SET_IS_STREAMING'; payload: boolean }
  | { type: 'SET_CURRENT_AGENT_STATUS'; payload: string }
  | { type: 'SET_AGENT_START_TIME'; payload: number | null };

// Initial state
const initialState: AppState = {
  sessionId: null,
  agentType: 'codact',
  messages: [],
  activeTab: 'browser',
  currentStep: 0,
  maxStep: 0,
  isConnected: false,
  isGenerating: false,
  isCompleted: false,
  currentQuestion: '',
  agentTaskStatus: '',
  agentTaskState: null,
  isStreaming: false,
  currentAgentStatus: 'standby',
  agentStartTime: null,
};

// Create the context
const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}>({
  state: initialState,
  dispatch: () => null,
});

// Reducer function
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
      
    case 'SET_AGENT_TYPE':
      return { ...state, agentType: action.payload };
      
    case 'SET_MESSAGES':
      const maxStepFromMessages = Math.max(
        0,
        ...action.payload.map(m => m.step_number || 0)
      );
      return { 
        ...state, 
        messages: action.payload,
        maxStep: maxStepFromMessages
      };
      
    case 'ADD_MESSAGE':
      // Check if message with same ID already exists
      const existingIndex = state.messages.findIndex(
        msg => msg.message_id === action.payload.message_id
      );
      
      let newMessages;
      if (existingIndex >= 0) {
        // Update existing message instead of adding duplicate
        console.warn(`Message with ID ${action.payload.message_id} already exists, updating instead`);
        newMessages = [...state.messages];
        newMessages[existingIndex] = action.payload;
      } else {
        // Add new message
        newMessages = [...state.messages, action.payload];
      }
      
      const newMaxStep = action.payload.step_number 
        ? Math.max(state.maxStep, action.payload.step_number)
        : state.maxStep;
      return { 
        ...state, 
        messages: newMessages,
        maxStep: newMaxStep
      };
      
    case 'UPDATE_MESSAGE':
      // Find message by message_id first
      let messageFound = false;
      let updatedMessages = state.messages.map((message) => {
        if (message.message_id === action.payload.message_id) {
          messageFound = true;
          return action.payload;
        }
        return message;
      });
      
      // If not found by message_id and we have a stream_id, try that
      if (!messageFound && action.payload.metadata?.stream_id) {
        updatedMessages = state.messages.map((message) => {
          if (message.metadata?.stream_id === action.payload.metadata.stream_id ||
              message.message_id === action.payload.metadata.stream_id) {
            messageFound = true;
            // Preserve the original message_id
            return { ...action.payload, message_id: message.message_id };
          }
          return message;
        });
      }
      
      // If still not found, log warning but don't add as new message
      if (!messageFound) {
        console.warn(`UPDATE_MESSAGE: No message found with ID ${action.payload.message_id} or stream_id ${action.payload.metadata?.stream_id}`);
      }
      
      return {
        ...state,
        messages: updatedMessages,
      };
      
    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };
      
    case 'SET_CURRENT_STEP':
      return { ...state, currentStep: action.payload };
      
    case 'SET_MAX_STEP':
      return { ...state, maxStep: action.payload };
      
    case 'SET_CONNECTION_STATUS':
      return { ...state, isConnected: action.payload };
      
    case 'SET_GENERATING':
      return { ...state, isGenerating: action.payload };
      
    case 'SET_COMPLETED':
      return { ...state, isCompleted: action.payload };
      
    case 'SET_CURRENT_QUESTION':
      return { ...state, currentQuestion: action.payload };
      
    case 'CLEAR_MESSAGES':
      return { 
        ...state, 
        messages: [], 
        currentStep: 0, 
        maxStep: 0,
        isCompleted: false,
        isGenerating: false
      };
      
    case 'RESET_STATE':
      return initialState;
      
    case 'SET_AGENT_TASK_STATUS':
      return { ...state, agentTaskStatus: action.payload };
      
    case 'SET_AGENT_TASK_STATE':
      return { ...state, agentTaskState: action.payload };
      
    case 'SET_IS_STREAMING':
      return { ...state, isStreaming: action.payload };
      
    case 'SET_CURRENT_AGENT_STATUS':
      return { 
        ...state, 
        currentAgentStatus: action.payload
      };
      
    case 'SET_AGENT_START_TIME':
      return { 
        ...state, 
        agentStartTime: action.payload
      };
      
    default:
      return state;
  }
}

// Context provider component
export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

// Custom hook to use the app context
export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used within AppProvider");
  }
  return context;
}