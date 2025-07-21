#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/events.py
# code style: PEP 8

"""
Event models for DeepSearchAgents Web API v2.

Defines comprehensive event types for real-time streaming of agent
execution, providing clear separation between reasoning, code generation,
execution, and tool usage.
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class EventType(str, Enum):
    """Event types for agent execution streaming"""
    
    # Agent reasoning events
    AGENT_THOUGHT = "agent_thought"
    AGENT_PLANNING = "agent_planning"
    
    # Code generation and execution events
    CODE_GENERATED = "code_generated"
    CODE_EXECUTION_START = "code_execution_start"
    CODE_EXECUTION_OUTPUT = "code_execution_output"
    CODE_EXECUTION_COMPLETE = "code_execution_complete"
    CODE_EXECUTION_ERROR = "code_execution_error"
    
    # Tool interaction events
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_OUTPUT = "tool_call_output"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    TOOL_CALL_ERROR = "tool_call_error"
    
    # Task lifecycle events
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    FINAL_ANSWER = "final_answer"
    
    # Streaming and metadata events
    STREAM_DELTA = "stream_delta"
    TOKEN_UPDATE = "token_update"
    STEP_SUMMARY = "step_summary"
    
    # Planning events (for ReAct mode)
    PLANNING = "planning"


class BaseEvent(BaseModel):
    """Base event model with common fields"""
    
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event identifier"
    )
    event_type: EventType = Field(description="Type of event")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of event"
    )
    step_number: Optional[int] = Field(
        default=None,
        description="Agent step number this event belongs to"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for multi-turn conversations"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentThoughtEvent(BaseEvent):
    """Agent reasoning/thinking event"""
    
    event_type: EventType = Field(
        default=EventType.AGENT_THOUGHT,
        const=True
    )
    content: str = Field(description="Agent's reasoning text")
    streaming: bool = Field(
        default=False,
        description="Is this a streaming delta"
    )
    complete: bool = Field(
        default=False,
        description="Is thought complete"
    )
    thought_type: Optional[str] = Field(
        default=None,
        description="Type of thought (analysis, planning, etc.)"
    )


class PlanningEvent(BaseEvent):
    """Planning step event (for ReAct agents)"""
    
    event_type: EventType = Field(
        default=EventType.PLANNING,
        const=True
    )
    plan: str = Field(description="The planning content")
    plan_number: Optional[int] = Field(
        default=None,
        description="Planning step number"
    )


class CodeGeneratedEvent(BaseEvent):
    """Code generation event"""
    
    event_type: EventType = Field(
        default=EventType.CODE_GENERATED,
        const=True
    )
    code: str = Field(description="Generated Python code")
    language: str = Field(default="python", description="Code language")
    purpose: str = Field(
        description="What this code intends to do"
    )
    tools_used: List[str] = Field(
        default_factory=list,
        description="Tools that will be called in this code"
    )


class CodeExecutionStartEvent(BaseEvent):
    """Code execution start event"""
    
    event_type: EventType = Field(
        default=EventType.CODE_EXECUTION_START,
        const=True
    )
    code_id: str = Field(
        description="Identifier linking to CodeGeneratedEvent"
    )


class CodeExecutionOutputEvent(BaseEvent):
    """Code execution output event"""
    
    event_type: EventType = Field(
        default=EventType.CODE_EXECUTION_OUTPUT,
        const=True
    )
    code_id: str = Field(
        description="Identifier linking to CodeGeneratedEvent"
    )
    output_type: str = Field(
        description="Type of output: stdout, stderr, result, display"
    )
    content: str = Field(description="Output content")
    line_number: Optional[int] = Field(
        default=None,
        description="Line number in output"
    )
    mime_type: Optional[str] = Field(
        default=None,
        description="MIME type for display outputs"
    )


class CodeExecutionCompleteEvent(BaseEvent):
    """Code execution completion event"""
    
    event_type: EventType = Field(
        default=EventType.CODE_EXECUTION_COMPLETE,
        const=True
    )
    code_id: str = Field(
        description="Identifier linking to CodeGeneratedEvent"
    )
    success: bool = Field(description="Whether execution succeeded")
    execution_time: float = Field(
        description="Execution time in seconds"
    )
    result_summary: Optional[str] = Field(
        default=None,
        description="Summary of execution result"
    )


class CodeExecutionErrorEvent(BaseEvent):
    """Code execution error event"""
    
    event_type: EventType = Field(
        default=EventType.CODE_EXECUTION_ERROR,
        const=True
    )
    code_id: str = Field(
        description="Identifier linking to CodeGeneratedEvent"
    )
    error_type: str = Field(description="Type of error")
    error_message: str = Field(description="Error message")
    traceback: Optional[str] = Field(
        default=None,
        description="Full traceback if available"
    )


class ToolCallStartEvent(BaseEvent):
    """Tool call start event"""
    
    event_type: EventType = Field(
        default=EventType.TOOL_CALL_START,
        const=True
    )
    tool_name: str = Field(description="Name of the tool")
    tool_arguments: Dict[str, Any] = Field(
        description="Arguments passed to the tool"
    )
    tool_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique tool call identifier"
    )
    parent_code_id: Optional[str] = Field(
        default=None,
        description="Parent code execution ID if called from code"
    )


class ToolCallOutputEvent(BaseEvent):
    """Tool call output event"""
    
    event_type: EventType = Field(
        default=EventType.TOOL_CALL_OUTPUT,
        const=True
    )
    tool_id: str = Field(description="Tool call identifier")
    output: Any = Field(description="Tool output data")
    output_type: str = Field(
        default="result",
        description="Type of output"
    )


class ToolCallCompleteEvent(BaseEvent):
    """Tool call completion event"""
    
    event_type: EventType = Field(
        default=EventType.TOOL_CALL_COMPLETE,
        const=True
    )
    tool_id: str = Field(description="Tool call identifier")
    tool_name: str = Field(description="Name of the tool")
    success: bool = Field(description="Whether tool call succeeded")
    execution_time: float = Field(
        description="Execution time in seconds"
    )


class ToolCallErrorEvent(BaseEvent):
    """Tool call error event"""
    
    event_type: EventType = Field(
        default=EventType.TOOL_CALL_ERROR,
        const=True
    )
    tool_id: str = Field(description="Tool call identifier")
    tool_name: str = Field(description="Name of the tool")
    error_type: str = Field(description="Type of error")
    error_message: str = Field(description="Error message")


class TaskStartEvent(BaseEvent):
    """Task start event"""
    
    event_type: EventType = Field(
        default=EventType.TASK_START,
        const=True
    )
    query: str = Field(description="User query/task")
    agent_type: str = Field(description="Type of agent (react/codact)")
    max_steps: Optional[int] = Field(
        default=None,
        description="Maximum steps allowed"
    )


class TaskCompleteEvent(BaseEvent):
    """Task completion event"""
    
    event_type: EventType = Field(
        default=EventType.TASK_COMPLETE,
        const=True
    )
    success: bool = Field(description="Whether task completed successfully")
    total_steps: int = Field(description="Total steps taken")
    total_time: float = Field(description="Total execution time in seconds")
    reason: Optional[str] = Field(
        default=None,
        description="Completion reason"
    )


class FinalAnswerEvent(BaseEvent):
    """Final answer event"""
    
    event_type: EventType = Field(
        default=EventType.FINAL_ANSWER,
        const=True
    )
    content: str = Field(description="Final answer content")
    format: str = Field(
        default="markdown",
        description="Content format (markdown, html, plain)"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Source URLs/references"
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score (0-1)"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Brief summary of the answer"
    )


class StreamDeltaEvent(BaseEvent):
    """Streaming delta event for real-time updates"""
    
    event_type: EventType = Field(
        default=EventType.STREAM_DELTA,
        const=True
    )
    delta_type: str = Field(
        description="Type of delta (thought, code, output)"
    )
    content: str = Field(description="Delta content")
    position: Optional[int] = Field(
        default=None,
        description="Position in the full content"
    )
    parent_event_id: Optional[str] = Field(
        default=None,
        description="Parent event this delta belongs to"
    )


class TokenUpdateEvent(BaseEvent):
    """Token usage update event"""
    
    event_type: EventType = Field(
        default=EventType.TOKEN_UPDATE,
        const=True
    )
    input_tokens: int = Field(description="Input tokens used")
    output_tokens: int = Field(description="Output tokens generated")
    total_tokens: int = Field(description="Total tokens")
    model: Optional[str] = Field(
        default=None,
        description="Model that used the tokens"
    )
    cost_estimate: Optional[float] = Field(
        default=None,
        description="Estimated cost in USD"
    )


class StepSummaryEvent(BaseEvent):
    """Step summary event"""
    
    event_type: EventType = Field(
        default=EventType.STEP_SUMMARY,
        const=True
    )
    step_type: str = Field(description="Type of step (action, planning, etc.)")
    duration: float = Field(description="Step duration in seconds")
    token_usage: Dict[str, int] = Field(
        description="Token usage for this step"
    )
    tools_called: List[str] = Field(
        default_factory=list,
        description="Tools called in this step"
    )
    success: bool = Field(description="Whether step succeeded")
    summary: str = Field(description="Brief summary of what happened")


# Type alias for all event types
EventUnion = Union[
    AgentThoughtEvent,
    PlanningEvent,
    CodeGeneratedEvent,
    CodeExecutionStartEvent,
    CodeExecutionOutputEvent,
    CodeExecutionCompleteEvent,
    CodeExecutionErrorEvent,
    ToolCallStartEvent,
    ToolCallOutputEvent,
    ToolCallCompleteEvent,
    ToolCallErrorEvent,
    TaskStartEvent,
    TaskCompleteEvent,
    FinalAnswerEvent,
    StreamDeltaEvent,
    TokenUpdateEvent,
    StepSummaryEvent
]