#!/usr/bin/env python
"""
Test multiple scenarios to ensure the empty chatbox fix works in all cases.
"""

import asyncio
from test_frontend_automated import FrontendTester
from rich.console import Console

console = Console()

TEST_SCENARIOS = [
    {
        "name": "Simple Query",
        "query": "What is 2+2?",
        "description": "Tests basic single-step response"
    },
    {
        "name": "Multi-Step Query", 
        "query": "Solve the equation x² + 3x - 4 = 0 step by step",
        "description": "Tests multiple action steps with separators"
    },
    {
        "name": "Search Query",
        "query": "What's the latest news about AI?",
        "description": "Tests queries that use search tools"
    }
]


async def run_all_scenarios():
    """Run all test scenarios."""
    console.print("[bold cyan]🧪 Running Multiple Test Scenarios[/bold cyan]\n")
    
    results = []
    
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        console.print(f"\n[bold]Scenario {i}/{len(TEST_SCENARIOS)}: {scenario['name']}[/bold]")
        console.print(f"Query: {scenario['query']}")
        console.print(f"Description: {scenario['description']}")
        
        tester = FrontendTester()
        tester.TEST_QUERY = scenario['query']
        
        try:
            # Run the test (simplified version)
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Set up console capture
                page.on("console", tester.capture_console)
                
                # Navigate and send query
                await page.goto("http://localhost:3000")
                await page.wait_for_load_state("networkidle")
                
                # Send query
                input_selector = 'textarea[placeholder*="Ask a question"], input[placeholder*="Ask a question"]'
                await page.wait_for_selector(input_selector, timeout=10000)
                await page.fill(input_selector, scenario['query'])
                await page.press(input_selector, "Enter")
                
                # Wait for response
                await page.wait_for_timeout(10000)  # 10 seconds
                
                # Check for empty boxes
                empty_count = await tester.check_for_empty_boxes(page)
                
                # Record results
                results.append({
                    "scenario": scenario['name'],
                    "empty_boxes": empty_count,
                    "filtering_logs": len(tester.filtering_logs),
                    "success": empty_count == 0 and len(tester.filtering_logs) > 0
                })
                
                await browser.close()
                
                # Quick result
                if results[-1]['success']:
                    console.print(f"[green]✅ Success: {tester.filtering_logs} filters, 0 empty boxes[/green]")
                else:
                    console.print(f"[red]❌ Failed: {empty_count} empty boxes found[/red]")
                    
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            results.append({
                "scenario": scenario['name'],
                "error": str(e),
                "success": False
            })
    
    # Summary
    console.print("\n[bold cyan]📊 Overall Results Summary[/bold cyan]")
    
    success_count = sum(1 for r in results if r.get('success', False))
    console.print(f"\nScenarios passed: {success_count}/{len(TEST_SCENARIOS)}")
    
    for result in results:
        status = "[green]✅[/green]" if result.get('success') else "[red]❌[/red]"
        console.print(f"{status} {result['scenario']}")
        if 'error' in result:
            console.print(f"   Error: {result['error']}")
        else:
            console.print(f"   Empty boxes: {result['empty_boxes']}, Filters: {result['filtering_logs']}")
    
    if success_count == len(TEST_SCENARIOS):
        console.print("\n[bold green]🎉 ALL TESTS PASSED! The fix is working correctly.[/bold green]")
    else:
        console.print("\n[bold red]⚠️  Some tests failed. Further investigation needed.[/bold red]")


if __name__ == "__main__":
    asyncio.run(run_all_scenarios())