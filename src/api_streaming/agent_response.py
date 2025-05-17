#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api_streaming/agent_response.py
# code style: PEP 8
# code-related content: MUST be in English
"""
Agent Run Steps Events & Steps Data MQ Server - Core Implementation
Provides real-time agent run events and steps data via Redis.

NOTE: Agent Callbacks &  Stream Real-Time Data(Streamable HTTP & SSE)
      FastAPI are not working.
"""

import json
import logging
import uuid
import os
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
import time
import asyncio

from pydantic import BaseModel, Field
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Core event types for agent execution"""
    INIT = "init"                # Session initialization event
    STEP_UPDATE = "step_update"  # Step update event
    COMPLETE = "complete"        # Session completion event
    ERROR = "error"              # Error event


class AgentSessionStatus(str, Enum):
    """Agent session status"""
    CREATED = "created"    # Created but not started
    RUNNING = "running"    # Running
    COMPLETED = "completed"  # Completed
    ERROR = "error"        # Error


class AgentEvent(BaseModel):
    """Agent event base model"""
    session_id: str
    event_type: EventType
    timestamp: float = Field(
        default_factory=lambda: datetime.now().timestamp()
    )
    data: Dict[str, Any]


class AgentSession(BaseModel):
    """Agent session information"""
    id: str
    status: AgentSessionStatus = AgentSessionStatus.CREATED
    query: str = ""
    agent_type: str = "codact"
    created_at: float = Field(
        default_factory=lambda: datetime.now().timestamp()
    )
    updated_at: float = Field(
        default_factory=lambda: datetime.now().timestamp()
    )


class AgentObserver:
    """Agent observer class for tracking and publishing agent events"""

    def __init__(self):
        """Initialize the agent observer"""
        # Get Redis configuration from environment
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD", "yourpassword")

        # Create Redis connection URL
        self.redis_url = (
            f"redis://:{redis_password}@{redis_host}:{redis_port}/0"
        )
        self.redis_pool = None
        self._create_redis_pool()

        logger.info(
            f"AgentObserver initialized with Redis at "
            f"{redis_host}:{redis_port}"
        )

    def _create_redis_pool(self):
        """Create Redis connection pool"""
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True
            )
            logger.info("Redis connection pool created")
        except Exception as e:
            logger.error(f"Error creating Redis connection pool: {e}")
            raise

    async def _get_redis_connection(self):
        """Get Redis connection from pool"""
        if not self.redis_pool:
            self._create_redis_pool()
        return redis.Redis(connection_pool=self.redis_pool)

    async def create_session(
        self, query: str, agent_type: str = "codact"
    ) -> str:
        """Create a new agent session

        Args:
            query: User query
            agent_type: Agent type

        Returns:
            str: Session ID
        """
        session_id = str(uuid.uuid4())

        # Create session object
        session = AgentSession(
            id=session_id,
            status=AgentSessionStatus.CREATED,
            query=query,
            agent_type=agent_type
        )

        # Store session in Redis
        r = await self._get_redis_connection()
        session_key = f"session:{session_id}"
        await r.hset(session_key, mapping=session.dict())
        await r.expire(session_key, 60 * 60 * 24)  # 24 hour expiry

        # Add to session index
        await r.sadd("sessions:index", session_id)

        logger.info(f"Created session {session_id} for {agent_type} agent")
        return session_id

    async def _get_session_data(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get session data from Redis

        Args:
            session_id: Session ID

        Returns:
            Optional[Dict[str, Any]]: Session data or None
        """
        try:
            r = await self._get_redis_connection()
            session_key = f"session:{session_id}"
            session_data = await r.hgetall(session_key)

            if not session_data:
                return None

            # Convert numeric fields
            if "created_at" in session_data:
                session_data["created_at"] = float(session_data["created_at"])
            if "updated_at" in session_data:
                session_data["updated_at"] = float(session_data["updated_at"])

            return session_data
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None

    async def list_sessions(self) -> List[str]:
        """List all sessions

        Returns:
            List[str]: List of session IDs
        """
        try:
            r = await self._get_redis_connection()
            return await r.smembers("sessions:index")
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    async def update_session_status(
        self,
        session_id: str,
        status: AgentSessionStatus
    ) -> bool:
        """Update session status

        Args:
            session_id: Session ID
            status: New status

        Returns:
            bool: Success flag
        """
        try:
            r = await self._get_redis_connection()
            session_key = f"session:{session_id}"

            # Check if session exists
            if not await r.exists(session_key):
                logger.error(f"Session {session_id} not found")
                return False

            # Update status and timestamp
            await r.hset(
                session_key,
                mapping={
                    "status": status,
                    "updated_at": datetime.now().timestamp()
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False

    async def publish_step(
        self,
        session_id: str,
        step_data: Dict[str, Any]
    ) -> bool:
        """Optimized step publishing method, ensuring real-time push

        Args:
            session_id: session ID
            step_data: step data

        Returns:
            bool: success flag
        """
        try:
            # ensure basic fields exist
            if "session_id" not in step_data:
                step_data["session_id"] = session_id

            if "timestamp" not in step_data:
                step_data["timestamp"] = datetime.now().timestamp()

            if "event_type" not in step_data:
                step_data["event_type"] = "step"

            # format step data
            formatted_step = self.format_step_data(step_data, session_id)

            # get Redis connection
            r = await self._get_redis_connection()

            # publish to all possible channels, ensure clients can receive
            all_channels = [
                f"agent_step_notifications:{session_id}",
                f"agent_direct_notifications:{session_id}",
                f"agent_runtime_events:{session_id}",
                f"agent_event_notifications:{session_id}"
            ]

            # parallel publish to improve speed
            publish_tasks = [
                r.publish(channel, json.dumps(formatted_step))
                for channel in all_channels
            ]
            publish_results = await asyncio.gather(*publish_tasks)

            # add to step stream
            stream_key = f"agent_steps:{session_id}"
            await r.xadd(
                stream_key,
                formatted_step,
                maxlen=500
            )

            # add to global session step list immediately
            step_counter = formatted_step.get('step_counter', 0)
            step_key = f"step:{session_id}:{step_counter}"
            await r.hset(step_key, mapping=formatted_step)

            logger.info(
                f"Step published to {len(all_channels)} channels, "
                f"total receivers: {sum(publish_results)}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error publishing step for session {session_id}: {e}",
                exc_info=True
            )
            return False

    async def publish_event(
        self,
        session_id: str,
        event_type: EventType,
        data: Dict[str, Any]
    ) -> bool:
        """Publish event to Redis stream

        Args:
            session_id: Session ID
            event_type: Event type
            data: Event data

        Returns:
            bool: Success flag
        """
        try:
            formatted_event = self.format_event_data(
                session_id,
                event_type,
                data
            )
            r = await self._get_redis_connection()

            # 1. add to Redis stream
            stream_key = f"agent_events:{session_id}"
            event_id = await r.xadd(
                stream_key,
                formatted_event,
                maxlen=1000
            )

            # 2. publish to PubSub channel, for real-time notifications
            notification_channel = f"agent_event_notifications:{session_id}"
            await r.publish(
                notification_channel,
                json.dumps({
                    "session_id": session_id,
                    "event_id": event_id,
                    "event_type": event_type,
                    "timestamp": time.time(),
                    "data": data,
                    "notification_type": "event_update"
                })
            )

            # 3. update session status
            if event_type == EventType.COMPLETE:
                await self.update_session_status(
                    session_id,
                    AgentSessionStatus.COMPLETED
                )
            elif event_type == EventType.ERROR:
                await self.update_session_status(
                    session_id,
                    AgentSessionStatus.ERROR
                )

            # 4. store event data
            event_id_str = str(uuid.uuid4())
            event_key = f"event:{session_id}:{event_id_str}"
            await r.hset(event_key, mapping=formatted_event)
            await r.expire(event_key, 60 * 60 * 24)  # 24 hours expiration

            # 5. add to event index
            await r.sadd(f"events:index:{session_id}", event_id_str)

            return True
        except Exception as e:
            logger.error(
                f"Error publishing event for session {session_id}: {e}"
            )
            return False

    async def record_final_answer(
        self,
        session_id: str,
        answer_data: Any
    ) -> bool:
        """Record final answer and complete the session

        Args:
            session_id: Session ID
            answer_data: Final answer data

        Returns:
            bool: Success flag
        """
        try:
            # Format answer data
            formatted_answer = self.format_final_answer(answer_data)

            # Create complete event
            event_data = {
                "timestamp": datetime.now().timestamp(),
                "answer": formatted_answer
            }

            # Publish complete event
            await self.publish_event(
                session_id,
                EventType.COMPLETE,
                event_data
            )

            # Update session with final answer
            r = await self._get_redis_connection()
            session_key = f"session:{session_id}"
            await r.hset(
                session_key,
                mapping={
                    "final_answer": json.dumps(formatted_answer),
                    "status": AgentSessionStatus.COMPLETED,
                    "updated_at": datetime.now().timestamp()
                }
            )

            return True
        except Exception as e:
            logger.error(
                f"Error recording final answer for session {session_id}: {e}"
            )
            return False

    def format_step_data(
        self,
        step_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Format step data for publishing

        Args:
            step_data: Step data from agent_callbacks
            session_id: Session ID

        Returns:
            Dict[str, Any]: Formatted step data
        """
        # Add session ID and timestamp if not present
        if "session_id" not in step_data:
            step_data["session_id"] = session_id

        if "timestamp" not in step_data:
            step_data["timestamp"] = datetime.now().timestamp()

        # Convert any non-string values to strings for Redis compatibility
        formatted_data = {}
        for key, value in step_data.items():
            if isinstance(value, (dict, list)):
                formatted_data[key] = json.dumps(value)
            elif value is None:
                formatted_data[key] = ""
            else:
                formatted_data[key] = str(value)

        return formatted_data

    def format_event_data(
        self,
        session_id: str,
        event_type: EventType,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format event data for publishing

        Args:
            session_id: Session ID
            event_type: Event type
            data: Event data

        Returns:
            Dict[str, Any]: Formatted event data
        """
        # Create event object
        event = AgentEvent(
            session_id=session_id,
            event_type=event_type,
            data=data
        )

        # Convert to dict
        event_dict = event.dict()

        # Convert any non-string values to strings for Redis compatibility
        formatted_data = {}
        for key, value in event_dict.items():
            if key == "data" and isinstance(value, dict):
                formatted_data[key] = json.dumps(value)
            elif isinstance(value, (dict, list)):
                formatted_data[key] = json.dumps(value)
            elif value is None:
                formatted_data[key] = ""
            else:
                formatted_data[key] = str(value)

        return formatted_data

    def format_final_answer(self, answer_data: Any) -> Dict[str, Any]:
        """Format final answer data

        Args:
            answer_data: Final answer data

        Returns:
            Dict[str, Any]: Formatted final answer
        """
        # Format answer data
        if not isinstance(answer_data, dict):
            try:
                # Try to parse JSON
                if isinstance(answer_data, str):
                    try:
                        answer_data = json.loads(answer_data)
                    except Exception:
                        answer_data = {"content": answer_data}
                else:
                    answer_data = {"content": str(answer_data)}
            except Exception:
                answer_data = {"content": str(answer_data)}

        return answer_data

    async def _get_session_status(
        self,
        session_id: str
    ) -> Optional[str]:
        """Get session status quickly

        Args:
            session_id: session ID

        Returns:
            Optional[str]: session status or None
        """
        try:
            r = await self._get_redis_connection()
            status = await r.hget(f"session:{session_id}", "status")
            return status
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return None


# Create agent observer instance
agent_observer = AgentObserver()
