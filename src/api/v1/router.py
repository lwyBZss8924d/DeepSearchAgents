#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/api/v1/router.py
# code style: PEP 8

"""
DeepSearchAgents - API Router

This is a simplified version without Streamable HTTP & SSE functionality.
Only basic endpoints are enabled.
"""

from fastapi import APIRouter

from .endpoints import agent, health

# Create API v1 version routes
api_router = APIRouter(prefix="/api/v1")

# Include endpoints routes
api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent.router, prefix="/agents", tags=["agents"])
