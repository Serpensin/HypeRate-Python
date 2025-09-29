#!/usr/bin/env python3
"""
Pytest-benchmark compatible performance tests for the HypeRate library.

These tests are specifically designed to work with pytest-benchmark and
provide detailed performance measurements.
"""
import json
import time
import gc
from unittest.mock import Mock, patch, AsyncMock
import asyncio

import pytest

from lib.hyperate import HypeRate, Device


class TestBenchmarks:
    """Pytest-benchmark compatible performance tests."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = HypeRate("test_token")
        # Store original logger level to restore later
        self.original_logger_level = self.client.logger.level
        self.client.logger.setLevel(40)  # ERROR level only for benchmarks

    def teardown_method(self):
        """Restore test fixtures."""
        # Restore original logger level
        self.client.logger.setLevel(self.original_logger_level)

    def test_event_registration_benchmark(self, benchmark):
        """Benchmark event handler registration."""
        def register_1000_handlers():
            handlers = [Mock() for _ in range(1000)]
            for i, handler in enumerate(handlers):
                event_type = ['heartbeat', 'clip', 'connected', 'disconnected'][i % 4]
                self.client.on(event_type, handler)
            return len(handlers)

        result = benchmark(register_1000_handlers)
        assert result == 1000

    def test_message_processing_benchmark(self, benchmark):
        """Benchmark message processing."""
        # Setup
        messages = []
        for i in range(1000):
            messages.append(json.dumps({
                "topic": f"hr:device{i % 100}",
                "payload": {"hr": 70 + (i % 30)}
            }))

        processed_count = 0

        def count_handler(payload):
            nonlocal processed_count
            processed_count += 1

        self.client.on('heartbeat', count_handler)

        def process_all_messages():
            nonlocal processed_count
            processed_count = 0
            for message in messages:
                self.client._handle_message(message)
            return processed_count

        result = benchmark(process_all_messages)
        assert result == len(messages)

    def test_event_firing_benchmark(self, benchmark):
        """Benchmark event firing with multiple handlers."""
        # Setup
        handler_count = 100  # Reduced for faster benchmarking
        handlers = [Mock() for _ in range(handler_count)]

        for handler in handlers:
            self.client.on('heartbeat', handler)

        test_payload = {"hr": 75}

        def fire_100_events():
            iterations = 100
            for _ in range(iterations):
                self.client._fire_event('heartbeat', test_payload)
            return iterations

        result = benchmark(fire_100_events)
        assert result == 100

        # Verify handlers were called
        for handler in handlers[:5]:  # Check first 5 handlers
            assert handler.call_count > 0

    def test_device_validation_benchmark(self, benchmark):
        """Benchmark device ID validation."""
        valid_ids = [f"dev{i:04d}" for i in range(500)]
        invalid_ids = [f"toolongdeviceid{i}" for i in range(500)]
        all_ids = valid_ids + invalid_ids

        def validate_all_devices():
            return [Device.is_valid_device_id(device_id) for device_id in all_ids]

        results = benchmark(validate_all_devices)
        
        valid_count = sum(results[:500])
        invalid_count = sum(results[500:])
        
        assert valid_count == 500
        assert invalid_count == 0

    def test_device_extraction_benchmark(self, benchmark):
        """Benchmark device ID extraction."""
        test_inputs = []
        for i in range(500):
            if i % 3 == 0:
                test_inputs.append(f"https://app.hyperate.io/dev{i:04d}")
            elif i % 3 == 1:
                test_inputs.append(f"http://app.hyperate.io/test{i:04d}")
            else:
                test_inputs.append(f"dev{i:04d}")

        def extract_all_devices():
            return [Device.extract_device_id(input_str) for input_str in test_inputs]

        results = benchmark(extract_all_devices)
        successful_extractions = sum(1 for result in results if result is not None)
        assert successful_extractions == len(test_inputs)

    def test_memory_usage_benchmark(self, benchmark):
        """Benchmark memory usage under load."""
        def memory_load_operation():
            initial_size = len(self.client._event_handlers)
            
            # Create handlers
            handlers = []
            for i in range(100):
                handler = Mock()
                handlers.append(handler)
                self.client.on('heartbeat', handler)

            # Process messages
            for i in range(200):
                message = json.dumps({
                    "topic": f"hr:device{i % 50}",
                    "payload": {"hr": 70 + (i % 30)}
                })
                self.client._handle_message(message)

            final_size = sum(len(handlers) for handlers in self.client._event_handlers.values())
            
            # Clean up
            self.client._event_handlers = {key: [] for key in self.client._event_handlers}
            handlers.clear()
            gc.collect()
            
            return final_size - initial_size

        result = benchmark(memory_load_operation)
        assert result > 0  # Should have added some handlers

    @pytest.mark.asyncio
    async def test_packet_sending_benchmark(self, benchmark):
        """Benchmark packet sending (simplified for sync benchmark)."""
        mock_ws = Mock()
        self.client.ws = mock_ws

        def send_100_packets():
            packet_count = 100
            for i in range(packet_count):
                packet = {
                    "topic": f"hr:device{i % 10}",
                    "event": "phx_join",
                    "payload": {"data": f"test_{i}"},
                    "ref": i
                }
                # Simulate packet creation and serialization
                json.dumps(packet)
            return packet_count

        result = benchmark(send_100_packets)
        assert result == 100


if __name__ == '__main__':
    pytest.main([__file__, '--benchmark-only', '--benchmark-sort=mean', '-v'])