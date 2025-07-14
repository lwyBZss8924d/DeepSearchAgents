#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/codact_agent.py
# code style: PEP 8

"""
CodeAct agent implementation, uses Python code execution mode
for deep search task
"""


from typing import (
    List, Optional, Dict, Any
)
import importlib
import yaml
from smolagents import (
    CodeAgent, Tool, PromptTemplates
)
from .prompt_templates.codact_prompts import (
    CODACT_SYSTEM_EXTENSION, PLANNING_TEMPLATES,
    FINAL_ANSWER_EXTENSION, MANAGED_AGENT_TEMPLATES,
    merge_prompt_templates
)
import logging
from .base_agent import BaseAgent, MultiModelRouter

logger = logging.getLogger(__name__)


class CodeActAgent(BaseAgent):
    """CodeAct agent implementation, uses Python code execution mode
    for deep search"""

    def __init__(
        self,
        orchestrator_model,
        search_model,
        tools: List[Tool],
        initial_state: Dict[str, Any],
        executor_type: str = "local",
        executor_kwargs: Optional[Dict[str, Any]] = None,
        max_steps: int = 25,
        verbosity_level: int = 2,
        additional_authorized_imports: Optional[List[str]] = None,
        enable_streaming: bool = False,
        planning_interval: int = 5,
        use_structured_outputs_internally: bool = True,
        name: str = "DeepResearchAgent",
        description: str = (
            "DeepResearchAgent is a CodeAct multi-agent that can use tools "
            "and programming Python code to deeply web search and analyze "
            "for research tasks."
        ),
        managed_agents: List['BaseAgent'] = None,
        cli_console=True,
        step_callbacks: Optional[List[Any]] = None,
        **kwargs
    ):
        """Initialize CodeAct agent

        Args:
            orchestrator_model: Model for planning and final answer
            search_model: Model for general code generation and search
            tools: Pre-initialized list of tools from runtime
            initial_state: Initial agent state from runtime
            executor_type: Code executor type
            executor_kwargs: Additional executor parameters
            max_steps: Maximum execution steps
            verbosity_level: Verbosity level for logging
            additional_authorized_imports: Additional modules to
                allow importing
            enable_streaming: Whether to enable streaming output
            planning_interval: Interval for planning steps
            use_structured_outputs_internally: Enable JSON-structured
                output format (experimental)
            name: Agent name for identification in hierarchical systems
            description: Agent description for manager agents
            managed_agents: List of sub-agents this agent can manage
            cli_console: CLI console object
            step_callbacks: List of step callbacks
            **kwargs: Additional parameters for future extensions
        """
        # 1. ensure additional_authorized_imports is always a flat list
        if additional_authorized_imports is None:
            self.additional_authorized_imports = []
        elif isinstance(additional_authorized_imports, list):
            # check if there is a nested list and flatten it
            if (
                additional_authorized_imports and
                isinstance(additional_authorized_imports[0], list)
            ):
                self.additional_authorized_imports = (
                    additional_authorized_imports[0]
                )
            else:
                self.additional_authorized_imports = (
                    additional_authorized_imports
                )
        else:
            self.additional_authorized_imports = [
                additional_authorized_imports
            ]

        # 2. ensure the collection type in initial_state is correct
        if initial_state and "visited_urls" in initial_state:
            if not isinstance(initial_state["visited_urls"], set):
                # convert to set
                initial_state["visited_urls"] = set(
                    initial_state["visited_urls"]
                    if initial_state["visited_urls"]
                    else []
                )

        # other initialization remains unchanged
        self.executor_type = executor_type

        # Security: Add default safety settings to executor kwargs
        # Note: Only include parameters supported by smolagents' LocalPythonExecutor
        default_security_kwargs = {
            # LocalPythonExecutor in smolagents may not support all these parameters
            # Keep only what's supported to avoid errors
        }

        # Merge user kwargs with security defaults
        self.executor_kwargs = {**default_security_kwargs, **(executor_kwargs or {})}

        # Warn if user tries to override security settings
        if executor_kwargs:
            overridden = set(executor_kwargs.keys()) & set(default_security_kwargs.keys())
            if overridden:
                logger.warning(
                    f"Security settings overridden by user: {overridden}"
                )

        self.verbosity_level = verbosity_level
        self.use_structured_outputs_internally = use_structured_outputs_internally
        self.step_callbacks = step_callbacks or []

        # call parent class constructor
        super().__init__(
            agent_type="codact",
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

    def validate_code_safety(self, code: str) -> bool:
        """Validate that code is safe to execute

        Args:
            code: Python code string to validate

        Returns:
            bool: True if code appears safe, False otherwise
        """
        # Security patterns to check for
        dangerous_patterns = [
            r"eval\s*\(",  # eval() calls
            r"exec\s*\(",  # exec() calls
            r"compile\s*\(",  # compile() calls
            r"globals\s*\(",  # globals() access
            r"locals\s*\(",  # locals() access
            r"vars\s*\(",  # vars() access
            r"dir\s*\(",  # dir() introspection
            r"getattr\s*\(",  # getattr() for dynamic access
            r"setattr\s*\(",  # setattr() for dynamic modification
            r"delattr\s*\(",  # delattr() for deletion
            r"\bos\.",  # os module access
            r"\bsys\.",  # sys module access
            r"\bsubprocess\.",  # subprocess module
            r"\.\.\/",  # Path traversal
            r"\/etc\/",  # System paths
            r"\/root\/",  # Root paths
        ]

        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                logger.warning(f"Potentially dangerous pattern detected: {pattern}")
                return False

        return True

    def _create_prompt_templates(self):
        """Create extended prompt templates

        Returns:
            dict: Extended prompt templates
        """
        # Select appropriate base templates based on structured outputs setting
        if self.use_structured_outputs_internally:
            # Try to load structured templates from smolagents
            try:
                base_prompts = yaml.safe_load(
                    importlib.resources.files(
                        "smolagents.prompts"
                    ).joinpath("structured_code_agent.yaml").read_text()
                )
                logger.info("Using structured code agent prompts")
            except FileNotFoundError:
                # Fallback to regular prompts if structured not available
                logger.warning(
                    "Structured prompts not found, falling back to regular prompts"
                )
                base_prompts = yaml.safe_load(
                    importlib.resources.files(
                        "smolagents.prompts"
                    ).joinpath("code_agent.yaml").read_text()
                )
        else:
            # Load regular CodeAgent prompt templates
            base_prompts = yaml.safe_load(
                importlib.resources.files(
                    "smolagents.prompts"
                ).joinpath("code_agent.yaml").read_text()
            )

        # Get current UTC time for template rendering
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Create extension content
        extension_content = {
            "system_extension": CODACT_SYSTEM_EXTENSION,
            "planning": PLANNING_TEMPLATES,
            "final_answer": FINAL_ANSWER_EXTENSION,
            "managed_agent": MANAGED_AGENT_TEMPLATES
        }

        # Merge base templates with extension content
        return merge_prompt_templates(
            base_templates=base_prompts,
            extensions=extension_content,
            current_time=current_time
        )

    def _get_authorized_imports(self):
        """Get list of authorized import modules

        Returns:
            List[str]: List of authorized import modules
        """
        # Set default allowed import modules with security restrictions
        # Note: BASE_PYTHON_TOOLS contains built-in functions (bool, str, int, etc.)
        # which are automatically available and should not be in authorized imports

        default_authorized_imports = [
            "logging", "json", "re", "time", "datetime",
            "copy", "requests", "aiohttp", "asyncio",
            "bs4", "urllib", "html",
            "math", "csv", "pandas", "numpy", "tabulate2",
            "arxiv", "wikipediaapi",
            "pymupdf", "markitdown",
            "dotenv",
        ]
        # Security: PROD MUST Removed Dev dangerous imports like 'os', 'sys', 'dotenv'
        # These can be used for file system access or environment manipulation

        if self.additional_authorized_imports:
            # Security check: Filter out dangerous modules (PROD MUST config this)
            dangerous_modules = {

            }
            safe_additions = [
                mod for mod in self.additional_authorized_imports
                if mod not in dangerous_modules
            ]
            if len(safe_additions) < len(self.additional_authorized_imports):
                blocked_imports = (
                    set(self.additional_authorized_imports) -
                    set(safe_additions)
                )
                logger.warning(
                    f"Some requested imports were blocked for security: "
                    f"{blocked_imports}"
                )
            # Merge and deduplicate import module lists
            # Do NOT include BASE_PYTHON_TOOLS as they are built-in functions
            all_imports = (
                default_authorized_imports +
                safe_additions
            )
            return list(set(all_imports))
        else:
            # Do NOT include BASE_PYTHON_TOOLS as they are built-in functions
            return default_authorized_imports

    def create_agent(self):
        """Create CodeAct agent instance

        Returns:
            CodeAgent: Configured CodeAct agent instance
        """
        # Create extended prompt templates
        extended_prompt_templates = PromptTemplates(
            **self._create_prompt_templates()
        )

        # Get authorized import modules
        authorized_imports = self._get_authorized_imports()

        # Create JSON grammar (if using reranker)
        json_grammar = None
        if hasattr(self, 'reranker_type') and self.reranker_type:
            json_grammar = {
                "json_object": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "confidence": {"type": "number"}
                    },
                    "required": ["title", "content"]
                }
            }

        # Validation: structured outputs cannot be used with grammar
        if self.use_structured_outputs_internally and json_grammar is not None:
            logger.warning(
                "Cannot use structured outputs with grammar parameter. "
                "Disabling structured outputs."
            )
            self.use_structured_outputs_internally = False

        # Create model router to use different models for different prompts
        model_router = MultiModelRouter(
            search_model=self.search_model,
            orchestrator_model=self.orchestrator_model
        )

        # Disable streaming processing, use CodeAgent directly
        # Note: Even if enable_streaming=True is passed, non-streaming mode
        # will be used
        if self.enable_streaming:
            # Use normal agent, but output warning only in verbose mode
            if self.verbosity_level >= 2:
                print("Warning: Streaming mode is temporarily disabled in "
                      "this version.")
            agent = CodeAgent(
                tools=self.tools,
                model=model_router,  # Use model router here
                prompt_templates=extended_prompt_templates,
                additional_authorized_imports=authorized_imports,
                executor_type=self.executor_type,
                executor_kwargs=self.executor_kwargs,
                max_steps=self.max_steps,
                verbosity_level=self.verbosity_level,
                grammar=json_grammar if not self.use_structured_outputs_internally else None,
                planning_interval=self.planning_interval,
                step_callbacks=self.step_callbacks,
                use_structured_outputs_internally=self.use_structured_outputs_internally,
                managed_agents=self.managed_agents
            )
        else:
            agent = CodeAgent(
                tools=self.tools,
                model=model_router,  # Use model router here
                prompt_templates=extended_prompt_templates,
                additional_authorized_imports=authorized_imports,
                executor_type=self.executor_type,
                executor_kwargs=self.executor_kwargs,
                max_steps=self.max_steps,
                verbosity_level=self.verbosity_level,
                grammar=json_grammar if not self.use_structured_outputs_internally else None,
                planning_interval=self.planning_interval,
                step_callbacks=self.step_callbacks,
                use_structured_outputs_internally=self.use_structured_outputs_internally,
                managed_agents=self.managed_agents
            )

        # Initialize agent state
        agent.state.update(self.initial_state)

        # Output log information only if not in streaming mode or verbosity is high
        if not self.enable_streaming or self.verbosity_level >= 2:
            print(
                f"DeepSearch CodeAct agent initialized successfully, "
                f"using executor: {self.executor_type}"
            )
            print(f"Allowed import modules: {authorized_imports}")
            print(
                f"Configured tools: "
                f"{[tool.name for tool in agent.tools.values()]}"
            )
            if self.planning_interval:
                print(
                    f"Planning interval: "
                    f"Every {self.planning_interval} steps"
                )
            print(
                f"Using orchestrator model: "
                f"{self.orchestrator_model.model_id} for planning"
            )
            print(
                f"Using search model: {self.search_model.model_id} "
                f"for code generation"
            )
            if self.use_structured_outputs_internally:
                print(
                    "Structured outputs enabled: Using JSON format for "
                    "internal agent communication"
                )

        # ensure callbacks can be accessed and debugged
        if self.step_callbacks and len(self.step_callbacks) > 0:
            logger.info(f"There are {len(self.step_callbacks)} step callbacks "
                        f"when initializing the agent")
            for i, callback in enumerate(self.step_callbacks):
                logger.info(f"Step callback #{i+1}: "
                            f"{callback.__class__.__name__}")
        else:
            logger.warning("Warning: No step callbacks provided!")

        # add extra logs to confirm step callbacks
        # this will check if the wrapped agent retains callbacks
        if hasattr(agent, 'step_callbacks') and agent.step_callbacks:
            logger.info("Agent created with step callbacks configured")
        else:
            logger.warning("Warning: Agent created without step callbacks!")

        return agent
