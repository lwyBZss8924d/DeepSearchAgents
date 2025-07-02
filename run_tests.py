#!/usr/bin/env python
# -*- coding: utf-8 -*-
# run_tests.py
# code style: PEP 8

"""
Test runner script for DeepSearchAgents v0.2.9.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", verbose=False, coverage=False):
    """Run tests based on type."""
    
    # Base pytest command
    cmd = ["pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add coverage
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    
    # Select test type
    if test_type == "unit":
        cmd.extend(["-m", "unit", "tests/unit/"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration", "tests/integration/"])
    elif test_type == "performance":
        cmd.extend(["-m", "performance", "tests/performance/"])
    elif test_type == "compatibility":
        cmd.extend(["-m", "compatibility", "tests/compatibility/"])
    elif test_type == "quick":
        # Quick tests - exclude slow and tests requiring APIs
        cmd.extend(["-m", "not slow and not requires_llm and not requires_search"])
    elif test_type == "all":
        cmd.append("tests/")
    else:
        print(f"Unknown test type: {test_type}")
        return 1
    
    # Run tests
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Run DeepSearchAgents tests"
    )
    
    parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "performance", "compatibility", "quick"],
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run smoke tests only (quick tests without API calls)"
    )
    
    args = parser.parse_args()
    
    # Override type if smoke test
    if args.smoke:
        args.type = "quick"
    
    # Run tests
    exit_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    # Print summary
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 60)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()