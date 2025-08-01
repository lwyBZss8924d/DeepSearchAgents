"use client";

import { useState } from "react";
import { 
  DSAgentMessageCard,
  DSAgentStateBadge,
  DSAgentStreamingText
} from "@/components/ds";

interface ActionThoughtCardProps {
  content: string;
  stepNumber?: number;
  className?: string;
  metadata?: Record<string, unknown>;
}

export default function ActionThoughtCard({ 
  content, 
  stepNumber, 
  className = "",
  metadata
}: ActionThoughtCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Use thoughts_content from metadata if available, otherwise truncate
  const truncatedContent = metadata?.thoughts_content || content.substring(0, 60);
  const fullContent = content;
  const isStreaming = metadata?.streaming === true;
  
  // Terminal-style display
  const collapsedDisplay = `Thinking🤔...${truncatedContent}...and Action Running[⚡]...`;
  
  return (
    <DSAgentMessageCard 
      type="action" 
      state={isStreaming ? "streaming" : "idle"}
      className={className}
    >
      {/* Header with expand/collapse */}
      <div 
        className="ds-action-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <DSAgentStateBadge 
          state="thinking" 
          text={stepNumber ? `Step ${stepNumber} Thinking` : 'Agent Thinking'}
          showSpinner={isStreaming}
        />
        <button 
          className="ds-expand-toggle"
          aria-label={isExpanded ? "Collapse" : "Expand"}
        >
          {isExpanded ? '[-]' : '[+]'}
        </button>
      </div>
      
      {/* Content */}
      <div className="ds-action-content">
        {isExpanded ? (
          <div className="ds-action-full">
            <DSAgentStreamingText
              text={fullContent}
              isStreaming={isStreaming}
              showCursor={isStreaming}
              profile="thinking"
            />
          </div>
        ) : (
          <div className="ds-action-collapsed">
            <DSAgentStreamingText
              text={collapsedDisplay}
              isStreaming={isStreaming}
              showCursor={false}
            />
          </div>
        )}
      </div>
    </DSAgentMessageCard>
  );
}