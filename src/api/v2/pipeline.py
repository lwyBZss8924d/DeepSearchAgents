#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/pipeline.py
# code style: PEP 8

"""
Event processing pipeline for converting smolagents memory steps
to web-friendly events.

This module handles the transformation of internal agent execution
steps into structured events suitable for real-time web streaming.
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional, Generator, Tuple
from collections import defaultdict

from smolagents.memory import (
    ActionStep, PlanningStep, TaskStep, SystemPromptStep,
    FinalAnswerStep, MemoryStep
)
from smolagents.models import ChatMessageStreamDelta
from smolagents.agents import ToolCall
from smolagents import TokenUsage

from .events import (
    BaseEvent, AgentThoughtEvent, PlanningEvent,
    CodeGeneratedEvent, CodeExecutionStartEvent,
    CodeExecutionOutputEvent, CodeExecutionCompleteEvent,
    CodeExecutionErrorEvent, ToolCallStartEvent,
    ToolCallOutputEvent, ToolCallCompleteEvent,
    ToolCallErrorEvent, TaskStartEvent, TaskCompleteEvent,
    FinalAnswerEvent, StreamDeltaEvent, TokenUpdateEvent,
    StepSummaryEvent
)

logger = logging.getLogger(__name__)


class EventProcessor:
    """
    Process smolagents memory steps and streaming events into
    web-friendly event objects.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize event processor.
        
        Args:
            session_id: Optional session ID to attach to events
        """
        self.session_id = session_id
        self.step_counter = 0
        self.code_id_mapping: Dict[int, str] = {}
        self.tool_timings: Dict[str, float] = {}
        
    def process_memory_step(
        self, 
        step: MemoryStep
    ) -> List[BaseEvent]:
        """
        Convert a smolagents memory step to web events.
        
        Args:
            step: Memory step from smolagents
            
        Returns:
            List of web events
        """
        events = []
        
        if isinstance(step, SystemPromptStep):
            # System prompts are internal, no events needed
            pass
            
        elif isinstance(step, TaskStep):
            events.extend(self._process_task_step(step))
            
        elif isinstance(step, ActionStep):
            events.extend(self._process_action_step(step))
            
        elif isinstance(step, PlanningStep):
            events.extend(self._process_planning_step(step))
            
        elif isinstance(step, FinalAnswerStep):
            events.extend(self._process_final_answer_step(step))
            
        else:
            logger.warning(f"Unknown step type: {type(step).__name__}")
            
        return events
    
    def _process_task_step(self, step: TaskStep) -> List[BaseEvent]:
        """Process task step into events."""
        self.step_counter = 0  # Reset counter for new task
        
        return [
            TaskStartEvent(
                session_id=self.session_id,
                query=step.task,
                agent_type="unknown",  # Will be set by session
                metadata={
                    "has_images": bool(step.task_images)
                }
            )
        ]
    
    def _process_action_step(self, step: ActionStep) -> List[BaseEvent]:
        """Process action step into events."""
        events = []
        self.step_counter += 1
        step_start_time = time.time()
        
        # Extract agent thought/reasoning
        if step.model_output:
            thought_content = self._clean_model_output(step.model_output)
            events.append(AgentThoughtEvent(
                session_id=self.session_id,
                step_number=self.step_counter,
                content=thought_content,
                complete=True,
                thought_type="reasoning"
            ))
        
        # Process tool calls
        if step.tool_calls:
            for tool_call in step.tool_calls:
                tool_events = self._process_tool_call(
                    tool_call, 
                    step.observations,
                    step.error
                )
                events.extend(tool_events)
        
        # Add token update if available
        if hasattr(step, "token_usage") and step.token_usage:
            events.append(self._create_token_event(step.token_usage))
        
        # Add step summary
        step_duration = time.time() - step_start_time
        events.append(self._create_step_summary(
            step, 
            "action", 
            step_duration
        ))
        
        return events
    
    def _process_tool_call(
        self,
        tool_call: ToolCall,
        observations: Optional[str],
        error: Optional[Any]
    ) -> List[BaseEvent]:
        """Process a tool call into events."""
        events = []
        tool_start_time = time.time()
        
        if tool_call.name == "python_interpreter":
            # This is code execution
            code = tool_call.arguments.get("code", "")
            code_id = self._generate_code_id()
            self.code_id_mapping[self.step_counter] = code_id
            
            # Extract tools that will be called in the code
            tools_in_code = self._extract_tools_from_code(code)
            
            # Code generated event
            events.append(CodeGeneratedEvent(
                session_id=self.session_id,
                step_number=self.step_counter,
                code=code,
                purpose=self._extract_code_purpose(code),
                tools_used=tools_in_code
            ))
            
            # Code execution start
            events.append(CodeExecutionStartEvent(
                session_id=self.session_id,
                step_number=self.step_counter,
                code_id=code_id
            ))
            
            # Process execution output
            if observations:
                output_events = self._parse_code_output(
                    observations, 
                    code_id
                )
                events.extend(output_events)
            
            # Code execution complete/error
            if error:
                events.append(CodeExecutionErrorEvent(
                    session_id=self.session_id,
                    step_number=self.step_counter,
                    code_id=code_id,
                    error_type=type(error).__name__,
                    error_message=str(error)
                ))
            else:
                exec_time = time.time() - tool_start_time
                events.append(CodeExecutionCompleteEvent(
                    session_id=self.session_id,
                    step_number=self.step_counter,
                    code_id=code_id,
                    success=True,
                    execution_time=exec_time
                ))
        else:
            # Regular tool call
            tool_id = tool_call.id or self._generate_tool_id()
            
            # Tool call start
            events.append(ToolCallStartEvent(
                session_id=self.session_id,
                step_number=self.step_counter,
                tool_name=tool_call.name,
                tool_arguments=tool_call.arguments,
                tool_id=tool_id,
                parent_code_id=self.code_id_mapping.get(
                    self.step_counter
                )
            ))
            
            # Tool output
            if observations and not error:
                events.append(ToolCallOutputEvent(
                    session_id=self.session_id,
                    step_number=self.step_counter,
                    tool_id=tool_id,
                    output=observations
                ))
            
            # Tool complete/error
            exec_time = time.time() - tool_start_time
            if error:
                events.append(ToolCallErrorEvent(
                    session_id=self.session_id,
                    step_number=self.step_counter,
                    tool_id=tool_id,
                    tool_name=tool_call.name,
                    error_type=type(error).__name__,
                    error_message=str(error)
                ))
            else:
                events.append(ToolCallCompleteEvent(
                    session_id=self.session_id,
                    step_number=self.step_counter,
                    tool_id=tool_id,
                    tool_name=tool_call.name,
                    success=True,
                    execution_time=exec_time
                ))
        
        return events
    
    def _process_planning_step(
        self, 
        step: PlanningStep
    ) -> List[BaseEvent]:
        """Process planning step into events."""
        self.step_counter += 1
        
        events = [
            PlanningEvent(
                session_id=self.session_id,
                step_number=self.step_counter,
                plan=step.plan,
                plan_number=self.step_counter
            )
        ]
        
        # Add token update if available
        if hasattr(step, "token_usage") and step.token_usage:
            events.append(self._create_token_event(step.token_usage))
        
        return events
    
    def _process_final_answer_step(
        self,
        step: FinalAnswerStep
    ) -> List[BaseEvent]:
        """Process final answer step into events."""
        # Extract sources from the answer if present
        sources = self._extract_sources(step.final_answer)
        
        return [
            FinalAnswerEvent(
                session_id=self.session_id,
                step_number=self.step_counter,
                content=step.final_answer,
                sources=sources,
                metadata={
                    "output_type": type(step.output).__name__
                    if hasattr(step, "output") else None
                }
            ),
            TaskCompleteEvent(
                session_id=self.session_id,
                success=True,
                total_steps=self.step_counter,
                total_time=0.0,  # Will be calculated by session
                reason="Final answer provided"
            )
        ]
    
    def _clean_model_output(self, model_output: str) -> str:
        """Clean up model output by removing tags and formatting."""
        if not model_output:
            return ""
            
        output = model_output.strip()
        
        # Remove various end tags
        output = re.sub(r"```\s*<end_code>", "```", output)
        output = re.sub(r"<end_code>\s*```", "```", output)
        output = re.sub(r"```\s*\n\s*<end_code>", "```", output)
        output = re.sub(r"<end_code>", "", output)
        
        return output.strip()
    
    def _extract_tools_from_code(self, code: str) -> List[str]:
        """Extract tool names from Python code."""
        tools = []
        
        # Common tool names to look for
        tool_patterns = [
            r"search_links\s*\(",
            r"search_fast\s*\(",
            r"read_url\s*\(",
            r"chunk_text\s*\(",
            r"embed_texts\s*\(",
            r"rerank_texts\s*\(",
            r"wolfram\s*\(",
            r"academic_retrieval\s*\(",
            r"final_answer\s*\(",
            r"xcom_deep_qa\s*\(",
            r"github_repo_qa\s*\("
        ]
        
        for pattern in tool_patterns:
            if re.search(pattern, code):
                tool_name = pattern.split(r"\s*\(")[0]
                tools.append(tool_name.replace("\\", ""))
        
        return list(set(tools))
    
    def _extract_code_purpose(self, code: str) -> str:
        """Extract purpose from code comments or structure."""
        lines = code.strip().split('\n')
        
        # Look for initial comments
        for line in lines[:5]:
            if line.strip().startswith('#'):
                return line.strip('#').strip()
        
        # Try to infer from code structure
        if "search" in code.lower():
            return "Search for information"
        elif "read_url" in code:
            return "Read and analyze web content"
        elif "final_answer" in code:
            return "Generate final answer"
        else:
            return "Execute code actions"
    
    def _parse_code_output(
        self,
        observations: str,
        code_id: str
    ) -> List[CodeExecutionOutputEvent]:
        """Parse code execution output into events."""
        events = []
        
        if not observations:
            return events
        
        # Split output into lines
        lines = observations.split('\n')
        
        for i, line in enumerate(lines):
            if line.strip():
                # Determine output type
                output_type = "stdout"
                if "error" in line.lower() or "traceback" in line.lower():
                    output_type = "stderr"
                elif line.startswith("Result:") or line.startswith("Output:"):
                    output_type = "result"
                
                events.append(CodeExecutionOutputEvent(
                    session_id=self.session_id,
                    step_number=self.step_counter,
                    code_id=code_id,
                    output_type=output_type,
                    content=line,
                    line_number=i + 1
                ))
        
        return events
    
    def _extract_sources(self, content: str) -> List[str]:
        """Extract source URLs from content."""
        sources = []
        
        # Look for URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+(?:/[^\s<>"{}|\\^`\[\]]*)?'
        urls = re.findall(url_pattern, content)
        
        # Clean and deduplicate
        for url in urls:
            # Remove trailing punctuation
            url = re.sub(r'[.,;:!?]+$', '', url)
            if url not in sources:
                sources.append(url)
        
        return sources
    
    def _create_token_event(self, token_usage: TokenUsage) -> TokenUpdateEvent:
        """Create token update event from token usage."""
        input_tokens = token_usage.input_tokens or 0
        output_tokens = token_usage.output_tokens or 0
        
        return TokenUpdateEvent(
            session_id=self.session_id,
            step_number=self.step_counter,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )
    
    def _create_step_summary(
        self,
        step: MemoryStep,
        step_type: str,
        duration: float
    ) -> StepSummaryEvent:
        """Create step summary event."""
        tools_called = []
        
        if hasattr(step, "tool_calls") and step.tool_calls:
            tools_called = [tc.name for tc in step.tool_calls]
        
        token_usage = {}
        if hasattr(step, "token_usage") and step.token_usage:
            token_usage = {
                "input": step.token_usage.input_tokens or 0,
                "output": step.token_usage.output_tokens or 0
            }
        
        success = not bool(getattr(step, "error", None))
        
        return StepSummaryEvent(
            session_id=self.session_id,
            step_number=self.step_counter,
            step_type=step_type,
            duration=duration,
            token_usage=token_usage,
            tools_called=tools_called,
            success=success,
            summary=self._generate_step_summary(step, step_type)
        )
    
    def _generate_step_summary(
        self,
        step: MemoryStep,
        step_type: str
    ) -> str:
        """Generate a brief summary of what happened in the step."""
        if step_type == "action" and hasattr(step, "tool_calls"):
            if step.tool_calls:
                tool_names = [tc.name for tc in step.tool_calls]
                return f"Called tools: {', '.join(tool_names)}"
        elif step_type == "planning":
            return "Created execution plan"
        
        return f"Completed {step_type} step"
    
    def _generate_code_id(self) -> str:
        """Generate unique code execution ID."""
        import uuid
        return f"code_{uuid.uuid4().hex[:8]}"
    
    def _generate_tool_id(self) -> str:
        """Generate unique tool call ID."""
        import uuid
        return f"tool_{uuid.uuid4().hex[:8]}"


class StreamEventAggregator:
    """
    Aggregate streaming deltas into complete events.
    
    Handles the conversion of ChatMessageStreamDelta objects
    into appropriate web events.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize stream aggregator."""
        self.session_id = session_id
        self.current_content = ""
        self.current_type = None
        self.delta_count = 0
        
    def process_stream_delta(
        self,
        delta: ChatMessageStreamDelta
    ) -> Optional[StreamDeltaEvent]:
        """
        Process a streaming delta.
        
        Args:
            delta: Stream delta from smolagents
            
        Returns:
            StreamDeltaEvent if content is available
        """
        if not delta.content:
            return None
        
        self.current_content += delta.content
        self.delta_count += 1
        
        # Determine delta type from content patterns
        delta_type = self._determine_delta_type(delta.content)
        
        return StreamDeltaEvent(
            session_id=self.session_id,
            delta_type=delta_type,
            content=delta.content,
            position=len(self.current_content)
        )
    
    def _determine_delta_type(self, content: str) -> str:
        """Determine the type of streaming delta."""
        # Simple heuristic based on content patterns
        if "```" in content:
            return "code"
        elif any(indicator in content.lower() 
                 for indicator in ["thinking", "analyzing", "let me"]):
            return "thought"
        else:
            return "output"
    
    def get_complete_content(self) -> str:
        """Get the complete aggregated content."""
        return self.current_content
    
    def reset(self):
        """Reset the aggregator for a new stream."""
        self.current_content = ""
        self.current_type = None
        self.delta_count = 0