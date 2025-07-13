#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/servers/run_fastmcp.py
# code style: PEP 8

"""Run DeepSearchAgents as a FastMCP server exposing a Streamable HTTP API.

This module implements a standalone FastMCP server that wraps the
DeepSearchAgents' CodeAct/ReAct agent capabilities and exposes them via the
Model Context Protocol (MCP).

The implementation uses FastMCP's Streamable HTTP transport to provide
real-time streaming of agent execution steps and results to MCP clients.

Key components:
- FastMCP Server: Creates and configures the MCP server
- DeepSearch Tool: Exposes agent capabilities through a single MCP tool
- Streaming Callbacks: Provides real-time progress updates to clients

Example usage:
    python -m src.agents.servers.run_fastmcp --agent-type codact --port 8100

MCP clients can connect to:
    http://localhost:8100/mcp
"""
from __future__ import annotations

# Standard library imports
import argparse
import logging
import sys
import asyncio

from fastmcp import FastMCP

try:
    from smolagents.gradio_ui import stream_to_gradio
except ImportError:
    stream_to_gradio = None

# Local imports
from src.agents.runtime import agent_runtime
from src.agents.ui_common.gradio_adapter import create_gradio_compatible_agent
from src.core.config.settings import settings

logger = logging.getLogger(__name__)


def build_agent(agent_type: str):
    """Create a DeepSearch agent instance of the given type.

    Args:
        agent_type: The type of agent to create ("react" or "codact")
        Default is "codact"

    Returns:
        A Gradio-compatible agent instance
    """
    if agent_type == "react":
        agent = agent_runtime.create_react_agent()
        agent_name = "DeepSearch ReAct Agent"
        agent_description = (
            "An intelligent agent using the ReAct (Reasoning + Acting) "
            "paradigm for deep web research."
        )
    else:
        agent = agent_runtime.create_codact_agent()
        agent_name = "DeepSearch CodeAct Agent"
        agent_description = (
            "An intelligent agent using the CodeAct paradigm for "
            "deep web research through code execution."
        )

    return create_gradio_compatible_agent(
        agent,
        name=agent_name,
        description=agent_description
    )


def create_deepsearch_tool(agent_type: str = "codact"):
    """Create the DeepSearch MCP tool function.

    This function creates a "DeepSearch" MCP tool that can be
    registered with FastMCP.

    Args:
        agent_type: The type of agent to use ("react" or "codact")
        Default is "codact"

    Returns:
        A function that can be used as an MCP tool
    """
    # Create the agent instance
    agent = build_agent(agent_type)

    # use existing GradioUIAdapter to wrap agent, ensure compatible streaming
    adapted_agent = create_gradio_compatible_agent(
        agent,
        name=f"DeepSearch {agent_type.capitalize()} Agent",
        description="Provide DeepSearchAgent capabilities via MCP"
    )

    async def deepsearch_tool(query: str, ctx=None) -> str:
        """Execute DeepSearchAgent for deep search"""
        if not query or not query.strip():
            return "Please provide a valid search query"

        # initialize notification to client
        if ctx:
            await ctx.info(f"Starting DeepSearch ({agent_type}) "
                           f"query: {query[:50]}...")
            await ctx.report_progress(0, 100)

        try:
            # use final_result to store the final result
            final_result = None

            # handle streaming output mode
            if ctx:
                try:
                    # get generator, but not initialize as async type
                    generator = adapted_agent.run(query, stream=True)

                    # validate return type
                    if not hasattr(generator, "__iter__"):
                        # not generator, handle as single result
                        logger.warning(f"Expected generator but got "
                                       f"{type(generator)}")
                        final_result = str(generator)
                    else:
                        # do synchronous iteration, avoid using await
                        result_content = ""
                        step_count = 0

                        # do synchronous iteration, avoid using await
                        for chunk in generator:
                            # yield control back to event loop
                            # to prevent blocking
                            await asyncio.sleep(0)
                            step_count += 1

                            # update progress
                            if ctx:
                                progress = min(
                                    95,
                                    int((step_count / 25) * 100)
                                )
                                await ctx.report_progress(progress, 100)

                                # send status update every 1 steps
                                if step_count % 1 == 0:
                                    await ctx.info(f"Processing: step "
                                                   f"{step_count}")

                            # content extraction - add type checking
                            # and more logging
                            logger.debug(f"Chunk type: {type(chunk)}")
                            if isinstance(chunk, dict) and "content" in chunk:
                                result_content = chunk.get("content", "")
                            elif isinstance(chunk, str):
                                result_content = chunk

                        # set final result
                        final_result = result_content

                    # send completion progress
                    if ctx:
                        await ctx.report_progress(100, 100)
                        await ctx.info("DeepSearch completed!")

                        # send result preview
                        preview = (final_result[:40] + "..."
                                   if len(final_result) > 40
                                   else final_result)
                        await ctx.info(f"Result: {preview}")

                except Exception as stream_error:
                    logger.error(f"Streaming processing error: "
                                 f"{str(stream_error)}",
                                 exc_info=True)
                    if ctx:
                        await ctx.error(f"Streaming processing error: "
                                        f"{str(stream_error)}")

                    # fallback to non-streaming mode
                    logger.info("Attempting to fallback to non-streaming mode")
                    if ctx:
                        await ctx.info("Switching to non-streaming mode...")

            # non-streaming mode or streaming processing failed
            if final_result is None:
                logger.info("Using non-streaming mode")

                # get result (not using await)
                result_obj = adapted_agent.run(query, stream=False)

                # check if result is an awaitable object
                if hasattr(result_obj, "__await__"):
                    # if it's a coroutine object, use await
                    result = await result_obj
                else:
                    # if it's a normal object (like a dict), use it directly
                    result = result_obj

                # handle different types of results
                if isinstance(result, dict) and "content" in result:
                    final_result = result["content"]
                elif isinstance(result, str):
                    final_result = result
                else:
                    # other types, try to convert to string
                    try:
                        import json
                        if hasattr(result, "__dict__"):
                            final_result = json.dumps(result.__dict__)
                        else:
                            final_result = str(result)
                    except Exception:
                        final_result = str(result)

            # ensure result is not empty
            return final_result or "Execution completed but no valid result " \
                                   "generated"

        except Exception as e:
            error_msg = f"Error executing DeepSearch: {str(e)}"
            logger.exception(error_msg)
            if ctx:
                await ctx.error(error_msg)
                await ctx.report_progress(100, 100)
            return f"Error: {error_msg}"

    return deepsearch_tool


