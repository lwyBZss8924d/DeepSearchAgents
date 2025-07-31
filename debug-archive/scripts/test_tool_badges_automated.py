#!/usr/bin/env python
"""
Automated frontend-backend test for Tool Call Badges fix verification.
Uses Playwright to control browser and verify tool badges appear correctly.
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
# Query that should trigger CodeAct agent to use multiple tools
TEST_QUERY = "search for information about quantum computing and summarize what you find"
WAIT_TIMEOUT = 40000  # 40 seconds

class ToolBadgeTester:
    def __init__(self):
        self.console_logs: List[str] = []
        self.tool_badge_logs: List[Dict[str, Any]] = []
        self.tool_badges_found: List[Dict[str, Any]] = []
        self.badge_elements_in_dom: List[Dict[str, Any]] = []
        
    async def capture_console(self, msg: ConsoleMessage):
        """Capture console messages from the browser."""
        text = msg.text
        self.console_logs.append(text)
        
        # Check for tool badge logs
        if "[Tool Call Badge]" in text:
            # Try to extract tool name from the log
            tool_match = re.search(r'tool_name:\s*["\']?([^"\']+)["\']?', text)
            if tool_match:
                tool_name = tool_match.group(1)
                self.tool_badge_logs.append({
                    "tool_name": tool_name,
                    "log": text,
                    "timestamp": datetime.now().isoformat()
                })
                console.print(f"[green]✓ Tool badge logged:[/green] {tool_name}")
    
    async def check_for_tool_badges(self, page: Page) -> int:
        """Check DOM for tool badge elements."""
        # Look for badge elements containing tool names
        badges = await page.evaluate("""
            () => {
                const badges = [];
                
                // Look for elements with badge-like classes
                const selectors = [
                    '[class*="rounded-full"][class*="px-3"]',
                    '[class*="inline-flex items-center gap-2"]',
                    '[class*="bg-purple-100"]',  // python_interpreter
                    '[class*="bg-blue-100"]'      // other tools
                ];
                
                const toolNames = [
                    'python_interpreter', 'search_links', 'search_fast', 
                    'read_url', 'chunk_text', 'embed_texts', 'rerank_texts',
                    'wolfram', 'final_answer'
                ];
                
                const foundElements = new Set();
                
                selectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(elem => {
                        const text = elem.textContent.trim();
                        
                        // Check if this element contains any tool name
                        toolNames.forEach(toolName => {
                            if (text.includes(toolName) && !foundElements.has(elem)) {
                                foundElements.add(elem);
                                badges.push({
                                    tool_name: toolName,
                                    full_text: text,
                                    classes: Array.from(elem.classList),
                                    is_purple: elem.classList.toString().includes('purple'),
                                    is_blue: elem.classList.toString().includes('blue'),
                                    html: elem.outerHTML.substring(0, 200)
                                });
                            }
                        });
                    });
                });
                
                return badges;
            }
        """)
        
        self.badge_elements_in_dom = badges
        return len(badges)
    
    async def run_test(self):
        """Run the automated tool badge test."""
        console.print("[bold cyan]🧪 Automated Tool Badge Test Starting...[/bold cyan]\n")
        
        async with async_playwright() as p:
            # Launch browser (set headless=False to see the browser)
            browser = await p.chromium.launch(
                headless=False  # Show browser for debugging
            )
            
            try:
                # Create browser context and page
                context = await browser.new_context()
                page = await context.new_page()
                
                # Set up console log capture
                page.on("console", self.capture_console)
                
                # Navigate to frontend
                console.print(f"[cyan]1. Navigating to {FRONTEND_URL}...[/cyan]")
                await page.goto(FRONTEND_URL)
                await page.wait_for_load_state("networkidle")
                
                # Wait a bit more for React to fully render
                await page.wait_for_timeout(2000)
                
                # Check and change agent type if needed
                console.print("[cyan]Checking agent type...[/cyan]")
                
                # Look for agent type selector
                try:
                    # Try to find agent type dropdown
                    agent_selector = await page.query_selector('select[id*="agent"], button:has-text("CodeAct"), button:has-text("ReAct")')
                    if agent_selector:
                        # Check current selection
                        current_text = await agent_selector.inner_text()
                        if "CodeAct" in current_text:
                            console.print("[yellow]! Current agent is CodeAct, switching to ReAct...[/yellow]")
                            # Click to open dropdown if it's a button
                            await agent_selector.click()
                            await page.wait_for_timeout(500)
                            # Look for ReAct option
                            react_option = await page.query_selector('text="ReAct"')
                            if react_option:
                                await react_option.click()
                                console.print("[green]✓ Switched to ReAct agent[/green]")
                                await page.wait_for_timeout(1000)
                except:
                    console.print("[yellow]! Could not find agent selector, proceeding with default[/yellow]")
                
                # Take initial screenshot
                await page.screenshot(path="test_badges_1_initial.png")
                console.print("[green]✓ Initial screenshot saved[/green]")
                
                # Find and fill the input field
                console.print(f"\n[cyan]2. Sending test query: {TEST_QUERY}[/cyan]")
                
                # Try multiple selectors to find the input
                input_selectors = [
                    'textarea[placeholder*="Ask me anything"]',
                    'textarea[placeholder*="Ask a question"]',
                    'textarea',
                    'input[type="text"]'
                ]
                
                input_found = False
                for selector in input_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=3000)
                        await page.fill(selector, TEST_QUERY)
                        input_found = True
                        console.print(f"[green]✓ Found input with selector: {selector}[/green]")
                        break
                    except:
                        continue
                
                if not input_found:
                    raise Exception("Could not find input field. Check test_badges_1_initial.png")
                
                # Submit the query (Cmd+Enter on Mac, Ctrl+Enter on others)
                await page.keyboard.press("Meta+Enter")
                
                # Wait for agent to start processing
                console.print("[cyan]3. Waiting for agent response...[/cyan]")
                await page.wait_for_timeout(3000)  # Initial wait
                
                # Take screenshot during processing
                await page.screenshot(path="test_badges_2_processing.png")
                
                # Wait for some tool badges to appear
                console.print("[cyan]4. Waiting for tool badges to appear...[/cyan]")
                badge_check_interval = 2000  # Check every 2 seconds
                max_checks = 15  # Up to 30 seconds
                
                for i in range(max_checks):
                    badge_count = await self.check_for_tool_badges(page)
                    if badge_count > 0:
                        console.print(f"[green]✓ Found {badge_count} tool badges[/green]")
                        break
                    await page.wait_for_timeout(badge_check_interval)
                
                # Wait a bit more to ensure all badges are rendered
                await page.wait_for_timeout(3000)
                
                # Final badge check
                final_badge_count = await self.check_for_tool_badges(page)
                
                # Take final screenshot
                await page.screenshot(path="test_badges_3_final.png")
                console.print("[green]✓ Final screenshot saved[/green]")
                
                # Display results
                self.display_results(final_badge_count)
                
            finally:
                # Keep browser open for 5 seconds to observe
                console.print("\n[yellow]Browser will close in 5 seconds...[/yellow]")
                await page.wait_for_timeout(5000)
                await browser.close()
    
    def display_results(self, badge_count: int):
        """Display test results."""
        console.print("\n[bold cyan]📊 Test Results[/bold cyan]\n")
        
        # Tool badge logs from console
        console.print(f"[bold]1. Console Tool Badge Logs:[/bold] {len(self.tool_badge_logs)}")
        if self.tool_badge_logs:
            seen_tools = set()
            for log in self.tool_badge_logs:
                tool_name = log['tool_name']
                if tool_name not in seen_tools:
                    seen_tools.add(tool_name)
                    console.print(f"  • {tool_name}")
            console.print(f"  [dim]Total unique tools logged: {len(seen_tools)}[/dim]")
        else:
            console.print("  [red]❌ No tool badge logs found![/red]")
        
        # Tool badges in DOM
        console.print(f"\n[bold]2. Tool Badges Found in DOM:[/bold] {badge_count}")
        if badge_count > 0:
            console.print("[green]✅ Tool badges present in UI![/green]")
            
            # Group by tool name
            tools_in_dom = {}
            for badge in self.badge_elements_in_dom:
                tool_name = badge['tool_name']
                if tool_name not in tools_in_dom:
                    tools_in_dom[tool_name] = []
                tools_in_dom[tool_name].append(badge)
            
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Tool Name", width=20)
            table.add_column("Badge Type", width=15)
            table.add_column("Full Text", width=40)
            
            for tool_name, badges in tools_in_dom.items():
                for badge in badges:
                    badge_type = "Purple" if badge['is_purple'] else "Blue" if badge['is_blue'] else "Unknown"
                    table.add_row(
                        tool_name,
                        badge_type,
                        badge['full_text'][:40] + "..." if len(badge['full_text']) > 40 else badge['full_text']
                    )
            
            console.print(table)
        else:
            console.print("[red]❌ No tool badges found in DOM![/red]")
        
        # Validation
        console.print("\n[bold]3. Validation:[/bold]")
        
        # Check for python_interpreter
        has_python_console = any(log['tool_name'] == 'python_interpreter' for log in self.tool_badge_logs)
        has_python_dom = any(badge['tool_name'] == 'python_interpreter' for badge in self.badge_elements_in_dom)
        console.print(f"  • python_interpreter logged: {'✓' if has_python_console else '✗'}")
        console.print(f"  • python_interpreter in DOM: {'✓' if has_python_dom else '✗'}")
        
        # Check for extracted tools
        extracted_tools_console = [log['tool_name'] for log in self.tool_badge_logs if log['tool_name'] != 'python_interpreter']
        extracted_tools_dom = [badge['tool_name'] for badge in self.badge_elements_in_dom if badge['tool_name'] != 'python_interpreter']
        
        console.print(f"  • Extracted tools logged: {len(set(extracted_tools_console))} unique")
        console.print(f"  • Extracted tools in DOM: {len(set(extracted_tools_dom))} unique")
        
        if extracted_tools_console:
            console.print(f"    Tools: {', '.join(set(extracted_tools_console))}")
        
        # Summary
        console.print("\n[bold]4. Summary:[/bold]")
        success_criteria = [
            has_python_console and has_python_dom,
            len(extracted_tools_console) > 0,
            len(extracted_tools_dom) > 0,
            badge_count >= 2  # At least python_interpreter + one extracted tool
        ]
        
        if all(success_criteria):
            console.print("[bold green]✅ FIX VERIFIED! Tool badges are working correctly.[/bold green]")
            console.print("  • Backend is sending tool call messages")
            console.print("  • Frontend is logging tool badges") 
            console.print("  • DOM contains multiple tool badges")
            console.print("  • Both python_interpreter and extracted tools are shown")
        elif any(success_criteria):
            console.print("[bold yellow]⚠️  Partial success[/bold yellow]")
            if not (has_python_console and has_python_dom):
                console.print("  • Missing python_interpreter badge")
            if len(extracted_tools_console) == 0:
                console.print("  • No extracted tools logged in console")
            if len(extracted_tools_dom) == 0:
                console.print("  • No extracted tool badges in DOM")
        else:
            console.print("[bold red]❌ FIX NOT WORKING[/bold red]")
            console.print("  • Tool badges are not appearing correctly")
        
        # Additional info
        console.print(f"\n[dim]Total console logs captured: {len(self.console_logs)}[/dim]")
        console.print("[dim]Screenshots saved:[/dim]")
        console.print("[dim]  - test_badges_1_initial.png[/dim]")
        console.print("[dim]  - test_badges_2_processing.png[/dim]")
        console.print("[dim]  - test_badges_3_final.png[/dim]")


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
    
    # Check if servers are running
    console.print("[cyan]Checking if servers are running...[/cyan]")
    
    # Simple check for frontend
    try:
        import urllib.request
        urllib.request.urlopen(FRONTEND_URL, timeout=2)
        console.print("[green]✓ Frontend is running[/green]")
    except:
        console.print("[red]✗ Frontend is not running[/red]")
        console.print("  Please run: cd frontend && npm run dev")
        return
    
    # Run the test
    tester = ToolBadgeTester()
    try:
        await tester.run_test()
    except Exception as e:
        console.print(f"[red]❌ Test failed with error: {e}[/red]")
        console.print("\nMake sure:")
        console.print("  1. Frontend is running on http://localhost:3000")
        console.print("  2. Backend is running on http://localhost:8000")
        console.print("  3. Playwright browsers are installed (run: playwright install)")
        
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())