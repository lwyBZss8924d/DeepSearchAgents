#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/runtime.py
# code style: PEP 8

"""
DeepSearchAgent core agent runtime module
"""

import logging
from typing import (
    Optional, Dict, Type, Any, List, Union, AsyncGenerator
)
from smolagents import Tool, LiteLLMModel
from ..core.config.settings import settings
from .base_agent import BaseAgent
from .react_agent import ReactAgent
from .codact_agent import CodeActAgent
from .manager_agent import ManagerAgent
from .ui_common.agent_step_callback import AgentStepCallback
from ..tools import from_toolbox
from inspect import isawaitable

logger = logging.getLogger(__name__)


# Create a simple no-op callback class for fallback
class NoOpCallback:
    """Simple no-operation callback that does nothing

    Used as a fallback when a proper callback is not provided
    """

    def __init__(self, session_id=None):
        """Initialize with optional session ID

        Args:
            session_id: Optional session identifier
        """
        self.session_id = session_id
        self.step_counter = 0
        self.tools_used = set()

    def __call__(self, memory_step):
        """No-op callback function that implements minimal logging

        Args:
            memory_step: Step data from smolagents.memory
        """
        # Just log the step number and increment counter
        self.step_counter += 1
        step_type = type(memory_step).__name__
        logging.debug(
            f"Agent step #{self.step_counter} ({step_type}) processed"
        )
        return memory_step

    def get_statistics(self):
        """Get basic statistics

        Returns:
            Dict: Basic statistics
        """
        return {
            "steps_count": self.step_counter,
            "tools_used": list(self.tools_used)
        }


# Dummy agent observer
class DummyAgentObserver:
    """Dummy agent observer implementation"""

    async def create_session(self, query, agent_type):
        """Create a dummy session"""
        return f"dummy-session-{hash(query)}-{agent_type}"

    async def update_session_status(self, session_id, status):
        """Update session status - no-op"""
        logging.debug(f"Would update session {session_id} to status {status}")

    async def publish_event(self, session_id, event_type, data):
        """Publish event - no-op"""
        logging.debug(
            f"Would publish {event_type} event for session {session_id} "
            f"with data length: {len(str(data)) if data else 0}"
        )


# Create dummy agent observer instance
agent_observer = DummyAgentObserver()

logger = logging.getLogger(__name__)

# Dictionary to track active sessions with agents
_active_sessions: Dict[str, Any] = {}


