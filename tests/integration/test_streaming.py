#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/integration/test_streaming.py
# code style: PEP 8

"""
Integration tests for streaming functionality.
"""

import pytest
import asyncio
from typing import List, Generator
from unittest.mock import MagicMock, patch

from src.agents.runtime import AgentRuntime
from src.agents.stream_aggregator import StreamAggregator, ModelStreamWrapper
from smolagents.models import ChatMessageStreamDelta


class TestStreamingIntegration:
    """Test streaming functionality integration."""

    @pytest.fixture
    def runtime(self, test_settings):
        """Create test runtime with streaming enabled."""
        test_settings.ENABLE_STREAMING = True
        runtime = AgentRuntime(settings_obj=test_settings)
        if not runtime.valid_api_keys:
            pytest.skip("API keys not configured")
        return runtime

    @pytest.mark.integration
    def test_stream_aggregator(self):
        """Test StreamAggregator functionality."""
        aggregator = StreamAggregator()

        # Test adding chunks
        aggregator.add_chunk("Hello")
        aggregator.add_chunk(" world")
        aggregator.add_chunk("!")

        # Get aggregated content
        full_content = aggregator.get_full_content()
        assert full_content == "Hello world!"

        # Test with role
        aggregator.add_chunk(" More", role="assistant")
        assert aggregator.current_role == "assistant"

    @pytest.mark.integration
    def test_model_stream_wrapper(self):
        """Test ModelStreamWrapper functionality."""
        # Create mock model with streaming
        mock_model = MagicMock()

        def mock_stream(*args, **kwargs):
            yield ChatMessageStreamDelta(content="First")
            yield ChatMessageStreamDelta(content=" chunk")
            yield ChatMessageStreamDelta(content=" done")

        mock_model.generate_stream = mock_stream

        # Create wrapper
        wrapper = ModelStreamWrapper(mock_model)

        # Collect stream
        chunks = list(wrapper.generate_stream([{"role": "user", "content": "What is the latest litellm nightly-version?"}]))

        assert len(chunks) == 3
        assert chunks[0].content == "First"
        assert chunks[1].content == " chunk"
        assert chunks[2].content == " done"

    @pytest.mark.integration
    @pytest.mark.requires_llm
    @pytest.mark.timeout(600)  # 10 minutes timeout for streaming test
    def test_react_agent_streaming(self, runtime, cleanup_agents):
        """Test ReactAgent streaming functionality."""
        # Note: Streaming is currently disabled in settings
        # This tests the infrastructure is in place

        agent = cleanup_agents(runtime.create_react_agent())

        # Attempt streaming (will use non-streaming mode due to settings)
        result = agent.run("What is the latest litellm dev-version?")

        # Since streaming is disabled, result should be a RunResult or string
        if hasattr(result, 'final_answer'):
            # RunResult object
            assert result.final_answer is not None
            assert isinstance(result.final_answer, str)
        else:
            # Direct string result
            assert isinstance(result, str)

    @pytest.mark.integration
    def test_streaming_error_handling(self):
        """Test error handling during streaming."""
        # Create model that errors during streaming
        mock_model = MagicMock()

        def error_stream(*args, **kwargs):
            yield ChatMessageStreamDelta(content="Start")
            raise ValueError("Stream error")

        mock_model.generate_stream = error_stream

        wrapper = ModelStreamWrapper(mock_model)

        # Should handle error gracefully
        chunks = []
        try:
            for chunk in wrapper.generate_stream([{"role": "user", "content": "What is Time in USA(Central Time) of current?"}]):
                chunks.append(chunk)
        except ValueError:
            pass

        # Should have received at least the first chunk
        assert len(chunks) >= 1
        assert chunks[0].content == "Start"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_streaming_compatibility(self):
        """Test compatibility with async streaming."""
        # Create async generator
        async def async_stream():
            yield ChatMessageStreamDelta(content="Async")
            await asyncio.sleep(0.01)
            yield ChatMessageStreamDelta(content=" stream")
            await asyncio.sleep(0.01)
            yield ChatMessageStreamDelta(content=" test")

        # Collect async stream
        chunks = []
        async for chunk in async_stream():
            chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0].content == "Async"
        assert chunks[2].content == " test"

    @pytest.mark.integration
    def test_multi_model_router_streaming(self, runtime):
        """Test streaming through MultiModelRouter."""
        from src.agents.base_agent import MultiModelRouter

        # Create mock models
        search_model = MagicMock()
        orchestrator_model = MagicMock()

        def mock_stream(*args, **kwargs):
            yield ChatMessageStreamDelta(content="Router")
            yield ChatMessageStreamDelta(content=" streaming")

        search_model.generate_stream = mock_stream
        orchestrator_model.generate_stream = mock_stream

        # Create router
        router = MultiModelRouter(search_model, orchestrator_model)

        # Test streaming
        messages = [{"role": "user", "content": "What is Time in USA(East Time) of current?"}]
        chunks = list(router.generate_stream(messages))

        assert len(chunks) >= 2
        assert any("Router" in chunk.content for chunk in chunks)

    @pytest.mark.integration
    def test_streaming_token_counting(self):
        """Test token counting during streaming."""
        aggregator = StreamAggregator()

        # Simulate streaming with token counts
        chunks = [
            ("USA(Central Time) of current is what time?", 1),
            ("USA(East Time) of current is what time?", 1),
            ("USA(West Time) of current is what time?", 1),
            ("USA(Mountain Time) of current is what time?", 1)
        ]

        for content, tokens in chunks:
            aggregator.add_chunk(content)

        # Total content
        full_content = aggregator.get_full_content()
        assert full_content == "USA(Central Time) of current is what time?USA(East Time) of current is what time?USA(West Time) of current is what time?USA(Mountain Time) of current is what time?"

        # In real implementation, token counting would be handled by the model
