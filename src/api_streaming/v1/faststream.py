#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api_streaming/v1/faststream.py
# code style: PEP 8
# code-related content: MUST be in English
"""
FastStream integration for Redis messaging

NOTE: Agent Callbacks &  Stream Real-Time Data(Streamable HTTP & SSE)
      FastAPI are not working.
"""

from datetime import datetime
import logging
import os
from typing import Dict, Any
from faststream import FastStream
from faststream.redis import RedisBroker
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import time
import json

from src.api_streaming.agent_response import (
    agent_observer, EventType, AgentSessionStatus
)

logger = logging.getLogger(__name__)

# Get Redis configuration from environment
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_password = os.getenv("REDIS_PASSWORD", "yourpassword")
redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"

# Create Redis broker with correct configuration
broker = RedisBroker(redis_url)
app = FastStream(broker)

# Create a FastAPI router
api_router = APIRouter()


# Define message models
class StepData(BaseModel):
    """Step data model"""
    session_id: str
    step_counter: int
    step_type: str
    timestamp: float
    # Additional fields would be included dynamically


class EventData(BaseModel):
    """Event data model"""
    session_id: str
    event_type: str
    timestamp: float
    data: Dict[str, Any]


class SessionCreate(BaseModel):
    """Session creation request model"""
    query: str
    agent_type: str = "codact"


class SessionResponse(BaseModel):
    """Session response model"""
    session_id: str
    status: str


# Define subscribers and publishers for Redis Streams
# Note: Using stream with message filter in handler, not in decorator
@broker.subscriber("agent_steps")
async def handle_step(
    step_data: Dict[str, Any],
    logger: logging.Logger
):
    """Step subscriber

    This subscriber is called when a new step is published.
    It updates the session status if needed.

    Args:
        step_data: Step data
        logger: FastStream logger
    """
    # Extract session ID from step data
    session_id = step_data.get("session_id")
    if not session_id:
        logger.warning("Received step without session_id")
        return

    # Log step reception
    logger.info(f"Received step for session {session_id}")

    # Update session status if needed
    session = await agent_observer._get_session_data(session_id)
    if session and session["status"] == AgentSessionStatus.CREATED:
        session["status"] = AgentSessionStatus.RUNNING


@broker.subscriber("agent_events")
async def handle_event(
    event_data: Dict[str, Any],
    logger: logging.Logger
):
    """Event subscriber

    This subscriber is called when a new event is published.
    It updates the session status based on the event type.

    Args:
        event_data: Event data
        logger: FastStream logger
    """
    # Extract session ID and event type from event data
    session_id = event_data.get("session_id")
    event_type = event_data.get("event_type")

    if not session_id:
        logger.warning("Received event without session_id")
        return

    # Log event reception
    logger.info(f"Received event {event_type} for session {session_id}")

    # Update session status based on event type
    session = await agent_observer._get_session_data(session_id)
    if session:
        if event_type == EventType.COMPLETE:
            session["status"] = AgentSessionStatus.COMPLETED
        elif event_type == EventType.ERROR:
            session["status"] = AgentSessionStatus.ERROR


@broker.publisher("agent_events")
@broker.publisher("agent_sessions")
async def create_session(data: SessionCreate) -> Dict[str, Any]:
    """Create a new agent session

    Args:
        data: Session creation data

    Returns:
        Dict[str, Any]: Session data
    """
    # Create session using agent_observer
    session_id = await agent_observer.create_session(
        data.query, data.agent_type
    )

    # Get session data
    session = await agent_observer._get_session_data(session_id)

    # Create init event
    init_event = agent_observer.format_event_data(
        session_id=session_id,
        event_type=EventType.INIT,
        data={
            "agent_type": data.agent_type,
            "query": data.query,
            "timestamp": session["created_at"]
        }
    )

    # Return both the session and publish the event
    return {
        "session": session,
        "event": init_event
    }


@broker.publisher("agent_steps")
async def publish_step(
    step_data: Dict[str, Any],
    session_id: str
) -> Dict[str, Any]:
    """Publish step data

    This method is called by agent_callbacks to publish step data.
    Improved to ensure real-time streaming.

    Args:
        step_data: Step data
        session_id: Session ID

    Returns:
        Dict[str, Any]: Formatted step data
    """
    # Ensure session_id is in step_data
    if "session_id" not in step_data:
        step_data["session_id"] = session_id

    # Format step data
    formatted_step = agent_observer.format_step_data(step_data, session_id)

    # Publish step update event for real-time notifications
    event_data = agent_observer.format_event_data(
        session_id=session_id,
        event_type=EventType.STEP_UPDATE,
        data={
            "step_number": formatted_step.get("step_counter", 0),
            "step_type": formatted_step.get("step_type"),
            "timestamp": formatted_step.get("timestamp", time.time())
        }
    )

    # Publish event - this must happen immediately
    await publish_event(event_data, session_id)

    # use synchronous Redis client to ensure real-time push
    import redis as sync_redis
    r = sync_redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        decode_responses=True
    )

    # publish to PubSub channel for real-time notifications
    r.publish(
        f"agent_step_notifications:{session_id}",
        json.dumps(formatted_step)
    )

    r.close()

    return formatted_step


@broker.publisher("agent_events")
async def publish_event(
    event_data: Dict[str, Any],
    session_id: str
) -> Dict[str, Any]:
    """Publish event data

    This method is called to publish event data.

    Args:
        event_data: Event data
        session_id: Session ID

    Returns:
        Dict[str, Any]: Event data
    """
    # Ensure session_id is in event_data
    if "session_id" not in event_data:
        event_data["session_id"] = session_id

    # Update session status based on event type
    if "event_type" in event_data:
        session = await agent_observer._get_session_data(session_id)
        if session:
            if event_data["event_type"] == EventType.COMPLETE:
                session["status"] = AgentSessionStatus.COMPLETED
            elif event_data["event_type"] == EventType.ERROR:
                session["status"] = AgentSessionStatus.ERROR

    return event_data


@broker.publisher("agent_events")
async def publish_final_answer(
    answer_data: Any,
    session_id: str
) -> Dict[str, Any]:
    """Publish final answer

    This method is called to publish the final answer.

    Args:
        answer_data: Final answer data
        session_id: Session ID

    Returns:
        Dict[str, Any]: Complete event data
    """
    # Format answer data
    formatted_answer = agent_observer.format_final_answer(answer_data)

    # Create complete event
    event_data = agent_observer.format_event_data(
        session_id=session_id,
        event_type=EventType.COMPLETE,
        data={
            "timestamp": datetime.now().timestamp(),
            "answer": formatted_answer
        }
    )

    # Update session
    session = await agent_observer._get_session_data(session_id)
    if session:
        session["final_answer"] = formatted_answer
        session["status"] = AgentSessionStatus.COMPLETED

    return event_data


# HTTP endpoint to get session data
# (using FastAPI router instead of broker.api)
@api_router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """Get session data

    Args:
        session_id: Session ID

    Returns:
        Dict[str, Any]: Session data
    """
    # Get session data
    session = await agent_observer._get_session_data(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session
