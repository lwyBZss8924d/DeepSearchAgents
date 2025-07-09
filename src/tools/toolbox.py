#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/tools/toolbox.py
# code style: PEP 8

"""
Agent ToolBox is Full Tools collection for DeepSearchAgent.
This module provides a centralized way to manage and initialize
all DeepSearchAgent tools using the ToolCollection interface.
"""

import logging
import os
from typing import Dict, List, Optional, Type, Any
from contextlib import contextmanager
from ..core.config.settings import settings
from smolagents import Tool, ToolCollection

# Import all DeepSearchAgent system agent's tools classes
from .search import SearchLinksTool
from .search_fast import SearchLinksFastTool
from .readurl import ReadURLTool
from .xcom_readurl import XcomReadURLTool
from .chunk import ChunkTextTool
from .embed import EmbedTextsTool
from .rerank import RerankTextsTool
from .wolfram import EnhancedWolframAlphaTool
from .final_answer import EnhancedFinalAnswerTool
from .github_qa import GitHubRepoQATool

TOOL_ICONS = {
    "search_links": "🔍",  # search
    "search_fast": "⚡",   # fast search
    "read_url": "📄",      # read URL
    "xcom_read_url": "🐦",  # X.com read URL
    "chunk_text": "✂️",    # chunk text
    "embed_texts": "🧩",   # embed texts
    "rerank_texts": "🏆",  # rerank texts
    "wolfram": "🧮",       # wolfram
    "final_answer": "✅",  # final answer
    "github_repo_qa": "🐙"  # GitHub repo deep analysis
}

logger = logging.getLogger(__name__)


# Define tool registry
BUILTIN_TOOLS = {
    "search_links": SearchLinksTool,
    "search_fast": SearchLinksFastTool,
    "read_url": ReadURLTool,
    "xcom_read_url": XcomReadURLTool,
    "chunk_text": ChunkTextTool,
    "embed_texts": EmbedTextsTool,
    "rerank_texts": RerankTextsTool,
    "wolfram": EnhancedWolframAlphaTool,
    "final_answer": EnhancedFinalAnswerTool,
    "github_repo_qa": GitHubRepoQATool,
}


