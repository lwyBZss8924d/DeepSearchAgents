#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/app.py
# code style: PEP 8

"""
DeepSearchAgents - GradioUI Web GUI application entry point
"""

import argparse
import logging
import os
import sys
from src.agents.servers.gradio_patch import apply_gradio_patches
from src.agents.servers.run_gaia import run_gradio_ui
from src.core.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
current_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def parse_args():
    """Parse command line arguments for the application"""
    parser = argparse.ArgumentParser(
        description="DeepSearchAgents - AI Agent for Web Research"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["react", "codact"],
        default=None,
        help="Agent mode (react or codact)"
    )

    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public shareable link"
    )

    parser.add_argument(
        "--server-name",
        type=str,
        default="0.0.0.0",
        help="Hostname to bind server to"
    )

    parser.add_argument(
        "--server-port",
        type=int,
        default=7860,
        help="Port to bind server to"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with additional logging"
    )

    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Temporarily disable proxy settings to start local server"
    )

    return parser.parse_args()


def main():
    """Main application entry point"""
    try:
        args = parse_args()

        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled")

        # Apply patches
        apply_gradio_patches()

        # Display startup information
        print("Starting DeepSearchAgent Gradio UI...")
        print(f"Version: {settings.VERSION}")
        print(f"Mode: {args.mode or settings.DEEPSEARCH_AGENT_MODE}")
        print(f"Server address: http://{args.server_name}:{args.server_port}")
        if args.no_proxy:
            print("Note: Proxy settings are disabled")

        # Launch UI
        run_gradio_ui(
            mode=args.mode,
            share=args.share,
            server_name=args.server_name,
            server_port=args.server_port,
            debug_mode=args.debug,
            no_proxy=args.no_proxy
        )
    except Exception as e:
        logger.error(f"Error running DeepSearchAgent: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
