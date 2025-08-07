"use client"

import React, { useEffect } from 'react'
import { DSAgentToolBadge } from './DSAgentToolBadge'

/**
 * Debug component to test tool badge rendering
 */
export function DSAgentToolBadgeDebug() {
  useEffect(() => {
    console.log('[DSAgentToolBadgeDebug] Component mounted')
  }, [])

  const testCases = [
    // Clean tool names
    { name: 'python_interpreter', label: 'Clean Python' },
    { name: 'final_answer', label: 'Clean Final' },
    
    // With strikethrough marks (what user sees)
    { name: '~~✓~~ ~~💻~~python_interpreter~~', label: 'With Strikethrough' },
    { name: '~~⚡~~ ~~💻~~python_interpreter~~', label: 'Active with Strikethrough' },
    { name: '~~⚡~~ ~~📝~~final_answer~~', label: 'Final with Strikethrough' },
    
    // Mixed content
    { name: '✓💻python_interpreter', label: 'With Icons No Strikethrough' },
    { name: '⚡💻python_interpreter', label: 'Active Icons No Strikethrough' },
  ]

  return (
    <div style={{ 
      padding: '2rem', 
      background: '#0d1117', 
      color: '#58a6ff',
      fontFamily: 'monospace' 
    }}>
      <h2 style={{ marginBottom: '1rem' }}>Tool Badge Debug Test</h2>
      
      {testCases.map((test, idx) => (
        <div key={idx} style={{ marginBottom: '1rem' }}>
          <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem', opacity: 0.7 }}>
            {test.label}: &quot;{test.name}&quot;
          </div>
          <DSAgentToolBadge 
            toolName={test.name}
            status="active"
          />
        </div>
      ))}
      
      <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #30363d' }}>
        <h3>Direct HTML Test</h3>
        <div>Raw text with strikethrough marks: ~~✓~~ ~~💻~~python_interpreter~~</div>
        <div>In a code block: <code>~~✓~~ ~~💻~~python_interpreter~~</code></div>
      </div>
    </div>
  )
}