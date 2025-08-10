#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/unit/test_multi_model_router.py
# code style: PEP 8

"""
Unit tests for MultiModelRouter functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from smolagents import LiteLLMModel
from smolagents.models import ChatMessage, ChatMessageStreamDelta

from src.agents.base_agent import MultiModelRouter


class TestMultiModelRouter:
    """Test MultiModelRouter functionality."""

    @pytest.fixture
    def mock_models(self):
        """Create mock models for testing."""
        search_model = MagicMock(spec=LiteLLMModel)
        search_model.model_id = "test-search-model"
        search_model.last_input_token_count = 100
        search_model.last_output_token_count = 50

        orchestrator_model = MagicMock(spec=LiteLLMModel)
        orchestrator_model.model_id = "test-orchestrator-model"
        orchestrator_model.last_input_token_count = 200
        orchestrator_model.last_output_token_count = 100

        return search_model, orchestrator_model

    @pytest.fixture
    def router(self, mock_models):
        """Create MultiModelRouter instance."""
        search_model, orchestrator_model = mock_models
        return MultiModelRouter(search_model, orchestrator_model)

    def test_initialization(self, router, mock_models):
        """Test router initialization."""
        search_model, orchestrator_model = mock_models

        assert router.search_model == search_model
        assert router.orchestrator_model == orchestrator_model
        assert router.model_id == "test-orchestrator-model+test-search-model"
        assert router.last_input_token_count == 0
        assert router.last_output_token_count == 0

    def test_model_selection_for_planning(self, router):
        """Test model selection for planning messages."""
        messages = [
            {"role": "system", "content": "You are an AI assistant"},
            {"role": "user", "content": "Help me with a task"},
            {"role": "assistant", "content": "Let me update the Facts survey with the current information"}
        ]

        selected_model = router._select_model_for_messages(messages)
        assert selected_model == router.orchestrator_model

    def test_model_selection_for_search(self, router):
        """Test model selection for regular search tasks."""
        messages = [
            {"role": "system", "content": "You are an AI assistant"},
            {"role": "user", "content": "Search for information about langgraph python latest version"}
        ]

        selected_model = router._select_model_for_messages(messages)
        assert selected_model == router.search_model

    def test_model_selection_for_final_answer(self, router):
        """Test model selection for final answer generation."""
        messages = [
            {"role": "user", "content": "What Time is in USA(Central Time) of current?"},
            {"role": "assistant", "content": "I need to provide the final answer to the original question"}
        ]

        selected_model = router._select_model_for_messages(messages)
        assert selected_model == router.orchestrator_model

    def test_call_method(self, router, mock_models):
        """Test the __call__ method routes correctly."""
        search_model, orchestrator_model = mock_models

        # Mock response
        mock_response = ChatMessage(content="Test response", role="assistant")
        search_model.return_value = mock_response

        messages = [{"role": "user", "content": "Search for information about langgraph python latest version"}]
        result = router(messages)

        assert result == mock_response
        search_model.assert_called_once_with(messages)
        assert router.last_input_token_count == 100
        assert router.last_output_token_count == 50

    def test_generate_method(self, router, mock_models):
        """Test the generate method."""
        search_model, orchestrator_model = mock_models

        mock_response = ChatMessage(content="Generated response", role="assistant")
        search_model.return_value = mock_response

        messages = [{"role": "user", "content": "What Time is in USA(Central Time) of current?"}]
        result = router.generate(messages)

        assert result == mock_response
        search_model.assert_called_once()

    def test_token_counting(self, router, mock_models):
        """Test token counting functionality."""
        search_model, orchestrator_model = mock_models

        # Use search model
        router._update_token_counts_from_model(search_model)
        assert router.last_input_token_count == 100
        assert router.last_output_token_count == 50

        # Use orchestrator model
        router._update_token_counts_from_model(orchestrator_model)
        assert router.last_input_token_count == 200
        assert router.last_output_token_count == 100

        # Test get_token_counts
        counts = router.get_token_counts()
        assert counts["input"] == 200
        assert counts["output"] == 100

    def test_streaming_generation(self, router, mock_models):
        """Test streaming generation functionality."""
        search_model, orchestrator_model = mock_models

        # Mock streaming response
        def mock_stream(*args, **kwargs):
            yield ChatMessageStreamDelta(content="Test")
            yield ChatMessageStreamDelta(content=" streaming")
            yield ChatMessageStreamDelta(content=" response")

        search_model.generate_stream = mock_stream

        messages = [{"role": "user", "content": "What Time is in USA(Central Time) of current?"}]

        # Collect stream chunks
        chunks = list(router.generate_stream(messages))

        assert len(chunks) == 3
        assert chunks[0].content == "Test"
        assert chunks[1].content == " streaming"
        assert chunks[2].content == " response"

    def test_streaming_error_handling(self, router, mock_models):
        """Test error handling during streaming."""
        search_model, orchestrator_model = mock_models

        # Mock streaming with error
        def mock_stream_error(*args, **kwargs):
            yield ChatMessageStreamDelta(content="Start")
            raise ValueError("Stream error")

        search_model.generate_stream = mock_stream_error

        messages = [{"role": "user", "content": "What Time is in USA(Central Time) of current?"}]

        # Collect stream chunks
        chunks = list(router.generate_stream(messages))

        # Should get start chunk and error chunk
        assert len(chunks) >= 2
        assert chunks[0].content == "Start"
        assert "Error" in chunks[-1].content

    def test_complex_message_parsing(self, router):
        """Test parsing complex message structures."""
        # Test with list content structure containing planning keywords
        messages = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check the Updated facts survey"},
                    {"type": "code", "code": "print('hello')"}
                ]
            }
        ]

        selected_model = router._select_model_for_messages(messages)
        # Should select orchestrator for planning content
        assert selected_model.model_id == "test-orchestrator-model"

        # Test with mixed content without planning keywords
        messages = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Regular search task"},
                    {"type": "text", "text": "Continue searching for information"}
                ]
            }
        ]

        selected_model = router._select_model_for_messages(messages)
        # Should select search model for non-planning content
        assert selected_model.model_id == "test-search-model"
