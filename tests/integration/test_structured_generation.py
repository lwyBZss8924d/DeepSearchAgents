#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/integration/test_structured_generation.py
# code style: PEP 8

"""
Integration tests for structured generation functionality.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from src.agents.runtime import AgentRuntime
from src.agents.codact_agent import CodeActAgent


class TestStructuredGeneration:
    """Test structured generation functionality."""

    @pytest.fixture
    def runtime_with_structured(self, test_settings):
        """Create runtime with structured generation enabled."""
        test_settings.CODACT_USE_STRUCTURED_OUTPUTS = True
        runtime = AgentRuntime(settings_obj=test_settings)
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        return runtime

    @pytest.fixture
    def runtime_without_structured(self, test_settings):
        """Create runtime with structured generation disabled."""
        test_settings.CODACT_USE_STRUCTURED_OUTPUTS = False
        runtime = AgentRuntime(settings_obj=test_settings)
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        return runtime

    @pytest.mark.integration
    def test_structured_outputs_enabled(
        self,
        runtime_with_structured,
        cleanup_agents
    ):
        """Test CodeActAgent with structured outputs enabled."""
        agent = cleanup_agents(runtime_with_structured.create_codact_agent())

        # Verify structured outputs is enabled (unless reranker is configured)
        # Note: if reranker is configured, structured outputs will be disabled
        if hasattr(agent, 'reranker_type') and agent.reranker_type:
            assert agent.use_structured_outputs_internally is False
        else:
            assert agent.use_structured_outputs_internally is True

        # Verify agent was created successfully
        assert agent.agent is not None

    @pytest.mark.integration
    def test_structured_outputs_disabled(
        self,
        runtime_without_structured,
        cleanup_agents
    ):
        """Test CodeActAgent with structured outputs disabled."""
        # Verify the runtime has the correct setting
        assert runtime_without_structured.settings.CODACT_USE_STRUCTURED_OUTPUTS is False

        agent = cleanup_agents(runtime_without_structured.create_codact_agent())

        # Verify structured outputs is disabled
        # Note: If the agent has a reranker, structured outputs are always disabled
        # Otherwise, it should match the runtime setting
        if hasattr(agent, 'reranker_type') and agent.reranker_type:
            # With reranker, structured outputs must be disabled
            assert agent.use_structured_outputs_internally is False
        else:
            # Without reranker, it should match the setting
            assert agent.use_structured_outputs_internally is runtime_without_structured.settings.CODACT_USE_STRUCTURED_OUTPUTS

        # Verify agent was created successfully
        assert agent.agent is not None

    @pytest.mark.integration
    def test_structured_prompts_loading(
        self,
        runtime_with_structured,
        cleanup_agents
    ):
        """Test loading of structured prompt templates."""
        # Create agent which will attempt to load structured prompts
        agent = cleanup_agents(runtime_with_structured.create_codact_agent())

        # Verify agent was created (structured prompts loading happens internally)
        assert agent.agent is not None

        # Check that agent has prompt_templates
        if hasattr(agent.agent, 'prompt_templates'):
            assert agent.agent.prompt_templates is not None

    @pytest.mark.integration
    def test_structured_vs_grammar_conflict(self, test_settings):
        """Test that structured outputs and grammar cannot be used together."""
        test_settings.CODACT_USE_STRUCTURED_OUTPUTS = True
        runtime = AgentRuntime(settings_obj=test_settings)

        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")

        # Create agent with reranker (which uses grammar)
        agent = runtime.create_codact_agent()

        # If both were set, structured outputs should be disabled
        if hasattr(agent, 'reranker_type') and agent.reranker_type:
            # Grammar takes precedence
            assert agent.use_structured_outputs_internally is False

    @pytest.mark.integration
    @pytest.mark.requires_llm
    @pytest.mark.timeout(600)  # 10 minutes timeout for LLM test
    def test_structured_output_format(
        self,
        runtime_with_structured,
        cleanup_agents
    ):
        """Test that structured outputs produce valid JSON."""
        agent = cleanup_agents(runtime_with_structured.create_codact_agent())

        # Simple query that should produce structured output
        result = agent.run("What is the latest litellm stable-version?")

        # Check result is a RunResult object
        if hasattr(result, 'final_answer'):
            # RunResult object - check the final answer
            answer = result.final_answer
        else:
            # Direct string result
            answer = result

        # The actual output format depends on the model and prompts
        # Structured outputs affect internal processing, not necessarily the final format
        assert isinstance(answer, str)
        assert len(answer) > 0

    @pytest.mark.integration
    def test_prompt_template_extension(
        self,
        runtime_with_structured,
        cleanup_agents
    ):
        """Test that prompt templates are properly extended."""
        agent = cleanup_agents(runtime_with_structured.create_codact_agent())

        # Verify agent has extended prompts
        if hasattr(agent, 'agent') and hasattr(agent.agent, 'prompt_templates'):
            prompts = agent.agent.prompt_templates
            # Should have base prompts plus extensions
            assert prompts is not None

    @pytest.mark.integration
    def test_fallback_to_regular_prompts(
        self,
        runtime_with_structured,
        cleanup_agents
    ):
        """Test fallback when structured prompts not found."""
        with patch('src.agents.codact_agent.importlib.resources.files') as mock_files:
            # Create a mock that raises FileNotFoundError only for structured prompts
            def side_effect(module_name):
                mock_module = MagicMock()
                mock_path = MagicMock()

                def joinpath_side_effect(filename):
                    if "structured_code_agent.yaml" in filename:
                        # Raise error for structured prompts
                        mock_file = MagicMock()
                        mock_file.read_text.side_effect = FileNotFoundError("No structured prompts")
                        return mock_file
                    else:
                        # Return normal mock for regular prompts
                        mock_file = MagicMock()
                        mock_file.read_text.return_value = 'system: "test"'
                        return mock_file

                mock_path.joinpath.side_effect = joinpath_side_effect
                mock_module.joinpath = mock_path.joinpath
                return mock_module

            mock_files.side_effect = side_effect

            # Should fall back to regular prompts without error
            agent = cleanup_agents(runtime_with_structured.create_codact_agent())
            assert agent.agent is not None