def _create_tool_instance(
    tool_cls: Type[Tool],
    api_keys: Dict[str, str],
    cli_console=True,
    verbose: bool = False,
    tool_specific_kwargs: Optional[Dict[str, Dict[str, Any]]] = None,
    **kwargs
) -> Optional[Tool]:
    """
    Create a tool instance from the given tool class.

    Args:
        tool_cls: The tool class to instantiate
        api_keys: Dictionary of API keys
        cli_console: Optional console for rich output
        verbose: Whether to enable verbose logging
        tool_specific_kwargs: Optional dictionary mapping tool names to
                             tool-specific kwargs dictionaries
        **kwargs: Additional tool-specific arguments

    Returns:
        Tool: The initialized tool instance, or None if initialization failed
    """
    tool_name = getattr(tool_cls, "name", None)

    # Prepare arguments with keys relevant to this tool
    tool_args = {}

    # Add API keys based on tool class naming patterns
    if (
        "SearchLinksTool" in tool_cls.__name__ and
        "SearchLinksFastTool" not in tool_cls.__name__
    ):
        tool_args["serper_api_key"] = api_keys.get("serper_api_key")
        tool_args["xai_api_key"] = api_keys.get("xai_api_key")
    elif "SearchLinksFastTool" in tool_cls.__name__:
        # SearchLinksFastTool accepts a dict of API keys
        tool_args["api_keys"] = {
            "serper": api_keys.get("serper_api_key"),
            "xai": api_keys.get("xai_api_key"),
            "jina": api_keys.get("jina_api_key"),
            "exa": api_keys.get("exa_api_key")
        }
    elif ("ReadURLTool" in tool_cls.__name__ and
          "XcomReadURLTool" not in tool_cls.__name__):
        tool_args["jina_api_key"] = api_keys.get("jina_api_key")
    elif "XcomReadURLTool" in tool_cls.__name__:
        tool_args["xai_api_key"] = api_keys.get("xai_api_key")
    elif "ChunkTextTool" in tool_cls.__name__:
        tool_args["jina_api_key"] = api_keys.get("jina_api_key")
    elif "EmbedTextsTool" in tool_cls.__name__:
        tool_args["jina_api_key"] = api_keys.get("jina_api_key")
    elif "RerankTextsTool" in tool_cls.__name__:
        tool_args["jina_api_key"] = api_keys.get("jina_api_key")
    elif "WolframAlphaTool" in tool_cls.__name__:
        tool_args["wolfram_app_id"] = api_keys.get("wolfram_app_id")

    # Add common arguments (except for tools that don't accept them)
    if "SearchLinksFastTool" not in tool_cls.__name__:
        tool_args["cli_console"] = cli_console
        tool_args["verbose"] = verbose

    # Add tool-specific arguments if provided and the tool is found
    if tool_specific_kwargs and tool_name in tool_specific_kwargs:
        specific_kwargs = tool_specific_kwargs[tool_name]

        # Handle parameter name mappings for specific tools
        if "SearchLinksTool" in tool_cls.__name__:
            # SearchLinksTool doesn't accept these in __init__
            # They should be used in forward() method
            if 'num_results' in specific_kwargs:
                specific_kwargs.pop('num_results')
            if 'location' in specific_kwargs:
                specific_kwargs.pop('location')
        elif "ChunkTextTool" in tool_cls.__name__:
            # Map chunk_size -> default_chunk_size
            # Map chunk_overlap -> default_chunk_overlap
            if 'chunk_size' in specific_kwargs:
                tool_args["default_chunk_size"] = specific_kwargs.pop(
                    'chunk_size'
                )
            if 'chunk_overlap' in specific_kwargs:
                tool_args["default_chunk_overlap"] = specific_kwargs.pop(
                    'chunk_overlap'
                )
        elif "EnhancedWolframAlphaTool" in tool_cls.__name__:
            # Map wolfram_app_id -> app_id
            if 'wolfram_app_id' in specific_kwargs:
                # This is already handled by API keys, so we can just remove it
                specific_kwargs.pop('wolfram_app_id')

        # Update with any remaining specific kwargs after mapping
        tool_args.update(specific_kwargs)

    # Add any remaining kwargs for all tools
    tool_args.update(kwargs)

    try:
        # Handle specific tools with special initialization requirements
        if "RerankTextsTool" in tool_cls.__name__:
            # If default_model is provided in tool args or via
            # tool_specific_kwargs
            if 'default_model' in tool_args:
                reranker_type = tool_args.pop('default_model')
                return tool_cls(
                    default_model=reranker_type,
                    **tool_args
                )
            else:
                # Create with standard arguments
                return tool_cls(**tool_args)
        else:
            # Generic initialization for other tool types
            return tool_cls(**tool_args)

    except Exception as e:
        logger.error(
            f"Failed to create tool instance for {tool_cls.__name__}: {e}"
        )
        return None


def from_toolbox(
    api_keys: Dict[str, str],
    tool_names: Optional[List[str]] = None,
    cli_console=True,
    verbose: bool = False,
    tool_specific_kwargs: Optional[Dict[str, Dict[str, Any]]] = None,
    **kwargs
) -> ToolCollection:
    """
    Create a ToolCollection containing DeepSearchAgent system tools.

    Args:
        api_keys: Dictionary with API keys (serper_api_key, jina_api_key,
                 wolfram_app_id)
        tool_names: Optional list of tool names to include, defaults to all
                    built-in tools
        cli_console: Optional console for rich output
        verbose: Whether to enable verbose output
        tool_specific_kwargs: Optional dictionary mapping tool names to
                             tool-specific kwargs dictionaries
        **kwargs: Additional tool-specific arguments

    Returns:
        ToolCollection: Collection of initialized tools
    """
    # Use all tools if none specified
    if tool_names is None:
        tool_names = list(BUILTIN_TOOLS.keys())

    tools = []

    # Create instances of requested tools
    for name in tool_names:
        if name not in BUILTIN_TOOLS:
            logger.warning(f"Unknown tool: {name}. Skipping.")
            continue

        tool_instance = _create_tool_instance(
            BUILTIN_TOOLS[name],
            api_keys,
            cli_console=cli_console,
            verbose=verbose,
            tool_specific_kwargs=tool_specific_kwargs,
            **kwargs
        )

        if tool_instance:
            tools.append(tool_instance)
            logger.debug(
                f"Added tool {name} {TOOL_ICONS.get(name, '')} to toolbox"
            )

    tool_names_str = ", ".join([t.name for t in tools])
    logger.info(
        f"Created toolbox with {len(tools)} tools: {tool_names_str}"
    )
    return ToolCollection(tools)


