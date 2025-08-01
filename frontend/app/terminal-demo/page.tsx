"use client"

import { TerminalUIDemo } from '@/components/terminal-ui-demo'
import { TerminalAgentChat } from '@/components/terminal-agent-chat'
import { DSAgentRunMessage } from '@/types/api.types'

// Demo messages to show the terminal UI in action
const demoMessages: DSAgentRunMessage[] = [
  {
    message_id: "1",
    role: "user",
    content: "Search for information about the CodeAct paradigm and how it enables agents to execute code as actions",
    step_number: 0,
    metadata: {}
  },
  {
    message_id: "2", 
    role: "assistant",
    content: "◆ Analyzing task requirements...\n◆ Identifying required tools: search_web, read_url, final_answer\n◆ Creating execution plan with 3 steps",
    step_number: 1,
    metadata: {
      step_type: "planning",
      message_type: "planning_message"
    }
  },
  {
    message_id: "3",
    role: "assistant", 
    content: "I need to search for information about the CodeAct paradigm and how it enables agents to execute code as actions. Let me start by searching for relevant sources.\n\n```python\nresults = search_web(\n    query=\"CodeAct paradigm executable code agents\",\n    max_results=5\n)\nprint(f\"Found {len(results)} relevant sources\")\n```",
    step_number: 2,
    metadata: {
      step_type: "action",
      message_type: "action_message",
      tool_name: "search_web"
    }
  },
  {
    message_id: "4",
    role: "assistant",
    content: "Based on my research, I've compiled comprehensive information about the CodeAct paradigm:\n\n## The CodeAct Paradigm\n\nCodeAct represents a revolutionary approach to building AI agents where **executable code becomes the primary action mechanism**. Instead of using predefined JSON-based tool calls, agents generate and execute Python code directly.\n\n### Key Benefits:\n1. **Flexibility**: Agents can perform complex multi-step operations\n2. **Transparency**: All actions are visible as readable code\n3. **Power**: Full computational capabilities of Python",
    step_number: 3,
    metadata: {
      step_type: "final_answer",
      message_type: "final_answer",
      has_structured_data: true,
      answer_title: "Understanding the CodeAct Paradigm"
    }
  }
]

export default function TerminalDemoPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8 space-y-8">
        <h1 className="text-3xl font-bold text-center mb-8">
          Terminal UI Design System Demo
        </h1>
        
        {/* Terminal Agent Chat Demo */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Terminal Agent Chat</h2>
          <div className="h-[600px] border border-border rounded-lg overflow-hidden">
            <TerminalAgentChat 
              messages={demoMessages}
              isGenerating={false}
            />
          </div>
        </section>

        {/* Component Library Demo */}
        <section>
          <h2 className="text-2xl font-semibold mb-4">Component Library</h2>
          <TerminalUIDemo />
        </section>
      </div>
    </div>
  )
}