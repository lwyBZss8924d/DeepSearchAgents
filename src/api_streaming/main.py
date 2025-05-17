#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api_streaming/main.py
# code style: PEP 8
# code-related content: MUST be in English
"""
DeepSearchAgents - Streaming API Service (CURRENTLY DISABLED)

This module contains the main entry point for the streaming API service.
This service is currently disabled and not functional.

NOTE: This file is for reference only and should not be used in production.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Application lifecycle management stub"""
    logger.info("⚠️ THIS SERVICE IS CURRENTLY DISABLED")
    logger.info("Streaming API service initialization would start here")
    yield
    logger.info("Streaming API service shutdown would happen here")


def create_app():
    """Create and configure the FastAPI application for streaming service"""
    app = FastAPI(
        title="DeepSearchAgents Streaming API",
        description="Streaming API service for DeepSearchAgents (DISABLED)",
        version="0.0.1-disabled",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "Content-Type", "Cache-Control", "X-Accel-Buffering",
            "Mcp-Session-Id", "Connection"
        ],
    )

    # Add a simple info route
    @app.get("/")
    async def root():
        return {
            "message": "DeepSearchAgents Streaming API is currently disabled",
            "status": "disabled",
            "version": "0.0.1-disabled"
        }

    return app


app = create_app()


if __name__ == "__main__":
    """Entry point when running directly"""
    logger.warning("⚠️ This service is currently disabled and not functional.")
    logger.warning("It should not be used in production.")

    # Example configuration that would be used if this service was enabled
    host = os.getenv("STREAMING_API_HOST", "0.0.0.0")
    port = int(os.getenv("STREAMING_API_PORT", "8001"))

    # This will never be run in normal operation
    logger.error("NOT starting streaming API server")
    # If enabled in the future, would use uvicorn to run the app
