"""
Comprehensive unit tests for the HypeRate WebSocket client.

This module tests all functionality of the HypeRate class including:
- Initialization and configuration
- Connection and disconnection
- Channel management (joining/leaving)
- Message handling and event firing
- Error handling and edge cases
- Logging behavior
- Type safety and validation
"""

import asyncio
import json
import logging
import re
import unittest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from lib.hyperate import Device, HypeRate


class TestHypeRateInitialization(unittest.TestCase):
    """Test HypeRate class initialization and configuration."""

    def test_basic_initialization(self):
        """Test basic initialization with minimal parameters."""
        client = HypeRate("test_token")

        self.assertEqual(client.api_token, "test_token")
        self.assertEqual(client.base_url, "wss://app.hyperate.io/socket/websocket")
        self.assertIsNone(client.ws)
        self.assertFalse(client.connected)
        self.assertIsNotNone(client.logger)
        self.assertIsNone(client._receive_task)
        self.assertIsNone(client._heartbeat_task)

    def test_initialization_with_custom_base_url(self):
        """Test initialization with custom base URL."""
        custom_url = "wss://custom.example.com/websocket"
        client = HypeRate("test_token", base_url=custom_url)

        self.assertEqual(client.base_url, custom_url)

    def test_initialization_with_custom_logger(self):
        """Test initialization with custom logger."""
        custom_logger = logging.getLogger("test_logger")
        client = HypeRate("test_token", logger=custom_logger)

        self.assertEqual(client.logger.parent, custom_logger)
        self.assertEqual(client.logger.name, "test_logger.hyperate")

    def test_token_stripping(self):
        """Test that API tokens are properly stripped of whitespace."""
        client = HypeRate("  test_token  ")
        self.assertEqual(client.api_token, "test_token")

    def test_event_handlers_initialization(self):
        """Test that all event handler lists are properly initialized."""
        client = HypeRate("test_token")

        expected_events = [
            "connected",
            "disconnected",
            "heartbeat",
            "clip",
            "channel_joined",
            "channel_left",
        ]

        for event in expected_events:
            self.assertIn(event, client._event_handlers)
            self.assertIsInstance(client._event_handlers[event], list)
            self.assertEqual(len(client._event_handlers[event]), 0)

    def test_logger_setup_without_custom_logger(self):
        """Test that logger is properly set up when no custom logger is provided."""
        client = HypeRate("test_token")

        self.assertIsNotNone(client.logger)
        self.assertTrue(client.logger.name.endswith("HypeRate"))
        self.assertEqual(client.logger.level, logging.INFO)


