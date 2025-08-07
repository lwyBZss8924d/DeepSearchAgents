"use client";

import { useAppContext } from "@/context/app-context";
import { DSAgentStateBadge } from "@/components/ds/DSAgentStateBadge";
import { DSAgentTimer } from "@/components/ds/DSAgentTimer";
import { DSAgentRandomMatrix } from "@/components/ds/DSAgentRandomMatrix";
// import { cn } from "@/lib/utils";
import { 
  DetailedAgentStatus, 
  statusConfig
} from "@/types/agent-status.types";

export default function AgentRunningStatus() {
  const { state } = useAppContext();
  const { currentAgentStatus, isGenerating, currentStep, messages } = state;

  // Get display configuration from the current status
  // Simplified: No animation, just accurate status display
  // If we have a status, use it; otherwise show loading if generating
  const status = currentAgentStatus as DetailedAgentStatus;
  const config = statusConfig[status] || statusConfig.standby;
  
  // Override with loading if no specific status but still generating
  const displayConfig = (status === 'standby' && isGenerating) 
    ? statusConfig.loading 
    : config;

  // Enable animation based on status configuration
  const shouldAnimate = displayConfig.animated;
  
  // Check if agent is active (has start time)
  const { agentStartTime } = state;
  const isActive = !!agentStartTime;
  
  // Calculate max step from messages
  const maxStep = Math.max(
    ...messages.map(m => m.step_number || 0),
    currentStep || 0
  );
  
  // Show step indicator only when agent is running (not standby)
  const showStepIndicator = isActive && status !== 'standby';
  
  return (
    <div className="ds-agent-running-status">
      <DSAgentStateBadge
        state={displayConfig.agentState}
        text={displayConfig.text}
        showSpinner={shouldAnimate}  // Show animation for divining
        isAnimated={shouldAnimate}   // Enable animation for divining
        className="text-sm"
      />
      {showStepIndicator && maxStep > 0 && (
        <span className="ds-step-indicator text-xs opacity-60 ml-2">
          [Step {maxStep}]
        </span>
      )}
      <DSAgentRandomMatrix 
        isActive={isActive}
        className="text-xs opacity-70"
      />
      <DSAgentTimer 
        className="text-xs opacity-80"
      />
    </div>
  );
}