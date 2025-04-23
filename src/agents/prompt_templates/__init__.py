"""
Prompt template package, providing system prompts and structured templates
 for different types of agents.
"""

from .react_prompts import REACT_PROMPT
from .codact_prompts import (
    CODACT_SYSTEM_EXTENSION,
    PLANNING_TEMPLATES,
    FINAL_ANSWER_EXTENSION,
    MANAGED_AGENT_TEMPLATES,
    merge_prompt_templates
)

__all__ = [
    "REACT_PROMPT", "CODACT_SYSTEM_EXTENSION", "PLANNING_TEMPLATES",
    "FINAL_ANSWER_EXTENSION", "MANAGED_AGENT_TEMPLATES",
    "merge_prompt_templates"
]
