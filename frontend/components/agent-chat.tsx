"use client";

// Simplified chat component for DeepSearchAgents
import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { User, Bot, Loader2 } from "lucide-react";
import { useAppContext } from "@/context/app-context";
import { DSAgentRunMessage } from "@/types/api.types";
import Markdown from "@/components/markdown";
import FinalAnswer from "@/components/final-answer";
import FinalAnswerDisplay from "@/components/final-answer-display";
import ActionThoughtCard from "@/components/action-thought-card";
import ToolCallBadge from "@/components/tool-call-badge";
import { 
  isThinkingMessage, 
  isFinalAnswer, 
  getToolName, 
  extractFinalAnswerContent,
  isPlanningStep,
  isActionStepThought,
  getMessageComponent
} from "@/utils/extractors";

interface AgentChatProps {
  className?: string;
}

export default function AgentChat({ className }: AgentChatProps) {
  const { state } = useAppContext();
  const { messages, isGenerating } = state;
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Debug: Log when messages change
  useEffect(() => {
    console.log(`AgentChat: messages updated, count: ${messages.length}`, {
      totalMessages: messages.length,
      streamingMessages: messages.filter(m => m.metadata?.streaming).length,
      lastMessage: messages[messages.length - 1]
    });
  }, [messages]);

  // Group messages by step
  const messagesByStep = messages.reduce((acc, message) => {
    const step = message.step_number || 0;
    if (!acc[step]) acc[step] = [];
    acc[step].push(message);
    return acc;
  }, {} as Record<number, DSAgentRunMessage[]>);

  // Show all messages that have arrived (no filtering by currentStep for real-time streaming)
  const visibleSteps = Object.keys(messagesByStep)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {visibleSteps.map(step => (
          <div key={step} className="space-y-3">
            {step > 0 && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <div className="flex-1 h-[1px] bg-border" />
                <span>Step {step}</span>
                <div className="flex-1 h-[1px] bg-border" />
              </div>
            )}
            
            {messagesByStep[step].map((message) => (
              <MessageItem key={message.message_id} message={message} />
            ))}
          </div>
        ))}

        {/* Loading indicator */}
        {isGenerating && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 bg-muted rounded-lg p-3">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm text-muted-foreground">
                  Agent is thinking...
                </span>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}

