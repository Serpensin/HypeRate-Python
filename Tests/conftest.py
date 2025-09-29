"""
Test configuration and utilities for the HypeRate library tests.

This module provides common test configurations, fixtures, and utilities
used across all test modules.
"""

import asyncio
import logging
import os
import tempfile
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Configure test logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise during tests
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Global variable to store the API token from command line
_api_token = None


def get_api_token():
    """Get the API token from command line argument or environment variable."""
    global _api_token
    # First check if we have a token from command line
    if _api_token and _api_token.strip() and not _api_token.startswith("${"):
        return _api_token

    # Check environment variable
    env_token = os.environ.get("HYPERATE_API_TOKEN")
    if env_token and env_token.strip():
        return env_token

    return None


def set_api_token(token):
    """Set the global API token."""
    global _api_token
    _api_token = token


def pytest_addoption(parser):
    """Add custom command line option to pytest."""
    parser.addoption(
        "--token",
        action="store",
        default=None,
        help="HypeRate API token for real integration tests",
    )


def pytest_configure(config):
    """Configure pytest with the token argument."""
    token = config.getoption("--token")
    if token:
        set_api_token(token)
        # Also set it in the test_real_integration module
        try:
            import test_real_integration

            test_real_integration.set_api_token(token)
        except ImportError:
            pass


# Test configuration
TEST_CONFIG = {
    "default_token": "test_token_12345",
    "default_base_url": "wss://app.hyperate.io/socket/websocket",
    "test_device_ids": ["abc123", "def456", "test01", "device1"],
    "invalid_device_ids": [
        "",
        "ab",
        "toolongdevice",
        "test-with-dash",
        "test_with_underscore",
    ],
    "test_urls": [
        "https://app.hyperate.io/abc123",
        "http://app.hyperate.io/def456",
        "app.hyperate.io/test01",
        "https://app.hyperate.io/device1?param=value",
    ],
    "performance_thresholds": {
        "message_processing_rate": 1000,  # messages per second
        "event_registration_rate": 5000,  # registrations per second
        "memory_growth_limit_mb": 100,  # max memory growth in MB
        "max_processing_time_ms": 100,  # max time for large payloads
    },
}


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_messages: List[str] = []
        self.closed = False
        self._messages_to_receive: List[str] = []
        self._receive_index = 0

    async def send(self, message: str) -> None:
        """Mock send method."""
        if self.closed:
            raise Exception("WebSocket is closed")
        self.sent_messages.append(message)

    async def close(self) -> None:
        """Mock close method."""
        self.closed = True

    def add_message(self, message: str) -> None:
        """Add a message to be received."""
        self._messages_to_receive.append(message)

    def __aiter__(self):
        """Async iterator for receiving messages."""
        return self

    async def __anext__(self):
        """Get next message."""
        if self._receive_index >= len(self._messages_to_receive):
            raise StopAsyncIteration

        message = self._messages_to_receive[self._receive_index]
        self._receive_index += 1
        return message


