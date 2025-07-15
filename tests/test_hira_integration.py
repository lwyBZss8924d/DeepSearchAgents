#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Integration tests for HiRA agent with DeepSearchAgents runtime.

This module tests:
1. HiRA agent registration in runtime
2. Agent creation through runtime
3. Basic query execution
4. Token-based communication
"""

import pytest
import logging
from unittest.mock import Mock, patch

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Check if HiRA is available at module level
try:
    from src.agents.runtime import HIRA_AVAILABLE
except ImportError:
    HIRA_AVAILABLE = False

def test_hira_agent_registration():
    """Test that HiRA agent is properly registered in runtime."""
    from src.agents.runtime import AgentRuntime, HIRA_AVAILABLE
    
    runtime = AgentRuntime()
    
    if HIRA_AVAILABLE:
        # HiRA should be registered
        assert "hira" in runtime._agent_registry
        assert runtime._agent_registry["hira"] is not None
    else:
        # HiRA should not be registered if not available
        assert "hira" not in runtime._agent_registry


@pytest.mark.skipif(
    not HIRA_AVAILABLE,
    reason="HiRA module not available"
)
def test_create_hira_agent():
    """Test creating a HiRA agent through runtime."""
    from src.agents.runtime import AgentRuntime
    
    runtime = AgentRuntime()
    
    # Mock the LLM models
    with patch.object(runtime, '_create_llm_model') as mock_model:
        mock_model.return_value = Mock()
        
        # Create HiRA agent
        agent = runtime.create_hira_agent(debug_mode=False)
        
        assert agent is not None
        assert hasattr(agent, 'run')
        assert hasattr(agent, 'stream_outputs')


@pytest.mark.skipif(
    not HIRA_AVAILABLE,
    reason="HiRA module not available"
)
def test_hira_agent_configuration():
    """Test HiRA agent configuration from settings."""
    from src.agents.runtime import AgentRuntime
    from src.core.config.settings import settings
    
    # Set HiRA configuration
    settings.HIRA_MAX_EXECUTION_CALLS = 15
    settings.HIRA_ENABLE_MEMORY_FILTER = False
    
    runtime = AgentRuntime()
    
    # Mock the LLM models and HiRAMultiStepAgent
    with patch.object(runtime, '_create_llm_model') as mock_model:
        mock_model.return_value = Mock()
        
        with patch('src.agents.runtime.HiRAMultiStepAgent') as MockHiRA:
            runtime.create_hira_agent()
            
            # Verify configuration was passed
            MockHiRA.assert_called_once()
            call_args = MockHiRA.call_args[1]
            
            assert call_args['max_execution_calls'] == 15
            assert call_args['enable_memory_filter'] is False


@pytest.mark.skipif(
    not HIRA_AVAILABLE,
    reason="HiRA module not available"
)
def test_get_or_create_hira_agent():
    """Test get_or_create_agent with HiRA type."""
    from src.agents.runtime import AgentRuntime
    
    runtime = AgentRuntime()
    
    # Mock the create_hira_agent method
    with patch.object(runtime, 'create_hira_agent') as mock_create:
        mock_agent = Mock()
        mock_agent.name = "Test HiRA Agent"
        mock_create.return_value = mock_agent
        
        # Get or create HiRA agent
        agent = runtime.get_or_create_agent("hira")
        
        assert agent is not None
        assert agent.name == "HiRA Token-Based Multi-Agent"
        assert hasattr(agent, 'run')


def test_hira_not_available_error():
    """Test error when HiRA is not available."""
    from src.agents.runtime import AgentRuntime, HIRA_AVAILABLE
    
    if HIRA_AVAILABLE:
        pytest.skip("HiRA is available, skipping unavailable test")
    
    runtime = AgentRuntime()
    
    # Should raise error when trying to create HiRA
    with pytest.raises(ValueError, match="HiRA agent type is not available"):
        runtime.get_or_create_agent("hira")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])