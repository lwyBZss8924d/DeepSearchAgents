#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/compatibility/test_backward_compatibility.py
# code style: PEP 8

"""
Backward compatibility tests for v0.2.8 to v0.2.9 upgrade.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.agents.runtime import AgentRuntime
from src.agents.base_agent import BaseAgent
from src.agents.react_agent import ReactAgent
from src.agents.codact_agent import CodeActAgent


class TestBackwardCompatibility:
    """Test backward compatibility with v0.2.8."""
    
    @pytest.fixture
    def runtime(self, test_settings):
        """Create test runtime."""
        runtime = AgentRuntime(settings_obj=test_settings)
        return runtime
    
    @pytest.mark.compatibility
    def test_legacy_agent_creation(self, runtime):
        """Test legacy agent creation patterns still work."""
        # Legacy pattern without managed agents
        react_agent = runtime.create_react_agent()
        assert react_agent is not None
        assert react_agent.managed_agents == []
        
        codact_agent = runtime.create_codact_agent()
        assert codact_agent is not None
        assert codact_agent.managed_agents == []
    
    @pytest.mark.compatibility
    def test_legacy_run_method(self, runtime, cleanup_agents):
        """Test legacy run method patterns."""
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        
        agent = cleanup_agents(runtime.create_react_agent())
        
        # Legacy call - returns RunResult in v1.19.0
        result = agent.run("What is 2 + 2?")
        
        # In smolagents v1.19.0, run() always returns RunResult
        if hasattr(result, 'final_answer'):
            # RunResult object
            assert result.final_answer is not None
            assert hasattr(result, 'token_usage')
        else:
            # Direct string result (legacy behavior)
            assert isinstance(result, str)
    
    @pytest.mark.compatibility
    def test_legacy_state_format(self, runtime):
        """Test compatibility with legacy state format."""
        # Legacy state with list instead of set
        legacy_state = {
            "visited_urls": ["url1", "url2"],  # List in v0.2.8
            "search_queries": [],
            "key_findings": {}
        }
        
        # Create runtime with custom initial state
        runtime._get_initial_state = lambda: legacy_state
        
        # Should handle conversion automatically during agent creation
        agent = runtime.create_codact_agent()
        
        # Should be converted to set in the agent's state
        if hasattr(agent, 'agent') and hasattr(agent.agent, 'state'):
            assert isinstance(agent.agent.state.get("visited_urls"), set)
        else:
            # For BaseAgent, check initial_state
            assert isinstance(agent.initial_state["visited_urls"], set)
    
    @pytest.mark.compatibility
    def test_legacy_tool_usage(self, runtime, cleanup_agents):
        """Test that legacy tool usage patterns still work."""
        agent = cleanup_agents(runtime.create_react_agent())
        
        # Verify tools are accessible as before
        if hasattr(agent, 'agent') and hasattr(agent.agent, 'tools'):
            tools = agent.agent.tools
            assert len(tools) > 0
            
            # Common tools should still exist
            tool_names = list(tools.keys())
            expected_tools = ["search_links", "read_url", "final_answer"]
            for expected in expected_tools:
                assert any(expected in name for name in tool_names)
    
    @pytest.mark.compatibility
    def test_legacy_streaming_parameter(self, runtime, cleanup_agents):
        """Test legacy streaming parameter handling."""
        agent = cleanup_agents(runtime.create_react_agent())
        
        # Legacy streaming=False (default)
        result = agent.run("Test query", stream=False)
        assert isinstance(result, str)
        
        # Streaming=True should work (even if disabled in config)
        result_stream = agent.run("Test query", stream=True)
        # Could be generator or string depending on config
        assert result_stream is not None
    
    @pytest.mark.compatibility
    def test_legacy_config_parameters(self, test_settings):
        """Test legacy configuration parameters."""
        # These parameters should still work
        legacy_params = {
            "ORCHESTRATOR_MODEL_ID": test_settings.ORCHESTRATOR_MODEL_ID,
            "SEARCH_MODEL_NAME": test_settings.SEARCH_MODEL_NAME,
            "REACT_MAX_STEPS": test_settings.REACT_MAX_STEPS,
            "CODACT_MAX_STEPS": test_settings.CODACT_MAX_STEPS,
            "ENABLE_STREAMING": test_settings.ENABLE_STREAMING
        }
        
        for param, value in legacy_params.items():
            assert value is not None
    
    @pytest.mark.compatibility
    def test_legacy_api_compatibility(self, runtime):
        """Test that public API remains compatible."""
        # AgentRuntime methods
        assert hasattr(runtime, 'create_react_agent')
        assert hasattr(runtime, 'create_codact_agent')
        assert hasattr(runtime, 'get_or_create_agent')
        assert hasattr(runtime, 'run')
        
        # Agent methods
        agent = runtime.create_react_agent()
        assert hasattr(agent, 'run')
        assert hasattr(agent, 'reset_agent_memory')
        assert hasattr(agent, 'get_memory_summary')
    
    @pytest.mark.compatibility
    def test_legacy_error_handling(self, runtime, cleanup_agents):
        """Test that error handling remains compatible."""
        agent = cleanup_agents(runtime.create_react_agent())
        
        # Mock agent to raise error
        if hasattr(agent, 'agent'):
            agent.agent.run = MagicMock(side_effect=ValueError("Test error"))
        
        # In v1.19.0, errors are still raised
        with pytest.raises(ValueError):
            agent.run("Error query")
    
    @pytest.mark.compatibility
    def test_legacy_context_manager(self, runtime):
        """Test legacy context manager usage."""
        # Should work as before
        with runtime.create_react_agent() as agent:
            assert agent is not None
            assert hasattr(agent, 'run')
        
        # After exit, cleanup should have occurred
        assert agent.orchestrator_model is None
        assert agent.search_model is None
    
    @pytest.mark.compatibility
    def test_legacy_prompt_templates(self):
        """Test that legacy prompt templates still work."""
        # Import should work
        from src.agents.prompt_templates.react_prompts import REACT_PROMPT
        from src.agents.prompt_templates.codact_prompts import (
            CODACT_SYSTEM_EXTENSION, PLANNING_TEMPLATES
        )
        
        assert REACT_PROMPT is not None
        assert CODACT_SYSTEM_EXTENSION is not None
        assert PLANNING_TEMPLATES is not None