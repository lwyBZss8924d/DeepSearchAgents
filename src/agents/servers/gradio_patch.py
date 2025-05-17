#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/servers/gradio_patch.py
# code style: PEP 8

"""
Provide compatibility patches for Gradio
"""

import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def dummy_sidebar(*args, **kwargs):
    """Dummy sidebar context manager that does nothing"""
    yield None


def apply_gradio_patches():
    """Apply patches to fix Gradio compatibility issues

    This function checks for Gradio version compatibility issues
    and applies necessary patches
    """
    try:
        import gradio as gr
        if not hasattr(gr, "Sidebar"):
            logger.info("Gradio.Sidebar not found - applying patch")
            setattr(gr, "Sidebar", dummy_sidebar)

        # Ensure ChatMessage is properly registered for type="messages" Chatbot
        try:
            # Check if ChatMessage exists and is properly registered
            if hasattr(gr, "ChatMessage"):
                logger.info(
                    "Gradio.ChatMessage found - checking compatibility"
                )

                # Test basic ChatMessage functionality
                test_msg = gr.ChatMessage(role="user", content="test")
                if (not hasattr(test_msg, "role") or
                        not hasattr(test_msg, "content")):
                    logger.warning(
                        "ChatMessage missing attributes - applying fix"
                    )

                    # Fix ChatMessage class if needed
                    original_init = gr.ChatMessage.__init__

                    def fixed_init(self, role, content, *args, **kwargs):
                        original_init(self, role, content, *args, **kwargs)
                        # Ensure required attributes exist
                        self.role = role
                        self.content = content
                        if "metadata" not in kwargs:
                            self.metadata = {"status": "done"}

                    gr.ChatMessage.__init__ = fixed_init
                    logger.info(
                        "Applied ChatMessage compatibility patch"
                    )
            else:
                logger.warning(
                    "Gradio.ChatMessage not found - "
                    "UI may not render correctly"
                )
        except Exception as e:
            logger.warning(
                f"Error applying ChatMessage patch: {e}"
            )

    except ImportError:
        logger.warning("Gradio module not found, cannot apply patches")
        return False

    return True
