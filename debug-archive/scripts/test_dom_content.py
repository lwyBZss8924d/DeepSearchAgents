#!/usr/bin/env python3
"""
Test to check actual DOM content of tool badges.
This will help us see what's actually being rendered.
"""

import asyncio
from playwright.async_api import async_playwright
from rich.console import Console

console = Console()

async def check_dom_content():
    """Check the actual DOM content of tool badges"""
    console.print("[bold cyan]DOM Content Inspector[/bold cyan]\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        try:
            page = await browser.new_page()
            
            # Add console listener
            page.on("console", lambda msg: console.print(f"[dim]Browser:[/dim] {msg.text[:100]}"))
            
            # Navigate to frontend
            console.print("1. Navigating to http://localhost:3000...")
            await page.goto("http://localhost:3000")
            await page.wait_for_timeout(2000)
            
            # Send a query to trigger tool badges
            console.print("2. Sending test query...")
            await page.fill('textarea', 'write a simple Python hello world')
            await page.keyboard.press("Enter")
            
            # Wait for badges to appear
            console.print("3. Waiting for tool badges...")
            await page.wait_for_timeout(8000)
            
            # Inspect DOM for tool badges
            console.print("\n[bold]4. Inspecting DOM content:[/bold]")
            
            result = await page.evaluate("""
                () => {
                    const results = {
                        badges: [],
                        rawHTML: [],
                        computedStyles: []
                    };
                    
                    // Find all tool badge elements
                    const selectors = [
                        '.ds-tool-badge',
                        '[agent-badge-="tool"]',
                        'button[is-="badge"]',
                        '.ds-tool-badge-container'
                    ];
                    
                    selectors.forEach(selector => {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(elem => {
                            const textContent = elem.textContent || '';
                            const innerHTML = elem.innerHTML || '';
                            
                            // Get computed styles
                            const styles = window.getComputedStyle(elem);
                            const textDecoration = styles.textDecoration;
                            const textDecorationLine = styles.textDecorationLine;
                            
                            results.badges.push({
                                selector: selector,
                                textContent: textContent,
                                innerHTML: innerHTML.substring(0, 200),
                                hasStrikethrough: textContent.includes('~~'),
                                textDecoration: textDecoration,
                                textDecorationLine: textDecorationLine,
                                classes: Array.from(elem.classList || [])
                            });
                            
                            // Check children for del or s tags
                            const delTags = elem.querySelectorAll('del, s');
                            if (delTags.length > 0) {
                                results.badges[results.badges.length - 1].hasDelTags = true;
                                results.badges[results.badges.length - 1].delContent = Array.from(delTags).map(d => d.textContent);
                            }
                        });
                    });
                    
                    // Also check for any del or s tags globally
                    document.querySelectorAll('del, s').forEach(elem => {
                        results.rawHTML.push({
                            tag: elem.tagName,
                            content: elem.textContent,
                            parent: elem.parentElement?.className || 'no-class'
                        });
                    });
                    
                    return results;
                }
            """)
            
            # Display results
            console.print("\n[bold]Badge Elements Found:[/bold]")
            for badge in result['badges']:
                console.print(f"\n[yellow]Selector:[/yellow] {badge['selector']}")
                console.print(f"  Text: {badge['textContent']}")
                console.print(f"  Has ~~: {badge.get('hasStrikethrough', False)}")
                console.print(f"  Text-decoration: {badge.get('textDecoration', 'none')}")
                console.print(f"  Has <del> tags: {badge.get('hasDelTags', False)}")
                if badge.get('delContent'):
                    console.print(f"  Del content: {badge['delContent']}")
                console.print(f"  Classes: {', '.join(badge.get('classes', []))}")
            
            if result['rawHTML']:
                console.print("\n[bold red]Strikethrough HTML Elements Found:[/bold red]")
                for elem in result['rawHTML']:
                    console.print(f"  <{elem['tag']}>{elem['content']}</{elem['tag']}> in {elem['parent']}")
            
            # Take screenshot
            await page.screenshot(path="dom_inspection.png")
            console.print("\n[green]Screenshot saved as dom_inspection.png[/green]")
            
        finally:
            console.print("\nBrowser will close in 5 seconds...")
            await page.wait_for_timeout(5000)
            await browser.close()

async def main():
    try:
        await check_dom_content()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())