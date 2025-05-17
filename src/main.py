#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/main.py
# code style: PEP 8

"""
DeepSearchAgents - FastAPI API Entry

This is a simplified version without Streamable HTTP & SSE functionality.
Only basic Agent Run API endpoints are enabled.
"""

import os
import logging
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


app = create_app(lifespan=lifespan)


if __name__ == "__main__":
    """Entry point when running directly"""
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    host_port = f"http://{settings.SERVICE_HOST}:{settings.SERVICE_PORT}"
    logger.info(f"Starting FastAPI server: {host_port}")

    # Run server using Uvicorn
    uvicorn.run(
        "main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        log_level=log_level
    )
