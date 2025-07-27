#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/__init__.py
# code style: PEP 8

"""
DeepSearchAgents Web API v2

Simplified API using direct Gradio message pass-through for real-time
streaming of agent execution.

This API is designed to work alongside existing CLI and MCP interfaces
without impacting their functionality.
"""

from .models import DSAgentRunMessage
from .session import SessionState, AgentSession, AgentSessionManager
from .ds_agent_message_processor import DSAgentMessageProcessor

__all__ = [
    # Message model
    "DSAgentRunMessage",
    # Session management
    "SessionState",
    "AgentSession",
    "AgentSessionManager",
    # Message processor
    "DSAgentMessageProcessor"
]
