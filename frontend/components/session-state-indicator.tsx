"use client";

import { useAppContext } from "@/context/app-context";
// import { cn } from "@/lib/utils";

export default function SessionStateIndicator() {
  const { state } = useAppContext();
  const { isConnected, sessionId } = state;

  // Simplified state - show connection status with session ID
  const getStateInfo = () => {
    if (!isConnected) {
      return {
        icon: '◉',
        color: 'var(--ds-terminal-red)',
        text: 'Disconnected',
        showId: false
      };
    }

    if (!sessionId) {
      return {
        icon: '◎',
        color: 'var(--ds-terminal-yellow)',
        text: 'Connecting',
        showId: false
      };
    }

    // Connected with session - show as Connected with ID
    return {
      icon: '◉',
      color: 'var(--ds-terminal-green)',
      text: 'Connected',
      showId: true
    };
  };

  const stateInfo = getStateInfo();

  return (
    <div className="ds-session-state">
      <span 
        className="ds-session-state-icon"
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
      {stateInfo.showId && sessionId && (
        <span className="ds-session-state-id">
          [{sessionId.slice(0, 8)}]
        </span>
      )}
    </div>
  );
}