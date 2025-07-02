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
    CodeAgent, Tool
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
        use_structured_outputs_internally: bool = False,
        cli_console=None,
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
        default_security_kwargs = {
            "timeout": 300,  # 300 second timeout for code execution
            "max_output_size": 100000,  # Limit output to 100KB
            "disable_network": False,  # Keep network for API calls
            "restricted_paths": ["/etc", "/root", "/home"],  # Block sensitive paths
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
            r"__import__",  # Dynamic imports
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
            r"open\s*\(",  # file operations
            r"file\s*\(",  # file operations
            r"input\s*\(",  # user input
            r"raw_input\s*\(",  # user input (Python 2)
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
            extensions=extension_content
        )

    def _get_authorized_imports(self):
        """Get list of authorized import modules

        Returns:
            List[str]: List of authorized import modules
        """
        # Set default allowed import modules with security restrictions
        default_authorized_imports = [
            "json", "re", "collections", "datetime",
            "time", "calendar", "math", "csv", "itertools", "copy",
            "requests", "bs4", "urllib", "html",
            "io", "aiohttp", "asyncio",
            "logging", "pandas", "numpy", "tabulate",
            "rich"
        ]
        # Security: Removed dangerous imports like 'os', 'sys', 'dotenv'
        # These can be used for file system access or environment manipulation

        if self.additional_authorized_imports:
            # Security check: Filter out dangerous modules
            dangerous_modules = {
                "os", "sys", "subprocess", "eval", "exec", 
                "compile", "__builtins__", "open", "file",
                "input", "raw_input", "execfile", "dotenv"
            }
            safe_additions = [
                mod for mod in self.additional_authorized_imports 
                if mod not in dangerous_modules
            ]
            if len(safe_additions) < len(self.additional_authorized_imports):
                logger.warning(
                    "Some requested imports were blocked for security: "
                    f"{set(self.additional_authorized_imports) - set(safe_additions)}"
                )
            # Merge and deduplicate import module lists
            return list(set(default_authorized_imports + safe_additions))
        else:
            return default_authorized_imports

    def create_agent(self):
        """Create CodeAct agent instance

        Returns:
            CodeAgent: Configured CodeAct agent instance
        """
        # Create extended prompt templates
        extended_prompt_templates = self._create_prompt_templates()

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
            # Use normal agent, but output warning
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
                use_structured_outputs_internally=self.use_structured_outputs_internally
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
                use_structured_outputs_internally=self.use_structured_outputs_internally
            )

        # Initialize agent state
        agent.state.update(self.initial_state)

        # Output log information
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
            logger.info(f"Agent created, has {len(agent.step_callbacks)} "
                        f"step callbacks")
        else:
            logger.warning("Warning: Agent created without step callbacks!")

        return agent
