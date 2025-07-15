#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/integration/test_managed_agents.py
# code style: PEP 8

"""
Integration tests for managed agents functionality.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.agents.runtime import AgentRuntime
from src.agents.base_agent import BaseAgent
from src.agents.react_agent import ReactAgent
from src.agents.codact_agent import CodeActAgent
from src.agents.manager_agent import ManagerAgent


class TestManagedAgentsIntegration:
    """Test managed agents integration."""

    @pytest.fixture
    def runtime(self, test_settings):
        """Create test runtime."""
        # Skip if no API keys
        runtime = AgentRuntime(settings_obj=test_settings)
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        return runtime

    @pytest.mark.integration
    @pytest.mark.requires_llm
    def test_manager_with_sub_agents(self, runtime, cleanup_agents):
        """Test manager agent with sub-agents."""
        # Create sub-agents
        react_agent = cleanup_agents(runtime.create_react_agent())
        codact_agent = cleanup_agents(runtime.create_codact_agent())

        # Create manager with sub-agents
        manager = cleanup_agents(runtime.create_manager_agent(
            managed_agents=[react_agent, codact_agent]
        ))

        # Verify manager has access to sub-agents
        assert len(manager.managed_agents) == 2
        assert any(a.name == react_agent.name for a in manager.managed_agents)
        assert any(a.name == codact_agent.name for a in manager.managed_agents)

    @pytest.mark.integration
    def test_agent_callable_interface(self, runtime, cleanup_agents):
        """Test agents can be called as tools."""
        agent = cleanup_agents(runtime.create_react_agent())

        # Call agent as a tool
        result = agent("solve a x^2 + b x + c = 0 for x ?")

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_hierarchical_delegation(self, runtime, cleanup_agents):
        """Test hierarchical task delegation."""
        # Create specialized agents
        search_agent = cleanup_agents(runtime.create_react_agent())
        search_agent.name = "search_specialist"
        search_agent.description = "Specializes in web search"

        code_agent = cleanup_agents(runtime.create_codact_agent())
        code_agent.name = "code_specialist"
        code_agent.description = "Specializes in code generation"

        # Create manager
        manager = cleanup_agents(runtime.create_manager_agent(
            managed_agents=[search_agent, code_agent]
        ))

        # Test delegation
        result = manager.delegate_task(
            task="Find the latest litellm nightly-version",
            target_agent="search_specialist"
        )

        assert isinstance(result, str)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_complex_orchestration(self, runtime, cleanup_agents):
        """Test complex task orchestration."""
        # Create agents
        react_agent = cleanup_agents(runtime.create_react_agent())
        codact_agent = cleanup_agents(runtime.create_codact_agent())

        manager = cleanup_agents(runtime.create_manager_agent(
            managed_agents=[react_agent, codact_agent]
        ))

        # Analyze complex task
        task = "Research litellm latest dev-version changelog of new features"
        analysis = manager.analyze_task(task)

        assert analysis["complexity"] in ["complex", "moderate"]
        assert analysis["requires_delegation"] is True

    @pytest.mark.integration
    def test_agent_state_isolation(self, runtime, cleanup_agents):
        """Test that managed agents maintain isolated state."""
        # Create two agents
        agent1 = cleanup_agents(runtime.create_react_agent())
        agent2 = cleanup_agents(runtime.create_react_agent())

        # Modify agent1 state
        if hasattr(agent1, 'agent') and hasattr(agent1.agent, 'state'):
            agent1.agent.state["test_key"] = "agent1_value"

        # Verify agent2 state is not affected
        if hasattr(agent2, 'agent') and hasattr(agent2.agent, 'state'):
            assert "test_key" not in agent2.agent.state

    @pytest.mark.integration
    def test_manager_agent_from_runtime(self, runtime, cleanup_agents):
        """Test creating manager agent through runtime."""
        manager = cleanup_agents(
            runtime.get_or_create_agent("manager")
        )

        assert manager.name == "DeepSearch Manager Agent"
        assert len(manager.managed_agents) > 0
        assert manager.agent_type == "react"  # Manager extends ReactAgent
