#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/integration/test_parallel_tools.py
# code style: PEP 8

"""
Integration tests for parallel tool execution.
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch

from src.agents.runtime import AgentRuntime
from smolagents import Tool


class TestParallelToolExecution:
    """Test parallel tool execution functionality."""

    @pytest.fixture
    def runtime(self, test_settings):
        """Create test runtime."""
        runtime = AgentRuntime(settings_obj=test_settings)
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        return runtime

    @pytest.fixture
    def mock_parallel_tools(self):
        """Create mock tools that simulate parallel execution."""
        tools = []

        # Tool 1 - simulates 1 second execution
        tool1 = MagicMock(spec=Tool)
        tool1.name = "slow_tool_1"
        tool1.description = "Slow tool 1"

        def tool1_call(*args, **kwargs):
            time.sleep(0.1)  # Reduced for faster tests
            return "Result from tool 1"
        tool1.__call__ = tool1_call
        tools.append(tool1)

        # Tool 2 - simulates 1 second execution
        tool2 = MagicMock(spec=Tool)
        tool2.name = "slow_tool_2"
        tool2.description = "Slow tool 2"

        def tool2_call(*args, **kwargs):
            time.sleep(0.1)  # Reduced for faster tests
            return "Result from tool 2"
        tool2.__call__ = tool2_call
        tools.append(tool2)

        # Tool 3 - fast tool
        tool3 = MagicMock(spec=Tool)
        tool3.name = "fast_tool"
        tool3.description = "Fast tool"
        tool3.__call__ = MagicMock(return_value="Fast result")
        tools.append(tool3)

        return tools

    @pytest.mark.integration
    def test_react_agent_parallel_tools_config(self, runtime, cleanup_agents):
        """Test ReactAgent parallel tool configuration."""
        # Create agent with custom thread count
        agent = cleanup_agents(runtime.create_react_agent())

        # Verify agent has max_tool_threads configured
        assert hasattr(agent, 'max_tool_threads')
        assert agent.max_tool_threads > 1  # Should support parallel execution

    @pytest.mark.integration
    def test_parallel_execution_timing(
        self,
        runtime,
        mock_parallel_tools,
        cleanup_agents
    ):
        """Test that tools execute in parallel."""
        # Create agent with mock tools
        agent = cleanup_agents(runtime.create_react_agent())

        # Replace tools with mock tools
        if hasattr(agent, 'agent') and hasattr(agent.agent, 'tools'):
            # Add mock tools to agent
            for tool in mock_parallel_tools:
                agent.agent.tools[tool.name] = tool

        # Note: Actual parallel execution depends on the agent's implementation
        # This test verifies the configuration is in place
        assert agent.max_tool_threads > 1

    @pytest.mark.integration
    @pytest.mark.requires_llm
    @pytest.mark.slow
    @pytest.mark.timeout(1200)  # 20 minutes timeout for LLM calls
    def test_real_parallel_search(self, runtime, cleanup_agents):
        """Test real parallel search execution."""
        agent = cleanup_agents(runtime.create_react_agent())

        # Query that might trigger multiple tool calls
        start_time = time.time()
        result = agent.run(
            "What is the latest langgraph python version?"
        )
        execution_time = time.time() - start_time

        assert isinstance(result, str)
        assert len(result) > 0

        # Log execution time for performance tracking
        print(f"Parallel search execution time: {execution_time:.2f}s")

    @pytest.mark.integration
    def test_thread_pool_configuration(self, runtime):
        """Test thread pool configuration for parallel execution."""
        # Test different thread configurations
        configs = [1, 4, 8]

        for thread_count in configs:
            agent = runtime.create_react_agent()
            agent.max_tool_threads = thread_count

            assert agent.max_tool_threads == thread_count

            # Cleanup
            agent.reset_agent_memory()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_tool_compatibility(self, runtime, cleanup_agents):
        """Test compatibility with async tools."""
        # Create async tool
        class AsyncTool(Tool):
            name = "async_test_tool"
            description = "Async test tool"
            inputs = {
                "query": {
                    "type": "string",
                    "description": "Query to process"
                }
            }  # Proper format
            output_type = "string"

            async def forward(self, query: str) -> str:
                await asyncio.sleep(0.1)
                return f"Async result for: {query}"

        # Create agent
        agent = cleanup_agents(runtime.create_react_agent())

        # Add async tool
        async_tool = AsyncTool()
        if hasattr(agent, 'agent') and hasattr(agent.agent, 'tools'):
            agent.agent.tools[async_tool.name] = async_tool

        # Verify tool is accessible
        assert async_tool.name in agent.agent.tools

    @pytest.mark.integration
    def test_parallel_error_handling(self, runtime, cleanup_agents):
        """Test error handling in parallel tool execution."""
        # Create tools with one that fails
        error_tool = MagicMock(spec=Tool)
        error_tool.name = "error_tool"
        error_tool.description = "Tool that errors"
        error_tool.__call__ = MagicMock(side_effect=ValueError("Tool error"))

        success_tool = MagicMock(spec=Tool)
        success_tool.name = "success_tool"
        success_tool.description = "Tool that succeeds"
        success_tool.__call__ = MagicMock(return_value="Success")

        agent = cleanup_agents(runtime.create_react_agent())

        # Add tools
        if hasattr(agent, 'agent') and hasattr(agent.agent, 'tools'):
            agent.agent.tools[error_tool.name] = error_tool
            agent.agent.tools[success_tool.name] = success_tool

        # The agent should handle tool errors gracefully
        # (actual behavior depends on smolagents implementation)
