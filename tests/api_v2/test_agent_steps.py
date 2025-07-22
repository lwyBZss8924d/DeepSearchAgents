#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/api_v2/test_agent_steps.py
# code style: PEP 8

"""
Test agent steps run message for DeepSearchAgents Web API v2.

This test validates that all agent steps (ActionStep, PlanningStep, etc.)
are properly streamed as DSAgentRunMessage objects.
"""

import pytest
import asyncio
import json
import re
from typing import Dict, Any, List

from tests.api_v2.utils import (
    websocket_session, assert_message_format,
    count_step_types, MessageCollector
)


class TestAgentSteps:
    """Test agent steps streaming functionality."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_llm_research_steps(self, test_client, websocket_url):
        """
        Test case: Search about New LLM: Qwen [Qwen3-235B-A22B] model info,
        and summarize it into a nice table for me.

        This test validates:
        - Streaming of ActionStep messages
        - PlanningStep messages
        - Tool execution updates
        - Progress indicators
        - Final answer with table format
        """
        async with websocket_session(test_client, websocket_url) as manager:
            # Send the research query
            query = (
                "Search about New LLM: Qwen [Qwen3-235B-A22B] model info, "
                "and summarize it into a nice table for me."
            )
            await manager.send_query(query)

            # Track different types of steps
            planning_steps = []
            action_steps = []
            tool_executions = []

            # Collect messages for analysis
            start_time = asyncio.get_event_loop().time()
            timeout = 2000  # 33 minutes timeout as requested

            while asyncio.get_event_loop().time() - start_time < timeout:
                # Check if we have final answer
                if manager.collector.final_answer:
                    break

                # Analyze current messages
                for msg in manager.collector.messages:
                    if msg in planning_steps + action_steps + tool_executions:
                        continue  # Already processed

                    content = msg.get("content", "")
                    metadata = msg.get("metadata", {})

                    # Identify planning steps
                    if self._is_planning_step(content, metadata):
                        planning_steps.append(msg)

                    # Identify action steps
                    elif self._is_action_step(content, metadata):
                        action_steps.append(msg)

                    # Identify tool executions
                    elif self._is_tool_execution(content, metadata):
                        tool_executions.append(msg)

                await asyncio.sleep(0.5)

            # Assertions
            assert manager.collector.final_answer is not None, \
                "Should receive final answer"

            # Validate message formats
            for msg in manager.collector.messages:
                assert_message_format(msg)

            # Should have planning steps
            assert len(planning_steps) > 0, \
                "Should have at least one planning step"

            # Should have action steps
            assert len(action_steps) > 0, \
                "Should have at least one action step"

            # Should have tool executions (search tools)
            assert len(tool_executions) > 0, \
                "Should have tool executions for search"

            # Final answer should contain table
            final_content = manager.collector.final_answer.get("content", "")
            assert self._contains_table(final_content), \
                "Final answer should contain a table"

            # Verify step progression
            self._verify_step_progression(manager.collector.messages)

    @pytest.mark.asyncio
    async def test_step_numbering(self, test_client, websocket_url):
        """Test that steps are properly numbered."""
        async with websocket_session(test_client, websocket_url) as manager:
            # Send query that will generate multiple steps
            await manager.send_query(
                "Search for information about Python asyncio and "
                "explain its event loop"
            )

            # Wait for some steps
            await manager.wait_for_condition(
                lambda: len(manager.collector.get_step_messages()) >= 3,
                timeout=1000
            )

            # Extract step numbers
            step_numbers = []
            for msg in manager.collector.messages:
                if msg.get("step_number") is not None:
                    step_numbers.append(msg["step_number"])

                # Also check content for step indicators
                content = msg.get("content", "")
                step_match = re.search(r"Step (\d+)", content)
                if step_match:
                    step_numbers.append(int(step_match.group(1)))

            # Should have sequential step numbers
            assert len(step_numbers) > 0, "Should have step numbers"

            # Check for reasonable progression
            unique_steps = sorted(set(step_numbers))
            assert unique_steps[0] <= 1, "Steps should start from 1 or 0"

    @pytest.mark.asyncio
    async def test_planning_step_content(self, test_client, websocket_url):
        """Test planning step content structure."""
        async with websocket_session(test_client, websocket_url) as manager:
            await manager.send_query(
                "Search & query the weather in [New York] US city for tomorrow and summarize it into a nice table for me."
            )

            # Wait for planning step
            await manager.wait_for_condition(
                manager.collector.has_planning_step,
                timeout=1000
            )

            # Find planning messages
            planning_messages = [
                msg for msg in manager.collector.messages
                if self._is_planning_step(
                    msg.get("content", ""),
                    msg.get("metadata", {})
                )
            ]

            assert len(planning_messages) > 0, \
                "Should have planning messages"

            # Verify planning content structure
            for msg in planning_messages:
                content = msg["content"]

                # Should have structured planning
                assert any([
                    "facts" in content.lower(),
                    "plan" in content.lower(),
                    "steps" in content.lower(),
                    "approach" in content.lower()
                ]), f"Planning should have structure, got: {content[:200]}"

    @pytest.mark.asyncio
    async def test_action_step_details(self, test_client, websocket_url):
        """Test action step details and tool calls."""
        async with websocket_session(test_client, websocket_url) as manager:
            await manager.send_query(
                "Search & query the weather in [Los Angeles] US city for tomorrow and summarize it into a nice table for me."
            )

            # Wait for action steps
            await manager.wait_for_condition(
                manager.collector.has_action_step,
                timeout=1000
            )

            # Find action messages
            action_messages = [
                msg for msg in manager.collector.messages
                if self._is_action_step(
                    msg.get("content", ""),
                    msg.get("metadata", {})
                )
            ]

            assert len(action_messages) > 0, "Should have action messages"

            # Verify action content
            for msg in action_messages:
                content = msg["content"]
                metadata = msg.get("metadata", {})

                # Should indicate what tool/action is being performed
                assert any([
                    "search" in content.lower(),
                    "executing" in content.lower(),
                    "calling" in content.lower(),
                    metadata.get("status") == "running"
                ]), f"Action should indicate execution, got: {content[:200]}"

    @pytest.mark.asyncio
    async def test_step_metadata(self, test_client, websocket_url):
        """Test metadata in step messages."""
        async with websocket_session(test_client, websocket_url) as manager:
            await manager.send_query("Search & query the weather in [Dallas] US city for tomorrow and summarize it into a nice table for me.")

            # Collect messages for a while
            await asyncio.sleep(10)

            # Check metadata in step messages
            step_messages = manager.collector.get_step_messages()
            assert len(step_messages) > 0, "Should have step messages"

            for msg in step_messages:
                metadata = msg.get("metadata", {})

                # Should have some metadata
                assert metadata != {}, \
                    "Step messages should have metadata"

                # Common metadata fields
                if "status" in metadata:
                    assert metadata["status"] in [
                        "thinking", "running", "complete", "waiting"
                    ]

                if "title" in metadata:
                    assert isinstance(metadata["title"], str)

    @pytest.mark.asyncio
    async def test_error_recovery_in_steps(self, test_client, websocket_url):
        """Test error handling and recovery in step execution."""
        async with websocket_session(test_client, websocket_url) as manager:
            # Query that might trigger errors and recovery
            await manager.send_query(
                "Search & query the weather in [Boston] US city for tomorrow and summarize it into a nice table for me."
            )

            # Wait for completion
            await manager.wait_for_final_answer(timeout=1000)

            # Should complete despite potential search failures
            assert manager.collector.final_answer is not None

            # Check for error handling
            step_types = count_step_types(manager.collector.messages)

            # Should still have planning and actions
            assert step_types["planning"] > 0
            assert step_types["action"] > 0

    # Helper methods
    def _is_planning_step(self, content: str, metadata: Dict) -> bool:
        """Check if message is a planning step."""
        content_lower = content.lower()
        title_lower = metadata.get("title", "").lower()

        return any([
            "planning" in content_lower,
            "facts survey" in content_lower,
            "facts to look up" in content_lower,
            "plan" in title_lower,
            "analysis" in title_lower and "plan" in content_lower
        ])

    def _is_action_step(self, content: str, metadata: Dict) -> bool:
        """Check if message is an action step."""
        content_lower = content.lower()

        return any([
            "executing" in content_lower,
            "calling tool" in content_lower,
            "running" in content_lower,
            metadata.get("status") == "running",
            re.search(r"tool:\s*\w+", content_lower)
        ])

    def _is_tool_execution(self, content: str, metadata: Dict) -> bool:
        """Check if message is a tool execution."""
        content_lower = content.lower()

        return any([
            "search_" in content_lower,
            "read_url" in content_lower,
            "wolfram" in content_lower,
            "calling function:" in content_lower,
            re.search(r"```python.*?```", content, re.DOTALL)
        ])

    def _contains_table(self, content: str) -> bool:
        """Check if content contains a table."""
        # Look for markdown table indicators
        if "|" in content and "-" in content:
            lines = content.split("\n")
            table_lines = [l for l in lines if "|" in l]
            if len(table_lines) >= 3:  # Header + separator + at least one row
                return True

        # Look for structured data that looks like a table
        if all(keyword in content.lower() for keyword in ["model", "parameter", "size"]):
            return True

        # Look for HTML table
        if "<table" in content.lower():
            return True

        return False

    def _verify_step_progression(self, messages: List[Dict[str, Any]]):
        """Verify logical progression of steps."""
        # Track step sequence
        sequence = []

        for msg in messages:
            if msg["role"] == "user":
                sequence.append("user_query")
            elif self._is_planning_step(msg.get("content", ""), msg.get("metadata", {})):
                sequence.append("planning")
            elif self._is_action_step(msg.get("content", ""), msg.get("metadata", {})):
                sequence.append("action")
            elif "final answer" in msg.get("content", "").lower():
                sequence.append("final_answer")

        # Verify sequence makes sense
        assert sequence[0] == "user_query", "Should start with user query"
        assert "planning" in sequence, "Should have planning"
        assert "action" in sequence, "Should have actions"
        assert sequence[-1] == "final_answer" or sequence[-2] == "final_answer", \
            "Should end with final answer"

        # Planning should generally come before actions
        first_planning = sequence.index("planning") if "planning" in sequence else -1
        first_action = sequence.index("action") if "action" in sequence else -1

        if first_planning != -1 and first_action != -1:
            assert first_planning < first_action, \
                "Planning should generally precede actions"
