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
from .react_agent import ReactAgent

logger = logging.getLogger(__name__)


class ManagerAgent(ReactAgent):
    """Manager agent that orchestrates other agents in a hierarchical manner
    
    The ManagerAgent extends ReactAgent to leverage its tool-calling capabilities
    while treating managed agents as specialized tools. This enables sophisticated
    multi-agent architectures where different agents handle different aspects of
    complex tasks.
    """
    
    def __init__(
        self,
        orchestrator_model,
        search_model,
        tools: List[Tool],
        initial_state: Dict[str, Any],
        managed_agents: List[BaseAgent],
        enable_streaming: bool = False,
        max_steps: int = 25,
        planning_interval: int = 7,
        max_tool_threads: int = 1,
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
            tools: List of traditional tools
            initial_state: Initial agent state
            managed_agents: List of agents to manage and orchestrate
            enable_streaming: Whether to enable streaming output
            max_steps: Maximum number of execution steps
            planning_interval: Interval for planning steps
            max_tool_threads: Maximum threads for parallel execution
            max_delegation_depth: Maximum depth of agent delegation
            name: Manager agent name
            description: Manager agent description
            cli_console: CLI console object
            **kwargs: Additional parameters
        """
        self.max_delegation_depth = max_delegation_depth
        
        # Default name and description for manager
        if not name:
            name = "DeepSearch Manager Agent"
        if not description:
            description = (
                "Orchestrates multiple specialized agents to solve complex "
                "tasks through intelligent delegation and coordination"
            )
        
        # Initialize parent ReactAgent with managed agents
        super().__init__(
            orchestrator_model=orchestrator_model,
            search_model=search_model,
            tools=tools,
            initial_state=initial_state,
            enable_streaming=enable_streaming,
            max_steps=max_steps,
            planning_interval=planning_interval,
            max_tool_threads=max_tool_threads,
            name=name,
            description=description,
            managed_agents=managed_agents,
            cli_console=cli_console,
            **kwargs
        )
        
        # Track delegation depth to prevent infinite recursion
        self.initial_state["delegation_depth"] = 0
        
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
            
            # Log managed agent registration
            logger.info(
                f"Registered managed agent: {agent.name} - {agent.description}"
            )
    
    def create_agent(self):
        """Create the manager agent with managed agents registered
        
        Returns:
            ToolCallingAgent: Configured manager agent
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
    
    def delegate_task(
        self, 
        task: str, 
        target_agent: str,
        additional_context: Dict[str, Any] = None
    ) -> str:
        """Delegate a specific task to a managed agent
        
        Args:
            task: The task to delegate
            target_agent: Name of the agent to delegate to
            additional_context: Optional additional context
            
        Returns:
            str: Result from the delegated agent
        """
        # Find the target agent
        for agent in self.managed_agents:
            if agent.name == target_agent:
                # Check delegation depth
                current_depth = self.agent.state.get("delegation_depth", 0)
                if current_depth >= self.max_delegation_depth:
                    return (
                        f"Maximum delegation depth ({self.max_delegation_depth}) "
                        f"reached. Cannot delegate further."
                    )
                
                # Update delegation depth in context
                if additional_context is None:
                    additional_context = {}
                additional_context["delegation_depth"] = current_depth + 1
                
                # Delegate the task
                try:
                    result = agent(task, additional_context)
                    return result
                except Exception as e:
                    logger.error(
                        f"Error delegating to {target_agent}: {str(e)}"
                    )
                    return f"Delegation error: {str(e)}"
        
        return f"No managed agent found with name: {target_agent}"
    
    def analyze_task_complexity(self, task: str) -> Dict[str, Any]:
        """Analyze task to determine delegation strategy
        
        Args:
            task: The task to analyze
            
        Returns:
            Dict containing analysis results and recommendations
        """
        analysis = {
            "requires_web_search": any(
                keyword in task.lower() 
                for keyword in ["search", "find", "latest", "current", "news"]
            ),
            "requires_computation": any(
                keyword in task.lower()
                for keyword in ["calculate", "compute", "analyze", "data"]
            ),
            "requires_synthesis": any(
                keyword in task.lower()
                for keyword in ["summarize", "explain", "compare", "evaluate"]
            ),
            "recommended_agents": []
        }
        
        # Recommend agents based on task analysis
        for agent in self.managed_agents:
            agent_name_lower = agent.name.lower()
            
            if analysis["requires_web_search"] and "search" in agent_name_lower:
                analysis["recommended_agents"].append(agent.name)
            elif analysis["requires_computation"] and any(
                kw in agent_name_lower for kw in ["data", "compute", "analyst"]
            ):
                analysis["recommended_agents"].append(agent.name)
            elif analysis["requires_synthesis"] and any(
                kw in agent_name_lower for kw in ["summary", "synthesis"]
            ):
                analysis["recommended_agents"].append(agent.name)
        
        return analysis