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
import time
import sys
import io
from contextlib import contextmanager

from smolagents import Tool, LiteLLMModel, TokenUsage
from smolagents.models import ChatMessage, ChatMessageStreamDelta

from .run_result import RunResult
from .stream_aggregator import StreamAggregator, ModelStreamWrapper
import logging

logger = logging.getLogger(__name__)


@contextmanager
def suppress_output():
    """Context manager to suppress stdout during streaming"""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old_stdout


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
        # Use helper method to select model
        active_model = self._select_model_for_messages(messages)

        # Call the selected model
        result = active_model(messages, **kwargs)

        # Update token counts
        self._update_token_counts_from_model(active_model)

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
        """Stream generation results using StreamAggregator (v1.19.0 pattern)

        Args:
            messages: List of messages to process
            **kwargs: Additional parameters for the model

        Returns:
            Generator yielding message chunks
        """
        # Determine which model to use
        active_model = self._select_model_for_messages(messages)

        # Create stream wrapper with aggregator
        stream_wrapper = ModelStreamWrapper(active_model)

        try:
            # Use the wrapper to handle streaming with aggregation
            for delta in stream_wrapper.generate_stream(messages, **kwargs):
                yield delta

            # Update token counts after streaming completes
            self._update_token_counts_from_model(active_model)

        except Exception as e:
            import traceback
            error_msg = (
                f"Error in streaming generation: {str(e)}\\n"
                f"{traceback.format_exc()}"
            )
            logging.error(error_msg)
            yield ChatMessageStreamDelta(content=f"Error: {str(e)}")

    def _select_model_for_messages(
        self,
        messages: List[Union[Dict[str, Any], ChatMessage]]
    ) -> Any:
        """Select appropriate model based on message content

        Args:
            messages: List of messages to analyze

        Returns:
            Selected model (orchestrator or search)
        """
        is_planning = False
        is_final_answer = False

        for msg in messages:
            # Handle both dict and ChatMessage objects
            if hasattr(msg, 'content'):
                # ChatMessage object
                content = msg.content or ""
            else:
                # Dictionary message
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

        # Select model based on content
        if is_planning or is_final_answer:
            self._last_used_model = self.orchestrator_model
            return self.orchestrator_model
        else:
            self._last_used_model = self.search_model
            return self.search_model

    def _update_token_counts_from_model(self, model):
        """Update token counts from the model after generation

        Args:
            model: The model that was used for generation
        """
        if hasattr(model, "last_input_token_count"):
            self.last_input_token_count = model.last_input_token_count
        if hasattr(model, "last_output_token_count"):
            self.last_output_token_count = model.last_output_token_count


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
        # Managed agents support
        name: str = None,
        description: str = None,
        managed_agents: List['BaseAgent'] = None,
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
            name: Agent name for identification in hierarchical systems
            description: Agent description for manager agents
            managed_agents: List of sub-agents this agent can manage
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

        # Managed agents support
        self.name = name or f"DeepSearch {agent_type.title()} Agent"
        self.description = description or (
            f"Agent that uses {agent_type} architecture for deep search tasks"
        )
        self.managed_agents = managed_agents or []

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
        return_result: bool = False,  # New parameter for RunResult
        **kwargs
    ) -> Union[str, Generator, RunResult]:
        """Run agent to process user input

        Args:
            user_input: User input
            stream: Whether to enable streaming output
            images: Optional list of images (for compatibility with
            stream_to_gradio)
            reset: Whether to reset agent state
            additional_args: Additional arguments for the agent
            return_result: Whether to return RunResult object (v1.19.0 feature)
            **kwargs: Additional keyword arguments

        Returns:
            str: Agent response (backward compatibility)
            Generator: For streaming responses
            RunResult: When return_result=True (new v1.19.0 feature)
        """
        # Reset memory if requested
        if reset and not stream:
            self.reset_agent_memory()
        if self.agent is None:
            error_msg = (
                f"Error: {self.agent_type} agent initialization failed"
            )
            if return_result:
                return RunResult(
                    final_answer=error_msg,
                    error=error_msg,
                    agent_type=self.agent_type
                )
            return error_msg

        # Track execution time
        start_time = time.time()

        # Enable streaming if requested
        if stream:
            self.enable_streaming = True
            if hasattr(self.agent, 'stream_outputs'):
                self.agent.stream_outputs = True
                
            # Temporarily reduce verbosity during streaming
            original_verbosity = None
            if hasattr(self.agent, 'verbosity_level'):
                original_verbosity = self.agent.verbosity_level
                self.agent.verbosity_level = 0

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

            # Return a generator for streaming (no RunResult for streaming)
            # The verbosity reduction should help minimize console output
            return self.agent.run(user_input, **run_kwargs)

        # Default non-streaming mode
        try:
            result = self.agent.run(user_input)

            # Handle JSON response from final_answer tool
            if isinstance(result, dict) and "content" in result:
                # Extract content from JSON response
                result = result["content"]
            elif isinstance(result, str) and result.strip().startswith('{'):
                # Try to parse JSON string
                try:
                    import json
                    answer_dict = json.loads(result)
                    if isinstance(answer_dict, dict) and "content" in answer_dict:
                        result = answer_dict["content"]
                except json.JSONDecodeError:
                    pass

            # If not returning RunResult, just return the string
            if not return_result:
                return result

            # Create RunResult object
            execution_time = time.time() - start_time

            # Collect token usage from model router
            token_usage = None
            if hasattr(self, 'orchestrator_model') and isinstance(
                self.orchestrator_model, MultiModelRouter
            ):
                router_tokens = self.orchestrator_model.get_token_counts()
                input_tokens = router_tokens.get("input", 0)
                output_tokens = router_tokens.get("output", 0)
                token_usage = TokenUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

            # Collect model info
            model_info = {}
            if hasattr(self, 'orchestrator_model'):
                if hasattr(self.orchestrator_model, 'model_id'):
                    model_info["orchestrator"] = self.orchestrator_model.model_id
            if hasattr(self, 'search_model'):
                if hasattr(self.search_model, 'model_id'):
                    model_info["search"] = self.search_model.model_id

            # Create and return RunResult
            run_result = RunResult(
                final_answer=result,
                execution_time=execution_time,
                token_usage=token_usage,
                agent_type=self.agent_type,
                model_info=model_info
            )

            # Try to collect steps if available
            if hasattr(self.agent, 'logs') and self.agent.logs:
                for log_entry in self.agent.logs:
                    step_info = {
                        "type": getattr(log_entry, 'type', 'unknown'),
                        "content": str(log_entry)
                    }
                    run_result.add_step(step_info)

            return run_result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Agent execution failed: {str(e)}"

            if return_result:
                return RunResult(
                    final_answer="",
                    error=error_msg,
                    execution_time=execution_time,
                    agent_type=self.agent_type
                )
            else:
                raise

    def __call__(self, task: str, additional_args: Dict[str, Any] = None) -> str:
        """Make agent callable as a tool by manager agents

        This allows hierarchical agent architectures where manager agents
        can call sub-agents just like they call tools.

        Args:
            task: The task/query to execute
            additional_args: Optional additional arguments

        Returns:
            str: The agent's response/final answer
        """
        try:
            # Run the agent with the task
            result = self.run(
                user_input=task,
                stream=False,
                additional_args=additional_args,
                return_result=True
            )

            # Extract final answer from RunResult
            if isinstance(result, RunResult):
                if result.error:
                    agent_name = self.name or self.agent_type
                    return f"Error executing sub-agent {agent_name}: {result.error}"
                return result.final_answer or "No answer generated"
            else:
                # Direct string result
                return str(result)

        except Exception as e:
            agent_name = self.name or self.agent_type
            logger.error(f"Error in managed agent {agent_name}: {str(e)}")
            return f"Error: Failed to execute sub-agent {agent_name}: {str(e)}"

    def __enter__(self):
        """Context manager entry for resource initialization"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit for resource cleanup

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred

        Returns:
            False to propagate any exceptions
        """
        # Clean up agent resources
        if hasattr(self, 'agent') and self.agent:
            # Memory cleanup is handled internally by smolagents in v1.19.0
            # No need to manually reset it

            # Clean up any tool resources
            if hasattr(self.agent, 'tools') and self.agent.tools:
                for tool in self.agent.tools:
                    if hasattr(tool, 'cleanup') and callable(tool.cleanup):
                        try:
                            tool.cleanup()
                        except Exception as e:
                            logger.warning(
                                f"Error cleaning up tool {tool.name}: {e}"
                            )

            # Clean up any executor resources (for CodeAct)
            if hasattr(self.agent, 'executor') and hasattr(
                self.agent.executor, 'close'
            ):
                try:
                    self.agent.executor.close()
                except Exception as e:
                    logger.warning(f"Error closing executor: {e}")

        # Clear model references to free memory
        self.orchestrator_model = None
        self.search_model = None

        return False  # Don't suppress exceptions

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit for resource cleanup

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred

        Returns:
            False to propagate any exceptions
        """
        # Use sync cleanup for now
        return self.__exit__(exc_type, exc_val, exc_tb)

    def reset_agent_memory(self):
        """Reset agent memory and state

        Clears agent memory while preserving tools and configuration.
        This is useful for starting fresh conversations without recreating
        the entire agent instance.
        """
        if hasattr(self, 'agent') and self.agent:
            # In smolagents v1.19.0, memory is a proper object, not a list
            # Use the reset() method if available
            if hasattr(self.agent, 'memory') and hasattr(self.agent.memory, 'reset'):
                self.agent.memory.reset()
                logger.debug(f"Reset memory for {self.agent_type} agent")
            elif hasattr(self.agent, 'reset'):
                # Some agents might have a reset method
                self.agent.reset()
                logger.debug(f"Reset {self.agent_type} agent using reset method")

            # Logs are now read-only in v1.19.0, handled via memory.steps
            # No need to manually reset logs

            # Reset agent state to initial state
            if hasattr(self.agent, 'state') and hasattr(self, 'initial_state'):
                # Create a fresh copy of initial state
                import copy
                self.agent.state = copy.deepcopy(self.initial_state)
                logger.debug("Reset agent state to initial state")
        else:
            logger.warning(
                f"Cannot reset memory - {self.agent_type} agent not initialized"
            )

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of the current agent memory state

        Returns:
            Dict containing memory statistics and content summary
        """
        summary = {
            "agent_type": self.agent_type,
            "memory_length": 0,
            "logs_length": 0,
            "has_planning_memory": False,
            "state_keys": []
        }

        if hasattr(self, 'agent') and self.agent:
            if hasattr(self.agent, 'memory'):
                summary["memory_length"] = len(self.agent.memory)

            if hasattr(self.agent, 'logs'):
                summary["logs_length"] = len(self.agent.logs)

            if hasattr(self.agent, 'planning_memory'):
                summary["has_planning_memory"] = True
                summary["planning_memory_length"] = len(
                    self.agent.planning_memory
                )

            if hasattr(self.agent, 'state') and isinstance(
                self.agent.state, dict
            ):
                summary["state_keys"] = list(self.agent.state.keys())

        return summary

    def optimize_memory_for_planning(self):
        """Optimize memory specifically for planning steps

        This method helps manage memory during planning intervals by:
        - Keeping only essential memory items
        - Summarizing previous steps
        - Preserving critical findings
        """
        if not hasattr(self, 'agent') or not self.agent:
            return

        # Keep the last N memory items for context
        MEMORY_WINDOW = 10

        if hasattr(self.agent, 'memory') and len(self.agent.memory) > MEMORY_WINDOW:
            # Keep recent memory items
            self.agent.memory = self.agent.memory[-MEMORY_WINDOW:]
            logger.debug(
                f"Optimized memory for planning - kept last {MEMORY_WINDOW} items"
            )
