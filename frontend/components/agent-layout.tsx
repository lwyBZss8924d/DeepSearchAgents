"use client";

// Main layout component for DeepSearchAgents with DS components
import { useEffect, useState } from "react";
import { MonitorIcon, CodeIcon, TerminalIconComponent } from "@/components/terminal-icons";
import { useAppContext } from "@/context/app-context";
import { useWebSocket } from "@/hooks/use-websocket";
import { useSession } from "@/hooks/use-session";
import { useKeyboardShortcuts, commonShortcuts } from "@/hooks/use-keyboard-shortcuts";
import AgentChat from "@/components/agent-chat";
import AgentQuestionInput from "@/components/agent-question-input";
import CodeEditor from "@/components/code-editor-wrapper";
import Terminal from "@/components/terminal-wrapper";
import Browser from "@/components/browser";
import { StepNavigator } from "@/components/step-navigator";
import SessionStateIndicator from "@/components/session-state-indicator";
import AgentRunningStatus from "@/components/agent-running-status";
// Removed toast import - using console.error for now
import { 
  DSAgentTerminalContainer,
  DSTabs,
  DSTabsList,
  DSTabsTrigger,
  DSTabsContent 
} from "@/components/ds";

export default function AgentLayoutV2() {
  const { state, dispatch } = useAppContext();
  const { sessionId, createSession } = useSession();
  const { sendQuery } = useWebSocket(sessionId);
  const [showHelp, setShowHelp] = useState(false);

  // Create session on mount
  useEffect(() => {
    const initSession = async () => {
      console.log('Initializing session...');
      try {
        const newSessionId = await createSession({
          agent_type: state.agentType,
          max_steps: 20
        });
        console.log('Session created:', newSessionId);
        dispatch({ type: 'SET_SESSION_ID', payload: newSessionId });
      } catch (error) {
        console.error('Failed to create session:', error);
        console.error('Failed to create session');
      }
    };

    if (!state.sessionId) {
      initSession();
    }
  }, [state.agentType, state.sessionId, createSession, dispatch]);

  // Setup keyboard shortcuts
  useKeyboardShortcuts([
    {
      ...commonShortcuts.help,
      handler: () => setShowHelp(!showHelp),
    },
    {
      ...commonShortcuts.clearChat,
      handler: () => {
        if (confirm('Clear all messages?')) {
          dispatch({ type: 'CLEAR_MESSAGES' });
        }
      },
    },
    {
      ...commonShortcuts.focusInput,
      handler: () => {
        // Focus on the input textarea
        const input = document.querySelector('textarea[placeholder*="Ask a question"]') as HTMLTextAreaElement;
        if (input) {
          input.focus();
        }
      },
    },
    {
      ...commonShortcuts.toggleTheme,
      handler: () => {
        // Toggle theme - to be implemented with theme switcher
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
      },
    },
    {
      key: 'Escape',
      handler: () => setShowHelp(false),
    },
  ]);

  const handleSendQuery = async (query: string) => {
    if (!sessionId) {
      console.error('No active session');
      return;
    }

    // Clear messages when starting a new query
    dispatch({ type: 'CLEAR_MESSAGES' });
    dispatch({ type: 'SET_GENERATING', payload: true });

    try {
      await sendQuery(query);
    } catch (error) {
      console.error('Failed to send query:', error);
      console.error('Failed to send query');
      dispatch({ type: 'SET_GENERATING', payload: false });
    }
  };

  // Header content with agent status in fixed container on left, connection status on right
  const headerContent = (
    <>
      <div className="ds-agent-status-container">
        <AgentRunningStatus />
      </div>
    </>
  );
  
  // Right side header content - only session indicator now shows connection + ID
  const headerRightContent = (
    <>
      <SessionStateIndicator />
    </>
  );

  return (
    <DSAgentTerminalContainer
      className="h-screen flex flex-col"
      headerContent={headerContent}
      headerRightContent={headerRightContent}
    >

      {/* Main content area - Split Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Chat (50% width) */}
        <div className="w-1/2 flex flex-col border-r border-[var(--ds-border-default)]">
          <div className="flex-1 overflow-y-auto">
            <AgentChat />
          </div>
          <div className="border-t border-[var(--ds-border-default)]">
            <AgentQuestionInput
              onSubmit={handleSendQuery}
              isRunning={state.isGenerating}
              sessionId={sessionId}
            />
          </div>
        </div>

        {/* Right Panel - Split into upper and lower sections (50% width) */}
        <div className="w-1/2 flex flex-col">
          {/* Upper Section - Code Editor/Browser tabs (50% height) */}
          <div className="h-1/2 flex flex-col border-b border-[var(--ds-border-default)]">
            <DSTabs defaultValue="code" className="h-full flex flex-col">
              <DSTabsList className="px-4">
                <DSTabsTrigger value="code" icon={<CodeIcon size={16} />}>
                  Code
                </DSTabsTrigger>
                <DSTabsTrigger value="browser" icon={<MonitorIcon size={16} />}>
                  Browser
                </DSTabsTrigger>
              </DSTabsList>
              
              <DSTabsContent value="code" className="flex-1 overflow-hidden">
                <CodeEditor />
              </DSTabsContent>
              
              <DSTabsContent value="browser" className="flex-1 overflow-hidden">
                <Browser />
              </DSTabsContent>
            </DSTabs>
          </div>

          {/* Lower Section - Terminal (50% height) */}
          <div className="h-1/2 flex flex-col">
            <div className="flex items-center gap-2 px-4 py-2 border-b border-[var(--ds-border-default)] bg-[var(--ds-bg-elevated)]">
              <TerminalIconComponent size={16} className="text-[var(--ds-terminal-dim)]" />
              <span className="text-sm font-mono text-[var(--ds-terminal-fg)]">Terminal</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <Terminal />
            </div>
          </div>

          {/* Step Navigator - fixed at bottom */}
          {state.maxStep > 0 && (
            <div className="border-t border-[var(--ds-border-default)]">
              <StepNavigator
                currentStep={state.currentStep}
                maxStep={state.maxStep}
                onStepChange={(step) => dispatch({ type: 'SET_CURRENT_STEP', payload: step })}
              />
            </div>
          )}
        </div>
      </div>
      
      {/* Help Overlay */}
      {showHelp && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowHelp(false)}>
          <div className="ds-help-overlay" onClick={(e) => e.stopPropagation()}>
            <pre>{`
╔═══════════════════════════════════════════════════════╗
║              Keyboard Shortcuts                       ║
╠═══════════════════════════════════════════════════════╣
║  ?         Show this help                             ║
║  /         Focus input                                ║
║  Ctrl+K    Open command palette (coming soon)         ║
║  Ctrl+L    Clear chat                                 ║
║  Ctrl+T    Toggle theme                               ║
║  Ctrl+Shift+C  Copy last message (coming soon)        ║
║  Ctrl+E    Export chat (coming soon)                  ║
║  Esc       Close this help                            ║
╚═══════════════════════════════════════════════════════╝
            `}</pre>
          </div>
        </div>
      )}
    </DSAgentTerminalContainer>
  );
}