"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";
import rehypeMathJax from "rehype-mathjax";
import rehypeKatex from "rehype-katex";
import { 
  DSAgentMessageCard,
  DSAgentStateBadge
} from "@/components/ds";

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
    <DSAgentMessageCard 
      type="planning" 
      state="idle"
      className={className}
    >
      {/* Planning Header */}
      <div className="ds-planning-header">
        <DSAgentStateBadge 
          state="planning"
          text={isInitial ? "Initial Plan" : "Updated Plan"}
          showIcon={true}
        />
        {stepNumber && (
          <span className="ds-planning-step">
            [Step {stepNumber}]
          </span>
        )}
      </div>
      
      {/* Planning Content with Terminal-style Markdown */}
      <div className="ds-planning-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeHighlight, rehypeRaw, rehypeMathJax, rehypeKatex]}
          components={{
            // Terminal-style paragraphs
            p: ({ children, ...props }) => (
              <p className="ds-planning-paragraph" {...props}>
                {children}
              </p>
            ),
            // Terminal-style lists
            ul: ({ children, ...props }) => (
              <ul className="ds-planning-list" {...props}>
                {children}
              </ul>
            ),
            ol: ({ children, ...props }) => (
              <ol className="ds-planning-list ds-planning-list-ordered" {...props}>
                {children}
              </ol>
            ),
            li: ({ children, ...props }) => (
              <li className="ds-planning-list-item" {...props}>
                <span className="ds-list-marker">▸</span> {children}
              </li>
            ),
            // Terminal-style headings
            h1: ({ children, ...props }) => (
              <h1 className="ds-planning-heading-1" {...props}>
                ═══ {children} ═══
              </h1>
            ),
            h2: ({ children, ...props }) => (
              <h2 className="ds-planning-heading-2" {...props}>
                ─── {children} ───
              </h2>
            ),
            h3: ({ children, ...props }) => (
              <h3 className="ds-planning-heading-3" {...props}>
                ▪ {children}
              </h3>
            ),
            // Terminal-style code blocks
            code: ({ className, children, ...props }: React.ComponentPropsWithoutRef<'code'>) => {
              const match = /language-(\w+)/.exec(className || '');
              const language = match ? match[1] : '';
              const isInline = !className?.includes('language-');
              
              if (!isInline) {
                return (
                  <div className="ds-planning-code-block">
                    <div className="ds-code-header">
                      <span className="ds-code-lang">[{language || 'CODE'}]</span>
                    </div>
                    <pre className="ds-code-content">
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  </div>
                );
              }
              return (
                <code className="ds-planning-inline-code" {...props}>
                  {children}
                </code>
              );
            },
            // Terminal-style emphasis
            em: ({ children, ...props }) => (
              <em className="ds-planning-emphasis" {...props}>
                _{children}_
              </em>
            ),
            strong: ({ children, ...props }) => (
              <strong className="ds-planning-strong" {...props}>
                *{children}*
              </strong>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </DSAgentMessageCard>
  );
}