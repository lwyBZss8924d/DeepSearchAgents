"use client"

import React, { useEffect, useState, useRef, useCallback } from 'react'
import { cn } from '@/lib/utils'

export type StreamingMode = 'instant' | 'char' | 'word' | 'line'

interface StreamingProfile {
  mode: StreamingMode
  speed: number
  smoothScroll?: boolean
  highlightNew?: boolean
}

interface DSAgentStreamingTextProps {
  text: string
  isStreaming?: boolean
  typewriterSpeed?: number
  showCursor?: boolean
  cursorChar?: string
  className?: string
  mode?: StreamingMode
  profile?: keyof typeof streamingProfiles
  onStreamComplete?: () => void
}

// Predefined streaming profiles for different content types
export const streamingProfiles: Record<string, StreamingProfile> = {
  planning: { mode: 'line', speed: 50, smoothScroll: true, highlightNew: true },
  thinking: { mode: 'word', speed: 30, smoothScroll: true },
  coding: { mode: 'char', speed: 10, smoothScroll: true },
  result: { mode: 'instant', speed: 0, smoothScroll: false },
  default: { mode: 'char', speed: 20, smoothScroll: true }
}

/**
 * DSAgentStreamingText - Enhanced WebTUI-based streaming text component
 * 
 * Supports multiple streaming modes: instant, character, word, and line
 * Includes performance optimizations and smooth scrolling
 */
export function DSAgentStreamingText({ 
  text,
  isStreaming = false,
  typewriterSpeed,
  showCursor = true,
  cursorChar = '█',
  className,
  mode = 'char',
  profile = 'default',
  onStreamComplete
}: DSAgentStreamingTextProps) {
  const [displayText, setDisplayText] = useState('')
  const [currentPosition, setCurrentPosition] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const animationFrameRef = useRef<number>(0)
  const lastUpdateRef = useRef<number>(0)
  
  // Get streaming configuration
  const config = streamingProfiles[profile]
  const streamMode = mode || config.mode
  const speed = typewriterSpeed ?? config.speed
  
  // Split text based on mode
  const getTextChunks = useCallback((text: string, mode: StreamingMode) => {
    switch (mode) {
      case 'word':
        return text.match(/\S+\s*/g) || []
      case 'line':
        return text.split('\n').map(line => line + '\n')
      case 'char':
        return text.split('')
      case 'instant':
      default:
        return [text]
    }
  }, [])
  
  const chunks = getTextChunks(text, streamMode)
  
  // Optimized streaming with requestAnimationFrame
  const streamText = useCallback(() => {
    if (currentPosition >= chunks.length || speed === 0) {
      setDisplayText(text)
      setIsComplete(true)
      onStreamComplete?.()
      return
    }
    
    const now = performance.now()
    const deltaTime = now - lastUpdateRef.current
    
    if (deltaTime >= speed) {
      const nextPosition = currentPosition + 1
      const nextText = chunks.slice(0, nextPosition).join('')
      setDisplayText(nextText)
      setCurrentPosition(nextPosition)
      lastUpdateRef.current = now
      
      if (nextPosition >= chunks.length) {
        setIsComplete(true)
        onStreamComplete?.()
        return
      }
    }
    
    animationFrameRef.current = requestAnimationFrame(streamText)
  }, [chunks, currentPosition, speed, text, onStreamComplete])
  
  // Start/stop streaming
  useEffect(() => {
    if (speed > 0 && !isComplete) {
      animationFrameRef.current = requestAnimationFrame(streamText)
      
      return () => {
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
        }
      }
    }
  }, [streamText, speed, isComplete])
  
  // Reset when text changes
  useEffect(() => {
    setDisplayText(speed > 0 ? '' : text)
    setCurrentPosition(0)
    setIsComplete(speed === 0)
    lastUpdateRef.current = performance.now()
  }, [text, speed])
  
  const isTyping = !isComplete && speed > 0
  const shouldShowCursor = showCursor && (isStreaming || isTyping)
  
  return (
    <span
      className={cn(
        'ds-streaming-text',
        isStreaming && 'ds-streaming-active',
        isTyping && 'ds-streaming-typing',
        config.highlightNew && 'ds-streaming-highlight',
        className
      )}
      agent-streaming={isStreaming ? '' : undefined}
      data-mode={streamMode}
      data-complete={isComplete ? '' : undefined}
    >
      <span className="ds-streaming-content">{displayText}</span>
      {shouldShowCursor && (
        <span 
          className="ds-streaming-cursor"
          aria-hidden="true"
        >
          {cursorChar}
        </span>
      )}
    </span>
  )
}

// Export for use in other components
export default DSAgentStreamingText