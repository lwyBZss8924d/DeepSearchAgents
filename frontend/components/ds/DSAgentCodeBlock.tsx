"use client"

import React, { useState } from 'react'
import { cn } from '@/lib/utils'

interface ExecutionResult {
  output?: string
  error?: string
  exitCode?: number
}

interface DSAgentCodeBlockProps {
  code: string
  language?: 'python' | 'javascript' | 'bash' | 'json' | string
  lineNumbers?: boolean
  highlightLines?: number[]
  streaming?: boolean
  executable?: boolean
  onExecute?: () => void | Promise<void>
  executionResult?: ExecutionResult
  className?: string
  showHeader?: boolean
  onCopy?: () => void
}

/**
 * DSAgentCodeBlock - WebTUI-based code block component
 * 
 * Terminal-style code display with line numbers and execution support
 * Uses WebTUI box-="double" for classic code block borders
 */
export function DSAgentCodeBlock({ 
  code,
  language = 'text',
  lineNumbers = true,
  highlightLines = [],
  streaming = false,
  executable = false,
  onExecute,
  executionResult,
  className,
  showHeader = true,
  onCopy
}: DSAgentCodeBlockProps) {
  const [isCopied, setIsCopied] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  
  const lines = code.split('\n')
  const maxLineNumberWidth = lines.length.toString().length
  
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
      onCopy?.()
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }
  
  const handleExecute = async () => {
    if (!onExecute || isExecuting) return
    
    setIsExecuting(true)
    try {
      await onExecute()
    } finally {
      setIsExecuting(false)
    }
  }
  
  return (
    <div className={cn('ds-code-block-container neovim-style', className)}>
      {/* Header */}
      {showHeader && (
        <div className="ds-code-header">
          <span className="ds-code-language text-[var(--ds-terminal-dim)]">{language}</span>
          <div className="ds-code-actions">
            <button
              onClick={handleCopy}
              className="ds-code-action-btn"
              data-copied={isCopied}
              aria-label="Copy code"
            >
              {isCopied ? '[✓]' : '[⧉]'}
            </button>
            {executable && onExecute && (
              <button
                onClick={handleExecute}
                className="ds-code-action-btn"
                disabled={isExecuting}
                aria-label="Run code"
              >
                {isExecuting ? '[◐]' : '[▶]'}
              </button>
            )}
          </div>
        </div>
      )}
      
      {/* Code Content */}
      <div
        box-="double"
        className="ds-code-content"
        code-streaming={streaming ? '' : undefined}
      >
        <pre className="ds-code-pre">
          <code className={`language-${language}`}>
            {lines.map((line, idx) => {
              const lineNumber = idx + 1
              const isHighlighted = highlightLines.includes(lineNumber)
              
              return (
                <div
                  key={idx}
                  className={cn(
                    'ds-code-line',
                    isHighlighted && 'ds-code-line-highlighted'
                  )}
                >
                  {lineNumbers && (
                    <span 
                      className="ds-code-line-number"
                      style={{ width: `${maxLineNumberWidth}ch` }}
                    >
                      {lineNumber}
                    </span>
                  )}
                  <span className="ds-code-line-content">{line || ' '}</span>
                </div>
              )
            })}
            {streaming && (
              <span className="ds-code-cursor" aria-hidden="true">▋</span>
            )}
          </code>
        </pre>
      </div>
      
      {/* Execution Result */}
      {executionResult && (
        <div
          box-="single"
          className={cn(
            'ds-code-result',
            executionResult.error && 'ds-code-result-error'
          )}
        >
          {executionResult.output && (
            <pre className="ds-code-output">{executionResult.output}</pre>
          )}
          {executionResult.error && (
            <pre className="ds-code-error">{executionResult.error}</pre>
          )}
          {executionResult.exitCode !== undefined && (
            <div className="ds-code-exit-code">
              Exit code: {executionResult.exitCode}
            </div>
          )}
        </div>
      )}
      
      {/* Neovim-style status bar */}
      <div className="neovim-status-bar">
        <span>{language} | {lines.length} lines</span>
        <span>-- {streaming ? 'INSERT' : 'NORMAL'} --</span>
      </div>
    </div>
  )
}