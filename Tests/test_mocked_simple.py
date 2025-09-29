"""
Simple mocked scenario tests for the HypeRate library.

These tests simulate simple real-world usage scenarios using mocked connections
to test the interaction between different components of the library without
requiring actual network connections or API tokens.
"""
import asyncio
import json
import logging
import time
import unittest
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict, Any

import pytest

from lib.hyperate import HypeRate, Device


class TestSimpleMockedScenarios(unittest.IsolatedAsyncioTestCase):
    """Test simple scenarios with mocked components."""

    async def test_streaming_session_simulation(self):
        """Simulate a complete streaming session with heartbeat monitoring."""
        client = HypeRate("test_token")
        mock_ws = AsyncMock()
        
        # Track received heartbeat data
        heartbeat_data: List[Dict[str, Any]] = []
        clip_data: List[Dict[str, Any]] = []
        connection_events: List[str] = []
        
        def on_connected():
            connection_events.append("connected")
        
        def on_heartbeat(payload):
            heartbeat_data.append(payload)
        
        def on_clip(payload):
            clip_data.append(payload)
        
        def on_disconnected():
            connection_events.append("disconnected")
        
        # Register event handlers
        client.on('connected', on_connected)
        client.on('heartbeat', on_heartbeat)
        client.on('clip', on_clip)
        client.on('disconnected', on_disconnected)
        
        # Mock websockets.connect to return the mock_ws directly
        async def mock_connect(url):
            return mock_ws
        
        # Simulate connection
        with patch('websockets.connect', side_effect=mock_connect):
            await client.connect()
        
        # Simulate joining channels
        await client.join_heartbeat_channel("streamer123")
        await client.join_clips_channel("streamer123")
        
        # Simulate receiving heartbeat data over time
        heartbeat_messages = [
            {"topic": "hr:streamer123", "payload": {"hr": 75}},
            {"topic": "hr:streamer123", "payload": {"hr": 82}},
            {"topic": "hr:streamer123", "payload": {"hr": 78}},
            {"topic": "hr:streamer123", "payload": {"hr": 95}},  # Spike!
            {"topic": "hr:streamer123", "payload": {"hr": 88}},
        ]
        
        # Simulate clip creation during high heart rate
        clip_message = {
            "topic": "clips:streamer123",
            "payload": {"twitch_slug": "epic_moment_123"}
        }
        
        # Process messages
        for msg in heartbeat_messages:
            client._handle_message(json.dumps(msg))
        
        client._handle_message(json.dumps(clip_message))
        
        # Verify data was captured
        self.assertEqual(len(connection_events), 1)
        self.assertEqual(connection_events[0], "connected")
        self.assertEqual(len(heartbeat_data), 5)
        self.assertEqual(len(clip_data), 1)
        
        # Verify heart rate progression
        hr_values = [data["hr"] for data in heartbeat_data]
        self.assertEqual(hr_values, [75, 82, 78, 95, 88])
        
        # Verify clip data
        self.assertEqual(clip_data[0]["twitch_slug"], "epic_moment_123")
        
        # Simulate disconnection
        await client.disconnect()
        self.assertEqual(len(connection_events), 2)
        self.assertEqual(connection_events[1], "disconnected")

    async def test_multi_device_monitoring(self):
        """Test monitoring multiple devices simultaneously."""
        client = HypeRate("test_token")
        mock_ws = AsyncMock()
        
        # Track data per device
        device_data: Dict[str, List[int]] = {
            "device1": [],
            "device2": [],
            "device3": []
        }
        
        def on_heartbeat(payload):
            # Extract device from current context or use a more sophisticated approach
            # For this test, we'll track the last processed message's topic
            if hasattr(client, '_last_topic'):
                device_id = client._last_topic.split(":")[1]
                if device_id in device_data:
                    device_data[device_id].append(payload["hr"])
        
        client.on('heartbeat', on_heartbeat)
        
        async def mock_connect(url):
            return mock_ws
        
        with patch('websockets.connect', side_effect=mock_connect):
            await client.connect()
        
        # Join multiple device channels
        devices = ["device1", "device2", "device3"]
        for device in devices:
            await client.join_heartbeat_channel(device)
        
        # Simulate messages from different devices
        messages = [
            {"topic": "hr:device1", "payload": {"hr": 75}},
            {"topic": "hr:device2", "payload": {"hr": 82}},
            {"topic": "hr:device3", "payload": {"hr": 68}},
            {"topic": "hr:device1", "payload": {"hr": 78}},
            {"topic": "hr:device2", "payload": {"hr": 85}},
        ]
        
        for msg in messages:
            # Store the topic for the handler to access
            client._last_topic = msg["topic"]
            client._handle_message(json.dumps(msg))
        
        # Verify each device received the correct data
        self.assertEqual(device_data["device1"], [75, 78])
        self.assertEqual(device_data["device2"], [82, 85])
        self.assertEqual(device_data["device3"], [68])

    async def test_connection_resilience(self):
        """Test connection resilience and reconnection scenarios."""
        client = HypeRate("test_token")
        connection_attempts = []
        
        async def track_connection(url):
            connection_attempts.append(time.time())
            if len(connection_attempts) <= 2:
                raise ConnectionError("Connection failed")
            return AsyncMock()
        
        # Simulate multiple connection failures followed by success
        with patch('websockets.connect', side_effect=track_connection):
            # First two attempts should fail
            with pytest.raises(ConnectionError):
                await client.connect()
            
            with pytest.raises(ConnectionError):
                await client.connect()
            
            # Third attempt should succeed
            await client.connect()
            
            self.assertTrue(client.connected)
            self.assertEqual(len(connection_attempts), 3)

    async def test_high_frequency_data_handling(self):
        """Test handling of high-frequency heartbeat data."""
        client = HypeRate("test_token")
        received_count = 0
        
        def count_heartbeats(payload):
            nonlocal received_count
            received_count += 1
        
        client.on('heartbeat', count_heartbeats)
        
        # Simulate rapid heartbeat messages (1 per second simulation)
        messages = []
        base_hr = 70
        for i in range(100):  # 100 heartbeats
            hr = base_hr + (i % 30)  # Vary between 70-100
            messages.append({
                "topic": "hr:athlete123",
                "payload": {"hr": hr}
            })
        
        # Process all messages rapidly
        start_time = time.time()
        for msg in messages:
            client._handle_message(json.dumps(msg))
        end_time = time.time()
        
        # Verify all messages were processed
        self.assertEqual(received_count, 100)
        
        # Verify processing was reasonably fast (should be much less than 1s)
        processing_time = end_time - start_time
        self.assertLess(processing_time, 1.0)

    async def test_error_handling_during_stream(self):
        """Test error handling during active streaming."""
        client = HypeRate("test_token")
        mock_ws = AsyncMock()
        
        error_count = 0
        successful_messages = 0
        
        def track_success(payload):
            nonlocal successful_messages
            successful_messages += 1
        
        def failing_handler(payload):
            nonlocal error_count
            error_count += 1
            raise ValueError("Handler error")
        
        # Register both good and bad handlers
        client.on('heartbeat', track_success)
        client.on('heartbeat', failing_handler)
        
        async def mock_connect(url):
            return mock_ws
        
        with patch('websockets.connect', side_effect=mock_connect):
            await client.connect()
        
        # Send some messages
        messages = [
            {"topic": "hr:test", "payload": {"hr": 75}},
            {"topic": "hr:test", "payload": {"hr": 80}},
            {"topic": "hr:test", "payload": {"hr": 85}},
        ]
        
        for msg in messages:
            client._handle_message(json.dumps(msg))
        
        # Verify that despite errors, successful handler still worked
        self.assertEqual(successful_messages, 3)
        self.assertEqual(error_count, 3)

    async def test_device_validation_workflow(self):
        """Test complete device ID validation and extraction workflow."""
        test_cases = [
            # (input, is_valid, expected_extracted)
            ("abc123", True, "abc123"),
            ("https://app.hyperate.io/def456", True, "def456"),
            ("internal-testing", True, "internal-testing"),
            ("toolong123", False, "toolong123"),  # Too long but extractable
            ("", False, None),
            ("https://other-site.com/abc123", False, None),  # Different domain - won't extract properly
        ]
        
        for input_str, should_be_valid, expected_extracted in test_cases:
            with self.subTest(input_str=input_str):
                # Test extraction
                extracted = Device.extract_device_id(input_str) if input_str else None
                
                if expected_extracted is not None:
                    self.assertEqual(extracted, expected_extracted)
                else:
                    self.assertIsNone(extracted)
                
                # Test validation on extracted ID
                if extracted:
                    is_valid = Device.is_valid_device_id(extracted)
                    self.assertEqual(is_valid, should_be_valid)


if __name__ == '__main__':
    # Configure logging for complex scenario tests
    logging.basicConfig(level=logging.INFO)
    
    # Run tests with high verbosity
    unittest.main(verbosity=2)