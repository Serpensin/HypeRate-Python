#!/usr/bin/env python3
"""
Helper script to run real integration tests with proper token handling.

This script makes it easier to run the real integration tests by handling
token input and providing clear instructions.
"""
import argparse
import getpass
import os
import subprocess
import sys
from typing import Optional


def get_token_from_input() -> Optional[str]:
    """Prompt user for API token securely."""
    print("HypeRate API token is required for real integration tests.")
    print("You can get your API token from: https://app.hyperate.io/")
    print()

    try:
        token = getpass.getpass(
            "Enter your HypeRate API token (input will be hidden): "
        ).strip()
        if not token:
            print("No token provided.")
            return None
        if token.startswith("${") or len(token) < 10:
            print("Invalid token format. Please provide a valid API token.")
            return None
        return token
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled by user.")
        return None


def run_tests_with_token(token: str, extra_args: list = None) -> int:
    """Run the real integration tests with the provided token."""
    if extra_args is None:
        extra_args = []

    # Set environment variable
    env = os.environ.copy()
    env["HYPERATE_API_TOKEN"] = token

    # Build pytest command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "Tests/test_real_integration.py",
        "-v",
        "--tb=short",
    ] + extra_args

    print(f"Running: {' '.join(cmd[:-1])} --token=***")
    print(f"Using token: {token[:8]}...")
    print()

    try:
        result = subprocess.run(cmd, env=env, check=False)
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run HypeRate real integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python Tests/run_real_integration.py
  python Tests/run_real_integration.py --token=your_token
  python Tests/run_real_integration.py --interactive
  python Tests/run_real_integration.py --token=your_token -k test_connection
        """,
    )

    parser.add_argument("--token", type=str, help="HypeRate API token")

    parser.add_argument(
        "--interactive", action="store_true", help="Prompt for API token interactively"
    )

    parser.add_argument(
        "--env-var",
        action="store_true",
        help="Use HYPERATE_API_TOKEN environment variable",
    )

    # Parse known args to allow pytest arguments to pass through
    args, extra_pytest_args = parser.parse_known_args()

    # Determine token source
    token = None

    if args.token:
        token = args.token.strip()
        if token.startswith("${"):
            print("Warning: Token appears to be an unexpanded environment variable.")
            token = None

    if not token and args.env_var:
        token = os.environ.get("HYPERATE_API_TOKEN")
        if not token:
            print("HYPERATE_API_TOKEN environment variable is not set.")
        elif token.startswith("${"):
            print("Warning: Environment variable contains unexpanded shell variable.")
            token = None

    if not token and (args.interactive or (not args.token and not args.env_var)):
        token = get_token_from_input()

    if not token:
        print("\nNo valid API token provided. Cannot run real integration tests.")
        print("\nOptions:")
        print("1. Set environment variable: export HYPERATE_API_TOKEN=your_token")
        print(
            "2. Use command line: python Tests/run_real_integration.py --token=your_token"
        )
        print("3. Interactive mode: python Tests/run_real_integration.py --interactive")
        return 1

    # Validate token format
    if len(token) < 10:
        print("Error: Token appears to be too short. Please check your API token.")
        return 1

    # Run tests
    return run_tests_with_token(token, extra_pytest_args)


if __name__ == "__main__":
    sys.exit(main())
