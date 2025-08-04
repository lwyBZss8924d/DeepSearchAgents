"use client";

import { motion } from "framer-motion";
import {
  Check,
  SkipForward,
} from "lucide-react";
import { useState, useEffect } from "react";

import Markdown from "@/components/markdown";
import QuestionInput from "@/components/question-input";
import FinalAnswerDisplay from "@/components/final-answer-display";
import PlanningCard from "@/components/planning-card";
import ActionThoughtCard from "@/components/action-thought-card";
import { DSAgentToolBadge } from "@/components/ds";
import { DSAgentRunMessage } from "@/types/api.types";
import { isFinalAnswer } from "@/utils/extractors";
import { DSButton } from "@/components/ds";
import { useAppContext } from "@/context/app-context";

interface ChatMessageProps {
  isReplayMode: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  setCurrentQuestion: (value: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  handleQuestionSubmit: (question: string) => void;
  handleEnhancePrompt: () => void;
  handleCancel: () => void;
  processAllEventsImmediately?: () => void;
  connectWebSocket: () => void;
}

const ChatMessage = ({
  messagesEndRef,
  isReplayMode,
  setCurrentQuestion,
  handleKeyDown,
  handleQuestionSubmit,
  handleEnhancePrompt,
  handleCancel,
  processAllEventsImmediately,
  connectWebSocket,
}: ChatMessageProps) => {
  const { state } = useAppContext();
  const [showQuestionInput, setShowQuestionInput] = useState(false);
  const [pendingFilesCount, setPendingFilesCount] = useState(0);
  const [userHasScrolledUp, setUserHasScrolledUp] = useState(false);
  
  // Helper function to render assistant message content
  const renderAssistantMessage = (message: DSAgentRunMessage) => {
    // Ensure we're working with DSAgentRunMessage
    const dsMessage = message as DSAgentRunMessage;
    
    // Safely access metadata with fallback
    const metadata = dsMessage.metadata || {};
    const messageType = metadata.message_type;
    
    // Comprehensive diagnostic logging
    console.log("[renderAssistantMessage] Processing:", {
      message_id: dsMessage.message_id,
      hasMetadata: !!dsMessage.metadata,
      messageType: messageType,
      contentLength: message.content?.length || 0,
      contentPreview: message.content?.substring(0, 50),
      role: message.role
    });
    
    // Additional check for action_thought
    if (messageType === "action_thought" || message.content?.startsWith("Thought:")) {
      console.log("[ACTION_THOUGHT DETECTED]", {
        messageType,
        contentStarts: message.content?.substring(0, 50),
        willUseActionThoughtCard: true
      });
    }
    if (messageType === "planning_header") {
      console.log("[Planning Header Debug]", {
        planning_type: metadata.planning_type,
        content: message.content,
        full_metadata: metadata
      });
      
      const planningType = metadata.planning_type || "initial";
      const badgeText = planningType === "initial" ? "Initial Plan" : "Updated Plan";
      const badgeClass = planningType === "initial" ? "planning-badge-initial" : "planning-badge-update";
      
      console.log("[Planning Badge] Rendering with:", {
        planningType,
        badgeText,
        badgeClass,
        fullClassName: `planning-badge ${badgeClass}`
      });
      
      return (
        <div className="w-full">
          <span className={`planning-badge ${badgeClass}`}>
            {badgeText}
          </span>
          {message.content && (
            <div className="mt-2">
              <Markdown>{message.content}</Markdown>
            </div>
          )}
        </div>
      );
    }
    
    // Final answer
    if (isFinalAnswer(metadata, message.content)) {
      console.log("[Chat Message] Final answer detected:", {
        metadata: metadata,
        content_preview: message.content?.substring(0, 100) + "...",
        content_empty: !message.content || message.content === "",
        has_structured_data: metadata?.has_structured_data,
        answer_format: metadata?.answer_format,
        answer_title: metadata?.answer_title,
        answer_content_preview: metadata?.answer_content?.substring(0, 100) + "..."
      });
      console.log("[Chat Message] Rendering FinalAnswerDisplay component");
      return <FinalAnswerDisplay 
        content={message.content || ""} 
        metadata={metadata}
        className="w-full" 
      />;
    }
    
    // Planning content
    if (messageType === "planning_content") {
      return (
        <PlanningCard
          content={message.content || ""}
          planningType={metadata.planning_type || "initial"}
          stepNumber={dsMessage.step_number}
          className="w-full"
        />
      );
    }
    
    // Tool call badge
    if (messageType === "tool_call") {
      console.log("[Tool Call Badge]", {
        tool_name: metadata.tool_name,
        tool_id: metadata.tool_id,
        args_summary: metadata.tool_args_summary
      });
      return (
        <DSAgentToolBadge
          toolName={metadata.tool_name || "unknown"}
          status="active"
          metadata={{
            resultPreview: metadata.tool_args_summary,
            toolId: metadata.tool_id
          }}
          className="mb-2"
        />
      );
    }
    
    // Action thought
    if (messageType === "action_thought") {
      console.log("[Action Thought Debug]", {
        content_length: message.content?.length,
        content_preview: message.content?.substring(0, 50) + "...",
        metadata: metadata
      });
      return (
        <ActionThoughtCard
          content={message.content || ""}
          stepNumber={dsMessage.step_number}
          className="w-full"
        />
      );
    }
    
    // Additional check for Thought: prefix
    if (message.content?.startsWith("Thought:")) {
      console.log("[Thought Message Fallback]", {
        content_preview: message.content?.substring(0, 100) + "...",
        metadata: metadata,
        message_type: messageType
      });
      // Use ActionThoughtCard for these messages too
      return (
        <ActionThoughtCard
          content={message.content || ""}
          stepNumber={dsMessage.step_number}
          className="w-full"
        />
      );
    }
    
    // Additional check for final answer JSON structure
    if (message.content && message.content.includes('"title"') && message.content.includes('"content"') && message.content.includes('"sources"')) {
      console.log("[Final Answer JSON Fallback]", {
        content_preview: message.content?.substring(0, 100) + "...",
        metadata: metadata
      });
      // Force use of FinalAnswerDisplay for JSON that looks like final answer
      return <FinalAnswerDisplay 
        content={message.content || ""} 
        metadata={metadata}
        className="w-full" 
      />;
    }
    
    // Default markdown rendering
    return <Markdown>{message.content}</Markdown>;
  };

  const handleFilesChange = (count: number) => {
    setPendingFilesCount(count);
  };

  useEffect(() => {
    if (isReplayMode && !state.isGenerating && state.messages.length > 0) {
      // If we're in replay mode, loading is complete, and we have messages,
      // we can assume all events have been processed
      setShowQuestionInput(true);
    }
  }, [isReplayMode, state.isGenerating, state.messages.length]);

  // Add scroll event listener to detect manual scrolling
  useEffect(() => {
    const messagesContainer = messagesEndRef.current?.parentElement;
    if (!messagesContainer) return;

    const handleScroll = () => {
      const isAtBottom =
        messagesContainer.scrollHeight -
          messagesContainer.scrollTop -
          messagesContainer.clientHeight <
        50;
      setUserHasScrolledUp(!isAtBottom);
    };

    messagesContainer.addEventListener("scroll", handleScroll);
    return () => messagesContainer.removeEventListener("scroll", handleScroll);
  }, [messagesEndRef]);

  // Replace the existing useEffect for message changes
  useEffect(() => {
    if (state.messages.length > 0 && !userHasScrolledUp) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [state.messages?.length, userHasScrolledUp]);

  const handleJumpToResult = () => {
    if (processAllEventsImmediately) {
      processAllEventsImmediately();
    }

    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      setShowQuestionInput(true);
    }, 100);
  };


