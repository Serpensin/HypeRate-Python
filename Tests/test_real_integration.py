"""
True integration tests for the HypeRate library.

These tests require a valid API token and make real connections to HypeRate servers.
They are skipped if the --token argument is not provided or if HYPERATE_API_TOKEN env var is not set.
"""
import argparse
import asyncio
import os
import sys
import time
import unittest
from typing import List, Dict, Any

import pytest

# Handle imports for both direct execution and pytest
try:
    from lib.hyperate import HypeRate, Device
except ImportError:
    # Add parent directory to path for direct execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
    from lib.hyperate import HypeRate, Device

# Import token management from conftest
try:
    from conftest import get_api_token, set_api_token
except ImportError:
    # Fallback if conftest is not available (direct script execution)
    _api_token = None
    
    def get_api_token():
        """Get the API token from command line argument or environment."""
        global _api_token
        # First check if we have a token from command line
        if _api_token and _api_token.strip() and not _api_token.startswith('${'):
            return _api_token
        
        # Check environment variable
        env_token = os.environ.get('HYPERATE_API_TOKEN')
        if env_token and env_token.strip():
            return env_token
            
        return None

    def set_api_token(token):
        """Set the global API token."""
        global _api_token
        _api_token = token

def skip_if_no_token():
    """Dynamic skip function that checks for token at test time."""
    token = get_api_token()
    if not token:
        pytest.skip(
            "API token not provided. Set HYPERATE_API_TOKEN environment variable "
            "or use --token argument with a valid API token"
        )
    return token

class TestRealIntegration(unittest.IsolatedAsyncioTestCase):
    """Real integration tests that connect to HypeRate servers."""

    def setUp(self):
        """Set up test with API token."""
        self.api_token = skip_if_no_token()

    async def test_real_connection_and_authentication(self):
        """Test real connection to HypeRate with valid API token."""
        client = HypeRate(self.api_token)
        
        connection_successful = False
        
        def on_connected():
            nonlocal connection_successful
            connection_successful = True
        
        client.on('connected', on_connected)
        
        try:
            await client.connect()
            
            # Wait a moment for connection to establish
            await asyncio.sleep(2)
            
            # Verify connection was successful
            self.assertTrue(client.connected)
            self.assertTrue(connection_successful)
            
        finally:
            if client.connected:
                await client.disconnect()

    async def test_internal_testing_channel_subscription(self):
        """Test subscribing to the internal-testing channel."""
        client = HypeRate(self.api_token)
        
        channel_joined = False
        heartbeat_received = False
        
        def on_channel_joined(channel):
            nonlocal channel_joined
            if channel == "internal-testing":
                channel_joined = True
        
        def on_heartbeat(payload):
            nonlocal heartbeat_received
            heartbeat_received = True
            print(f"Received heartbeat: {payload}")
        
        client.on('channel_joined', on_channel_joined)
        client.on('heartbeat', on_heartbeat)
        
        try:
            await client.connect()
            await asyncio.sleep(1)  # Wait for connection
            
            # Subscribe to internal testing channel
            await client.join_heartbeat_channel("internal-testing")
            
            # Wait for potential heartbeat data (internal-testing might send test data)
            await asyncio.sleep(10)  # Wait up to 10 seconds for data
            
            # Verify channel subscription worked (even if no heartbeat data)
            self.assertTrue(channel_joined)
            
        finally:
            if client.connected:
                await client.disconnect()

    async def test_invalid_device_channel_behavior(self):
        """Test behavior when subscribing to non-existent device channel."""
        client = HypeRate(self.api_token)
        
        try:
            await client.connect()
            await asyncio.sleep(1)
            
            # Try to subscribe to a non-existent device
            await client.join_heartbeat_channel("definitely-not-a-real-device-12345")
            
            # Wait a moment to see if any error occurs
            await asyncio.sleep(2)
            
            # Should not crash, but might not receive data
            self.assertTrue(client.connected)
            
        finally:
            if client.connected:
                await client.disconnect()

    async def test_connection_with_invalid_token(self):
        """Test connection with invalid API token."""
        client = HypeRate("invalid_token_12345")
        
        try:
            # This should either fail to connect or fail during authentication
            await client.connect()
            
            # If connection succeeds, authentication might fail later
            # Try to join a channel to trigger authentication
            await client.join_heartbeat_channel("internal-testing")
            await asyncio.sleep(3)
            
            # Depending on HypeRate's implementation, this might:
            # 1. Fail during connection
            # 2. Connect but fail during channel join
            # 3. Connect but not receive data
            
        except Exception as e:
            # Expected behavior for invalid token
            print(f"Expected authentication error: {e}")
            
        finally:
            if client.connected:
                await client.disconnect()

    async def test_graceful_disconnect(self):
        """Test graceful disconnection from HypeRate."""
        client = HypeRate(self.api_token)
        
        disconnected = False
        
        def on_disconnected():
            nonlocal disconnected
            disconnected = True
        
        client.on('disconnected', on_disconnected)
        
        await client.connect()
        await asyncio.sleep(1)
        
        # Subscribe to a channel
        await client.join_heartbeat_channel("internal-testing")
        await asyncio.sleep(1)
        
        # Gracefully disconnect
        await client.disconnect()
        
        # Verify disconnection
        self.assertFalse(client.connected)
        self.assertTrue(disconnected)

    async def test_multiple_channel_subscriptions(self):
        """Test subscribing to multiple channels simultaneously."""
        client = HypeRate(self.api_token)
        
        joined_channels = []
        
        def on_channel_joined(channel):
            joined_channels.append(channel)
        
        client.on('channel_joined', on_channel_joined)
        
        try:
            await client.connect()
            await asyncio.sleep(1)
            
            # Subscribe to multiple channels
            channels = ["internal-testing", "test-device-1", "test-device-2"]
            
            for channel in channels:
                await client.join_heartbeat_channel(channel)
                await asyncio.sleep(0.5)  # Small delay between subscriptions
            
            # Wait for all subscriptions to process
            await asyncio.sleep(2)
            
            # At least one channel should have joined successfully
            self.assertGreater(len(joined_channels), 0)
            
        finally:
            if client.connected:
                await client.disconnect()

    async def test_network_resilience(self):
        """Test network resilience (basic connectivity test)."""
        client = HypeRate(self.api_token)
        
        connection_count = 0
        
        def on_connected():
            nonlocal connection_count
            connection_count += 1
        
        client.on('connected', on_connected)
        
        # Test multiple connection cycles
        for i in range(3):
            await client.connect()
            await asyncio.sleep(1)
            self.assertTrue(client.connected)
            
            await client.disconnect()
            await asyncio.sleep(0.5)
            self.assertFalse(client.connected)
        
        # Should have connected 3 times
        self.assertEqual(connection_count, 3)


