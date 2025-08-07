#!/usr/bin/env python3
"""Test script to verify the new Bagua badge system with a simpler query"""

import time
from playwright.sync_api import sync_playwright

def test_bagua_badges():
    with sync_playwright() as p:
        print("Starting Playwright browser...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Navigate to the app
        page.goto("http://localhost:3000")
        print("Navigated to app")
        
        # Wait for page to load
        page.wait_for_timeout(2000)
        
        # Type a simpler query that will trigger immediate tool usage
        input_box = page.locator('textarea').first
        input_box.fill("Use python to calculate fibonacci numbers")
        print("Typed query")
        
        # Submit the query
        page.keyboard.press("Enter")
        print("Submitted query")
        
        # Wait longer for complete response
        print("Waiting for agent response...")
        page.wait_for_timeout(30000)  # Wait 30 seconds for full response
        
        print("\n=== BADGE ANALYSIS ===")
        
        # Find all text content to see what's being displayed
        all_text = page.locator('.ds-state-badge, .ds-tool-badge, .ds-step-label').all()
        
        print(f"\nFound {len(all_text)} badge/label elements:")
        for i, element in enumerate(all_text):
            text = element.inner_text()
            if text.strip():  # Only show non-empty text
                print(f"\nElement {i+1}:")
                print(f"  Text: '{text}'")
                
                # Check for our special symbols
                if '☯' in text:
                    print(f"  ✅ Contains Yin Yang (Planning)")
                if any(trigram in text for trigram in ['☰', '☱', '☲', '☳', '☴', '☵', '☶', '☷']):
                    print(f"  ✅ Contains Bagua trigram")
                if '⌘' in text:
                    print(f"  ✅ Contains Command symbol")
                if '~Py' in text:
                    print(f"  ✅ Contains Python code marker")
                if '🀅' in text:
                    print(f"  ✅ Contains Mahjong Dragon (Final Answer)")
        
        # Specifically look for tool badges
        print("\n=== TOOL BADGES ===")
        tool_badges = page.locator('.ds-tool-badge-text').all()
        if tool_badges:
            for i, badge in enumerate(tool_badges):
                text = badge.inner_text()
                print(f"Tool Badge {i+1}: '{text}'")
        else:
            print("No tool badges found with .ds-tool-badge-text class")
            # Try alternate selector
            tool_badges_alt = page.locator('.ds-tool-name').all()
            if tool_badges_alt:
                print("Found badges with .ds-tool-name:")
                for i, badge in enumerate(tool_badges_alt):
                    text = badge.inner_text()
                    print(f"  Badge {i+1}: '{text}'")
        
        # Take multiple screenshots at different scroll positions
        page.screenshot(path="debug-archive/screenshots/bagua_badges_top.png")
        print("\nScreenshot 1 saved (top of page)")
        
        # Scroll down to see more content
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(500)
        page.screenshot(path="debug-archive/screenshots/bagua_badges_middle.png")
        print("Screenshot 2 saved (middle of page)")
        
        # Clean up
        browser.close()
        
        print("\n✅ Test completed! Check the screenshots for visual verification.")
        return True

if __name__ == "__main__":
    test_bagua_badges()