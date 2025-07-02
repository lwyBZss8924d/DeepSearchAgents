#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/agents/ui_common/streaming_formatter.py
# code style: PEP 8

"""
Streaming Console Formatter for CLI
Handles real-time display of streaming agent responses
"""

import time
from typing import Dict, Any, Optional, Union
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

from .console_formatter import ConsoleFormatter
from .constants import (
    THINKING_COLOR, THINKING_EMOJI, COLORS
)

import logging

logger = logging.getLogger(__name__)


class StreamingConsoleFormatter(ConsoleFormatter):
    """Formatter for handling streaming output in CLI
    
    Extends ConsoleFormatter to add streaming-specific functionality
    for displaying real-time agent responses.
    """
    
    def __init__(self, agent_type: str, console: Console, 
                 debug_mode: bool = False):
        """Initialize streaming formatter
        
        Args:
            agent_type: Type of agent ("react" or "codact")
            console: Rich console instance
            debug_mode: Whether to show debug information
        """
        super().__init__(agent_type, console, debug_mode)
        self.streaming_panel = None
        self.stream_content = ""
        self.stream_start_time = None
        self.is_streaming = False
        self._last_displayed_length = 0
        
    def _clean_chunk(self, chunk_str: str) -> str:
        """Clean console formatting from chunk
        
        Args:
            chunk_str: Raw chunk string
            
        Returns:
            Cleaned chunk string
        """
        import re
        
        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        chunk_str = ansi_escape.sub('', chunk_str)
        
        # Remove Rich markup
        rich_markup = re.compile(r'\[/?[a-zA-Z0-9_]+\]')
        chunk_str = rich_markup.sub('', chunk_str)
        
        # Remove box drawing characters
        box_chars = "━╭─│╰┌┐└┘├┤┬┴┼"
        for char in box_chars:
            chunk_str = chunk_str.replace(char, '')
            
        return chunk_str.strip()
        
    def on_stream_start(self):
        """Initialize streaming display"""
        self.stream_start_time = time.time()
        self.stream_content = ""
        self.is_streaming = True
        self._last_displayed_length = 0  # Track what we've already displayed
        
        # Display initial header
        agent_color = COLORS.get(self.agent_type, {}).get('primary', 'cyan')
        self.console.print(
            f"[{agent_color}]{THINKING_EMOJI} Streaming Response Starting..."
            f"[/{agent_color}]"
        )
        logger.debug("Streaming display started")
        
    def on_stream_chunk(self, chunk: Union[str, Any]):
        """Display streaming chunk in real-time
        
        Args:
            chunk: New content chunk from streaming response
        """
        if not self.is_streaming:
            logger.warning("Received stream chunk without active stream")
            return
            
        # Convert chunk to string if needed
        if hasattr(chunk, 'content'):
            chunk_str = chunk.content
        elif hasattr(chunk, 'text'):
            chunk_str = chunk.text
        elif isinstance(chunk, dict) and 'content' in chunk:
            chunk_str = chunk.get('content', '')
        elif isinstance(chunk, dict) and 'text' in chunk:
            chunk_str = chunk.get('text', '')
        else:
            chunk_str = str(chunk)
            
        # Skip None or empty chunks
        if chunk_str is None:
            return
            
        # Skip if chunk looks like a title/status message or console formatting
        skip_patterns = [
            "Streaming Response",
            "Streaming...",
            "[dim]",
            "[/dim]",
            "MultiModelRouter",
            "openai/claude",
            "━━━",  # Box drawing characters
            "╭─",   # Box drawing characters
            "│",    # Box drawing characters
            "╰─",   # Box drawing characters
            "New run"
        ]
        
        for pattern in skip_patterns:
            if pattern in chunk_str:
                logger.debug(f"Skipping formatted chunk containing '{pattern}': {chunk_str[:50]}")
                return
        
        # Clean the chunk
        cleaned_chunk = self._clean_chunk(chunk_str)
        
        # Skip chunks that are entirely whitespace or very short after cleaning
        if len(cleaned_chunk) < 2:
            return
            
        # Append cleaned chunk to content
        self.stream_content += cleaned_chunk
        
        # Just print the new chunk incrementally without re-rendering everything
        # This avoids the repetitive display issue
        self.console.print(cleaned_chunk, end="", markup=False)
            
    def on_stream_end(self):
        """Finalize streaming display"""
        if not self.is_streaming:
            return
            
        self.is_streaming = False
        
        # Calculate elapsed time
        elapsed = 0.0
        if self.stream_start_time:
            elapsed = time.time() - self.stream_start_time
            
        # Add a newline after streaming content
        self.console.print()  # New line after streamed content
        
        # Display completion message
        agent_color = COLORS.get(self.agent_type, {}).get('primary', 'cyan')
        self.console.print(
            f"\n[{agent_color}]✓ Streaming completed in {elapsed:.1f}s[/{agent_color}]"
        )
            
        logger.debug(f"Streaming ended after {elapsed:.1f} seconds")
        
        # Reset state
        self.stream_content = ""
        self.stream_start_time = None
        self._last_displayed_length = 0
        
    def on_stream_error(self, error: str):
        """Handle streaming error
        
        Args:
            error: Error message
        """
        # Stop streaming if active
        if self.is_streaming:
            self.on_stream_end()
            
        # Display error
        self.console.print(f"[red]Streaming error: {error}[/red]")
        logger.error(f"Streaming error: {error}")
        
    def format_streaming_stats(self, stats: Dict[str, Any]) -> Panel:
        """Format statistics for streaming session
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            Formatted panel with statistics
        """
        # Add streaming-specific stats if available
        if 'streaming_chunks' in stats:
            stats['Streaming Chunks'] = stats['streaming_chunks']
            
        if 'streaming_duration' in stats:
            stats['Streaming Duration'] = f"{stats['streaming_duration']:.2f}s"
            
        # Use parent formatter for standard stats
        return super().format_statistics(stats)