#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/__init__.py
# code style: PEP 8

"""
Agent Tools for DeepSearchAgents.
"""

from .search import SearchLinksTool
from .readurl import ReadURLTool
from .chunk import ChunkTextTool
from .embed import EmbedTextsTool
from .rerank import RerankTextsTool
from .wolfram import EnhancedWolframAlphaTool
from .final_answer import EnhancedFinalAnswerTool as FinalAnswerTool
from .toolbox import (
    ToolCollection,
    DeepSearchToolbox,
    toolbox,
    from_toolbox,
    TOOL_ICONS
)

# Re-export TOOL_ICONS
__all__ = [
    "SearchLinksTool",
    "ReadURLTool",
    "ChunkTextTool",
    "EmbedTextsTool",
    "RerankTextsTool",
    "EnhancedWolframAlphaTool",
    "FinalAnswerTool",
    "TOOL_ICONS",
    "ToolCollection",
    "DeepSearchToolbox",
    "toolbox",
    "from_toolbox",
]
