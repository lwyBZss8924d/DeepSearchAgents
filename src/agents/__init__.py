#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/__init__.py

"""
DeepSearchAgent <main package>
Provides agent execution, management, and UI components

NOTE: Some components like Redis and SSE have been temporarily disabled for
      reconstruction
"""

# import runtime components that depend on the above
from .runtime import AgentRuntime
# import base components first, ensure correct order
# from .servers.agent_response import agent_observer
# from .servers.agent_callbacks import AgentStepCallback
# agent memory callback UI message formatter
from .ui_common.console_formatter import ConsoleFormatter
# v1.19.0 feature: RunResult for rich metadata
from .run_result import RunResult

__all__ = [
    "AgentRuntime",
    # "agent_observer",  # ensure observer is initialized first
    # "AgentStepCallback",  # removed temporarily, class has been refactored
    "ConsoleFormatter",
    "RunResult"  # v1.19.0 feature
]