class TestRealDeviceValidation(unittest.TestCase):
    """Test device validation with real scenarios."""

    def setUp(self):
        """Set up test with API token."""
        self.api_token = skip_if_no_token()

    def test_internal_testing_device_validation(self):
        """Test that internal-testing device ID is valid."""
        self.assertTrue(Device.is_valid_device_id("internal-testing"))

    def test_hyperate_url_extraction(self):
        """Test extracting device IDs from HypeRate URLs."""
        test_cases = [
            ("https://app.hyperate.io/abc123", "abc123"),
            ("https://app.hyperate.io/internal-testing", "internal-testing"),
            ("app.hyperate.io/def456", "def456"),
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url):
                extracted = Device.extract_device_id(url)
                self.assertEqual(extracted, expected)


def parse_args():
    """Parse command line arguments for direct script execution."""
    parser = argparse.ArgumentParser(description='Run HypeRate integration tests')
    parser.add_argument('--token', type=str, help='HypeRate API token for testing')
    
    # Parse known args to allow pytest arguments to pass through
    args, remaining = parser.parse_known_args()
    
    # Update sys.argv to remove our custom arguments so pytest doesn't see them
    sys.argv = [sys.argv[0]] + remaining
    
    return args

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_args()
    set_api_token(args.token)
    
    # Get the final token (from args or environment)
    final_token = get_api_token()
    
    # Only run if API token is available
    if not final_token:
        print("Skipping real integration tests - no API token provided")
        print()
        print("To run real integration tests, either:")
        print("1. Set environment variable:")
        print("   export HYPERATE_API_TOKEN=your_actual_api_token")
        print("   python Tests/test_real_integration.py")
        print()
        print("2. Use command line argument:")
        print("   python Tests/test_real_integration.py --token your_actual_api_token")
        print()
        print("3. With pytest:")
        print("   export HYPERATE_API_TOKEN=your_actual_api_token")
        print("   python -m pytest Tests/test_real_integration.py -v")
        print("   # OR")
        print("   python -m pytest Tests/test_real_integration.py --token=your_actual_api_token -v")
        print()
        print("Note: Replace 'your_actual_api_token' with your real HypeRate API token")
    else:
        print(f"Running real integration tests with token: {final_token[:8]}...")
        unittest.main(verbosity=2)