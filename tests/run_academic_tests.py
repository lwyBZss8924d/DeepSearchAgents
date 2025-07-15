#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tests/run_academic_tests.py
# code style: PEP 8

"""
Test runner for AcademicRetrieval tool tests.

This script provides an easy way to run the academic retrieval tests
with proper environment setup.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_api_key():
    """Check if FutureHouse API key is set."""
    if not os.getenv("FUTUREHOUSE_API_KEY"):
        print("❌ Error: FUTUREHOUSE_API_KEY environment variable is not set")
        print("\nPlease set your FutureHouse API key:")
        print("  export FUTUREHOUSE_API_KEY='your-api-key-here'")
        return False
    print("✅ FutureHouse API key is set")
    return True


def run_integration_tests():
    """Run integration tests for AcademicRetrieval tool."""
    print("\n" + "="*60)
    print("Running AcademicRetrieval Integration Tests")
    print("="*60 + "\n")
    
    # Run the integration test
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/integration/test_academic_retrieval_integration.py",
        "-xvs",
        "-m", "integration"
    ]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode == 0


def run_cli_tests():
    """Run CLI tests for AcademicRetrieval tool."""
    print("\n" + "="*60)
    print("Running AcademicRetrieval CLI Tests")
    print("="*60 + "\n")
    
    # Run the CLI test
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/integration/test_academic_retrieval_cli.py",
        "-xvs",
        "-m", "integration"
    ]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode == 0


def run_specific_test(test_name):
    """Run a specific test by name."""
    print(f"\n" + "="*60)
    print(f"Running specific test: {test_name}")
    print("="*60 + "\n")
    
    # Find which file contains the test
    test_files = [
        "tests/integration/test_academic_retrieval_integration.py",
        "tests/integration/test_academic_retrieval_cli.py"
    ]
    
    for test_file in test_files:
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-xvs",
            "-k", test_name
        ]
        
        result = subprocess.run(
            cmd, 
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        
        if "deselected" not in result.stdout:
            # Test was found and run
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return result.returncode == 0
    
    print(f"❌ Test '{test_name}' not found in any test file")
    return False


def run_cli_manual_test():
    """Run a manual CLI test with the academic retrieval tool."""
    print("\n" + "="*60)
    print("Manual CLI Test - Academic Retrieval")
    print("="*60 + "\n")
    
    test_query = (
        "Use the academic_retrieval tool to search for papers about "
        "'Large Language Model agent architectures' and summarize "
        "the top 5 results."
    )
    
    print(f"Test Query: {test_query}\n")
    
    # Run with React agent
    print("Testing with React agent...")
    cmd = [
        sys.executable, "-m", "src.cli",
        "--agent-type", "react",
        "--query", test_query
    ]
    
    subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    
    print("\n" + "-"*60 + "\n")
    
    # Run with CodeAct agent
    print("Testing with CodeAct agent...")
    cmd = [
        sys.executable, "-m", "src.cli",
        "--agent-type", "codact",
        "--query", test_query
    ]
    
    subprocess.run(cmd, cwd=Path(__file__).parent.parent)


def main():
    """Main test runner."""
    print("🧪 AcademicRetrieval Tool Test Runner\n")
    
    # Check API key
    if not check_api_key():
        return 1
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "integration":
            success = run_integration_tests()
        elif command == "cli":
            success = run_cli_tests()
        elif command == "manual":
            run_cli_manual_test()
            success = True
        elif command == "all":
            success1 = run_integration_tests()
            success2 = run_cli_tests()
            success = success1 and success2
        elif command.startswith("test_"):
            success = run_specific_test(command)
        else:
            print(f"❌ Unknown command: {command}")
            print("\nUsage:")
            print("  python run_academic_tests.py [command]")
            print("\nCommands:")
            print("  integration  - Run integration tests")
            print("  cli          - Run CLI tests")
            print("  manual       - Run manual CLI test")
            print("  all          - Run all tests")
            print("  test_*       - Run specific test by name")
            return 1
    else:
        # Default: run all tests
        print("Running all tests (use 'python run_academic_tests.py -h' for options)\n")
        success1 = run_integration_tests()
        success2 = run_cli_tests()
        success = success1 and success2
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())