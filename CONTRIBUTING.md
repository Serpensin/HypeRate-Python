# Contributing to HypeRate Python

Thank you for your interest in contributing to HypeRate Python! This document provides guidelines and instructions for contributing to the project.

## 🤝 Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct. Please report unacceptable behavior to [serpensin@serpensin.com](mailto:serpensin@serpensin.com).

## 🚀 How to Contribute

### Reporting Bugs

Before creating bug reports, please check the issue list to see if the problem has already been reported. When you are creating a bug report, please include as many details as possible:

- Use a clear and descriptive title
- Describe the exact steps to reproduce the problem
- Provide specific examples to demonstrate the steps
- Describe the behavior you observed and what behavior you expected
- Include environment details (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- Use a clear and descriptive title
- Provide a detailed description of the suggested enhancement
- Provide specific examples to demonstrate how the enhancement would be used
- Explain why this enhancement would be useful

### Pull Requests

1. Fork the repository
2. Create a new branch from `master` for your feature or bug fix
3. Make your changes
4. Add or update tests as needed
5. Ensure all tests pass
6. Update documentation if necessary
7. Submit a pull request

## 🛠️ Development Setup

### Prerequisites

- Python 3.8 or higher
- Git

### Setting Up Your Development Environment

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/HypeRate-Python.git
   cd HypeRate-Python
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   pip install -r requirements.txt
   ```

4. **Install development tools:**
   ```bash
   pip install -r Tests\requirements-testing.txt
   pip install black isort
   ```

### Running Tests

We provide a comprehensive test runner script that handles all types of testing:

```bash
# Run all tests (comprehensive test suite)
python Tests/run_tests.py --all

# Run specific test types
python Tests/run_tests.py --unit                    # Unit tests only
python Tests/run_tests.py --integration             # Mocked integration tests
python Tests/run_tests.py --performance             # Performance tests
python Tests/run_tests.py --stress                  # Stress tests
python Tests/run_tests.py --benchmark               # Benchmark tests

# Run tests with coverage (required: 85%+ coverage)
python Tests/run_tests.py --coverage

# Run tests in parallel (faster execution)
python Tests/run_tests.py --parallel

# Quick smoke test for rapid feedback
python Tests/run_tests.py --quick
```

#### Real Integration Tests

To run real integration tests against the HypeRate API, you need to provide an API token:

```bash
# Run real integration tests with API token
python Tests/run_tests.py --real-integration --token=your_hyperate_api_token

# Run all tests including real integration tests
python Tests/run_tests.py --all --token=your_hyperate_api_token
```

**Getting an API Token:**
1. Visit [HypeRate.io](https://www.hyperate.io/api-free-request.html)
2. Fill out the form to request a free API token
3. You will receive the token via email

#### Manual Test Commands

If you prefer running tests manually with pytest:

```bash
# Unit tests
python -m pytest Tests/test_hyperate.py -v

# Integration tests (mocked)
python -m pytest Tests/test_mocked_scenarios.py Tests/test_mocked_simple.py -v

# Performance tests
python -m pytest Tests/test_performance.py -v -s

# Real integration tests (requires token)
python -m pytest Tests/test_real_integration.py --token=your_token -v -s

# All tests with coverage
python -m pytest Tests/ --cov=lib.hyperate --cov-report=html --cov-report=term-missing --cov-fail-under=85 -v
```

### Code Quality

Before submitting a pull request, please ensure your code meets our strict quality standards:

```bash
# Run all code quality checks
python Tests/run_tests.py --lint

# Individual quality checks:

# Format code with black (only lib and Tests directories)
black lib Tests

# Sort imports with isort (only lib and Tests directories)
isort lib Tests

# PyLint check (must score 10.0/10.0)
python -m pylint lib/hyperate/ --fail-under=10.0

# Mypy type checking (must pass with --strict)
python -m mypy lib/hyperate/ --strict

# Flake8 style checking (uses .flake8 config file)
python -m flake8 lib/hyperate/
```

**Important:** 
- Only run `black` and `isort` on the `lib` and `Tests` directories
- Never run formatting tools on other directories (like `venv`, `.github`, etc.)
- PyLint must achieve a perfect score of 10.0/10.0
- Mypy must pass with strict mode enabled
- Flake8 must pass style checks with 88 character line limit
- The CI pipeline automatically checks these requirements

## 📝 Style Guidelines

### Python Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Maximum line length is 88 characters (enforced by Flake8)
- Use type hints for all public functions
- Write docstrings for all public functions and classes
- PyLint score must be 10.0/10.0 (perfect score required)
- All code must pass Mypy strict type checking
- All code must pass Flake8 style checks

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

### Documentation

- Update the README.md if your changes affect the public API
- Add docstrings to new functions and classes
- Update type hints when modifying function signatures
- Include examples in docstrings where helpful

## 🧪 Testing Guidelines

- Write tests for all new functionality
- Ensure existing tests continue to pass
- Aim for high test coverage (85%+ required)
- Use descriptive test names that explain what is being tested
- Group related tests in test classes
- Use pytest fixtures for common test setup

### Test Structure

```python
import pytest
from hyperate import Client

class TestClient:
    def test_client_initialization_with_valid_id(self):
        """Test that client initializes correctly with valid ID."""
        client = Client("valid_id")
        assert client.id == "valid_id"
    
    def test_client_initialization_with_invalid_id_raises_error(self):
        """Test that client raises error with invalid ID."""
        with pytest.raises(ValueError):
            Client("")
```

### Test Types

Our test suite includes several types of tests:

1. **Unit Tests** (`test_hyperate.py`) - Test individual functions and classes
2. **Integration Tests** (`test_mocked_*.py`) - Test component interactions with mocked services
3. **Real Integration Tests** (`test_real_integration.py`) - Test against actual HypeRate API
4. **Performance Tests** (`test_performance.py`) - Test performance characteristics
5. **Stress Tests** - Test system behavior under load

## 📚 Documentation

### Docstring Format

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Example function with Google-style docstring.
    
    Args:
        param1: The first parameter.
        param2: The second parameter.
        
    Returns:
        True if successful, False otherwise.
        
    Raises:
        ValueError: If param1 is empty.
    """
    pass
```

## 🏷️ Versioning

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** version when you make incompatible API changes
- **MINOR** version when you add functionality in a backwards compatible manner
- **PATCH** version when you make backwards compatible bug fixes

## 📋 Release Process

1. Update version in `setup.py` and `lib/hyperate/__init__.py`
2. Update `CHANGELOG.md` with release notes
3. Create a pull request for the version bump
4. After merge, create a Git tag for the version
5. Create a GitHub release using the tag
6. The CI/CD pipeline will automatically publish to PyPI

## 🤖 Continuous Integration

Our CI pipeline runs the following checks on every push and pull request:

### Code Quality Checks
- **PyLint**: Must achieve 10.0/10.0 score
- **Mypy**: Must pass with `--strict` mode
- **Flake8**: Must pass style checks (max line length: 88 characters)
- **Tests**: Must pass with 85%+ coverage

### Test Matrix
Tests run on Python versions: 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14

### Workflows
- **Code Quality** (`.github/workflows/code-quality.yml`) - PyLint, Mypy, and Flake8 checks
- **Test Suite** (`.github/workflows/tests.yml`) - Comprehensive test execution
- **PyPI Publishing** (`.github/workflows/publish-pypi.yml`) - Automated package publishing

## 🆘 Getting Help

If you need help with contributing:

- Check the [README.md](README.md) for basic usage
- Look at existing issues for examples
- Ask questions in [GitHub Discussions](https://github.com/Serpensin/HypeRate-Python/discussions)
- Contact the maintainer: [serpensin@serpensin.com](mailto:serpensin@serpensin.com)

## 🎉 Recognition

Contributors will be recognized in:

- The repository's contributor list
- Release notes for significant contributions
- Special thanks in the README for major features

Thank you for contributing to HypeRate Python! 🚀