// Utility functions for extracting content from DSAgentRunMessage
// Based on metadata fields from gradio_passthrough_processor.py

export interface ExtractedCode {
  code: string;
  language: string;
}

// Message type detection based on metadata
export function getMessageType(metadata: Record<string, any>): string | null {
  // Check event_type first (most reliable)
  if (metadata?.event_type) {
    return metadata.event_type;
  }
  
  // Check title patterns
  if (metadata?.title) {
    if (metadata.title.includes('Planning step')) return 'planning';
    if (metadata.title.includes('Step')) return 'action_step';
    if (metadata.title.includes('Used tool')) return 'tool_call';
    if (metadata.title.includes('Execution Logs')) return 'execution_logs';
    if (metadata.title.includes('Error')) return 'error';
    if (metadata.title.includes('Final answer')) return 'final_answer';
  }
  
  return null;
}

// Get component routing from metadata
export function getMessageComponent(metadata: Record<string, any>): 'chat' | 'webide' | 'terminal' {
  // Trust metadata.component if present
  if (metadata?.component) {
    return metadata.component as 'chat' | 'webide' | 'terminal';
  }
  
  // Default to chat
  return 'chat';
}

// Extract code blocks from markdown content (fallback when metadata doesn't contain code)
export function extractPythonCode(content: string): ExtractedCode | null {
  // Match any code block, not just Python
  const match = content.match(/```(\w+)?\n([\s\S]*?)```/);
  if (match) {
    return {
      language: match[1] || 'python',
      code: match[2]
    };
  }
  return null;
}

// Extract all code blocks (for multiple blocks in one message)
export function extractAllCodeBlocks(content: string): ExtractedCode[] {
  const matches = Array.from(content.matchAll(/```(\w+)?\n([\s\S]*?)```/g));
  return matches.map(match => ({
    language: match[1] || 'text',
    code: match[2]
  }));
}

// Extract execution logs (usually in bash blocks)
export function extractExecutionLogs(content: string): string[] {
  const logs: string[] = [];
  
  // Extract from code blocks (bash, text, output)
  const blocks = extractAllCodeBlocks(content);
  blocks
    .filter(block => ['bash', 'text', 'output', ''].includes(block.language))
    .forEach(block => logs.push(block.code));
  
  // Extract from "Observations:" section
  const obsMatch = content.match(/Observations?:\s*\n([\s\S]*?)(?=\n\n|\n\*\*|$)/);
  if (obsMatch) {
    logs.push(obsMatch[1].trim());
  }
  
  // Extract from "Execution logs:" section
  const execMatch = content.match(/Execution logs?:\s*\n([\s\S]*?)(?=\n\n|\n\*\*|$)/);
  if (execMatch) {
    logs.push(execMatch[1].trim());
  }
  
  return logs;
}

// Extract clean text output from observations
export function extractObservations(content: string): string {
  // Remove code blocks and return clean text
  const withoutCodeBlocks = content.replace(/```[\s\S]*?```/g, '');
  // Extract text after "Execution logs:" or "Observations:"
  const match = withoutCodeBlocks.match(/(?:Execution logs:|Observations:)\s*([\s\S]*)/);
  return match ? match[1].trim() : withoutCodeBlocks.trim();
}

// Check if message contains code
export function hasCodeBlock(content: string): boolean {
  return /```[\s\S]*?```/.test(content);
}

// Get tool name from metadata
export function getToolName(metadata: Record<string, any>): string | null {
  // First check metadata.tool_name field (preferred)
  if (metadata?.tool_name) {
    return metadata.tool_name;
  }
  
  // Fallback to parsing from title
  if (metadata?.title?.includes('Used tool')) {
    const match = metadata.title.match(/Used tool (\w+)/);
    return match ? match[1] : null;
  }
  
  return null;
}

// Check if message is a thinking/reasoning step
export function isThinkingMessage(metadata: Record<string, any>): boolean {
  return metadata?.status === 'thinking' || 
         metadata?.event_type === 'planning' ||
         metadata?.title?.toLowerCase().includes('analysis') ||
         metadata?.title?.toLowerCase().includes('planning');
}

// Check if message is a planning step
export function isPlanningStep(metadata: Record<string, any>): boolean {
  return metadata?.event_type === 'planning' || 
         metadata?.title?.toLowerCase().includes('planning step') ||
         metadata?.title === '**Planning step**';
}

// Check if message is an action step thought
export function isActionStepThought(metadata: Record<string, any>, content?: string): boolean {
  // Check message_type first (used by v2 API)
  if (metadata?.message_type === 'action_thought') return true;
  
  // Fallback: check event_type for backwards compatibility
  if (metadata?.event_type === 'action_thought') return true;
  
  // Check if it's Step N content that's not code or execution logs
  const stepPattern = /^\*\*Step \d+\*\*/;
  if (content && stepPattern.test(content)) {
    // It's a thought if it's not code execution or logs
    return !hasCodeBlock(content) && 
           metadata?.component !== 'webide' && 
           metadata?.component !== 'terminal';
  }
  
  return false;
}

