"use client"

import React from 'react'
import { cn } from '@/lib/utils'

export type AgentCardType = 'planning' | 'action' | 'observation' | 'final' | 'user' | 'system'
export type AgentCardState = 'idle' | 'active' | 'streaming'

interface DSAgentMessageCardProps extends React.HTMLAttributes<HTMLDivElement> {
  type?: AgentCardType
  state?: AgentCardState
  children: React.ReactNode
  className?: string
}

/**
 * DSAgentMessageCard - WebTUI-based message card component
 * 
 * Uses WebTUI attributes for terminal-style rendering:
 * - box-="single" for border styling
 * - agent-card-={type} for message type styling
 * - agent-state-={state} for state-based animations
 */
export function DSAgentMessageCard({ 
  type = 'system',
  state = 'idle',
  children,
  className,
  ...props 
}: DSAgentMessageCardProps) {
  return (
    <div 
      box-="single"
      agent-card-={type}
      agent-state-={state}
      className={cn(
        'ds-message-card',
        'terminal-transition',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}