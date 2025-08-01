"use client"

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface TerminalToolBadgeProps {
  toolName: string
  icon?: string
  onClick?: () => void
  className?: string
}

const toolIcons: Record<string, string> = {
  search_web: '🔍',
  search: '🔍',
  readurl: '📄',
  read_url: '📄',
  wolfram: '🧮',
  wolfram_alpha: '🧮',
  analyze_data: '📊',
  embed: '🔤',
  chunk: '📋',
  rerank: '📈',
  final_answer: '✅',
  python: '🐍',
  code: '💻'
}

export function TerminalToolBadge({ 
  toolName, 
  icon,
  onClick,
  className 
}: TerminalToolBadgeProps) {
  const displayIcon = icon || toolIcons[toolName.toLowerCase()] || '🔧'
  
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.1 }}
      className={cn(
        "tool-badge",
        onClick && "cursor-pointer",
        className
      )}
      onClick={onClick}
      whileHover={onClick ? { scale: 1.05 } : undefined}
      whileTap={onClick ? { scale: 0.95 } : undefined}
    >
      <span className="tool-icon">{displayIcon}</span>
      {toolName}
    </motion.span>
  )
}