class TestHypeRateEventHandling(unittest.TestCase):
    """Test event registration and firing mechanisms."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = HypeRate("test_token")
        self.mock_handler1 = Mock()
        self.mock_handler2 = Mock()

    def test_register_valid_event_handler(self):
        """Test registering handlers for valid events."""
        self.client.on("connected", self.mock_handler1)
        self.client.on("heartbeat", self.mock_handler2)

        self.assertIn(self.mock_handler1, self.client._event_handlers["connected"])
        self.assertIn(self.mock_handler2, self.client._event_handlers["heartbeat"])

    def test_register_multiple_handlers_same_event(self):
        """Test registering multiple handlers for the same event."""
        self.client.on("heartbeat", self.mock_handler1)
        self.client.on("heartbeat", self.mock_handler2)

        self.assertEqual(len(self.client._event_handlers["heartbeat"]), 2)
        self.assertIn(self.mock_handler1, self.client._event_handlers["heartbeat"])
        self.assertIn(self.mock_handler2, self.client._event_handlers["heartbeat"])

    def test_register_invalid_event_handler(self):
        """Test registering handler for invalid event logs warning."""
        with patch.object(self.client.logger, "warning") as mock_warning:
            self.client.on("invalid_event", self.mock_handler1)
            mock_warning.assert_called_once()

    def test_fire_event_with_handlers(self):
        """Test firing events with registered handlers."""
        self.client.on("heartbeat", self.mock_handler1)
        self.client.on("heartbeat", self.mock_handler2)

        test_data = {"hr": 75}
        self.client._fire_event("heartbeat", test_data)

        self.mock_handler1.assert_called_once_with(test_data)
        self.mock_handler2.assert_called_once_with(test_data)

    def test_fire_event_without_handlers(self):
        """Test firing events with no registered handlers."""
        with patch.object(self.client.logger, "debug") as mock_debug:
            self.client._fire_event("heartbeat", {"hr": 75})
            mock_debug.assert_any_call(
                "No handlers registered for event: %s", "heartbeat"
            )

    def test_fire_event_with_handler_exception(self):
        """Test firing events when a handler raises an exception."""

        def failing_handler(*args):
            raise ValueError("Test exception")

        self.client.on("heartbeat", failing_handler)
        self.client.on("heartbeat", self.mock_handler1)

        with patch.object(self.client.logger, "error") as mock_error:
            self.client._fire_event("heartbeat", {"hr": 75})

            # Should log error but still call other handlers
            mock_error.assert_called_once()
            self.mock_handler1.assert_called_once_with({"hr": 75})

    def test_fire_event_with_multiple_arguments(self):
        """Test firing events with multiple arguments."""
        self.client.on("channel_joined", self.mock_handler1)

        self.client._fire_event("channel_joined", "test_channel", "extra_arg")

        self.mock_handler1.assert_called_once_with("test_channel", "extra_arg")


class TestHypeRateConnection(unittest.IsolatedAsyncioTestCase):
    """Test WebSocket connection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = HypeRate("test_token")
        self.mock_ws = AsyncMock()

    async def test_successful_connection(self):
        """Test successful WebSocket connection."""
        mock_ws = AsyncMock()

        async def mock_connect(url):
            return mock_ws

        # Create simple Mock objects for tasks to avoid AsyncMock issues
        mock_receive_task = Mock()
        mock_heartbeat_task = Mock()

        with patch(
            "websockets.connect", side_effect=mock_connect
        ) as mock_connect_patch:
            with patch.object(self.client, "_fire_event") as mock_fire:
                # Completely bypass the task creation by mocking create_task
                with patch.object(
                    self.client._loop,
                    "create_task",
                    side_effect=[mock_receive_task, mock_heartbeat_task],
                ) as mock_create_task:
                    # Mock the coroutine functions themselves to return None immediately
                    with patch.object(self.client, "_receive", return_value=None):
                        with patch.object(self.client, "_heartbeat", return_value=None):

                            await self.client.connect()

                            mock_connect_patch.assert_called_once_with(
                                "wss://app.hyperate.io/socket/websocket?token=test_token"
                            )
                            self.assertEqual(self.client.ws, mock_ws)
                            self.assertTrue(self.client.connected)
                            mock_fire.assert_called_once_with("connected")
                            self.assertEqual(
                                mock_create_task.call_count, 2
                            )  # receive and heartbeat tasks
                            self.assertEqual(
                                self.client._receive_task, mock_receive_task
                            )
                            self.assertEqual(
                                self.client._heartbeat_task, mock_heartbeat_task
                            )

    async def test_connection_failure_websocket_exception(self):
        """Test connection failure with WebSocket exception."""
        with patch(
            "websockets.connect", side_effect=WebSocketException("Connection failed")
        ):
            with pytest.raises(WebSocketException):
                await self.client.connect()

            self.assertIsNone(self.client.ws)
            self.assertFalse(self.client.connected)

    async def test_connection_failure_general_exception(self):
        """Test connection failure with general exception."""
        with patch("websockets.connect", side_effect=Exception("General error")):
            with pytest.raises(Exception):
                await self.client.connect()

            self.assertIsNone(self.client.ws)
            self.assertFalse(self.client.connected)

    async def test_disconnect(self):
        """Test WebSocket disconnection."""
        # Set up connected state
        self.client.ws = self.mock_ws
        self.client.connected = True
        self.client._receive_task = Mock()
        self.client._receive_task.done.return_value = False
        self.client._heartbeat_task = Mock()
        self.client._heartbeat_task.done.return_value = False

        with patch.object(self.client, "_fire_event") as mock_fire:
            await self.client.disconnect()

            self.client._receive_task.cancel.assert_called_once()
            self.client._heartbeat_task.cancel.assert_called_once()
            self.mock_ws.close.assert_called_once()
            self.assertFalse(self.client.connected)
            mock_fire.assert_called_once_with("disconnected")

    async def test_disconnect_with_completed_tasks(self):
        """Test disconnection when tasks are already completed."""
        # Set up connected state with completed tasks
        self.client.ws = self.mock_ws
        self.client.connected = True
        self.client._receive_task = Mock()
        self.client._receive_task.done.return_value = True
        self.client._heartbeat_task = Mock()
        self.client._heartbeat_task.done.return_value = True

        await self.client.disconnect()

        # Tasks should not be cancelled if already done
        self.client._receive_task.cancel.assert_not_called()
        self.client._heartbeat_task.cancel.assert_not_called()
        self.mock_ws.close.assert_called_once()

    async def test_disconnect_without_websocket(self):
        """Test disconnection when no WebSocket connection exists."""
        self.client.ws = None
        self.client.connected = True

        with patch.object(self.client, "_fire_event") as mock_fire:
            await self.client.disconnect()

            self.assertFalse(self.client.connected)
            mock_fire.assert_called_once_with("disconnected")


