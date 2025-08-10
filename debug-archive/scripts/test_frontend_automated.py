#!/usr/bin/env python
"""
Automated frontend test for Empty ChatBox fix verification.
Uses Playwright to control browser and verify fixes work.
"""

import asyncio
import json
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page, ConsoleMessage
from rich.console import Console
from rich.table import Table
from datetime import datetime

console = Console()

# Test configuration
FRONTEND_URL = "http://localhost:3000"
TEST_QUERY = "What's the weather forecast for San Francisco tomorrow?"
WAIT_TIMEOUT = 30000  # 30 seconds


class FrontendTester:
    def __init__(self):
        self.console_logs: List[str] = []
        self.filtering_logs: List[str] = []
        self.empty_boxes_found: List[Dict[str, Any]] = []
        
    async def capture_console(self, msg: ConsoleMessage):
        """Capture console messages from the browser."""
        text = msg.text
        self.console_logs.append(text)
        
        # Check for our specific filtering logs
        if "Filtering out separator" in text or "Filtering out empty" in text:
            self.filtering_logs.append(text)
            console.print(f"[green]✓ Captured:[/green] {text}")
    
    async def check_for_empty_boxes(self, page: Page) -> int:
        """Check DOM for empty message boxes."""
        # Look for message containers with bg-muted class
        empty_boxes = await page.evaluate("""
            () => {
                const boxes = [];
                const messages = document.querySelectorAll('.bg-muted');
                
                messages.forEach((elem, index) => {
                    const text = elem.textContent.trim();
                    const hasHR = elem.querySelector('hr') !== null;
                    const innerHTML = elem.innerHTML.trim();
                    
                    // Check if it's empty or just has a horizontal rule
                    if (text === '' || text === '-----' || hasHR || innerHTML === '<hr>') {
                        boxes.push({
                            index: index,
                            text: text,
                            hasHR: hasHR,
                            innerHTML: innerHTML.substring(0, 100),
                            classList: Array.from(elem.classList)
                        });
                    }
                });
                
                return boxes;
            }
        """)
        
        self.empty_boxes_found = empty_boxes
        return len(empty_boxes)
    
    async def run_test(self):
        """Run the automated frontend test."""
        console.print("[bold cyan]🤖 Automated Frontend Test Starting...[/bold cyan]\n")
        
        async with async_playwright() as p:
            # Launch browser (headless by default)
            browser = await p.chromium.launch(
                headless=True  # Set to False to see the browser
            )
            
            try:
                # Create browser context and page
                context = await browser.new_context()
                page = await context.new_page()
                
                # Set up console log capture
                page.on("console", self.capture_console)
                
                # Navigate to frontend
                console.print(f"[cyan]Navigating to {FRONTEND_URL}...[/cyan]")
                await page.goto(FRONTEND_URL)
                await page.wait_for_load_state("networkidle")
                
                # Take initial screenshot
                await page.screenshot(path="debug-before-query.png")
                console.print("[green]✓ Initial screenshot saved[/green]")
                
                # Find and fill the input field
                console.print(f"\n[cyan]Sending test query: {TEST_QUERY}[/cyan]")
                
                # Wait for the input to be visible and type the query
                input_selector = 'textarea[placeholder*="Ask a question"], input[placeholder*="Ask a question"]'
                await page.wait_for_selector(input_selector, timeout=10000)
                await page.fill(input_selector, TEST_QUERY)
                
                # Submit the query (press Enter or click send button)
                await page.press(input_selector, "Enter")
                
                # Wait for agent to start processing
                console.print("[cyan]Waiting for agent response...[/cyan]")
                await page.wait_for_timeout(2000)  # Initial wait
                
                # Wait for completion (look for Final Answer or specific indicators)
                try:
                    await page.wait_for_selector(
                        'text=/Final Answer|Forecast|Weather/',
                        timeout=WAIT_TIMEOUT
                    )
                    console.print("[green]✓ Agent completed response[/green]")
                except:
                    console.print("[yellow]⚠️  Timeout waiting for completion[/yellow]")
                
                # Check for empty boxes
                console.print("\n[cyan]Checking for empty message boxes...[/cyan]")
                empty_count = await self.check_for_empty_boxes(page)
                
                # Take final screenshot
                await page.screenshot(path="debug-after-query.png")
                console.print("[green]✓ Final screenshot saved[/green]")
                
                # Display results
                self.display_results(empty_count)
                
            finally:
                await browser.close()
    
    def display_results(self, empty_count: int):
        """Display test results."""
        console.print("\n[bold cyan]📊 Test Results[/bold cyan]\n")
        
        # Filtering logs
        console.print(f"[bold]Console Filtering Logs:[/bold] {len(self.filtering_logs)}")
        if self.filtering_logs:
            for log in self.filtering_logs[:10]:  # Show first 10
                console.print(f"  • {log}")
            if len(self.filtering_logs) > 10:
                console.print(f"  ... and {len(self.filtering_logs) - 10} more")
        else:
            console.print("  [red]❌ No filtering logs found![/red]")
        
        # Empty boxes
        console.print(f"\n[bold]Empty Message Boxes Found:[/bold] {empty_count}")
        if empty_count > 0:
            console.print("[red]❌ Empty boxes still present![/red]")
            
            table = Table(show_header=True, header_style="bold red")
            table.add_column("Index", width=8)
            table.add_column("Content", width=20)
            table.add_column("Has HR", width=10)
            table.add_column("Classes", width=40)
            
            for box in self.empty_boxes_found[:5]:  # Show first 5
                table.add_row(
                    str(box['index']),
                    box['text'] or "<empty>",
                    "Yes" if box['hasHR'] else "No",
                    ", ".join(box['classList'][:3])
                )
            
            console.print(table)
        else:
            console.print("[green]✅ No empty boxes found![/green]")
        
        # Summary
        console.print("\n[bold]Summary:[/bold]")
        if len(self.filtering_logs) > 0 and empty_count == 0:
            console.print("[bold green]✅ FIX VERIFIED! Filtering is working correctly.[/bold green]")
        elif len(self.filtering_logs) > 0 and empty_count > 0:
            console.print("[bold yellow]⚠️  Partial success: Filtering logs present but empty boxes remain[/bold yellow]")
        else:
            console.print("[bold red]❌ FIX NOT WORKING: No filtering occurring[/bold red]")
        
        # Additional info
        console.print(f"\n[dim]Total console logs captured: {len(self.console_logs)}[/dim]")
        console.print("[dim]Screenshots saved: debug-before-query.png, debug-after-query.png[/dim]")


async def main():
    """Main entry point."""
    # First check if Playwright is installed
    try:
        import playwright
    except ImportError:
        console.print("[red]❌ Playwright not installed![/red]")
        console.print("\nPlease install it with:")
        console.print("  pip install playwright")
        console.print("  playwright install chromium")
        return
    
    tester = FrontendTester()
    try:
        await tester.run_test()
    except Exception as e:
        console.print(f"[red]❌ Test failed with error: {e}[/red]")
        console.print("\nMake sure:")
        console.print("  1. Frontend is running on http://localhost:3000")
        console.print("  2. Backend is running on http://localhost:8000")
        console.print("  3. Playwright browsers are installed (run: playwright install)")


if __name__ == "__main__":
    asyncio.run(main())