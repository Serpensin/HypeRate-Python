# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-09-29

### Added
- Initial production release of the HypeRate Python client library
- Real-time heartbeat monitoring via WebSocket API
- Clip notification support
- Async/await architecture with asyncio
- Event-driven handler system
- Comprehensive type hints
- Built-in logging with configurable levels
- Robust error handling and connection management
- Support for Python 3.8 through 3.13
- Comprehensive test suite with unit, integration, and performance tests
- PyLint and Mypy code quality checks
- Codecov integration for test coverage reporting
- GitHub Actions CI/CD pipeline
- PyPI publishing workflow

### Changed
- Migrated repository from testing location to production repository
- Updated all repository URLs to https://github.com/Serpensin/HypeRate-Python
- Bumped version to 1.0.0 for stable production release

### Technical Details
- WebSocket connection handling with automatic reconnection
- Device ID validation and URL extraction utilities
- Event system for heartbeat, clip, connection, and channel events
- MIT License
- Minimum test coverage requirement of 85%
- Support for real-time data from HypeRate devices