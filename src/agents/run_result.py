#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/run_result.py
# code style: PEP 8

"""
RunResult class for agent execution metadata
Provides rich metadata about agent execution following smolagents v1.19.0
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import time

from smolagents import TokenUsage


@dataclass
class RunResult:
    """Result object containing execution metadata from agent.run()

    Attributes:
        final_answer: The final answer/output from the agent
        steps: List of execution steps with details
        token_usage: TokenUsage object with input/output token counts
        execution_time: Total execution time in seconds
        error: Optional error message if execution failed
        agent_type: Type of agent that produced this result
        model_info: Information about models used
    """
    final_answer: str
    steps: List[Dict[str, Any]] = None
    token_usage: Optional[TokenUsage] = None
    execution_time: float = 0.0
    error: Optional[str] = None
    agent_type: str = "unknown"
    model_info: Dict[str, str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Initialize default values"""
        if self.steps is None:
            self.steps = []
        if self.token_usage is None:
            self.token_usage = TokenUsage(input_tokens=0, output_tokens=0)
        if self.model_info is None:
            self.model_info = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert RunResult to dictionary format"""
        token_usage_dict = None
        if self.token_usage:
            if isinstance(self.token_usage, TokenUsage):
                token_usage_dict = {
                    "input": self.token_usage.input_tokens or 0,
                    "output": self.token_usage.output_tokens or 0,
                    "total": (self.token_usage.input_tokens or 0) + 
                             (self.token_usage.output_tokens or 0)
                }
            else:
                # Fallback for dict-based token usage
                token_usage_dict = self.token_usage

        return {
            "final_answer": self.final_answer,
            "steps": self.steps,
            "token_usage": token_usage_dict,
            "execution_time": self.execution_time,
            "error": self.error,
            "agent_type": self.agent_type,
            "model_info": self.model_info,
            "success": self.success,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
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

    def to_json(self) -> str:
        """Convert RunResult to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    def summary(self) -> str:
        """Generate a summary of the execution"""
        agent_name = self.agent_type.capitalize() if self.agent_type else "Unknown"
        lines = []
        lines.append(f"{agent_name} Agent Execution Summary")
        lines.append("=" * 40)

        if self.error:
            lines.append("✗ Failed")
            lines.append(f"Error: {self.error}")
        else:
            lines.append("✓ Success")

        lines.append(f"Execution Time: {self.execution_time:.2f} seconds")
        lines.append(f"Total Tokens: {self.total_tokens} tokens")
        lines.append(f"Steps: {len(self.steps)} steps")

        if not self.error and self.final_answer:
            lines.append(f"Answer: {self.final_answer}")

        if self.model_info:
            lines.append(f"Models: {', '.join(self.model_info.values())}")

        return "\n".join(lines)

    def get_step_types(self) -> List[str]:
        """Get unique types of steps executed"""
        return list(set(step.get("type", "unknown") for step in self.steps))

    def get_steps_by_type(self, step_type: str) -> List[Dict[str, Any]]:
        """Get all steps of a specific type"""
        return [step for step in self.steps if step.get("type") == step_type]
