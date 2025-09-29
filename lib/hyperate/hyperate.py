"""
HypeRate WebSocket Client Module.

This module provides a WebSocket client for connecting to the HypeRate API
to receive real-time heartbeat and clip data.
"""
import asyncio
import json
import logging
import re
import sys
import warnings
from typing import Any, Callable, Dict, List, Optional, Union

import websockets

# Check Python version early but after imports
if sys.version_info < (3, 8):
    raise ImportError(
        f"HypeRate requires Python 3.8 or higher. "
        f"You are using Python {sys.version_info.major}.{sys.version_info.minor}."
        f"{sys.version_info.micro}"
    )

# Type alias for WebSocket connection - this works across different websockets versions
WebSocketConnection = Any  # websockets.WebSocketClientProtocol or similar

# Type alias for regex pattern - compatible with Python 3.8+
if sys.version_info >= (3, 8):
    from typing import Pattern
    RegexPattern = Pattern[str]
else:
    RegexPattern = type(re.compile(''))


# pylint: disable=too-many-instance-attributes
class HypeRate:
    """
    A WebSocket client for connecting to the HypeRate API to receive real-time
    heartbeat and clip data.

    The HypeRate class provides an asynchronous interface for connecting to
    HypeRate's WebSocket service, subscribing to heartbeat and clip channels,
    and handling incoming data through event handlers.

    Attributes:
        api_token (str): The API token for authentication with HypeRate service.
        base_url (str): The WebSocket URL for the HypeRate service.
        ws: The WebSocket connection object.
        connected (bool): Flag indicating if the client is currently connected.
        logger (logging.Logger): Logger instance for logging messages.
    """

    def __init__(self, api_token: str,
                 base_url: str = "wss://app.hyperate.io/socket/websocket",
                 logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the HypeRate client with API token and optional base URL.

        Args:
            api_token (str): The API token for authentication with HypeRate service.
            base_url (str, optional): The WebSocket URL for the HypeRate service.
                                    Defaults to "wss://app.hyperate.io/socket/websocket".
            logger (logging.Logger, optional): Custom logger instance. If provided, a
                                             child logger named 'hyperate' will be created
                                             from it to maintain proper logging hierarchy.
        """
        self.api_token: str = api_token.strip()
        self.base_url: str = base_url
        self.ws: Optional[WebSocketConnection] = None
        self.connected: bool = False
        self._event_handlers: Dict[str, List[Callable[..., None]]] = {
            'connected': [],
            'disconnected': [],
            'heartbeat': [],
            'clip': [],
            'channel_joined': [],
            'channel_left': [],
        }
        self._receive_task: Optional[asyncio.Task[None]] = None
        self._heartbeat_task: Optional[asyncio.Task[None]] = None

        # Get or create event loop safely, avoiding deprecation warnings
        try:
            self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop, create a new one for this thread
            # Suppress deprecation warning for asyncio.get_event_loop()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning,
                                        message="There is no current event loop")
                try:
                    self._loop = asyncio.get_event_loop()
                except RuntimeError:
                    # Create a new event loop if none exists
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)

        if logger is None:
            self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger.getChild("hyperate")

        self.logger.debug("HypeRate client initialized with base_url: %s", self.base_url)

    def on(self, event: str, handler: Callable[..., None]) -> None:
        """
        Register an event handler for a specific event type.

        Args:
            event (str): The event type to listen for. Valid events are:
                        'connected', 'disconnected', 'heartbeat', 'clip',
                        'channel_joined', 'channel_left'.
            handler (Callable): The function to call when the event occurs.
        """
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)
            self.logger.debug("Event handler registered for event: %s", event)
        else:
            self.logger.warning("Attempted to register handler for unknown event: %s", event)

    async def connect(self) -> None:
        """
        Establish a WebSocket connection to the HypeRate service.

        This method connects to the WebSocket endpoint, starts the receive and heartbeat tasks,
        and fires the 'connected' event.

        Raises:
            websockets.exceptions.WebSocketException: If the connection fails.
        """
        try:
            url = f"{self.base_url}?token={self.api_token}"
            self.logger.info("Attempting to connect to HypeRate WebSocket: %s", self.base_url)

            self.ws = await websockets.connect(url)
            self.connected = True
            self.logger.info("Successfully connected to HypeRate WebSocket")

            self._fire_event('connected')
            self._receive_task = self._loop.create_task(self._receive())
            self._heartbeat_task = self._loop.create_task(self._heartbeat())

            self.logger.debug("Receive and heartbeat tasks started")

        except websockets.exceptions.WebSocketException as e:
            self.logger.error("Failed to connect to HypeRate WebSocket: %s", e)
            raise
        except Exception as e:
            self.logger.error("Unexpected error during connection: %s", e)
            raise

    async def disconnect(self) -> None:
        """
        Close the WebSocket connection and clean up resources.

        This method closes the WebSocket connection, sets the connected flag to False,
        and fires the 'disconnected' event.
        """
        self.logger.info("Disconnecting from HypeRate WebSocket")

        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            # Await the cancellation to prevent warnings about unawaited coroutines
            # Only if it's an actual asyncio.Task
            if hasattr(self._receive_task, '__await__'):
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
            self.logger.debug("Receive task cancelled")

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            # Await the cancellation to prevent warnings about unawaited coroutines
            # Only if it's an actual asyncio.Task
            if hasattr(self._heartbeat_task, '__await__'):
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            self.logger.debug("Heartbeat task cancelled")

        if self.ws:
            await self.ws.close()
            self.logger.debug("WebSocket connection closed")

        self.connected = False
        self._fire_event('disconnected')
        self.logger.info("Successfully disconnected from HypeRate WebSocket")

    async def send_packet(self, packet: Dict[str, Any]) -> None:
        """
        Send a packet to the WebSocket server.

        Args:
            packet (dict): The packet data to send, which will be JSON-encoded.
        """
        if self.ws:
            try:
                json_data = json.dumps(packet)
                await self.ws.send(json_data)
                self.logger.debug("Sent packet: %s", packet)
            except websockets.exceptions.WebSocketException as e:
                self.logger.error("WebSocket error while sending packet %s: %s", packet, e)
                raise
            except (json.JSONDecodeError, TypeError) as e:
                self.logger.error("Failed to encode packet %s as JSON: %s", packet, e)
                raise
            except Exception as e:
                self.logger.error("Unexpected error while sending packet %s: %s", packet, e)
                raise
        else:
            self.logger.warning("Attempted to send packet but WebSocket is not connected")

    async def join_heartbeat_channel(self, device_id: str) -> None:
        """
        Subscribe to heartbeat data for a specific device.

        Args:
            device_id (str): The device ID to subscribe to for heartbeat data.
        """
        channel_name = f"hr:{device_id}"
        self.logger.info("Joining heartbeat channel for device: %s", device_id)
        await self.join_channel(channel_name)

    async def leave_heartbeat_channel(self, device_id: str) -> None:
        """
        Unsubscribe from heartbeat data for a specific device.

        Args:
            device_id (str): The device ID to unsubscribe from for heartbeat data.
        """
        channel_name = f"hr:{device_id}"
        self.logger.info("Leaving heartbeat channel for device: %s", device_id)
        await self.leave_channel(channel_name)

    async def join_clips_channel(self, device_id: str) -> None:
        """
        Subscribe to clip data for a specific device.

        Args:
            device_id (str): The device ID to subscribe to for clip data.
        """
        channel_name = f"clips:{device_id}"
        self.logger.info("Joining clips channel for device: %s", device_id)
        await self.join_channel(channel_name)

    async def leave_clips_channel(self, device_id: str) -> None:
        """
        Unsubscribe from clip data for a specific device.

        Args:
            device_id (str): The device ID to unsubscribe from for clip data.
        """
        channel_name = f"clips:{device_id}"
        self.logger.info("Leaving clips channel for device: %s", device_id)
        await self.leave_channel(channel_name)

    async def join_channel(self, channel_name: str) -> None:
        """
        Join a specific channel to receive data.

        This method sends a join packet for the specified channel. The 'channel_joined' 
        event will be fired when the server confirms the successful join.

        Args:
            channel_name (str): The name of the channel to join.
        """
        try:
            packet = {"topic": channel_name, "event": "phx_join", "payload": {}, "ref": 1}
            await self.send_packet(packet)
            self.logger.debug("Sent join request for channel: %s", channel_name)
        except websockets.exceptions.WebSocketException as e:
            self.logger.error("WebSocket error while joining channel %s: %s",
                              channel_name, e)
            raise
        # Keep broad exception catching for robustness in critical networking code
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Unexpected error while joining channel %s: %s",
                              channel_name, e)
            raise

    async def leave_channel(self, channel_name: str) -> None:
        """
        Leave a specific channel to stop receiving data.

        This method sends a leave packet for the specified channel. The 'channel_left'
        event will be fired when the server confirms the successful leave.

        Args:
            channel_name (str): The name of the channel to leave.
        """
        try:
            packet = {"topic": channel_name, "event": "phx_leave", "payload": {}, "ref": 2}
            await self.send_packet(packet)
            self.logger.debug("Sent leave request for channel: %s", channel_name)
        except websockets.exceptions.WebSocketException as e:
            self.logger.error("WebSocket error while leaving channel %s: %s",
                              channel_name, e)
            raise
        # Keep broad exception catching for robustness in critical networking code
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Unexpected error while leaving channel %s: %s",
                              channel_name, e)
            raise

    async def _heartbeat(self) -> None:
        """
        Send periodic heartbeat messages to maintain the WebSocket connection.

        This internal method runs in a loop while connected, sending heartbeat packets
        every 10 seconds to keep the connection alive.
        """
        self.logger.debug("Heartbeat task started")
        try:
            while self.connected:
                await self.send_packet({"topic": "phoenix", "event": "heartbeat",
                                        "payload": {}, "ref": 0})
                self.logger.debug("Heartbeat packet sent")
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            self.logger.debug("Heartbeat task cancelled")
        except websockets.exceptions.WebSocketException as e:
            self.logger.error("WebSocket error in heartbeat task: %s", e)
        # Keep broad exception catching for robustness in background task
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Unexpected error in heartbeat task: %s", e)
        finally:
            self.logger.debug("Heartbeat task ended")

    async def _receive(self) -> None:
        """
        Listen for incoming WebSocket messages and handle them.

        This internal method runs continuously while connected, processing incoming
        messages and firing appropriate events. If an exception occurs, it sets
        the connected flag to False and fires the 'disconnected' event.
        """
        self.logger.debug("Receive task started")
        try:
            if self.ws is not None:
                async for message in self.ws:
                    self.logger.debug("Received message: %s", message)
                    self._handle_message(message)
        except asyncio.CancelledError:
            self.logger.debug("Receive task cancelled")
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.warning("WebSocket connection closed: %s", e)
            self.connected = False
            self._fire_event('disconnected')
        except websockets.exceptions.WebSocketException as e:
            self.logger.error("WebSocket error in receive task: %s", e)
            self.connected = False
            self._fire_event('disconnected')
        # Keep broad exception catching for robustness in critical receive loop
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Unexpected error in receive task: %s", e)
            self.connected = False
            self._fire_event('disconnected')
        finally:
            self.logger.debug("Receive task ended")

    def _handle_message(self, message: Union[str, bytes]) -> None:
        """
        Process incoming WebSocket messages and fire appropriate events.

        This internal method parses JSON messages and fires 'heartbeat' events for
        heartrate data (topics starting with 'hr:') and 'clip' events for clip data
        (topics starting with 'clips:').

        Args:
            message: The raw WebSocket message to process.
        """
        try:
            # Convert bytes to string if necessary
            message_str = message if isinstance(message, str) else message.decode('utf-8')
            data = json.loads(message_str)
            topic = data.get("topic", "")
            event = data.get("event", "")
            payload = data.get("payload", {})
            ref = data.get("ref")

            # Log all messages for debugging (but not too verbose in production)
            self.logger.debug("Received message: topic=%s, event=%s, ref=%s", topic, event, ref)

            # Handle different message types
            if event == "phx_reply":
                self._handle_phoenix_reply(topic, payload, ref, data)
            elif topic.startswith("hr:"):
                self._handle_heartbeat_message(topic, payload)
            elif topic.startswith("clips:"):
                self._handle_clip_message(topic, payload)
            else:
                self.logger.debug("Received message for topic: %s, event: %s", topic, event)

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.error("Failed to parse message: %s", e)
        # Keep broad exception catching for robustness in message handling
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Unexpected error handling message: %s", e)

    def _handle_phoenix_reply(self, topic: str, payload: Dict[str, Any],
                              ref: Optional[int], data: Dict[str, Any]) -> None:
        """
        Handle Phoenix WebSocket reply messages (channel join/leave confirmations).

        Args:
            topic: The channel topic
            payload: The message payload
            ref: The message reference number
            data: The complete message data
        """
        status = payload.get("status")
        response = payload.get("response", {})

        if status == "ok":
            if ref == 1:  # Join confirmation (we use ref=1 for joins)
                self.logger.info("Channel join confirmed for topic: %s", topic)
                device_id = self._extract_device_id_from_topic(topic)
                self._fire_event('channel_joined', device_id)
            elif ref == 2:  # Leave confirmation (we use ref=2 for leaves)
                self.logger.info("Channel leave confirmed for topic: %s", topic)
                device_id = self._extract_device_id_from_topic(topic)
                self._fire_event('channel_left', device_id)
            else:
                self.logger.debug("Phoenix reply with status 'ok': %s", data)
        elif status == "error":
            self.logger.error("Channel operation failed for topic %s: %s", topic, response)
        else:
            self.logger.debug("Phoenix reply with status '%s': %s", status, data)

    def _extract_device_id_from_topic(self, topic: str) -> str:
        """
        Extract device ID from channel topic.

        Args:
            topic: The channel topic (e.g., "hr:device123" or "clips:device123")

        Returns:
            The extracted device ID or the original topic if no prefix matches
        """
        if topic.startswith("hr:"):
            return topic[3:]  # Remove "hr:" prefix
        if topic.startswith("clips:"):
            return topic[6:]  # Remove "clips:" prefix
        return topic

    def _handle_heartbeat_message(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Handle heartbeat messages.

        Args:
            topic: The heartbeat topic
            payload: The message payload containing heart rate data
        """
        hr = payload.get("hr")
        if hr is not None:
            self.logger.debug("Heartbeat data received for topic %s: HR=%s", topic, hr)
            self._fire_event('heartbeat', payload)

    def _handle_clip_message(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Handle clip messages.

        Args:
            topic: The clip topic
            payload: The message payload containing clip data
        """
        slug = payload.get("twitch_slug")
        if slug:
            self.logger.debug("Clip data received for topic %s: slug=%s", topic, slug)
            self._fire_event('clip', payload)

    def _fire_event(self, event: str, *args: Any) -> None:
        """
        Fire all registered handlers for a specific event.

        This internal method calls all registered event handlers for the given
        event type, passing any additional arguments to each handler.

        Args:
            event (str): The event type to fire.
            *args: Additional arguments to pass to the event handlers.
        """
        handlers = self._event_handlers.get(event, [])
        if handlers:
            self.logger.debug("Firing event '%s' to %d handler(s)", event, len(handlers))
            for handler in handlers:
                try:
                    handler(*args)
                # Keep broad exception catching to prevent one bad handler from breaking others
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error("Error in event handler for '%s': %s", event, e)
        else:
            self.logger.debug("No handlers registered for event: %s", event)


class Device:
    """
    Utility class for validating and extracting device IDs used in the HypeRate system.
    """

    VALID_ID_REGEX: RegexPattern = re.compile(r'^[a-zA-Z0-9]{3,8}$')

    @staticmethod
    def is_valid_device_id(device_id: str) -> bool:
        """
        Check if the provided device_id is valid.

        Args:
            device_id (str): The device ID to validate.

        Returns:
            bool: True if the device ID is valid or is 'internal-testing', False otherwise.
        """
        if device_id == "internal-testing":
            return True
        return bool(Device.VALID_ID_REGEX.match(device_id))

    @staticmethod
    def extract_device_id(input_str: str) -> Optional[str]:
        """
        Extract a device ID from a given string, which may be a URL or a raw device ID.

        Args:
            input_str (str): The input string containing a device ID or a URL.

        Returns:
            Optional[str]: The extracted device ID if found, otherwise None.
        """
        # First, try to match the HypeRate URL pattern
        hyperate_pattern = r'(?:https?://)?app\.hyperate\.io/([a-zA-Z0-9\-]+)(?:\?.*)?'
        match = re.search(hyperate_pattern, input_str)
        if match:
            return match.group(1)

        # If no URL match, check if the input itself is a valid device ID
        if re.match(r'^[a-zA-Z0-9\-]+$', input_str):
            return input_str

        return None
