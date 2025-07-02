#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/ui_common/__init__.py

"""DeepSearchAgent UI General UI
providing constants and tools for UI interaction"""

# Export constants
from .constants import (
    AGENT_EMOJIS, TOOL_ICONS, COLORS, TOOL_COLORS, STATUS_TEXT,
    THINKING_COLOR, THINKING_EMOJI,
    PLANNING_COLOR, PLANNING_EMOJI,
    REPLANNING_COLOR, REPLANNING_EMOJI,
    ACTION_COLOR, ACTION_EMOJI,
    FINAL_COLOR, FINAL_EMOJI,
    ERROR_COLOR, ERROR_EMOJI,
    CODE_EXECUTION_EMOJI
)

# Export UI formatter
from .console_formatter import ConsoleFormatter
from .streaming_formatter import StreamingConsoleFormatter

# Export Gradio adapter
from .gradio_adapter import (
    GradioUIAdapter, create_gradio_compatible_agent
)

__all__ = [
    # Constants
    'AGENT_EMOJIS', 'TOOL_ICONS', 'COLORS', 'TOOL_COLORS', 'STATUS_TEXT',
    'THINKING_COLOR', 'THINKING_EMOJI',
    'PLANNING_COLOR', 'PLANNING_EMOJI',
    'REPLANNING_COLOR', 'REPLANNING_EMOJI',
    'ACTION_COLOR', 'ACTION_EMOJI',
    'FINAL_COLOR', 'FINAL_EMOJI',
    'ERROR_COLOR', 'ERROR_EMOJI',
    'CODE_EXECUTION_EMOJI',
    # Classes
    'ConsoleFormatter',
    'StreamingConsoleFormatter',
    # Gradio Adapter
    'GradioUIAdapter', 'create_gradio_compatible_agent'
]
