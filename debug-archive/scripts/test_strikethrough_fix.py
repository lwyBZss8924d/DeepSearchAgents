#!/usr/bin/env python3
"""
Playwright test to verify strikethrough marks are removed from tool badges.
Tests that tool badges display clean text without ~~ marks.
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
TEST_QUERY = "write a simple Python function to calculate fibonacci numbers"
WAIT_TIMEOUT = 30000  # 30 seconds

class StrikethroughTester:
    def __init__(self):
        self.console_logs: List[str] = []
        self.strikethrough_found: List[Dict[str, Any]] = []
        self.clean_badges: List[Dict[str, Any]] = []
        self.all_badge_texts: List[str] = []
        
    async def capture_console(self, msg: ConsoleMessage):
        """Capture console messages from the browser."""
        text = msg.text
        self.console_logs.append(text)
        
        # Check for debug logs about tool names
        if "toolName" in text or "tool_name" in text:
            console.print(f"[dim]Console:[/dim] {text[:100]}")
    
    async def check_for_strikethrough(self, page: Page) -> Dict[str, Any]:
        """Check DOM for strikethrough marks in tool badges."""
        result = await page.evaluate("""
            () => {
                const result = {
                    strikethrough_found: [],
                    clean_badges: [],
                    all_texts: [],
                    strikethrough_html: []
                };
                
                // Look for tool badge containers
                const selectors = [
                    '.ds-tool-badge-container',
                    '.ds-tool-badge',
                    '[class*="tool"][class*="badge"]',
                    'button[is-="badge"]',
                    // Check markdown content areas
                    '.ds-agent-message',
                    '.markdown-body',
                    // Fallback selectors
                    'span:has-text("python_interpreter")',
                    'span:has-text("final_answer")',
                    'div:has-text("~~")'
                ];
                
                const elements = new Set();
                
                selectors.forEach(selector => {
                    try {
                        const found = document.querySelectorAll(selector);
                        found.forEach(elem => elements.add(elem));
                    } catch (e) {
                        // Some selectors might not be valid
                    }
                });
                
                // Check for <del> or <s> tags (strikethrough HTML)
                const strikethroughElements = document.querySelectorAll('del, s');
                strikethroughElements.forEach(elem => {
                    const text = elem.textContent || '';
                    const parent = elem.parentElement;
                    result.strikethrough_html.push({
                        text: text,
                        tag: elem.tagName,
                        parentClasses: parent ? Array.from(parent.classList || []) : [],
                        context: parent ? parent.textContent.substring(0, 100) : ''
                    });
                });
                
                // Check each element
                elements.forEach(elem => {
                    const text = elem.textContent || '';
                    const innerHTML = elem.innerHTML || '';
                    
                    if (text.trim()) {
                        result.all_texts.push(text.trim());
                        
                        // Check for strikethrough marks in text
                        if (text.includes('~~')) {
                            result.strikethrough_found.push({
                                text: text,
                                innerHTML: innerHTML.substring(0, 200),
                                classes: Array.from(elem.classList || []),
                                tagName: elem.tagName,
                                selector: elem.className,
                                type: 'raw_marks'
                            });
                        }
                        
                        // Check for HTML strikethrough tags in innerHTML
                        if (innerHTML.includes('<del>') || innerHTML.includes('<s>')) {
                            result.strikethrough_found.push({
                                text: text,
                                innerHTML: innerHTML.substring(0, 200),
                                classes: Array.from(elem.classList || []),
                                tagName: elem.tagName,
                                selector: elem.className,
                                type: 'html_strikethrough'
                            });
                        }
                        
                        // Check for clean tool badges (contain tool names without ~~)
                        const toolNames = ['python_interpreter', 'final_answer', 'search', 'readurl'];
                        toolNames.forEach(tool => {
                            if (text.includes(tool) && !text.includes('~~') && !innerHTML.includes('<del>') && !innerHTML.includes('<s>')) {
                                result.clean_badges.push({
                                    tool: tool,
                                    text: text,
                                    classes: Array.from(elem.classList || [])
                                });
                            }
                        });
                    }
                });
                
                // Also check for any text nodes containing ~~
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while (node = walker.nextNode()) {
                    if (node.textContent && node.textContent.includes('~~')) {
                        const parent = node.parentElement;
                        if (parent && !result.strikethrough_found.some(item => item.text === node.textContent)) {
                            result.strikethrough_found.push({
                                text: node.textContent.trim(),
                                innerHTML: 'TEXT_NODE',
                                classes: Array.from(parent.classList || []),
                                tagName: parent.tagName,
                                selector: parent.className,
                                type: 'text_node'
                            });
                        }
                    }
                }
                
                return result;
            }
        """)
        
        self.strikethrough_found = result['strikethrough_found']
        self.clean_badges = result['clean_badges']
        self.all_badge_texts = result['all_texts']
        
        return result
    
    async def run_test(self):
        """Run the automated strikethrough test."""
        console.print("[bold cyan]🔍 Strikethrough Marks Test Starting...[/bold cyan]\n")
        
        async with async_playwright() as p:
            # Launch browser
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
                await page.wait_for_timeout(2000)
                
                # Take initial screenshot
                await page.screenshot(path="strikethrough_1_initial.png")
                console.print("[green]✓ Initial screenshot saved[/green]")
                
                # Find and fill the input field
                console.print(f"\n[cyan]2. Sending test query: {TEST_QUERY}[/cyan]")
                
                # Try to find the input
                input_selector = 'textarea'
                await page.wait_for_selector(input_selector, timeout=5000)
                await page.fill(input_selector, TEST_QUERY)
                console.print("[green]✓ Query entered[/green]")
                
                # Submit the query
                await page.keyboard.press("Enter")
                console.print("[green]✓ Query submitted[/green]")
                
                # Wait for agent to process
                console.print("\n[cyan]3. Waiting for tool badges to appear...[/cyan]")
                await page.wait_for_timeout(5000)  # Initial wait
                
                # Take processing screenshot
                await page.screenshot(path="strikethrough_2_processing.png")
                
                # Check for strikethrough marks periodically
                max_checks = 10
                found_badges = False
                
                for i in range(max_checks):
                    result = await self.check_for_strikethrough(page)
                    
                    if len(result['strikethrough_found']) > 0 or len(result['clean_badges']) > 0:
                        found_badges = True
                        console.print(f"[yellow]Check {i+1}:[/yellow]")
                        console.print(f"  • Strikethrough found: {len(result['strikethrough_found'])}")
                        console.print(f"  • Clean badges: {len(result['clean_badges'])}")
                        
                        if len(result['strikethrough_found']) > 0:
                            # Found strikethrough - this is the issue!
                            console.print("[red]⚠️  Strikethrough marks detected![/red]")
                            break
                    
                    await page.wait_for_timeout(2000)
                
                # Final check
                final_result = await self.check_for_strikethrough(page)
                
                # Take final screenshot
                await page.screenshot(path="strikethrough_3_final.png")
                console.print("\n[green]✓ Final screenshot saved[/green]")
                
                # Display results
                self.display_results(final_result)
                
                # Return test success/failure
                return len(final_result['strikethrough_found']) == 0
                
            finally:
                # Keep browser open for observation
                console.print("\n[yellow]Browser will close in 5 seconds...[/yellow]")
                await page.wait_for_timeout(5000)
                await browser.close()
    
    def display_results(self, result: Dict[str, Any]):
        """Display test results."""
        console.print("\n[bold cyan]📊 Test Results[/bold cyan]\n")
        
        # Strikethrough HTML elements
        if 'strikethrough_html' in result and result['strikethrough_html']:
            console.print(f"[bold red]1. HTML Strikethrough Elements Found:[/bold red] {len(result['strikethrough_html'])}")
            console.print("[red]❌ CRITICAL: Markdown is rendering ~~ as HTML strikethrough![/red]")
            
            for item in result['strikethrough_html'][:5]:
                console.print(f"  • <{item['tag']}>{item['text']}</{item['tag']}>")
                console.print(f"    Context: {item['context'][:50]}...")
        else:
            console.print("[bold]1. HTML Strikethrough Elements:[/bold] None found")
        
        # Strikethrough marks found
        console.print(f"\n[bold]2. Strikethrough Marks Found:[/bold] {len(result['strikethrough_found'])}")
        
        if result['strikethrough_found']:
            console.print("[red]❌ ISSUE CONFIRMED: Strikethrough marks present![/red]")
            
            # Group by type
            by_type = {}
            for item in result['strikethrough_found']:
                type_name = item.get('type', 'unknown')
                if type_name not in by_type:
                    by_type[type_name] = []
                by_type[type_name].append(item)
            
            for type_name, items in by_type.items():
                console.print(f"\n  [yellow]{type_name}:[/yellow] {len(items)} occurrences")
                for item in items[:2]:  # Show first 2 of each type
                    console.print(f"    • {item['text'][:60]}")
                    if type_name == 'html_strikethrough':
                        console.print(f"      HTML: {item['innerHTML'][:60]}...")
        else:
            console.print("[green]✅ No strikethrough marks found![/green]")
        
        # Clean badges
        console.print(f"\n[bold]2. Clean Tool Badges:[/bold] {len(result['clean_badges'])}")
        
        if result['clean_badges']:
            console.print("[green]✅ Clean badges found[/green]")
            for badge in result['clean_badges'][:3]:
                console.print(f"  • {badge['tool']}: {badge['text'][:40]}")
        else:
            console.print("[yellow]⚠️  No clean badges found[/yellow]")
        
        # All badge texts
        console.print(f"\n[bold]3. All Badge Texts Found:[/bold] {len(self.all_badge_texts)}")
        if self.all_badge_texts:
            console.print("[dim]First 5 texts:[/dim]")
            for text in self.all_badge_texts[:5]:
                console.print(f"  • {text[:60]}")
        
        # Summary
        console.print("\n[bold]4. Summary:[/bold]")
        if len(result['strikethrough_found']) == 0 and len(result['clean_badges']) > 0:
            console.print("[bold green]✅ TEST PASSED! No strikethrough marks, badges display cleanly.[/bold green]")
        elif len(result['strikethrough_found']) > 0:
            console.print("[bold red]❌ TEST FAILED! Strikethrough marks still present.[/bold red]")
            console.print("[yellow]The fix needs to be applied to remove ~~ marks from:[/yellow]")
            console.print("  • Tool names (e.g., ~~python_interpreter~~)")
            console.print("  • Status icons (e.g., ~~✓~~)")
            console.print("  • Tool icons (e.g., ~~💻~~)")
        else:
            console.print("[bold yellow]⚠️  INCONCLUSIVE: No badges found at all.[/bold yellow]")
            console.print("  Make sure the agent is generating tool calls.")
        
        # Screenshots info
        console.print("\n[dim]Screenshots saved:[/dim]")
        console.print("[dim]  - strikethrough_1_initial.png[/dim]")
        console.print("[dim]  - strikethrough_2_processing.png[/dim]")
        console.print("[dim]  - strikethrough_3_final.png[/dim]")


async def main():
    """Main entry point."""
    # Check Playwright
    try:
        import playwright
    except ImportError:
        console.print("[red]❌ Playwright not installed![/red]")
        console.print("\nPlease install it with:")
        console.print("  pip install playwright")
        console.print("  playwright install chromium")
        return False
    
    # Check servers
    console.print("[cyan]Checking if servers are running...[/cyan]")
    
    try:
        import urllib.request
        urllib.request.urlopen(FRONTEND_URL, timeout=2)
        console.print("[green]✓ Frontend is running[/green]")
    except:
        console.print("[red]✗ Frontend is not running[/red]")
        console.print("  Please run: cd frontend && npm run dev")
        return False
    
    # Run the test
    tester = StrikethroughTester()
    try:
        success = await tester.run_test()
        return success
    except Exception as e:
        console.print(f"[red]❌ Test failed with error: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)