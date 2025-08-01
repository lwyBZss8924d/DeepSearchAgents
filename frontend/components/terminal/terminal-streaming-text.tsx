"use client"

import React from 'react'
import { cn } from '@/lib/utils'

interface TerminalStreamingTextProps {
  children: React.ReactNode
  isStreaming?: boolean
  className?: string
}

export function TerminalStreamingText({ 
  children, 
  isStreaming = false,
  className 
}: TerminalStreamingTextProps) {
  return (
    <div className={cn(
      isStreaming && "streaming-text",
      className
    )}>
      {children}
    </div>
  )
}