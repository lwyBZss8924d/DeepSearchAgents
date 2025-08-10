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

interface ToolCallBadgeProps {
  toolName: string;
  toolId?: string;
  argsSummary?: string;
  isPythonInterpreter?: boolean;
  className?: string;
}

export default function ToolCallBadge({
  toolName,
  toolId,
  argsSummary,
  isPythonInterpreter, // eslint-disable-line @typescript-eslint/no-unused-vars
  className = ""
}: ToolCallBadgeProps) {
  // Map old props to new DS component props
  const metadata = argsSummary ? {
    resultPreview: argsSummary,
    toolId: toolId
  } : undefined;
  
  // Note: isPythonInterpreter is ignored in the new component
  // The DS component handles tool-specific styling based on toolName
  
  return (
    <DSAgentToolBadge
      toolName={toolName}
      status="active"
      metadata={metadata}
      className={className}
    />
  );
}