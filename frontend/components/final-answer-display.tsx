"use client";

import { useState, useEffect } from "react";
import Markdown from "@/components/markdown";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CheckCircle2, Link2 } from "lucide-react";

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
      console.log("[FinalAnswerDisplay] Set state values:", {
        title: newTitle,
        answerContent: newContent.substring(0, 100) + "...",
        sourcesCount: newSources.length
      });
      return;
    }
    
    // If no structured metadata, try to parse content as JSON
    if (content && content.trim().startsWith("{") && content.trim().endsWith("}")) {
      try {
        const parsed = JSON.parse(content);
        if (parsed.title) setTitle(parsed.title);
        if (parsed.content) setAnswerContent(parsed.content);
        if (parsed.sources) setSources(parsed.sources);
        console.log("[FinalAnswerDisplay] Parsed JSON content successfully");
        return;
      } catch {
        console.log("[FinalAnswerDisplay] Failed to parse JSON");
      }
    }
    
    // Final fallback - use content as-is
    // Remove any "Final answer:" prefix variations
    let cleanedContent = content;
    cleanedContent = cleanedContent.replace(/^\*?\*?Final answer:?\*?\*?:?\s*/i, '');
    setAnswerContent(cleanedContent);
  }, [content, metadata]);
  
  console.log("[FinalAnswerDisplay] Rendering with state:", {
    title,
    answerContentLength: answerContent.length,
    answerContentPreview: answerContent.substring(0, 50) + "...",
    sourcesCount: sources.length,
    className
  });
  
  return (
    <Card className={`bg-green-50/10 border-green-500/20 ${className}`}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-green-600">
          <CheckCircle2 className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Main content */}
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <Markdown>{answerContent}</Markdown>
        </div>
        
        {/* Sources section if not already in content */}
        {sources.length > 0 && !answerContent.includes("## Sources") && (
          <div className="border-t pt-4 mt-4">
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
              <Link2 className="h-4 w-4" />
              Sources
            </h3>
            <ol className="space-y-1">
              {sources.map((source, index) => (
                <li key={index} className="text-sm">
                  <span className="text-muted-foreground">{index + 1}.</span>{" "}
                  <a 
                    href={source} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    {source}
                  </a>
                </li>
              ))}
            </ol>
          </div>
        )}
      </CardContent>
    </Card>
  );
}