// Check if message should be shown in terminal
export function isTerminalMessage(metadata: Record<string, any>): boolean {
  return metadata?.component === 'terminal' ||
         metadata?.title === '📝 Execution Logs' ||
         metadata?.event_type === 'execution_logs' ||
         metadata?.event_type === 'tool_output' ||
         (metadata?.tool_name === 'python_interpreter' && metadata?.event_type === 'tool_output');
}

// Check if message should be shown in code editor
export function isCodeEditorMessage(metadata: Record<string, any>): boolean {
  return metadata?.component === 'webide' ||
         (metadata?.event_type === 'tool_invocation' && metadata?.tool_name === 'python_interpreter') ||
         (metadata?.event_type === 'tool_call' && metadata?.tool_name === 'python_interpreter');
}

// Check if message is a final answer
export function isFinalAnswer(metadata: Record<string, any>, content?: string): boolean {
  // Check metadata
  if (metadata?.is_final_answer || 
      metadata?.message_type === 'final_answer' ||
      metadata?.tool_name === 'final_answer' ||
      metadata?.status === 'complete' || 
      metadata?.title?.toLowerCase().includes('final answer')) {
    return true;
  }
  
  // Check content for final_answer tool usage
  if (content && content.includes('Used tool final_answer')) {
    return true;
  }
  
  return false;
}

// Parse JSON content safely
function parseJSON(content: string): any {
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

// Extract final answer content
export function extractFinalAnswerContent(content: string): string | null {
  // First check if content contains "Used tool final_answer"
  if (content.includes('Used tool final_answer')) {
    // Look for code block after tool usage
    const toolMatch = content.match(/Used tool final_answer[\s\S]*?```(?:json)?\s*([\s\S]*?)```/);
    if (toolMatch) {
      const jsonContent = toolMatch[1].trim();
      const parsed = parseJSON(jsonContent);
      if (parsed && parsed.content) {
        // Return the markdown content from the JSON
        return parsed.content;
      }
    }
  }
  
  // Look for any JSON code block with content field
  const codeBlockMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    const jsonContent = codeBlockMatch[1].trim();
    // Check if it looks like JSON (starts with { and has quotes)
    if (jsonContent.startsWith('{') && jsonContent.includes('"')) {
      const parsed = parseJSON(jsonContent);
      if (parsed && parsed.content) {
        // Return the markdown content from the JSON
        return parsed.content;
      }
    }
    // If not JSON but in a code block after final answer mention, return as-is
    if (content.toLowerCase().includes('final answer')) {
      return jsonContent;
    }
  }
  
  // Look for direct JSON in content (not in code block)
  const jsonMatch = content.match(/\{[\s\S]*?"content"\s*:\s*"[\s\S]*?\}/);
  if (jsonMatch) {
    const parsed = parseJSON(jsonMatch[0]);
    if (parsed && parsed.content) {
      return parsed.content;
    }
  }
  
  // Look for content after "Final Answer:" or "Final answer:"
  const finalMatch = content.match(/[Ff]inal [Aa]nswer:?\s*\n?([\s\S]*?)$/);
  if (finalMatch) {
    const answer = finalMatch[1].trim();
    // Check if the answer itself is a code block
    const answerCodeBlock = answer.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (answerCodeBlock) {
      const parsed = parseJSON(answerCodeBlock[1].trim());
      if (parsed && parsed.content) {
        return parsed.content;
      }
      return answerCodeBlock[1].trim();
    }
    return answer;
  }
  
  // Look for "**Final answer:**" pattern from smolagents
  const finalAnswerPattern = content.match(/\*\*Final answer:\*\*\s*\n?([\s\S]*?)$/);
  if (finalAnswerPattern) {
    return finalAnswerPattern[1].trim();
  }
  
  return null;
}

// Extract final answer metadata (title, sources, etc)
export function extractFinalAnswerMetadata(content: string): { title?: string; sources?: string[]; confidence?: number } | null {
  // Look for JSON content
  const codeBlockMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    const parsed = parseJSON(codeBlockMatch[1].trim());
    if (parsed && typeof parsed === 'object') {
      return {
        title: parsed.title,
        sources: parsed.sources,
        confidence: parsed.confidence
      };
    }
  }
  
  // Look for direct JSON
  const jsonMatch = content.match(/\{[\s\S]*"content"[\s\S]*\}/);
  if (jsonMatch) {
    const parsed = parseJSON(jsonMatch[0]);
    if (parsed && typeof parsed === 'object') {
      return {
        title: parsed.title,
        sources: parsed.sources,
        confidence: parsed.confidence
      };
    }
  }
  
  return null;
}