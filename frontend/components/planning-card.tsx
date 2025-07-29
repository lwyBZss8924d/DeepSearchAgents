"use client";

import { motion } from "framer-motion";
import { Calendar, RefreshCcw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";
import rehypeMathJax from "rehype-mathjax";
import rehypeKatex from "rehype-katex";

import "katex/dist/katex.min.css";

interface PlanningCardProps {
  content: string;
  planningType: "initial" | "update";
  stepNumber?: number;
  className?: string;
}

export default function PlanningCard({ 
  content, 
  planningType, 
  stepNumber, 
  className = "" 
}: PlanningCardProps) {
  const isInitial = planningType === "initial";
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`planning-card ${className}`}
    >
      {/* Planning Badge */}
      <div className="planning-header">
        <span className={`planning-badge ${
          isInitial ? "planning-badge-initial" : "planning-badge-update"
        }`}>
          {isInitial ? (
            <>
              <Calendar className="w-3 h-3 mr-1" />
              Initial Plan
            </>
          ) : (
            <>
              <RefreshCcw className="w-3 h-3 mr-1" />
              Updated Plan
            </>
          )}
        </span>
        {stepNumber && (
          <span className="planning-step-number">
            Step {stepNumber}
          </span>
        )}
      </div>
      
      {/* Planning Content with Custom Markdown Rendering */}
      <div className="planning-content-wrapper">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeHighlight, rehypeRaw, rehypeMathJax, rehypeKatex]}
          components={{
            // Custom rendering for paragraphs to avoid code block styling
            p: ({ children, ...props }) => (
              <p className="planning-paragraph" {...props}>
                {children}
              </p>
            ),
            // Lists with proper styling
            ul: ({ children, ...props }) => (
              <ul className="planning-list" {...props}>
                {children}
              </ul>
            ),
            ol: ({ children, ...props }) => (
              <ol className="planning-list planning-list-ordered" {...props}>
                {children}
              </ol>
            ),
            // Headers with planning-specific styling
            h1: ({ children, ...props }) => (
              <h1 className="planning-heading planning-h1" {...props}>
                {children}
              </h1>
            ),
            h2: ({ children, ...props }) => (
              <h2 className="planning-heading planning-h2" {...props}>
                {children}
              </h2>
            ),
            h3: ({ children, ...props }) => (
              <h3 className="planning-heading planning-h3" {...props}>
                {children}
              </h3>
            ),
            // Code blocks should still look like code
            pre: ({ children, ...props }) => (
              <pre className="planning-code-block" {...props}>
                {children}
              </pre>
            ),
            // Inline code
            code: ({ children, inline, ...props }) => (
              inline ? (
                <code className="planning-inline-code" {...props}>
                  {children}
                </code>
              ) : (
                <code {...props}>{children}</code>
              )
            ),
            // Links
            a: ({ ...props }) => (
              <a 
                target="_blank" 
                rel="noopener noreferrer" 
                className="planning-link"
                {...props} 
              />
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
      
      {/* Optional visual separator */}
      <div className="planning-separator" />
    </motion.div>
  );
}