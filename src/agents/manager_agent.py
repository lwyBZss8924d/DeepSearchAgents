#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/manager_agent.py
# code style: PEP 8

"""
Manager Agent implementation for hierarchical agent orchestration
"""

import logging
from typing import Dict, Any, List, Optional, Union
from smolagents import Tool
from .base_agent import BaseAgent
from .codact_agent import CodeActAgent

logger = logging.getLogger(__name__)


class ManagerAgent(CodeActAgent):
    """Manager agent that orchestrates other agents in a hierarchical manner

    The ManagerAgent extends CodeAgent to dynamically orchestrate sub-agents
    through code execution. This enables sophisticated multi-agent architectures
    where the LLM writes Python code to analyze tasks, check results, and
    intelligently delegate to the most appropriate sub-agents.
    """

    def __init__(
        self,
        orchestrator_model,
        search_model,
        tools: List[Tool],
        initial_state: Dict[str, Any],
        managed_agents: List[BaseAgent],
        enable_streaming: bool = False,
        max_steps: int = 30,
        planning_interval: int = 10,
        executor_type: str = "local",
        executor_kwargs: Optional[Dict[str, Any]] = None,
        verbosity_level: int = 2,
        additional_authorized_imports: Optional[List[str]] = None,
        use_structured_outputs_internally: bool = False,
        max_delegation_depth: int = 3,
        name: str = None,
        description: str = None,
        cli_console=None,
        **kwargs
    ):
        """Initialize Manager Agent

        Args:
            orchestrator_model: Model for planning and orchestration
            search_model: Model for general operations
            tools: List of traditional tools (usually empty for manager)
            initial_state: Initial agent state
            managed_agents: List of agents to manage and orchestrate
            enable_streaming: Whether to enable streaming output
            max_steps: Maximum number of execution steps
            planning_interval: Interval for planning steps
            executor_type: Type of code executor to use
            executor_kwargs: Additional executor configuration
            verbosity_level: Level of output verbosity
            additional_authorized_imports: Additional Python imports allowed
            use_structured_outputs_internally: Use structured outputs
            max_delegation_depth: Maximum depth of agent delegation
            name: Manager agent name
            description: Manager agent description
            cli_console: CLI console object
            **kwargs: Additional parameters
        """
        self.max_delegation_depth = max_delegation_depth
        self.agent_type = "manager"  # Set agent type

        # Default name and description for manager
        if not name:
            name = "Research Multi-Agent Team"
        if not description:
            description = (
                "orchestrates a team of specialized research agents through "
                "intelligent code-based delegation and coordination"
            )

        # Initialize parent CodeActAgent
        super().__init__(
            orchestrator_model=orchestrator_model,
            search_model=search_model,
            tools=tools,  # Usually empty for managers
            initial_state=initial_state,
            executor_type=executor_type,
            executor_kwargs=executor_kwargs,
            max_steps=max_steps,
            verbosity_level=verbosity_level,
            additional_authorized_imports=additional_authorized_imports,
            enable_streaming=enable_streaming,
            planning_interval=planning_interval,
            use_structured_outputs_internally=use_structured_outputs_internally,
            name=name,
            description=description,
            managed_agents=managed_agents,
            cli_console=cli_console,
            **kwargs
        )

        # Track delegation depth to prevent infinite recursion
        self.initial_state["delegation_depth"] = 0
        self.initial_state["delegation_history"] = []
        self.initial_state["current_delegation_depth"] = 0

    def _prepare_managed_agents(self):
        """Prepare managed agents to be callable as tools

        This ensures each managed agent has the required attributes
        for the manager agent to recognize and use them.
        """
        for agent in self.managed_agents:
            # Ensure each agent has required attributes
            if not hasattr(agent, 'name') or not agent.name:
                logger.warning(
                    f"Managed agent {agent.__class__.__name__} missing name"
                )
                continue

            if not hasattr(agent, 'description') or not agent.description:
                logger.warning(
                    f"Managed agent {agent.name} missing description"
                )
                continue

            # Ensure name is a valid Python identifier
            if not agent.name.isidentifier():
                logger.error(
                    f"Managed agent name '{agent.name}' is not a valid Python "
                    f"identifier. Names must be valid function names."
                )
                continue

            # Get display name for user-friendly output
            display_name = getattr(agent, 'display_name', agent.name)

            # Log managed agent registration
            logger.info(
                f"Registered managed agent: {agent.name} ({display_name}) - "
                f"{agent.description}"
            )

    def _create_prompt_templates(self):
        """Create extended prompt templates with manager-specific instructions

        Returns:
            dict: Extended prompt templates
        """
        # Get base templates from parent
        templates = super()._create_prompt_templates()

        # Add manager-specific instructions
        from .prompt_templates.codact_prompts import MANAGED_AGENT_TEMPLATES
        manager_instructions = MANAGED_AGENT_TEMPLATES.get("manager_instructions", "")

        if manager_instructions:
            # Append to system prompt
            templates["system_prompt"] = (
                templates.get("system_prompt", "") + "\n\n" + manager_instructions
            )
            logger.debug("Added manager-specific instructions to prompt templates")

        return templates

    def create_agent(self):
        """Create the manager agent with managed agents registered

        Returns:
            CodeAgent: Configured manager agent
        """
        # Prepare managed agents first
        self._prepare_managed_agents()

        # Let parent create the base agent
        agent = super().create_agent()

        # Log manager agent configuration
        logger.info(
            f"Manager agent '{self.name}' initialized with "
            f"{len(self.managed_agents)} managed agents"
        )

        return agent
