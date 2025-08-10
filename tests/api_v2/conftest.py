#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/api_v2/conftest.py
# code style: PEP 8

"""
Pytest configuration and shared fixtures for API v2 tests.
"""

import pytest
import asyncio
import sys
import os
from typing import AsyncGenerator, Dict, Any
from fastapi.testclient import TestClient
import httpx

# Add src to path
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', '..'
))

from src.api.v2.main import app
from src.api.v2.session import session_manager
from src.api.v2.models import DSAgentRunMessage


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async HTTP client for API testing."""
    # For testing against running server
    async with httpx.AsyncClient(
        base_url="http://0.0.0.0:8000"
    ) as client:
        yield client


@pytest.fixture
async def websocket_url(api_client: httpx.AsyncClient) -> str:
    """Create a session and return WebSocket URL."""
    # Create session via API
    response = await api_client.post(
        "/api/v2/sessions",
        json={"agent_type": "codact", "max_steps": 25}
    )
    assert response.status_code == 200
    data = response.json()

    # Return WebSocket URL
    return data["websocket_url"]


@pytest.fixture
async def test_session_id() -> AsyncGenerator[str, None]:
    """Create a test session and clean up after."""
    # Create session
    session = session_manager.create_session(
        agent_type="codact",
        max_steps=25
    )
    session_id = session.session_id

    yield session_id

    # Cleanup
    await session_manager.remove_session(session_id)


@pytest.fixture
def validate_ds_message():
    """Factory fixture for validating DSAgentRunMessage."""
    def _validate(message: Dict[str, Any]):
        """Validate message structure."""
        # Required fields
        assert "role" in message
        assert message["role"] in ["user", "assistant"]
        assert "content" in message
        assert isinstance(message["content"], str)

        # Optional fields
        if "metadata" in message:
            assert isinstance(message["metadata"], dict)

        if "message_id" in message:
            assert isinstance(message["message_id"], str)

        if "timestamp" in message:
            assert isinstance(message["timestamp"], str)

        if "session_id" in message:
            assert isinstance(message["session_id"], str)

        if "step_number" in message:
            assert isinstance(message["step_number"], (int, type(None)))

        return True

    return _validate


@pytest.fixture
def mock_agent_response():
    """Mock agent response for testing."""
    return {
        "final_answer": "Test answer",
        "steps": [
            {"type": "planning", "content": "Planning step"},
            {"type": "action", "content": "Action step"}
        ]
    }


# Configure test timeouts
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests"
    )


# Async test utilities
@pytest.fixture
async def wait_for_condition():
    """Utility to wait for a condition with timeout."""
    async def _wait(condition_func, timeout=10, interval=0.1):
        elapsed = 0
        while elapsed < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(interval)
            elapsed += interval
        return False

    return _wait