class AgentRuntime:
    """Unified runtime for DeepSearchAgent, supporting dynamic registration
    of different agent types"""

    def __init__(self, settings_obj=None):
        """Initialize the agent runtime

        Args:
            settings_obj: Optional settings object to override defaults
        """
        self.settings = settings_obj or settings
        self._agent_registry: Dict[str, Type] = {}
        self._agent_instances: Dict[str, Any] = {}
        self._tools: List[Tool] = []
        self._active_sessions: Dict[str, Dict] = {}
        self.running_agent = None
        self.result = None
        self.model_args = None
        self.react_agent = None
        self.code_agent = None

        # Get API keys and validate them
        self.api_keys = self._get_api_keys()
        self.valid_api_keys = self._validate_api_keys()

        # Initialize tools if API keys are valid
        if self.valid_api_keys:
            self._tools = self._initialize_tools()

        # Register default agent types
        self.register_agent("react", ReactAgent)
        self.register_agent("codact", CodeActAgent)
        self.register_agent("manager", ManagerAgent)

    def register_agent(self, agent_type: str, agent_class: Type) -> None:
        """Register an agent type with the runtime

        Args:
            agent_type: The type identifier for the agent
            agent_class: The agent class
        """
        self._agent_registry[agent_type] = agent_class
        logger.debug(f"Registered agent type: {agent_type}")

    def _get_api_keys(self) -> Dict[str, str]:
        """Get API keys from settings"""
        return {
            "litellm_master_key": settings.get_api_key("LITELLM_MASTER_KEY"),
            "serper_api_key": settings.get_api_key("SERPER_API_KEY"),
            "jina_api_key": settings.get_api_key("JINA_API_KEY"),
            "wolfram_app_id": settings.get_api_key("WOLFRAM_ALPHA_APP_ID"),
            "litellm_base_url": settings.get_api_key("LITELLM_BASE_URL"),
            "xai_api_key": settings.get_api_key("XAI_API_KEY"),
            # "futurehouse_api_key": settings.get_api_key("FUTUREHOUSE_API_KEY"),
        }

    def _validate_api_keys(self) -> bool:
        """Validate necessary API keys

        Returns:
            bool: True if all required keys are available, False otherwise
        """
        valid_keys = True

        if not self.api_keys.get("serper_api_key"):
            print("Error: SERPER_API_KEY is missing, "
                  "SearchLinksTool with Google search will not work")
            valid_keys = False

        if not self.api_keys.get("jina_api_key"):
            print("Error: JINA_API_KEY is missing, "
                  "ReadURLTool, EmbedTextsTool, "
                  "and RerankTextsTool will not work")
            valid_keys = False

        if not self.api_keys.get("wolfram_app_id"):
            print("Warning: WOLFRAM_ALPHA_APP_ID is missing, "
                  "WolframAlphaTool will not work")

        if not self.api_keys.get("xai_api_key"):
            print("Warning: XAI_API_KEY is missing, "
                  "SearchLinksTool with X.com search will not work")

        # if not self.api_keys.get("futurehouse_api_key"):
        #     print("Warning: FUTUREHOUSE_API_KEY is missing, "
        #           "AcademicRetrieval tool will not work")

        return valid_keys

    def _initialize_tools(self) -> List[Tool]:
        """Initialize all agent tools

        Returns:
            List[Tool]: List of initialized tools
        """
        # Get tool-specific configuration from settings
        tool_specific_kwargs = settings.TOOLS_SPECIFIC_CONFIG.copy()

        # Always make sure rerank_texts has default_model set
        if "rerank_texts" not in tool_specific_kwargs:
            tool_specific_kwargs["rerank_texts"] = {}

        # Set default_model for rerank_texts if not already set
        rerank_config = tool_specific_kwargs.get("rerank_texts", {})
        if "default_model" not in rerank_config:
            rerank_config["default_model"] = settings.RERANKER_TYPE
            tool_specific_kwargs["rerank_texts"] = rerank_config

        # Create tool collection using the from_toolbox factory method
        tool_collection = from_toolbox(
            api_keys=self.api_keys,
            cli_console=None,
            verbose=settings.VERBOSE_TOOL_CALLBACKS,
            tool_specific_kwargs=tool_specific_kwargs
        )

        # Get the list of initialized tools
        tools = tool_collection.tools

        # Log available tools
        logger.info(f"Tools available: {[t.name for t in tools]}")

        return tools

    def _create_llm_model(
        self,
        model_id: str
    ) -> Union[
        LiteLLMModel
    ]:
        """Create LLM model instance

        Args:
            model_id: Model ID to use

        Returns:
            LiteLLMModel: Configured LLM model
        """
        model_cls = LiteLLMModel

        # Get API key and base URL
        api_key = self.api_keys.get("litellm_master_key")
        api_base = self.api_keys.get("litellm_base_url")

        # Strip trailing slash from api_base to avoid double slashes
        if api_base and api_base.endswith('/'):
            api_base = api_base.rstrip('/')

        # Check if API key exists
        if not api_key:
            logger.warning("Missing LITELLM_MASTER_KEY - API calls will fail")

        # Create model instance, ensure API key is correctly set
        model = model_cls(
            model_id=model_id,
            temperature=0.2,
            api_key=api_key,
            api_base=api_base
        )

        return model

    def _get_initial_state(self) -> Dict[str, Any]:
        """Get initial state for agents

        Returns:
            Dict[str, Any]: Initial state for all agents
        """
        return {
            "visited_urls": set(),  # fix: changed from list to set
            "search_queries": [],  # Search queries executed
            "key_findings": {},  # Key findings indexed by topic
            "search_depth": {},  # Current search depth
            "reranking_history": [],  # Reranking history
            "content_quality": {}
        }

    def _create_step_callback(self, session_id=None, debug_mode=True):
        """Create step callback for agent execution tracking

        Args:
            session_id: Optional session ID
            debug_mode: Enable debugging output

        Returns:
            AgentStepCallback: Configured callback
        """
        model = None

        # TODO: try to get model instance from different paths
        # (need to clean up invalid paths)
        if hasattr(self, 'code_agent') and self.code_agent:
            # try path 1: get model directly from agent
            if hasattr(self.code_agent, 'model'):
                model = self.code_agent.model
                logger.debug(
                    f"Found model at code_agent.model: {type(model).__name__}"
                )
            # try path 2: get model from agent.agent
            elif (hasattr(self.code_agent, 'agent') and
                  hasattr(self.code_agent.agent, 'model')):
                model = self.code_agent.agent.model
                logger.debug(
                    f"Found model at code_agent.agent.model: "
                    f"{type(model).__name__}"
                )

        # try to get model instance from react_agent
        if model is None and hasattr(self, 'react_agent') and self.react_agent:
            # try path 1: get model directly from agent
            if hasattr(self.react_agent, 'model'):
                model = self.react_agent.model
                logger.debug(
                    f"Found model at react_agent.model: "
                    f"{type(model).__name__}"
                )
            # try path 2: get model from agent.model
            elif (hasattr(self.react_agent, 'agent') and
                  hasattr(self.react_agent.agent, 'model')):
                model = self.react_agent.agent.model
                logger.debug(
                    f"Found model at react_agent.agent.model: "
                    f"{type(model).__name__}"
                )

        # print model type for debugging
        if model:
            logger.debug(
                f"Model type for token counting: {type(model).__name__}"
            )
            # check token counting attributes
            if (hasattr(model, "last_input_token_count") or
                    hasattr(model, "get_token_counts")):
                logger.debug("Model supports token counting")
            else:
                logger.warning("Model lacks token counting attributes")

        return AgentStepCallback(debug_mode=debug_mode, model=model)

    def create_react_agent(
        self,
        session_id: Optional[str] = None,
        step_callback=None,
        debug_mode=True
    ):
        """Create a ReAct agent

        Args:
            session_id: Optional session ID for step tracking
            step_callback: Optional custom step callback
            debug_mode: Whether to enable debug mode

        Returns:
            ToolCallingAgent: Initialized ReAct agent
        """
        initial_state = self._get_initial_state()

        # Use provided callback or create a new one
        callbacks = []
        if step_callback:
            callbacks.append(step_callback)
        else:
            callbacks.append(self._create_step_callback(
                session_id=session_id,
                debug_mode=debug_mode
            ))

        agent = ReactAgent(
            orchestrator_model=self._create_llm_model(
                model_id=settings.ORCHESTRATOR_MODEL_ID
            ),
            search_model=self._create_llm_model(
                model_id=settings.SEARCH_MODEL_NAME
            ),
            tools=self._tools,
            initial_state=initial_state,
            max_steps=settings.REACT_MAX_STEPS,
            planning_interval=settings.REACT_PLANNING_INTERVAL,
            max_tool_threads=settings.REACT_MAX_TOOL_THREADS,
            cli_console=None,
            step_callbacks=callbacks
        )

        # Store in active sessions
        if session_id:
            _active_sessions[session_id] = agent

        # Update react_agent instance
        self.react_agent = agent

        # Ensure agent object has stream_outputs and memory attributes
        if not hasattr(agent, 'stream_outputs'):
            agent.stream_outputs = settings.REACT_ENABLE_STREAMING

        # Memory is handled internally by smolagents in v1.19.0
        # No need to set it manually

        return agent

    def create_codact_agent(
        self,
        session_id: Optional[str] = None,
        step_callback=None,
        debug_mode=True
    ):
        """Create a CodeAct agent

        Args:
            session_id: Optional session ID for step tracking
            step_callback: Optional custom step callback
            debug_mode: Whether to enable debug mode

        Returns:
            CodeAgent: Initialized CodeAct agent
        """
        initial_state = self._get_initial_state()

        # Use provided callback or create a new one
        callbacks = []
        if step_callback:
            callbacks.append(step_callback)
        else:
            callbacks.append(self._create_step_callback(
                session_id=session_id,
                debug_mode=debug_mode
            ))

        # add final_answer_checks
        final_answer_checks = [self.format_final_answer_for_gradio]

        agent = CodeActAgent(
            orchestrator_model=self._create_llm_model(
                model_id=self.settings.ORCHESTRATOR_MODEL_ID
            ),
            search_model=self._create_llm_model(
                model_id=self.settings.SEARCH_MODEL_NAME
            ),
            tools=self._tools,
            initial_state=initial_state,
            executor_type=self.settings.CODACT_EXECUTOR_TYPE,
            max_steps=self.settings.CODACT_MAX_STEPS,
            verbosity_level=self.settings.CODACT_VERBOSITY_LEVEL,
            additional_authorized_imports=(
                self.settings.CODACT_ADDITIONAL_IMPORTS
            ),
            executor_kwargs=self.settings.CODACT_EXECUTOR_KWARGS,
            planning_interval=self.settings.CODACT_PLANNING_INTERVAL,
            use_structured_outputs_internally=self.settings.CODACT_USE_STRUCTURED_OUTPUTS,
            cli_console=None,
            step_callbacks=callbacks,
            final_answer_checks=final_answer_checks
        )

        # Store in active sessions
        if session_id:
            _active_sessions[session_id] = agent

        # Update code_agent instance
        self.code_agent = agent

        # Ensure agent object has stream_outputs and memory attributes
        if not hasattr(agent, 'stream_outputs'):
            agent.stream_outputs = settings.CODACT_ENABLE_STREAMING

        # Memory is handled internally by smolagents in v1.19.0
        # No need to set it manually

        return agent

    def create_manager_agent(
        self,
        managed_agents: List[Union[str, BaseAgent]] = None,
        session_id: Optional[str] = None,
        step_callback=None,
        debug_mode=True
    ):
        """Create a Manager agent for hierarchical orchestration

        Args:
            managed_agents: List of agent types or agent instances to manage
            session_id: Optional session ID for step tracking
            step_callback: Optional custom step callback
            debug_mode: Whether to enable debug mode

        Returns:
            ManagerAgent: Initialized manager agent
        """
        initial_state = self._get_initial_state()

        # Create managed agents if specified as strings
        if managed_agents:
            agents = []
            for agent_spec in managed_agents:
                if isinstance(agent_spec, str):
                    # Create agent from type string
                    if agent_spec == "react":
                        agent = self.create_react_agent(debug_mode=False)
                    elif agent_spec == "codact":
                        agent = self.create_codact_agent(debug_mode=False)
                    else:
                        logger.warning(f"Unknown agent type: {agent_spec}")
                        continue
                    agents.append(agent)
                elif hasattr(agent_spec, 'run'):
                    # Already an agent instance
                    agents.append(agent_spec)
            managed_agents = agents

        # Use provided callback or create a new one
        callbacks = []
        if step_callback:
            callbacks.append(step_callback)
        else:
            callbacks.append(self._create_step_callback(
                session_id=session_id,
                debug_mode=debug_mode
            ))

        # add final_answer_checks
        final_answer_checks = [self.format_final_answer_for_gradio]

        agent = ManagerAgent(
            orchestrator_model=self._create_llm_model(
                model_id=settings.ORCHESTRATOR_MODEL_ID
            ),
            search_model=self._create_llm_model(
                model_id=settings.SEARCH_MODEL_NAME
            ),
            tools=[],  # Manager typically doesn't use tools directly
            initial_state=initial_state,
            managed_agents=managed_agents or [],
            max_steps=getattr(settings, 'MANAGER_MAX_STEPS', 30),
            planning_interval=getattr(settings, 'MANAGER_PLANNING_INTERVAL', 10),
            executor_type=settings.CODACT_EXECUTOR_TYPE,
            executor_kwargs=settings.CODACT_EXECUTOR_KWARGS,
            verbosity_level=settings.CODACT_VERBOSITY_LEVEL,
            additional_authorized_imports=settings.CODACT_ADDITIONAL_IMPORTS,
            enable_streaming=getattr(settings, 'MANAGER_ENABLE_STREAMING', False),
            use_structured_outputs_internally=settings.CODACT_USE_STRUCTURED_OUTPUTS,
            cli_console=None,
            step_callbacks=callbacks,
            final_answer_checks=final_answer_checks
        )

        # Store in active sessions
        if session_id:
            _active_sessions[session_id] = agent

        # Ensure agent object has stream_outputs and memory attributes
        if not hasattr(agent, 'stream_outputs'):
            agent.stream_outputs = getattr(settings, 'MANAGER_ENABLE_STREAMING', False)

        # Memory is handled internally by smolagents in v1.19.0
        # No need to set it manually

        return agent

    def get_or_create_agent(
        self,
        agent_type="codact",
        step_callback=None,
        debug_mode=True
    ):
        """Get an existing agent or create a new one

        Args:
            agent_type: Agent type identifier
            step_callback: Optional step callback
            debug_mode: Whether to enable debug mode

        Returns:
            Agent instance

        Example usage with context manager:
            runtime = AgentRuntime()
            with runtime.get_or_create_agent("react") as agent:
                result = agent.run("What is the weather?")
                # Resources automatically cleaned up on exit
        """
        if agent_type.lower() == "react":
            if self.react_agent:
                # Recreate agent with step callback if provided
                if step_callback:
                    return self.create_react_agent(
                        step_callback=step_callback,
                        debug_mode=debug_mode
                    )

                # Ensure agent object has Gradio UI needed properties
                if not hasattr(self.react_agent, 'name'):
                    self.react_agent.name = "DeepSearch ReAct Agent"
                if not hasattr(self.react_agent, 'description'):
                    self.react_agent.description = (
                        "DeepSearchAgent with ReAct architecture combines "
                        "advanced web search, content processing, and "
                        "reasoning to answer complex questions."
                    )

                # Ensure run method proxies to smolagents needed interface
                if not hasattr(self.react_agent, 'original_run'):
                    self.react_agent.original_run = self.react_agent.run

                async def run_wrapper(user_input, *args, **kwargs):
                    """Wrap run method to match GradioUI expectations"""
                    condition = (not args and not kwargs and
                                 isinstance(user_input, str))
                    if condition:
                        result = self.react_agent.original_run(user_input)
                        if isawaitable(result):
                            return await result
                        return result

                    result = self.react_agent.original_run(
                        user_input, *args, **kwargs
                    )
                    if isawaitable(result):
                        return await result
                    return result

                self.react_agent.run = run_wrapper

                return self.react_agent
            else:
                agent = self.create_react_agent(
                    step_callback=step_callback,
                    debug_mode=debug_mode
                )

                # Ensure agent object has Gradio UI needed properties
                if not hasattr(agent, 'name'):
                    agent.name = "DeepSearch ReAct Agent"
                if not hasattr(agent, 'description'):
                    agent.description = (
                        "DeepSearchAgent with ReAct architecture combines "
                        "advanced web search, content processing, and "
                        "reasoning to answer complex questions."
                    )

                # Ensure run method proxies to smolagents needed interface
                if not hasattr(agent, 'original_run'):
                    agent.original_run = agent.run

                    async def run_wrapper(user_input, *args, **kwargs):
                        """Wrap run method to match GradioUI expectations"""
                        condition = (not args and not kwargs and
                                     isinstance(user_input, str))
                        if condition:
                            result = agent.original_run(user_input)
                            if isawaitable(result):
                                return await result
                            return result

                        result = agent.original_run(
                            user_input, *args, **kwargs
                        )
                        if isawaitable(result):
                            return await result
                        return result

                    agent.run = run_wrapper

                return agent

        elif agent_type.lower() == "codact":
            if self.code_agent:
                # Recreate agent with step callback if provided
                if step_callback:
                    return self.create_codact_agent(
                        step_callback=step_callback,
                        debug_mode=debug_mode
                    )

                # Ensure agent object has Gradio UI needed properties
                if not hasattr(self.code_agent, 'name'):
                    self.code_agent.name = "DeepSearch CodeAct Agent"
                if not hasattr(self.code_agent, 'description'):
                    self.code_agent.description = (
                        "DeepSearchAgent with CodeAct architecture "
                        "generates and executes Python code to "
                        "perform research actions to answer complex questions."
                    )

                # Ensure run method proxies to smolagents needed interface
                if not hasattr(self.code_agent, 'original_run'):
                    self.code_agent.original_run = self.code_agent.run

                    async def run_wrapper(user_input, *args, **kwargs):
                        """Wrap run method to match GradioUI expectations"""
                        condition = (not args and not kwargs and
                                     isinstance(user_input, str))
                        if condition:
                            result = self.code_agent.original_run(user_input)
                            if isawaitable(result):
                                return await result
                            return result

                        result = self.code_agent.original_run(
                            user_input, *args, **kwargs
                        )
                        if isawaitable(result):
                            return await result
                        return result

                    self.code_agent.run = run_wrapper

                return self.code_agent
            else:
                agent = self.create_codact_agent(
                    step_callback=step_callback,
                    debug_mode=debug_mode
                )

                # Ensure agent object has Gradio UI needed properties
                if not hasattr(agent, 'name'):
                    agent.name = "DeepSearch CodeAct Agent"
                if not hasattr(agent, 'description'):
                    agent.description = (
                        "DeepSearchAgent with CodeAct architecture "
                        "generates and executes Python code to "
                        "perform research actions to answer complex questions."
                    )

                # Ensure run method proxies to smolagents needed interface
                if not hasattr(agent, 'original_run'):
                    agent.original_run = agent.run

                    async def run_wrapper(user_input, *args, **kwargs):
                        """Wrap run method to match GradioUI expectations"""
                        condition = (not args and not kwargs and
                                     isinstance(user_input, str))
                        if condition:
                            result = agent.original_run(user_input)
                            if isawaitable(result):
                                return await result
                            return result

                        result = agent.original_run(
                            user_input, *args, **kwargs
                        )
                        if isawaitable(result):
                            return await result
                        return result

                    agent.run = run_wrapper

                return agent

        elif agent_type.lower() == "manager":
            # Create a new Manager agent with research team
            team_type = getattr(settings, 'MANAGER_TEAM', 'research')
            if team_type == 'research':
                managed_agents = self._create_research_team()
            else:
                # Custom team from settings
                custom_agents = getattr(settings, 'MANAGER_CUSTOM_AGENTS', None)
                if custom_agents:
                    managed_agents = self._create_custom_team(custom_agents)
                else:
                    # Default to research team if no custom agents specified
                    managed_agents = self._create_research_team()

            agent = self.create_manager_agent(
                managed_agents=managed_agents,
                step_callback=step_callback,
                debug_mode=debug_mode
            )

            # Ensure agent object has required properties
            if not hasattr(agent, 'name'):
                agent.name = "Research Multi-Agent Team"
            if not hasattr(agent, 'description'):
                agent.description = (
                    "Orchestrates a team of specialized research agents through "
                    "intelligent code-based delegation and coordination"
                )

            # Ensure run method proxies to smolagents needed interface
            if not hasattr(agent, 'original_run'):
                agent.original_run = agent.run

                async def run_wrapper(user_input, *args, **kwargs):
                    """Wrap run method to match expectations"""
                    condition = (not args and not kwargs and
                                 isinstance(user_input, str))
                    if condition:
                        result = agent.original_run(user_input)
                        if isawaitable(result):
                            return await result
                        return result

                    result = agent.original_run(
                        user_input, *args, **kwargs
                    )
                    if isawaitable(result):
                        return await result
                    return result

                agent.run = run_wrapper

            return agent

        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")

    def create_agent_team(self, team_type="research", custom_agents=None):
        """Create a team of agents for manager orchestration

        Args:
            team_type: Type of team ("research" or "custom")
            custom_agents: List of agent types for custom team

        Returns:
            List[BaseAgent]: List of configured agents
        """
        if team_type == "research":
            return self._create_research_team()
        elif team_type == "custom" and custom_agents:
            return self._create_custom_team(custom_agents)
        else:
            # Default to research team
            return self._create_research_team()

    def _create_research_team(self):
        """Create the research team with specialized agents

        Returns:
            List[BaseAgent]: Research team agents
        """
        team = []

        # Create Web Research Specialist (React agent)
        research_agent = self.create_react_agent(
            step_callback=None,
            debug_mode=False
        )
        # Use valid Python identifier for callable name
        research_agent.name = "web_search_agent"
        research_agent.display_name = "Research Team: Web Search Agent"
        research_agent.description = (
            "A team member specialized in web search, content retrieval, and "
            "information gathering using tool-calling approach"
        )
        team.append(research_agent)

        # Create Data Analysis Specialist (CodeAct agent)
        analysis_agent = self.create_codact_agent(
            step_callback=None,
            debug_mode=False
        )
        # Use valid Python identifier for callable name
        analysis_agent.name = "analysis_agent"
        analysis_agent.display_name = "Research Team: Analysis Agent"
        analysis_agent.description = (
            "A team member specialized in data processing, computation, and synthesis "
            "using code execution approach"
        )
        team.append(analysis_agent)

        logger.info("Created research team with 2 specialized agents")
        return team

    def _create_custom_team(self, agent_types):
        """Create a custom team based on specified agent types

        Args:
            agent_types: List of agent type strings

        Returns:
            List[BaseAgent]: Custom team agents
        """
        team = []

        for i, agent_type in enumerate(agent_types):
            if agent_type.lower() == "react":
                agent = self.create_react_agent(
                    step_callback=None,
                    debug_mode=False
                )
                agent.name = f"React Agent {i+1}"
                agent.description = "Tool-calling agent for structured tasks"
            elif agent_type.lower() == "codact":
                agent = self.create_codact_agent(
                    step_callback=None,
                    debug_mode=False
                )
                agent.name = f"CodeAct Agent {i+1}"
                agent.description = "Code execution agent for computational tasks"
            else:
                logger.warning(f"Unknown agent type: {agent_type}, skipping")
                continue

            team.append(agent)

        logger.info(f"Created custom team with {len(team)} agents")
        return team

    async def run_on_session(self, session_id: str) -> str:
        """Run agent on an existing session

        Args:
            session_id: Session ID to execute

        Returns:
            str: Agent result
        """
        try:
            # Get session data
            logger.info(f"Running agent for session {session_id}")

            # Just use a dummy implementation
            if session_id in _active_sessions:
                agent = _active_sessions[session_id]
                # Execute the agent if it exists in active sessions
                result = await agent.run()
                return result
            else:
                # Return error if session doesn't exist
                error_msg = f"Session {session_id} " \
                            "not found in active sessions"
                logger.error(error_msg)
                return f"Error: {error_msg}"

        except Exception as e:
            error_msg = f"Error executing agent for session {session_id}: {e}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

    async def run(
        self,
        user_input: str,
        agent_type: Optional[str] = None,
        model_args: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        step_callback=None,
        debug_mode: bool = True,
        stream: bool = True
    ) -> Union[str, AsyncGenerator[Dict[str, Any], None]]:
        """Run the agent with the given input

        Args:
            user_input: User input/query
            agent_type: Optional agent type (react or codact)
            model_args: Optional model arguments
            session_id: Optional session ID for step tracking
            step_callback: Optional step callback
            debug_mode: Whether to enable debug mode
            stream: Whether to enable streaming output

        Returns:
            Result from the agent (string or generator for streaming)
        """
        try:
            # Store for later use if needed
            self.model_args = model_args

            # Use the default agent type if none specified
            if agent_type is None:
                agent_type = settings.DEEPSEARCH_AGENT_MODE

            logger.info(f"Running {agent_type} agent with query: "
                        f"{user_input[:50] if user_input else ''}...")

            if agent_type.lower() == "react":
                # Create a new ReAct agent
                agent = self.create_react_agent(
                    session_id=session_id,
                    step_callback=step_callback,
                    debug_mode=debug_mode
                )
            elif agent_type.lower() == "codact":
                # Create a new CodeAct agent
                agent = self.create_codact_agent(
                    session_id=session_id,
                    step_callback=step_callback,
                    debug_mode=debug_mode
                )
            else:
                raise ValueError(f"Unsupported agent type: {agent_type}")

            # Store the running agent
            self.running_agent = agent

            # Run the agent with streaming if requested
            if stream:
                # Return a generator for streaming
                return agent.run(user_input, stream=True)
            else:
                # Run in non-streaming mode
                result = await agent.run(user_input, stream=False)
                self.result = result
                return result

        except Exception as e:
            error_msg = f"Error running agent: {e}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

    def format_final_answer_for_gradio(self, final_answer, memory=None):
        """Ensure final_answer can be rendered correctly by Gradio UI"""
        import json
        # If the answer is a JSON string, try to parse it
        if (isinstance(final_answer, str) and
                final_answer.strip().startswith('{')):
            try:
                answer_dict = json.loads(final_answer)
                # Extract content field as Markdown content
                if (isinstance(answer_dict, dict) and
                        "content" in answer_dict):
                    return answer_dict["content"]
            except json.JSONDecodeError:
                pass
        return final_answer


# Create a singleton agent runtime
agent_runtime = AgentRuntime()
