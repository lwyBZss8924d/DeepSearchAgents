"use client";

import { motion } from "framer-motion";
import { 
  Wrench, 
  Code2, 
  Search, 
  FileText, 
  Globe,
  Calculator,
  CheckCircle 
} from "lucide-react";

interface ToolCallBadgeProps {
  toolName: string;
  toolId?: string;
  argsSummary?: string;
  isPythonInterpreter?: boolean;
  className?: string;
}

// Map tool names to icons
const toolIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  python_interpreter: Code2,
  search: Search,
  readurl: Globe,
  chunk: FileText,
  embed: FileText,
  rerank: FileText,
  wolfram: Calculator,
  final_answer: CheckCircle,
};

export default function ToolCallBadge({
  toolName,
  argsSummary,
  isPythonInterpreter,
  className = ""
}: ToolCallBadgeProps) {
  const Icon = toolIcons[toolName] || Wrench;
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
        isPythonInterpreter 
          ? "bg-purple-100 text-purple-700 border border-purple-200" 
          : "bg-blue-100 text-blue-700 border border-blue-200"
      } ${className}`}
    >
      <Icon className="w-3 h-3" />
      <span className="font-semibold">{toolName}</span>
      {argsSummary && (
        <span className="text-xs opacity-75 max-w-[200px] truncate">
          ({argsSummary})
        </span>
      )}
    </motion.div>
  );
}