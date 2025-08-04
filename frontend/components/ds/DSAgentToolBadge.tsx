"use client"

import React, { useState } from 'react'
import { cn } from '@/lib/utils'

interface DSAgentToolBadgeProps {
  toolName: string
  icon?: string | React.ReactNode
  status?: 'pending' | 'active' | 'completed' | 'error'
  expandable?: boolean
  onClick?: () => void
  metadata?: Record<string, unknown>
  className?: string
}

// Default tool icons
const toolIcons: Record<string, string> = {
  // Original names from tool-call-badge.tsx
  python_interpreter: '💻',
  search: '🔍',
  readurl: '📄',
  chunk: '✂️',
  embed: '🔢',
  rerank: '📊',
  wolfram: '🧮',
  final_answer: '📝',
  // Alternative names
  search_web: '🔍',
  read_url: '📄',
  chunk_text: '✂️',
  embed_text: '🔢',
  wolfram_alpha: '🧮',
  default: '🔧'
}

/**
 * DSAgentToolBadge - WebTUI-based tool execution badge
 * 
 * Displays tool name with icon and optional metadata
 * Uses WebTUI attribute is-="badge" and custom agent-badge-="tool"
 */
export function DSAgentToolBadge({ 
  toolName,
  icon,
  status = 'pending',
  expandable = false,
  onClick,
  metadata,
  className 
}: DSAgentToolBadgeProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  const displayIcon = icon || toolIcons[toolName] || toolIcons.default
  const isClickable = expandable || onClick
  
  const handleClick = () => {
    if (expandable) {
      setIsExpanded(!isExpanded)
    }
    onClick?.()
  }
  
  const statusIcon = {
    pending: '',
    active: '⚡',
    completed: '✓',
    error: '✗'
  }
  
  // Determine glamour effects based on status
  const glamourClasses = cn({
    // Active tools get animated glow
    'glamour-glow glamour-hover': status === 'active',
    'coding-glow': status === 'active' && toolName === 'python_interpreter',
    'planning-glow': status === 'active' && (toolName === 'search' || toolName === 'search_web'),
    'running-glow': status === 'active' && toolName === 'wolfram',
    
    // Completed tools get subtle gradient
    'glamour-gradient-text': status === 'completed',
    
    // Error state gets attention
    'glamour-text-glow': status === 'error',
    
    // Spring animation on mount
    'glamour-spring': true
  })
  
  return (
    <div className="ds-tool-badge-container">
      <button
        is-="badge"
        agent-badge-="tool"
        tool-status-={status}
        onClick={isClickable ? handleClick : undefined}
        className={cn(
          'ds-tool-badge',
          isClickable && 'ds-tool-badge-clickable',
          'particle-container',
          glamourClasses,
          className
        )}
        type="button"
        disabled={!isClickable}
      >
        {/* Add animated particles for active status */}
        {status === 'active' && (
          <>
            <div className="particle" style={{ left: '20%', animationDelay: '0s' }} />
            <div className="particle" style={{ left: '80%', animationDelay: '0.3s' }} />
          </>
        )}
        
        {status !== 'pending' && (
          <span className="ds-tool-status-icon" aria-hidden="true">
            {statusIcon[status]}
          </span>
        )}
        <span className="ds-tool-icon" aria-hidden="true">
          {displayIcon}
        </span>
        <span className="ds-tool-name">{toolName}</span>
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