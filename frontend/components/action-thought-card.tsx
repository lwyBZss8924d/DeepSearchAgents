"use client";

import { 
  DSAgentMessageCard
} from "@/components/ds";

interface ActionThoughtCardProps {
  content: string;
  stepNumber?: number;
  className?: string;
  metadata?: Record<string, unknown>;
}

export default function ActionThoughtCard({ 
  content, 
  className = "",
  metadata
}: ActionThoughtCardProps) {
  // Use thoughts_content from metadata if available, otherwise truncate
  // Backend now includes ellipsis in thoughts_content when truncated
  const truncatedContent = metadata?.thoughts_content || 
    (content && content.length > 120 ? content.substring(0, 120) + "..." : content);
  
  // Terminal-style display
  const finalContent = String(truncatedContent || "");
  
  return (
    <DSAgentMessageCard 
      type="action" 
      state="idle"
      className={className}
    >
      {/* Content */}
      <div className="ds-action-content">
        <div className="ds-action-full">
          <span className="ds-action-text">{finalContent.startsWith('Thought:') ? finalContent : `Thought: ${finalContent}`}</span>
        </div>
      </div>
    </DSAgentMessageCard>
  );
}