class HypeRateTestCase(unittest.TestCase):
    """Base test case for HypeRate tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_token = TEST_CONFIG["default_token"]
        self.test_base_url = TEST_CONFIG["default_base_url"]
        self.mock_logger = Mock(spec=logging.Logger)

        # Suppress actual logging during tests
        self.log_patcher = patch("lib.hyperate.hyperate.logging.getLogger")
        self.mock_get_logger = self.log_patcher.start()
        self.mock_get_logger.return_value = self.mock_logger

    def tearDown(self):
        """Clean up after tests."""
        self.log_patcher.stop()

    def create_test_message(self, topic: str, payload: Dict[str, Any]) -> str:
        """Create a test message JSON string."""
        import json

        return json.dumps({"topic": topic, "payload": payload})

    def create_heartbeat_message(self, device_id: str, hr: int) -> str:
        """Create a heartbeat message."""
        return self.create_test_message(f"hr:{device_id}", {"hr": hr})

    def create_clip_message(self, device_id: str, slug: str) -> str:
        """Create a clip message."""
        return self.create_test_message(f"clips:{device_id}", {"twitch_slug": slug})


class AsyncHypeRateTestCase(unittest.IsolatedAsyncioTestCase, HypeRateTestCase):
    """Base async test case for HypeRate tests."""

    async def asyncSetUp(self):
        """Async setup."""
        HypeRateTestCase.setUp(self)
        self.mock_ws = MockWebSocket()

    async def asyncTearDown(self):
        """Async cleanup."""
        HypeRateTestCase.tearDown(self)


class TestDataGenerator:
    """Generate test data for various scenarios."""

    @staticmethod
    def generate_heartbeat_sequence(
        device_id: str, count: int, base_hr: int = 70, variation: int = 30
    ) -> List[str]:
        """Generate a sequence of heartbeat messages."""
        import json

        messages = []
        for i in range(count):
            hr = base_hr + (i % variation)
            message = json.dumps(
                {"topic": f"hr:{device_id}", "payload": {"hr": hr, "timestamp": i}}
            )
            messages.append(message)
        return messages

    @staticmethod
    def generate_mixed_messages(device_ids: List[str], count: int) -> List[str]:
        """Generate mixed heartbeat and clip messages."""
        import json
        import random

        messages = []

        for i in range(count):
            device_id = random.choice(device_ids)

            if i % 10 == 0:  # 10% clip messages
                message = json.dumps(
                    {
                        "topic": f"clips:{device_id}",
                        "payload": {"twitch_slug": f"clip_{i}"},
                    }
                )
            else:  # 90% heartbeat messages
                hr = random.randint(60, 180)
                message = json.dumps(
                    {"topic": f"hr:{device_id}", "payload": {"hr": hr}}
                )

            messages.append(message)

        return messages

    @staticmethod
    def generate_invalid_messages(count: int) -> List[str]:
        """Generate invalid messages for error testing."""
        invalid_messages = [
            "invalid json",
            '{"topic": "hr:test"}',  # Missing payload
            '{"payload": {"hr": 75}}',  # Missing topic
            '{"topic": "", "payload": {"hr": 75}}',  # Empty topic
            '{"topic": "hr:", "payload": {"hr": 75}}',  # Empty device ID
            '{"topic": "unknown:test", "payload": {"data": "value"}}',  # Unknown topic
        ]

        # Cycle through invalid patterns
        messages = []
        for i in range(count):
            pattern = invalid_messages[i % len(invalid_messages)]
            messages.append(pattern)

        return messages


def create_performance_test_suite() -> unittest.TestSuite:
    """Create a test suite focused on performance tests."""
    from tests.test_performance import (
        TestAsyncPerformance,
        TestPerformanceBenchmarks,
        TestStressTests,
    )

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPerformanceBenchmarks))
    suite.addTest(unittest.makeSuite(TestStressTests))
    suite.addTest(unittest.makeSuite(TestAsyncPerformance))
    return suite


def create_integration_test_suite() -> unittest.TestSuite:
    """Create a test suite focused on integration tests."""
    from tests.test_integration import (
        TestEdgeIntegrationScenarios,
        TestPerformanceScenarios,
        TestRealWorldScenarios,
        TestRegressionScenarios,
    )

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRealWorldScenarios))
    suite.addTest(unittest.makeSuite(TestPerformanceScenarios))
    suite.addTest(unittest.makeSuite(TestEdgeIntegrationScenarios))
    suite.addTest(unittest.makeSuite(TestRegressionScenarios))
    return suite


def create_unit_test_suite() -> unittest.TestSuite:
    """Create a test suite focused on unit tests."""
    from tests.test_hyperate import (
        TestDevice,
        TestHypeRateBackgroundTasks,
        TestHypeRateChannelManagement,
        TestHypeRateConnection,
        TestHypeRateEdgeCases,
        TestHypeRateEventHandling,
        TestHypeRateInitialization,
        TestHypeRateIntegration,
        TestHypeRateLogging,
        TestHypeRateMessageHandling,
        TestHypeRatePacketSending,
    )

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHypeRateInitialization))
    suite.addTest(unittest.makeSuite(TestHypeRateEventHandling))
    suite.addTest(unittest.makeSuite(TestHypeRateConnection))
    suite.addTest(unittest.makeSuite(TestHypeRatePacketSending))
    suite.addTest(unittest.makeSuite(TestHypeRateChannelManagement))
    suite.addTest(unittest.makeSuite(TestHypeRateMessageHandling))
    suite.addTest(unittest.makeSuite(TestHypeRateBackgroundTasks))
    suite.addTest(unittest.makeSuite(TestDevice))
    suite.addTest(unittest.makeSuite(TestHypeRateIntegration))
    suite.addTest(unittest.makeSuite(TestHypeRateLogging))
    suite.addTest(unittest.makeSuite(TestHypeRateEdgeCases))
    return suite


def run_all_tests(verbosity: int = 2) -> bool:
    """Run all test suites."""
    print("=" * 80)
    print("RUNNING COMPLETE HYPERATE TEST SUITE")
    print("=" * 80)

    # Create master test suite
    master_suite = unittest.TestSuite()
    master_suite.addTest(create_unit_test_suite())
    master_suite.addTest(create_integration_test_suite())
    master_suite.addTest(create_performance_test_suite())

    # Run all tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(master_suite)

    # Print summary
    print("=" * 80)
    print("TEST SUITE SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )

    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}")

    print("=" * 80)

    return result.wasSuccessful()


# Pytest configuration and fixtures
@pytest.fixture
def hyperate_client():
    """Pytest fixture for HypeRate client."""
    from lib.hyperate import HypeRate

    return HypeRate(TEST_CONFIG["default_token"])


@pytest.fixture
def mock_websocket():
    """Pytest fixture for mock WebSocket."""
    return MockWebSocket()


@pytest.fixture
def test_messages():
    """Pytest fixture for test messages."""
    return TestDataGenerator.generate_heartbeat_sequence("test_device", 10)


# Test markers
pytest.mark.unit = pytest.mark.unit  # Unit tests
pytest.mark.integration = pytest.mark.integration  # Integration tests
pytest.mark.performance = pytest.mark.performance  # Performance tests
pytest.mark.slow = pytest.mark.slow  # Slow running tests


if __name__ == "__main__":
    import sys

    success = run_all_tests()
    sys.exit(0 if success else 1)
