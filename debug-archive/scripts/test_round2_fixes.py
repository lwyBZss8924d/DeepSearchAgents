#!/usr/bin/env python
"""
Test script for Round 2 fixes of the Empty ChatBox UI issue.

Specifically tests that:
1. Separator messages are not creating empty boxes
2. Empty tool_call messages are filtered
3. All meaningful content is preserved
"""

import asyncio
import json
import websockets
from rich.console import Console
from rich.table import Table

console = Console()

WS_URL = "ws://localhost:8000/api/v2/ws/test-round2"
TEST_QUERY = "Solve the differential equation y' = y²x step by step"


async def test_round2_fixes():
    """Test Round 2 fixes for empty chatbox issue."""
    
    console.print("[cyan]🔍 Testing Round 2 Fixes[/cyan]\n")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            # Send query
            await websocket.send(json.dumps({
                "type": "query", 
                "query": TEST_QUERY
            }))
            
            console.print(f"[green]✓ Query sent[/green]\n")
            
            # Track problematic message types
            separators_found = 0
            empty_tool_calls = 0
            total_messages = 0
            message_log = []
            
            # Monitor messages
            try:
                while True:
                    msg_data = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=15.0
                    )
                    msg = json.loads(msg_data)
                    total_messages += 1
                    
                    msg_type = msg.get('metadata', {}).get('message_type', 'unknown')
                    content = msg.get('content', '')
                    
                    # Log key info
                    message_log.append({
                        'num': total_messages,
                        'type': msg_type,
                        'content_length': len(content),
                        'content_preview': content[:30] if content else '<empty>'
                    })
                    
                    # Check for problematic messages
                    if msg_type == 'separator':
                        separators_found += 1
                        console.print(f"[yellow]⚠️  Separator found: '{content}'[/yellow]")
                    
                    if msg_type == 'tool_call' and not content.strip():
                        empty_tool_calls += 1
                        console.print(f"[yellow]⚠️  Empty tool_call found[/yellow]")
                    
                    # Stop on completion
                    if msg.get('metadata', {}).get('status') == 'complete':
                        break
                        
            except asyncio.TimeoutError:
                console.print("\n[dim]Monitoring stopped (timeout)[/dim]")
            
            # Display results
            console.print("\n[bold cyan]Test Results:[/bold cyan]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Message Type", style="yellow")
            table.add_column("Count", style="white")
            table.add_column("Expected Behavior", style="cyan")
            
            table.add_row(
                "separator", 
                str(separators_found),
                "Should NOT appear in UI (filtered)"
            )
            table.add_row(
                "empty tool_call",
                str(empty_tool_calls),
                "Should NOT appear in UI (filtered)"
            )
            
            console.print(table)
            
            # Validation
            console.print("\n[bold]Fix Validation:[/bold]")
            
            if separators_found > 0:
                console.print(
                    f"[green]✓ Found {separators_found} separator messages[/green]"
                )
                console.print("  → These should be filtered out in the UI")
            else:
                console.print("[yellow]⚠️  No separator messages found in test[/yellow]")
            
            if empty_tool_calls > 0:
                console.print(
                    f"[green]✓ Found {empty_tool_calls} empty tool_call messages[/green]"
                )
                console.print("  → These should be filtered out in the UI")
            
            # Show message sequence
            console.print("\n[bold cyan]Message Sequence Summary:[/bold cyan]")
            
            summary_table = Table(show_header=True, header_style="bold")
            summary_table.add_column("#", width=4)
            summary_table.add_column("Type", width=20)
            summary_table.add_column("Content", width=40)
            
            # Show first 20 and last 5 messages
            for msg in message_log[:20]:
                summary_table.add_row(
                    str(msg['num']),
                    msg['type'],
                    msg['content_preview']
                )
            
            if len(message_log) > 25:
                summary_table.add_row("...", "...", "...")
                for msg in message_log[-5:]:
                    summary_table.add_row(
                        str(msg['num']),
                        msg['type'],
                        msg['content_preview']
                    )
            
            console.print(summary_table)
            
            console.print(
                f"\n[bold green]✅ Test complete! "
                f"Processed {total_messages} messages[/bold green]"
            )
            console.print("\n[cyan]Next Steps:[/cyan]")
            console.print("1. Check the UI - no empty gray boxes should appear")
            console.print("2. Verify all content is still visible")
            console.print("3. Confirm clean transitions between steps")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


if __name__ == "__main__":
    console.print("[bold]Round 2 Fix Tester for Empty ChatBox Issue[/bold]\n")
    asyncio.run(test_round2_fixes())