#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/session.py
# code style: PEP 8

"""
Simplified session management for DeepSearchAgents Web API v2.

Uses direct Gradio message pass-through for maximum reliability.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, AsyncGenerator
from enum import Enum
from datetime import datetime, timezone
from collections import deque

from src.agents.runtime import agent_runtime
from .models import DSAgentRunMessage, SessionState as SessionStateModel
from .gradio_passthrough_processor import GradioPassthroughProcessor

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """Session states"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    EXPIRED = "expired"


class MessageStore:
    """
    Simple message store for session history.
    """

    def __init__(self, max_messages: int = 10000):
        """
        Initialize message store.

        Args:
            max_messages: Maximum messages to store (FIFO)
        """
        self.messages: deque[DSAgentRunMessage] = deque(maxlen=max_messages)

    def add(self, message: DSAgentRunMessage):
        """Add a message to the store."""
        self.messages.append(message)

    def get_recent(self, limit: int = 100) -> List[DSAgentRunMessage]:
        """Get most recent messages."""
        return list(self.messages)[-limit:]

    def get_count(self) -> int:
        """Get total message count."""
        return len(self.messages)

    def clear(self):
        """Clear all messages."""
        self.messages.clear()


class AgentSession:
    """
    Simplified agent session using Gradio pass-through.
    """

    def __init__(
        self,
        session_id: str,
        agent_type: str = "codact",
        max_steps: Optional[int] = None
    ):
        """
        Initialize agent session.

        Args:
            session_id: Unique session identifier
            agent_type: Type of agent (react/codact)
            max_steps: Maximum steps for agent
        """
        self.session_id = session_id
        self.agent_type = agent_type
        self.max_steps = max_steps or 25

        self.state = SessionState.IDLE
        self.message_store = MessageStore()
        self.processor = GradioPassthroughProcessor(session_id)

        self.agent = None
        self.current_task: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)

        logger.info(
            f"Created session {session_id} with {agent_type} agent"
        )

    async def initialize_agent(self):
        """Initialize the agent instance."""
        if self.agent is not None:
            return

        if self.agent_type == "react":
            self.agent = agent_runtime.create_react_agent(
                step_callback=None,
                debug_mode=False
            )
        else:  # codact
            self.agent = agent_runtime.create_codact_agent(
                step_callback=None,
                debug_mode=False
            )

        # Enable streaming
        if hasattr(self.agent, "enable_streaming"):
            self.agent.enable_streaming = True
        if hasattr(self.agent, "stream_outputs"):
            self.agent.stream_outputs = True

        # Also check if agent has an inner agent object
        if hasattr(self.agent, "agent"):
            if hasattr(self.agent.agent, "stream_outputs"):
                self.agent.agent.stream_outputs = True

        # Set max steps
        if hasattr(self.agent, "max_steps"):
            self.agent.max_steps = self.max_steps
        elif hasattr(self.agent, "agent") and hasattr(
            self.agent.agent, "max_steps"
        ):
            self.agent.agent.max_steps = self.max_steps

    async def process_query(
        self,
        query: str
    ) -> AsyncGenerator[DSAgentRunMessage, None]:
        """
        Process a query and yield messages.

        Args:
            query: User query to process

        Yields:
            DSAgentRunMessage objects
        """
        if self.state == SessionState.PROCESSING:
            raise RuntimeError("Session is already processing a query")

        self.state = SessionState.PROCESSING
        self.current_task = query
        self.last_activity = datetime.now(timezone.utc)

        # Ensure agent is initialized
        await self.initialize_agent()

        # Add user message
        user_msg = DSAgentRunMessage(
            role="user",
            content=query,
            session_id=self.session_id
        )
        self.message_store.add(user_msg)
        yield user_msg

        try:
            # Process through Gradio pass-through
            async for message in self.processor.process_agent_stream(
                self.agent,
                query,
                reset_agent_memory=False
            ):
                # Store and yield each message
                self.message_store.add(message)
                self.last_activity = datetime.now(timezone.utc)
                yield message

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            # Yield error message
            error_msg = DSAgentRunMessage(
                role="assistant",
                content=f"Error: {str(e)}",
                metadata={"error": True},
                session_id=self.session_id
            )
            self.message_store.add(error_msg)
            yield error_msg
            self.state = SessionState.ERROR
        else:
            self.state = SessionState.COMPLETED

    def get_messages(
        self,
        limit: Optional[int] = None
    ) -> List[DSAgentRunMessage]:
        """
        Get messages from the session.

        Args:
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        if limit:
            return self.message_store.get_recent(limit)
        return list(self.message_store.messages)

    def get_state(self) -> SessionStateModel:
        """Get current session state."""
        return SessionStateModel(
            session_id=self.session_id,
            agent_type=self.agent_type,
            state=self.state.value,
            created_at=self.created_at,
            last_activity=self.last_activity,
            message_count=self.message_store.get_count()
        )

    async def cleanup(self):
        """Clean up session resources."""
        logger.info(f"Cleaning up session {self.session_id}")
        self.message_store.clear()
        self.agent = None
        self.state = SessionState.EXPIRED


class AgentSessionManager:
    """
    Manages multiple agent sessions.
    """

    _instance = None
    _sessions: Dict[str, AgentSession] = {}
    _cleanup_task: Optional[asyncio.Task] = None

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize session manager."""
        if self._initialized:
            return

        self._initialized = True
        self._sessions = {}
        self._cleanup_interval = 300  # 5 minutes
        self._session_timeout = 3600  # 1 hour
        self._cleanup_task = None

        logger.info("Initialized AgentSessionManager")

    async def start(self):
        """Start the session manager background tasks."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(
                self._cleanup_expired_sessions()
            )
            logger.info("Started session manager cleanup task")

    def create_session(
        self,
        agent_type: str = "codact",
        max_steps: Optional[int] = None
    ) -> AgentSession:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        session = AgentSession(session_id, agent_type, max_steps)
        self._sessions[session_id] = session

        logger.info(
            f"Created session {session_id}, "
            f"total sessions: {len(self._sessions)}"
        )

        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get session by ID."""
        session = self._sessions.get(session_id)

        if session:
            # Update last activity
            session.last_activity = datetime.now(timezone.utc)

        return session

    def get_or_create(
        self,
        session_id: str,
        agent_type: str = "codact"
    ) -> AgentSession:
        """Get existing session or create new one."""
        session = self.get_session(session_id)

        if not session:
            session = AgentSession(session_id, agent_type)
            self._sessions[session_id] = session

        return session

    async def remove_session(self, session_id: str):
        """Remove a session."""
        session = self._sessions.pop(session_id, None)

        if session:
            await session.cleanup()
            logger.info(
                f"Removed session {session_id}, "
                f"remaining sessions: {len(self._sessions)}"
            )

    async def _cleanup_expired_sessions(self):
        """Periodically clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)

                now = datetime.now(timezone.utc)
                expired = []

                for session_id, session in self._sessions.items():
                    # Check if session is expired
                    if session.state in [
                        SessionState.COMPLETED,
                        SessionState.ERROR,
                        SessionState.EXPIRED
                    ]:
                        time_since_activity = (
                            now - session.last_activity
                        ).total_seconds()

                        if time_since_activity > self._session_timeout:
                            expired.append(session_id)

                # Remove expired sessions
                for session_id in expired:
                    await self.remove_session(session_id)

                if expired:
                    logger.info(
                        f"Cleaned up {len(expired)} expired sessions"
                    )

            except Exception as e:
                logger.error(
                    f"Error in session cleanup: {e}",
                    exc_info=True
                )

    def get_active_sessions(self) -> List[SessionStateModel]:
        """Get info about all active sessions."""
        return [
            session.get_state()
            for session in self._sessions.values()
            if session.state not in [
                SessionState.EXPIRED,
                SessionState.ERROR
            ]
        ]

    async def shutdown(self):
        """Shutdown session manager."""
        logger.info("Shutting down AgentSessionManager")

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clean up all sessions
        for session_id in list(self._sessions.keys()):
            await self.remove_session(session_id)


# Global session manager instance
session_manager = AgentSessionManager()
