"use client"

import React, { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { User, Bot } from 'lucide-react'
import { DSAgentRunMessage } from '@/types/api.types'
import { 
  TerminalMessageCard, 
  TerminalStateBadge, 
  TerminalToolBadge,
  TerminalCodeBlock,
  TerminalStreamingText,
  type AgentState
} from './terminal'
import { 
  // isThinkingMessage,  // Commented out - not currently used
  isFinalAnswer, 
  getToolName, 
  isPlanningStep,
  isActionStepThought,
} from '@/utils/extractors'
import Markdown from '@/components/markdown'
import FinalAnswerDisplay from '@/components/final-answer-display-v2'

interface TerminalAgentChatProps {
  messages: DSAgentRunMessage[]
  isGenerating?: boolean
  className?: string
}

export function TerminalAgentChat({ 
  messages, 
  isGenerating = false,
  className 
}: TerminalAgentChatProps) {
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Group messages by step
  const messagesByStep = messages.reduce((acc, message) => {
    const step = message.step_number || 0
    if (!acc[step]) acc[step] = []
    acc[step].push(message)
    return acc
  }, {} as Record<number, DSAgentRunMessage[]>)

  const visibleSteps = Object.keys(messagesByStep)
    .map(Number)
    .sort((a, b) => a - b)

  return (
    <div className={`terminal-ui terminal-theme flex flex-col h-full ${className}`}>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {visibleSteps.map(step => (
          <div key={step} className="space-y-3">
            {step > 0 && (
              <div className="flex items-center gap-2 text-xs text-terminal-dim-green">
                <div className="flex-1 h-[1px] bg-terminal-dim" />
                <span className="font-terminal">Step {step}</span>
                <div className="flex-1 h-[1px] bg-terminal-dim" />
              </div>
            )}
            
            {messagesByStep[step].map((message) => (
              <TerminalMessageItem key={message.message_id} message={message} />
            ))}
          </div>
        ))}

        {/* Loading indicator */}
        {isGenerating && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-full bg-terminal-green/20 flex items-center justify-center">
              <Bot className="w-5 h-5 text-terminal-green" />
            </div>
            <TerminalMessageCard type="system" isActive>
              <TerminalStateBadge state="thinking" text="Agent is working..." />
            </TerminalMessageCard>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}

// Individual message component with terminal styling
function TerminalMessageItem({ message }: { message: DSAgentRunMessage }) {
  const isUser = message.role === 'user'
  // const isThinking = isThinkingMessage(message.metadata) || isPlanningStep(message.metadata)
  const isPlanning = isPlanningStep(message.metadata)
  const isActionThought = isActionStepThought(message.metadata, message.content)
  const isFinal = isFinalAnswer(message.metadata, message.content)
  const isStreaming = message.metadata?.streaming === true
  const toolName = getToolName(message.metadata)
  
  // Determine agent state
  let agentState: AgentState | null = null
  if (isPlanning) agentState = 'planning'
  else if (isActionThought && !toolName) agentState = 'thinking'
  else if (toolName) agentState = 'coding'
  else if (isFinal) agentState = 'final'
  
  // Extract code from content
  const codeMatch = message.content.match(/```python\n([\s\S]*?)```/)
  const code = codeMatch ? codeMatch[1] : null
  const textContent = code 
    ? message.content.replace(/```python\n[\s\S]*?```/, '').trim()
    : message.content

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex items-start gap-3"
      >
        <div className="w-8 h-8 rounded-full bg-terminal-blue/20 flex items-center justify-center">
          <User className="w-5 h-5 text-terminal-blue" />
        </div>
        <TerminalMessageCard type="user" className="flex-1">
          <div className="text-terminal-fg">{message.content}</div>
        </TerminalMessageCard>
      </motion.div>
    )
  }

  // Agent message
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-start gap-3"
    >
      <div className="w-8 h-8 rounded-full bg-terminal-green/20 flex items-center justify-center">
        <Bot className="w-5 h-5 text-terminal-green" />
      </div>
      <TerminalMessageCard 
        type={isPlanning ? 'planning' : isActionThought ? 'action' : isFinal ? 'final' : 'system'}
        isActive={isStreaming}
        className="flex-1"
      >
        <div className="space-y-3">
          {/* Header with state badge and tool badge */}
          <div className="flex items-center gap-2 flex-wrap">
            {agentState && (
              <TerminalStateBadge 
                state={agentState} 
                showSpinner={isStreaming}
              />
            )}
            {toolName && <TerminalToolBadge toolName={toolName} />}
          </div>

          {/* Message content */}
          {textContent && (
            <TerminalStreamingText isStreaming={isStreaming}>
              {isFinal && message.metadata?.has_structured_data ? (
                <FinalAnswerDisplay 
                  content={textContent}
                  metadata={message.metadata}
                />
              ) : isPlanning ? (
                <div className="space-y-1 text-sm text-terminal-dim-green">
                  {textContent.split('\n').map((line, i) => (
                    <div key={i}>{line.startsWith('◆') ? line : `◆ ${line}`}</div>
                  ))}
                </div>
              ) : (
                <div className="text-terminal-fg prose prose-invert prose-sm max-w-none">
                  <Markdown content={textContent} />
                </div>
              )}
            </TerminalStreamingText>
          )}

          {/* Code block if present */}
          {code && (
            <TerminalCodeBlock code={code} />
          )}
        </div>
      </TerminalMessageCard>
    </motion.div>
  )
}