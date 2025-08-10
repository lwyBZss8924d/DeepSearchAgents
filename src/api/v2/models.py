#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/models.py
# code style: PEP 8

"""
Simplified models for DeepSearchAgents v2 Web API.

Direct pass-through of Gradio ChatMessages with field renaming.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class DSAgentRunMessage(BaseModel):
    """
    DeepSearchAgent message format - direct mapping of Gradio ChatMessage.

    This is a simplified pass-through of smolagents' Gradio messages
    with DS-specific field names and minimal additions.
    """
    # Core Gradio ChatMessage fields
    role: Literal["user", "assistant"] = Field(
        description="Message role"
    )
    content: str = Field(
        description="Message content (markdown, code blocks, etc.)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Original Gradio metadata (status, title, etc.)"
    )

    # DS-specific additions
    message_id: str = Field(
        default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}",
        description="Unique message identifier"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Message timestamp"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier"
    )
    step_number: Optional[int] = Field(
        default=None,
        description="Agent execution step number"
    )

    class Config:
        """Pydantic config"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryRequest(BaseModel):
    """WebSocket query request"""
    type: Literal["query"] = "query"
    query: str = Field(description="User query to process")


class PingMessage(BaseModel):
    """WebSocket ping message for keepalive"""
    type: Literal["ping"] = "ping"


class PongMessage(BaseModel):
    """WebSocket pong response"""
    type: Literal["pong"] = "pong"


class ErrorMessage(BaseModel):
    """WebSocket error message"""
    type: Literal["error"] = "error"
    message: str = Field(description="Error message")
    error_code: Optional[str] = Field(
        default=None,
        description="Optional error code"
    )


class SessionState(BaseModel):
    """Session state information"""
    session_id: str
    agent_type: str
    state: str
    created_at: datetime
    last_activity: datetime
    message_count: int = 0

    class Config:
        """Pydantic config"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
