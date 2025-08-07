"use client"

import React, { useState } from 'react'
import { cn } from '@/lib/utils'

interface DSAgentToolBadgeProps {
  toolName: string
  status?: 'pending' | 'active' | 'completed' | 'error'
  expandable?: boolean
  onClick?: () => void
  metadata?: Record<string, unknown>
  className?: string
  stepNumber?: number  // For Bagua trigram mapping
  isCodeAction?: boolean  // Whether this is a code action
}

// Tool display name mappings for WebTUI (updated specifications)
const toolDisplayNames: Record<string, string> = {
  python_interpreter: 'Code Actions',
  final_answer: 'Final Answer',
  search: 'WebSearch',
  search_links: 'WebSearch',
  search_fast: 'Quick-WebSearch',
  search_web: 'WebSearch',
  readurl: 'Read-WebPage',
  read_url: 'Read-WebPage',
  chunk: 'Chunk-InContext',
  chunk_text: 'Chunk-InContext',
  embed: 'Embeddings',
  embed_text: 'Embeddings',
  embed_texts: 'Embeddings',
  rerank: 'Reranker',
  rerank_texts: 'Reranker',
  wolfram: 'Wolfram',
  wolfram_alpha: 'Wolfram',
  github_repo_qa: 'Github',
  xcom_deep_qa: 'x.com',
  academic_retrieval: 'Academic-Research',
  default: 'Tools'
}

// Tool category mappings for color theming
const toolCategories: Record<string, string> = {
  // Code/Programming Tools
  python_interpreter: 'code',
  
  // Search/Web Tools
  search: 'search',
  search_links: 'search',
  search_fast: 'search',
  search_web: 'search',
  readurl: 'search',
  read_url: 'search',
  
  // Data Processing Tools
  chunk: 'data',
  chunk_text: 'data',
  embed: 'data',
  embed_text: 'data',
  embed_texts: 'data',
  rerank: 'data',
  rerank_texts: 'data',
  
  // External APIs
  wolfram: 'external',
  wolfram_alpha: 'external',
  github_repo_qa: 'external',
  xcom_deep_qa: 'external',
  
  // Research Tools
  academic_retrieval: 'research',
  
  // Final Answer
  final_answer: 'final',
  
  // Default
  default: 'default'
}

// Import Bagua utilities
import { getBaguaTrigram, AGENT_SYMBOLS } from '@/utils/bagua-symbols'

/**
 * DSAgentToolBadge - WebTUI-based tool execution badge
 * 
 * Displays tool name with icon and optional metadata
 * Uses WebTUI attribute is-="badge" and custom agent-badge-="tool"
 */
