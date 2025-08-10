#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/unit/test_manager_agent.py
# code style: PEP 8

"""
Unit tests for ManagerAgent functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from smolagents import Tool, LiteLLMModel

from src.agents.manager_agent import ManagerAgent
from src.agents.base_agent import BaseAgent


class TestManagerAgent:
    """Test ManagerAgent functionality."""

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
        tool = MagicMock(spec=Tool)
        tool.name = "basic_tool"
        return [tool]

    @pytest.fixture
    def mock_managed_agents(self):
        """Create mock managed agents."""
        agent1 = MagicMock(spec=BaseAgent)
        agent1.name = "research_agent"
        agent1.description = "Agent for research tasks"
        agent1.return_value = "Research result"

        agent2 = MagicMock(spec=BaseAgent)
        agent2.name = "code_agent"
        agent2.description = "Agent for coding tasks"
        agent2.return_value = "Code result"

        return [agent1, agent2]

    @pytest.fixture
    def initial_state(self):
        """Create initial state."""
        return {
            "visited_urls": set(),
            "task_history": [],
            "delegation_count": 0
        }

    @pytest.fixture
    def manager_agent(
        self,
        mock_models,
        mock_tools,
        mock_managed_agents,
        initial_state
    ):
        """Create ManagerAgent instance."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.manager_agent.ToolCallingAgent'):
            agent = ManagerAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                managed_agents=mock_managed_agents,
                max_steps=10
            )
            return agent

    def test_initialization(self, manager_agent, mock_managed_agents):
        """Test ManagerAgent initialization."""
        assert manager_agent.agent_type == "react"  # Inherits from ReactAgent
        assert len(manager_agent.managed_agents) == 2
        assert manager_agent.max_delegation_depth == 3  # default
        assert manager_agent.name == "DeepSearch Manager Agent"
        assert "orchestrates" in manager_agent.description

    def test_managed_agents_as_tools(
        self,
        mock_models,
        mock_tools,
        mock_managed_agents,
        initial_state
    ):
        """Test that managed agents are properly registered."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.react_agent.ToolCallingAgent') \
                as mock_agent_class:
            manager = ManagerAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                managed_agents=mock_managed_agents
            )

            # Get the actual call arguments
            assert mock_agent_class.called
            call_kwargs = mock_agent_class.call_args.kwargs

            # Check tools
            tools = call_kwargs['tools']
            if isinstance(tools, list):
                tools_dict = {t.name: t for t in tools}
            else:
                tools_dict = tools

            # Should have the basic tool
            assert "basic_tool" in tools_dict

            # Managed agents are not passed directly to ToolCallingAgent
            # They are stored in the ManagerAgent instance
            assert 'managed_agents' not in call_kwargs

            # Verify managed agents are stored in the manager
            assert len(manager.managed_agents) == 2

    def test_delegation_state_tracking(self, manager_agent):
        """Test delegation state tracking."""
        # Initial state
        assert "delegation_history" in manager_agent.initial_state
        assert "current_delegation_depth" in manager_agent.initial_state
        assert manager_agent.initial_state["current_delegation_depth"] == 0

    def test_delegate_task(self, manager_agent, mock_managed_agents):
        """Test task delegation."""
        result = manager_agent.delegate_task(
            task="Research AI trends",
            target_agent="research_agent",
            additional_context={"focus": "2024 trends"}
        )

        assert result == "Research result"
        # Check that the agent was called
        assert mock_managed_agents[0].called
        # Check call arguments
        call_args = mock_managed_agents[0].call_args
        assert call_args[0][0] == "Research AI trends"
        assert call_args[0][1]["focus"] == "2024 trends"
        assert call_args[0][1]["delegation_depth"] == 1

    def test_delegate_task_not_found(self, manager_agent):
        """Test delegation to non-existent agent."""
        result = manager_agent.delegate_task(
            task="Unknown task",
            target_agent="unknown_agent"
        )

        assert "not found" in result

    def test_analyze_task_simple(self, manager_agent):
        """Test task analysis for simple tasks."""
        analysis = manager_agent.analyze_task("What is 2 + 2?")

        assert analysis["complexity"] == "simple"
        assert analysis["requires_delegation"] is False
        assert analysis["suggested_agent"] is None

    def test_analyze_task_complex(self, manager_agent):
        """Test task analysis for complex tasks."""
        analysis = manager_agent.analyze_task(
            "Research the latest litellm nightly-version full changelog of new features and analyze the key improvements"
        )

        assert analysis["complexity"] == "complex"
        assert analysis["requires_delegation"] is True
        assert len(analysis["subtasks"]) > 0

    def test_analyze_task_research(self, manager_agent):
        """Test task analysis for research tasks."""
        analysis = manager_agent.analyze_task(
            "Find information about langgraph python latest version full changelog of new features"
        )

        assert analysis["task_type"] == "research"
        assert analysis["suggested_agent"] == "research_agent"

    def test_analyze_task_coding(self, manager_agent):
        """Test task analysis for coding tasks."""
        analysis = manager_agent.analyze_task(
            "Write a Python function to sort a list of random numbers"
        )

        assert analysis["task_type"] == "coding"
        assert analysis["suggested_agent"] == "code_agent"

    def test_max_delegation_depth(
        self,
        mock_models,
        mock_tools,
        mock_managed_agents,
        initial_state
    ):
        """Test max delegation depth configuration."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.manager_agent.ToolCallingAgent'):
            manager_agent = ManagerAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                managed_agents=mock_managed_agents,
                max_delegation_depth=5
            )

            assert manager_agent.max_delegation_depth == 5

    def test_custom_name_description(
        self,
        mock_models,
        mock_tools,
        mock_managed_agents,
        initial_state
    ):
        """Test custom name and description."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.manager_agent.ToolCallingAgent'):
            manager_agent = ManagerAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                managed_agents=mock_managed_agents,
                name="Custom Manager",
                description="Custom manager description"
            )

            assert manager_agent.name == "Custom Manager"
            assert manager_agent.description == "Custom manager description"

    def test_orchestrate_complex_task(self, manager_agent):
        """Test orchestration of complex tasks."""
        result = manager_agent.orchestrate_complex_task(
            task="Build a web scraper and analyze the data",
            analysis={
                "complexity": "complex",
                "subtasks": [
                    {"task": "Build scraper", "agent": "code_agent"},
                    {"task": "Analyze data", "agent": "research_agent"}
                ]
            }
        )

        assert "results" in result
        assert "summary" in result
        assert len(result["results"]) == 2