  useEffect(() => {
    if (isReplayMode && showQuestionInput) {
      connectWebSocket();
    }
  }, [isReplayMode, showQuestionInput, connectWebSocket]);

  return (
    <div className="col-span-4">
      <motion.div
        className={`p-4 pt-0 w-full h-full ${
          isReplayMode && !showQuestionInput
            ? "max-h-[calc(100vh-182px)]"
            : pendingFilesCount > 0
            ? "max-h-[calc(100vh-330px)]"
            : "max-h-[calc(100vh-252px)]"
        } overflow-y-auto relative`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.3 }}
      >
        {state.messages
          .filter((message) => {
            // Only show messages that are meant for chat or have no component specified
            const dsMsg = message as DSAgentRunMessage;
            const component = dsMsg.metadata?.component;
            
            // Debug logging for planning messages
            if (dsMsg.metadata?.message_type === "planning_header" || 
                dsMsg.metadata?.message_type === "planning_content") {
              console.log(`[Planning Message]`, {
                message_type: dsMsg.metadata.message_type,
                planning_type: dsMsg.metadata.planning_type,
                content_preview: message.content?.substring(0, 50),
                step_number: dsMsg.step_number,
                full_metadata: dsMsg.metadata
              });
            }
            
            // Debug logging for thoughts
            if (dsMsg.metadata?.message_type === "action_thought") {
              console.log(`[Action Thought FILTER]`, {
                message_id: dsMsg.message_id,
                content: message.content,
                content_length: message.content?.length,
                metadata: dsMsg.metadata,
                component: component,
                willBeShown: !component || component === "chat"
              });
            }
            
            // Debug logging for final answers
            if (dsMsg.metadata?.message_type === "final_answer" || dsMsg.metadata?.is_final_answer) {
              console.log(`[Final Answer FILTER]`, {
                message_id: dsMsg.message_id,
                message_type: dsMsg.metadata?.message_type,
                is_final_answer: dsMsg.metadata?.is_final_answer,
                component: component,
                content_empty: !message.content || message.content === "",
                has_structured_data: dsMsg.metadata?.has_structured_data,
                willBeShown: !component || component === "chat",
                full_metadata: dsMsg.metadata
              });
            }
            
            // Explicitly exclude webide and terminal messages
            if (component === "webide" || component === "terminal") {
              return false;
            }
            
            // Include messages with no component or chat component
            return !component || component === "chat";
          })
          .map((message) => (
          <div
            key={message.message_id}
            className={`mb-4 ${
              message.role === "user" ? "text-right" : "text-left"
            } ${message.role === "user" && "mb-8"}`}
          >

            {(() => {
              const hasContent = !!message.content;
              const isPlanningHeader = (message as DSAgentRunMessage).metadata?.message_type === "planning_header";
              const isActionThought = (message as DSAgentRunMessage).metadata?.message_type === "action_thought";
              const isFinalAnswerMessage = (message as DSAgentRunMessage).metadata?.message_type === "final_answer" || (message as DSAgentRunMessage).metadata?.is_final_answer;
              const shouldRender = hasContent || isPlanningHeader || isActionThought || isFinalAnswerMessage;
              
              // Debug all assistant messages
              if (message.role === "assistant") {
                console.log("[RENDER CONDITION CHECK]", {
                  message_id: (message as DSAgentRunMessage).message_id,
                  message_type: (message as DSAgentRunMessage).metadata?.message_type,
                  hasContent,
                  isPlanningHeader,
                  isActionThought,
                  isFinalAnswerMessage,
                  shouldRender,
                  content: message.content?.substring(0, 50) || "EMPTY"
                });
              }
              
              return shouldRender;
            })() && (
              <div
                className={`inline-block text-left rounded-lg ${
                  message.role === "user"
                    ? "bg-[#35363a] p-3 max-w-[80%] text-white border border-[#3A3B3F] shadow-sm whitespace-pre-wrap"
                    : "text-white w-full"
                } ${
                  message.content?.startsWith("```Thinking:")
                    ? "agent-thinking w-full"
                    : ""
                } ${
                  message.metadata?.message_type === "planning_header"
                    ? "font-semibold text-blue-400 w-full"
                    : ""
                }`}
              >
                {message.role === "user" ? (
                  <div className="text-left">{message.content}</div>
                ) : (
                  renderAssistantMessage(message)
                )}
              </div>
            )}

          </div>
        ))}

        {state.isGenerating && (
          <motion.div
            className="mb-4 text-left"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 30,
            }}
          >
            <motion.div
              className="inline-block p-3 text-left rounded-lg bg-neutral-800/90 text-white backdrop-blur-sm"
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              transition={{
                type: "spring",
                stiffness: 400,
                damping: 25,
              }}
            >
              <div className="flex items-center gap-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-white rounded-full animate-[dot-bounce_1.2s_ease-in-out_infinite_0ms]" />
                  <div className="w-2 h-2 bg-white rounded-full animate-[dot-bounce_1.2s_ease-in-out_infinite_200ms]" />
                  <div className="w-2 h-2 bg-white rounded-full animate-[dot-bounce_1.2s_ease-in-out_infinite_400ms]" />
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}

        {state.isCompleted && (
          <div className="flex flex-col gap-y-4">
            <div className="flex gap-x-2 items-center bg-[#25BA3B1E] text-green-600 text-sm p-2 rounded-full">
              <div className="flex gap-x-2 items-center">
                <Check className="size-4" />
                <span>Agent has completed the current task.</span>
              </div>
            </div>
          </div>
        )}


        <div ref={messagesEndRef} />
      </motion.div>
      {isReplayMode ? (
        showQuestionInput ? (
          <QuestionInput
            hideSettings
            className="px-4 w-full max-w-none"
            textareaClassName="min-h-40 h-40 w-full"
            placeholder="Ask me anything..."
            value={state.currentQuestion}
            setValue={setCurrentQuestion}
            handleKeyDown={handleKeyDown}
            handleSubmit={handleQuestionSubmit}
            handleEnhancePrompt={handleEnhancePrompt}
            handleCancel={handleCancel}
            onFilesChange={handleFilesChange}
          />
        ) : (
          <motion.div
            className="sticky bottom-0 left-0 w-full p-4 pb-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.3 }}
          >
            <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl p-3 flex items-center justify-between">
              <div className="flex items-center gap-2 ml-2">
                <div className="animate-pulse">
                  <div className="h-2 w-2 bg-white rounded-full"></div>
                </div>
                <span className="text-white">
                  Agent is replaying the task...
                </span>
              </div>
              <div className="flex gap-2">
                <DSButton
                  variant="secondary"
                  className="cursor-pointer"
                  onClick={handleJumpToResult}
                >
                  <SkipForward /> Skip to results
                </DSButton>
              </div>
            </div>
          </motion.div>
        )
      ) : (
        <motion.div
          className="sticky bottom-0 left-0 w-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.3 }}
        >
          <QuestionInput
            hideSettings
            className="p-4 pb-0 w-full max-w-none"
            textareaClassName="min-h-40 h-40 w-full"
            placeholder="Ask me anything..."
            value={state.currentQuestion}
            setValue={setCurrentQuestion}
            handleKeyDown={handleKeyDown}
            handleSubmit={handleQuestionSubmit}
            handleEnhancePrompt={handleEnhancePrompt}
            handleCancel={handleCancel}
            onFilesChange={handleFilesChange}
          />
        </motion.div>
      )}
    </div>
  );
};

export default ChatMessage;
