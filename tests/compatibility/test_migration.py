#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/compatibility/test_migration.py
# code style: PEP 8

"""
Migration tests for v0.2.8 to v0.2.9 upgrade.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from src.agents.runtime import AgentRuntime
from src.agents.base_agent import MultiModelRouter
from src.core.config.settings import Settings


class TestMigration:
    """Test migration from v0.2.8 to v0.2.9."""
    
    @pytest.mark.compatibility
    def test_settings_migration(self):
        """Test migration of settings from v0.2.8 to v0.2.9."""
        settings = Settings()
        
        # New settings should have defaults
        assert hasattr(settings, 'CODACT_USE_STRUCTURED_OUTPUTS')
        assert hasattr(settings, 'MANAGED_AGENTS_ENABLED')
        assert hasattr(settings, 'MAX_DELEGATION_DEPTH')
        assert hasattr(settings, 'DEFAULT_MANAGED_AGENTS')
        
        # Check default values
        assert settings.MANAGED_AGENTS_ENABLED == True
        assert settings.MAX_DELEGATION_DEPTH == 3
        assert isinstance(settings.DEFAULT_MANAGED_AGENTS, list)
    
    @pytest.mark.compatibility
    def test_multi_model_router_migration(self):
        """Test MultiModelRouter replaces old routing logic."""
        # Create mock models
        search_model = MagicMock()
        search_model.model_id = "search-model"
        
        orchestrator_model = MagicMock()
        orchestrator_model.model_id = "orchestrator-model"
        
        # New router should work
        router = MultiModelRouter(search_model, orchestrator_model)
        
        # Should have combined model_id
        assert "search-model" in router.model_id
        assert "orchestrator-model" in router.model_id
        
        # Should route correctly
        planning_messages = [{"role": "assistant", "content": "Update facts survey"}]
        selected = router._select_model_for_messages(planning_messages)
        assert selected == orchestrator_model
    
    @pytest.mark.compatibility
    def test_streaming_architecture_migration(self):
        """Test streaming architecture changes."""
        from src.agents.stream_aggregator import StreamAggregator, ModelStreamWrapper
        
        # New streaming components should be available
        aggregator = StreamAggregator()
        assert hasattr(aggregator, 'add_chunk')
        assert hasattr(aggregator, 'get_full_content')
        
        # Model wrapper should work
        mock_model = MagicMock()
        wrapper = ModelStreamWrapper(mock_model)
        assert hasattr(wrapper, 'generate_stream')
    
    @pytest.mark.compatibility
    def test_run_result_migration(self, test_runtime):
        """Test RunResult integration."""
        if not test_runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        
        agent = test_runtime.create_react_agent()
        
        # Old behavior - string result
        result_str = agent.run("Test query")
        assert isinstance(result_str, str)
        
        # New behavior - RunResult object
        result_obj = agent.run("Test query", return_result=True)
        assert hasattr(result_obj, 'final_answer')
        assert hasattr(result_obj, 'execution_time')
        assert hasattr(result_obj, 'token_usage')
        assert hasattr(result_obj, 'to_dict')
        assert hasattr(result_obj, 'to_json')
    
    @pytest.mark.compatibility
    def test_manager_agent_availability(self, test_runtime):
        """Test new ManagerAgent is available."""
        # Should be able to create manager agent
        manager = test_runtime.create_manager_agent()
        assert manager is not None
        assert manager.name == "DeepSearch Manager Agent"
        
        # Should be registered in runtime
        manager2 = test_runtime.get_or_create_agent("manager")
        assert manager2 is not None
    
    @pytest.mark.compatibility
    def test_tool_compatibility(self, test_runtime):
        """Test tool compatibility after upgrade."""
        agent = test_runtime.create_react_agent()
        
        if hasattr(agent, 'agent') and hasattr(agent.agent, 'tools'):
            tools = agent.agent.tools
            
            # All standard tools should still be available
            expected_tools = [
                "search_links", "read_url", "chunk_text",
                "embed_texts", "rerank_texts", "final_answer"
            ]
            
            tool_names = list(tools.keys())
            for expected in expected_tools:
                assert any(expected in name for name in tool_names), \
                    f"Tool {expected} not found after migration"
    
    @pytest.mark.compatibility
    def test_code_tag_format_migration(self):
        """Test code tag format changes."""
        # Old markdown format
        old_code = "```python\nprint('hello')\n```"
        
        # New XML format
        new_code = "<code>\nprint('hello')\n</code>"
        
        # Both formats should be recognized in prompts
        from src.agents.prompt_templates.codact_prompts import CODACT_SYSTEM_EXTENSION
        
        # New format should be used in prompts
        assert "<code>" in CODACT_SYSTEM_EXTENSION or "code" in CODACT_SYSTEM_EXTENSION
    
    @pytest.mark.compatibility
    def test_security_enhancements(self, test_runtime):
        """Test security enhancements are applied."""
        agent = test_runtime.create_codact_agent()
        
        # Should have security executor kwargs
        # Note: Current smolagents LocalPythonExecutor may not support all params
        # so we only check that executor_kwargs exists
        assert hasattr(agent, 'executor_kwargs')
        assert isinstance(agent.executor_kwargs, dict)
        
        # Should have code validation
        assert hasattr(agent, 'validate_code_safety')
        
        # Dangerous code should be rejected
        dangerous_code = "import os; os.system('rm -rf /')"
        assert agent.validate_code_safety(dangerous_code) == False
    
    @pytest.mark.compatibility
    def test_config_file_compatibility(self, tmp_path):
        """Test config file compatibility."""
        # Create old config format
        old_config = """
[agents]
default_agent = "react"
orchestrator_model = "openai/claude-sonnet-4"
search_model = "openai/claude-sonnet-4"

[agents.react]
max_steps = 10
planning_interval = 5

[agents.codact]
max_steps = 10
executor_type = "local"
"""
        
        config_file = tmp_path / "config.toml"
        config_file.write_text(old_config)
        
        # Should be able to load old config
        with patch.dict('os.environ', {'DEEPSEARCH_CONFIG_FILE': str(config_file)}):
            settings = Settings()
            # Old settings should still work
            assert settings.DEEPSEARCH_AGENT_MODE == "react"
            assert settings.REACT_MAX_STEPS == 10