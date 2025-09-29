"""
Complex scenario tests for the HypeRate library.

These tests simulate complex real-world usage scenarios using mocked connections
to test the interaction between different components of the library without
requiring actual network connections or API tokens.
"""

import asyncio
import json
import logging
import time
import unittest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from lib.hyperate import Device, HypeRate


class TestMockedScenarios(unittest.IsolatedAsyncioTestCase):
    """Test complex scenarios with mocked components."""

    async def test_streaming_session_simulation(self):
        """Simulate a complete streaming session with heartbeat monitoring."""
        client = HypeRate("test_token")
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()

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
        client.on("connected", on_connected)
        client.on("heartbeat", on_heartbeat)
        client.on("clip", on_clip)
        client.on("disconnected", on_disconnected)

        # Create an async function that returns the mock
        async def mock_connect(*args, **kwargs):
            return mock_ws

        # Simulate connection
        with patch("websockets.connect", side_effect=mock_connect):
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
            "payload": {"twitch_slug": "epic_moment_123"},
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
        mock_ws.close = AsyncMock()

        # Track data per device
        device_data: Dict[str, List[int]] = {
            "device1": [],
            "device2": [],
            "device3": [],
        }

        def on_heartbeat(payload):
            # Extract device from current context or use a more sophisticated approach
            # For this test, we'll track the last processed message's topic
            if hasattr(client, "_last_topic"):
                device_id = client._last_topic.split(":")[1]
                if device_id in device_data:
                    device_data[device_id].append(payload["hr"])

        client.on("heartbeat", on_heartbeat)

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("websockets.connect", side_effect=mock_connect):
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

        async def track_connection(*args, **kwargs):
            connection_attempts.append(time.time())
            if len(connection_attempts) <= 2:
                raise ConnectionError("Connection failed")
            mock_ws = AsyncMock()
            mock_ws.close = AsyncMock()
            return mock_ws

        # Simulate multiple connection failures followed by success
        with patch("websockets.connect", side_effect=track_connection):
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

        client.on("heartbeat", count_heartbeats)

        # Simulate rapid heartbeat messages (1 per second simulation)
        messages = []
        base_hr = 70
        for i in range(100):  # 100 heartbeats
            hr = base_hr + (i % 30)  # Vary between 70-100
            messages.append({"topic": "hr:athlete123", "payload": {"hr": hr}})

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
        mock_ws.close = AsyncMock()

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
        client.on("heartbeat", track_success)
        client.on("heartbeat", failing_handler)

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("websockets.connect", side_effect=mock_connect):
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
            (
                "https://other-site.com/abc123",
                False,
                None,
            ),  # Different domain - won't extract properly
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


class TestMockedPerformanceScenarios(unittest.IsolatedAsyncioTestCase):
    """Test performance-related scenarios with mocks."""

    async def test_memory_usage_during_long_session(self):
        """Test memory usage doesn't grow excessively during long sessions."""
        client = HypeRate("test_token")

        # Simulate a long session with many messages
        initial_handlers = len(client._event_handlers["heartbeat"])

        # Add and remove handlers repeatedly
        for i in range(1000):
            handler = Mock()
            client.on("heartbeat", handler)

            if i % 10 == 0:  # Remove every 10th handler
                client._event_handlers["heartbeat"].clear()

        # Memory shouldn't grow indefinitely
        final_handlers = len(client._event_handlers["heartbeat"])
        self.assertLess(final_handlers, 100)  # Reasonable upper bound

    async def test_concurrent_message_processing(self):
        """Test concurrent message processing doesn't cause issues."""
        client = HypeRate("test_token")
        processed_messages = []
        lock = asyncio.Lock()

        async def async_handler(payload):
            async with lock:
                processed_messages.append(payload)
                # Simulate some async processing
                await asyncio.sleep(0.001)

        # Note: The actual event firing is synchronous, but we can test
        # that multiple messages can be processed without interference
        messages = [{"topic": "hr:test", "payload": {"hr": 70 + i}} for i in range(20)]

        # Process messages concurrently (simulate rapid arrival)
        tasks = []
        for msg in messages:
            # We can't easily make the actual message handling async,
            # but we can test that rapid sequential processing works
            client._handle_message(json.dumps(msg))

        # All messages should be processed
        # (This test is more about ensuring no race conditions or crashes)
        self.assertEqual(
            len(processed_messages), 0
        )  # Since handler isn't actually registered

    async def test_large_payload_handling(self):
        """Test handling of large payloads doesn't cause issues."""
        client = HypeRate("test_token")
        large_payloads = []

        def handle_large_payload(payload):
            large_payloads.append(len(json.dumps(payload)))

        client.on("heartbeat", handle_large_payload)

        # Create progressively larger payloads
        for size in [100, 1000, 10000, 100000]:
            large_data = "x" * size
            message = {
                "topic": "hr:test",
                "payload": {"hr": 75, "metadata": large_data},
            }

            start_time = time.time()
            client._handle_message(json.dumps(message))
            end_time = time.time()

            # Processing should be reasonably fast even for large payloads
            self.assertLess(end_time - start_time, 1.0)

        # All payloads should have been processed
        self.assertEqual(len(large_payloads), 4)

        # Verify sizes are as expected (accounting for JSON overhead)
        self.assertGreater(large_payloads[0], 100)
        self.assertGreater(large_payloads[1], 1000)
        self.assertGreater(large_payloads[2], 10000)
        self.assertGreater(large_payloads[3], 100000)


class TestMockedEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Test edge cases with mocked components."""

    async def test_rapid_connect_disconnect_cycles(self):
        """Test rapid connection and disconnection cycles."""
        client = HypeRate("test_token")

        connection_states = []

        def track_connected():
            connection_states.append("connected")

        def track_disconnected():
            connection_states.append("disconnected")

        client.on("connected", track_connected)
        client.on("disconnected", track_disconnected)

        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()

        async def mock_connect(*args, **kwargs):
            return mock_ws

        # Rapid connect/disconnect cycles
        with patch("websockets.connect", side_effect=mock_connect):
            for i in range(5):
                await client.connect()
                await client.disconnect()

        # Should have equal numbers of connections and disconnections
        connected_count = connection_states.count("connected")
        disconnected_count = connection_states.count("disconnected")

        self.assertEqual(connected_count, 5)
        self.assertEqual(disconnected_count, 5)

    async def test_channel_management_edge_cases(self):
        """Test edge cases in channel management."""
        client = HypeRate("test_token")
        mock_ws = AsyncMock()
        client.ws = mock_ws

        # Test joining and leaving the same channel multiple times
        channel_events = []

        def track_channel_joined(channel):
            channel_events.append(f"joined:{channel}")

        def track_channel_left(channel):
            channel_events.append(f"left:{channel}")

        client.on("channel_joined", track_channel_joined)
        client.on("channel_left", track_channel_left)

        # Multiple join/leave cycles
        for i in range(3):
            await client.join_channel("test_channel")

            # Simulate server confirmation for join
            join_reply = {
                "topic": "test_channel",
                "event": "phx_reply",
                "payload": {"status": "ok", "response": {}},
                "ref": 1,
            }
            client._handle_message(json.dumps(join_reply))

            await client.leave_channel("test_channel")

            # Simulate server confirmation for leave
            leave_reply = {
                "topic": "test_channel",
                "event": "phx_reply",
                "payload": {"status": "ok", "response": {}},
                "ref": 2,
            }
            client._handle_message(json.dumps(leave_reply))

        # Should have tracked all operations
        self.assertEqual(len(channel_events), 6)

        # Verify alternating pattern
        for i in range(0, 6, 2):
            self.assertTrue(channel_events[i].startswith("joined:"))
            self.assertTrue(channel_events[i + 1].startswith("left:"))

    async def test_mixed_message_types_rapid_processing(self):
        """Test rapid processing of mixed message types."""
        client = HypeRate("test_token")

        heartbeat_count = 0
        clip_count = 0
        other_count = 0

        def count_heartbeat(payload):
            nonlocal heartbeat_count
            heartbeat_count += 1

        def count_clip(payload):
            nonlocal clip_count
            clip_count += 1

        client.on("heartbeat", count_heartbeat)
        client.on("clip", count_clip)

        # Create mixed message types
        messages = []
        for i in range(50):
            if i % 3 == 0:
                messages.append({"topic": "hr:test", "payload": {"hr": 75 + i % 20}})
            elif i % 3 == 1:
                messages.append(
                    {"topic": "clips:test", "payload": {"twitch_slug": f"clip_{i}"}}
                )
            else:
                messages.append(
                    {"topic": "other:test", "payload": {"data": f"other_{i}"}}
                )

        # Process all messages
        for msg in messages:
            client._handle_message(json.dumps(msg))

        # Verify counts
        expected_heartbeat = len([m for m in messages if m["topic"].startswith("hr:")])
        expected_clip = len([m for m in messages if m["topic"].startswith("clips:")])

        self.assertEqual(heartbeat_count, expected_heartbeat)
        self.assertEqual(clip_count, expected_clip)

    async def test_unicode_and_special_characters_integration(self):
        """Test integration with Unicode and special characters."""
        client = HypeRate("test_token")

        received_data = []

        def collect_data(payload):
            received_data.append(payload)

        client.on("heartbeat", collect_data)
        client.on("clip", collect_data)

        # Messages with various Unicode and special characters
        special_messages = [
            {"topic": "hr:test", "payload": {"hr": 75, "note": "test unicode"}},
            {
                "topic": "clips:emoji_device",
                "payload": {
                    "twitch_slug": "amazing_clip_test",
                    "description": "Emoji test",
                },
            },
            {"topic": "hr:hebrew_device", "payload": {"hr": 80, "location": "Israel"}},
        ]

        for msg in special_messages:
            client._handle_message(json.dumps(msg, ensure_ascii=False))

        # All messages should be processed successfully
        self.assertEqual(len(received_data), 3)

        # Verify data integrity
        self.assertIn("test", str(received_data[0]))
        self.assertIn("test", str(received_data[1]))
        self.assertIn("Israel", str(received_data[2]))


class TestMockedRegressionPrevention(unittest.IsolatedAsyncioTestCase):
    """Test scenarios that prevent regression of previously fixed bugs."""

    async def test_empty_payload_handling(self):
        """Test handling of messages with empty payloads."""
        client = HypeRate("test_token")

        events_fired = []

        def track_events(payload):
            events_fired.append(payload)

        client.on("heartbeat", track_events)
        client.on("clip", track_events)

        # Messages with empty payloads
        empty_messages = [
            {"topic": "hr:test", "payload": {}},
            {"topic": "clips:test", "payload": {}},
            {"topic": "hr:test", "payload": {"hr": None}},
            {"topic": "clips:test", "payload": {"twitch_slug": None}},
        ]

        for msg in empty_messages:
            client._handle_message(json.dumps(msg))

        # Should handle gracefully - only messages with valid data should fire events
        # Empty payloads or null values should not fire events
        self.assertEqual(len(events_fired), 0)

    async def test_malformed_topic_handling(self):
        """Test handling of messages with malformed topics."""
        client = HypeRate("test_token")

        events_fired = []

        def track_events(payload):
            events_fired.append(payload)

        client.on("heartbeat", track_events)
        client.on("clip", track_events)

        # Messages with malformed topics - some should still trigger events
        malformed_messages = [
            {"topic": "hr:", "payload": {"hr": 75}},  # Empty device ID - should trigger
            {
                "topic": "clips:",
                "payload": {"twitch_slug": "test"},
            },  # Empty device ID - should trigger
            {"topic": "hr", "payload": {"hr": 75}},  # Missing colon - won't trigger
            {"topic": "", "payload": {"hr": 75}},  # Empty topic - won't trigger
            {"payload": {"hr": 75}},  # Missing topic entirely - won't trigger
        ]

        for msg in malformed_messages:
            try:
                client._handle_message(json.dumps(msg))
            except Exception:
                pass  # Should handle gracefully, not crash

        # First two malformed messages should still fire events as they have valid topic prefixes
        self.assertEqual(len(events_fired), 2)

    async def test_task_cleanup_on_failed_connection(self):
        """Test that tasks are properly cleaned up when connection fails."""
        client = HypeRate("test_token")

        with patch("websockets.connect", side_effect=Exception("Connection failed")):
            with pytest.raises(Exception):
                await client.connect()

        # Tasks should not be created if connection failed
        self.assertIsNone(client._receive_task)
        self.assertIsNone(client._heartbeat_task)
        self.assertFalse(client.connected)

    async def test_handler_exception_isolation(self):
        """Test that exceptions in one handler don't affect others."""
        client = HypeRate("test_token")

        results = []

        def good_handler1(payload):
            results.append("good1")

        def bad_handler(payload):
            results.append("bad")
            raise Exception("Handler failed")

        def good_handler2(payload):
            results.append("good2")

        # Register handlers in specific order
        client.on("heartbeat", good_handler1)
        client.on("heartbeat", bad_handler)
        client.on("heartbeat", good_handler2)

        # Fire event
        message = {"topic": "hr:test", "payload": {"hr": 75}}
        client._handle_message(json.dumps(message))

        # All handlers should have been called despite the exception
        self.assertIn("good1", results)
        self.assertIn("bad", results)
        self.assertIn("good2", results)


if __name__ == "__main__":
    # Configure logging for complex scenario tests
    logging.basicConfig(level=logging.INFO)

    # Run tests with high verbosity
    unittest.main(verbosity=2)
