#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run the API with instrumentation applied.

This is a standalone script to start the API with detailed logging.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Apply instrumentation BEFORE importing anything else
print("🔧 Applying instrumentation...")
from tests.streaming.instrument_backend import apply_all_instrumentation
timing_tracker = apply_all_instrumentation()

# Now import and configure the API
import logging
import uvicorn

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s.%(msecs)03d] [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

# Import the app
from src.api.v2.main import app

if __name__ == "__main__":
    print("\n🚀 Starting instrumented API server...")
    print("=" * 80)
    print("Instrumentation is active - all streaming operations will be logged")
    print("=" * 80)
    
    # Run with detailed logging
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",  # More detailed logging
        ws_ping_interval=20,
        ws_ping_timeout=60,
        ws_max_size=16777216,
        ws_per_message_deflate=False,
        # Add access log for debugging
        access_log=True
    )