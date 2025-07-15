#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/ui_common/constants.py

"""
UI Common Constants, used to define constants, Emoji and colors
for TUI interface, and provide unified visual elements for React and CodeAct
"""

# Agent status Emoji
AGENT_EMOJIS = {
    "thinking": "🤔",
    "planning": "📌",
    "replanning": "🔄📌",
    "action": "🪄",
    "code_execution": "⌨️",
    "final": "✏️",
    "error": "❌"
}

# Define the tool icons here to avoid circular imports
TOOL_ICONS = {
    "search_links": "🔍",  # search
    "search_fast": "⚡🔍",   # fast search
    "read_url": "📄",      # read URL
    "xcom_deep_qa": "🐦",  # X.com deep Q&A (search posts & read posts)
    "github_repo_qa": "🐙",  # GitHub repo deep analysis
    "chunk_text": "✂️",    # chunk text
    "embed_texts": "🧩",   # embed texts
    "rerank_texts": "🏆",  # rerank texts
    "wolfram": "🧮",       # wolfram
    "academic_retrieval": "🎓",  # academic retrieval
    "final_answer": "✅",  # final answer
    "python_interpreter": "🐍"  # Python interpreter
}

# Colors definition
COLORS = {
    "thinking": "bold cyan",
    "planning": "bold green",
    "replanning": "bold yellow",
    "action": "bold cyan",
    "final": "bold green",
    "error": "bold red",
    "react": {"name": "bold blue", "border": "blue"},
    "codact": {"name": "bold green", "border": "green"},
    "manager": {"name": "bold cyan", "border": "cyan"}
}

# Agent Tools colors mapping
TOOL_COLORS = {
    "search_links": "bold magenta",
    "search_fast": "bold magenta",
    "read_url": "bold blue",
    "xcom_deep_qa": "bold blue",
    "github_repo_qa": "bold blue",
    "chunk_text": "bold green",
    "embed_texts": "bold yellow",
    "rerank_texts": "bold cyan",
    "wolfram": "bold red",
    "academic_retrieval": "bold blue",
    "final_answer": "bold pink",
    "python_interpreter": "bold green"
}

# Status text (Chinese)
STATUS_TEXT = {
    "thinking": "思考中...",
    "planning": "规划中...",
    "replanning": "重新规划中...",
    "action": "Action...",
    "code_execution": "代码执行中...",
    "final": "Final Answer...",
    "error": "错误",
    "observation": "观察结果...",
    "processing": "处理中...",
    "init": "初始化中..."
}

# Status text (English)
STATUS_TEXT_EN = {
    "thinking": "Thinking...",
    "planning": "Planning...",
    "replanning": "Replanning...",
    "action": "Action...",
    "code_execution": "Code Execution...",
    "final": "Final Answer...",
    "error": "Error",
    "observation": "Observing...",
    "processing": "Processing...",
    "init": "Initializing..."
}

# Top-level constants, for direct import
THINKING_COLOR = COLORS["thinking"]
PLANNING_COLOR = COLORS["planning"]
REPLANNING_COLOR = COLORS["replanning"]
ACTION_COLOR = COLORS["action"]
FINAL_COLOR = COLORS["final"]
ERROR_COLOR = COLORS["error"]

THINKING_EMOJI = AGENT_EMOJIS["thinking"]
PLANNING_EMOJI = AGENT_EMOJIS["planning"]
REPLANNING_EMOJI = AGENT_EMOJIS["replanning"]
ACTION_EMOJI = AGENT_EMOJIS["action"]
FINAL_EMOJI = AGENT_EMOJIS["final"]
ERROR_EMOJI = AGENT_EMOJIS["error"]
CODE_EXECUTION_EMOJI = AGENT_EMOJIS["code_execution"]


def get_status_text(key, lang="en"):
    """
    Get the corresponding status text based on the language

    Args:
        key: status text key name
        lang: language code 'zh' or 'en'

    Returns:
        status text in corresponding language, return key name if not found
    """
    if lang == "en":
        return STATUS_TEXT_EN.get(key, key)
    return STATUS_TEXT.get(key, key)


CODE_EXECUTION_COLOR = "bold magenta"  # code execution color definition
OBSERVATION_COLOR = "bold white"       # observation color definition
OBSERVATION_EMOJI = "👁️"               # observation emoji
DISPLAY_WIDTH = 120  # UI display width setting
