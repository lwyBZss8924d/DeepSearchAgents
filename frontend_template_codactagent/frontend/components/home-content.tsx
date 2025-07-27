"use client";

import { Terminal as XTerm } from "@xterm/xterm";
import { AnimatePresence, LayoutGroup, motion } from "framer-motion";
import {
  Code,
  Globe,
  Terminal as TerminalIcon,
  X,
  Share,
  Loader2,
} from "lucide-react";
import Image from "next/image";
import { useMemo, useRef, useCallback } from "react";
import { toast } from "sonner";
import dynamic from "next/dynamic";
import { Kumbh_Sans } from "next/font/google";
import { useSearchParams } from "next/navigation";

import { useDeviceId } from "@/hooks/use-device-id";
import { useWebSocket } from "@/hooks/use-websocket";
import { useSessionManager } from "@/hooks/use-session-manager";
import { useAppEvents } from "@/hooks/use-app-events";
import { useAppContext } from "@/context/app-context";

import SidebarButton from "@/components/sidebar-button";
import ConnectionStatus from "@/components/connection-status";
import Browser from "@/components/browser";
import CodeEditor from "@/components/code-editor";
import QuestionInput from "@/components/question-input";
import SearchBrowser from "@/components/search-browser";
import { Button } from "@/components/ui/button";
import ChatMessage from "@/components/chat-message";
import ImageBrowser from "@/components/image-browser";
import { Message, TAB, TOOL } from "@/typings/agent";

const Terminal = dynamic(() => import("@/components/terminal"), {
  ssr: false,
});

const kumbh_sans = Kumbh_Sans({
  subsets: ["latin"],
});