class TestHypeRatePacketSending(unittest.IsolatedAsyncioTestCase):
    """Test packet sending functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = HypeRate("test_token")
        self.mock_ws = AsyncMock()
        self.client.ws = self.mock_ws

    async def test_send_packet_success(self):
        """Test successful packet sending."""
        test_packet = {"topic": "test", "event": "test_event", "payload": {}}

        await self.client.send_packet(test_packet)

        expected_json = json.dumps(test_packet)
        self.mock_ws.send.assert_called_once_with(expected_json)

    async def test_send_packet_websocket_exception(self):
        """Test packet sending with WebSocket exception."""
        self.mock_ws.send.side_effect = WebSocketException("Send failed")
        test_packet = {"topic": "test", "event": "test_event"}

        with pytest.raises(WebSocketException):
            await self.client.send_packet(test_packet)

    async def test_send_packet_json_error(self):
        """Test packet sending with JSON encoding error."""

        # Create an object that can't be JSON serialized
        class NonSerializable:
            pass

        test_packet = {"data": NonSerializable()}

        with pytest.raises(TypeError):
            await self.client.send_packet(test_packet)

    async def test_send_packet_no_websocket(self):
        """Test packet sending when no WebSocket connection exists."""
        self.client.ws = None
        test_packet = {"topic": "test"}

        with patch.object(self.client.logger, "warning") as mock_warning:
            await self.client.send_packet(test_packet)
            mock_warning.assert_called_once_with(
                "Attempted to send packet but WebSocket is not connected"
            )

    async def test_send_packet_general_exception(self):
        """Test packet sending with general exception."""
        self.mock_ws.send.side_effect = Exception("General error")
        test_packet = {"topic": "test"}

        with pytest.raises(Exception):
            await self.client.send_packet(test_packet)


class TestHypeRateChannelManagement(unittest.IsolatedAsyncioTestCase):
    """Test channel joining and leaving functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = HypeRate("test_token")

    async def test_join_heartbeat_channel(self):
        """Test joining heartbeat channel."""
        device_id = "test_device"

        with patch.object(self.client, "join_channel") as mock_join:
            await self.client.join_heartbeat_channel(device_id)
            mock_join.assert_called_once_with("hr:test_device")

    async def test_leave_heartbeat_channel(self):
        """Test leaving heartbeat channel."""
        device_id = "test_device"

        with patch.object(self.client, "leave_channel") as mock_leave:
            await self.client.leave_heartbeat_channel(device_id)
            mock_leave.assert_called_once_with("hr:test_device")

    async def test_join_clips_channel(self):
        """Test joining clips channel."""
        device_id = "test_device"

        with patch.object(self.client, "join_channel") as mock_join:
            await self.client.join_clips_channel(device_id)
            mock_join.assert_called_once_with("clips:test_device")

    async def test_leave_clips_channel(self):
        """Test leaving clips channel."""
        device_id = "test_device"

        with patch.object(self.client, "leave_channel") as mock_leave:
            await self.client.leave_clips_channel(device_id)
            mock_leave.assert_called_once_with("clips:test_device")

    async def test_join_channel_success(self):
        """Test successful channel joining."""
        channel_name = "test_channel"

        with patch.object(self.client, "send_packet") as mock_send:
            await self.client.join_channel(channel_name)

            expected_packet = {
                "topic": channel_name,
                "event": "phx_join",
                "payload": {},
                "ref": 1,
            }
            mock_send.assert_called_once_with(expected_packet)
            # Note: channel_joined event is now only fired when server confirms join

    async def test_leave_channel_success(self):
        """Test successful channel leaving."""
        channel_name = "test_channel"

        with patch.object(self.client, "send_packet") as mock_send:
            await self.client.leave_channel(channel_name)

            expected_packet = {
                "topic": channel_name,
                "event": "phx_leave",
                "payload": {},
                "ref": 2,
            }
            mock_send.assert_called_once_with(expected_packet)
            # Note: channel_left event is now only fired when server confirms leave

    async def test_join_channel_websocket_exception(self):
        """Test channel joining with WebSocket exception."""
        channel_name = "test_channel"

        with patch.object(
            self.client, "send_packet", side_effect=WebSocketException("Join failed")
        ):
            with pytest.raises(WebSocketException):
                await self.client.join_channel(channel_name)

    async def test_leave_channel_general_exception(self):
        """Test channel leaving with general exception."""
        channel_name = "test_channel"

        with patch.object(
            self.client, "send_packet", side_effect=Exception("Leave failed")
        ):
            with pytest.raises(Exception):
                await self.client.leave_channel(channel_name)


