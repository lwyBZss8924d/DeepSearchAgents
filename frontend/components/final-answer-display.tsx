"use client";

import { useState, useEffect } from "react";
import Markdown from "@/components/markdown";
import { 
  DSCard,
  DSCardHeader,
  DSCardTitle,
  DSCardContent,
  DSCardFooter,
  DSTerminalCard 
} from "@/components/ds";
import { CheckCircle2, Link2 } from "lucide-react";

interface FinalAnswerDisplayProps {
  content: string;
  metadata?: Record<string, unknown>;  // Metadata from backend with structured data
  className?: string;
}

export default function FinalAnswerDisplayV2({ content, metadata, className = "" }: FinalAnswerDisplayProps) {
  const [title, setTitle] = useState<string>("Final Answer");
  const [answerContent, setAnswerContent] = useState<string>("");
  const [sources, setSources] = useState<string[]>([]);
  
  useEffect(() => {
    console.log("[FinalAnswerDisplay] Component mounted/updated");
    console.log("[FinalAnswerDisplay] Props received:", {
      content: content?.substring(0, 100) + "...",
      contentLength: content?.length || 0,
      contentEmpty: !content || content === "",
      metadata,
      hasStructuredData: metadata?.has_structured_data,
      answerFormat: metadata?.answer_format,
      metadataKeys: metadata ? Object.keys(metadata) : []
    });
    
    // Parse structured data from metadata if available
    if (metadata?.has_structured_data && metadata?.answer_title) {
      setTitle(metadata.answer_title as string);
    } else {
      setTitle("Final Answer");
    }
    
    // Extract content and sources
    if (metadata?.answer_format === "structured") {
      // If structured, use the content directly
      setAnswerContent(content);
      
      // Extract sources from metadata if available
      if (metadata?.sources && Array.isArray(metadata.sources)) {
        setSources(metadata.sources as string[]);
      }
    } else {
      // Otherwise parse the content
      const lines = content.split('\n');
      const titleMatch = lines[0]?.match(/^#+\s*(.+)/);
      
      if (titleMatch) {
        setTitle(titleMatch[1]);
        setAnswerContent(lines.slice(1).join('\n').trim());
      } else {
        setAnswerContent(content);
      }
      
      // Extract sources from content
      const sourceSection = content.match(/(?:Sources?|References?):\s*\n([\s\S]*?)(?:\n\n|$)/i);
      if (sourceSection) {
        const sourceList = sourceSection[1]
          .split('\n')
          .filter(line => line.trim())
          .map(line => line.replace(/^[-*]\s*/, '').trim());
        setSources(sourceList);
      }
    }
  }, [content, metadata]);

  const renderSources = () => {
    if (sources.length === 0) return null;
    
    return (
      <DSCardFooter className="flex flex-col items-start gap-2">
        <div className="text-sm font-mono text-[var(--ds-terminal-bright)] flex items-center gap-2">
          <Link2 size={14} />
          Sources
        </div>
        <ul className="text-xs space-y-1 w-full">
          {sources.map((source, index) => (
            <li key={index} className="text-[var(--ds-terminal-dim)] font-mono">
              [{index + 1}] {source}
            </li>
          ))}
        </ul>
      </DSCardFooter>
    );
  };

  // Use terminal card for enhanced visual style
  if (metadata?.use_terminal_style) {
    return (
      <DSTerminalCard
        title={title}
        className={className}
      >
        <Markdown>{answerContent}</Markdown>
        {renderSources()}
      </DSTerminalCard>
    );
  }

  // Default card style
  return (
    <DSCard
      variant="elevated"
      border="single"
      className={className}
    >
      <DSCardHeader>
        <DSCardTitle icon={<CheckCircle2 className="text-[var(--ds-agent-final)]" size={20} />}>
          {title}
        </DSCardTitle>
      </DSCardHeader>
      
      <DSCardContent>
        <Markdown>{answerContent}</Markdown>
      </DSCardContent>
      
      {renderSources()}
    </DSCard>
  );
}

// Export a wrapper component that maintains compatibility
export function FinalAnswerWrapper(props: FinalAnswerDisplayProps) {
  // If children contains the old final-answer-display, replace with v2
  return <FinalAnswerDisplayV2 {...props} />;
}