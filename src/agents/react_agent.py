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
        planning_interval: int = 7,
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
            cli_console: CLI console object
            **kwargs: Additional parameters for future extensions
        """
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

        # Set up the agent
        agent = ToolCallingAgent(
            model=model_router,
            tools=self.tools,
            prompt_templates=REACT_PROMPT,
            max_steps=self.max_steps,
            stream_outputs=self.enable_streaming,
            planning_interval=self.planning_interval,
            # Pass initial state
            state=self.initial_state,
            # Pass step callbacks
            step_callbacks=self.kwargs.get("step_callbacks", []),
        )

        return agent
