#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/unit/test_base_agent.py
# code style: PEP 8

"""
Unit tests for BaseAgent functionality.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from smolagents import Tool, LiteLLMModel

from src.agents.base_agent import BaseAgent, MultiModelRouter
from src.agents.run_result import RunResult


class TestBaseAgent:
    """Test BaseAgent functionality."""

    @pytest.fixture
    def mock_models(self):
        """Create mock models."""
        search_model = MagicMock(spec=LiteLLMModel)
        search_model.model_id = "test-search"

        orchestrator_model = MagicMock(spec=LiteLLMModel)
        orchestrator_model.model_id = "test-orchestrator"

        return search_model, orchestrator_model

    @pytest.fixture
    def mock_tools(self):
        """Create mock tools."""
        tool1 = MagicMock(spec=Tool)
        tool1.name = "test_tool_1"

        tool2 = MagicMock(spec=Tool)
        tool2.name = "test_tool_2"

        return [tool1, tool2]

    @pytest.fixture
    def initial_state(self):
        """Create initial state."""
        return {
            "visited_urls": set(),
            "search_queries": [],
            "key_findings": {}
        }

    @pytest.fixture
    def test_agent(self, mock_models, mock_tools, initial_state):
        """Create a test implementation of BaseAgent."""
        search_model, orchestrator_model = mock_models

        class TestAgentImpl(BaseAgent):
            def create_agent(self):
                # Create a simple mock agent that allows attribute assignment
                class MockAgent:
                    def __init__(self, initial_state):
                        self.run = MagicMock(return_value="Test response")
                        self.memory = []
                        self.logs = []
                        # Use deepcopy to match the reset behavior
                        import copy
                        self.state = copy.deepcopy(initial_state)
                        self.stream_outputs = False

                    def reset(self):
                        """Reset method for compatibility with reset_agent_memory"""
                        self.memory = []
                        self.logs = []

                return MockAgent(self.initial_state)

        agent = TestAgentImpl(
            agent_type="test",
            orchestrator_model=orchestrator_model,
            search_model=search_model,
            tools=mock_tools,
            initial_state=initial_state,
            max_steps=10,
            planning_interval=4,
            name="DeepSearch Test Agent"
        )
        agent.initialize()
        return agent

    def test_initialization(self, test_agent, mock_models, mock_tools):
        """Test agent initialization."""
        search_model, orchestrator_model = mock_models

        assert test_agent.agent_type == "test"
        assert test_agent.orchestrator_model == orchestrator_model
        assert test_agent.search_model == search_model
        assert test_agent.tools == mock_tools
        assert test_agent.max_steps == 10
        assert test_agent.planning_interval == 4
        assert test_agent.name == "DeepSearch Test Agent"
        assert "test architecture" in test_agent.description

    def test_managed_agents_initialization(
        self,
        mock_models,
        mock_tools,
        initial_state
    ):
        """Test initialization with managed agents."""
        search_model, orchestrator_model = mock_models

        # Create managed agents
        managed1 = MagicMock(spec=BaseAgent)
        managed1.name = "managed_agent_1"

        managed2 = MagicMock(spec=BaseAgent)
        managed2.name = "managed_agent_2"

        class TestAgentImpl(BaseAgent):
            def create_agent(self):
                return MagicMock()

        agent = TestAgentImpl(
            agent_type="test",
            orchestrator_model=orchestrator_model,
            search_model=search_model,
            tools=mock_tools,
            initial_state=initial_state,
            name="Test Manager",
            description="Test manager agent",
            managed_agents=[managed1, managed2]
        )

        assert agent.name == "Test Manager"
        assert agent.description == "Test manager agent"
        assert len(agent.managed_agents) == 2
        assert agent.managed_agents[0] == managed1
        assert agent.managed_agents[1] == managed2

    def test_run_basic(self, test_agent):
        """Test basic run functionality."""
        result = test_agent.run("What Time is in USA(Central Time) of current?")

        assert result == "Test response"
        test_agent.agent.run.assert_called_once_with("What Time is in USA(Central Time) of current?")

    def test_run_with_return_result(self, test_agent):
        """Test run with RunResult return."""
        result = test_agent.run("What Time is in USA(West Time) of current?", return_result=True)

        assert isinstance(result, RunResult)
        assert result.final_answer == "Test response"
        assert result.agent_type == "test"
        assert result.execution_time > 0

    def test_run_with_error(self, test_agent):
        """Test run with error handling."""
        test_agent.agent.run.side_effect = ValueError("Test error")

        # Without return_result, should raise
        with pytest.raises(ValueError):
            test_agent.run("What Time is in USA(Mountain Time) of current?")

        # With return_result, should return RunResult with error
        result = test_agent.run("What Time is in USA(Mountain Time) of current?", return_result=True)
        assert isinstance(result, RunResult)
        assert result.error == "Agent execution failed: Test error"
        assert result.final_answer == ""

    def test_callable_interface(self, test_agent):
        """Test agent as callable (for managed agents)."""
        result = test_agent("What Time is in USA(Central Time) of current?", {"context": "additional"})

        assert result == "Test response"
        test_agent.agent.run.assert_called()

    def test_callable_with_error(self, test_agent):
        """Test callable interface error handling."""
        test_agent.agent.run.side_effect = RuntimeError("Execution failed")

        result = test_agent("What Time is in USA(Mountain Time) of current?")
        # The error message format: "Error executing sub-agent {name}: {error}"
        assert "Error executing sub-agent DeepSearch Test Agent" in result
        assert "Agent execution failed: Execution failed" in result

    def test_context_manager(self, test_agent):
        """Test context manager functionality."""
        with test_agent as agent:
            assert agent == test_agent

        # After exit, models should be cleared
        assert test_agent.orchestrator_model is None
        assert test_agent.search_model is None

    def test_reset_memory(self, test_agent):
        """Test memory reset functionality."""
        # Add some memory
        test_agent.agent.memory = ["item1", "item2"]
        test_agent.agent.logs = ["log1", "log2"]
        test_agent.agent.state["visited_urls"].add("http://example.com")

        # Reset memory
        test_agent.reset_agent_memory()

        assert test_agent.agent.memory == []
        assert test_agent.agent.logs == []
        # State should be reset to initial state (fresh copy)
        # The initial state has an empty set, so after reset it should be empty
        assert test_agent.agent.state["visited_urls"] == set()
        # Check all keys match initial state
        assert test_agent.agent.state["search_queries"] == []
        assert test_agent.agent.state["key_findings"] == {}

    def test_memory_summary(self, test_agent):
        """Test memory summary functionality."""
        # Set up memory
        test_agent.agent.memory = ["item1", "item2", "item3"]
        test_agent.agent.logs = ["log1", "log2"]

        summary = test_agent.get_memory_summary()

        assert summary["agent_type"] == "test"
        assert summary["memory_length"] == 3
        assert summary["logs_length"] == 2
        assert summary["has_planning_memory"] is False
        assert "visited_urls" in summary["state_keys"]

    def test_optimize_memory_for_planning(self, test_agent):
        """Test memory optimization for planning."""
        # Add many memory items
        test_agent.agent.memory = [f"item{i}" for i in range(20)]

        test_agent.optimize_memory_for_planning()

        # Should keep only last 10 items
        assert len(test_agent.agent.memory) == 10
        assert test_agent.agent.memory[0] == "item10"
        assert test_agent.agent.memory[-1] == "item19"

    def test_streaming_mode(self, test_agent):
        """Test streaming mode activation."""
        # Mock streaming generator
        def mock_stream():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        test_agent.agent.run = MagicMock(return_value=mock_stream())
        test_agent.agent.stream_outputs = False

        result = test_agent.run("What Time is in USA(Central Time) of current?", stream=True)

        # Should return generator
        chunks = list(result)
        assert chunks == ["chunk1", "chunk2", "chunk3"]
        assert test_agent.agent.stream_outputs is True

    def test_run_with_images_and_reset(self, test_agent):
        """Test run with additional parameters."""
        # Mock agent.run to accept additional params
        test_agent.agent.run = MagicMock(return_value="Response with image")

        result = test_agent.run(
            "What is this image about?",
            images=["https://react-lm.github.io/files/diagram.png"],
            reset=True,
            additional_args={"key": "value"}
        )

        assert result == "Response with image"
        # Memory should be reset before run
        assert test_agent.agent.memory == []

    def test_token_usage_tracking(
        self,
        mock_models,
        mock_tools,
        initial_state
    ):
        """Test token usage tracking with MultiModelRouter."""
        search_model, orchestrator_model = mock_models

        # Create router
        router = MultiModelRouter(search_model, orchestrator_model)
        router.last_input_token_count = 150
        router.last_output_token_count = 75

        class TestAgentImpl(BaseAgent):
            def create_agent(self):
                agent = MagicMock()
                agent.run = MagicMock(return_value="Response")
                return agent

        agent = TestAgentImpl(
            agent_type="test",
            orchestrator_model=router,
            search_model=search_model,
            tools=mock_tools,
            initial_state=initial_state
        )
        agent.initialize()

        result = agent.run("What Time is in USA(Central Time) of current?", return_result=True)

        assert result.token_usage["input"] == 150
        assert result.token_usage["output"] == 75
        assert result.token_usage["total"] == 225