export function DSAgentToolBadge({ 
  toolName,
  status = 'pending',
  expandable = false,
  onClick,
  metadata,
  className,
  stepNumber,
  isCodeAction = false
}: DSAgentToolBadgeProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  // Debug logging
  if (typeof window !== 'undefined' && toolName.includes('~~')) {
    console.log('[DSAgentToolBadge] Raw toolName with strikethrough:', toolName);
  }
  
  // Clean and transform the tool name
  // The backend is sending something like "~~✓~~ ~~💻~~python_interpreter~~"
  // We need to extract just the actual tool name
  
  // Extract the actual tool name from potential patterns:
  // Pattern 1: "~~icon~~ ~~icon~~tool_name~~" 
  // Pattern 2: "icon tool_name"
  // Pattern 3: "tool_name"
  
  let cleaned = toolName;
  
  // If it contains ~~, extract the last part between ~~ marks or after them
  if (cleaned.includes('~~')) {
    // Split by ~~ and get the last non-empty part that looks like a tool name
    const parts = cleaned.split('~~').filter(p => p.trim());
    // The actual tool name is usually the last part that contains letters/underscores
    cleaned = parts.find(p => /^[a-z_]+$/i.test(p.trim())) || parts[parts.length - 1] || toolName;
  }
  
  // Remove any remaining formatting and icons
  cleaned = cleaned.replace(/~~/g, ''); // Remove any remaining strikethrough marks
  cleaned = cleaned.replace(/[✓⚡✗×○]/g, ''); // Remove status icons (removed ◉●)
  cleaned = cleaned.replace(/[💻📝🔍📄✂️🔢📊🧮🔧🌐]/g, ''); // Remove emoji
  cleaned = cleaned.replace(/[▶◆◎▼■▓◈↕∑⊙×◊]/g, ''); // Remove ASCII icons (removed ●)
  cleaned = cleaned.trim();
  
  const cleanedName = cleaned.toLowerCase()
  
  // Get display name
  const displayName = toolDisplayNames[cleanedName] || 
                     cleanedName.charAt(0).toUpperCase() + cleanedName.slice(1).replace(/_/g, '-')
  
  // Get tool category for color theming
  const toolCategory = toolCategories[cleanedName] || 'default'
  
  // Determine if this is a Python code action
  const isPythonInterpreter = cleanedName === 'python_interpreter'
  const isPythonAction = isPythonInterpreter || isCodeAction
  
  // Build the badge display content with colored spans
  let badgeContent: React.ReactNode
  if (cleanedName === 'final_answer') {
    // Final answer with Mahjong Green Dragon
    if (stepNumber) {
      const trigram = getBaguaTrigram(stepNumber)
      badgeContent = (
        <>
          <span className="ds-badge-trigram">{trigram}</span>
          {' '}
          <span className="ds-badge-final-symbol">{AGENT_SYMBOLS.FINAL_ANSWER}</span>
          {' '}
          <span className="ds-badge-tool-name" data-category={toolCategory}>({displayName})</span>
        </>
      )
    } else {
      badgeContent = (
        <>
          <span className="ds-badge-final-symbol">{AGENT_SYMBOLS.FINAL_ANSWER}</span>
          {' '}
          <span className="ds-badge-tool-name" data-category={toolCategory}>({displayName})</span>
        </>
      )
    }
  } else if (stepNumber) {
    // Action step with Bagua trigram
    const trigram = getBaguaTrigram(stepNumber)
    if (isPythonInterpreter) {
      // Python interpreter itself - no command symbol
      badgeContent = (
        <>
          <span className="ds-badge-trigram">{trigram}</span>
          {' '}
          <span className="ds-badge-code-symbol">{AGENT_SYMBOLS.CODE_ACTION}</span>
          {' '}
          <span className="ds-badge-tool-name" data-category={toolCategory}>({displayName})</span>
        </>
      )
    } else if (isPythonAction) {
      // Other tools called from Python code
      badgeContent = (
        <>
          <span className="ds-badge-trigram">{trigram}</span>
          {' '}
          <span className="ds-badge-code-symbol">{AGENT_SYMBOLS.CODE_ACTION}</span>
          {' '}
          <span className="ds-badge-command-symbol">{AGENT_SYMBOLS.COMMAND}</span>
          <span className="ds-badge-tool-name" data-category={toolCategory}>({displayName})</span>
        </>
      )
    } else {
      // Regular tool calls
      badgeContent = (
        <>
          <span className="ds-badge-trigram">{trigram}</span>
          {' '}
          <span className="ds-badge-command-symbol">{AGENT_SYMBOLS.COMMAND}</span>
          <span className="ds-badge-tool-name" data-category={toolCategory}>({displayName})</span>
        </>
      )
    }
  } else {
    // Default format for tools without step number
    if (isPythonInterpreter) {
      badgeContent = (
        <>
          <span className="ds-badge-code-symbol">{AGENT_SYMBOLS.CODE_ACTION}</span>
          {' '}
          <span className="ds-badge-tool-name" data-category={toolCategory}>({displayName})</span>
        </>
      )
    } else {
      badgeContent = (
        <>
          <span className="ds-badge-command-symbol">{AGENT_SYMBOLS.COMMAND}</span>
          <span className="ds-badge-tool-name" data-category={toolCategory}>({displayName})</span>
        </>
      )
    }
  }
  
  const isClickable = expandable || onClick
  
  const handleClick = () => {
    if (expandable) {
      setIsExpanded(!isExpanded)
    }
    onClick?.()
  }
  
  const statusIcon = {
    pending: '○',  // Empty circle
    active: '',    // No icon for active (removed ◉)
    completed: '', // No icon for completed (removed ●)
    error: '×'     // X mark
  }
  
  // Minimal styling without glamour effects
  const statusClasses = cn({
    // Simple status-based classes without animations
    'ds-tool-badge-active': status === 'active',
    'ds-tool-badge-completed': status === 'completed',
    'ds-tool-badge-error': status === 'error',
    'ds-tool-badge-pending': status === 'pending'
  })
  
  return (
    <div className="ds-tool-badge-container">
      <button
        is-="badge"
        agent-badge-="tool"
        tool-status-={status}
        data-tool-category={toolCategory}
        onClick={isClickable ? handleClick : undefined}
        className={cn(
          'ds-tool-badge',
          isClickable && 'ds-tool-badge-clickable',
          statusClasses,
          className
        )}
        type="button"
        disabled={!isClickable}
      >
        
        {statusIcon[status] && (
          <span className="ds-tool-status-icon" aria-hidden="true">
            {statusIcon[status]}
          </span>
        )}
        <span className="ds-tool-badge-text">{badgeContent}</span>
        {expandable && (
          <span className="ds-tool-expand-icon" aria-hidden="true">
            {isExpanded ? '▼' : '▶'}
          </span>
        )}
      </button>
      
      {isExpanded && metadata && (
        <div
          box-="single"
          className="ds-tool-metadata"
          aria-label="Tool execution details"
        >
          {(metadata.duration as number | undefined) && (
            <div className="ds-tool-metadata-item">
              <span className="ds-tool-metadata-label">Duration:</span>
              <span className="ds-tool-metadata-value">{String(metadata.duration)}s</span>
            </div>
          )}
          {(metadata.tokenCount as number | undefined) && (
            <div className="ds-tool-metadata-item">
              <span className="ds-tool-metadata-label">Tokens:</span>
              <span className="ds-tool-metadata-value">{String(metadata.tokenCount)}</span>
            </div>
          )}
          {(metadata.resultPreview as string | undefined) && (
            <div className="ds-tool-metadata-item">
              <span className="ds-tool-metadata-label">Results:</span>
              <span className="ds-tool-metadata-value">{String(metadata.resultPreview)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}