def create_fastmcp_server(agent_type: str) -> FastMCP:
    """Create the FastMCP server with DeepSearch tool.

    Args:
        agent_type: The type of agent to use ("react" or "codact")

    Returns:
        A configured FastMCP server instance
    """
    # Create the server
    agent_type_upper = agent_type.upper()
    server = FastMCP(
        name="DeepSearchAgents",
        description=(
            "DeepSearchAgents is an intelligent research agent system that "
            f"uses {agent_type_upper} architecture to perform comprehensive "
            "web searches and deep analysis."
        ),
        version=settings.VERSION,
    )

    # Register the DeepSearch tool
    deepsearch_tool_func = create_deepsearch_tool(agent_type)
    server.tool(
        name="deepsearch_tool",
        description=(
            "DeepResearchAgent is a CodeAct multi-agent that can use large "
            "numbers of web search & scraping tools with programming Python "
            "code to deeply web search and analyze for research tasks."
        ),
        tags={"category": "search", "complexity": "high"}
    )(deepsearch_tool_func)

    return server


def serve(
    agent_type: str,
    host: str,
    port: int,
    debug: bool = False,
    path: str = "/mcp"
) -> None:
    """Start the FastMCP server.

    Args:
        agent_type: The type of agent to use ("react" or "codact")
        host: The host to bind to
        port: The port to listen on
        debug: Whether to enable debug logging
        path: The URL path for the MCP endpoint
    """
    try:
        # Create the server
        server = create_fastmcp_server(agent_type)

        # Configure and start the server with Streamable HTTP transport
        server_url = f"http://{host}:{port}{path}"
        logger.info(
            f"Starting DeepSearchAgents MCP server (agent_type={agent_type}) "
            f"at {server_url}"
        )

        # Use the standard FastMCP run method which correctly handles lifespan
        # This is more reliable than manually configuring uvicorn
        server.run(
            transport="streamable-http",
            host=host,
            port=port,
            path=path,
            log_level="debug" if debug else "info"
        )
    except ImportError as e:
        logger.error(f"Failed to start FastMCP server: {e}")
        install_msg = (
            "Please install FastMCP v2.3.0+ with "
            "'pip install fastmcp>=2.3.0'"
        )
        logger.error(install_msg)
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error starting FastMCP server: {e}")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Run DeepSearchAgents MCP server"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8100, help="Server port")
    parser.add_argument(
        "--agent-type", choices=["codact", "react"], default="codact",
        help="Agent mode exposed via MCP",
    )
    parser.add_argument(
        "--path", default="/mcp", help="URL path for MCP endpoint"
    )
    parser.add_argument("--debug", action="store_true", help="Debug logging")
    return parser.parse_args()


def main() -> None:
    """Main entry point for the FastMCP server."""
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Start the server
    serve(
        args.agent_type,
        args.host,
        args.port,
        debug=args.debug,
        path=args.path
    )


if __name__ == "__main__":
    main()
