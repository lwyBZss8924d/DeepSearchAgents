"use client";

// WebTUI-based chat component for DeepSearchAgents
import { useEffect } from "react";
import { useAppContext } from "@/context/app-context";
import { DSAgentRunMessage } from "@/types/api.types";
import { useAutoScroll, ScrollToBottomButton } from "@/hooks/use-auto-scroll";
import Markdown from "@/components/markdown";
import FinalAnswer from "@/components/final-answer";
import FinalAnswerDisplay from "@/components/final-answer-display";
import ActionThoughtCard from "@/components/action-thought-card";
import { cn } from "@/lib/utils";
import { 
  DSAgentMessageCard,
  DSAgentStateBadge,
  DSAgentToolBadge,
  DSAgentStreamingText,
  DSAgentTUILogo,
  type AgentState
} from "@/components/ds";
import { AGENT_SYMBOLS } from '@/utils/bagua-symbols';
import { mapBackendToFrontendStatus, getStatusDisplay } from '@/types/agent-status.types';
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
  const { messages } = state;
  
  // Use enhanced auto-scroll hook
  const { 
    scrollRef, 
    isAtBottom, 
    scrollToBottom 
  } = useAutoScroll({
    enabled: true,
    smooth: true,
    pauseOnHover: true
  });

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
    <div className={cn("flex flex-col h-full", className)}>
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        {/* Welcome ASCII art when no messages */}
        {messages.length === 0 && (
          <div className="ds-welcome-container flex flex-col items-center justify-center min-h-[400px] space-y-4">
            <DSAgentTUILogo variant="default" animate={true} />
          </div>
        )}
        
        {visibleSteps.map(step => (
          <div key={step} className="ds-step-group">
            {step > 0 && (
              <div className="ds-step-separator my-4">
                <div className="ds-step-line" />
                <span className="ds-step-label text-[var(--ds-terminal-dim)] text-xs font-mono">
                  Step {step}
                </span>
                <div className="ds-step-line" />
              </div>
            )}
            {messagesByStep[step].map((message, index) => (
              <MessageItem 
                key={message.message_id} 
                message={message} 
                previousMessage={index > 0 ? messagesByStep[step][index - 1] : undefined}
              />
            ))}
          </div>
        ))}


      </div>
      <ScrollToBottomButton 
        isVisible={!isAtBottom} 
        onClick={scrollToBottom} 
      />
    </div>
  );
}

