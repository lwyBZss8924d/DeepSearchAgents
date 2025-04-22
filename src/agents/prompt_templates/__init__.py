"""
Prompt template package, providing system prompts and structured templates
 for different types of agents.
"""

from .react_prompts import REACT_PROMPT
from .codact_prompts import CODACT_ACTION_PROMPT, CODACT_SYSTEM_PROMPT

__all__ = ["REACT_PROMPT", "CODACT_ACTION_PROMPT", "CODACT_SYSTEM_PROMPT"]
