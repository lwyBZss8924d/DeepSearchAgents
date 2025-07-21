#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/ui_common/web_adapter.py
# code style: PEP 8

"""
Web UI adapter for DeepSearchAgents.

Provides integration between agents and the Web API v2 event system,
enabling real-time streaming of agent execution steps to web clients.
"""

import asyncio
import logging
from typing import Any, Dict, Generator, List, Optional, Union
from smolagents.models import ChatMessageStreamDelta
from smolagents.memory import MemoryStep

from src.api.v2.events import (
    AgentThoughtEvent, StreamDeltaEvent
)
from src.api.v2.pipeline import EventProcessor, StreamEventAggregator

logger = logging.getLogger(__name__)


class WebUIAdapter:
    """
    Adapter class to make DeepSearchAgent compatible with Web API v2.
    
    Similar to GradioUIAdapter but designed for web event streaming
    rather than Gradio-specific formatting.
    """
    
    def __init__(
        self,
        agent,
        session_id: Optional[str] = None,
        event_callback=None
    ):
        """
        Initialize the web adapter.
        
        Args:
            agent: The original DeepSearchAgent instance
            session_id: Optional session ID for events
            event_callback: Callback function for events
        """
        self.agent = agent
        self.session_id = session_id
        self.event_callback = event_callback
        
        # Event processors
        self.event_processor = EventProcessor(session_id)
        self.stream_aggregator = StreamEventAggregator(session_id)
        
        # Expose agent properties
        self.tools = getattr(agent, 'tools', [])
        self.memory = getattr(agent, 'memory', None)
        self.name = getattr(agent, 'name', 'DeepSearchAgent')
        self.description = getattr(
            agent, 
            'description',
            'DeepSearchAgent for web research'
        )
        
        # Model reference for token counting
        if hasattr(agent, 'model'):
            self.model = agent.model
        elif hasattr(agent, 'agent') and hasattr(agent.agent, 'model'):
            self.model = agent.agent.model
        else:
            self.model = None
    
    async def run_async(
        self,
        task: str,
        stream: bool = True,
        reset: bool = True,
        images: Optional[List[Any]] = None,
        additional_args: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None
    ) -> Union[str, AsyncGenerator[Any, None]]:
        """
        Run the agent asynchronously with event emission.
        
        Args:
            task: Task description or user query
            stream: Whether to stream output
            reset: Whether to reset the session
            images: Optional list of images
            additional_args: Additional arguments
            max_steps: Maximum number of steps
            
        Returns:
            Final result or async generator of events
        """
        logger.info(f"Running web agent with task: {task[:50]}...")
        
        # Configure max steps if provided
        if max_steps is not None and hasattr(self.agent, 'max_steps'):
            self.agent.max_steps = max_steps
        
        if stream:
            return self._run_streaming(task, reset)
        else:
            return await self._run_batch(task, reset)
    
    def run(
        self,
        task: str,
        stream: bool = True,
        reset: bool = True,
        images: Optional[List[Any]] = None,
        additional_args: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None
    ) -> Union[str, Generator[Any, None, None]]:
        """
        Synchronous run method for compatibility.
        
        Wraps async execution for sync contexts.
        """
        if stream:
            # Return a sync generator that wraps async
            def sync_generator():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    async_gen = self._run_streaming(task, reset)
                    
                    while True:
                        try:
                            event = loop.run_until_complete(
                                async_gen.__anext__()
                            )
                            yield event
                        except StopAsyncIteration:
                            break
                finally:
                    loop.close()
            
            return sync_generator()
        else:
            # Run async in new loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                return loop.run_until_complete(
                    self._run_batch(task, reset)
                )
            finally:
                loop.close()
    
    async def _run_streaming(
        self,
        task: str,
        reset: bool
    ) -> AsyncGenerator[Any, None]:
        """
        Run agent with streaming events.
        
        Yields events as they are generated.
        """
        # Reset stream aggregator
        self.stream_aggregator.reset()
        
        # Check if agent supports streaming
        agent_supports_stream = (
            hasattr(self.agent, 'run') and
            'stream' in self.agent.run.__code__.co_varnames
        )
        
        if agent_supports_stream:
            # Use agent's native streaming
            try:
                # Run agent with streaming
                if asyncio.iscoroutinefunction(self.agent.run):
                    # Async agent
                    result_gen = self.agent.run(task, stream=True)
                    
                    async for item in result_gen:
                        # Process different types of streaming output
                        if isinstance(item, ChatMessageStreamDelta):
                            # Convert to our event
                            event = self.stream_aggregator.process_stream_delta(
                                item
                            )
                            if event:
                                yield event
                        elif isinstance(item, MemoryStep):
                            # Convert memory step to events
                            events = self.event_processor.process_memory_step(
                                item
                            )
                            for event in events:
                                yield event
                        else:
                            # Try to convert to string for thought event
                            yield AgentThoughtEvent(
                                session_id=self.session_id,
                                content=str(item),
                                streaming=True,
                                complete=False
                            )
                else:
                    # Sync agent - run in thread
                    import concurrent.futures
                    
                    loop = asyncio.get_event_loop()
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # This is tricky - we need to handle sync generator
                        # in async context
                        future = loop.run_in_executor(
                            executor,
                            lambda: list(self.agent.run(task, stream=True))
                        )
                        
                        items = await future
                        
                        for item in items:
                            if isinstance(item, MemoryStep):
                                events = self.event_processor.process_memory_step(
                                    item
                                )
                                for event in events:
                                    yield event
                
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                raise
        else:
            # Agent doesn't support streaming, fall back to batch
            result = await self._run_batch(task, reset)
            
            # Emit final thought event with result
            yield AgentThoughtEvent(
                session_id=self.session_id,
                content=str(result),
                streaming=False,
                complete=True
            )
    
    async def _run_batch(self, task: str, reset: bool) -> str:
        """
        Run agent in batch mode.
        
        Returns final result after processing.
        """
        try:
            if asyncio.iscoroutinefunction(self.agent.run):
                # Async agent
                result = await self.agent.run(task, stream=False)
            else:
                # Sync agent - run in executor
                import concurrent.futures
                
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(
                        executor,
                        self.agent.run,
                        task,
                        False  # stream=False
                    )
            
            return str(result)
            
        except Exception as e:
            logger.error(f"Batch execution error: {e}", exc_info=True)
            raise
    
    def process_memory_step(self, step: MemoryStep) -> List[Any]:
        """
        Process a memory step into web events.
        
        This method is called by step callbacks.
        """
        events = self.event_processor.process_memory_step(step)
        
        # Emit events via callback if provided
        if self.event_callback:
            for event in events:
                try:
                    self.event_callback(event)
                except Exception as e:
                    logger.error(
                        f"Error in event callback: {e}",
                        exc_info=True
                    )
        
        return events
    
    def get_token_counts(self) -> Dict[str, int]:
        """
        Get token usage information.
        
        Returns:
            Dict with token count information
        """
        if not self.model:
            return {"input": 0, "output": 0}
        
        # Try different ways to get token information
        if hasattr(self.model, "get_token_counts"):
            try:
                return self.model.get_token_counts()
            except Exception:
                pass
        
        if hasattr(self.model, "last_input_token_count"):
            return {
                "input": getattr(self.model, "last_input_token_count", 0),
                "output": getattr(self.model, "last_output_token_count", 0)
            }
        
        return {"input": 0, "output": 0}
    
    def __getattr__(self, name):
        """
        Proxy attribute access to underlying agent.
        
        This allows the adapter to be used as a drop-in replacement.
        """
        return getattr(self.agent, name)


def create_web_compatible_agent(
    agent,
    session_id: Optional[str] = None,
    event_callback=None
):
    """
    Create a web UI compatible agent adapter.
    
    Args:
        agent: The original DeepSearchAgent instance
        session_id: Optional session ID
        event_callback: Optional callback for events
        
    Returns:
        WebUIAdapter: The adapted agent instance
    """
    return WebUIAdapter(
        agent,
        session_id=session_id,
        event_callback=event_callback
    )