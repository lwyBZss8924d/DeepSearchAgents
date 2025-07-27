"use client";

import { useState, useEffect } from "react";
import Markdown from "@/components/markdown";
import { extractFinalAnswerContent, extractFinalAnswerMetadata } from "@/utils/extractors";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CheckCircle2, Link2, FileText } from "lucide-react";

interface FinalAnswerDisplayProps {
  content: string;
  className?: string;
}

export default function FinalAnswerDisplay({ content, className = "" }: FinalAnswerDisplayProps) {
  const [title, setTitle] = useState<string>("Final Answer");
  const [answerContent, setAnswerContent] = useState<string>("");
  const [sources, setSources] = useState<string[]>([]);
  
  useEffect(() => {
    // Extract structured content from the message
    const extractedContent = extractFinalAnswerContent(content);
    const metadata = extractFinalAnswerMetadata(content);
    
    if (extractedContent) {
      setAnswerContent(extractedContent);
    } else {
      // Fallback to raw content if extraction fails
      setAnswerContent(content);
    }
    
    if (metadata) {
      if (metadata.title) setTitle(metadata.title);
      if (metadata.sources) setSources(metadata.sources);
    }
  }, [content]);
  
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