export default function HomeContent() {
  const xtermRef = useRef<XTerm | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { state, dispatch } = useAppContext();
  const { handleEvent, handleClickAction } = useAppEvents({ xtermRef });
  const searchParams = useSearchParams();

  const { deviceId } = useDeviceId();

  // Use the Session Manager hook
  const {
    sessionId,
    isLoadingSession,
    isReplayMode,
    setSessionId,
    processAllEventsImmediately,
  } = useSessionManager({
    searchParams,
    handleEvent,
  });

  // Use the WebSocket hook
  const { socket, sendMessage, connectWebSocket } = useWebSocket(
    deviceId,
    isReplayMode,
    handleEvent
  );

  const handleEnhancePrompt = () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      toast.error("WebSocket connection is not open. Please try again.");
      return;
    }
    dispatch({ type: "SET_GENERATING_PROMPT", payload: true });
    sendMessage({
      type: "enhance_prompt",
      content: {
        model_name: state.selectedModel,
        text: state.currentQuestion,
        files: state.uploadedFiles?.map((file) => `.${file}`),
        tool_args: {
          thinking_tokens: 0,
        },
      },
    });
  };

  const handleQuestionSubmit = async (newQuestion: string) => {
    if (!newQuestion.trim() || state.isLoading) return;

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      toast.error("WebSocket connection is not open. Please try again.");
      dispatch({ type: "SET_LOADING", payload: false });
      return;
    }

    dispatch({ type: "SET_REQUIRE_CLEAR_FILES", payload: true });
    dispatch({ type: "SET_LOADING", payload: true });
    dispatch({ type: "SET_CURRENT_QUESTION", payload: "" });
    dispatch({ type: "SET_COMPLETED", payload: false });
    dispatch({ type: "SET_STOPPED", payload: false });

    if (!sessionId) {
      const id = `${state.workspaceInfo}`.split("/").pop();
      if (id) {
        setSessionId(id);
      }
    }

    // Show all hidden messages
    state.messages.forEach((message) => {
      if (message.isHidden) {
        dispatch({
          type: "UPDATE_MESSAGE",
          payload: { ...message, isHidden: false },
        });
      }
    });

    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: newQuestion,
      timestamp: Date.now(),
    };

    dispatch({
      type: "ADD_MESSAGE",
      payload: newUserMessage,
    });

    const { thinking_tokens, ...tool_args } = state.toolSettings;

    // Only send init_agent event if agent is not already initialized
    if (!state.isAgentInitialized) {
      sendMessage({
        type: "init_agent",
        content: {
          model_name: state.selectedModel,
          tool_args,
          thinking_tokens,
        },
      });
    }

    // Send the query using the existing socket connection
    sendMessage({
      type: "query",
      content: {
        text: newQuestion,
        resume: state.messages.length > 0,
        files: state.uploadedFiles?.map((file) => `.${file}`),
      },
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQuestionSubmit((e.target as HTMLTextAreaElement).value);
    }
  };

  const handleResetChat = () => {
    window.location.href = "/";
  };

  const handleOpenVSCode = () => {
    if (!sessionId) {
      toast.error("Session not available. Please try again.");
      return;
    }

    // const url = `http://${sessionId}-9000.${process.env.NEXT_PUBLIC_VSCODE_URL}`;
    if (!state.vscodeUrl) {
      toast.error("VS Code URL not available. Please try again.");
      return;
    }
    const url = state.vscodeUrl;
    window.open(url, "_blank");
  };

  const parseJson = (jsonString: string) => {
    try {
      return JSON.parse(jsonString);
    } catch {
      return null;
    }
  };

  const handleReviewResult = () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      toast.error("WebSocket connection is not open. Please try again.");
      dispatch({ type: "SET_LOADING", payload: false });
      return;
    }
    const { thinking_tokens, ...tool_args } = state.toolSettings;

    dispatch({ type: "SET_LOADING", payload: true });
    dispatch({ type: "SET_COMPLETED", payload: false });

    // Only send init_agent event if agent is not already initialized
    if (!state.isAgentInitialized) {
      sendMessage({
        type: "init_agent",
        content: {
          model_name: state.selectedModel,
          tool_args,
          thinking_tokens,
        },
      });
    }

    // Find the last user message
    const userMessages = state.messages.filter((msg) => msg.role === "user");
    const lastUserMessage =
      userMessages.length > 0
        ? userMessages[userMessages.length - 1].content
        : "";

    sendMessage({
      type: "review_result",
      content: {
        user_input: lastUserMessage,
      },
    });
  };

  const handleEditMessage = (newQuestion: string) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      toast.error("WebSocket connection is not open. Please try again.");
      dispatch({ type: "SET_LOADING", payload: false });
      return;
    }

    socket.send(
      JSON.stringify({
        type: "edit_query",
        content: {
          text: newQuestion,
          files: state.uploadedFiles?.map((file) => `.${file}`),
        },
      })
    );

    // Update the edited message and remove all subsequent messages
    const editIndex = state.messages.findIndex(
      (m) => m.id === state.editingMessage?.id
    );

    if (editIndex >= 0) {
      const updatedMessages = [...state.messages.slice(0, editIndex + 1)];
      updatedMessages[editIndex] = {
        ...updatedMessages[editIndex],
        content: newQuestion,
      };

      dispatch({
        type: "SET_MESSAGES",
        payload: updatedMessages,
      });
    }

    dispatch({ type: "SET_COMPLETED", payload: false });
    dispatch({ type: "SET_STOPPED", payload: false });
    dispatch({ type: "SET_LOADING", payload: true });
    dispatch({ type: "SET_EDITING_MESSAGE", payload: undefined });
  };

  const getRemoteURL = useCallback(
    (path: string | undefined) => {
      if (!path || !state.workspaceInfo) return "";
      const workspaceId = state.workspaceInfo.split("/").pop();
      return `${process.env.NEXT_PUBLIC_API_URL}/workspace/${workspaceId}/${path}`;
    },
    [state.workspaceInfo]
  );

  const isInChatView = useMemo(
    () => !!sessionId && !isLoadingSession,
    [isLoadingSession, sessionId]
  );

  const handleShare = () => {
    if (!sessionId) return;
    const url = `${window.location.origin}/?id=${sessionId}`;
    navigator.clipboard.writeText(url);
    toast.success("Copied to clipboard");
  };

  const handleCancelQuery = () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      toast.error("WebSocket connection is not open.");
      return;
    }

    // Send cancel message to the server
    socket.send(
      JSON.stringify({
        type: "cancel",
        content: {},
      })
    );
    dispatch({ type: "SET_LOADING", payload: false });
    dispatch({ type: "SET_STOPPED", payload: true });
  };

  const isBrowserTool = useMemo(
    () =>
      [
        TOOL.BROWSER_VIEW,
        TOOL.BROWSER_CLICK,
        TOOL.BROWSER_ENTER_TEXT,
        TOOL.BROWSER_PRESS_KEY,
        TOOL.BROWSER_GET_SELECT_OPTIONS,
        TOOL.BROWSER_SELECT_DROPDOWN_OPTION,
        TOOL.BROWSER_SWITCH_TAB,
        TOOL.BROWSER_OPEN_NEW_TAB,
        TOOL.BROWSER_WAIT,
        TOOL.BROWSER_SCROLL_DOWN,
        TOOL.BROWSER_SCROLL_UP,
        TOOL.BROWSER_NAVIGATION,
        TOOL.BROWSER_RESTART,
      ].includes(state.currentActionData?.type as TOOL),
    [state.currentActionData]
  );

  const browserProps = useMemo(
    () => ({
      className:
        state.activeTab === TAB.BROWSER &&
        (state.currentActionData?.type === TOOL.VISIT || isBrowserTool)
          ? ""
          : "hidden",
      url: state.currentActionData?.data?.tool_input?.url || state.browserUrl,
      screenshot: isBrowserTool
        ? (state.currentActionData?.data.result as string)
        : undefined,
      raw:
        state.currentActionData?.type === TOOL.VISIT
          ? (state.currentActionData?.data?.result as string)
          : undefined,
    }),
    [state.activeTab, state.currentActionData, state.browserUrl, isBrowserTool]
  );

  const searchBrowserProps = useMemo(
    () => ({
      className:
        state.activeTab === TAB.BROWSER &&
        state.currentActionData?.type === TOOL.WEB_SEARCH
          ? ""
          : "hidden",
      keyword: state.currentActionData?.data.tool_input?.query,
      search_results:
        state.currentActionData?.type === TOOL.WEB_SEARCH &&
        state.currentActionData?.data?.result
          ? parseJson(state.currentActionData?.data?.result as string)
          : undefined,
    }),
    [state.activeTab, state.currentActionData]
  );

  const imageBrowserProps = useMemo(
    () => ({
      className:
        (state.activeTab === TAB.BROWSER &&
          state.currentActionData?.type === TOOL.IMAGE_GENERATE) ||
        state.currentActionData?.type === TOOL.IMAGE_SEARCH
          ? ""
          : "hidden",
      url:
        state.currentActionData?.data.tool_input?.output_filename ||
        state.currentActionData?.data.tool_input?.query,
      images:
        state.currentActionData?.type === TOOL.IMAGE_SEARCH
          ? parseJson(state.currentActionData?.data?.result as string)?.map(
              (item: { image_url: string }) => item?.image_url
            )
          : [
              getRemoteURL(
                state.currentActionData?.data.tool_input?.output_filename
              ),
            ],
    }),
    [state.activeTab, state.currentActionData, getRemoteURL]
  );

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#191E1B]">
      <SidebarButton />
      {!isInChatView && (
        <Image
          src="/logo-only.png"
          alt="II-Agent Logo"
          width={80}
          height={80}
          className="rounded-sm"
        />
      )}
      <div
        className={`flex justify-between w-full ${
          !isInChatView ? "pt-0 pb-8" : "p-4"
        }`}
      >
        {!isInChatView && <div />}
        <motion.h1
          className={`font-semibold text-center ${
            isInChatView ? "flex items-center gap-x-2 text-2xl" : "text-4xl"
          } ${kumbh_sans.className}`}
          layout
          layoutId="page-title"
        >
          {isInChatView && (
            <Image
              src="/logo-only.png"
              alt="II-Agent Logo"
              width={40}
              height={40}
              className="rounded-sm"
            />
          )}
          {`II-Agent`}
        </motion.h1>
        {isInChatView && isReplayMode ? (
          <div className="flex gap-x-2">
            <Button
              className="cursor-pointer h-10"
              variant="outline"
              onClick={handleShare}
            >
              <Share /> Share
            </Button>
            <Button className="cursor-pointer" onClick={handleResetChat}>
              <X className="size-5" />
            </Button>
          </div>
        ) : isInChatView ? (
          <div className="flex gap-x-2">
            <Button
              className="cursor-pointer h-10"
              variant="outline"
              onClick={handleShare}
            >
              <Share /> Share
            </Button>
            <Button className="cursor-pointer" onClick={handleResetChat}>
              <X className="size-5" />
            </Button>
          </div>
        ) : (
          <div />
        )}
      </div>
      {isLoadingSession ? (
        <div className="flex flex-col items-center justify-center p-8">
          <Loader2 className="h-8 w-8 text-white animate-spin mb-4" />
          <p className="text-white text-lg">Loading session history...</p>
        </div>
      ) : (
        <LayoutGroup>
          <AnimatePresence mode="wait">
            {!isInChatView ? (
              <QuestionInput
                placeholder="Give II-Agent a task to work on..."
                value={state.currentQuestion}
                setValue={(value) =>
                  dispatch({ type: "SET_CURRENT_QUESTION", payload: value })
                }
                handleKeyDown={handleKeyDown}
                handleSubmit={handleQuestionSubmit}
                isDisabled={!socket || socket.readyState !== WebSocket.OPEN}
                handleEnhancePrompt={handleEnhancePrompt}
              />
            ) : (
              <motion.div
                key="chat-view"
                initial={{ opacity: 0, y: 30, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -20, scale: 0.95 }}
                transition={{
                  type: "spring",
                  stiffness: 300,
                  damping: 30,
                  mass: 1,
                }}
                className="w-full grid grid-cols-10 write-report overflow-hidden flex-1 pr-4 pb-4 "
              >
                <ChatMessage
                  handleClickAction={handleClickAction}
                  isReplayMode={isReplayMode}
                  messagesEndRef={messagesEndRef}
                  setCurrentQuestion={(value) =>
                    dispatch({ type: "SET_CURRENT_QUESTION", payload: value })
                  }
                  handleKeyDown={handleKeyDown}
                  handleQuestionSubmit={handleQuestionSubmit}
                  handleEnhancePrompt={handleEnhancePrompt}
                  handleCancel={handleCancelQuery}
                  handleEditMessage={handleEditMessage}
                  processAllEventsImmediately={processAllEventsImmediately}
                  connectWebSocket={connectWebSocket}
                  handleReviewSession={handleReviewResult}
                />

                <div className="col-span-6 bg-[#1e1f23] border border-[#3A3B3F] p-4 rounded-2xl">
                  <div className="pb-4 bg-neutral-850 flex items-center justify-between">
                    <div className="flex gap-x-4">
                      <Button
                        className={`cursor-pointer hover:!bg-black ${
                          state.activeTab === TAB.BROWSER
                            ? "bg-gradient-skyblue-lavender !text-black"
                            : ""
                        }`}
                        variant="outline"
                        onClick={() =>
                          dispatch({
                            type: "SET_ACTIVE_TAB",
                            payload: TAB.BROWSER,
                          })
                        }
                      >
                        <Globe className="size-4" /> Browser
                      </Button>
                      <Button
                        className={`cursor-pointer hover:!bg-black ${
                          state.activeTab === TAB.CODE
                            ? "bg-gradient-skyblue-lavender !text-black"
                            : ""
                        }`}
                        variant="outline"
                        onClick={() =>
                          dispatch({
                            type: "SET_ACTIVE_TAB",
                            payload: TAB.CODE,
                          })
                        }
                      >
                        <Code className="size-4" /> Code
                      </Button>
                      <Button
                        className={`cursor-pointer hover:!bg-black ${
                          state.activeTab === TAB.TERMINAL
                            ? "bg-gradient-skyblue-lavender !text-black"
                            : ""
                        }`}
                        variant="outline"
                        onClick={() =>
                          dispatch({
                            type: "SET_ACTIVE_TAB",
                            payload: TAB.TERMINAL,
                          })
                        }
                      >
                        <TerminalIcon className="size-4" /> Terminal
                      </Button>
                    </div>
                    <Button
                      className="cursor-pointer"
                      variant="outline"
                      onClick={handleOpenVSCode}
                    >
                      <Image
                        src={"/vscode.png"}
                        alt="VS Code"
                        width={20}
                        height={20}
                      />{" "}
                      Open with VS Code
                    </Button>
                  </div>
                  <Browser {...browserProps} />
                  <SearchBrowser {...searchBrowserProps} />
                  <ImageBrowser {...imageBrowserProps} />
                  <CodeEditor
                    currentActionData={state.currentActionData}
                    activeTab={state.activeTab}
                    className={state.activeTab === TAB.CODE ? "" : "hidden"}
                    workspaceInfo={state.workspaceInfo}
                    activeFile={state.activeFileCodeEditor}
                    setActiveFile={(file) =>
                      dispatch({
                        type: "SET_ACTIVE_FILE",
                        payload: file,
                      })
                    }
                    filesContent={state.filesContent}
                    isReplayMode={isReplayMode}
                  />
                  <Terminal
                    ref={xtermRef}
                    className={state.activeTab === TAB.TERMINAL ? "" : "hidden"}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </LayoutGroup>
      )}
      {!isInChatView && <ConnectionStatus />}
    </div>
  );
}
