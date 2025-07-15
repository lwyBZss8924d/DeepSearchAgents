#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/__init__.py
# code style: PEP 8

"""
Agent Tools for DeepSearchAgents.
"""

from .search import SearchLinksTool
from .search_fast import SearchLinksFastTool, search_fast
from .search_helpers import (
    MultiQuerySearchTool,
    DomainSearchTool,
    search_code,
    search_docs,
    search_recent
)
from .readurl import ReadURLTool
from .chunk import ChunkTextTool
from .embed import EmbedTextsTool
from .rerank import RerankTextsTool
from .wolfram import EnhancedWolframAlphaTool
from .xcom_qa import XcomDeepQATool
from .github_qa import GitHubRepoQATool
# TODO: Academic retrieval temporarily disabled - awaiting new implementation
# from .academic_retrieval import AcademicRetrieval
try:
    from .academic_retrieval import AcademicRetrieval
except ImportError:
    AcademicRetrieval = None  # Tool temporarily unavailable
from .final_answer import EnhancedFinalAnswerTool as FinalAnswerTool
from .toolbox import (
    ToolCollection,
    DeepSearchToolbox,
    toolbox,
    from_toolbox
)
from src.agents.ui_common.constants import TOOL_ICONS

# Re-export
__all__ = [
    "SearchLinksTool",
    "SearchLinksFastTool",
    "search_fast",
    "MultiQuerySearchTool",
    "DomainSearchTool",
    "search_code",
    "search_docs",
    "search_recent",
    "ReadURLTool",
    "ChunkTextTool",
    "EmbedTextsTool",
    "RerankTextsTool",
    "XcomDeepQATool",
    "GitHubRepoQATool",
    "EnhancedWolframAlphaTool",
    "FinalAnswerTool",
    "TOOL_ICONS",
    "ToolCollection",
    "DeepSearchToolbox",
    "toolbox",
    "from_toolbox",
]

# Add AcademicRetrieval only if it was successfully imported
if AcademicRetrieval is not None:
    __all__.insert(__all__.index("EnhancedWolframAlphaTool"), "AcademicRetrieval")
