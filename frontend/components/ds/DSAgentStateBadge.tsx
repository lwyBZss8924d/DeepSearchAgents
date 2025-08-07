"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { DSAgentASCIISpinner } from './DSAgentASCIISpinner'

export type AgentState = 'planning' | 'thinking' | 'coding' | 'running' | 'final' | 'working' | 'error'

interface DSAgentStateBadgeProps {
  state: AgentState
  text?: string
  showIcon?: boolean
  showSpinner?: boolean
  isAnimated?: boolean  // Controls whether animations are active
  className?: string
}

// State icons following the design specification
const stateIcons: Record<AgentState, string> = {
  planning: '◆',
  thinking: '𐅡',
  coding: '▶',
  running: '■',
  final: '✓',
  working: '◊',
  error: '✗'
}

// Default state text
const stateTexts: Record<AgentState, string> = {
  planning: 'Planning...',
  thinking: 'Thinking...',
  coding: 'Coding...',
  running: 'Actions Running...',
  final: 'Writing...',
  working: 'Working...',
  error: 'Error'
}

/**
 * DSAgentStateBadge - WebTUI-based agent state badge
 * 
 * Displays agent state with icons and optional spinner animations
 * Uses WebTUI attribute is-="badge" and custom agent-badge-="state"
 */
export function DSAgentStateBadge({ 
  state, 
  text,
  showIcon = true,
  showSpinner = false,
  isAnimated,
  className 
}: DSAgentStateBadgeProps) {
  const displayText = text || stateTexts[state]
  
  // Determine if we should show spinner
  // If isAnimated is explicitly set, use it
  // Otherwise, check showSpinner or default behavior for certain states
  const shouldShowSpinner = isAnimated !== undefined 
    ? isAnimated && showSpinner !== false
    : showSpinner || ['planning', 'thinking', 'coding', 'running', 'working'].includes(state)
  
  // Show static icon when not animated or when spinner is disabled
  const shouldShowStaticIcon = showIcon && !shouldShowSpinner
  
  return (
    <span
      is-="badge"
      agent-badge-="state"
      agent-state-={state}
      agent-animated-={isAnimated ? "true" : "false"}
      className={cn(
        'ds-state-badge',
        `agent-${state}`,
        isAnimated && 'ds-state-animated',
        className
      )}
    >
      {shouldShowSpinner && (
        <DSAgentASCIISpinner 
          state={state}
          size="sm"
          className="ds-state-spinner"
          aria-label={`${displayText} spinner`}
        />
      )}
      {shouldShowStaticIcon && (
        <span className="ds-state-icon" aria-hidden="true">
          {displayText === 'Standby' ? '⚉' : stateIcons[state]}
        </span>
      )}
      <span className="ds-state-text">{displayText}</span>
    </span>
  )
}