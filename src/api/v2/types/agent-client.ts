/**
 * WebSocket client for DeepSearchAgents Web API v2
 * 
 * Provides a type-safe client for interacting with the agent
 * through WebSocket connections.
 */

import { 
  EventType, 
  AgentEvent, 
  WebSocketMessage, 
  WebSocketResponse,
  SessionState 
} from './agent-events';

// Re-export types for convenience
export {
  EventType,
  AgentEvent,
  AgentThoughtEvent,
  PlanningEvent,
  CodeGeneratedEvent,
  CodeExecutionStartEvent,
  CodeExecutionOutputEvent,
  CodeExecutionCompleteEvent,
  CodeExecutionErrorEvent,
  ToolCallStartEvent,
  ToolCallOutputEvent,
  ToolCallCompleteEvent,
  ToolCallErrorEvent,
  TaskStartEvent,
  TaskCompleteEvent,
  FinalAnswerEvent,
  StreamDeltaEvent,
  TokenUpdateEvent,
  StepSummaryEvent,
  SessionState,
  WebSocketMessage,
  WebSocketResponse
} from './agent-events';

/**
 * Event handler type
 */
export type EventHandler<T = AgentEvent> = (event: T) => void;

/**
 * Event handler map
 */
export type EventHandlerMap = {
  [K in EventType]?: EventHandler<Extract<AgentEvent, { event_type: K }>>;
} & {
  '*'?: EventHandler<AgentEvent>;
};

/**
 * WebSocket client options
 */
export interface AgentWebSocketOptions {
  url?: string;
  reconnect?: boolean;
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
}

/**
 * WebSocket connection state
 */
export enum ConnectionState {
  CONNECTING = "connecting",
  CONNECTED = "connected",
  DISCONNECTED = "disconnected",
  RECONNECTING = "reconnecting",
  ERROR = "error"
}

/**
 * Agent WebSocket client
 */
export class AgentWebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private options: Required<AgentWebSocketOptions>;
  private eventHandlers: EventHandlerMap = {};
  private connectionHandlers: {
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Error) => void;
    onStateChange?: (state: ConnectionState) => void;
  } = {};
  
  private reconnectAttempts = 0;
  private pingTimer?: number;
  private connectionState: ConnectionState = ConnectionState.DISCONNECTED;
  
  constructor(sessionId: string, options: AgentWebSocketOptions = {}) {
    this.sessionId = sessionId;
    this.options = {
      url: options.url || `/api/v2/ws/agent/${sessionId}`,
      reconnect: options.reconnect ?? true,
      reconnectDelay: options.reconnectDelay ?? 1000,
      maxReconnectAttempts: options.maxReconnectAttempts ?? 5,
      pingInterval: options.pingInterval ?? 30000
    };
  }
  
  /**
   * Connect to WebSocket
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }
      
      this.setConnectionState(ConnectionState.CONNECTING);
      
      try {
        // Construct full WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const url = `${protocol}//${host}${this.options.url}`;
        
        this.ws = new WebSocket(url);
        
        this.ws.onopen = () => {
          this.setConnectionState(ConnectionState.CONNECTED);
          this.reconnectAttempts = 0;
          this.startPing();
          this.connectionHandlers.onConnect?.();
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as WebSocketResponse;
            this.handleMessage(data);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };
        
        this.ws.onclose = () => {
          this.setConnectionState(ConnectionState.DISCONNECTED);
          this.stopPing();
          this.connectionHandlers.onDisconnect?.();
          
          if (this.options.reconnect && this.reconnectAttempts < this.options.maxReconnectAttempts) {
            this.reconnect();
          }
        };
        
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.connectionHandlers.onError?.(new Error('WebSocket error'));
          reject(new Error('WebSocket connection failed'));
        };
        
      } catch (error) {
        this.setConnectionState(ConnectionState.ERROR);
        reject(error);
      }
    });
  }
  
  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.options.reconnect = false;
    this.stopPing();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.setConnectionState(ConnectionState.DISCONNECTED);
  }
  
  /**
   * Send a query to the agent
   */
  sendQuery(query: string): void {
    this.send({ type: "query", query });
  }
  
  /**
   * Get historical events
   */
  getEvents(eventType?: EventType, limit?: number): void {
    this.send({ 
      type: "get_events", 
      event_type: eventType,
      limit 
    });
  }
  
  /**
   * Get session state
   */
  getState(): void {
    this.send({ type: "get_state" });
  }
  
  /**
   * Register event handler
   */
  on<T extends EventType>(
    eventType: T,
    handler: EventHandler<Extract<AgentEvent, { event_type: T }>>
  ): void {
    this.eventHandlers[eventType] = handler as any;
  }
  
  /**
   * Remove event handler
   */
  off(eventType: EventType): void {
    delete this.eventHandlers[eventType];
  }
  
  /**
   * Register connection event handlers
   */
  onConnection(handlers: {
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Error) => void;
    onStateChange?: (state: ConnectionState) => void;
  }): void {
    this.connectionHandlers = { ...this.connectionHandlers, ...handlers };
  }
  
  /**
   * Get current connection state
   */
  getConnectionState(): ConnectionState {
    return this.connectionState;
  }
  
  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
  
  private send(message: WebSocketMessage): void {
    if (!this.isConnected()) {
      throw new Error('WebSocket is not connected');
    }
    
    this.ws!.send(JSON.stringify(message));
  }
  
  private handleMessage(data: WebSocketResponse): void {
    // Handle different response types
    if ('event_type' in data) {
      // This is an agent event
      const event = data as AgentEvent;
      const handler = this.eventHandlers[event.event_type];
      if (handler) {
        handler(event as any);
      }
      
      // Also call generic event handler if exists
      const allHandler = (this.eventHandlers as any)['*'] as EventHandler<AgentEvent> | undefined;
      if (allHandler) {
        allHandler(event);
      }
    } else if ('type' in data) {
      // This is a WebSocket control message
      switch (data.type) {
        case 'error':
          console.error('WebSocket error:', data.message);
          this.connectionHandlers.onError?.(new Error(data.message));
          break;
          
        case 'pong':
          // Pong received, connection is alive
          break;
          
        case 'events':
          // Historical events received
          // Could emit a special event or handle differently
          break;
          
        case 'state':
          // Session state received
          // Could emit a special event or handle differently
          break;
      }
    }
  }
  
  private setConnectionState(state: ConnectionState): void {
    if (this.connectionState !== state) {
      this.connectionState = state;
      this.connectionHandlers.onStateChange?.(state);
    }
  }
  
  private reconnect(): void {
    this.reconnectAttempts++;
    this.setConnectionState(ConnectionState.RECONNECTING);
    
    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
      this.connect().catch(() => {
        // Error handled in connect method
      });
    }, this.options.reconnectDelay * this.reconnectAttempts);
  }
  
  private startPing(): void {
    this.pingTimer = window.setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: "ping" });
      }
    }, this.options.pingInterval);
  }
  
  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = undefined;
    }
  }
}

/**
 * Helper function to create and connect client
 */
export async function createAgentClient(
  sessionId: string,
  options?: AgentWebSocketOptions
): Promise<AgentWebSocketClient> {
  const client = new AgentWebSocketClient(sessionId, options);
  await client.connect();
  return client;
}