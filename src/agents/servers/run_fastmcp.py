#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run DeepSearchAgents as a FastMCP server exposing a Streamable HTTP API.

This server wraps the existing CodeAct/React agent runtime with the FastMCP
framework so it can be consumed by MCP compatible clients. The implementation
mirrors the streaming behaviour used in ``run_gaia.py`` where
``stream_to_gradio`` yields incremental results.

The ``fastmcp`` package is optional; this module gracefully degrades when it is
not installed so unit tests can still run without the dependency.
"""
from __future__ import annotations

import argparse
import logging
from typing import AsyncGenerator, Dict, Any

from src.agents.runtime import agent_runtime
from src.agents.ui_common.gradio_adapter import create_gradio_compatible_agent

try:  # FastMCP is only available when the optional dependency is installed
    from fastmcp.server import FastMCPServer
    from fastmcp.server.fastapi import create_app
    from smolagents.gradio_ui import stream_to_gradio
except Exception:  # pragma: no cover - optional dependency
    FastMCPServer = None  # type: ignore
    stream_to_gradio = None  # type: ignore
    create_app = None  # type: ignore

logger = logging.getLogger(__name__)


async def agent_stream(task: str, agent) -> AsyncGenerator[Dict[str, Any], None]:
    """Yield agent responses using ``stream_to_gradio`` if available."""
    if stream_to_gradio is None:
        yield {"role": "assistant", "content": "Error: fastmcp not installed"}
        return

    try:
        generator = stream_to_gradio(agent, task=task, reset_agent_memory=False)
        async for chunk in generator:
            yield chunk
    except Exception as exc:  # pragma: no cover - runtime error
        logger.error("Streaming error: %s", exc)
        yield {"role": "assistant", "content": f"Error: {exc}"}


def build_agent(agent_type: str):
    """Create a DeepSearch agent instance of the given type."""
    if agent_type == "react":
        agent = agent_runtime.create_react_agent()
    else:
        agent = agent_runtime.create_codact_agent()
    return create_gradio_compatible_agent(agent)


def serve(agent_type: str, host: str, port: int, debug: bool = False) -> None:
    """Start the FastMCP server."""
    if FastMCPServer is None or create_app is None:
        logger.error("FastMCP package is not available")
        return

    agent = build_agent(agent_type)
    server = FastMCPServer(
        name="DeepSearchAgents",
        description="DeepSearchAgents MCP server",
        version="0.1",
        stream_handler=lambda prompt, *_: agent_stream(prompt, agent),
    )
    app = create_app(server)

    logger.info("Starting FastMCP server at http://%s:%s", host, port)
    server.serve(app, host=host, port=port, log_level="debug" if debug else "info")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DeepSearchAgents MCP server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8100, help="Server port")
    parser.add_argument(
        "--agent-type", choices=["codact", "react"], default="codact",
        help="Agent mode exposed via MCP",
    )
    parser.add_argument("--debug", action="store_true", help="Debug logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    serve(args.agent_type, args.host, args.port, debug=args.debug)


if __name__ == "__main__":
    main()
