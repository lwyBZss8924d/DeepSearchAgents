#!/usr/bin/env python3
"""Test script to verify the new Bagua badge system"""

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
        
        # Type a query that will trigger tool usage
        input_box = page.locator('textarea').first
        input_box.fill("Create a plan to search for information about Chinese trigrams, then use python to analyze them")
        print("Typed query")
        
        # Submit the query
        page.keyboard.press("Enter")
        print("Submitted query")
        
        # Wait for badges to appear
        page.wait_for_timeout(20000)  # Wait for agent to respond
        
        # Find all badges
        all_badges = page.locator('.ds-state-badge, .ds-tool-badge').all()
        print(f"\nFound {len(all_badges)} badges total")
        
        # Check for planning badges with Yin Yang symbol
        planning_badges = page.locator('.ds-state-badge').all()
        for i, badge in enumerate(planning_badges):
            text = badge.inner_text()
            print(f"\nPlanning Badge {i+1}: '{text}'")
            
            # Check for Yin Yang symbol
            if '☯' in text:
                print(f"  ✅ Contains Yin Yang symbol")
                if 'Initial Plan' in text or 'Updated Plan' in text:
                    print(f"  ✅ Correct planning format")
            
        # Check for tool badges with trigrams
        tool_badges = page.locator('.ds-tool-badge').all()
        print(f"\n\nFound {len(tool_badges)} tool badges")
        
        trigrams = ['☰', '☱', '☲', '☳', '☴', '☵', '☶', '☷']
        
        for i, badge in enumerate(tool_badges):
            text = badge.inner_text()
            print(f"\nTool Badge {i+1}: '{text}'")
            
            # Check for trigram
            has_trigram = any(trigram in text for trigram in trigrams)
            if has_trigram:
                print(f"  ✅ Contains Bagua trigram")
            
            # Check for command symbol
            if '⌘' in text:
                print(f"  ✅ Contains command symbol")
            
            # Check for code action
            if '~Py' in text:
                print(f"  ✅ Contains Python code action symbol")
            
            # Check for final answer
            if '🀅' in text:
                print(f"  ✅ Contains Mahjong Green Dragon for final answer")
        
        # Check separators
        separators = page.locator('.ds-step-separator').all()
        print(f"\n\nFound {len(separators)} separators")
        for i, sep in enumerate(separators):
            text = sep.inner_text()
            if text:
                print(f"Separator {i+1}: '{text}'")
                if '☯' in text:
                    print(f"  ✅ Planning separator with Yin Yang")
                if '🀅' in text:
                    print(f"  ✅ Final answer separator with Mahjong Dragon")
        
        # Take a screenshot for verification
        page.screenshot(path="debug-archive/screenshots/bagua_badges_test.png")
        print("\nScreenshot saved to debug-archive/screenshots/bagua_badges_test.png")
        
        # Clean up
        browser.close()
        
        print("\n✅ Test completed! Check the screenshot for visual verification.")
        return True

if __name__ == "__main__":
    test_bagua_badges()