// Individual message component
function MessageItem({ message }: { message: DSAgentRunMessage }) {
  const isUser = message.role === 'user';
  const isThinking = isThinkingMessage(message.metadata) || isPlanningStep(message.metadata);
  const isPlanning = isPlanningStep(message.metadata);
  const isActionThought = isActionStepThought(message.metadata, message.content);
  const isFinal = isFinalAnswer(message.metadata, message.content);
  const isStreaming = message.metadata?.streaming === true;
  const toolName = getToolName(message.metadata);
  const finalAnswerContent = isFinal ? extractFinalAnswerContent(message.content) : null;
  
  // Debug final answer rendering
  if (isFinal) {
    console.log("[AgentChat] Final answer detected:", {
      has_structured_data: message.metadata?.has_structured_data,
      answer_format: message.metadata?.answer_format,
      content_empty: !message.content,
      finalAnswerContent,
      metadata: message.metadata
    });
  }
  
  // Debug action thought rendering
  if (isActionThought) {
    console.log("[AgentChat] Action thought detected:", {
      message_type: message.metadata?.message_type,
      thoughts_content: message.metadata?.thoughts_content,
      content_length: message.content?.length,
      step_number: message.step_number,
      metadata: message.metadata
    });
  }
  
  // Use metadata-based routing - trust the backend's component field
  const messageComponent = getMessageComponent(message.metadata);
  
  // Skip messages that are specifically routed to other components
  if (!isUser && messageComponent !== 'chat') {
    return null;
  }
  
  // Skip duplicate error messages that should only appear in code editor
  if (message.content.includes('Error in code parsing') || 
      message.content.includes('Executing parsed code')) {
    return null;
  }
  
  // Handle planning header messages (badges)
  if (message.metadata?.message_type === 'planning_header') {
    const planningType = message.metadata.planning_type || 'initial';
    const badgeText = planningType === 'initial' ? 'Initial Plan' : 'Updated Plan';
    const badgeClass = planningType === 'initial' ? 'planning-badge-initial' : 'planning-badge-update';
    
    console.log('[AgentChat] Rendering planning badge:', {
      planningType,
      badgeText,
      badgeClass,
      metadata: message.metadata
    });
    
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start gap-3"
      >
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
          <Bot className="w-5 h-5 text-primary" />
        </div>
        <div className="flex-1">
          <span className={`planning-badge ${badgeClass}`}>
            {badgeText}
          </span>
        </div>
      </motion.div>
    );
  }
  
  // Handle empty planning messages with a fallback display
  if (isPlanning && (!message.content || message.content.trim() === '')) {
    console.warn('Planning message with empty content detected:', message);
    // Show planning message with placeholder content instead of hiding it
    message = {
      ...message,
      content: '*Planning in progress...*'
    };
  }

  // Skip separator messages entirely - they just add visual clutter
  if (message.metadata?.message_type === 'separator') {
    console.log('[AgentChat] Filtering out separator message');
    return null;
  }

  // Skip empty content messages (except planning_header and tool_call which have special handling)
  if (!message.content?.trim() && 
      message.metadata?.message_type !== 'planning_header' &&
      message.metadata?.message_type !== 'tool_call' &&
      !isFinal) {
    console.log('[AgentChat] Filtering out empty message:', {
      message_type: message.metadata?.message_type,
      content: message.content
    });
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isUser ? 'bg-blue-500' : 'bg-primary/10'
      }`}>
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-primary" />
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
        {/* Metadata tags */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {/* Tool name tag */}
            {toolName && (
              <span className="text-xs px-2 py-1 bg-blue-500/10 text-blue-500 rounded">
                Tool: {toolName}
              </span>
            )}
            
            {/* Message type tags based on metadata */}
            {isPlanning && (
              <span className="text-xs px-2 py-1 bg-purple-500/10 text-purple-500 rounded">
                Planning
              </span>
            )}
            
            {/* Show Step N tag for action steps */}
            {message.content.startsWith('**Step') && !isPlanning && (
              <span className="text-xs px-2 py-1 bg-indigo-500/10 text-indigo-500 rounded">
                Action Step
              </span>
            )}
            
            {isActionThought && (
              <span className="text-xs px-2 py-1 bg-orange-500/10 text-orange-500 rounded">
                Thought
              </span>
            )}
            
            {isFinal && (
              <span className="text-xs px-2 py-1 bg-green-500/10 text-green-500 rounded">
                Final Answer
              </span>
            )}
            
            {/* Event type from metadata */}
            {message.metadata?.event_type && !toolName && !isPlanning && !isFinal && (
              <span className="text-xs px-2 py-1 bg-gray-500/10 text-gray-500 rounded">
                {message.metadata.event_type.replace(/_/g, ' ')}
              </span>
            )}
            
            {/* Streaming indicator */}
            {isStreaming && (
              <span className="text-xs px-2 py-1 bg-blue-500/10 text-blue-500 rounded animate-pulse">
                Streaming...
              </span>
            )}
          </div>
        )}

        {/* Message bubble */}
        {message.metadata?.message_type === 'tool_call' ? (
          // Use ToolCallBadge for tool calls
          <ToolCallBadge
            toolName={message.metadata?.tool_name || "unknown"}
            toolId={message.metadata?.tool_call_id}
            argsSummary={message.content || ""}
            isPythonInterpreter={message.metadata?.tool_name === 'python_interpreter'}
            className="w-full"
          />
        ) : message.metadata?.message_type === 'action_thought' || isActionThought ? (
          // Use ActionThoughtCard for action thoughts
          <ActionThoughtCard
            content={message.content || ""}
            stepNumber={message.step_number}
            metadata={message.metadata}
            className="w-full"
          />
        ) : isFinal ? (
          // Check if we have structured data in metadata
          message.metadata?.has_structured_data ? (
            <FinalAnswerDisplay 
              content={message.content || ""} 
              metadata={message.metadata}
              className="w-full" 
            />
          ) : finalAnswerContent ? (
            <FinalAnswer content={finalAnswerContent} />
          ) : (
            // Fallback for final answer with no content
            <FinalAnswer content="Processing final answer..." />
          )
        ) : (
          <div className={`inline-block max-w-[80%] ${
            isUser 
              ? 'bg-blue-500 text-white rounded-2xl px-4 py-2' 
              : isThinking
              ? 'bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 w-full max-w-none'
              : 'bg-muted rounded-lg p-3'
          }`}>
            {isUser ? (
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <Markdown>{message.content}</Markdown>
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        {message.timestamp && (
          <div className="text-xs text-muted-foreground mt-1">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
    </motion.div>
  );
}