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
 * 
 * Enhanced with glamorous gradient effects based on card type
 */
export function DSAgentMessageCard({ 
  type = 'system',
  state = 'idle',
  children,
  className,
  ...props 
}: DSAgentMessageCardProps) {
  // Determine glamour effects based on type and state
  const glamourClasses = cn({
    // Planning cards get gradient border animation
    'glamour-gradient planning-glow': type === 'planning' && state === 'active',
    'glamour-border-dance': type === 'planning' && state === 'streaming',
    
    // Action cards get coding glow
    'coding-glow glamour-hover': type === 'action' && state === 'active',
    'glamour-morph': type === 'action' && state === 'streaming',
    
    // Final answers get special treatment
    'glamour-gradient glamour-glow': type === 'final',
    'glamour-spring': type === 'final' && state === 'idle',
    
    // User messages get subtle hover effect
    'glamour-hover': type === 'user',
    
    // System messages get running glow when active
    'running-glow': type === 'system' && state === 'active'
  });

  return (
    <div 
      box-="single"
      agent-card-={type}
      agent-state-={state}
      className={cn(
        'ds-message-card',
        'terminal-transition',
        'particle-container',
        glamourClasses,
        className
      )}
      {...props}
    >
      {/* Add gradient overlay for certain types */}
      {(type === 'planning' || type === 'final') && state === 'active' && (
        <div className="absolute inset-0 opacity-10 glamour-gradient pointer-events-none" />
      )}
      
      {/* Add particles for final answers */}
      {type === 'final' && (
        <>
          <div className="particle" style={{ left: '10%', animationDelay: '0s' }} />
          <div className="particle" style={{ left: '30%', animationDelay: '0.5s' }} />
          <div className="particle" style={{ left: '50%', animationDelay: '1s' }} />
          <div className="particle" style={{ left: '70%', animationDelay: '1.5s' }} />
          <div className="particle" style={{ left: '90%', animationDelay: '2s' }} />
        </>
      )}
      
      {children}
    </div>
  )
}