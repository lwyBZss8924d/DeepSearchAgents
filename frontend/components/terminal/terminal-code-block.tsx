"use client"

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface TerminalCodeBlockProps {
  code: string
  language?: string
  showLineNumbers?: boolean
  className?: string
}

export function TerminalCodeBlock({ 
  code, 
  language = 'python',
  showLineNumbers = false,
  className 
}: TerminalCodeBlockProps) {
  // language prop is available for future syntax highlighting
  const lines = code.split('\n')
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className={cn("terminal-code-block", className)}
    >
      <code className="block pt-4">
        {showLineNumbers ? (
          lines.map((line, index) => (
            <div key={index} className="flex">
              <span className="text-terminal-dim-green mr-4 select-none">
                {String(index + 1).padStart(3, ' ')}
              </span>
              <span>{line || '\n'}</span>
            </div>
          ))
        ) : (
          code
        )}
      </code>
    </motion.div>
  )
}