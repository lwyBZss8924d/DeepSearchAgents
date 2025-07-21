#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v2/session.py
# code style: PEP 8

"""
Session management for DeepSearchAgents Web API v2.

Handles agent lifecycle, event streaming, and multi-turn conversations
while maintaining isolation from existing CLI and MCP functionality.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, AsyncGenerator
from enum import Enum
from datetime import datetime, timedelta
from collections import deque

from src.agents.runtime import agent_runtime
from src.agents.base_agent import BaseAgent
from .events import (
    BaseEvent, EventUnion, TaskStartEvent, TaskCompleteEvent,
    AgentThoughtEvent, StreamDeltaEvent, TokenUpdateEvent
)
from .pipeline import EventProcessor, StreamEventAggregator

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """Session states"""
    IDLE = "idle"
    PROCESSING = "processing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"
    EXPIRED = "expired"


class EventStore:
    """
    Store and manage events for a session.
    
    Provides efficient storage and retrieval of events with
    support for filtering and pagination.
    """
    
    def __init__(self, max_events: int = 10000):
        """
        Initialize event store.
        
        Args:
            max_events: Maximum events to store (FIFO)
        """
        self.events: deque[BaseEvent] = deque(maxlen=max_events)
        self.event_index: Dict[str, BaseEvent] = {}
        self.step_events: Dict[int, List[BaseEvent]] = {}
        
    def add(self, event: BaseEvent):
        """Add an event to the store."""
        self.events.append(event)
        self.event_index[event.event_id] = event
        
        # Index by step number if available
        if event.step_number is not None:
            if event.step_number not in self.step_events:
                self.step_events[event.step_number] = []
            self.step_events[event.step_number].append(event)
    
    def get_by_id(self, event_id: str) -> Optional[BaseEvent]:
        """Get event by ID."""
        return self.event_index.get(event_id)
    
    def get_by_step(self, step_number: int) -> List[BaseEvent]:
        """Get all events for a step."""
        return self.step_events.get(step_number, [])
    
    def get_by_type(
        self,
        event_type: str,
        limit: Optional[int] = None
    ) -> List[BaseEvent]:
        """Get events by type."""
        matching = [
            e for e in self.events
            if e.event_type == event_type
        ]
        
        if limit:
            return matching[-limit:]
        return matching
    
    def get_recent(self, limit: int = 100) -> List[BaseEvent]:
        """Get most recent events."""
        return list(self.events)[-limit:]
    
    def clear(self):
        """Clear all events."""
        self.events.clear()
        self.event_index.clear()
        self.step_events.clear()


class AgentSession:
    """
    Manages a single agent session with event streaming.
    
    Handles agent lifecycle, query processing, and event generation
    for web clients.
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
        self.event_store = EventStore()
        self.event_processor = EventProcessor(session_id)
        self.stream_aggregator = StreamEventAggregator(session_id)
        
        self.agent: Optional[BaseAgent] = None
        self.current_task: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
        # Performance tracking
        self.start_time: Optional[float] = None
        self.total_tokens = {"input": 0, "output": 0}
        
        # Event queue for streaming
        self.event_queue: asyncio.Queue[Optional[BaseEvent]] = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"Created session {session_id} with {agent_type} agent"
        )
    
    async def initialize_agent(self):
        """Initialize the agent instance."""
        if self.agent is not None:
            return
        
        # Create agent with web-specific callback
        step_callback = self._create_step_callback()
        
        if self.agent_type == "react":
            self.agent = agent_runtime.create_react_agent(
                step_callback=step_callback,
                debug_mode=False
            )
        else:  # codact
            self.agent = agent_runtime.create_codact_agent(
                step_callback=step_callback,
                debug_mode=False
            )
        
        # Set max steps
        if hasattr(self.agent, "max_steps"):
            self.agent.max_steps = self.max_steps
        elif hasattr(self.agent, "agent") and hasattr(
            self.agent.agent, "max_steps"
        ):
            self.agent.agent.max_steps = self.max_steps
    
    def _create_step_callback(self):
        """Create callback for agent steps."""
        def callback(memory_step):
            # Process step into events
            try:
                events = self.event_processor.process_memory_step(
                    memory_step
                )
                for event in events:
                    # Store event
                    self.event_store.add(event)
                    # Queue for streaming
                    asyncio.create_task(
                        self.event_queue.put(event)
                    )
            except Exception as e:
                logger.error(
                    f"Error processing memory step: {e}",
                    exc_info=True
                )
        
        return callback
    
    async def process_query(
        self,
        query: str,
        stream: bool = True
    ) -> AsyncGenerator[BaseEvent, None]:
        """
        Process a query and yield events.
        
        Args:
            query: User query to process
            stream: Whether to stream events
            
        Yields:
            Events as they are generated
        """
        if self.state == SessionState.PROCESSING:
            raise RuntimeError("Session is already processing a query")
        
        self.state = SessionState.PROCESSING
        self.current_task = query
        self.last_activity = datetime.utcnow()
        self.start_time = time.time()
        
        # Ensure agent is initialized
        await self.initialize_agent()
        
        # Emit task start event
        start_event = TaskStartEvent(
            session_id=self.session_id,
            query=query,
            agent_type=self.agent_type,
            max_steps=self.max_steps
        )
        self.event_store.add(start_event)
        yield start_event
        
        if stream:
            # Stream events as they are generated
            async for event in self._process_streaming(query):
                yield event
        else:
            # Process all at once
            events = await self._process_batch(query)
            for event in events:
                yield event
        
        # Mark session as completed
        self.state = SessionState.COMPLETED
    
    async def _process_streaming(
        self,
        query: str
    ) -> AsyncGenerator[BaseEvent, None]:
        """Process query with streaming."""
        self.state = SessionState.STREAMING
        
        # Start agent processing in background
        self.processing_task = asyncio.create_task(
            self._run_agent_async(query)
        )
        
        # Stream events from queue
        try:
            while True:
                # Wait for events with timeout
                try:
                    event = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=0.1
                    )
                    
                    if event is None:
                        # Sentinel value indicating completion
                        break
                    
                    yield event
                    
                except asyncio.TimeoutError:
                    # Check if processing is complete
                    if self.processing_task.done():
                        # Drain any remaining events
                        while not self.event_queue.empty():
                            event = await self.event_queue.get()
                            if event is not None:
                                yield event
                        break
                    
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            self.state = SessionState.ERROR
            raise
    
    async def _process_batch(
        self,
        query: str
    ) -> List[BaseEvent]:
        """Process query in batch mode."""
        events = []
        
        async for event in self._process_streaming(query):
            events.append(event)
        
        return events
    
    async def _run_agent_async(self, query: str):
        """Run agent asynchronously."""
        try:
            # Check if agent supports streaming
            if hasattr(self.agent, "run") and asyncio.iscoroutinefunction(
                self.agent.run
            ):
                # Async agent
                result = await self.agent.run(query, stream=False)
            else:
                # Sync agent - run in executor
                import concurrent.futures
                
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(
                        executor,
                        self.agent.run,
                        query,
                        False  # stream=False
                    )
            
            # Generate completion event
            total_time = time.time() - self.start_time
            complete_event = TaskCompleteEvent(
                session_id=self.session_id,
                success=True,
                total_steps=self.event_processor.step_counter,
                total_time=total_time,
                reason="Task completed successfully"
            )
            
            self.event_store.add(complete_event)
            await self.event_queue.put(complete_event)
            
        except Exception as e:
            logger.error(f"Agent execution error: {e}", exc_info=True)
            
            # Generate error completion event
            total_time = time.time() - self.start_time
            error_event = TaskCompleteEvent(
                session_id=self.session_id,
                success=False,
                total_steps=self.event_processor.step_counter,
                total_time=total_time,
                reason=f"Error: {str(e)}"
            )
            
            self.event_store.add(error_event)
            await self.event_queue.put(error_event)
            
        finally:
            # Send sentinel to indicate completion
            await self.event_queue.put(None)
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        step_number: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[BaseEvent]:
        """
        Get events from the session.
        
        Args:
            event_type: Filter by event type
            step_number: Filter by step number
            limit: Maximum events to return
            
        Returns:
            List of events matching criteria
        """
        if step_number is not None:
            return self.event_store.get_by_step(step_number)
        elif event_type is not None:
            return self.event_store.get_by_type(event_type, limit)
        else:
            return self.event_store.get_recent(limit or 100)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current session state."""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "agent_type": self.agent_type,
            "current_task": self.current_task,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "total_events": len(self.event_store.events),
            "total_steps": self.event_processor.step_counter,
            "total_tokens": self.total_tokens
        }
    
    async def cleanup(self):
        """Clean up session resources."""
        logger.info(f"Cleaning up session {self.session_id}")
        
        # Cancel processing if active
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Clear event store
        self.event_store.clear()
        
        # Clear agent
        self.agent = None
        
        self.state = SessionState.EXPIRED


class AgentSessionManager:
    """
    Manages multiple agent sessions.
    
    Provides session lifecycle management, cleanup, and access control.
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
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(
            self._cleanup_expired_sessions()
        )
        
        logger.info("Initialized AgentSessionManager")
    
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
            session.last_activity = datetime.utcnow()
        
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
                
                now = datetime.utcnow()
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
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
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