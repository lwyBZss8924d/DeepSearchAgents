#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/react_agent.py
# code style: PEP 8

"""
ReAct agent implementation, uses reasoning and tool calling paradigm
for deep search task
"""

import logging
from typing import Dict, Any, List
from smolagents import ToolCallingAgent, Tool
from .prompt_templates import REACT_PROMPT
from .base_agent import BaseAgent, MultiModelRouter


logger = logging.getLogger(__name__)


class DebuggingToolCallingAgent(ToolCallingAgent):
    """Custom ToolCallingAgent with debugging and validation"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._empty_answer_count = 0
        self._max_empty_retries = 2
        self._last_model_output = None

    def execute_tool_call(self, tool_name: str, arguments: dict | str) -> Any:
        """Override to add validation and retry logic for empty final_answer"""

        # Special handling for final_answer tool
        if tool_name == "final_answer":
            # Check if arguments is empty or has empty answer
            if isinstance(arguments, dict):
                answer_content = arguments.get("answer", {})
                if not answer_content or answer_content == {}:
                    self._empty_answer_count += 1
                    logger.error(
                        f"Empty final_answer detected (attempt "
                        f"{self._empty_answer_count}/{self._max_empty_retries})"
                        f"\nArguments received: {arguments}"
                        f"\nLast model output: {self._last_model_output}"
                        f"\nStep number: {getattr(self, 'step_number', 'unknown')}"
                        f"\nPlanning interval: {getattr(self, 'planning_interval', 'unknown')}"
                    )

                    # Check if this is happening at a planning step
                    step_num = getattr(self, 'step_number', 0)
                    planning_int = getattr(self, 'planning_interval', 0)
                    if planning_int and step_num > 1 and (step_num - 1) % planning_int == 0:
                        logger.warning(
                            "Empty final_answer occurred at a planning step. "
                            "This suggests the model may be confused about when to plan vs act."
                        )

                    if self._empty_answer_count <= self._max_empty_retries:
                        # Instead of executing the tool, return an error message
                        # that will be fed back to the model
                        error_msg = (
                            "ERROR: Your final_answer was empty. This is not allowed.\n\n"
                            "IMPORTANT: You should only call final_answer when you have:\n"
                            "1. Gathered sufficient information\n"
                            "2. Synthesized a comprehensive answer\n"
                            "3. Have source URLs to cite\n\n"
                            "The correct format is:\n"
                            "{\n"
                            '  "title": "Your Answer Title",\n'
                            '  "content": "Your comprehensive answer with details",\n'
                            '  "sources": ["url1", "url2"]\n'
                            "}\n\n"
                            "Continue with your research or provide a complete answer."
                        )
                        return error_msg
                else:
                    # Reset counter on successful final_answer
                    self._empty_answer_count = 0

        # Call parent implementation
        return super().execute_tool_call(tool_name, arguments)

    def _step_stream(self, memory_step):
        """Override to capture model outputs for debugging"""
        # Store the current step for debugging
        try:
            if hasattr(self, 'memory') and hasattr(self.memory, 'steps'):
                # Access steps from AgentMemory object
                if self.memory.steps:
                    last_step = self.memory.steps[-1]
                    # Try different attributes that might contain the output
                    if hasattr(last_step, 'llm_output'):
                        self._last_model_output = last_step.llm_output
                    elif hasattr(last_step, 'content'):
                        self._last_model_output = last_step.content
                    elif hasattr(last_step, 'agent_output'):
                        self._last_model_output = last_step.agent_output
        except Exception as e:
            logger.debug(f"Could not capture model output: {e}")

        # Call parent implementation
        yield from super()._step_stream(memory_step)


class ReactAgent(BaseAgent):
    """React agent implementation, uses reasoning and tool calling paradigm"""

    def __init__(
        self,
        orchestrator_model,
        search_model,
        tools: List[Tool],
        initial_state: Dict[str, Any],
        enable_streaming: bool = False,
        max_steps: int = 25,
        planning_interval: int = 3,
        max_tool_threads: int = 4,
        name: str = None,
        description: str = None,
        managed_agents: List['BaseAgent'] = None,
        cli_console=None,
        **kwargs
    ):
        """Initialize React agent

        Args:
            orchestrator_model: Model for planning and final answer
            search_model: Model for general code generation and search
            tools: Pre-initialized list of tools from runtime
            initial_state: Initial agent state from runtime
            enable_streaming: Whether to enable streaming output
            max_steps: Maximum number of execution steps
            planning_interval: Interval for planning steps
            max_tool_threads: Maximum threads for parallel tool execution
            name: Agent name for identification in hierarchical systems
            description: Agent description for manager agents
            managed_agents: List of sub-agents this agent can manage
            cli_console: CLI console object
            **kwargs: Additional parameters for future extensions
        """
        self.max_tool_threads = max_tool_threads
        # Call parent class initialization
        super().__init__(
            agent_type="react",
            orchestrator_model=orchestrator_model,
            search_model=search_model,
            tools=tools,
            initial_state=initial_state,
            enable_streaming=enable_streaming,
            max_steps=max_steps,
            planning_interval=planning_interval,
            name=name,
            description=description,
            managed_agents=managed_agents,
            cli_console=cli_console,
            **kwargs
        )

        # initialize agent
        self.initialize()

    def create_agent(self):
        """Create a ReAct agent instance

        Returns:
            ToolCallingAgent: Initialized agent
        """
        # Create model router for multi-model support
        model_router = MultiModelRouter(
            self.search_model,
            self.orchestrator_model
        )

        # Log configuration for debugging
        logger.debug(f"Creating ReAct agent with planning_interval={self.planning_interval}")
        logger.debug(f"Max steps: {self.max_steps}, Streaming: {self.enable_streaming}")

        # Set up the agent with debugging wrapper
        agent = DebuggingToolCallingAgent(
            model=model_router,
            tools=self.tools,
            prompt_templates=REACT_PROMPT,
            max_steps=self.max_steps,
            stream_outputs=self.enable_streaming,
            planning_interval=self.planning_interval,
            # Pass step callbacks if provided
            step_callbacks=self.step_callbacks,
            # Enable parallel tool execution
            max_tool_threads=self.max_tool_threads,
        )

        # Set initial state after creation
        if self.initial_state:
            agent.state = self.initial_state

        return agent
