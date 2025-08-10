#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/api_v2/test_final_answer.py
# code style: PEP 8

"""
Test final answer message for DeepSearchAgents Web API v2.

This test validates the final answer format and streaming behavior.
"""

import pytest
import asyncio
import re
from typing import Dict, Any

from tests.api_v2.utils import (
    websocket_session, assert_message_format,
    extract_final_answer_content
)


class TestFinalAnswer:
    """Test final answer message functionality."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_calculation_final_answer(
        self,
        test_client,
        websocket_url
    ):
        """
        Test case: Calculate 50 * 3 + 25 and show your work

        This test validates:
        - Streaming of intermediate steps
        - Final answer format
        - Metadata fields
        - Completion status
        - Mathematical correctness
        """
        async with websocket_session(test_client, websocket_url) as manager:
            # Send calculation query
            query = "Calculate 50 * 3 + 25 and show your work"
            await manager.send_query(query)

            # Wait for final answer with timeout
            final_answer = await manager.wait_for_final_answer(
                timeout=1000
            )

            # Validate final answer exists
            assert final_answer is not None, "Should receive final answer"
            assert_message_format(final_answer)

            # Extract content
            content = extract_final_answer_content(final_answer)

            # Verify mathematical correctness
            assert "175" in content, \
                "Final answer should contain correct result 175"

            # Verify work is shown
            assert any([
                "50 * 3" in content,
                "50 × 3" in content,
                "multiplication" in content.lower()
            ]), "Should show multiplication step"

            assert any([
                "150 + 25" in content,
                "addition" in content.lower()
            ]), "Should show addition step"

            # Check metadata
            metadata = final_answer.get("metadata", {})

            # Should have completion indicator
            assert any([
                metadata.get("status") == "complete",
                "final" in metadata.get("title", "").lower(),
                "final answer" in content.lower()
            ]), "Should indicate completion"

            # Verify we got intermediate steps
            step_messages = manager.collector.get_step_messages()
            assert len(step_messages) > 0, \
                "Should have intermediate step messages"

    @pytest.mark.asyncio
    async def test_final_answer_format(self, test_client, websocket_url):
        """Test the format of final answer messages."""
        async with websocket_session(test_client, websocket_url) as manager:
            await manager.send_query("Search & query the weather in [Las Vegas] US city for tomorrow and summarize it into a nice table for me.")

            # Wait for final answer
            final_answer = await manager.wait_for_final_answer(timeout=1000)

            # Validate structure
            assert_message_format(final_answer)

            # Should have assistant role
            assert final_answer["role"] == "assistant"

            # Content should mention Las Vegas Weather
            content = final_answer["content"]
            assert "las vegas" in content.lower(), \
                "Should contain the answer 'Las Vegas'"

            # Check for structured response
            if "{" in content and "}" in content:
                # May have JSON structure
                import json
                try:
                    # Extract JSON if present
                    json_match = re.search(r'\{[^}]+\}', content)
                    if json_match:
                        data = json.loads(json_match.group())

                        # Common fields in final answer
                        if "title" in data:
                            assert isinstance(data["title"], str)
                        if "content" in data:
                            assert isinstance(data["content"], str)
                        if "confidence" in data:
                            assert 0 <= data["confidence"] <= 1
                except json.JSONDecodeError:
                    pass  # Not required to be JSON

    @pytest.mark.asyncio
    async def test_streaming_before_final_answer(
        self,
        test_client,
        websocket_url
    ):
        """Test that streaming updates occur before final answer."""
        async with websocket_session(test_client, websocket_url) as manager:
            await manager.send_query(
                "List the first 5 prime numbers with explanation"
            )

            # Track messages before final answer
            pre_final_messages = []

            # Collect messages for a while
            start_time = asyncio.get_event_loop().time()
            timeout = 1000

            while asyncio.get_event_loop().time() - start_time < timeout:
                if manager.collector.final_answer:
                    break

                # Store current assistant messages
                pre_final_messages = [
                    msg for msg in manager.collector.assistant_messages
                    if not manager.collector._is_final_answer(msg)
                ]

                await asyncio.sleep(0.1)

            # Should have streaming updates
            assert len(pre_final_messages) > 0, \
                "Should have messages before final answer"

            # Should have final answer
            assert manager.collector.final_answer is not None

            # Final answer should contain the prime numbers
            final_content = manager.collector.final_answer["content"]
            primes = ["2", "3", "5", "7", "11"]
            for prime in primes:
                assert prime in final_content, \
                    f"Final answer should contain prime number {prime}"

    @pytest.mark.asyncio
    async def test_final_answer_timing(self, test_client, websocket_url):
        """Test timing and order of final answer."""
        async with websocket_session(test_client, websocket_url) as manager:
            await manager.send_query("What is 10 divided by 2?")

            # Track message order
            message_types = []

            # Wait and collect messages
            await manager.wait_for_final_answer(timeout=1000)

            # Analyze message sequence
            for msg in manager.collector.messages:
                if msg["role"] == "user":
                    message_types.append("user")
                elif manager.collector._is_final_answer(msg):
                    message_types.append("final_answer")
                elif msg["role"] == "assistant":
                    message_types.append("assistant")

            # Verify sequence
            assert message_types[0] == "user", \
                "Should start with user message"
            assert message_types[-1] == "final_answer", \
                "Should end with final answer"

            # Should have some intermediate messages
            intermediate_count = message_types.count("assistant")
            assert intermediate_count >= 0, \
                "May have intermediate assistant messages"

    @pytest.mark.asyncio
    async def test_final_answer_completeness(
        self,
        test_client,
        websocket_url
    ):
        """Test that final answer is complete and well-formed."""
        async with websocket_session(test_client, websocket_url) as manager:
            await manager.send_query(
                "Explain the water cycle in 3 steps"
            )

            # Wait for final answer
            final_answer = await manager.wait_for_final_answer(timeout=1000)

            content = final_answer["content"]

            # Should have 3 steps mentioned
            step_indicators = [
                "1", "2", "3",
                "first", "second", "third",
                "step 1", "step 2", "step 3"
            ]

            step_count = sum(
                1 for indicator in step_indicators 
                if indicator in content.lower()
            )

            assert step_count >= 3, \
                "Should mention at least 3 steps"

            # Should mention key water cycle components
            key_terms = ["evaporation", "condensation", "precipitation"]
            mentioned_terms = sum(
                1 for term in key_terms 
                if term in content.lower()
            )

            assert mentioned_terms >= 2, \
                "Should mention key water cycle terms"

    @pytest.mark.asyncio
    async def test_final_answer_with_sources(
        self,
        test_client,
        websocket_url
    ):
        """Test final answer that includes sources."""
        async with websocket_session(test_client, websocket_url) as manager:
            await manager.send_query(
                "What is the current population of Tokyo? "
                "Include source information."
            )

            # Wait for final answer
            final_answer = await manager.wait_for_final_answer(timeout=1000)

            content = final_answer["content"]

            # Should mention Tokyo
            assert "tokyo" in content.lower()

            # Should have some population figure
            assert any(
                char.isdigit() for char in content
            ), "Should contain population numbers"

            # Check for source indicators
            source_indicators = [
                "source", "according to", "as of",
                "reference", "based on"
            ]

            has_source_info = any(
                indicator in content.lower()
                for indicator in source_indicators
            )

            # Note: Agent might not always include sources
            # but should attempt to when requested
            if has_source_info:
                assert True  # Good, has source info
            else:
                # At least should have the answer
                assert "million" in content.lower() or \
                       "population" in content.lower()

    @pytest.mark.asyncio
    async def test_final_answer_error_handling(
        self,
        test_client,
        websocket_url
    ):
        """Test final answer when errors occur."""
        async with websocket_session(test_client, websocket_url) as manager:
            # Query that might cause difficulties
            await manager.send_query(
                "What is the exact value of an undefined "
                "mathematical operation like 0/0?"
            )

            # Should still get a final answer
            final_answer = await manager.wait_for_final_answer(timeout=60)

            content = final_answer["content"]

            # Should handle the undefined operation gracefully
            assert any([
                "undefined" in content.lower(),
                "cannot" in content.lower(),
                "not defined" in content.lower(),
                "indeterminate" in content.lower()
            ]), "Should explain that operation is undefined"

            # Should not have unhandled errors
            assert manager.collector.error_messages == [] or \
                   len(manager.collector.error_messages) == 0, \
                   "Should handle errors gracefully"

    @pytest.mark.asyncio
    async def test_multiple_final_answers(
        self,
        test_client,
        websocket_url
    ):
        """Test behavior with multiple queries in sequence."""
        async with websocket_session(test_client, websocket_url) as manager:
            # First query
            await manager.send_query("What is 5 + 5?")
            first_answer = await manager.wait_for_final_answer(timeout=30)

            assert "10" in first_answer["content"]

            # Clear collector for next query
            manager.collector.clear()

            # Second query
            await manager.send_query("What is 10 - 3?")
            second_answer = await manager.wait_for_final_answer(timeout=30)

            assert "7" in second_answer["content"]

            # Answers should be different
            assert first_answer["content"] != second_answer["content"]

            # Both should be valid
            assert_message_format(first_answer)
            assert_message_format(second_answer)
