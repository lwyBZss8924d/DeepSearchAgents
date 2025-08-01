"use client"

import React from 'react'

export function TerminalUIDemo() {
  return (
    <div className="terminal-ui terminal-theme p-8 min-h-screen bg-background">
      <div className="max-w-4xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-terminal-green mb-8">
          DeepSearchAgents Terminal UI Demo
        </h1>

        {/* Agent State Badges Demo */}
        <section className="space-y-4">
          <h2 className="text-lg text-terminal-cyan mb-4">Agent State Indicators</h2>
          <div className="flex flex-wrap gap-3">
            <div className="agent-state-badge planning">
              <span className="agent-spinner"></span>
              Planning...
            </div>
            <div className="agent-state-badge thinking">
              <span className="agent-spinner"></span>
              Thinking...
            </div>
            <div className="agent-state-badge coding">
              <span className="agent-spinner"></span>
              Coding...
            </div>
            <div className="agent-state-badge running">
              <span className="agent-spinner"></span>
              Actions Running...
            </div>
            <div className="agent-state-badge final">
              Writing...
            </div>
          </div>
        </section>

        {/* Tool Badges Demo */}
        <section className="space-y-4">
          <h2 className="text-lg text-terminal-cyan mb-4">Tool Call Badges</h2>
          <div className="flex flex-wrap gap-2">
            <span className="tool-badge">
              <span className="tool-icon">🔍</span>
              search_web
            </span>
            <span className="tool-badge">
              <span className="tool-icon">📄</span>
              read_url
            </span>
            <span className="tool-badge">
              <span className="tool-icon">🧮</span>
              wolfram_alpha
            </span>
            <span className="tool-badge">
              <span className="tool-icon">📊</span>
              analyze_data
            </span>
            <span className="tool-badge">
              <span className="tool-icon">✅</span>
              final_answer
            </span>
          </div>
        </section>

        {/* Agent Message Cards Demo */}
        <section className="space-y-4">
          <h2 className="text-lg text-terminal-cyan mb-4">Agent Message Flow</h2>
          
          {/* Planning Message */}
          <div className="agent-message-card planning">
            <div className="flex items-center gap-2 mb-2">
              <div className="agent-state-badge planning">
                Planning
              </div>
            </div>
            <div className="text-sm space-y-1 text-muted-foreground">
              <div>◆ Analyzing task requirements...</div>
              <div>◆ Identifying required tools: search_web, read_url, final_answer</div>
              <div>◆ Creating execution plan with 3 steps</div>
            </div>
          </div>

          {/* Action Message */}
          <div className="agent-message-card action active">
            <div className="flex items-center gap-2 mb-2">
              <div className="agent-state-badge thinking">
                <span className="agent-spinner"></span>
                Action Thinking
              </div>
              <span className="tool-badge">
                <span className="tool-icon">🔍</span>
                search_web
              </span>
            </div>
            <div className="text-sm mb-3">
              I need to search for information about DeepSearchAgents and the CodeAct paradigm to understand how agents execute code as actions...
            </div>
            <div className="terminal-code-block">
              <code className="block pt-4">
{`results = search_web(
    query="DeepSearchAgents CodeAct paradigm executable code agents",
    max_results=5
)
print(f"Found {len(results)} relevant sources")`}
              </code>
            </div>
          </div>

          {/* Final Answer Message */}
          <div className="agent-message-card final">
            <div className="flex items-center gap-2 mb-2">
              <div className="agent-state-badge final">
                Final Answer
              </div>
            </div>
            <div className="streaming-text">
              Based on my research, DeepSearchAgents implements the CodeAct paradigm where agents use executable Python code as their primary action mechanism. This approach allows for more flexible and powerful agent behaviors compared to traditional JSON-based tool calling...
            </div>
          </div>
        </section>

        {/* Interactive Elements Demo */}
        <section className="space-y-4">
          <h2 className="text-lg text-terminal-cyan mb-4">Interactive Elements</h2>
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Enter your query..."
              className="terminal-input w-full"
            />
            <div className="flex gap-3">
              <button className="terminal-button">
                Execute Query
              </button>
              <button className="terminal-button">
                Clear History
              </button>
              <select className="terminal-select">
                <option>ReAct Agent</option>
                <option>CodeAct Agent</option>
              </select>
            </div>
          </div>
        </section>

        {/* Terminal Container Demo */}
        <section className="space-y-4">
          <h2 className="text-lg text-terminal-cyan mb-4">Terminal Output</h2>
          <div className="terminal-container font-mono text-sm">
            <div className="text-terminal-dim-green"># Agent Execution Log</div>
            <div className="text-terminal-green">▶ Initializing CodeAct Agent...</div>
            <div className="text-terminal-yellow">▶ Loading tools: search_web, read_url, wolfram_alpha, final_answer</div>
            <div className="text-terminal-cyan">▶ Agent ready. Waiting for user input...</div>
            <div className="mt-2">
              <span className="text-terminal-green">agent@deepsearch</span>
              <span className="text-terminal-white">:</span>
              <span className="text-terminal-blue">~</span>
              <span className="text-terminal-white">$</span>
              <span className="terminal-cursor"></span>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}