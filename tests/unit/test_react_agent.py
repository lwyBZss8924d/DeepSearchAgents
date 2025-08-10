#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/unit/test_react_agent.py
# code style: PEP 8

"""
Unit tests for ReactAgent functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from smolagents import Tool, LiteLLMModel, ToolCallingAgent

from src.agents.react_agent import ReactAgent
from src.agents.base_agent import MultiModelRouter


class TestReactAgent:
    """Test ReactAgent functionality."""

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
        search_tool = MagicMock(spec=Tool)
        search_tool.name = "search_links"
        search_tool.description = "Search the web"

        read_tool = MagicMock(spec=Tool)
        read_tool.name = "read_url"
        read_tool.description = "Read URL content"

        final_tool = MagicMock(spec=Tool)
        final_tool.name = "final_answer"
        final_tool.description = "Generate final answer"

        return [search_tool, read_tool, final_tool]

    @pytest.fixture
    def initial_state(self):
        """Create initial state."""
        return {
            "visited_urls": set(),
            "search_queries": [],
            "key_findings": {},
            "search_depth": {},
            "reranking_history": [],
            "content_quality": {}
        }

    @pytest.fixture
    def react_agent(self, mock_models, mock_tools, initial_state):
        """Create ReactAgent instance."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.react_agent.ToolCallingAgent'):
            agent = ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                max_steps=5,
                planning_interval=2
            )
            return agent

    def test_initialization(self, react_agent, mock_tools):
        """Test ReactAgent initialization."""
        assert react_agent.agent_type == "react"
        assert react_agent.max_steps == 5
        assert react_agent.planning_interval == 2
        assert react_agent.tools == mock_tools
        assert react_agent.max_tool_threads == 4  # default value

    def test_managed_agents_support(self, mock_models, mock_tools, initial_state):
        """Test ReactAgent with managed agents."""
        search_model, orchestrator_model = mock_models

        # Create managed agents
        managed1 = MagicMock()
        managed1.name = "sub_agent_1"

        managed2 = MagicMock()
        managed2.name = "sub_agent_2"

        with patch('src.agents.react_agent.ToolCallingAgent') as mock_agent_class:
            ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                managed_agents=[managed1, managed2]
            )

            # Verify ToolCallingAgent was called
            mock_agent_class.assert_called_once()
            call_kwargs = mock_agent_class.call_args.kwargs
            # managed_agents is not passed to ToolCallingAgent directly
            assert 'managed_agents' not in call_kwargs

    def test_parallel_tool_execution_config(self, mock_models, mock_tools, initial_state):
        """Test parallel tool execution configuration."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.react_agent.ToolCallingAgent') as mock_agent_class:
            ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                max_tool_threads=8  # Custom thread count
            )

            # Verify max_tool_threads was passed
            call_kwargs = mock_agent_class.call_args.kwargs
            assert call_kwargs['max_tool_threads'] == 8

    def test_model_router_creation(self, mock_models, mock_tools, initial_state):
        """Test MultiModelRouter creation."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.react_agent.ToolCallingAgent') as mock_agent_class:
            ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state
            )

            # Verify model router was created
            call_args = mock_agent_class.call_args
            model_arg = call_args.kwargs['model']

            assert isinstance(model_arg, MultiModelRouter)
            assert model_arg.search_model == search_model
            assert model_arg.orchestrator_model == orchestrator_model

    def test_prompt_configuration(self, mock_models, mock_tools, initial_state):
        """Test prompt template configuration."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.react_agent.ToolCallingAgent') as mock_agent_class:
            ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state
            )

            # Verify prompt templates were passed
            call_kwargs = mock_agent_class.call_args.kwargs
            assert 'prompt_templates' in call_kwargs
            assert call_kwargs['prompt_templates'] is not None

    def test_streaming_configuration(self, mock_models, mock_tools, initial_state):
        """Test streaming configuration."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.react_agent.ToolCallingAgent') as mock_agent_class:
            # Test with streaming enabled
            ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                enable_streaming=True
            )

            call_kwargs = mock_agent_class.call_args.kwargs
            assert call_kwargs['stream_outputs'] is True

            # Test with streaming disabled
            ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                enable_streaming=False
            )

            call_kwargs2 = mock_agent_class.call_args.kwargs
            assert call_kwargs2['stream_outputs'] is False

    def test_step_callbacks(self, mock_models, mock_tools, initial_state):
        """Test step callback configuration."""
        search_model, orchestrator_model = mock_models

        # Create custom callback
        custom_callback = MagicMock()

        with patch('src.agents.react_agent.ToolCallingAgent') as mock_agent_class:
            agent = ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                step_callbacks=[custom_callback]
            )

            call_kwargs = mock_agent_class.call_args.kwargs
            assert 'step_callbacks' in call_kwargs
            assert custom_callback in call_kwargs['step_callbacks']

    def test_agent_state_initialization(self, mock_models, mock_tools, initial_state):
        """Test agent state initialization."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.react_agent.ToolCallingAgent') as mock_agent_class:
            # Create mock agent instance
            mock_agent_instance = MagicMock()
            mock_agent_instance.state = {}
            mock_agent_class.return_value = mock_agent_instance

            agent = ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state
            )

            # Verify state was set after ToolCallingAgent creation
            assert mock_agent_instance.state == initial_state

    def test_custom_name_and_description(self, mock_models, mock_tools, initial_state):
        """Test custom name and description."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.react_agent.ToolCallingAgent'):
            react_agent = ReactAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                name="Custom React Agent",
                description="Custom description for testing"
            )

            assert react_agent.name == "Custom React Agent"
            assert react_agent.description == "Custom description for testing"
