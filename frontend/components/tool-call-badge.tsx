"use client";

/**
 * @deprecated This component is deprecated. Please use DSAgentToolBadge from @/components/ds instead.
 * This file now acts as a compatibility wrapper during the migration to WebTUI.
 * 
 * Migration guide:
 * - Import: import { DSAgentToolBadge } from '@/components/ds'
 * - Props: 
 *   - argsSummary → metadata.resultPreview
 *   - isPythonInterpreter → handled automatically via toolName
 *   - toolId → not needed in new component
 */

import { DSAgentToolBadge } from "@/components/ds";
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

// Map tool names to icons (maintained for backward compatibility)
const toolIcons: Record<string, React.ReactNode> = {
  python_interpreter: <Code2 className="w-4 h-4" />,
  search: <Search className="w-4 h-4" />,
  readurl: <Globe className="w-4 h-4" />,
  chunk: <FileText className="w-4 h-4" />,
  embed: <FileText className="w-4 h-4" />,
  rerank: <FileText className="w-4 h-4" />,
  wolfram: <Calculator className="w-4 h-4" />,
  final_answer: <CheckCircle className="w-4 h-4" />,
};

export default function ToolCallBadge({
  toolName,
  toolId,
  argsSummary,
  isPythonInterpreter, // eslint-disable-line @typescript-eslint/no-unused-vars
  className = ""
}: ToolCallBadgeProps) {
  // Map old props to new DS component props
  const icon = toolIcons[toolName] || <Wrench className="w-4 h-4" />;
  
  const metadata = argsSummary ? {
    resultPreview: argsSummary,
    toolId: toolId
  } : undefined;
  
  // Note: isPythonInterpreter is ignored in the new component
  // The DS component handles tool-specific styling based on toolName
  
  return (
    <DSAgentToolBadge
      toolName={toolName}
      icon={icon}
      status="active"
      metadata={metadata}
      className={className}
    />
  );
}