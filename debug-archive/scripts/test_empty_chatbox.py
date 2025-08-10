#!/usr/bin/env python
"""
Debug script to identify empty chatbox issue in DeepSearchAgents Web UI.

This script:
1. Connects to the WebSocket API
2. Sends a query that triggers agent steps
3. Logs all messages with their content and metadata
4. Identifies messages with empty or minimal content
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any
import websockets
from rich.console import Console
from rich.table import Table
from rich.pretty import Pretty
from rich.logging import RichHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)
console = Console()

# Configuration
WS_URL = "ws://localhost:8000/api/v2/ws/test-session"
TEST_QUERY = "What's the weather forecast for San Francisco tomorrow?"

class MessageCapture:
    """Captures and analyzes WebSocket messages."""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.empty_messages: List[Dict[str, Any]] = []
        self.problematic_messages: List[Dict[str, Any]] = []
        
    def add_message(self, msg: Dict[str, Any], raw_data: str):
        """Add a message and analyze it."""
        # Add timestamp and raw data
        msg['_timestamp'] = datetime.now().isoformat()
        msg['_raw_length'] = len(raw_data)
        
        self.messages.append(msg)
        
        # Check for empty content
        content = msg.get('content', '')
        if isinstance(content, str) and not content.strip():
            self.empty_messages.append(msg)
            console.print(f"[red]⚠️  Empty content message detected![/red]")
            
        # Check for problematic patterns
        if self._is_problematic(msg):
            self.problematic_messages.append(msg)
            
    def _is_problematic(self, msg: Dict[str, Any]) -> bool:
        """Check if message might cause UI issues."""
        content = msg.get('content', '')
        metadata = msg.get('metadata', {})
        
        # Check for action headers that might be misidentified
        if content == f"**Step {msg.get('step_number', 'N')}**":
            if metadata.get('message_type') == 'action_header':
                return True
                
        # Check for messages with only separators
        if content in ['-----', '---', '_____']:
            return True
            
        return False
        
    def print_summary(self):
        """Print analysis summary."""
        console.print("\n[bold cyan]📊 Message Analysis Summary[/bold cyan]")
        console.print(f"Total messages received: {len(self.messages)}")
        console.print(f"Empty content messages: {len(self.empty_messages)}")
        console.print(f"Problematic messages: {len(self.problematic_messages)}")
        
        if self.empty_messages:
            console.print("\n[bold red]🚨 Empty Content Messages:[/bold red]")
            for i, msg in enumerate(self.empty_messages, 1):
                self._print_message_details(f"Empty #{i}", msg)
                
        if self.problematic_messages:
            console.print("\n[bold yellow]⚠️  Problematic Messages:[/bold yellow]")
            for i, msg in enumerate(self.problematic_messages, 1):
                self._print_message_details(f"Problem #{i}", msg)
                
    def _print_message_details(self, label: str, msg: Dict[str, Any]):
        """Print detailed message information."""
        console.print(f"\n[bold]{label}:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        # Key fields
        table.add_row("Message ID", str(msg.get('message_id', 'N/A')))
        table.add_row("Step Number", str(msg.get('step_number', 'N/A')))
        table.add_row("Content", repr(msg.get('content', '')))
        table.add_row("Content Length", str(len(msg.get('content', ''))))
        
        # Metadata
        metadata = msg.get('metadata', {})
        table.add_row("Component", metadata.get('component', 'N/A'))
        table.add_row("Message Type", metadata.get('message_type', 'N/A'))
        table.add_row("Step Type", metadata.get('step_type', 'N/A'))
        
        console.print(table)
        
    def save_to_file(self, filename: str = "message_capture.json"):
        """Save all messages to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.messages, f, indent=2)
        console.print(f"\n[green]✅ Saved {len(self.messages)} messages to {filename}[/green]")


async def test_websocket():
    """Main test function."""
    capture = MessageCapture()
    
    try:
        console.print(f"[cyan]🔌 Connecting to {WS_URL}...[/cyan]")
        
        async with websockets.connect(WS_URL) as websocket:
            console.print("[green]✅ Connected![/green]")
            
            # Send test query
            query_msg = {
                "type": "query",
                "query": TEST_QUERY
            }
            
            console.print(f"\n[cyan]📤 Sending query: {TEST_QUERY}[/cyan]")
            await websocket.send(json.dumps(query_msg))
            
            # Receive messages
            console.print("\n[cyan]📥 Receiving messages...[/cyan]")
            message_count = 0
            
            while True:
                try:
                    raw_data = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    message_count += 1
                    
                    # Parse message
                    try:
                        msg = json.loads(raw_data)
                        
                        # Log message info
                        content_preview = msg.get('content', '')[:50]
                        if len(msg.get('content', '')) > 50:
                            content_preview += '...'
                            
                        msg_type = msg.get('metadata', {}).get('message_type', 'unknown')
                        console.print(
                            f"[dim]Message {message_count}:[/dim] "
                            f"[yellow]{msg_type}[/yellow] - "
                            f"[white]{repr(content_preview)}[/white]"
                        )
                        
                        # Capture message
                        capture.add_message(msg, raw_data)
                        
                        # Check for completion
                        if msg.get('metadata', {}).get('status') == 'complete':
                            console.print("\n[green]✅ Agent completed![/green]")
                            break
                            
                    except json.JSONDecodeError as e:
                        console.print(f"[red]❌ Failed to parse message: {e}[/red]")
                        console.print(f"[dim]Raw data: {raw_data[:100]}...[/dim]")
                        
                except asyncio.TimeoutError:
                    console.print("\n[yellow]⏱️  Timeout waiting for messages[/yellow]")
                    break
                    
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        return
        
    # Print analysis
    capture.print_summary()
    
    # Save messages
    capture.save_to_file("empty_chatbox_debug.json")
    
    # Print message sequence
    console.print("\n[bold cyan]📜 Message Sequence:[/bold cyan]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", style="yellow", width=20)
    table.add_column("Content", style="white", width=50)
    table.add_column("Empty?", style="red", width=7)
    
    for i, msg in enumerate(capture.messages, 1):
        msg_type = msg.get('metadata', {}).get('message_type', 'unknown')
        content = msg.get('content', '')
        is_empty = "YES" if not content.strip() else "NO"
        content_preview = repr(content[:40] + '...' if len(content) > 40 else content)
        
        table.add_row(str(i), msg_type, content_preview, is_empty)
        
    console.print(table)


if __name__ == "__main__":
    console.print("[bold cyan]🔍 DeepSearchAgents Empty ChatBox Debugger[/bold cyan]\n")
    asyncio.run(test_websocket())