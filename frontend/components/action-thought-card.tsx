"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { ChevronDownIcon, ChevronUpIcon, TerminalIconComponent } from "@/components/terminal-icons";

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
  const [isExpanded, setIsExpanded] = useState(true);
  
  // Use thoughts_content from metadata if available, otherwise truncate
  const truncatedContent = metadata?.thoughts_content || content.substring(0, 60);
  const displayContent = `Thinking🤔...${truncatedContent}...and Action Running[`;
  
  return (
    <Card className={`bg-purple-50/10 border-purple-500/20 ${className}`}>
      <div 
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-purple-50/5 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <span className="text-purple-500 font-mono">[🤔]</span>
          <span className="text-sm font-medium text-purple-600">
            {stepNumber ? `Step ${stepNumber} Thinking` : 'Agent Thinking'}
          </span>
        </div>
        <button className="text-purple-500 hover:text-purple-600">
          {isExpanded ? <ChevronUpIcon className="h-4 w-4" /> : <ChevronDownIcon className="h-4 w-4" />}
        </button>
      </div>
      
      {isExpanded && (
        <CardContent className="pt-0 pb-3">
          <div className="text-sm text-muted-foreground">
            <p className="whitespace-pre-wrap break-words flex items-center gap-1">
              {displayContent}
              <TerminalIconComponent className="h-4 w-4 inline-block" />
              ]...
            </p>
          </div>
        </CardContent>
      )}
    </Card>
  );
}