# Add from_hub and from_mcp convenience methods to ToolCollection
@classmethod
def from_toolbox_enhanced(
    cls,
    api_keys: Dict[str, str],
    tool_names: Optional[List[str]] = None,
    cli_console=True,
    verbose: bool = False,
    **kwargs
) -> "ToolCollection":
    """
    Extended version of from_toolbox for use as a ToolCollection class method.

    Args:
        api_keys: Dictionary with API keys
        tool_names: Optional list of tool names to include
        cli_console: Optional console for rich output
        verbose: Whether to enable verbose output
        **kwargs: Additional tool-specific arguments

    Returns:
        ToolCollection: Collection of initialized tools
    """
    return from_toolbox(
        api_keys=api_keys,
        tool_names=tool_names,
        cli_console=cli_console,
        verbose=verbose,
        **kwargs
    )


# Note: from_toolbox functionality is available via the standalone function
# ToolCollection.from_toolbox = from_toolbox_enhanced

class DeepSearchToolbox:
    """
    Unified interface for managing DeepSearchAgent tools and extensions.
    Provides registry and factory methods for all tool types.
    """

    def __init__(self, auto_load_from_config=True):
        """
        Initialize the toolbox with built-in tools and optionally load
        tools from configuration.

        Args:
            auto_load_from_config: Whether to automatically load tools
                                   from config.toml
        """
        self.tool_registry = BUILTIN_TOOLS.copy()

        # Auto-load tools from Hub and MCP if configured
        if auto_load_from_config:
            # Get API keys for tool initialization
            api_keys = {
                "hf_token": settings.hf_token,
                "jina_api_key": settings.jina_api_key,
                "serper_api_key": settings.serper_api_key,
                "wolfram_app_id": settings.wolfram_alpha_app_id,
                "xai_api_key": settings.xai_api_key,
            }

            # Load Hub collections if configured
            if settings.TOOLS_HUB_COLLECTIONS:
                self._load_hub_collections_from_config(api_keys)

            # Load MCP servers if configured
            if settings.TOOLS_MCP_SERVERS:
                self._load_mcp_servers_from_config(api_keys)

    def _load_hub_collections_from_config(
        self, api_keys: Dict[str, str]
    ) -> None:
        """
        Load Hub collections configured in settings

        Args:
            api_keys: Dictionary with API keys
        """
        for collection_slug in settings.TOOLS_HUB_COLLECTIONS:
            try:
                logger.info(
                    f"Loading tools from Hub collection: {collection_slug}"
                )
                self.load_from_hub(
                    collection_slug=collection_slug,
                    token=api_keys.get("hf_token"),
                    trust_remote_code=settings.TOOLS_TRUST_REMOTE_CODE,
                    replace_existing=True
                )
            except Exception as e:
                logger.error(
                    f"Failed to load Hub collection {collection_slug}: {e}"
                )

    def _load_mcp_servers_from_config(self, api_keys: Dict[str, str]) -> None:
        """
        Load MCP servers configured in settings

        Args:
            api_keys: Dictionary with API keys
        """
        for server_config in settings.TOOLS_MCP_SERVERS:
            try:
                # Skip if server configuration is missing required fields
                if "type" not in server_config:
                    logger.error(
                        "MCP server config missing 'type' field. Skipping."
                    )
                    continue

                server_type = server_config.get("type", "")

                # Configure server parameters based on type
                if server_type == "stdio":
                    self._load_stdio_mcp_server(server_config, api_keys)
                elif server_type == "sse":
                    self._load_sse_mcp_server(server_config, api_keys)
                else:
                    logger.error(
                        f"Unknown MCP server type: {server_type}. Skipping."
                    )
            except Exception as e:
                logger.error(f"Failed to load MCP server: {e}")

    def _load_stdio_mcp_server(
        self, server_config: Dict[str, Any], api_keys: Dict[str, str]
    ) -> None:
        """
        Load a stdio MCP server from configuration

        Args:
            server_config: Server configuration
            api_keys: Dictionary with API keys
        """
        try:
            # Import MCP dependencies dynamically
            try:
                from mcp import StdioServerParameters
            except ImportError:
                logger.error(
                    "Cannot load MCP server: 'mcp' package not installed. "
                    "Install with 'pip install \"smolagents[mcp]\"'"
                )
                return

            # Required fields check
            if not all(k in server_config for k in ["command", "args"]):
                logger.error(
                    "Stdio MCP server config missing required fields. "
                    "Skipping."
                )
                return

            # Create server parameters
            command = server_config.get("command")
            args = server_config.get("args", [])

            # Process environment variables
            env = os.environ.copy()
            if "env" in server_config and isinstance(
                server_config["env"], dict
            ):
                env.update(server_config["env"])

            args_str = ' '.join(args)
            logger.info(
                f"Loading stdio MCP server with command: {command} {args_str}"
            )

            # Create parameters object
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )

            # Load tools from MCP server
            with self.load_from_mcp(
                server_params,
                trust_remote_code=settings.TOOLS_TRUST_REMOTE_CODE,
                replace_existing=True
            ):
                pass  # Tools are loaded in the context manager

        except Exception as e:
            logger.error(f"Failed to load stdio MCP server: {e}")

    def _load_sse_mcp_server(
        self, server_config: Dict[str, Any], api_keys: Dict[str, str]
    ) -> None:
        """
        Load an SSE MCP server from configuration

        Args:
            server_config: Server configuration
            api_keys: Dictionary with API keys
        """
        try:
            # Required fields check
            if "url" not in server_config:
                logger.error(
                    "SSE MCP server config missing 'url' field. Skipping."
                )
                return

            url = server_config.get("url")
            logger.info(f"Loading SSE MCP server from URL: {url}")

            # For SSE servers, we pass the config as a dictionary directly
            # to ToolCollection.from_mcp which handles it appropriately
            with self.load_from_mcp(
                {"url": url},
                trust_remote_code=settings.TOOLS_TRUST_REMOTE_CODE,
                replace_existing=True
            ):
                pass  # Tools are loaded in the context manager

        except Exception as e:
            logger.error(f"Failed to load SSE MCP server: {e}")

    def register_tool(self, name: str, tool_cls: Type[Tool]) -> None:
        """
        Register a new tool in the toolbox

        Args:
            name: Tool identifier
            tool_cls: Tool class to register
        """
        self.tool_registry[name] = tool_cls
        logger.info(f"Registered tool {name} in toolbox")

    def create_tool_collection(
        self,
        api_keys: Dict[str, str],
        tool_names: Optional[List[str]] = None,
        cli_console=True,
        verbose: bool = False,
        **kwargs
    ) -> ToolCollection:
        """
        Create a tool collection with specified tools

        Args:
            api_keys: Dictionary of API keys
            tool_names: Optional list of tool names to include
            cli_console: Optional console for rich output
            verbose: Whether to enable verbose logging
            **kwargs: Additional tool-specific arguments

        Returns:
            ToolCollection with initialized tools
        """
        # If no tool names specified, use all registered tools
        if tool_names is None:
            tool_names = list(self.tool_registry.keys())

        tools = []

        for name in tool_names:
            if name not in self.tool_registry:
                logger.warning(f"Unknown tool: {name}. Skipping.")
                continue

            tool_cls = self.tool_registry[name]
            tool_instance = _create_tool_instance(
                tool_cls,
                api_keys,
                cli_console=cli_console,
                verbose=verbose,
                **kwargs
            )

            if tool_instance:
                tools.append(tool_instance)

        logger.info(f"Created tool collection with {len(tools)} tools")
        return ToolCollection(tools)

    def integrate_hub_collection(
        self,
        collection: ToolCollection,
        replace_existing: bool = False
    ) -> None:
        """
        Integrate tools from a Hub collection into the toolbox

        Args:
            collection: ToolCollection from Hub
            replace_existing: Whether to replace existing tools with same name
        """
        for tool in collection.tools:
            name = tool.name
            if name in self.tool_registry and not replace_existing:
                logger.warning(
                    f"Tool {name} already exists in registry. Skipping."
                )
                continue

            # Register tool class rather than instance
            tool_cls = tool.__class__
            self.register_tool(name, tool_cls)

    def integrate_mcp_collection(
        self,
        collection: ToolCollection,
        replace_existing: bool = False
    ) -> None:
        """
        Integrate tools from an MCP server collection into the toolbox

        Args:
            collection: ToolCollection from MCP
            replace_existing: Whether to replace existing tools with same name
        """
        # Similar implementation to integrate_hub_collection
        for tool in collection.tools:
            name = tool.name
            if name in self.tool_registry and not replace_existing:
                logger.warning(
                    f"Tool {name} already exists in registry. Skipping."
                )
                continue

            # Register tool class rather than instance
            tool_cls = tool.__class__
            self.register_tool(name, tool_cls)

    def load_from_hub(
        self,
        collection_slug: str,
        token: Optional[str] = None,
        trust_remote_code: bool = True,
        replace_existing: bool = False
    ) -> List[str]:
        """
        Load tools directly from Hub collection and register them to the
        toolbox.

        This method provides a convenient way to directly load tools from
        Hugging Face Hub and add them to the DeepSearchAgent toolbox.

        Args:
            collection_slug: Hub collection identifier
            token: Optional authentication token for private collections
            trust_remote_code: Whether to trust remote code
            replace_existing: Whether to replace existing tools with same name

        Returns:
            List of tool names that were successfully loaded
        """
        try:
            # Directly call ToolCollection.from_hub
            collection = ToolCollection.from_hub(
                collection_slug,
                token=token,
                trust_remote_code=trust_remote_code
            )

            # Get tool names before integration for return value
            loaded_tool_names = [tool.name for tool in collection.tools]

            # Integrate the collection into the toolbox
            self.integrate_hub_collection(
                collection,
                replace_existing=replace_existing
            )

            # Log the loaded tools, breaking the long line
            tools_str = ", ".join(loaded_tool_names)
            logger.info(
                f"Loaded {len(loaded_tool_names)} tools from Hub "
                f"collection: {tools_str}"
            )
            return loaded_tool_names

        except Exception as e:
            logger.error(f"Failed to load tools from Hub: {e}")
            return []

    @contextmanager
    def load_from_mcp(
        self,
        server_parameters,
        trust_remote_code: bool = True,
        replace_existing: bool = False
    ):
        """
        Load tools directly from MCP server and register them to the toolbox.

        This context manager provides a convenient way to directly load tools
        from an MCP server and add them to the DeepSearchAgent toolbox.

        Args:
            server_parameters: Parameters for MCP server connection
            trust_remote_code: Whether to trust remote code (REQUIRED for MCP)
            replace_existing: Whether to replace existing tools with same name

        Yields:
            The toolbox instance with loaded MCP tools

        Example:
            ```python
            from mcp import StdioServerParameters

            server_params = StdioServerParameters(
                command="uv",
                args=["--quiet", "pubmedmcp@0.1.3"],
                env={"UV_PYTHON": "3.12", **os.environ},
            )

            with toolbox.load_from_mcp(
                server_params,
                trust_remote_code=True
            ) as tb:
                # toolbox now contains MCP tools
                agent = CodeActAgent(tools=tb.create_tool_collection(...))
            ```
        """
        try:
            # Use the ToolCollection.from_mcp context manager
            with ToolCollection.from_mcp(
                server_parameters,
                trust_remote_code=trust_remote_code
            ) as collection:
                # Get tool names for logging
                mcp_tool_names = [tool.name for tool in collection.tools]

                # Integrate tools into the toolbox
                self.integrate_mcp_collection(
                    collection,
                    replace_existing=replace_existing
                )

                # Log the tools, breaking the long line
                tools_str = ", ".join(mcp_tool_names)
                logger.info(
                    f"Loaded {len(mcp_tool_names)} tools from MCP "
                    f"server: {tools_str}"
                )

                # Yield self to allow usage in context manager
                yield self

        except ImportError as e:
            # Break the error message into multiple lines
            logger.error(
                f"Failed to load MCP tools - missing dependencies: {e}. "
                f"Install with pip install 'smolagents[mcp]'"
            )
            yield self
        except Exception as e:
            logger.error(f"Failed to load tools from MCP server: {e}")
            yield self


# Create singleton toolbox instance
toolbox = DeepSearchToolbox()


__all__ = [
    "ToolCollection",
    "DeepSearchToolbox",
    "toolbox",
    "from_toolbox",
    "TOOL_ICONS",
]
