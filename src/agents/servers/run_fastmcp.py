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
- MCP Prompts: Pre-defined prompt templates for common research tasks

Available prompts:
- research_topic: Comprehensive research on a specific topic
- analyze_website: Analyze a website with optional focus areas
- compare_topics: Compare and contrast two topics
- fact_check: Fact-check claims with evidence-based analysis
- expert_analysis: Expert-level analysis from domain perspective
- summarize_search_results: Summarize search results in various formats

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

# Removed unused import stream_to_gradio

# Local imports
from src.agents.runtime import agent_runtime
# Gradio adapter no longer needed for MCP server
from src.core.config.settings import settings

logger = logging.getLogger(__name__)


def build_agent(agent_type: str):
    """Create a DeepSearch agent instance of the given type.

    Args:
        agent_type: The type of agent to create ("react" or "codact")
        Default is "codact"

    Returns:
        A raw agent instance
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

    # Return the raw agent - no longer need Gradio compatibility
    return agent


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
                    generator = agent.run(query, stream=True)

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
                            if isinstance(chunk, str):
                                result_content = chunk
                            elif hasattr(chunk, '__dict__'):
                                # Handle objects with attributes
                                if hasattr(chunk, 'content'):
                                    result_content = chunk.content
                                else:
                                    result_content = str(chunk)
                            else:
                                result_content = str(chunk)

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
                result_obj = agent.run(query, stream=False)

                # check if result is an awaitable object
                if hasattr(result_obj, "__await__"):
                    # if it's a coroutine object, use await
                    result = await result_obj
                else:
                    # if it's a normal object (like a dict), use it directly
                    result = result_obj

                # handle different types of results
                if hasattr(result, 'final_answer'):
                    # It's a RunResult object
                    final_result = result.final_answer
                elif isinstance(result, str):
                    final_result = result
                else:
                    # other types, try to convert to string
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
    server = FastMCP(
        name="DeepSearchAgents",
        version=settings.VERSION,
    )


    # Register prompts for common DeepSearch patterns
    @server.prompt()
    def research_topic(topic: str, depth: str = "comprehensive") -> str:
        """Generate a research prompt for a specific topic.

        Args:
            topic: The topic to research
            depth: Research depth - "quick", "standard", or "comprehensive"

        Returns:
            A formatted research prompt
        """
        depth_instructions = {
            "quick": "Provide a brief overview with key points",
            "standard": "Include main concepts, recent developments, and key sources",
            "comprehensive": "Conduct thorough research including history, current state, future trends, controversies, and expert opinions"
        }
        instruction = depth_instructions.get(depth, depth_instructions["comprehensive"])

        return f"""Please research the topic: "{topic}"

{instruction}

Requirements:
- Use multiple reliable sources
- Include recent information (2023-2025 if available)
- Cite sources with URLs when possible
- Highlight any conflicting viewpoints
- Provide a balanced analysis"""

    @server.prompt()
    def analyze_website(url: str, focus_areas: list[str] = None) -> str:
        """Create a prompt for analyzing a website.

        Args:
            url: The website URL to analyze
            focus_areas: Optional list of specific areas to focus on

        Returns:
            A formatted website analysis prompt
        """
        prompt = f"""Analyze the website: {url}

Please provide:
1. Overview of the site's purpose and content
2. Key information and main offerings
3. Credibility assessment
4. Notable features or unique aspects"""

        if focus_areas:
            prompt += f"\n5. Specific analysis of: {', '.join(focus_areas)}"

        prompt += "\n\nInclude relevant quotes and specific examples from the site."

        return prompt

    @server.prompt()
    def compare_topics(topic1: str, topic2: str, context: str = "") -> str:
        """Generate a comparison prompt for two topics.

        Args:
            topic1: First topic to compare
            topic2: Second topic to compare
            context: Optional context for the comparison

        Returns:
            A formatted comparison prompt
        """
        prompt = f"""Compare and contrast: "{topic1}" vs "{topic2}"""

        if context:
            prompt += f"\n\nContext: {context}"

        prompt += """

Please analyze:
1. Key similarities between the topics
2. Important differences
3. Unique advantages of each
4. Use cases where one might be preferred
5. Current trends and future outlook

Provide specific examples and cite sources where applicable."""

        return prompt

    @server.prompt()
    def fact_check(claim: str, sources: list[str] = None) -> str:
        """Generate a fact-checking prompt.

        Args:
            claim: The claim to fact-check
            sources: Optional list of sources to verify against

        Returns:
            A formatted fact-checking prompt
        """
        prompt = f"""Fact-check this claim: "{claim}"

Please:
1. Verify the accuracy of this statement
2. Find supporting or contradicting evidence
3. Check multiple reliable sources
4. Identify any nuances or context needed
5. Rate the claim (True/False/Partially True/Misleading)"""

        if sources:
            prompt += f"\n\nSpecifically check these sources: {', '.join(sources)}"
        else:
            prompt += "\n\nUse authoritative and recent sources."

        return prompt

    @server.prompt(
        name="expert_analysis",
        description="Request expert-level analysis on a topic with specific domain expertise"
    )
    def expert_analysis(
        topic: str,
        domain: str = "general",
        aspects: list[str] = None
    ) -> str:
        """Generate an expert analysis prompt.

        Args:
            topic: The topic for expert analysis
            domain: Domain of expertise (e.g., "technical", "business", "scientific")
            aspects: Specific aspects to analyze

        Returns:
            A formatted expert analysis prompt
        """
        prompt = f"""Provide an expert-level analysis of: "{topic}"

Domain perspective: {domain}

Analysis should include:
1. Technical/theoretical foundations
2. Current state of the art
3. Key challenges and limitations
4. Future developments and implications
5. Expert opinions and consensus"""

        if aspects:
            prompt += f"\n6. Specific focus on: {', '.join(aspects)}"

        prompt += "\n\nUse academic sources, industry reports, and expert commentary where available."

        return prompt

    @server.prompt()
    def summarize_search_results(
        query: str,
        num_sources: int = 5,
        output_format: str = "detailed"
    ) -> str:
        """Create a prompt for summarizing search results.

        Args:
            query: The original search query
            num_sources: Number of sources to include
            output_format: "brief", "detailed", or "academic"

        Returns:
            A formatted summarization prompt
        """
        format_instructions = {
            "brief": "Provide a concise summary with key points only",
            "detailed": "Include comprehensive information with examples and context",
            "academic": "Format as an academic summary with citations and critical analysis"
        }

        return f"""Search and summarize information about: "{query}"

Requirements:
- Analyze at least {num_sources} different sources
- {format_instructions.get(output_format, format_instructions["detailed"])}
- Synthesize information to avoid redundancy
- Highlight consensus and conflicting views
- Include source URLs for verification

Format the summary with clear sections and bullet points for readability."""

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
