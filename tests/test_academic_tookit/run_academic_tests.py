#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/run_academic_tests.py

"""
Test runner for academic toolkit tests.
Run this script to execute all tests with proper configuration.
"""

import sys
import subprocess
import os


def run_tests():
    """Run academic toolkit tests with appropriate configuration."""
    
    print("=" * 60)
    print("Academic Toolkit Test Runner")
    print("=" * 60)
    
    # Check for API keys
    has_mistral = bool(os.getenv("MISTRAL_API_KEY"))
    has_jina = bool(os.getenv("JINA_API_KEY"))
    
    print(f"\nAPI Keys Configured:")
    print(f"- Mistral: {'✓' if has_mistral else '✗'}")
    print(f"- Jina: {'✓' if has_jina else '✗'}")
    
    # Test categories
    test_suites = [
        {
            "name": "Unit Tests - ArxivClient",
            "cmd": ["pytest", "tests/test_academic_tookit/test_arxiv_client.py", "-v", "-m", "unit"],
            "requires_api": False
        },
        {
            "name": "Unit Tests - PaperReader",
            "cmd": ["pytest", "tests/test_academic_tookit/test_paper_reader.py", "-v", "-m", "unit"],
            "requires_api": False
        },
        {
            "name": "Unit Tests - PaperRetriever",
            "cmd": ["pytest", "tests/test_academic_tookit/test_paper_retriever.py", "-v", "-m", "unit"],
            "requires_api": False
        },
        {
            "name": "Integration Tests - Workflows",
            "cmd": ["pytest", "tests/test_academic_tookit/test_integration_workflow.py", "-v", "-m", "integration"],
            "requires_api": True
        },
        {
            "name": "Integration Tests - APIs",
            "cmd": ["pytest", "tests/test_academic_tookit/test_integration_apis.py", "-v", "-m", "integration"],
            "requires_api": True
        }
    ]
    
    # Run each test suite
    for suite in test_suites:
        print(f"\n{'=' * 60}")
        print(f"Running: {suite['name']}")
        print(f"{'=' * 60}")
        
        if suite["requires_api"] and not (has_mistral or has_jina):
            print("⚠️  Skipping - requires API keys")
            continue
        
        try:
            result = subprocess.run(suite["cmd"], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ Tests passed!")
                # Show summary
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if "passed" in line or "failed" in line or "skipped" in line:
                        print(f"  {line.strip()}")
            else:
                print("✗ Tests failed!")
                print(result.stdout)
                if result.stderr:
                    print("Errors:")
                    print(result.stderr)
                    
        except Exception as e:
            print(f"Error running tests: {e}")
    
    print(f"\n{'=' * 60}")
    print("Test run complete!")
    print(f"{'=' * 60}")


def run_specific_examples():
    """Run the specific examples from the user."""
    print("\n" + "=" * 60)
    print("Running User Examples")
    print("=" * 60)
    
    # Example 1: Search for ReAct papers
    print("\nExample 1: Search AI-LLM Agent papers about ReAct...")
    cmd = [
        "pytest", 
        "tests/test_academic_tookit/test_integration_workflow.py::TestAcademicWorkflows::test_search_ai_llm_agent_papers",
        "-v", "-s"
    ]
    subprocess.run(cmd)
    
    # Example 2: Read specific paper
    print("\nExample 2: Read ReAct paper (arXiv:2210.03629)...")
    cmd = [
        "pytest",
        "tests/test_academic_tookit/test_integration_workflow.py::TestAcademicWorkflows::test_read_specific_paper",
        "-v", "-s"
    ]
    subprocess.run(cmd)
    
    # Example 3: HTML availability detection
    print("\nExample 3: HTML availability detection (ReAct vs CodeAct)...")
    cmd = [
        "pytest",
        "tests/test_academic_tookit/test_paper_reader.py::TestPaperReader::test_html_availability_detection",
        "-v", "-s"
    ]
    subprocess.run(cmd)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        run_specific_examples()
    else:
        run_tests()
        
        print("\n💡 Tip: Run with --examples to test the specific user examples")
        print("💡 Set MISTRAL_API_KEY and JINA_API_KEY for full API tests")