# Official HypeRate Python Bindings

[![Code Quality](https://github.com/Serpensin/HypeRate-Python/workflows/Code%20Quality/badge.svg)](https://github.com/Serpensin/HypeRate-Python/actions/workflows/code-quality.yml)
[![Test Suite](https://github.com/Serpensin/HypeRate-Python/workflows/Test%20Suite/badge.svg)](https://github.com/Serpensin/HypeRate-Python/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/Serpensin/HypeRate-Python/branch/master/graph/badge.svg)](https://codecov.io/gh/Serpensin/HypeRate-Python)\
[![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://github.com/Serpensin/HypeRate-Python)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/hyperate.svg)](https://badge.fury.io/py/hyperate)

A Python client library for connecting to the HypeRate WebSocket API to receive real-time heartbeat and clip data.

## Features

- **Real-time heartbeat monitoring** - Subscribe to live heart rate data from HypeRate devices
- **Clip notifications** - Receive notifications when clips are created
- **Async/await support** - Built with asyncio for efficient WebSocket handling
- **Event-driven architecture** - Register handlers for different event types
- **Type hints** - Full type annotation support for better IDE integration
- **Comprehensive logging** - Built-in logging with configurable levels
- **Error handling** - Robust error handling and connection management

## Supported Python Versions

This library supports and is tested on:
- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13
- Python 3.14

## Installation

```bash
pip install hyperate
```

## Quick Start

```python
import asyncio
import hyperate

async def main():
    # Initialize and connect to HypeRate
    client = hyperate.HypeRate("your_api_token_here")
    await client.connect()

    # Define and register event handlers
    def on_heartbeat(data):
        print(f"Heartbeat received: {data['hr']} BPM")

    def on_connected():
        print("Connected to HypeRate!")

    def on_clip(data):
        print(f"New clip: {data['twitch_slug']}")

    client.on('heartbeat', on_heartbeat)
    client.on('connected', on_connected)  # Note: this fires after connection is already established
    client.on('clip', on_clip)

    # Subscribe to a device's heartbeat data
    await client.join_heartbeat_channel("internal-testing")  # Use "internal-testing" for testing

    # Keep the connection alive
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        await client.disconnect()

# Run the client
if __name__ == "__main__":
    asyncio.run(main())
```

### Alternative Quick Start (Lambda Style)

```python
import asyncio
from hyperate import HypeRate

async def main():
    client = HypeRate("your_api_token_here")
    await client.connect()

    # Register handlers with lambda functions
    client.on('heartbeat', lambda data: print(f"❤️ {data['hr']} BPM"))
    client.on('clip', lambda data: print(f"🎬 Clip: {data['twitch_slug']}"))

    await client.join_heartbeat_channel("internal-testing")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await client.disconnect()

asyncio.run(main())
```

## API Documentation

### HypeRate Class

#### Constructor
```python
HypeRate(api_token: str, base_url: str = "wss://app.hyperate.io/socket/websocket", logger: Optional[logging.Logger] = None)
```

#### Methods
- `connect()` - Connect to the HypeRate WebSocket
- `disconnect()` - Disconnect from the WebSocket
- `join_heartbeat_channel(device_id)` - Subscribe to heartbeat data for a device
- `leave_heartbeat_channel(device_id)` - Unsubscribe from heartbeat data
- `join_clips_channel(device_id)` - Subscribe to clip notifications for a device
- `leave_clips_channel(device_id)` - Unsubscribe from clip notifications
- `on(event, handler)` - Register an event handler

#### Events
- `connected` - Fired when connected to HypeRate
- `disconnected` - Fired when disconnected from HypeRate
- `heartbeat` - Fired when heartbeat data is received
- `clip` - Fired when clip data is received
- `channel_joined` - Fired when a channel is successfully joined
- `channel_left` - Fired when a channel is successfully left

#### Usage Notes
- Connect to HypeRate first with `await client.connect()` before registering handlers
- Use `"internal-testing"` as device ID for testing purposes
- Event handlers registered after connection won't receive the initial `connected` event
- Use `while True:` for the main loop as the client manages the connection state internally

### Device Class

Utility class for device ID validation and extraction.

#### Methods
- `is_valid_device_id(device_id)` - Check if a device ID is valid
- `extract_device_id(input_str)` - Extract device ID from URL or string

## Development

### Setting up the development environment

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -r .\Tests\test_requirements.txt
   ```
3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

### Running Tests

Use the comprehensive test runner:

```bash
# Run all tests
python Tests/run_tests.py --all

# Run specific test types
python Tests/run_tests.py --unit           # Unit tests only
python Tests/run_tests.py --integration    # Mocked scenario tests
python Tests/run_tests.py --real-integration --token=your_token  # Real API integration
python Tests/run_tests.py --performance    # Performance tests

# Run with coverage
python Tests/run_tests.py --coverage

# Run code quality checks
python Tests/run_tests.py --lint
```

#### Real Integration Tests

To run tests against the actual HypeRate API, provide your API token via command line:

```bash
# Using pytest (recommended)
python -m pytest Tests/test_real_integration.py --token=your_actual_api_token_here

# Using direct script execution
python Tests/test_real_integration.py --token=your_actual_api_token_here

# Using the test runner with token
python Tests/run_tests.py --real-integration --token=your_actual_api_token_here
```

### Code Quality

This project maintains high code quality standards:

- **Code Quality Checks**: PyLint (10.0/10.0), Mypy (strict mode), and Flake8 style checking
- **Test Coverage**: Minimum 85% code coverage required
- **Comprehensive Testing**: Unit, integration, and performance tests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code quality checks pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Links

- [HypeRate Website](https://hyperate.io/)
- [Documentation](https://github.com/Serpensin/HypeRate-Python#readme)
- [PyPI Package](https://pypi.org/project/hyperate/)
- [GitHub Repository](https://github.com/Serpensin/HypeRate-Python)

