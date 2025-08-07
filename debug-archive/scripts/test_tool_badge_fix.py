#!/usr/bin/env python3
"""Test script to verify tool badge strikethrough fix"""

import time
from playwright.sync_api import sync_playwright

def test_tool_badge_fix():
    with sync_playwright() as p:
        print("Starting Playwright browser...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Navigate to the app
        page.goto("http://localhost:3000")
        print("Navigated to app")
        
        # Wait for page to load
        page.wait_for_timeout(2000)
        
        # Type a query that will trigger tool usage
        input_box = page.locator('textarea.ds-textarea').first
        if input_box.count() == 0:
            # Try alternative selector
            input_box = page.locator('textarea').first
        input_box.fill("Use python_interpreter to calculate 2+2")
        print("Typed query")
        
        # Submit the query
        page.keyboard.press("Enter")
        print("Submitted query")
        
        # Wait for tool badges to appear
        page.wait_for_timeout(15000)  # Wait longer for agent to respond
        
        # Find all tool badges
        tool_badges = page.locator('.ds-tool-badge').all()
        print(f"Found {len(tool_badges)} tool badges")
        
        # Check each badge for strikethrough marks
        has_strikethrough = False
        for i, badge in enumerate(tool_badges):
            # Get the text content
            text = badge.inner_text()
            print(f"Badge {i+1}: '{text}'")
            
            # Check for strikethrough marks in the text
            if '~~' in text:
                print(f"  ⚠️  Badge {i+1} contains strikethrough marks!")
                has_strikethrough = True
            
            # Check for unwanted icons
            if any(icon in text for icon in ['💻', '📝', '🔍', '✓', '⚡']):
                print(f"  ⚠️  Badge {i+1} contains emoji/icons that should have been cleaned!")
                has_strikethrough = True
            
            # Check the visual style - if it has line-through CSS
            style = badge.evaluate("el => window.getComputedStyle(el).textDecoration")
            if 'line-through' in style:
                print(f"  ⚠️  Badge {i+1} has line-through CSS style!")
                has_strikethrough = True
            
            # Check child elements for strikethrough
            tool_name_el = badge.locator('.ds-tool-name').first
            if tool_name_el.count() > 0:
                tool_name_text = tool_name_el.inner_text()
                print(f"  Tool name element: '{tool_name_text}'")
                
                # Check if it's been properly transformed
                if tool_name_text.isupper() and '_' not in tool_name_text:
                    print(f"  ✅ Tool name properly transformed to CLI style")
                else:
                    print(f"  ⚠️  Tool name not properly transformed")
        
        # Take a screenshot for verification
        page.screenshot(path="debug-archive/screenshots/tool_badge_fix_test.png")
        print("Screenshot saved to debug-archive/screenshots/tool_badge_fix_test.png")
        
        # Clean up
        browser.close()
        
        # Report results
        if has_strikethrough:
            print("\n❌ TEST FAILED: Strikethrough marks or unwanted icons still present!")
            return False
        else:
            print("\n✅ TEST PASSED: No strikethrough marks or unwanted icons found!")
            return True

if __name__ == "__main__":
    success = test_tool_badge_fix()
    exit(0 if success else 1)