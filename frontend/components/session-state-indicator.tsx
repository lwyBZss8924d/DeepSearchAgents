"use client";

import { useAppContext } from "@/context/app-context";
import { cn } from "@/lib/utils";

export default function SessionStateIndicator() {
  const { state } = useAppContext();
  const { isConnected, isGenerating, isCompleted, sessionId } = state;

  const getStateInfo = () => {
    if (!isConnected) {
      return {
        status: 'offline',
        text: 'OFFLINE',
        color: 'var(--ds-terminal-red)',
        icon: '◉',
        pulse: false
      };
    }

    if (!sessionId) {
      return {
        status: 'initializing',
        text: 'INIT...',
        color: 'var(--ds-terminal-yellow)',
        icon: '◎',
        pulse: true
      };
    }

    if (isGenerating) {
      return {
        status: 'processing',
        text: 'PROCESSING',
        color: 'var(--ds-terminal-cyan)',
        icon: '◉',
        pulse: true
      };
    }

    if (isCompleted) {
      return {
        status: 'complete',
        text: 'COMPLETE',
        color: 'var(--ds-terminal-green)',
        icon: '✓',
        pulse: false
      };
    }

    return {
      status: 'ready',
      text: 'READY',
      color: 'var(--ds-terminal-green)',
      icon: '◉',
      pulse: false
    };
  };

  const stateInfo = getStateInfo();

  return (
    <div className="ds-session-state">
      <span 
        className={cn(
          "ds-session-state-icon",
          stateInfo.pulse && "ds-session-state-pulse"
        )}
        style={{ color: stateInfo.color }}
      >
        {stateInfo.icon}
      </span>
      <span 
        className="ds-session-state-text"
        style={{ color: stateInfo.color }}
      >
        {stateInfo.text}
      </span>
      {sessionId && (
        <span className="ds-session-state-id">
          [{sessionId.slice(0, 8)}]
        </span>
      )}
    </div>
  );
}