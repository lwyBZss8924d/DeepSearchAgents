#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/unit/test_codact_agent.py
# code style: PEP 8

"""
Unit tests for CodeActAgent functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from smolagents import Tool, LiteLLMModel, CodeAgent

from src.agents.codact_agent import CodeActAgent
from src.agents.base_agent import MultiModelRouter


class TestCodeActAgent:
    """Test CodeActAgent functionality."""

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

        read_tool = MagicMock(spec=Tool)
        read_tool.name = "read_url"

        final_tool = MagicMock(spec=Tool)
        final_tool.name = "final_answer"

        return [search_tool, read_tool, final_tool]

    @pytest.fixture
    def initial_state(self):
        """Create initial state."""
        return {
            "visited_urls": ["url1", "url2"],  # Will be converted to set
            "search_queries": [],
            "key_findings": {}
        }

    @pytest.fixture
    def codact_agent(self, mock_models, mock_tools, initial_state):
        """Create CodeActAgent instance."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.codact_agent.CodeAgent'):
            agent = CodeActAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                executor_type="local",
                max_steps=5,
                verbosity_level=2
            )
            return agent

    def test_initialization(self, codact_agent):
        """Test CodeActAgent initialization."""
        assert codact_agent.agent_type == "codact"
        assert codact_agent.executor_type == "local"
        assert codact_agent.max_steps == 5
        assert codact_agent.verbosity_level == 2
        assert codact_agent.use_structured_outputs_internally is False

    def test_authorized_imports_initialization(
        self,
        mock_models,
        mock_tools,
        initial_state
    ):
        """Test authorized imports handling."""
        search_model, orchestrator_model = mock_models

        # Test with nested list (legacy format)
        with patch('src.agents.codact_agent.CodeAgent'):
            agent = CodeActAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                additional_authorized_imports=[["pandas", "numpy"]]
            )
            assert agent.additional_authorized_imports == ["pandas", "numpy"]

        # Test with flat list
        with patch('src.agents.codact_agent.CodeAgent'):
            agent2 = CodeActAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                additional_authorized_imports=["matplotlib", "seaborn"]
            )
            assert agent2.additional_authorized_imports == ["matplotlib", "seaborn"]

    def test_initial_state_url_conversion(self, mock_models, mock_tools):
        """Test conversion of visited_urls to set."""
        search_model, orchestrator_model = mock_models

        initial_state = {
            "visited_urls": ["url1", "url2", "url1"],  # Duplicate
            "search_queries": []
        }
        with patch('src.agents.codact_agent.CodeAgent'):
            CodeActAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state
            )

            # Should be converted to set
            assert isinstance(initial_state["visited_urls"], set)
            assert len(initial_state["visited_urls"]) == 2
            assert "url1" in initial_state["visited_urls"]
            assert "url2" in initial_state["visited_urls"]

    def test_security_executor_kwargs(
        self,
        mock_models,
        mock_tools,
        initial_state
    ):
        """Test security settings in executor kwargs."""
        search_model, orchestrator_model = mock_models

        # Test default security settings
        with patch('src.agents.codact_agent.CodeAgent'):
            agent = CodeActAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state
            )

            # Check that executor_kwargs exists
            # (but may be empty due to compatibility)
            assert hasattr(agent, 'executor_kwargs')
            assert isinstance(agent.executor_kwargs, dict)
            # For now, we don't set any default security parameters due to
            # LocalPythonExecutor compatibility in smolagents v1.19.0

    def test_code_safety_validation(self, codact_agent):
        """Test code safety validation."""
        # Safe code
        safe_code = """
def calculate_sum(a, b):
    return a + b
result = calculate_sum(1, 2)
"""
        assert codact_agent.validate_code_safety(safe_code) is True

        # Unsafe code - eval
        unsafe_code1 = "result = eval('1 + 1')"
        assert codact_agent.validate_code_safety(unsafe_code1) is False

        # Unsafe code - file operations
        unsafe_code2 = "f = open('/etc/passwd', 'r')"
        assert codact_agent.validate_code_safety(unsafe_code2) is False

        # Unsafe code - os module
        unsafe_code3 = "import os; os.system('ls')"
        assert codact_agent.validate_code_safety(unsafe_code3) is False

    def test_authorized_imports_filtering(self, codact_agent):
        """Test filtering of dangerous imports."""
        # Get authorized imports
        imports = codact_agent._get_authorized_imports()

        # Check safe imports are included
        assert "json" in imports
        assert "requests" in imports
        assert "pandas" in imports

        # Check dangerous imports are excluded
        assert "os" not in imports
        assert "sys" not in imports
        assert "subprocess" not in imports
        assert "eval" not in imports

    def test_structured_outputs_configuration(
        self,
        mock_models,
        mock_tools,
        initial_state
    ):
        """Test structured outputs configuration."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.codact_agent.CodeAgent') as mock_agent_class:
            CodeActAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                use_structured_outputs_internally=True
            )

            # Verify structured outputs was passed
            call_kwargs = mock_agent_class.call_args.kwargs
            assert call_kwargs['use_structured_outputs_internally'] is True

    def test_managed_agents_support(self, mock_models, mock_tools, initial_state):
        """Test CodeActAgent with managed agents."""
        search_model, orchestrator_model = mock_models

        managed1 = MagicMock()
        managed1.name = "code_helper_1"

        with patch('src.agents.codact_agent.CodeAgent') as mock_agent_class:
            CodeActAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                managed_agents=[managed1]
            )

            # Verify managed_agents was passed
            call_kwargs = mock_agent_class.call_args.kwargs
            assert 'managed_agents' in call_kwargs
            assert call_kwargs['managed_agents'] == [managed1]

    def test_model_router_creation(
        self,
        mock_models,
        mock_tools,
        initial_state
    ):
        """Test MultiModelRouter creation."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.codact_agent.CodeAgent') as mock_agent_class:
            CodeActAgent(
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

    def test_step_callbacks_configuration(
        self,
        mock_models,
        mock_tools,
        initial_state
    ):
        """Test step callbacks configuration."""
        search_model, orchestrator_model = mock_models

        callback1 = MagicMock()
        callback2 = MagicMock()

        with patch('src.agents.codact_agent.CodeAgent') as mock_agent_class:
            CodeActAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                step_callbacks=[callback1, callback2]
            )

            call_kwargs = mock_agent_class.call_args.kwargs
            assert len(call_kwargs['step_callbacks']) == 2
            assert callback1 in call_kwargs['step_callbacks']
            assert callback2 in call_kwargs['step_callbacks']

    def test_planning_interval_configuration(
        self,
        mock_models,
        mock_tools,
        initial_state
    ):
        """Test planning interval configuration."""
        search_model, orchestrator_model = mock_models

        with patch('src.agents.codact_agent.CodeAgent') as mock_agent_class:
            CodeActAgent(
                orchestrator_model=orchestrator_model,
                search_model=search_model,
                tools=mock_tools,
                initial_state=initial_state,
                planning_interval=10
            )

            call_kwargs = mock_agent_class.call_args.kwargs
            assert call_kwargs['planning_interval'] == 10
