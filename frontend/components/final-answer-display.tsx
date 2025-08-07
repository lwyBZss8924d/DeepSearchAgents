"use client";

import { useState, useEffect } from "react";
import Markdown from "@/components/markdown";
import { 
  DSCardFooter,
  DSTerminalCard 
} from "@/components/ds";
import { Link2 } from "lucide-react";

interface FinalAnswerDisplayProps {
  content: string;
  metadata?: Record<string, unknown>;  // Metadata from backend with structured data
  className?: string;
}

export default function FinalAnswerDisplay({ content, metadata, className = "" }: FinalAnswerDisplayProps) {
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
    
    // First check if we have structured data in metadata
    if (metadata?.has_structured_data && metadata?.answer_format === "json") {
      // Use structured data directly from metadata
      const newTitle = (metadata.answer_title as string) || "Final Answer";
      const newContent = (metadata.answer_content as string) || content;
      const newSources = (metadata.answer_sources as string[]) || [];
      
      setTitle(newTitle);
      setAnswerContent(newContent);
      setSources(newSources);
      
      console.log("[FinalAnswerDisplay] Using structured data from metadata");
      return;
    }
    
    // Extract content and sources
    if (metadata?.answer_format === "json") {
      // If JSON format, use the content directly
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
    
    // If no structured metadata, try to parse content as JSON
    if (content && content.trim().startsWith("{") && content.trim().endsWith("}")) {
      try {
        const parsed = JSON.parse(content);
        if (parsed.title) setTitle(parsed.title);
        if (parsed.content) setAnswerContent(parsed.content);
        if (parsed.sources) setSources(parsed.sources);
        console.log("[FinalAnswerDisplay] Parsed JSON content successfully");
      } catch {
        console.log("[FinalAnswerDisplay] Failed to parse JSON content, using as-is");
        // If parsing fails, the content has already been set above
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

  // Always use terminal card for consistent WebTUI style
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

