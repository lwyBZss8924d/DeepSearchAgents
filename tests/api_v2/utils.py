#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/api_v2/utils.py
# code style: PEP 8

"""
Helper utilities for API v2 tests.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MessageCollector:
    """Collects messages from WebSocket stream."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.user_messages: List[Dict[str, Any]] = []
        self.assistant_messages: List[Dict[str, Any]] = []
        self.error_messages: List[Dict[str, Any]] = []
        self.final_answer: Optional[Dict[str, Any]] = None

    def add_message(self, message: Dict[str, Any]):
        """Add a message to the collection."""
        self.messages.append(message)

        # Categorize by role
        role = message.get("role")
        if role == "user":
            self.user_messages.append(message)
        elif role == "assistant":
            self.assistant_messages.append(message)

            # Check for final answer
            if self._is_final_answer(message):
                self.final_answer = message

        # Check for errors
        if message.get("type") == "error":
            self.error_messages.append(message)

    def _is_final_answer(self, message: Dict[str, Any]) -> bool:
        """Check if message contains final answer."""
        content = message.get("content", "").lower()
        metadata = message.get("metadata", {})

        # Check various indicators
        if "final answer" in content:
            return True

        if metadata.get("status") == "complete":
            return True

        if metadata.get("title") == "Final answer":
            return True

        return False

    def get_step_messages(self) -> List[Dict[str, Any]]:
        """Get messages that represent agent steps."""
        step_messages = []

        for msg in self.assistant_messages:
            metadata = msg.get("metadata", {})

            # Check for step indicators
            if any([
                metadata.get("status") in ["thinking", "running"],
                msg.get("step_number") is not None,
                "Step" in msg.get("content", ""),
                metadata.get("title", "").startswith("Step")
            ]):
                step_messages.append(msg)

        return step_messages

    def has_planning_step(self) -> bool:
        """Check if planning step was received."""
        for msg in self.messages:
            content = msg.get("content", "")
            metadata = msg.get("metadata", {})

            if any([
                "planning" in content.lower(),
                "plan" in metadata.get("title", "").lower(),
                "facts survey" in content.lower()
            ]):
                return True

        return False

    def has_action_step(self) -> bool:
        """Check if action step was received."""
        for msg in self.messages:
            content = msg.get("content", "")
            metadata = msg.get("metadata", {})

            if any([
                "executing" in content.lower(),
                metadata.get("status") == "running",
                "calling tool" in content.lower()
            ]):
                return True
   
        return False

    def clear(self):
        """Clear all collected messages."""
        self.messages.clear()
        self.user_messages.clear()
        self.assistant_messages.clear()
        self.error_messages.clear()
        self.final_answer = None


class WebSocketManager:
    """Manages WebSocket connection for testing."""

    def __init__(self, websocket):
        self.websocket = websocket
        self.collector = MessageCollector()
        self._receive_task: Optional[asyncio.Task] = None

    async def start_receiving(self):
        """Start background task to receive messages."""
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self):
        """Background loop to receive messages."""
        try:
            while True:
                message = await self.websocket.receive_json()
                self.collector.add_message(message)
                logger.debug(f"Received message: {message}")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")

    async def send_query(self, query: str):
        """Send a query to the WebSocket."""
        await self.websocket.send_json({
            "type": "query",
            "query": query
        })

    async def send_ping(self):
        """Send ping message."""
        await self.websocket.send_json({"type": "ping"})

    async def wait_for_final_answer(self, timeout: float = 300):
        """Wait for final answer with timeout."""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.collector.final_answer:
                return self.collector.final_answer

            await asyncio.sleep(0.1)

        raise TimeoutError(
            f"No final answer received within {timeout} seconds"
        )

    async def wait_for_messages(
        self,
        count: int,
        timeout: float = 10
    ) -> List[Dict[str, Any]]:
        """Wait for specific number of messages."""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if len(self.collector.messages) >= count:
                return self.collector.messages[:count]

            await asyncio.sleep(0.1)

        raise TimeoutError(
            f"Expected {count} messages but got "
            f"{len(self.collector.messages)} within {timeout} seconds"
        )

    async def wait_for_condition(
        self,
        condition: Callable[[], bool],
        timeout: float = 10,
        interval: float = 0.1
    ) -> bool:
        """Wait for a condition to be met."""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if condition():
                return True

            await asyncio.sleep(interval)

        return False

    async def close(self):
        """Close WebSocket and cleanup."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        await self.websocket.close()


@asynccontextmanager
async def websocket_session(test_client, url: str):
    """Context manager for WebSocket session."""
    async with test_client.websocket_connect(url) as websocket:
        manager = WebSocketManager(websocket)
        await manager.start_receiving()

        try:
            yield manager
        finally:
            await manager.close()


def assert_message_format(message: Dict[str, Any]):
    """Assert message has correct DSAgentRunMessage format."""
    # Required fields
    assert "role" in message, "Message missing 'role' field"
    assert message["role"] in ["user", "assistant"], \
        f"Invalid role: {message['role']}"

    assert "content" in message, "Message missing 'content' field"
    assert isinstance(message["content"], str), \
        f"Content must be string, got {type(message['content'])}"

    # Optional fields with type checks
    if "metadata" in message:
        assert isinstance(message["metadata"], dict), \
            "Metadata must be a dictionary"

    if "message_id" in message:
        assert isinstance(message["message_id"], str), \
            "Message ID must be a string"
        assert message["message_id"].startswith("msg_"), \
            "Message ID should start with 'msg_'"

    if "timestamp" in message:
        assert isinstance(message["timestamp"], str), \
            "Timestamp must be ISO format string"
        # Validate ISO format
        try:
            datetime.fromisoformat(message["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            raise AssertionError(
                f"Invalid timestamp format: {message['timestamp']}"
            )

    if "session_id" in message:
        assert isinstance(message["session_id"], str), \
            "Session ID must be a string"

    if "step_number" in message:
        assert isinstance(message["step_number"], (int, type(None))), \
            f"Step number must be int or None, got {type(message['step_number'])}"


def extract_final_answer_content(message: Dict[str, Any]) -> Optional[str]:
    """Extract final answer content from message."""
    content = message.get("content", "")

    # Try to extract from JSON format
    if "final answer" in content.lower():
        try:
            # Look for JSON in content
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("content", content)
        except:
            pass

    return content


def count_step_types(messages: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count different types of steps in messages."""
    step_types = {
        "planning": 0,
        "action": 0,
        "observation": 0,
        "final_answer": 0,
        "error": 0,
        "other": 0
    }

    for msg in messages:
        content = msg.get("content", "").lower()
        metadata = msg.get("metadata", {})

        if "planning" in content or "facts survey" in content:
            step_types["planning"] += 1
        elif "executing" in content or metadata.get("status") == "running":
            step_types["action"] += 1
        elif "observation" in content or "result" in content:
            step_types["observation"] += 1
        elif "final answer" in content:
            step_types["final_answer"] += 1
        elif msg.get("type") == "error":
            step_types["error"] += 1
        else:
            step_types["other"] += 1

    return step_types
