#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/ui_common/gradio_adapter.py
# code style: PEP 8

"""
Adapter class to ensure DeepSearchAgent is fully compatible with
smolagents.GradioUI
"""

import asyncio
import logging
from typing import Any, Dict, Generator, List, Optional, Union

logger = logging.getLogger(__name__)


class GradioUIAdapter:
    """
    Adapter class to ensure DeepSearchAgent is fully compatible with
    smolagents.GradioUI

    Wrap our custom Agent in the interface format expected by
    smolagents.GradioUI, mainly handling:
    1. Ensure the agent has name and description properties
    2. Adapt the run method's parameters and return format
    3. Provide other methods expected by GradioUI
    """

    def __init__(
        self,
        agent,
        name=None,
        description=None,
        enable_token_counting=True
    ):
        """
        Initialize the adapter

        Args:
            agent: The original DeepSearchAgent instance
            name: Optional agent name
            description: Optional agent description
            enable_token_counting: Whether to enable token counting
        """
        self.agent = agent
        self._name = name
        self._description = description
        self._enable_token_counting = enable_token_counting

        # Expose tools for smolagents.GradioUI
        self.tools = getattr(agent, 'tools', [])

        # Set other necessary properties for compatibility
        self.step_callbacks = getattr(agent, 'step_callbacks', [])
        self.memory = getattr(agent, 'memory', None)

        # Create reference to model for token counting
        if hasattr(agent, 'model'):
            self.model = agent.model
        elif hasattr(agent, 'agent') and hasattr(agent.agent, 'model'):
            self.model = agent.agent.model
        else:
            self.model = None
            logger.warning("No model found in agent for token counting")

    @property
    def name(self) -> str:
        """Get agent name"""
        if self._name:
            return self._name
        return getattr(
            self.agent, 'name',
            "DeepSearch Agent"
        )

    @property
    def description(self) -> str:
        """Get agent description"""
        if self._description:
            return self._description
        return getattr(
            self.agent, 'description',
            "DeepSearchAgent combines advanced web search, "
            "content processing, and reasoning abilities."
        )

    def _sync_run_stream(self, task, **kwargs):
        """Synchronously run streaming output, ensuring return format
        compatible with smolagents.gradio_ui.stream_to_gradio

        Args:
            task: User task/query
            **kwargs: Additional parameters

        Returns:
            Generator: Returns a generator compatible with stream_to_gradio
        """
        # Import stream_to_gradio function
        try:
            from smolagents.gradio_ui import stream_to_gradio
        except ImportError:
            logger.error(
                "Failed to import stream_to_gradio from smolagents.gradio_ui"
            )

            def error_gen():
                yield {
                    "role": "assistant",
                    "content": "Error: Failed to import stream_to_gradio"
                }
            return error_gen()

        # Find model in different possible locations
        model = None
        if hasattr(self.agent, 'model'):
            model = self.agent.model
        elif (hasattr(self.agent, 'agent') and
                hasattr(self.agent.agent, 'model')):
            model = self.agent.agent.model

        if not model:
            logger.warning("Model not found, streaming may not work")

            def error_gen():
                yield {
                    "role": "assistant",
                    "content": "Error: Current model does not support "
                    "streaming output. Please use a model that supports "
                    "streaming."
                }
            return error_gen()

        if not hasattr(model, 'generate_stream'):
            logger.warning("Model does not support streaming")

            def error_gen():
                yield {
                    "role": "assistant",
                    "content": "Error: Current model does not support "
                    "streaming output. Please use a model that supports "
                    "streaming."
                }
            return error_gen()

        # Try to use stream_to_gradio
        try:
            # Fix for CodeActAgent: Add model attribute if missing
            # This is needed for token counting in stream_to_gradio
            original_model = None
            if not hasattr(self.agent, 'model'):
                # Try to find model in different locations
                if (hasattr(self.agent, 'agent') and
                        hasattr(self.agent.agent, 'model')):
                    original_model = True  # Remember we didn't have model
                    self.agent.model = self.agent.agent.model
                    logger.debug(
                        "Added model attribute to agent for stream_to_gradio"
                    )

            # Check if our agent.run supports 'images' parameter
            import inspect
            run_params = inspect.signature(self.agent.run).parameters
            stream_to_gradio_kwargs = {
                'task': task,
                'reset_agent_memory': kwargs.get('reset', False)
            }

            # Only add images parameter if agent.run supports it
            if 'images' in run_params:
                stream_to_gradio_kwargs['task_images'] = None

            # Create a wrapper generator that will clean up after iteration
            def wrapper_generator():
                try:
                    # Get the original generator
                    generator = stream_to_gradio(
                        self.agent,
                        **stream_to_gradio_kwargs
                    )

                    # Yield from the generator
                    for item in generator:
                        yield item
                finally:
                    # Clean up after the generator is exhausted
                    if original_model:
                        if hasattr(self.agent, 'model'):
                            delattr(self.agent, 'model')
                            logger.debug(
                                "Removed temporary model attribute from agent"
                            )

            # Return the wrapper generator
            return wrapper_generator()

        except Exception as error:
            logger.error(f"Error in stream_to_gradio: {error}", exc_info=True)

            def error_gen(error=error):
                yield {
                    "role": "assistant",
                    "content": f"Error: {str(error)}"
                }
            return error_gen()

    def run(
        self,
        task: str,
        stream: bool = False,
        reset: bool = True,
        images: Optional[List[Any]] = None,
        additional_args: Optional[Dict[str, Any]] = None,
        max_steps: Optional[int] = None,
    ) -> Union[str, Generator[Any, None, None]]:
        """
        Run the agent to process the task, compatible with
        smolagents.MultiStepAgent.run interface

        Args:
            task: Task description or user query
            stream: Whether to stream output
            reset: Whether to reset the session
            images: Optional list of images
            additional_args: Additional arguments
            max_steps: Maximum number of steps

        Returns:
            Agent execution result or stream
        """
        # Log the task for debugging
        logger.info(f"Running agent with task: {task[:50]}...")

        # Check if agent needs max_steps configuration
        if max_steps is not None and hasattr(self.agent, 'max_steps'):
            self.agent.max_steps = max_steps

        # Handle streaming output
        if stream:
            # Ensure agent has memory for streaming
            if not hasattr(self.agent, 'memory'):
                self.agent.memory = []

            # Set streaming flag if agent supports it
            if hasattr(self.agent, 'stream_outputs'):
                self.agent.stream_outputs = True

            # Use _sync_run_stream to handle both async and sync cases
            return self._sync_run_stream(task, reset=reset)

        # Non-streaming mode
        # Create and manage event loop for async execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Async execution - only pass parameters BaseAgent.run supports
            if asyncio.iscoroutinefunction(self.agent.run):
                result = loop.run_until_complete(
                    self.agent.run(task, stream=False)
                )
            else:
                result = self.agent.run(task, stream=False)

            return result
        finally:
            loop.close()

    def _run_stream(
        self,
        task: str,
        **kwargs
    ) -> Generator[Any, None, None]:
        """
        Simulate streaming output interface

        Args:
            task: Task description
            **kwargs: Additional parameters

        Returns:
            Generator that yields streaming content
        """
        # Note: DeepSearchAgent streaming is not fully implemented
        # This is a placeholder for GradioUI compatibility
        logger.warning("Streaming requested but not fully implemented")
        yield from []

    def write_memory_to_messages(
        self,
        *args,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Convert agent memory to message format

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Returns:
            List of formatted messages for Gradio UI
        """
        if hasattr(self.agent, 'write_memory_to_messages'):
            return self.agent.write_memory_to_messages(*args, **kwargs)

        # Default implementation if agent doesn't have this method
        if hasattr(self.agent, 'memory') and self.agent.memory:
            # Convert memory to messages format using a simplified approach
            messages = []
            for step in self.agent.memory:
                if hasattr(step, 'content'):
                    messages.append({
                        "role": "assistant",
                        "content": step.content
                    })
                elif hasattr(step, 'task'):
                    messages.append({
                        "role": "user",
                        "content": step.task
                    })
            return messages

        return []

    def visualize(self) -> None:
        """Visualize agent structure"""
        if hasattr(self.agent, 'visualize'):
            self.agent.visualize()

    def replay(self, detailed: bool = False) -> None:
        """Replay agent execution steps"""
        if hasattr(self.agent, 'replay'):
            self.agent.replay(detailed=detailed)

    def __call__(self, task: str, **kwargs) -> Any:
        """Call the agent to process the task"""
        if hasattr(self.agent, '__call__'):
            return self.agent(task, **kwargs)
        return asyncio.run(self.run(task, **kwargs))

    def get_token_counts(self) -> Dict[str, int]:
        """
        Get token usage information

        Returns:
            Dict with token count information
        """
        if not self._enable_token_counting:
            return {"input": 0, "output": 0}

        # Try different ways to get token information
        if self.model:
            # Method 1: Use get_token_counts method
            if hasattr(self.model, "get_token_counts"):
                try:
                    return self.model.get_token_counts()
                except Exception as e:
                    logger.debug(f"Error getting token counts: {e}")

            # Method 2: Access direct attributes
            if hasattr(self.model, "last_input_token_count"):
                return {
                    "input": getattr(self.model, "last_input_token_count", 0),
                    "output": getattr(self.model, "last_output_token_count", 0)
                }

        # Try to get from agent.agent.model
        if hasattr(self.agent, 'agent') and hasattr(self.agent.agent, 'model'):
            model = self.agent.agent.model
            if hasattr(model, "get_token_counts"):
                try:
                    return model.get_token_counts()
                except Exception:
                    pass

            if hasattr(model, "last_input_token_count"):
                return {
                    "input": getattr(model, "last_input_token_count", 0),
                    "output": getattr(model, "last_output_token_count", 0)
                }

        # Default empty counts
        return {"input": 0, "output": 0}


def create_gradio_compatible_agent(agent, name=None, description=None):
    """
    Create a GradioUI compatible agent adapter

    Args:
        agent: The original DeepSearchAgent instance
        name: Optional agent name
        description: Optional agent description

    Returns:
        GradioUIAdapter: The adapted agent instance
    """
    return GradioUIAdapter(agent, name=name, description=description)
