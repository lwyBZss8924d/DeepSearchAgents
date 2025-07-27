"use client";

// Main layout component for DeepSearchAgents
import { useEffect } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Monitor, Code2, Terminal as TerminalIcon } from "lucide-react";
import { useAppContext } from "@/context/app-context";
import { useWebSocket } from "@/hooks/use-websocket";
import { useSession } from "@/hooks/use-session";
import AgentChat from "@/components/agent-chat";
import AgentQuestionInput from "@/components/agent-question-input";
import CodeEditor from "@/components/code-editor-wrapper";
import Terminal from "@/components/terminal-wrapper";
import Browser from "@/components/browser";
import { StepNavigator } from "@/components/step-navigator";
import ConnectionStatus from "@/components/connection-status";
import { toast } from "sonner";

export default function AgentLayout() {
  const { state, dispatch } = useAppContext();
  const { sessionId, createSession } = useSession();
  const { sendQuery } = useWebSocket(sessionId);

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
        toast.error('Failed to create session');
      }
    };

    if (!sessionId) {
      initSession();
    }
  }, [sessionId, createSession, state.agentType, dispatch]);

  const handleQuestionSubmit = (question: string) => {
    dispatch({ type: 'SET_CURRENT_QUESTION', payload: question });
    sendQuery(question);
  };

  const handleStepChange = (step: number) => {
    dispatch({ type: 'SET_CURRENT_STEP', payload: step });
  };

  const handleTabChange = (value: string) => {
    dispatch({ 
      type: 'SET_ACTIVE_TAB', 
      payload: value as 'browser' | 'code' 
    });
  };

  return (
    <div className="fixed inset-0 flex bg-background overflow-hidden">
      {/* Left Panel - Chat */}
      <div className="w-1/2 flex flex-col border-r h-full">
        {/* Header */}
        <div className="flex-shrink-0 flex items-center justify-between p-4 border-b">
          <div>
            <h1 className="text-lg font-semibold">DeepSearchAgents</h1>
            <p className="text-sm text-muted-foreground">
              {state.agentType === 'react' ? 'ReAct Agent' : 'CodeAct Agent'}
            </p>
          </div>
          <ConnectionStatus />
        </div>

        {/* Chat messages - scrollable */}
        <AgentChat className="flex-1 overflow-hidden" />

        {/* Question input - fixed at bottom */}
        <div className="flex-shrink-0">
          <AgentQuestionInput onSubmit={handleQuestionSubmit} />
        </div>
      </div>

      {/* Right Panel - Split Layout */}
      <div className="w-1/2 flex flex-col h-full">
        {/* Upper Section - Code Editor/Browser (50% height) */}
        <div className="h-1/2 flex flex-col border-b">
          <Tabs 
            value={state.activeTab} 
            onValueChange={handleTabChange}
            className="h-full flex flex-col"
          >
            <TabsList className="flex-shrink-0 w-full justify-start rounded-none border-b h-12">
              <TabsTrigger value="browser" className="gap-2">
                <Monitor className="h-4 w-4" />
                Browser
              </TabsTrigger>
              <TabsTrigger value="code" className="gap-2">
                <Code2 className="h-4 w-4" />
                Code Editor
              </TabsTrigger>
            </TabsList>

            <div className="flex-1 overflow-hidden">
              <TabsContent value="browser" className="h-full m-0">
                <Browser className="h-full" />
              </TabsContent>
              
              <TabsContent value="code" className="h-full m-0">
                <CodeEditor className="h-full" />
              </TabsContent>
            </div>
          </Tabs>
        </div>

        {/* Lower Section - Terminal (50% height) */}
        <div className="h-1/2 flex flex-col">
          <div className="flex-shrink-0 flex items-center justify-between p-3 border-b bg-background">
            <div className="flex items-center gap-2">
              <TerminalIcon className="h-4 w-4" />
              <span className="text-sm font-medium">Terminal</span>
            </div>
          </div>
          <div className="flex-1 overflow-hidden">
            <Terminal className="h-full" />
          </div>
        </div>

        {/* Step Navigator - fixed at bottom */}
        {state.maxStep > 0 && (
          <div className="flex-shrink-0">
            <StepNavigator
              currentStep={state.currentStep}
              maxStep={state.maxStep}
              onStepChange={handleStepChange}
            />
          </div>
        )}
      </div>
    </div>
  );
}