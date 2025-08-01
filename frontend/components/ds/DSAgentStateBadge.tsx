"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { DSAgentASCIISpinner } from './DSAgentASCIISpinner'

export type AgentState = 'planning' | 'thinking' | 'coding' | 'running' | 'final' | 'error'

interface DSAgentStateBadgeProps {
  state: AgentState
  text?: string
  showIcon?: boolean
  showSpinner?: boolean
  className?: string
}

// State icons following the design specification
const stateIcons: Record<AgentState, string> = {
  planning: '◆',
  thinking: '◊',
  coding: '▶',
  running: '■',
  final: '✓',
  error: '✗'
}

// Default state text
const stateTexts: Record<AgentState, string> = {
  planning: 'Planning...',
  thinking: 'Thinking...',
  coding: 'Coding...',
  running: 'Actions Running...',
  final: 'Writing...',
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
  className 
}: DSAgentStateBadgeProps) {
  const displayText = text || stateTexts[state]
  const shouldShowSpinner = showSpinner || ['planning', 'thinking', 'coding', 'running'].includes(state)
  
  return (
    <span
      is-="badge"
      agent-badge-="state"
      agent-state-={state}
      className={cn(
        'ds-state-badge',
        `agent-${state}`,
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
      {showIcon && (
        <span className="ds-state-icon" aria-hidden="true">
          {stateIcons[state]}
        </span>
      )}
      <span className="ds-state-text">{displayText}</span>
    </span>
  )
}