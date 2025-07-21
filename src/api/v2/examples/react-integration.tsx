/**
 * Example React component for DeepSearchAgents Web UI
 * 
 * Demonstrates how to integrate with the Web API v2 using
 * the WebSocket client and event system.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  AgentWebSocketClient, 
  EventType, 
  AgentEvent,
  AgentThoughtEvent,
  CodeGeneratedEvent,
  CodeExecutionOutputEvent,
  ToolCallStartEvent,
  FinalAnswerEvent,
  ConnectionState
} from '../types/agent-client';

interface Message {
  id: string;
  type: 'user' | 'agent' | 'thought' | 'planning';
  content: string;
  timestamp: Date;
}

interface CodeExecution {
  id: string;
  code: string;
  outputs: Array<{
    type: string;
    content: string;
  }>;
  status: 'running' | 'completed' | 'error';
}

interface AgentStep {
  number: number;
  thought?: string;
  code?: CodeExecution;
  tools: Array<{
    name: string;
    status: 'running' | 'completed' | 'error';
  }>;
}

export const DeepSearchAgentUI: React.FC = () => {
  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentStep, setCurrentStep] = useState<AgentStep | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>(
    ConnectionState.DISCONNECTED
  );
  const [sessionId] = useState(() => generateSessionId());
  
  // Refs
  const clientRef = useRef<AgentWebSocketClient | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const codeOutputRef = useRef<HTMLDivElement>(null);
  
  // Initialize WebSocket client
  useEffect(() => {
    const client = new AgentWebSocketClient(sessionId);
    clientRef.current = client;
    
    // Set up connection handlers
    client.onConnection({
      onConnect: () => {
        console.log('Connected to agent');
        setConnectionState(ConnectionState.CONNECTED);
      },
      onDisconnect: () => {
        console.log('Disconnected from agent');
        setConnectionState(ConnectionState.DISCONNECTED);
      },
      onError: (error) => {
        console.error('Connection error:', error);
        setConnectionState(ConnectionState.ERROR);
      },
      onStateChange: setConnectionState
    });
    
    // Set up event handlers
    setupEventHandlers(client);
    
    // Connect
    client.connect().catch(console.error);
    
    // Cleanup
    return () => {
      client.disconnect();
    };
  }, [sessionId]);
  
  // Set up event handlers
  const setupEventHandlers = (client: AgentWebSocketClient) => {
    // Task start
    client.on(EventType.TASK_START, (event) => {
      setIsProcessing(true);
      setMessages(prev => [...prev, {
        id: event.event_id,
        type: 'user',
        content: event.query,
        timestamp: new Date(event.timestamp)
      }]);
    });
    
    // Agent thoughts
    client.on(EventType.AGENT_THOUGHT, (event: AgentThoughtEvent) => {
      if (event.complete) {
        // Update current step
        setCurrentStep(prev => ({
          ...prev!,
          number: event.step_number || 0,
          thought: event.content
        }));
        
        // Add thought message
        setMessages(prev => [...prev, {
          id: event.event_id,
          type: 'thought',
          content: event.content,
          timestamp: new Date(event.timestamp)
        }]);
      }
    });
    
    // Planning
    client.on(EventType.PLANNING, (event) => {
      setMessages(prev => [...prev, {
        id: event.event_id,
        type: 'planning',
        content: event.plan,
        timestamp: new Date(event.timestamp)
      }]);
    });
    
    // Code generation
    client.on(EventType.CODE_GENERATED, (event: CodeGeneratedEvent) => {
      const codeExec: CodeExecution = {
        id: event.event_id,
        code: event.code,
        outputs: [],
        status: 'running'
      };
      
      setCurrentStep(prev => ({
        ...prev!,
        code: codeExec
      }));
    });
    
    // Code execution output
    client.on(EventType.CODE_EXECUTION_OUTPUT, (event: CodeExecutionOutputEvent) => {
      setCurrentStep(prev => {
        if (!prev?.code) return prev;
        
        return {
          ...prev,
          code: {
            ...prev.code,
            outputs: [...prev.code.outputs, {
              type: event.output_type,
              content: event.content
            }]
          }
        };
      });
    });
    
    // Code execution complete
    client.on(EventType.CODE_EXECUTION_COMPLETE, (event) => {
      setCurrentStep(prev => {
        if (!prev?.code) return prev;
        
        return {
          ...prev,
          code: {
            ...prev.code,
            status: event.success ? 'completed' : 'error'
          }
        };
      });
    });
    
    // Tool calls
    client.on(EventType.TOOL_CALL_START, (event: ToolCallStartEvent) => {
      setCurrentStep(prev => ({
        ...prev!,
        tools: [...(prev?.tools || []), {
          name: event.tool_name,
          status: 'running' as const
        }]
      }));
    });
    
    // Step summary - finalize step
    client.on(EventType.STEP_SUMMARY, (event) => {
      if (currentStep) {
        setSteps(prev => [...prev, currentStep]);
        setCurrentStep(null);
      }
    });
    
    // Final answer
    client.on(EventType.FINAL_ANSWER, (event: FinalAnswerEvent) => {
      setMessages(prev => [...prev, {
        id: event.event_id,
        type: 'agent',
        content: event.content,
        timestamp: new Date(event.timestamp)
      }]);
    });
    
    // Task complete
    client.on(EventType.TASK_COMPLETE, (event) => {
      setIsProcessing(false);
    });
  };
  
  // Handle query submission
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim() || !clientRef.current?.isConnected() || isProcessing) {
      return;
    }
    
    // Clear previous state
    setMessages([]);
    setSteps([]);
    setCurrentStep(null);
    
    // Send query
    clientRef.current.sendQuery(query.trim());
    setQuery('');
  }, [query, isProcessing]);
  
  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Auto-scroll code output
  useEffect(() => {
    if (currentStep?.code?.outputs.length) {
      codeOutputRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [currentStep?.code?.outputs]);
  
  return (
    <div className="deepsearch-agent-ui">
      {/* Header */}
      <header className="header">
        <h1>DeepSearch Agent</h1>
        <div className="connection-status">
          <span className={`status-indicator ${connectionState}`} />
          {connectionState}
        </div>
      </header>
      
      {/* Main content */}
      <div className="main-content">
        {/* Left panel - Chat */}
        <div className="chat-panel">
          <div className="messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`message ${msg.type}`}>
                <div className="message-header">
                  <span className="message-type">{msg.type}</span>
                  <span className="message-time">
                    {msg.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                <div className="message-content">
                  {msg.type === 'agent' ? (
                    <MarkdownRenderer content={msg.content} />
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Query input */}
          <form onSubmit={handleSubmit} className="query-form">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question..."
              disabled={!clientRef.current?.isConnected() || isProcessing}
              className="query-input"
            />
            <button 
              type="submit" 
              disabled={!clientRef.current?.isConnected() || isProcessing || !query.trim()}
              className="query-submit"
            >
              {isProcessing ? 'Processing...' : 'Send'}
            </button>
          </form>
        </div>
        
        {/* Right panel - Code & Output */}
        <div className="code-panel">
          {currentStep?.code && (
            <div className="code-execution">
              <div className="code-section">
                <h3>Code</h3>
                <pre className="code-block">
                  <code>{currentStep.code.code}</code>
                </pre>
              </div>
              
              <div className="output-section">
                <h3>Output</h3>
                <div className="output-content">
                  {currentStep.code.outputs.map((output, idx) => (
                    <div key={idx} className={`output-line ${output.type}`}>
                      {output.content}
                    </div>
                  ))}
                  <div ref={codeOutputRef} />
                </div>
              </div>
            </div>
          )}
          
          {/* Step history */}
          <div className="step-history">
            <h3>Execution Steps</h3>
            {steps.map((step) => (
              <div key={step.number} className="step-summary">
                <div className="step-number">Step {step.number}</div>
                {step.tools.map((tool, idx) => (
                  <div key={idx} className={`tool-call ${tool.status}`}>
                    {tool.name}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper components
const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  // Simple markdown rendering - in production use a proper library
  return <div dangerouslySetInnerHTML={{ __html: content }} />;
};

// Helper functions
function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}