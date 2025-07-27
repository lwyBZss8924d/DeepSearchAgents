"use client";

import { useState, useEffect } from "react";
import { useAppContext } from "@/context/app-context";
import { ChevronDown, ChevronRight, Eye, EyeOff, Bug } from "lucide-react";
import { DSAgentRunMessage } from "@/types/api.types";

export default function DebugPanel() {
  const { state } = useAppContext();
  const [isExpanded, setIsExpanded] = useState(false);
  const [showContent, setShowContent] = useState(true);
  const [filter, setFilter] = useState<"all" | "planning" | "streaming">("all");
  const [autoScroll, setAutoScroll] = useState(true);

  // Filter messages based on selected filter
  const filteredMessages = state.messages.filter(msg => {
    if (filter === "all") return true;
    if (filter === "planning") {
      return msg.metadata?.event_type === "planning" || 
             msg.metadata?.title?.toLowerCase().includes("planning") ||
             msg.content?.includes("Planning step");
    }
    if (filter === "streaming") {
      return msg.metadata?.streaming === true;
    }
    return true;
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && isExpanded) {
      const panel = document.getElementById("debug-messages");
      if (panel) {
        panel.scrollTop = panel.scrollHeight;
      }
    }
  }, [state.messages, isExpanded, autoScroll]);

  // Calculate stats
  const stats = {
    total: state.messages.length,
    planning: state.messages.filter(m => 
      m.metadata?.event_type === "planning" || 
      m.content?.includes("Planning step")
    ).length,
    streaming: state.messages.filter(m => m.metadata?.streaming === true).length,
    empty: state.messages.filter(m => !m.content || m.content.trim() === "").length
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-2xl">
      {/* Toggle Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg shadow-lg transition-all"
      >
        <Bug className="w-4 h-4" />
        <span>Debug Panel</span>
        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        <span className="bg-orange-800 px-2 py-1 rounded text-xs">
          {stats.total} msgs
        </span>
      </button>

      {/* Expanded Panel */}
      {isExpanded && (
        <div className="mt-2 bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="bg-gray-800 p-3 border-b border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-white font-semibold">Message Debug View</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowContent(!showContent)}
                  className="text-gray-400 hover:text-white transition-colors"
                  title={showContent ? "Hide content" : "Show content"}
                >
                  {showContent ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                </button>
                <label className="flex items-center gap-1 text-xs text-gray-400">
                  <input
                    type="checkbox"
                    checked={autoScroll}
                    onChange={(e) => setAutoScroll(e.target.checked)}
                    className="rounded"
                  />
                  Auto-scroll
                </label>
              </div>
            </div>

            {/* Stats */}
            <div className="flex gap-4 text-xs">
              <span className="text-gray-400">
                Total: <span className="text-white font-mono">{stats.total}</span>
              </span>
              <span className="text-yellow-400">
                Planning: <span className="text-white font-mono">{stats.planning}</span>
              </span>
              <span className="text-blue-400">
                Streaming: <span className="text-white font-mono">{stats.streaming}</span>
              </span>
              <span className="text-red-400">
                Empty: <span className="text-white font-mono">{stats.empty}</span>
              </span>
            </div>

            {/* Filters */}
            <div className="flex gap-2 mt-2">
              <button
                onClick={() => setFilter("all")}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  filter === "all" 
                    ? "bg-blue-600 text-white" 
                    : "bg-gray-700 text-gray-400 hover:text-white"
                }`}
              >
                All ({stats.total})
              </button>
              <button
                onClick={() => setFilter("planning")}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  filter === "planning" 
                    ? "bg-yellow-600 text-white" 
                    : "bg-gray-700 text-gray-400 hover:text-white"
                }`}
              >
                Planning ({stats.planning})
              </button>
              <button
                onClick={() => setFilter("streaming")}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  filter === "streaming" 
                    ? "bg-blue-600 text-white" 
                    : "bg-gray-700 text-gray-400 hover:text-white"
                }`}
              >
                Streaming ({stats.streaming})
              </button>
            </div>
          </div>

          {/* Messages */}
          <div 
            id="debug-messages"
            className="max-h-96 overflow-y-auto p-2 space-y-2"
          >
            {filteredMessages.length === 0 ? (
              <div className="text-gray-500 text-center py-4">
                No messages matching filter
              </div>
            ) : (
              filteredMessages.map((message, index) => (
                <MessageDebugItem 
                  key={message.message_id || index} 
                  message={message} 
                  showContent={showContent}
                  index={index}
                  messages={filteredMessages}
                />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MessageDebugItem({ 
  message, 
  showContent, 
  index,
  messages 
}: { 
  message: DSAgentRunMessage; 
  showContent: boolean;
  index: number;
  messages: DSAgentRunMessage[];
}) {
  const isPlanning = message.metadata?.event_type === "planning" || 
                    message.content?.includes("Planning step");
  const isStreaming = message.metadata?.streaming === true;
  const isEmpty = !message.content || message.content.trim() === "";
  
  // Extract message key from ID for debugging
  const messageKey = message.message_id?.match(/msg-(\d+)-([^-]+)/)?.[0] || "unknown";
  const messageTypeMatch = message.message_id?.match(/msg-\d+-([^-]+)(?:-seq\d+)?/);
  const messageType = messageTypeMatch?.[1] || "unknown";
  const isReplacement = messages.filter(m => 
    m.message_id?.startsWith(messageKey.split('-seq')[0]) && 
    m !== message
  ).length > 0;
  
  return (
    <div 
      className={`text-xs font-mono p-2 rounded border ${
        isEmpty 
          ? "bg-red-900/20 border-red-700" 
          : isPlanning 
          ? "bg-yellow-900/20 border-yellow-700"
          : isStreaming
          ? "bg-blue-900/20 border-blue-700"
          : "bg-gray-800 border-gray-700"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-gray-500">#{index}</span>
          <span className="text-blue-400" title={message.message_id}>
            {messageKey}
          </span>
          <span className="text-gray-500">Step {message.step_number || 0}</span>
          <span className={`px-1 py-0.5 rounded text-xs ${
            message.role === "user" ? "bg-blue-600" : "bg-green-600"
          }`}>
            {message.role}
          </span>
          {isReplacement && (
            <span className="px-1 py-0.5 bg-yellow-600 rounded text-xs" title="Message with same key exists">
              DUP KEY
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {isPlanning && (
            <span className="px-1 py-0.5 bg-yellow-600 rounded text-xs">
              PLAN
            </span>
          )}
          {isStreaming && (
            <span className="px-1 py-0.5 bg-blue-600 rounded text-xs animate-pulse">
              STREAM
            </span>
          )}
          {isEmpty && (
            <span className="px-1 py-0.5 bg-red-600 rounded text-xs">
              EMPTY
            </span>
          )}
          {messageType !== "unknown" && (
            <span className="px-1 py-0.5 bg-purple-600 rounded text-xs" title="Message type">
              {messageType}
            </span>
          )}
        </div>
      </div>

      {/* Metadata */}
      {message.metadata && Object.keys(message.metadata).length > 0 && (
        <div className="text-gray-400 mb-1">
          metadata: {JSON.stringify(message.metadata, null, 2).substring(0, 100)}
          {JSON.stringify(message.metadata).length > 100 && "..."}
        </div>
      )}

      {/* Content */}
      {showContent && (
        <div className={`mt-1 ${isEmpty ? "text-red-400" : "text-gray-300"}`}>
          {isEmpty ? (
            "<empty content>"
          ) : (
            <>
              content ({message.content.length} chars): 
              <span className="text-white">
                {message.content.substring(0, 150)}
                {message.content.length > 150 && "..."}
              </span>
            </>
          )}
        </div>
      )}

      {/* Timestamp */}
      {message.timestamp && (
        <div className="text-gray-500 mt-1">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}