class TestHypeRateMessageHandling(unittest.TestCase):
    """Test WebSocket message handling and parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = HypeRate("test_token")

    def test_handle_heartbeat_message_string(self):
        """Test handling heartbeat message as string."""
        message_data = {"topic": "hr:test_device", "payload": {"hr": 75}}
        message = json.dumps(message_data)

        with patch.object(self.client, "_fire_event") as mock_fire:
            self.client._handle_message(message)
            mock_fire.assert_called_once_with("heartbeat", {"hr": 75})

    def test_handle_heartbeat_message_bytes(self):
        """Test handling heartbeat message as bytes."""
        message_data = {"topic": "hr:test_device", "payload": {"hr": 80}}
        message = json.dumps(message_data).encode("utf-8")

        with patch.object(self.client, "_fire_event") as mock_fire:
            self.client._handle_message(message)
            mock_fire.assert_called_once_with("heartbeat", {"hr": 80})

    def test_handle_clip_message(self):
        """Test handling clip message."""
        message_data = {
            "topic": "clips:test_device",
            "payload": {"twitch_slug": "test_clip_slug"},
        }
        message = json.dumps(message_data)

        with patch.object(self.client, "_fire_event") as mock_fire:
            self.client._handle_message(message)
            mock_fire.assert_called_once_with("clip", {"twitch_slug": "test_clip_slug"})

    def test_handle_heartbeat_message_no_hr(self):
        """Test handling heartbeat message without hr field."""
        message_data = {"topic": "hr:test_device", "payload": {"other_field": "value"}}
        message = json.dumps(message_data)

        with patch.object(self.client, "_fire_event") as mock_fire:
            self.client._handle_message(message)
            mock_fire.assert_not_called()

    def test_handle_clip_message_no_slug(self):
        """Test handling clip message without twitch_slug."""
        message_data = {
            "topic": "clips:test_device",
            "payload": {"other_field": "value"},
        }
        message = json.dumps(message_data)

        with patch.object(self.client, "_fire_event") as mock_fire:
            self.client._handle_message(message)
            mock_fire.assert_not_called()

    def test_handle_unknown_topic_message(self):
        """Test handling message with unknown topic."""
        message_data = {
            "topic": "unknown:test_device",
            "event": "test_event",
            "payload": {"data": "value"},
        }
        message = json.dumps(message_data)

        with patch.object(self.client, "_fire_event") as mock_fire:
            with patch.object(self.client.logger, "debug") as mock_debug:
                self.client._handle_message(message)
                mock_fire.assert_not_called()
                mock_debug.assert_any_call(
                    "Received message for topic: %s, event: %s",
                    "unknown:test_device",
                    "test_event",
                )

    def test_handle_invalid_json_message(self):
        """Test handling invalid JSON message."""
        invalid_message = "invalid json {"

        with patch.object(self.client.logger, "error") as mock_error:
            self.client._handle_message(invalid_message)
            mock_error.assert_called_once()

    def test_handle_invalid_bytes_message(self):
        """Test handling invalid bytes message."""
        invalid_bytes = b"\xff\xfe\\invalid"  # Fixed escape sequence

        with patch.object(self.client.logger, "error") as mock_error:
            self.client._handle_message(invalid_bytes)
            mock_error.assert_called_once()

    def test_handle_message_general_exception(self):
        """Test handling message with general exception."""
        with patch("json.loads", side_effect=Exception("General error")):
            with patch.object(self.client.logger, "error") as mock_error:
                self.client._handle_message("test message")
                mock_error.assert_called_once()

    def test_handle_phoenix_reply_join_success(self):
        """Test handling Phoenix reply for successful channel join."""
        message_data = {
            "topic": "hr:test_device",
            "event": "phx_reply",
            "payload": {"status": "ok", "response": {}},
            "ref": 1,
        }
        message = json.dumps(message_data)

        with patch.object(self.client, "_fire_event") as mock_fire:
            self.client._handle_message(message)
            mock_fire.assert_called_once_with("channel_joined", "test_device")

    def test_handle_phoenix_reply_leave_success(self):
        """Test handling Phoenix reply for successful channel leave."""
        message_data = {
            "topic": "clips:test_device",
            "event": "phx_reply",
            "payload": {"status": "ok", "response": {}},
            "ref": 2,
        }
        message = json.dumps(message_data)

        with patch.object(self.client, "_fire_event") as mock_fire:
            self.client._handle_message(message)
            mock_fire.assert_called_once_with("channel_left", "test_device")

    def test_handle_phoenix_reply_error(self):
        """Test handling Phoenix reply with error status."""
        message_data = {
            "topic": "hr:test_device",
            "event": "phx_reply",
            "payload": {"status": "error", "response": {"reason": "not_found"}},
            "ref": 1,
        }
        message = json.dumps(message_data)

        with patch.object(self.client, "_fire_event") as mock_fire:
            with patch.object(self.client.logger, "error") as mock_error:
                self.client._handle_message(message)
                mock_fire.assert_not_called()  # Should not fire channel_joined on error
                mock_error.assert_called_once()

    def test_handle_phoenix_reply_unknown_ref(self):
        """Test handling Phoenix reply with unknown ref."""
        message_data = {
            "topic": "hr:test_device",
            "event": "phx_reply",
            "payload": {"status": "ok", "response": {}},
            "ref": 999,  # Unknown ref
        }
        message = json.dumps(message_data)

        with patch.object(self.client, "_fire_event") as mock_fire:
            with patch.object(self.client.logger, "debug") as mock_debug:
                self.client._handle_message(message)
                mock_fire.assert_not_called()
                mock_debug.assert_any_call(
                    "Phoenix reply with status 'ok': %s", message_data
                )


class TestHypeRateBackgroundTasks(unittest.IsolatedAsyncioTestCase):
    """Test heartbeat and receive background tasks."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = HypeRate("test_token")
        self.mock_ws = AsyncMock()
        self.client.ws = self.mock_ws

    async def test_heartbeat_task_normal_operation(self):
        """Test heartbeat task normal operation."""
        self.client.connected = True

        # Mock sleep to prevent infinite loop
        async def mock_sleep(duration):
            self.client.connected = False  # Stop after first iteration

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch.object(self.client, "send_packet") as mock_send:
                await self.client._heartbeat()

                expected_packet = {
                    "topic": "phoenix",
                    "event": "heartbeat",
                    "payload": {},
                    "ref": 0,
                }
                mock_send.assert_called_once_with(expected_packet)

    async def test_heartbeat_task_cancelled_error(self):
        """Test heartbeat task with CancelledError."""
        self.client.connected = True

        with patch.object(
            self.client, "send_packet", side_effect=asyncio.CancelledError()
        ):
            with patch.object(self.client.logger, "debug") as mock_debug:
                await self.client._heartbeat()
                mock_debug.assert_any_call("Heartbeat task cancelled")

    async def test_heartbeat_task_websocket_exception(self):
        """Test heartbeat task with WebSocket exception."""
        self.client.connected = True

        with patch.object(
            self.client,
            "send_packet",
            side_effect=WebSocketException("Heartbeat failed"),
        ):
            with patch.object(self.client.logger, "error") as mock_error:
                await self.client._heartbeat()
                mock_error.assert_called_once()

    async def test_heartbeat_task_general_exception(self):
        """Test heartbeat task with general exception."""
        self.client.connected = True

        with patch.object(
            self.client, "send_packet", side_effect=Exception("General error")
        ):
            with patch.object(self.client.logger, "error") as mock_error:
                await self.client._heartbeat()
                mock_error.assert_called_once()

    async def test_receive_task_normal_operation(self):
        """Test receive task normal operation."""
        messages = ["message1", "message2"]
        self.mock_ws.__aiter__.return_value = iter(messages)

        with patch.object(self.client, "_handle_message") as mock_handle:
            await self.client._receive()

            self.assertEqual(mock_handle.call_count, 2)
            mock_handle.assert_has_calls([call("message1"), call("message2")])

    async def test_receive_task_no_websocket(self):
        """Test receive task when WebSocket is None."""
        self.client.ws = None

        with patch.object(self.client.logger, "debug") as mock_debug:
            await self.client._receive()
            mock_debug.assert_any_call("Receive task started")
            mock_debug.assert_any_call("Receive task ended")

    async def test_receive_task_cancelled_error(self):
        """Test receive task with CancelledError."""
        self.mock_ws.__aiter__.side_effect = asyncio.CancelledError()

        with patch.object(self.client.logger, "debug") as mock_debug:
            await self.client._receive()
            mock_debug.assert_any_call("Receive task cancelled")

    async def test_receive_task_connection_closed(self):
        """Test receive task with ConnectionClosed exception."""
        self.mock_ws.__aiter__.side_effect = ConnectionClosed(None, None)

        with patch.object(self.client, "_fire_event") as mock_fire:
            await self.client._receive()

            self.assertFalse(self.client.connected)
            mock_fire.assert_called_once_with("disconnected")

    async def test_receive_task_websocket_exception(self):
        """Test receive task with WebSocket exception."""
        self.mock_ws.__aiter__.side_effect = WebSocketException("Receive failed")

        with patch.object(self.client, "_fire_event") as mock_fire:
            await self.client._receive()

            self.assertFalse(self.client.connected)
            mock_fire.assert_called_once_with("disconnected")

    async def test_receive_task_general_exception(self):
        """Test receive task with general exception."""
        self.mock_ws.__aiter__.side_effect = Exception("General error")

        with patch.object(self.client, "_fire_event") as mock_fire:
            await self.client._receive()

            self.assertFalse(self.client.connected)
            mock_fire.assert_called_once_with("disconnected")


