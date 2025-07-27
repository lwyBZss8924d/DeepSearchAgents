// Modified WebSocket hook for v2 API integration
import { useEffect, useRef, useCallback } from 'react';
import { useAppContext } from '@/context/app-context';
import { DSAgentRunMessage, WebSocketMessage } from '@/types/api.types';
import { toast } from 'sonner';

// Enable debug logging for planning messages
const DEBUG_PLANNING = true;

export function useWebSocket(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const pingIntervalRef = useRef<NodeJS.Timeout | undefined>(undefined);
  // Use a Map to track streaming messages by step-type key
  const streamingMessagesRef = useRef<Map<string, DSAgentRunMessage>>(new Map());
  const isConnectingRef = useRef<boolean>(false);
  const { state, dispatch } = useAppContext();
  
  // Note: Content-based detection is no longer needed - we use metadata from backend
  
  const connect = useCallback(() => {
    if (!sessionId) {
      console.log('No sessionId, skipping WebSocket connection');
      return;
    }
    
    // Prevent duplicate connections
    if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log('Already connecting, skipping...');
      return;
    }
    
    // Clear any existing connection
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('Closing existing connection');
      wsRef.current.close();
    }
    
    isConnectingRef.current = true;
    
    // v2 API WebSocket URL
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/api/v2/ws/${sessionId}`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    
    ws.onopen = () => {
      console.log('Connected to v2 WebSocket');
      isConnectingRef.current = false;
      dispatch({ type: 'SET_CONNECTION_STATUS', payload: true });
      toast.success('Connected to agent');
      
      // Clear streaming messages on new connection
      streamingMessagesRef.current.clear();
      
      // Start heartbeat
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
    };
    
    ws.onmessage = (event) => {
      try {
        // Parse JSON message
        const data = JSON.parse(event.data);
        
        // Debug logging
        if (DEBUG_PLANNING) {
          console.log('📨 WebSocket message:', {
            hasType: 'type' in data,
            type: data.type,
            hasRole: 'role' in data,
            role: data.role,
            hasContent: 'content' in data,
            contentLength: data.content?.length,
            hasMetadata: 'metadata' in data,
            metadata: data.metadata,
            step: data.step_number,
            contentPreview: data.content?.substring(0, 30) + '...',
            isStreaming: data.metadata?.streaming
          });
        }
        
        // 1. Handle protocol messages first
        if (data.type === 'pong') {
          return; // Heartbeat response
        }
        
        if (data.type === 'error') {
          console.error('WebSocket error:', data.message);
          toast.error(data.message);
          return;
        }
        
        if (data.type === 'state') {
          console.log('Session state update:', data.state);
          return;
        }
        
        // 2. Check if this is a DSAgentRunMessage (has role, content, or metadata)
        if ('role' in data || 'content' in data || 'metadata' in data) {
          const stepNumber = data.step_number ?? 0;
          
          if (DEBUG_PLANNING) {
            console.log('📩 Processing DSAgentRunMessage:', {
              message_id: data.message_id,
              is_delta: data.metadata?.is_delta,
              is_initial_stream: data.metadata?.is_initial_stream,
              streaming: data.metadata?.streaming,
              stream_id: data.metadata?.stream_id,
              message_type: data.metadata?.message_type,
              step: stepNumber,
              content_preview: data.content?.substring(0, 50) + '...'
            });
            console.log('Full metadata:', data.metadata);
            
            // Special logging for ANY streaming message
            if (data.metadata?.streaming === true) {
              console.log('🌊🌊🌊 STREAMING MESSAGE DETECTED!', {
                message_id: data.message_id,
                stream_id: data.metadata?.stream_id,
                is_initial_stream: data.metadata?.is_initial_stream,
                is_delta: data.metadata?.is_delta,
                willBeTracked: !!(data.metadata?.is_initial_stream && data.metadata?.stream_id)
              });
            }
          }
          
          // Simplified streaming message detection
          const isStreaming = data.metadata?.streaming === true;
          const isDelta = data.metadata?.is_delta === true;
          const messageId = data.message_id;
          
          if (DEBUG_PLANNING && isStreaming) {
            console.log(`🌊 Streaming message detected:`, {
              message_id: messageId,
              is_delta: isDelta,
              stream_id: data.metadata?.stream_id,
              content_length: data.content?.length || 0
            });
          }
          
          // Handle streaming messages
          if (isStreaming && !isDelta) {
            // Initial streaming message - track it by message_id
            if (DEBUG_PLANNING) {
              console.log(`🎯 Initial streaming message: ${messageId}`);
            }
            
            streamingMessagesRef.current.set(messageId, data as DSAgentRunMessage);
            
            // Add to messages array
            dispatch({ type: 'ADD_MESSAGE', payload: data as DSAgentRunMessage });
            
            // Update current step if needed
            if (stepNumber > 0) {
              dispatch({ type: 'SET_CURRENT_STEP', payload: stepNumber });
            }
            
            // Process message for UI updates
            processAgentMessage(data as DSAgentRunMessage, dispatch);
            
          } else if (isDelta && messageId) {
            // This is a streaming update - find and update existing message by message_id
            let foundMessage = false;
            
            if (DEBUG_PLANNING) {
              console.log(`🔍 Delta update for message: ${messageId}`);
              console.log(`Current streamingMessagesRef size: ${streamingMessagesRef.current.size}`);
              console.log(`Keys in streamingMessagesRef:`, Array.from(streamingMessagesRef.current.keys()));
            }
            
            // Try to find the message by message_id first
            const streamingMsg = streamingMessagesRef.current.get(messageId);
            if (streamingMsg) {
              // Update existing streaming message
              const updatedMessage = {
                ...streamingMsg,
                content: data.content // Replace with new accumulated content
              };
              streamingMessagesRef.current.set(messageId, updatedMessage);
              dispatch({ type: 'UPDATE_MESSAGE', payload: updatedMessage });
              
              if (DEBUG_PLANNING) {
                console.log(`🔄 Updated streaming message ${messageId} with ${data.content.length} chars`);
              }
              foundMessage = true;
            } else if (data.metadata?.stream_id) {
              // Fallback: try stream_id if message_id lookup fails
              const streamId = data.metadata.stream_id;
              const msgByStreamId = streamingMessagesRef.current.get(streamId);
              
              if (msgByStreamId) {
                const updatedMessage = {
                  ...msgByStreamId,
                  content: data.content
                };
                streamingMessagesRef.current.set(streamId, updatedMessage);
                dispatch({ type: 'UPDATE_MESSAGE', payload: updatedMessage });
                
                if (DEBUG_PLANNING) {
                  console.log(`🔄 Updated streaming message by stream_id ${streamId}`);
                }
                foundMessage = true;
              }
            }
            
            if (!foundMessage) {
              // Last resort: Update directly in messages array
              if (DEBUG_PLANNING) {
                console.warn(`⚠️ No streaming message found for delta. Updating directly.`);
                console.log(`Message ID: ${messageId}, Stream ID: ${data.metadata?.stream_id}`);
              }
              
              // Ensure we have a valid message_id
              if (!data.message_id && data.metadata?.stream_id) {
                data.message_id = data.metadata.stream_id;
              }
              
              dispatch({ type: 'UPDATE_MESSAGE', payload: data });
            }
            
            // Update current step if needed
            if (stepNumber > 0) {
              dispatch({ type: 'SET_CURRENT_STEP', payload: stepNumber });
            }
          } else {
            // This is a complete message
            console.log(`Complete message for step ${stepNumber}, metadata:`, data.metadata);
            
            // Check if this completes a streaming message
            if (data.metadata?.stream_id) {
              // This message completes a streaming message
              const streamingMsg = streamingMessagesRef.current.get(data.metadata.stream_id);
              if (streamingMsg) {
                // Replace streaming message with complete one
                data.message_id = streamingMsg.message_id; // Keep same ID
                dispatch({ type: 'UPDATE_MESSAGE', payload: data });
                streamingMessagesRef.current.delete(data.metadata.stream_id);
                
                if (DEBUG_PLANNING) {
                  console.log(`✅ Replaced streaming message ${data.metadata.stream_id} with complete message`);
                }
                
                // Process message for UI updates
                processAgentMessage(data, dispatch);
                return;
              } else {
                // If we didn't find it in streamingMessagesRef, it might already be in messages
                // This shouldn't happen, but log it
                console.warn(`⚠️ Complete message with stream_id ${data.metadata.stream_id} but no streaming message found`);
              }
            }
            
            // Regular new message
            if (!data.message_id) {
              data.message_id = `msg-${stepNumber}-${data.metadata?.message_type || 'unknown'}-${crypto.randomUUID()}`;
            }
            
            // CRITICAL: If this is a streaming message, track it by message_id
            // This ensures it's available when deltas arrive
            if (data.metadata?.streaming === true) {
              streamingMessagesRef.current.set(data.message_id, data as DSAgentRunMessage);
              
              // Also track by stream_id if available for backward compatibility
              if (data.metadata?.stream_id && data.metadata.stream_id !== data.message_id) {
                streamingMessagesRef.current.set(data.metadata.stream_id, data as DSAgentRunMessage);
              }
              
              if (DEBUG_PLANNING) {
                console.log(`📌 Tracking streaming message:`);
                console.log(`  message_id: ${data.message_id}`);
                console.log(`  stream_id: ${data.metadata?.stream_id}`);
                console.log(`  message_type: ${data.metadata?.message_type}`);
                console.log(`  streamingMessagesRef now has keys:`, Array.from(streamingMessagesRef.current.keys()));
              }
            }
            
            dispatch({ type: 'ADD_MESSAGE', payload: data as DSAgentRunMessage });
            
            // Process message for UI updates immediately
            processAgentMessage(data as DSAgentRunMessage, dispatch);
          }
        } else {
          console.warn('Unexpected message format:', data);
        }
        
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
        console.error('Raw event data:', event.data);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      isConnectingRef.current = false;
      toast.error('Connection error');
    };
    
    ws.onclose = () => {
      console.log('WebSocket closed');
      isConnectingRef.current = false;
      dispatch({ type: 'SET_CONNECTION_STATUS', payload: false });
      wsRef.current = null;
      
      // Clear streaming messages
      streamingMessagesRef.current.clear();
      
      // Clear heartbeat
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      
      // Attempt reconnection after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        if (sessionId) {
          console.log('Attempting to reconnect...');
          connect();
        }
      }, 3000);
    };
  }, [sessionId, dispatch]);
  
  // Send query to agent
  const sendQuery = useCallback((query: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // Clear any existing streaming messages before new query
      streamingMessagesRef.current.clear();
      
      const message: WebSocketMessage = {
        type: 'query',
        query: query
      };
      
      console.log('Sending query:', message);
      wsRef.current.send(JSON.stringify(message));
      
      // Don't add user message here - let the backend echo it back
      // This prevents duplication (Bug 1)
      
      dispatch({ type: 'SET_GENERATING', payload: true });
      dispatch({ type: 'SET_COMPLETED', payload: false });
      dispatch({ type: 'SET_CURRENT_STEP', payload: 0 });
    } else {
      toast.error('Not connected. Please wait...');
    }
  }, [sessionId, dispatch]);
  
  // Get message history
  const getMessages = useCallback((limit?: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'get_messages',
        limit: limit || 100
      }));
    }
  }, []);
  
  // Get session state
  const getState = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'get_state' }));
    }
  }, []);
  
  // Connect on mount
  useEffect(() => {
    connect();
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);
  
  return { 
    sendQuery,
    getMessages,
    getState,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN
  };
}

// Process DSAgentRunMessage for UI updates
function processAgentMessage(
  message: DSAgentRunMessage, 
  dispatch: any
) {
  console.log('Processing agent message:', {
    role: message.role,
    contentLength: message.content?.length,
    step_number: message.step_number,
    metadata: message.metadata,
    contentPreview: message.content?.substring(0, 100)
  });
  
  // Update UI based on metadata status
  if (message.metadata?.status === 'thinking') {
    console.log('Setting UI state: thinking/generating');
    dispatch({ type: 'SET_GENERATING', payload: true });
  } else if (message.metadata?.status === 'complete' || 
             message.metadata?.status === 'done' ||
             message.metadata?.status === 'finished') {
    console.log('Setting UI state: complete');
    dispatch({ type: 'SET_GENERATING', payload: false });
    dispatch({ type: 'SET_COMPLETED', payload: true });
  }
  
  // Update current step if provided
  if (message.step_number !== undefined && message.step_number !== null) {
    console.log('Updating current step to:', message.step_number);
    dispatch({ type: 'SET_CURRENT_STEP', payload: message.step_number });
  }
  
  // Switch tabs based on component metadata (preferred) or content patterns (fallback)
  const component = message.metadata?.component;
  if (component) {
    // Use component metadata from backend
    console.log(`Component metadata indicates: ${component}`);
    if (component === 'webide') {
      console.log('Switching to code tab - Web IDE component');
      dispatch({ type: 'SET_ACTIVE_TAB', payload: 'code' });
    } else if (component === 'terminal') {
      console.log('Switching to terminal tab - Terminal component');
      dispatch({ type: 'SET_ACTIVE_TAB', payload: 'terminal' });
    }
    // 'chat' component stays on current tab
  } else if (message.content) {
    // Fallback to content-based detection
    if (message.content.includes('```python')) {
      console.log('Switching to code tab - Python code detected');
      dispatch({ type: 'SET_ACTIVE_TAB', payload: 'code' });
    } else if (message.content.includes('Observations:') || 
               message.content.includes('Execution logs:') || 
               message.content.includes('```bash') ||
               message.content.includes('```text') ||
               message.content.includes('```output')) {
      console.log('Switching to terminal tab - Execution output detected');
      dispatch({ type: 'SET_ACTIVE_TAB', payload: 'terminal' });
    }
  }
  
  // Handle specific event types
  const eventType = message.metadata?.event_type;
  if (eventType) {
    console.log(`Event type: ${eventType}`);
    
    // Update state based on event type
    switch (eventType) {
      case 'tool_invocation':
        if (message.metadata?.tool_name === 'python_interpreter') {
          console.log('Python interpreter invoked - ensuring code tab is active');
          dispatch({ type: 'SET_ACTIVE_TAB', payload: 'code' });
        }
        break;
      case 'execution_logs':
      case 'tool_output':
        if (message.metadata?.tool_name === 'python_interpreter') {
          console.log('Python execution output - ensuring terminal tab is active');
          dispatch({ type: 'SET_ACTIVE_TAB', payload: 'terminal' });
        }
        break;
      case 'final_answer':
        console.log('Final answer event detected');
        dispatch({ type: 'SET_GENERATING', payload: false });
        dispatch({ type: 'SET_COMPLETED', payload: true });
        break;
    }
  }
  
  // Check for final answer in content (fallback)
  if (message.content && (
      message.content.includes('Used tool final_answer') || 
      message.content.includes('Final answer:') ||
      message.content.includes('Final Answer:'))) {
    console.log('Final answer detected in content');
    dispatch({ type: 'SET_GENERATING', payload: false });
    dispatch({ type: 'SET_COMPLETED', payload: true });
  }
  
  // Also check metadata for final answer
  if (message.metadata?.title?.toLowerCase().includes('final answer') ||
      message.metadata?.tool_name === 'final_answer' ||
      message.metadata?.is_final_answer) {
    console.log('Final answer detected in metadata');
    dispatch({ type: 'SET_GENERATING', payload: false });
    dispatch({ type: 'SET_COMPLETED', payload: true });
  }
}