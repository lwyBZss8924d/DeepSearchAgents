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
import asyncio
import logging
import sys

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

    # Define the tool function that will be exposed via MCP
    # Use a simpler type annotation approach to avoid Optional
    async def deepsearch_tool(query: str, ctx=None) -> str:
        """Execute a deep search using DeepSearchAgents.

        This tool uses CodeAct or ReAct agent to perform a comprehensive
        web search and analysis for your query.

        Args:
            query: The search query or question to research
            ctx: MCP context for progress reporting and logging

        Returns:
            str: Detailed research findings and analysis results
        """
        if not query or not query.strip():
            return "Please provide a valid search query."

        query_preview = query[:50] + "..." if len(query) > 50 else query

        # Initialize with proper logging
        if ctx:
            await ctx.info(
                f"Starting DeepSearch ({agent_type}) "
                f"for query: {query_preview}"
            )
            await ctx.report_progress(0, 100)
        else:
            logger.info(
                f"Starting DeepSearch ({agent_type}) "
                f"for query: {query_preview}"
            )

        try:
            # Initialize tracking variables
            steps_processed = 0
            max_expected_steps = 25  # Expected maximum steps
            final_result = None
            has_streaming_error = False

            # Create a custom step callback that reports to MCP ctx
            async def mcp_step_callback(step_data):
                nonlocal steps_processed, final_result

                # Track step count
                steps_processed += 1

                # Determine step type for better logging
                step_type = type(step_data).__name__
                step_info = {
                    "step_number": steps_processed,
                    "step_type": step_type
                }

                # Extract relevant information based on step type
                if (
                    step_type == "CodeExecutionStep"
                    and hasattr(step_data, "code")
                ):
                    # For code execution, show code length and output preview
                    code_lines = len(step_data.code.split("\n"))
                    step_info["code_lines"] = code_lines

                    # Get output preview if available
                    if hasattr(step_data, "output") and step_data.output:
                        output_preview = step_data.output
                        if len(output_preview) > 100:
                            output_preview = output_preview[:100] + "..."
                        step_info["output_preview"] = output_preview

                elif (
                    step_type == "FinalAnswerStep"
                    and hasattr(step_data, "final_answer")
                ):
                    # Capture final answer for later use
                    final_result = step_data.final_answer
                    step_info["final_answer"] = "✅ Generated"

                elif (
                    step_type == "ToolCallStep"
                    and hasattr(step_data, "name")
                ):
                    # For tool calls, show which tool was used
                    step_info["tool"] = step_data.name

                    # Add tool input preview
                    if (
                        hasattr(step_data, "inputs")
                        and step_data.inputs
                    ):
                        input_str = str(step_data.inputs)
                        if len(input_str) > 100:
                            input_str = input_str[:100] + "..."
                        step_info["inputs_preview"] = input_str

                # Report progress directly via await - no need for create_task
                if ctx:
                    # Calculate progress percentage - scale to 0-95%
                    progress = min(
                        95,
                        int((steps_processed / max_expected_steps) * 100)
                    )

                    # Send both progress update and step info
                    await ctx.report_progress(progress, 100)
                    step_msg = (
                        f"Step {steps_processed}: {step_type} - {step_info}"
                    )
                    await ctx.info(step_msg)

                # Return the step data to continue the agent's execution
                return step_data

            # Setup synchronous wrapper for the async step callback
            def sync_step_callback(step_data):
                # Create a wrapper function that calls the async function
                # but doesn't wait for it to complete
                if ctx:
                    # Create task in the current event loop
                    asyncio.create_task(mcp_step_callback(step_data))
                return step_data

            # Add our step callback to the agent if possible
            if (
                hasattr(agent, "step_callbacks")
                and isinstance(agent.step_callbacks, list)
            ):
                agent.step_callbacks.append(sync_step_callback)
            elif (
                hasattr(agent, "agent")
                and hasattr(agent.agent, "step_callbacks")
            ):
                if isinstance(agent.agent.step_callbacks, list):
                    agent.agent.step_callbacks.append(sync_step_callback)

            # Run agent using stream_to_gradio for streaming
            if ctx:
                await ctx.info(
                    "Starting agent execution, this may take some time..."
                )

            # If stream_to_gradio is available, use it for streaming execution
            if stream_to_gradio is not None:
                result_content = ""
                chunks_processed = 0

                try:
                    if ctx:
                        await ctx.info("Running with streamed output...")

                    # Create generator with stream_to_gradio
                    generator = stream_to_gradio(
                        agent,
                        task=query,
                        reset_agent_memory=False
                    )

                    # Process stream in simple batches
                    for chunk in generator:
                        chunks_processed += 1

                        # Process chunk content into result_content
                        if isinstance(chunk, dict) and "content" in chunk:
                            content = chunk.get("content", "")
                            if content and isinstance(content, str):
                                result_content = content
                        elif isinstance(chunk, str):
                            result_content = chunk

                        # Send intermittent progress updates to client
                        if ctx and chunks_processed % 10 == 0:
                            progress = min(
                                95,
                                10 + int((chunks_processed / 100) * 85)
                            )
                            await ctx.report_progress(progress, 100)

                            # Only send content updates occasionally
                            # to avoid flooding
                            if chunks_processed % 30 == 0:
                                preview = (
                                    result_content[:50] + "..."
                                    if len(result_content) > 50
                                    else result_content
                                )
                                await ctx.info(
                                    f"Processing chunk {chunks_processed}, "
                                    f"content preview: {preview}"
                                )
                    # Successfully completed processing all chunks
                    if ctx:
                        await ctx.info(
                            f"Processed {chunks_processed} chunks, "
                            f"finalizing result..."
                        )
                        await ctx.report_progress(98, 100)

                    # If we have a final result from the callback, use it
                    if final_result is not None:
                        logger.debug(
                            "Using final result from FinalAnswerStep callback"
                        )
                        result_content = final_result

                    # Process string result for JSON if needed
                    if result_content and isinstance(result_content, str):
                        if (
                            result_content.strip().startswith("{")
                            and result_content.strip().endswith("}")
                        ):
                            try:
                                import json
                                json_obj = json.loads(result_content)
                                if (
                                    isinstance(json_obj, dict)
                                    and "content" in json_obj
                                ):
                                    final_result = json_obj["content"]
                                else:
                                    final_result = result_content
                            except Exception:
                                # If JSON parsing fails, use the raw content
                                final_result = result_content
                        else:
                            final_result = result_content
                    else:
                        final_result = (
                            result_content or
                            "DeepSearch completed "
                            "but no result content was generated."
                        )

                except Exception as stream_error:
                    has_streaming_error = True
                    logger.error(
                        f"Error in streaming execution: {stream_error}",
                        exc_info=True
                    )
                    if ctx:
                        await ctx.error(
                            f"Error in streaming: {str(stream_error)}"
                        )
                    final_result = (
                        f"Error during streaming: {str(stream_error)}"
                    )

            # Fallback to non-streaming mode if streaming
            # failed or not available
            if not stream_to_gradio or has_streaming_error:
                # Non-streaming fallback mode
                if ctx:
                    await ctx.info("Using non-streaming mode")
                try:
                    # Execute agent run directly
                    result = await agent.run(query, stream=False)

                    # Process result
                    if isinstance(result, dict) and "content" in result:
                        final_result = result["content"]
                    else:
                        final_result = result
                except Exception as run_ex:
                    logger.error(
                        f"Error in non-streaming execution: {run_ex}",
                        exc_info=True
                    )
                    if ctx:
                        await ctx.error(
                            f"Error in non-streaming execution: {str(run_ex)}"
                        )
                    final_result = (
                        f"Error executing DeepSearch: {str(run_ex)}"
                    )

            # Complete with the final result
            if ctx:
                await ctx.report_progress(100, 100)
                await ctx.info("DeepSearch completed! Returning results...")

            # Return the final result
            return final_result or "No result was generated."

        except Exception as e:
            # Catch-all exception handler
            error_msg = f"Error executing DeepSearch: {str(e)}"
            logger.exception(error_msg)
            if ctx:
                await ctx.error(error_msg)
                await ctx.report_progress(100, 100)  # Mark as complete
            return error_msg

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
            "Execute a deep search across the web for a given query, "
            "gathering and analyzing information from multiple sources."
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
