#!/usr/bin/env python3
"""
Test runner for HypeRate library.

This script provides various options for running different types of tests
and generating reports.

Usage:
    python run_tests.py [options]
    python Tests/run_tests.py [options]  # When run from project root

Examples:
    python run_tests.py --all                             # Run all tests
    python run_tests.py --unit                            # Run only unit tests
    python run_tests.py --integration                     # Run only integration tests
    python run_tests.py --real-integration --token=TOKEN  # Run real API integration tests
    python run_tests.py --performance                     # Run only performance tests
    python run_tests.py --coverage                        # Run tests with coverage
    python run_tests.py --benchmark                       # Run benchmark tests
    python run_tests.py --parallel                        # Run tests in parallel
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    current_dir = Path(__file__).parent
    # If we're in the Tests folder, go up one level to project root
    if current_dir.name == "Tests":
        return current_dir.parent
    return current_dir


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    start_time = time.time()
    try:
        # Change to project root directory for running commands
        project_root = get_project_root()
        result = subprocess.run(cmd, check=True, capture_output=False, cwd=project_root)
        end_time = time.time()
        print(
            f"\n✅ {description} completed successfully in {end_time - start_time:.2f}s"
        )
        return True
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        print(f"\n❌ {description} failed after {end_time - start_time:.2f}s")
        print(f"Exit code: {e.returncode}")
        return False


def run_unit_tests() -> bool:
    """Run unit tests."""
    cmd = ["python", "-m", "pytest", "Tests/test_hyperate.py", "-v"]
    return run_command(cmd, "Unit Tests")


def run_integration_tests() -> bool:
    """Run integration tests."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "Tests/test_mocked_scenarios.py",
        "Tests/test_mocked_simple.py",
        "-v",
    ]
    return run_command(cmd, "Mocked Scenario Tests")


def run_real_integration_tests(token: str = None) -> bool:
    """Run real integration tests that require API token."""
    if not token:
        print("\n⚠️  Skipping real integration tests - no API token provided")
        print("To run real integration tests:")
        print(
            "  python Tests/run_tests.py --real-integration --token=your_actual_api_token"
        )
        return True  # Not a failure, just skipped

    # Set the token as an environment variable for the test
    env = os.environ.copy()
    env["HYPERATE_API_TOKEN"] = token
    
    cmd = [
        "python",
        "-m",
        "pytest",
        "Tests/test_real_integration.py",
        "-v",
        "-s",
    ]
    
    print(f"\n{'='*60}")
    print(f"Running: Real Integration Tests")
    print(f"Command: {' '.join(cmd)}")
    print(f"Token: {token[:8]}..." if token else "No token")
    print(f"{'='*60}")

    start_time = time.time()
    try:
        # Change to project root directory for running commands
        project_root = get_project_root()
        result = subprocess.run(cmd, check=True, capture_output=False, cwd=project_root, env=env)
        end_time = time.time()
        print(
            f"\n✅ Real Integration Tests completed successfully in {end_time - start_time:.2f}s"
        )
        return True
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        print(f"\n❌ Real Integration Tests failed after {end_time - start_time:.2f}s")
        print(f"Exit code: {e.returncode}")
        return False


def run_performance_tests() -> bool:
    """Run performance tests."""
    cmd = ["python", "-m", "pytest", "Tests/test_performance.py", "-v", "-s"]
    return run_command(cmd, "Performance Tests")


def run_all_tests() -> bool:
    """Run all tests."""
    cmd = ["python", "-m", "pytest", "Tests/", "-v"]
    return run_command(cmd, "All Tests")


def run_tests_with_coverage() -> bool:
    """Run tests with coverage reporting."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "Tests/",
        "--cov=lib.hyperate",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "--cov-fail-under=85",
        "-v",
    ]
    return run_command(cmd, "Tests with Coverage")


def run_benchmark_tests() -> bool:
    """Run benchmark tests."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "Tests/test_performance.py",
        "--benchmark-only",
        "--benchmark-sort=mean",
        "--benchmark-compare-fail=mean:5%",
        "-v",
    ]
    return run_command(cmd, "Benchmark Tests")


def run_parallel_tests() -> bool:
    """Run tests in parallel."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "Tests/",
        "-n",
        "auto",  # Use all available CPUs
        "--dist=loadscope",
        "-v",
    ]
    return run_command(cmd, "Parallel Tests")


def run_stress_tests() -> bool:
    """Run stress tests specifically."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "Tests/test_performance.py::TestStressTests",
        "-v",
        "-s",
    ]
    return run_command(cmd, "Stress Tests")