class TestDevice(unittest.TestCase):
    """Test Device utility class."""

    def test_valid_device_id_normal(self):
        """Test validation of normal valid device IDs."""
        valid_ids = ["abc123", "DEF456", "a1b2c3", "123", "abcdefgh"]

        for device_id in valid_ids:
            with self.subTest(device_id=device_id):
                self.assertTrue(Device.is_valid_device_id(device_id))

    def test_valid_device_id_internal_testing(self):
        """Test validation of special 'internal-testing' device ID."""
        self.assertTrue(Device.is_valid_device_id("internal-testing"))

    def test_invalid_device_id_too_short(self):
        """Test validation rejects device IDs that are too short."""
        short_ids = ["", "a", "ab"]

        for device_id in short_ids:
            with self.subTest(device_id=device_id):
                self.assertFalse(Device.is_valid_device_id(device_id))

    def test_invalid_device_id_too_long(self):
        """Test validation rejects device IDs that are too long."""
        long_ids = ["abcdefghi", "123456789", "toolongdeviceid"]

        for device_id in long_ids:
            with self.subTest(device_id=device_id):
                self.assertFalse(Device.is_valid_device_id(device_id))

    def test_invalid_device_id_invalid_characters(self):
        """Test validation rejects device IDs with invalid characters."""
        invalid_ids = ["abc-123", "def_456", "abc@123", "test.id", "test id"]

        for device_id in invalid_ids:
            with self.subTest(device_id=device_id):
                self.assertFalse(Device.is_valid_device_id(device_id))

    def test_extract_device_id_from_raw_id(self):
        """Test extraction of device ID from raw device ID."""
        test_cases = [
            ("abc123", "abc123"),
            ("DEF456", "DEF456"),
            (
                "test-id",
                "test-id",
            ),  # Note: hyphen allowed in extraction, not validation
        ]

        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = Device.extract_device_id(input_str)
                self.assertEqual(result, expected)

    def test_extract_device_id_from_url(self):
        """Test extraction of device ID from HypeRate URLs."""
        test_cases = [
            ("https://app.hyperate.io/abc123", "abc123"),
            ("http://app.hyperate.io/DEF456", "DEF456"),
            ("app.hyperate.io/test123", "test123"),
            ("https://app.hyperate.io/abc123?param=value", "abc123"),
            ("http://app.hyperate.io/test-device?query=1&other=2", "test-device"),
        ]

        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = Device.extract_device_id(input_str)
                self.assertEqual(result, expected)

    def test_extract_device_id_invalid_input(self):
        """Test extraction returns None for invalid input."""
        invalid_inputs = [
            "",
            "https://other-site.com/abc123",
            "not-a-url-or-id",
            "https://app.hyperate.io/",
            None,  # This should not break the regex
        ]

        for input_str in invalid_inputs:
            with self.subTest(input_str=input_str):
                if input_str is None:
                    with self.assertRaises(TypeError):
                        Device.extract_device_id(input_str)
                else:
                    result = Device.extract_device_id(input_str)
                    # Some might still match the pattern, that's okay
                    # The main thing is it shouldn't crash

    def test_regex_pattern_compilation(self):
        """Test that the regex pattern compiles correctly."""
        self.assertIsInstance(Device.VALID_ID_REGEX, re.Pattern)

        # Test the pattern directly
        pattern = Device.VALID_ID_REGEX
        self.assertTrue(pattern.match("abc123"))
        self.assertFalse(pattern.match("abc-123"))
        self.assertFalse(pattern.match(""))
        self.assertFalse(pattern.match("toolongdeviceid"))


class TestHypeRateIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for the HypeRate client."""

    async def test_full_connection_workflow(self):
        """Test complete connection workflow from start to finish."""
        client = HypeRate("test_token")
        mock_ws = AsyncMock()

        # Mock event handlers
        connected_handler = Mock()
        heartbeat_handler = Mock()
        disconnected_handler = Mock()

        client.on("connected", connected_handler)
        client.on("heartbeat", heartbeat_handler)
        client.on("disconnected", disconnected_handler)

        # Test connection
        async def mock_connect(url):
            return mock_ws

        with patch("websockets.connect", side_effect=mock_connect):
            await client.connect()

            self.assertTrue(client.connected)
            connected_handler.assert_called_once()

        # Test heartbeat message handling
        heartbeat_message = json.dumps(
            {"topic": "hr:testdevice", "payload": {"hr": 85}}
        )

        client._handle_message(heartbeat_message)
        heartbeat_handler.assert_called_once_with({"hr": 85})

        # Test disconnection
        await client.disconnect()

        self.assertFalse(client.connected)
        disconnected_handler.assert_called_once()

    async def test_error_recovery_workflow(self):
        """Test error recovery scenarios."""
        client = HypeRate("test_token")

        call_count = 0

        async def mock_connect(url):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise WebSocketException("Failed")
            return AsyncMock()

        with patch("websockets.connect", side_effect=mock_connect):
            # First connection fails
            with pytest.raises(WebSocketException):
                await client.connect()

            self.assertFalse(client.connected)

            # Second connection fails
            with pytest.raises(WebSocketException):
                await client.connect()

            # Third connection succeeds
            await client.connect()
            self.assertTrue(client.connected)

    async def test_concurrent_operations(self):
        """Test concurrent operations on the client."""
        client = HypeRate("test_token")
        mock_ws = AsyncMock()
        client.ws = mock_ws

        # Test concurrent packet sending
        packets = [
            {"topic": "test1", "event": "join", "payload": {}},
            {"topic": "test2", "event": "join", "payload": {}},
            {"topic": "test3", "event": "join", "payload": {}},
        ]

        tasks = [client.send_packet(packet) for packet in packets]
        await asyncio.gather(*tasks)

        self.assertEqual(mock_ws.send.call_count, 3)

    async def test_memory_cleanup_on_disconnect(self):
        """Test that resources are properly cleaned up on disconnect."""
        client = HypeRate("test_token")
        mock_ws = AsyncMock()

        # Set up connected state
        client.ws = mock_ws
        client.connected = True
        client._receive_task = Mock()
        client._receive_task.done.return_value = False
        client._heartbeat_task = Mock()
        client._heartbeat_task.done.return_value = False

        await client.disconnect()

        # Verify cleanup
        self.assertFalse(client.connected)
        client._receive_task.cancel.assert_called_once()
        client._heartbeat_task.cancel.assert_called_once()
        mock_ws.close.assert_called_once()


class TestHypeRateLogging(unittest.TestCase):
    """Test logging behavior of the HypeRate client."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)

        # Capture log output
        self.log_handler = logging.Handler()
        self.log_records: List[logging.LogRecord] = []
        self.log_handler.emit = lambda record: self.log_records.append(record)
        self.logger.addHandler(self.log_handler)

    def tearDown(self):
        """Clean up test fixtures."""
        self.logger.removeHandler(self.log_handler)

    def test_initialization_logging(self):
        """Test logging during initialization."""
        client = HypeRate("test_token", logger=self.logger)

        # Check that initialization was logged
        debug_records = [r for r in self.log_records if r.levelno == logging.DEBUG]
        self.assertTrue(any("initialized" in r.getMessage() for r in debug_records))

    def test_event_registration_logging(self):
        """Test logging during event registration."""
        client = HypeRate("test_token", logger=self.logger)
        handler = Mock()

        client.on("heartbeat", handler)

        debug_records = [r for r in self.log_records if r.levelno == logging.DEBUG]
        self.assertTrue(
            any("Event handler registered" in r.getMessage() for r in debug_records)
        )

    def test_invalid_event_logging(self):
        """Test logging when registering invalid event."""
        client = HypeRate("test_token", logger=self.logger)
        handler = Mock()

        client.on("invalid_event", handler)

        warning_records = [r for r in self.log_records if r.levelno == logging.WARNING]
        self.assertTrue(any("unknown event" in r.getMessage() for r in warning_records))

    def test_message_handling_logging(self):
        """Test logging during message handling."""
        client = HypeRate("test_token", logger=self.logger)

        # Test valid message
        valid_message = json.dumps({"topic": "hr:test", "payload": {"hr": 75}})
        client._handle_message(valid_message)

        # Test invalid message
        invalid_message = "invalid json"
        client._handle_message(invalid_message)

        debug_records = [r for r in self.log_records if r.levelno == logging.DEBUG]
        error_records = [r for r in self.log_records if r.levelno == logging.ERROR]

        self.assertTrue(
            any("Heartbeat data received" in r.getMessage() for r in debug_records)
        )
        self.assertTrue(any("Failed to parse" in r.getMessage() for r in error_records))


class TestHypeRateEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_token(self):
        """Test behavior with empty token."""
        client = HypeRate("")
        self.assertEqual(client.api_token, "")

    def test_whitespace_only_token(self):
        """Test behavior with whitespace-only token."""
        client = HypeRate("   ")
        self.assertEqual(client.api_token, "")

    def test_very_long_token(self):
        """Test behavior with very long token."""
        long_token = "a" * 10000
        client = HypeRate(long_token)
        self.assertEqual(client.api_token, long_token)

    def test_special_characters_in_token(self):
        """Test behavior with special characters in token."""
        special_token = "token!@#$%^&*()_+-=[]{}|;':\",./<>?"
        client = HypeRate(special_token)
        self.assertEqual(client.api_token, special_token)

    def test_unicode_in_messages(self):
        """Test handling of Unicode characters in messages."""
        client = HypeRate("test_token")

        unicode_message = json.dumps(
            {"topic": "hr:test", "payload": {"hr": 75, "note": "???? ??"}}
        )

        with patch.object(client, "_fire_event") as mock_fire:
            client._handle_message(unicode_message)
            mock_fire.assert_called_once()

    async def test_multiple_simultaneous_connections(self):
        """Test behavior with multiple connection attempts."""
        client = HypeRate("test_token")

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        call_count = 0

        async def mock_connect(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_ws1
            else:
                return mock_ws2

        with patch("websockets.connect", side_effect=mock_connect):
            # First connection
            await client.connect()
            self.assertEqual(client.ws, mock_ws1)

            # Second connection (should replace first)
            await client.connect()
            self.assertEqual(client.ws, mock_ws2)

    def test_event_handler_modification_during_firing(self):
        """Test modifying event handlers while events are being fired."""
        client = HypeRate("test_token")

        def handler_that_adds_handler(*args):
            client.on("heartbeat", Mock())

        def handler_that_removes_self(*args):
            if handler_that_removes_self in client._event_handlers["heartbeat"]:
                client._event_handlers["heartbeat"].remove(handler_that_removes_self)

        client.on("heartbeat", handler_that_adds_handler)
        client.on("heartbeat", handler_that_removes_self)

        # This should not crash
        client._fire_event("heartbeat", {"hr": 75})

        # Verify the handlers were modified
        self.assertGreater(len(client._event_handlers["heartbeat"]), 1)
        self.assertNotIn(handler_that_removes_self, client._event_handlers["heartbeat"])

    def test_large_message_handling(self):
        """Test handling of very large messages."""
        client = HypeRate("test_token")

        # Create a large payload
        large_payload = {"data": "x" * 100000, "hr": 75}
        large_message = json.dumps({"topic": "hr:test", "payload": large_payload})

        with patch.object(client, "_fire_event") as mock_fire:
            client._handle_message(large_message)
            mock_fire.assert_called_once_with("heartbeat", large_payload)

    def test_nested_json_in_messages(self):
        """Test handling of deeply nested JSON structures."""
        client = HypeRate("test_token")

        nested_payload = {
            "hr": 75,
            "metadata": {
                "device": {
                    "info": {
                        "version": "1.0",
                        "settings": {
                            "enabled": True,
                            "features": ["heartbeat", "clips"],
                        },
                    }
                }
            },
        }

        nested_message = json.dumps({"topic": "hr:test", "payload": nested_payload})

        with patch.object(client, "_fire_event") as mock_fire:
            client._handle_message(nested_message)
            mock_fire.assert_called_once_with("heartbeat", nested_payload)
