"use client"

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface TerminalMessageCardProps {
  children: React.ReactNode
  type?: 'planning' | 'action' | 'final' | 'user' | 'system'
  isActive?: boolean
  className?: string
}

export function TerminalMessageCard({ 
  children, 
  type = 'system',
  isActive = false,
  className 
}: TerminalMessageCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "agent-message-card",
        type && `agent-message-card ${type}`,
        isActive && "active",
        className
      )}
    >
      {children}
    </motion.div>
  )
}