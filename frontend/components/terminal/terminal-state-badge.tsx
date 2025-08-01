"use client"

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

export type AgentState = 'planning' | 'thinking' | 'coding' | 'running' | 'final' | 'error'

interface TerminalStateBadgeProps {
  state: AgentState
  text?: string
  showSpinner?: boolean
  className?: string
}

const stateTexts: Record<AgentState, string> = {
  planning: 'Planning...',
  thinking: 'Thinking...',
  coding: 'Coding...',
  running: 'Actions Running...',
  final: 'Writing...',
  error: 'Error'
}

export function TerminalStateBadge({ 
  state, 
  text,
  showSpinner = false,
  className 
}: TerminalStateBadgeProps) {
  const displayText = text || stateTexts[state]
  const shouldShowSpinner = showSpinner || ['planning', 'thinking', 'coding', 'running'].includes(state)

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.15 }}
      className={cn(
        "agent-state-badge",
        state,
        className
      )}
    >
      {shouldShowSpinner && <span className="agent-spinner" />}
      {displayText}
    </motion.div>
  )
}