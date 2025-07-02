#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/run_result.py
# code style: PEP 8

"""
RunResult class for agent execution metadata
Provides rich metadata about agent execution following smolagents v1.19.0
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time


@dataclass
class RunResult:
    """Result object containing execution metadata from agent.run()

    Attributes:
        final_answer: The final answer/output from the agent
        steps: List of execution steps with details
        token_usage: Dictionary with input/output token counts
        execution_time: Total execution time in seconds
        error: Optional error message if execution failed
        agent_type: Type of agent that produced this result
        model_info: Information about models used
    """
    final_answer: str
    steps: List[Dict[str, Any]] = None
    token_usage: Dict[str, int] = None
    execution_time: float = 0.0
    error: Optional[str] = None
    agent_type: str = "unknown"
    model_info: Dict[str, str] = None

    def __post_init__(self):
        """Initialize default values"""
        if self.steps is None:
            self.steps = []
        if self.token_usage is None:
            self.token_usage = {"input": 0, "output": 0, "total": 0}
        if self.model_info is None:
            self.model_info = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert RunResult to dictionary format"""
        return {
            "final_answer": self.final_answer,
            "steps": self.steps,
            "token_usage": self.token_usage,
            "execution_time": self.execution_time,
            "error": self.error,
            "agent_type": self.agent_type,
            "model_info": self.model_info
        }

    def __str__(self) -> str:
        """String representation returns just the final answer for
        backward compatibility"""
        return self.final_answer

    @property
    def total_tokens(self) -> int:
        """Get total token count"""
        return self.token_usage.get("total", 0)

    @property
    def success(self) -> bool:
        """Check if execution was successful"""
        return self.error is None

    def add_step(self, step: Dict[str, Any]):
        """Add an execution step"""
        self.steps.append(step)

    def update_token_usage(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0
    ):
        """Update token usage counts"""
        self.token_usage["input"] += input_tokens
        self.token_usage["output"] += output_tokens
        self.token_usage["total"] = self.token_usage["input"] + self.token_usage["output"]
