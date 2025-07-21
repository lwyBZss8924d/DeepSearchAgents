#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/__init__.py
# code style: PEP 8

"""
DeepSearchAgents Web API v2

Event-driven API architecture for web GUI, providing real-time streaming
of agent execution steps, code generation, and tool interactions.

This API is designed to work alongside existing CLI and MCP interfaces
without impacting their functionality.
"""

from .events import (
    EventType,
    BaseEvent,
    AgentThoughtEvent,
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
    StepSummaryEvent,
    PlanningEvent
)

from .session import (
    SessionState,
    AgentSession,
    AgentSessionManager
)

from .pipeline import (
    EventProcessor,
    StreamEventAggregator
)

__all__ = [
    # Event types
    "EventType",
    "BaseEvent",
    "AgentThoughtEvent",
    "CodeGeneratedEvent",
    "CodeExecutionStartEvent",
    "CodeExecutionOutputEvent",
    "CodeExecutionCompleteEvent",
    "CodeExecutionErrorEvent",
    "ToolCallStartEvent",
    "ToolCallOutputEvent",
    "ToolCallCompleteEvent",
    "ToolCallErrorEvent",
    "TaskStartEvent",
    "TaskCompleteEvent",
    "FinalAnswerEvent",
    "StreamDeltaEvent",
    "TokenUpdateEvent",
    "StepSummaryEvent",
    "PlanningEvent",
    # Session management
    "SessionState",
    "AgentSession",
    "AgentSessionManager",
    # Event processing
    "EventProcessor",
    "StreamEventAggregator"
]