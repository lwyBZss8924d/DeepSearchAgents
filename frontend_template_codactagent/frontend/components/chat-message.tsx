"use client";

import { motion } from "framer-motion";
import {
  Check,
  CircleStop,
  Pencil,
  Folder,
  SkipForward,
  SearchCheck,
} from "lucide-react";
import { useState, useEffect } from "react";

import Action from "@/components/action";
import Markdown from "@/components/markdown";
import QuestionInput from "@/components/question-input";
import { ActionStep, Message } from "@/typings/agent";
import { getFileIconAndColor } from "@/utils/file-utils";
import { Button } from "./ui/button";
import EditQuestion from "./edit-question";
import { useAppContext } from "@/context/app-context";

interface ChatMessageProps {
  isReplayMode: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  handleClickAction: (
    data: ActionStep | undefined,
    showTabOnly?: boolean
  ) => void;
  setCurrentQuestion: (value: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  handleQuestionSubmit: (question: string) => void;
  handleEnhancePrompt: () => void;
  handleCancel: () => void;
  handleEditMessage: (newQuestion: string) => void;
  processAllEventsImmediately?: () => void;
  connectWebSocket: () => void;
  handleReviewSession: () => void;
}

const ChatMessage = ({
  messagesEndRef,
  isReplayMode,
  handleClickAction,
  setCurrentQuestion,
  handleKeyDown,
  handleQuestionSubmit,
  handleEnhancePrompt,
  handleCancel,
  handleEditMessage,
  processAllEventsImmediately,
  connectWebSocket,
  handleReviewSession,
}: ChatMessageProps) => {
  const { state, dispatch } = useAppContext();
  const [showQuestionInput, setShowQuestionInput] = useState(false);
  const [pendingFilesCount, setPendingFilesCount] = useState(0);
  const [userHasScrolledUp, setUserHasScrolledUp] = useState(false);

  const handleFilesChange = (count: number) => {
    setPendingFilesCount(count);
  };

  useEffect(() => {
    if (isReplayMode && !state.isLoading && state.messages.length > 0) {
      // If we're in replay mode, loading is complete, and we have messages,
      // we can assume all events have been processed
      setShowQuestionInput(true);
    }
  }, [isReplayMode, state.isLoading, state.messages.length]);

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

  // Helper function to check if a message is the latest user message
  const isLatestUserMessage = (
    message: Message,
    allMessages: Message[]
  ): boolean => {
    const userMessages = allMessages.filter((msg) => msg.role === "user");
    return (
      userMessages.length > 0 &&
      userMessages[userMessages.length - 1].id === message.id
    );
  };

  const handleSetEditingMessage = (message?: Message) => {
    dispatch({ type: "SET_EDITING_MESSAGE", payload: message });
  };

  useEffect(() => {
    if (isReplayMode && showQuestionInput) {
      connectWebSocket();
    }
  }, [isReplayMode, showQuestionInput]);

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
        {state.messages.map((message) => (
          <div
            key={message.id}
            className={`mb-4 ${
              message.role === "user" ? "text-right" : "text-left"
            } ${message.role === "user" && !message.files && "mb-8"} ${
              message.isHidden ? "hidden" : ""
            }`}
          >
            {message.files && message.files.length > 0 && (
              <div className="flex flex-col gap-2 mb-2">
                {(() => {
                  // First, identify any folders in the files array
                  const folderFiles = message.files.filter((fileName) =>
                    fileName.match(/^folder:(.+):(\d+)$/)
                  );

                  // Extract folder names for filtering
                  const folderNames = folderFiles
                    .map((folderFile) => {
                      const match = folderFile.match(/^folder:(.+):(\d+)$/);
                      return match ? match[1] : null;
                    })
                    .filter(Boolean) as string[];

                  // Create a list of files to display:
                  // 1. Include all folder entries
                  // 2. Only include individual files that are NOT part of any folder
                  const filesToDisplay = message.files.filter((fileName) => {
                    // If it's a folder entry, always include it
                    if (fileName.match(/^folder:(.+):(\d+)$/)) {
                      return true;
                    }

                    // For regular files, exclude them if they might be part of a folder
                    // This is a simple heuristic that checks if the filename contains any folder name
                    for (const folderName of folderNames) {
                      // If the file appears to be from a Google Drive folder, exclude it
                      if (fileName.includes(folderName)) {
                        return false;
                      }
                    }

                    // Include all other files (they're not part of folders)
                    return true;
                  });

                  return filesToDisplay.map((fileName, fileIndex) => {
                    // Check if the file is a folder
                    const isFolderMatch = fileName.match(/^folder:(.+):(\d+)$/);
                    if (isFolderMatch) {
                      const folderName = isFolderMatch[1];
                      const fileCount = parseInt(isFolderMatch[2], 10);

                      return (
                        <div
                          key={`${message.id}-folder-${fileIndex}`}
                          className="inline-block ml-auto bg-[#35363a] text-white rounded-2xl px-4 py-3 border border-gray-700 shadow-sm"
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex items-center justify-center w-12 h-12 bg-blue-600 rounded-xl">
                              <Folder className="size-6 text-white" />
                            </div>
                            <div className="flex flex-col">
                              <span className="text-base font-medium">
                                {folderName}
                              </span>
                              <span className="text-left text-sm text-gray-500">
                                {fileCount} {fileCount === 1 ? "file" : "files"}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    }

                    // Handle regular files as before
                    // Check if the file is an image
                    const isImage =
                      fileName.match(
                        /\.(jpeg|jpg|gif|png|webp|svg|heic|bmp)$/i
                      ) !== null;

                    if (
                      isImage &&
                      message.fileContents &&
                      message.fileContents[fileName]
                    ) {
                      return (
                        <div
                          key={`${message.id}-file-${fileIndex}`}
                          className="inline-block ml-auto rounded-3xl overflow-hidden max-w-[320px]"
                        >
                          <div className="w-40 h-40 rounded-xl overflow-hidden">
                            <img
                              src={message.fileContents[fileName]}
                              alt={fileName}
                              className="w-full h-full object-cover"
                            />
                          </div>
                        </div>
                      );
                    }

                    // For non-image files, use the existing code
                    const { IconComponent, bgColor, label } =
                      getFileIconAndColor(fileName);

                    return (
                      <div
                        key={`${message.id}-file-${fileIndex}`}
                        className="inline-block ml-auto bg-[#35363a] text-white rounded-2xl px-4 py-3 border border-gray-700 shadow-sm"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={`flex items-center justify-center w-12 h-12 ${bgColor} rounded-xl`}
                          >
                            <IconComponent className="size-6 text-white" />
                          </div>
                          <div className="flex flex-col">
                            <span className="text-base font-medium">
                              {fileName}
                            </span>
                            <span className="text-left text-sm text-gray-500">
                              {label}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
            )}

            {message.content && (
              <div
                className={`inline-block text-left rounded-lg ${
                  message.role === "user"
                    ? "bg-[#35363a] p-3 max-w-[80%] text-white border border-[#3A3B3F] shadow-sm whitespace-pre-wrap"
                    : "text-white"
                } ${
                  state.editingMessage?.id === message.id
                    ? "w-full max-w-none"
                    : ""
                } ${
                  message.content?.startsWith("```Thinking:")
                    ? "agent-thinking w-full"
                    : ""
                }`}
              >
                {message.role === "user" ? (
                  <div>
                    {state.editingMessage?.id === message.id ? (
                      <EditQuestion
                        editingMessage={message.content}
                        handleCancel={() => handleSetEditingMessage(undefined)}
                        handleEditMessage={handleEditMessage}
                      />
                    ) : (
                      <div className="relative group">
                        <div className="text-left">{message.content}</div>
                        {isLatestUserMessage(message, state.messages) &&
                          !isReplayMode && (
                            <div className="absolute -bottom-[45px] -right-[20px] opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-xs cursor-pointer hover:!bg-transparent"
                                onClick={() => {
                                  handleSetEditingMessage(message);
                                }}
                              >
                                <Pencil className="size-3 mr-1" />
                              </Button>
                            </div>
                          )}
                      </div>
                    )}
                  </div>
                ) : (
                  <Markdown>{message.content}</Markdown>
                )}
              </div>
            )}

            {message.action && (
              <div className="mt-2">
                <Action
                  workspaceInfo={state.workspaceInfo}
                  type={message.action.type}
                  value={message.action.data}
                  onClick={() => handleClickAction(message.action, true)}
                />
              </div>
            )}
          </div>
        ))}

        {state.isLoading && (
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
                <span>II-Agent has completed the current task.</span>
              </div>
            </div>
            {state.toolSettings?.enable_reviewer && (
              <div
                className={`group cursor-pointer flex items-start gap-2 px-3 py-2 bg-[#35363a] rounded-xl backdrop-blur-sm 
      shadow-sm
      transition-all duration-200 ease-out
      hover:shadow-[0_2px_8px_rgba(0,0,0,0.24)]
      active:scale-[0.98] overflow-hidden
      animate-fadeIn`}
              >
                <div className="flex text-sm items-center justify-between flex-1">
                  <div className="flex items-center gap-x-1.5 flex-1">
                    <SearchCheck className="size-5 text-white" />
                    <span className="text-neutral-100 flex-1 font-medium group-hover:text-white">
                      Allow II-Agent to review the results
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="cursor-pointer text-neutral-900 bg-gradient-skyblue-lavender hover:text-neutral-950"
                    onClick={handleReviewSession}
                  >
                    Review
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {state.isStopped && (
          <div className="flex gap-x-2 items-center bg-[#ffbf361f] text-yellow-300 text-sm p-2 rounded-full">
            <CircleStop className="size-4" />
            <span>II-Agent has stopped, send a new message to continue.</span>
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
                  II-Agent is replaying the task...
                </span>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="cursor-pointer"
                  onClick={handleJumpToResult}
                >
                  <SkipForward /> Skip to results
                </Button>
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
