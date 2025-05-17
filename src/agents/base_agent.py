#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/base_agent.py
# code style: PEP 8

"""
Base Agent class for DeepSearchAgents
"""

from typing import (
    Dict, Any, List, Literal, Generator, Union
)

from smolagents import Tool, LiteLLMModel
from smolagents.models import ChatMessage, ChatMessageStreamDelta

import logging

logger = logging.getLogger(__name__)


class MultiModelRouter:
    """Router to use different models based on template context

    This wrapper presents a single model interface to smolagents
    but internally routes to different models based on the prompt
    being processed.
    """

    def __init__(self, search_model, orchestrator_model):
        """Initialize the model router

        Args:
            search_model: Model for general code generation and search
            orchestrator_model: Model for planning and final answers
        """
        self.search_model = search_model
        self.orchestrator_model = orchestrator_model
        self.model_id = (
            f"{orchestrator_model.model_id}+{search_model.model_id}"
        )
        # add token count attributes, default to 0
        self.last_input_token_count = 0
        self.last_output_token_count = 0
        # current used model, for token count retrieval
        self._last_used_model = None

    def __call__(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> ChatMessage:
        """Route model calls based on message content

        Args:
            messages: List of messages to process
            **kwargs: Additional parameters for the model

        Returns:
            ChatMessage: Response from the appropriate model
        """
        # Detect if this is a planning-related call
        is_planning = False
        is_final_answer = False

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        if (
                            "Facts survey" in text
                            or "Updated facts survey" in text
                            or "facts survey" in text.lower()
                            or "plan" in text.lower()
                        ):
                            is_planning = True
                        elif (
                            "final answer to the original question" in text
                            or "final answer" in text.lower()
                        ):
                            is_final_answer = True
            elif isinstance(content, str):
                if (
                    "Facts survey" in content
                    or "Updated facts survey" in content
                    or "facts survey" in content.lower()
                    or "plan" in content.lower()
                ):
                    is_planning = True
                elif (
                    "final answer to the original question" in content
                    or "final answer" in content.lower()
                ):
                    is_final_answer = True

        # Use orchestrator model for planning and final answers
        if is_planning or is_final_answer:
            self._last_used_model = self.orchestrator_model
            result = self.orchestrator_model(messages, **kwargs)
        else:
            # Use search model for everything else
            self._last_used_model = self.search_model
            result = self.search_model(messages, **kwargs)

        # update token count information
        if hasattr(self._last_used_model, "last_input_token_count"):
            self.last_input_token_count = (
                self._last_used_model.last_input_token_count
            )
            self.last_output_token_count = (
                self._last_used_model.last_output_token_count
            )

        return result

    def get_token_counts(self):
        """Get token count information

        Returns:
            Dict: Contains input and output token counts
        """
        return {
            "input": self.last_input_token_count,
            "output": self.last_output_token_count
        }

    def generate(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> ChatMessage:
        """Implement generate method to support smolagents API

        Args:
            messages: List of messages to process
            **kwargs: Additional parameters for the model

        Returns:
            ChatMessage: Response from the appropriate model
        """
        return self.__call__(messages, **kwargs)

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> Generator[ChatMessageStreamDelta, None, None]:
        """Stream generation results

        Args:
            messages: List of messages to process
            **kwargs: Additional parameters for the model

        Returns:
            Generator yielding message chunks
        """
        is_planning = False
        is_final_answer = False

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        if (
                            "Facts survey" in text
                            or "Updated facts survey" in text
                            or "facts survey" in text.lower()
                            or "plan" in text.lower()
                        ):
                            is_planning = True
                        elif (
                            "final answer to the original question" in text
                            or "final answer" in text.lower()
                        ):
                            is_final_answer = True
            elif isinstance(content, str):
                if (
                    "Facts survey" in content
                    or "Updated facts survey" in content
                    or "facts survey" in content.lower()
                    or "plan" in text.lower()
                ):
                    is_planning = True
                elif (
                    "final answer to the original question" in content
                    or "final answer" in content.lower()
                ):
                    is_final_answer = True

        active_model_for_stream = None
        if is_planning or is_final_answer:
            self._last_used_model = self.orchestrator_model
            active_model_for_stream = self.orchestrator_model
        else:
            self._last_used_model = self.search_model
            active_model_for_stream = self.search_model

        try:
            if hasattr(active_model_for_stream, 'generate_stream'):
                model_kwargs = kwargs.copy()
                if (hasattr(active_model_for_stream, 'api_key') and
                        active_model_for_stream.api_key):
                    model_kwargs['api_key'] = active_model_for_stream.api_key
                if (hasattr(active_model_for_stream, 'api_base') and
                        active_model_for_stream.api_base):
                    model_kwargs['api_base'] = active_model_for_stream.api_base

                # Yield all deltas from the underlying model's stream
                # This loop must complete for token counts to be updated
                # from the underlying model
                stream_generator = (
                    active_model_for_stream.generate_stream(
                        messages, **model_kwargs
                    )
                )
                for delta in stream_generator:
                    if delta.content is None:
                        yield ChatMessageStreamDelta(content="")
                    else:
                        yield delta

                # After the stream is exhausted, update self's token counts
                if hasattr(self._last_used_model, "last_input_token_count"):
                    self.last_input_token_count = (
                        self._last_used_model.last_input_token_count
                    )
                if hasattr(self._last_used_model, "last_output_token_count"):
                    self.last_output_token_count = (
                        self._last_used_model.last_output_token_count
                    )
            else:
                # Fallback if no stream method on the active model
                response = active_model_for_stream(messages, **kwargs)
                # Update token counts even in non-streaming fallback
                if hasattr(self._last_used_model, "last_input_token_count"):
                    self.last_input_token_count = (
                        self._last_used_model.last_input_token_count
                    )
                if hasattr(self._last_used_model, "last_output_token_count"):
                    self.last_output_token_count = (
                        self._last_used_model.last_output_token_count
                    )
                yield ChatMessageStreamDelta(
                    content=response.content or ""
                )
        except Exception as e:
            import traceback
            error_msg = (
                f"Error in streaming generation: {str(e)}\\\\n"
                f"{traceback.format_exc()}"
            )
            logging.error(error_msg)
            yield ChatMessageStreamDelta(content=f"Error: {str(e)}")


class BaseAgent:
    """Base class for DeepSearchAgent, providing shared functionality
    for React and CodeAct agents"""

    def __init__(
        self,
        agent_type: Literal["react", "codact"],
        orchestrator_model: LiteLLMModel,
        search_model: LiteLLMModel,
        # Tools and state - managed by runtime
        tools: List[Tool],
        initial_state: Dict[str, Any],
        # Basic configuration
        max_steps: int = 25,
        planning_interval: int = 5,
        enable_streaming: bool = False,
        # Additional options
        cli_console=None,
        **kwargs
    ):
        """Initialize the base agent

        Args:
            agent_type: Type of agent ("react" or "codact")
            orchestrator_model: Pre-configured LLM model for orchestrator
            search_model: Pre-configured LLM model for search
            tools: Pre-initialized list of tools from runtime
            initial_state: Initial agent state from runtime
            max_steps: Maximum number of execution steps
            planning_interval: Interval for planning steps
            enable_streaming: Whether to enable streaming output
            cli_console: CLI console object
            **kwargs: Additional parameters
        """
        # Basic configuration
        self.agent_type = agent_type
        self.orchestrator_model = orchestrator_model
        self.search_model = search_model
        self.max_steps = max_steps
        self.planning_interval = planning_interval
        self.enable_streaming = enable_streaming

        # Additional options
        self.cli_console = cli_console
        self.kwargs = kwargs

        # Tools and state from runtime
        self.tools = tools
        self.initial_state = initial_state
        self.agent = None

        # no longer call create_agent in __init__
        # instead, call it explicitly after subclass initialization

    def initialize(self):
        """Explicit initialization method, create agent instance
        call it after subclass initialization"""
        self.agent = self.create_agent()
        return self

    def create_agent(self):
        """Create agent instance (to be implemented by subclasses)"""
        raise NotImplementedError(
            "Subclasses must implement create_agent method"
        )

    def run(
        self,
        user_input: str,
        stream: bool = False,
        images: List = None,  # Add images parameter for compatibility
        reset: bool = True,   # Add reset parameter for compatibility
        additional_args: Dict[str, Any] = None,  # additional_args parameter
        **kwargs
    ) -> Union[str, Generator]:
        """Run agent to process user input

        Args:
            user_input: User input
            stream: Whether to enable streaming output
            images: Optional list of images (for compatibility with
            stream_to_gradio)
            reset: Whether to reset agent state
            additional_args: Additional arguments for the agent
            **kwargs: Additional keyword arguments

        Returns:
            str: Agent response or generator for streaming
        """
        if self.agent is None:
            error_msg = (
                f"Error: {self.agent_type} agent initialization failed"
            )
            return error_msg

        # Enable streaming if requested
        if stream:
            self.enable_streaming = True
            if hasattr(self.agent, 'stream_outputs'):
                self.agent.stream_outputs = True

            # Prepare run parameters
            run_kwargs = {'stream': True}

            # Only add parameters that are supported by the agent.run method
            import inspect
            run_params = inspect.signature(self.agent.run).parameters

            if 'reset' in run_params:
                run_kwargs['reset'] = reset

            if 'images' in run_params and images is not None:
                run_kwargs['images'] = images

            if 'additional_args' in run_params and additional_args is not None:
                run_kwargs['additional_args'] = additional_args

            # Return a generator for streaming
            return self.agent.run(user_input, **run_kwargs)

        # Default non-streaming mode
        return self.agent.run(user_input)
