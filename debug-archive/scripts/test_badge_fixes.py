#!/usr/bin/env python3
"""Test script to verify the corrected badge display formats"""

import time
from playwright.sync_api import sync_playwright

def test_badge_fixes():
    with sync_playwright() as p:
        print("Starting Playwright browser...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Navigate to the app
        page.goto("http://localhost:3000")
        print("Navigated to app")
        
        # Wait for page to load
        page.wait_for_timeout(2000)
        
        # Test 1: Python code action
        print("\n=== TEST 1: Python Code Action ===")
        input_box = page.locator('textarea').first
        input_box.fill("Use python to calculate 2+2")
        page.keyboard.press("Enter")
        
        # Wait for response
        page.wait_for_timeout(15000)
        
        # Check badges
        badges = page.locator('.ds-tool-badge-text').all()
        print(f"Found {len(badges)} badges:")
        for badge in badges:
            text = badge.inner_text()
            print(f"  Badge: '{text}'")
            if 'Code Actions' in text and '⌘' not in text and '~Py' in text:
                print("    ✅ Code Actions badge correct (no ⌘ symbol)")
            elif 'Code Actions' in text and '⌘' in text:
                print("    ❌ ERROR: Code Actions should not have ⌘ symbol")
        
        # Clear for next test
        page.reload()
        page.wait_for_timeout(2000)
        
        # Test 2: Tool calls from Python
        print("\n=== TEST 2: Tool Calls from Python ===")
        input_box = page.locator('textarea').first
        input_box.fill("Search for information about trigrams and analyze with python")
        page.keyboard.press("Enter")
        
        # Wait for response
        page.wait_for_timeout(20000)
        
        # Check badges
        badges = page.locator('.ds-tool-badge-text').all()
        print(f"Found {len(badges)} badges:")
        for badge in badges:
            text = badge.inner_text()
            print(f"  Badge: '{text}'")
            if 'WebSearch' in text and '⌘' in text:
                print("    ✅ WebSearch has ⌘ symbol")
            if 'Final Answer' in text:
                if '🀅' in text and '⌘' not in text:
                    print("    ✅ Final Answer correct (has 🀅, no ⌘)")
                elif '⌘' in text:
                    print("    ❌ ERROR: Final Answer should not have ⌘ symbol")
        
        # Take screenshots
        page.screenshot(path="debug-archive/screenshots/badge_fixes_test.png")
        print("\nScreenshot saved to debug-archive/screenshots/badge_fixes_test.png")
        
        # Clean up
        browser.close()
        
        print("\n✅ Test completed!")
        return True

if __name__ == "__main__":
    test_badge_fixes()