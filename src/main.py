#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/main.py
# code style: PEP 8

"""
DeepSearchAgents - FastAPI API Entry

This module provides the main FastAPI entry point with both standard REST API
endpoints and optional FastMCP integration for Streamable HTTP MCP API.
"""

import logging
import argparse
import uvicorn
from contextlib import asynccontextmanager
from src.api.api import create_app
from src.core.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Application lifecycle management - simplified version"""
    # Start logic
    logger.info("FastAPI application startup - initializing components...")

    # Record application startup information
    logger.info(f"Application started, address: "
                f"http://{settings.SERVICE_HOST}:{settings.SERVICE_PORT}")
    logger.info(f"Version: {settings.VERSION}")
    logger.info(f"Agent mode: {settings.DEEPSEARCH_AGENT_MODE}")

    # Startup complete message
    logger.info("FastAPI application startup completed - "
                "ready to handle requests")

    yield

    # Shutdown logic
    logger.info("FastAPI application shutdown - cleaning up resources...")
    logger.info("Application shutdown completed")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="DeepSearchAgents API Server"
    )

    # Server configuration
    parser.add_argument(
        "--host",
        type=str,
        default=settings.SERVICE_HOST,
        help="Host address to bind the server to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.SERVICE_PORT,
        help="Port to bind the server to"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level"
    )

    # FastMCP integration options
    parser.add_argument(
        "--enable-fastmcp",
        action="store_true",
        help="Enable FastMCP integration"
    )
    parser.add_argument(
        "--fastmcp-path",
        type=str,
        default="/mcp-server",
        help="Path to mount the FastMCP server at"
    )
    parser.add_argument(
        "--agent-type",
        type=str,
        default=settings.DEEPSEARCH_AGENT_MODE,
        choices=["react", "codact"],
        help="Agent type to use for FastMCP server"
    )

    return parser.parse_args()


# Create the application with default settings when imported as module
if __name__ == "__main__":
    args = parse_args()
    app = create_app(
        lifespan=lifespan,
        enable_fastmcp=args.enable_fastmcp,
        fastmcp_path=args.fastmcp_path,
        agent_type=args.agent_type
    )
else:
    # When imported by uvicorn, use default settings
    app = create_app(
        lifespan=lifespan,
        enable_fastmcp=False,
        fastmcp_path="/mcp-server",
        agent_type=settings.DEEPSEARCH_AGENT_MODE
    )


if __name__ == "__main__":
    """Entry point when running directly"""
    log_level = args.log_level.lower()

    host = args.host or settings.SERVICE_HOST
    port = args.port or settings.SERVICE_PORT

    # Show server configuration
    server_url = f"http://{host}:{port}"
    logger.info(f"Starting FastAPI server: {server_url}")

    # Show FastMCP integration status
    if args.enable_fastmcp:
        mcp_path = f"{server_url}{args.fastmcp_path}/mcp"
        logger.info(
            f"FastMCP integration enabled at {mcp_path} "
            f"(agent_type: {args.agent_type})"
        )
    else:
        logger.info("FastMCP integration disabled")

    # Run server using Uvicorn - pass the app instance directly
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level
    )