// Individual message component with WebTUI styling
function MessageItem({ message, previousMessage }: { message: DSAgentRunMessage; previousMessage?: DSAgentRunMessage }) {
  const isUser = message.role === 'user';
  const isPlanning = isPlanningStep(message.metadata);
  const isActionThought = isActionStepThought(message.metadata, message.content);
  const isFinal = isFinalAnswer(message.metadata, message.content);
  const isStreaming = message.metadata?.streaming === true;
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
  if (isActionThought || message.metadata?.message_type === 'action_thought') {
    console.log("[AgentChat] Action thought detected:", {
      message_type: message.metadata?.message_type,
      thoughts_content: message.metadata?.thoughts_content,
      content_length: message.content?.length,
      step_number: message.step_number,
      streaming: isStreaming,
      is_initial_stream: message.metadata?.is_initial_stream,
      metadata: message.metadata
    });
  }
  
  // Use metadata-based routing - trust the backend's component field
  const messageComponent = getMessageComponent(message.metadata);
  
  // Skip messages that are specifically routed to other components
  if (!isUser && messageComponent !== 'chat') {
    return null;
  }
  
  // Check if we need to render a "FINAL ANSWER" divider before this message
  // This handles the case where the backend doesn't send a separator for final answers
  const shouldShowFinalAnswerDivider = isFinal && (!previousMessage || 
    (previousMessage.metadata?.step_type !== 'final_answer' && 
     previousMessage.metadata?.message_type !== 'separator'));
  
  if (shouldShowFinalAnswerDivider) {
    return (
      <>
        <div className="ds-step-separator my-4">
          <div className="ds-step-line" />
          <span className="ds-step-label text-[var(--ds-terminal-dim)] text-xs font-mono">
            {AGENT_SYMBOLS.FINAL_ANSWER} FINAL ANSWER
          </span>
          <div className="ds-step-line" />
        </div>
        <MessageItemContent message={message} />
      </>
    );
  }
  
  // Skip duplicate error messages that should only appear in code editor
  if (message.content.includes('Error in code parsing') || 
      message.content.includes('Executing parsed code')) {
    return null;
  }
  
  // Handle planning header messages (badges)
  if (message.metadata?.message_type === 'planning_header') {
    const planningType = message.metadata.planning_type || 'initial';
    const badgeText = planningType === 'initial' 
      ? `${AGENT_SYMBOLS.PLANNING} (Initial Plan)` 
      : `${AGENT_SYMBOLS.PLANNING} (Updated Plan)`;
    const headerStatus = message.metadata.agent_status || (planningType === 'initial' ? 'initial_planning' : 'update_planning');
    const headerConfig = getStatusDisplay(headerStatus, false); // Headers are not animated
    
    console.log('[AgentChat] Rendering planning badge:', {
      planningType,
      badgeText,
      headerStatus,
      metadata: message.metadata
    });
    
    return (
      <DSAgentMessageCard type="planning" state="idle">
        <div className="ds-planning-header">
          <DSAgentStateBadge 
            state={headerConfig.agentState} 
            text={badgeText}
            showIcon={false}  // Don't show default icon, we have the Yin Yang symbol
            isAnimated={false}
          />
        </div>
      </DSAgentMessageCard>
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

  // Handle separator messages - render them as TUI-style dividers
  if (message.metadata?.message_type === 'separator') {
    const stepType = message.metadata?.step_type;
    let label = '';
    
    if (stepType === 'planning') {
      label = `${AGENT_SYMBOLS.PLANNING} Planning`;
    } else if (stepType === 'action') {
      label = 'Actions';
    } else if (stepType === 'final_answer') {
      label = `${AGENT_SYMBOLS.FINAL_ANSWER} Final Answer`;
    }
    
    return (
      <div className="ds-step-separator my-4">
        <div className="ds-step-line" />
        {label && (
          <span className="ds-step-label text-[var(--ds-terminal-dim)] text-xs font-mono">
            {label}
          </span>
        )}
        <div className="ds-step-line" />
      </div>
    );
  }

  // Skip empty content messages (except planning_header, tool_call, action_thought, and streaming messages)
  if (!message.content?.trim() && 
      message.metadata?.message_type !== 'planning_header' &&
      message.metadata?.message_type !== 'tool_call' &&
      message.metadata?.message_type !== 'action_thought' &&
      !isFinal &&
      !isStreaming) {
    console.log('[AgentChat] Filtering out empty message:', {
      message_type: message.metadata?.message_type,
      content: message.content,
      streaming: isStreaming
    });
    return null;
  }

  return <MessageItemContent message={message} />;
}

// Separate component for message content to allow reuse
function MessageItemContent({ message }: { message: DSAgentRunMessage }) {
  const isUser = message.role === 'user';
  const isThinking = isThinkingMessage(message.metadata) || isPlanningStep(message.metadata);
  const isPlanning = isPlanningStep(message.metadata);
  const isActionThought = isActionStepThought(message.metadata, message.content);
  const isFinal = isFinalAnswer(message.metadata, message.content);
  const isStreaming = message.metadata?.streaming === true;
  const isActive = message.metadata?.is_active === true;
  const toolName = getToolName(message.metadata);
  const finalAnswerContent = isFinal ? extractFinalAnswerContent(message.content) : null;
  
  // Determine card type and state
  let cardType: 'user' | 'planning' | 'action' | 'final' | 'system' = 'system';
  let cardState: 'idle' | 'active' | 'streaming' = 'idle';
  let agentState: AgentState | undefined;

  // Get detailed status from backend metadata
  const detailedStatus = message.metadata ? mapBackendToFrontendStatus(message.metadata) : 'standby';
  const statusConfig = getStatusDisplay(detailedStatus, isStreaming || isActive);

  if (isUser) {
    cardType = 'user';
  } else if (isFinal) {
    cardType = 'final';
    agentState = statusConfig.agentState;
  } else if (isPlanning) {
    cardType = 'planning';
    agentState = statusConfig.agentState;
  } else if (isActionThought) {
    cardType = 'action';
    agentState = statusConfig.agentState;
  }

  if (isStreaming && !isActionThought) {
    cardState = 'streaming';
  } else if ((isThinking || isPlanning || isActive) && !isActionThought) {
    cardState = 'active';
  }
  
  return (
    <DSAgentMessageCard type={cardType} state={cardState} data-role={isUser ? 'user' : 'agent'}>
      {/* User/Agent indicator */}
      <div className="ds-message-header">
        <span className="ds-message-role">
          {isUser ? '$ user>' : '▶ agent>'}
        </span>
        
        {/* State badges with dynamic animations */}
        {agentState && !isUser && (
          <DSAgentStateBadge 
            state={agentState} 
            text={isActionThought ? 'Thinking' : statusConfig.text}
            isAnimated={false}
            showSpinner={false}
          />
        )}
        
        {/* Tool badge */}
        {toolName && (
          <DSAgentToolBadge 
            toolName={toolName}
            status={isStreaming ? 'active' : 'completed'}
            stepNumber={message.step_number}
            isCodeAction={toolName === 'python_interpreter'}
          />
        )}
        
        {/* Timestamp */}
        {message.timestamp && (
          <span className="ds-message-timestamp">
            [{new Date(message.timestamp).toLocaleTimeString('en-US', { 
              hour12: false, 
              hour: '2-digit', 
              minute: '2-digit', 
              second: '2-digit' 
            })}]
          </span>
        )}
      </div>

      {/* Message content */}
      <div className="ds-message-content">
        {/* Tool call handling - skip rendering badge here as it's already in header */}
        {message.metadata?.message_type === 'tool_call' ? (
          null  // Badge is already displayed in the header
        ) : message.metadata?.message_type === 'action_thought' || isActionThought ? (
          // Action thought with truncated display
          <ActionThoughtCard
            content={message.content || ""}
            stepNumber={message.step_number}
            metadata={message.metadata}
            className="w-full"
          />
        ) : isFinal ? (
          // Final answer handling
          message.metadata?.has_structured_data ? (
            <FinalAnswerDisplay 
              content={message.content || ""} 
              metadata={message.metadata}
              className="ds-final-answer" 
            />
          ) : finalAnswerContent ? (
            <FinalAnswer content={finalAnswerContent} />
          ) : (
            <FinalAnswer content="Processing final answer..." />
          )
        ) : isStreaming && !isActionThought ? (
          // Streaming text with appropriate profile (but not for action thoughts)
          <DSAgentStreamingText
            text={message.content || ''}
            isStreaming={true}
            showCursor={true}
            profile={isPlanning ? 'planning' : 'default'}
          />
        ) : isUser ? (
          // User message
          <div className="ds-user-message">
            <pre className="ds-message-text">{message.content}</pre>
          </div>
        ) : (
          // Regular agent message with markdown
          <div className="ds-agent-message">
            <Markdown>{message.content || ''}</Markdown>
          </div>
        )}
      </div>
    </DSAgentMessageCard>
  );
}