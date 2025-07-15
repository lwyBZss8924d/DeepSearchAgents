#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/unit/test_run_result.py
# code style: PEP 8

"""
Unit tests for RunResult functionality.
"""

import pytest
import json
from datetime import datetime

from src.agents.run_result import RunResult


class TestRunResult:
    """Test RunResult functionality."""

    def test_initialization_minimal(self):
        """Test minimal RunResult initialization."""
        result = RunResult(final_answer="Test answer")

        assert result.final_answer == "Test answer"
        assert result.error is None
        assert result.execution_time == 0.0
        assert result.steps == []
        assert result.token_usage == {"input": 0, "output": 0, "total": 0}
        assert result.agent_type == "unknown"
        assert result.model_info == {}
        assert isinstance(result.timestamp, datetime)

    def test_initialization_full(self):
        """Test full RunResult initialization."""
        result = RunResult(
            final_answer="Complete answer",
            error="Some error",
            execution_time=1.5,
            token_usage={"input": 100, "output": 50, "total": 150},
            agent_type="react",
            model_info={
                "orchestrator": "openai/claude-sonnet-4",
                "search": "openai/claude-sonnet-4"
            }
        )

        assert result.final_answer == "Complete answer"
        assert result.error == "Some error"
        assert result.execution_time == 1.5
        assert result.token_usage["total"] == 150
        assert result.agent_type == "react"
        assert result.model_info["orchestrator"] == "openai/claude-sonnet-4"

    def test_add_step(self):
        """Test adding steps to RunResult."""
        result = RunResult(final_answer="Test")

        # Add first step
        result.add_step({
            "type": "search",
            "content": "Searching for information",
            "timestamp": "2024-01-01T10:00:00"
        })

        assert len(result.steps) == 1
        assert result.steps[0]["type"] == "search"

        # Add second step
        result.add_step({
            "type": "reasoning",
            "content": "Processing results"
        })

        assert len(result.steps) == 2
        assert result.steps[1]["type"] == "reasoning"

    def test_success_property(self):
        """Test success property."""
        # Success case
        result1 = RunResult(final_answer="Answer")
        assert result1.success is True

        # Error case
        result2 = RunResult(final_answer="", error="Failed")
        assert result2.success is False

        # Both final answer and error
        result3 = RunResult(final_answer="Answer", error="Warning")
        assert result3.success is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = RunResult(
            final_answer="Test answer",
            execution_time=2.5,
            token_usage={"input": 200, "output": 100, "total": 300},
            agent_type="codact"
        )

        # Add a step
        result.add_step({"type": "code", "content": "print('hello')"})

        # Convert to dict
        data = result.to_dict()

        assert data["final_answer"] == "Test answer"
        assert data["success"] is True
        assert data["execution_time"] == 2.5
        assert data["token_usage"]["total"] == 300
        assert data["agent_type"] == "codact"
        assert len(data["steps"]) == 1
        assert isinstance(data["timestamp"], str)

    def test_to_json(self):
        """Test JSON serialization."""
        result = RunResult(
            final_answer="JSON test",
            token_usage={"input": 50, "output": 25, "total": 75}
        )

        # Convert to JSON
        json_str = result.to_json()

        # Parse back
        data = json.loads(json_str)

        assert data["final_answer"] == "JSON test"
        assert data["token_usage"]["total"] == 75

    def test_summary(self):
        """Test summary generation."""
        result = RunResult(
            final_answer="Summary test answer",
            execution_time=3.14159,
            token_usage={"input": 1000, "output": 500, "total": 1500},
            agent_type="react"
        )

        # Add steps
        result.add_step({"type": "search", "content": "Step 1"})
        result.add_step({"type": "read", "content": "Step 2"})
        result.add_step({"type": "reasoning", "content": "Step 3"})

        summary = result.summary()

        assert "React Agent Execution Summary" in summary
        assert "✓ Success" in summary
        assert "3.14 seconds" in summary
        assert "1500 tokens" in summary
        assert "3 steps" in summary
        assert "Answer: Summary test answer" in summary

    def test_summary_with_error(self):
        """Test summary with error."""
        result = RunResult(
            final_answer="",
            error="Connection timeout",
            execution_time=10.0,
            agent_type="codact"
        )

        summary = result.summary()

        assert "Codact Agent Execution Summary" in summary
        assert "✗ Failed" in summary
        assert "Error: Connection timeout" in summary
        assert "Answer:" not in summary

    def test_get_step_types(self):
        """Test getting unique step types."""
        result = RunResult(final_answer="Test")

        # Add various steps
        result.add_step({"type": "search", "content": "Search 1"})
        result.add_step({"type": "reasoning", "content": "Think"})
        result.add_step({"type": "search", "content": "Search 2"})
        result.add_step({"type": "code", "content": "Execute"})

        step_types = result.get_step_types()

        assert len(step_types) == 3
        assert "search" in step_types
        assert "reasoning" in step_types
        assert "code" in step_types

    def test_get_steps_by_type(self):
        """Test filtering steps by type."""
        result = RunResult(final_answer="Test")

        # Add various steps
        result.add_step({"type": "search", "content": "Search 1", "query": "AI"})
        result.add_step({"type": "reasoning", "content": "Think"})
        result.add_step({"type": "search", "content": "Search 2", "query": "ML"})

        # Get search steps
        search_steps = result.get_steps_by_type("search")

        assert len(search_steps) == 2
        assert search_steps[0]["query"] == "AI"
        assert search_steps[1]["query"] == "ML"

        # Get reasoning steps
        reasoning_steps = result.get_steps_by_type("reasoning")
        assert len(reasoning_steps) == 1