def run_linting() -> bool:
    """Run code quality checks."""
    success = True

    # PyLint
    cmd = ["python", "-m", "pylint", "lib/hyperate/", "--output-format=text", "--fail-under=10.0"]
    success &= run_command(cmd, "PyLint Check")

    # Mypy
    cmd = ["python", "-m", "mypy", "lib/hyperate/", "--strict"]
    success &= run_command(cmd, "Mypy Type Check")

    # Flake8
    cmd = ["python", "-m", "flake8", "lib/hyperate/"]
    success &= run_command(cmd, "Flake8 Style Check")

    return success


def generate_test_report() -> bool:
    """Generate comprehensive test report."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "Tests/",
        "--cov=lib.hyperate",
        "--cov-report=html",
        "--html=report.html",
        "--self-contained-html",
        "--junit-xml=test-results.xml",
        "-v",
    ]
    return run_command(cmd, "Test Report Generation")


def check_test_dependencies() -> bool:
    """Check if all test dependencies are installed."""
    print("Checking test dependencies...")

    required_packages = [
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "websockets",
        "pylint",
        "mypy",
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print(r"Install with: pip install -r .\Tests\requirements.txt")
        return False

    print("✅ All test dependencies are installed")
    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Test runner for HypeRate library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --all                             # Run all tests
  python run_tests.py --unit                            # Run only unit tests
  python run_tests.py --integration                     # Run only integration tests
  python run_tests.py --real-integration --token=TOKEN  # Run real API integration tests
  python run_tests.py --performance                     # Run only performance tests
  python run_tests.py --coverage                        # Run tests with coverage
  python run_tests.py --benchmark                       # Run benchmark tests
  python run_tests.py --parallel                        # Run tests in parallel
  python run_tests.py --stress                          # Run stress tests
  python run_tests.py --lint                            # Run code quality checks
  python run_tests.py --report                          # Generate test report
        """,
    )

    # Test type options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--all", action="store_true", help="Run all tests")
    test_group.add_argument("--unit", action="store_true", help="Run unit tests only")
    test_group.add_argument(
        "--integration", action="store_true", help="Run mocked scenario tests"
    )
    test_group.add_argument(
        "--real-integration",
        action="store_true",
        help="Run real integration tests (requires API token)",
    )
    test_group.add_argument(
        "--performance", action="store_true", help="Run performance tests only"
    )
    test_group.add_argument(
        "--stress", action="store_true", help="Run stress tests only"
    )
    test_group.add_argument(
        "--benchmark", action="store_true", help="Run benchmark tests"
    )

    # Additional options
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage"
    )
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--lint", action="store_true", help="Run code quality checks")
    parser.add_argument(
        "--report", action="store_true", help="Generate comprehensive test report"
    )
    parser.add_argument(
        "--check-deps", action="store_true", help="Check test dependencies"
    )
    parser.add_argument("--quick", action="store_true", help="Run quick smoke tests")
    parser.add_argument(
        "--token", type=str, help="API token for real integration tests"
    )

    args = parser.parse_args()

    # Check dependencies first
    if args.check_deps or not check_test_dependencies():
        return 1 if not check_test_dependencies() else 0

    # Default to all tests if no specific option is given
    if not any(
        [
            args.all,
            args.unit,
            args.integration,
            args.real_integration,
            args.performance,
            args.stress,
            args.benchmark,
            args.coverage,
            args.parallel,
            args.lint,
            args.report,
            args.quick,
        ]
    ):
        args.all = True

    success = True

    # Run selected tests
    if args.quick:
        # Quick smoke test - just run a few basic tests
        cmd = [
            "python",
            "-c",
            "from lib.hyperate import HypeRate, Device; print('Import successful')",
        ]
        success &= run_command(cmd, "Quick Import Test")

        cmd = [
            "python",
            "-m",
            "pytest",
            "Tests/test_hyperate.py::TestHypeRateInitialization",
            "-v",
        ]
        success &= run_command(cmd, "Quick Unit Test")

    elif args.unit:
        success &= run_unit_tests()

    elif args.integration:
        success &= run_integration_tests()

    elif args.real_integration:
        success &= run_real_integration_tests(args.token)

    elif args.performance:
        success &= run_performance_tests()

    elif args.stress:
        success &= run_stress_tests()

    elif args.benchmark:
        success &= run_benchmark_tests()

    elif args.coverage:
        success &= run_tests_with_coverage()

    elif args.parallel:
        success &= run_parallel_tests()

    elif args.lint:
        success &= run_linting()

    elif args.report:
        success &= generate_test_report()

    elif args.all:
        # Run comprehensive test suite
        print("Running comprehensive test suite...")
        success &= run_linting()
        success &= run_unit_tests()
        success &= run_integration_tests()
        success &= run_real_integration_tests(
            args.token
        )  # Pass token for real integration tests
        success &= run_performance_tests()
        success &= run_tests_with_coverage()

    # Print final summary
    print(f"\n{'='*80}")
    if success:
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
    else:
        print("❌ SOME TESTS FAILED!")
    print(f"{'='*80}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
