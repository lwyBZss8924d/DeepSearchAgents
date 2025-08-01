"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeRaw from "rehype-raw";
import rehypeMathJax from "rehype-mathjax";
import rehypeKatex from "rehype-katex";
import { DSAgentCodeBlock } from "@/components/ds";

import "katex/dist/katex.min.css";

interface MarkdownProps {
  children: string | null | undefined;
  className?: string;
}

/**
 * Markdown-v2 - Terminal-style markdown renderer using DS components
 * 
 * Uses DSAgentCodeBlock for all code rendering to maintain
 * consistent terminal aesthetic across the application
 */
export default function Markdown({ children, className = "" }: MarkdownProps) {
  return (
    <div className={`markdown-body ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeRaw, rehypeMathJax, rehypeKatex]}
        components={{
          // Terminal-style links
          a: ({ ...props }) => (
            <a 
              target="_blank" 
              rel="noopener noreferrer" 
              className="ds-markdown-link"
              {...props} 
            />
          ),
          
          // Terminal-style code blocks using DSAgentCodeBlock
          code: ({ className, children, ...props }) => {
            // Check if this is inline code or a code block
            const isInline = !className?.includes('language-');
            
            if (isInline) {
              return (
                <code className="ds-markdown-inline-code" {...props}>
                  {children}
                </code>
              );
            }
            
            // Extract language from className (format: language-python)
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : 'text';
            
            // Convert children to string
            const codeString = String(children).replace(/\n$/, '');
            
            return (
              <DSAgentCodeBlock
                code={codeString}
                language={language}
                lineNumbers={true}
                className="ds-markdown-code-block"
              />
            );
          },
          
          // Terminal-style blockquotes
          blockquote: ({ children, ...props }) => (
            <blockquote className="ds-markdown-blockquote" {...props}>
              <span className="ds-quote-marker">│</span>
              {children}
            </blockquote>
          ),
          
          // Terminal-style lists
          ul: ({ children, ...props }) => (
            <ul className="ds-markdown-list" {...props}>
              {children}
            </ul>
          ),
          ol: ({ children, ...props }) => (
            <ol className="ds-markdown-list ds-markdown-list-ordered" {...props}>
              {children}
            </ol>
          ),
          li: ({ children, ...props }) => (
            <li className="ds-markdown-list-item" {...props}>
              <span className="ds-list-marker">▸</span> {children}
            </li>
          ),
          
          // Terminal-style headings
          h1: ({ children, ...props }) => (
            <h1 className="ds-markdown-h1" {...props}>
              # {children}
            </h1>
          ),
          h2: ({ children, ...props }) => (
            <h2 className="ds-markdown-h2" {...props}>
              ## {children}
            </h2>
          ),
          h3: ({ children, ...props }) => (
            <h3 className="ds-markdown-h3" {...props}>
              ### {children}
            </h3>
          ),
          
          // Terminal-style emphasis
          em: ({ children, ...props }) => (
            <em className="ds-markdown-emphasis" {...props}>
              _{children}_
            </em>
          ),
          strong: ({ children, ...props }) => (
            <strong className="ds-markdown-strong" {...props}>
              *{children}*
            </strong>
          ),
        }}
      >
        {children || ""}
      </ReactMarkdown>
    </div>
  );
}