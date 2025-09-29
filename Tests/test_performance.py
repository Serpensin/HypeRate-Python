"""
Performance benchmarks and stress tests for the HypeRate library.

These tests measure performance characteristics and test the library
under stress conditions to ensure it can handle high-load scenarios.
"""
import asyncio
import json
import time
import unittest
import gc
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any
import statistics

import pytest

from lib.hyperate import HypeRate, Device

# Import token management from conftest
try:
    from conftest import get_api_token
except ImportError:
    # Fallback if conftest is not available (direct script execution)
    def get_api_token():
        """Fallback token function for direct script execution."""
        return "test_token"


@pytest.mark.benchmark
class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmark tests."""

    def setUp(self):
        """Set up performance test fixtures."""
        # Use token from conftest or fallback to test token
        api_token = get_api_token() or "test_token"
        self.client = HypeRate(api_token)
        # Store original logger level to restore later
        self.original_logger_level = self.client.logger.level
        # Disable debug logging for performance tests
        self.client.logger.setLevel(40)  # ERROR level only

    def tearDown(self):
        """Restore test fixtures."""
        # Restore original logger level
        self.client.logger.setLevel(self.original_logger_level)

    def test_event_registration_performance(self, benchmark=None):
        """Benchmark event handler registration performance."""
        def register_handlers():
            handlers = [Mock() for _ in range(1000)]
            for i, handler in enumerate(handlers):
                event_type = ['heartbeat', 'clip', 'connected', 'disconnected'][i % 4]
                self.client.on(event_type, handler)
            return len(handlers)

        if benchmark:
            result = benchmark(register_handlers)
            self.assertEqual(result, 1000)
        else:
            # Fallback for non-benchmark execution
            handlers = [Mock() for _ in range(1000)]

            start_time = time.perf_counter()

            for i, handler in enumerate(handlers):
                event_type = ['heartbeat', 'clip', 'connected', 'disconnected'][i % 4]
                self.client.on(event_type, handler)

            end_time = time.perf_counter()
            registration_time = end_time - start_time

            # Should register handlers efficiently
            self.assertLess(registration_time, 1.0)

            # Calculate registrations per second
            registrations_per_second = len(handlers) / registration_time

            print(f"\nEvent Registration Performance:")
            print(f"  Registered {len(handlers)} handlers in {registration_time:.4f} seconds")
            print(f"  Rate: {registrations_per_second:.0f} registrations/second")

            # Verify all handlers were registered
            total_handlers = sum(len(handlers) for handlers in self.client._event_handlers.values())
            self.assertEqual(total_handlers, 1000)

    def test_message_processing_performance(self, benchmark=None):
        """Benchmark message processing performance."""
        # Create test messages
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

        def process_messages():
            nonlocal processed_count
            processed_count = 0
            for message in messages:
                self.client._handle_message(message)
            return processed_count

        if benchmark:
            result = benchmark(process_messages)
            self.assertEqual(result, len(messages))
        else:
            # Fallback for non-benchmark execution
            start_time = time.perf_counter()
            result = process_messages()
            end_time = time.perf_counter()
            processing_time = end_time - start_time

            self.assertLess(processing_time, 2.0)
            messages_per_second = len(messages) / processing_time

            print(f"\nMessage Processing Performance:")
            print(f"  Processed {len(messages)} messages in {processing_time:.4f} seconds")
            print(f"  Rate: {messages_per_second:.0f} messages/second")
            print(f"  Verified {result} events fired")

            self.assertEqual(result, len(messages))

    def test_event_firing_performance(self, benchmark=None):
        """Benchmark event firing performance with multiple handlers."""
        handler_count = 1000
        handlers = [Mock() for _ in range(handler_count)]

        for handler in handlers:
            self.client.on('heartbeat', handler)

        test_payload = {"hr": 75}

        def fire_events():
            iterations = 100  # Reduced for benchmark
            for _ in range(iterations):
                self.client._fire_event('heartbeat', test_payload)
            return iterations

        if benchmark:
            result = benchmark(fire_events)
            # Verify handlers were called
            for handler in handlers[:10]:  # Check first 10 handlers
                self.assertGreater(handler.call_count, 0)
        else:
            # Fallback for non-benchmark execution
            iterations = 1000

            start_time = time.perf_counter()

            for _ in range(iterations):
                self.client._fire_event('heartbeat', test_payload)

            end_time = time.perf_counter()
            firing_time = end_time - start_time

            events_per_second = iterations / firing_time
            handler_calls_per_second = (iterations * handler_count) / firing_time

            print(f"\nEvent Firing Performance:")
            print(f"  Fired {iterations} events with {handler_count} handlers each")
            print(f"  Total time: {firing_time:.4f} seconds")
            print(f"  Rate: {events_per_second:.0f} events/second")
            print(f"  Handler calls: {handler_calls_per_second:.0f} calls/second")

            # Verify all handlers were called for each event
            for handler in handlers:
                self.assertEqual(handler.call_count, iterations)

    def test_device_validation_performance(self, benchmark=None):
        """Benchmark device ID validation performance."""
        valid_ids = [f"dev{i:04d}" for i in range(1000)]
        invalid_ids = [f"toolongdeviceid{i}" for i in range(1000)]
        all_ids = valid_ids + invalid_ids

        def validate_all():
            return [Device.is_valid_device_id(device_id) for device_id in all_ids]

        if benchmark:
            results = benchmark(validate_all)
            valid_count = sum(results[:1000])
            invalid_count = sum(results[1000:])
            self.assertEqual(valid_count, 1000)
            self.assertEqual(invalid_count, 0)
        else:
            # Fallback for non-benchmark execution
            start_time = time.perf_counter()
            validation_results = validate_all()
            end_time = time.perf_counter()
            validation_time = end_time - start_time

            validations_per_second = len(all_ids) / validation_time

            print(f"\nDevice Validation Performance:")
            print(f"  Validated {len(all_ids)} device IDs in {validation_time:.4f} seconds")
            print(f"  Rate: {validations_per_second:.0f} validations/second")

            valid_count = sum(validation_results[:1000])
            invalid_count = sum(validation_results[1000:])

            self.assertEqual(valid_count, 1000)
            self.assertEqual(invalid_count, 0)

    def test_device_extraction_performance(self, benchmark=None):
        """Benchmark device ID extraction performance."""
        test_inputs = []
        for i in range(1000):  # Reduced for benchmark
            if i % 3 == 0:
                test_inputs.append(f"https://app.hyperate.io/dev{i:04d}")
            elif i % 3 == 1:
                test_inputs.append(f"http://app.hyperate.io/test{i:04d}")
            else:
                test_inputs.append(f"dev{i:04d}")

        def extract_all():
            return [Device.extract_device_id(input_str) for input_str in test_inputs]

        if benchmark:
            results = benchmark(extract_all)
            successful_extractions = sum(1 for result in results if result is not None)
            self.assertEqual(successful_extractions, len(test_inputs))
        else:
            # Fallback for non-benchmark execution
            start_time = time.perf_counter()
            extraction_results = extract_all()
            end_time = time.perf_counter()
            extraction_time = end_time - start_time

            extractions_per_second = len(test_inputs) / extraction_time

            print(f"\nDevice Extraction Performance:")
            print(f"  Extracted from {len(test_inputs)} inputs in {extraction_time:.4f} seconds")
            print(f"  Rate: {extractions_per_second:.0f} extractions/second")

            successful_extractions = sum(1 for result in extraction_results if result is not None)
            self.assertEqual(successful_extractions, len(test_inputs))


@pytest.mark.benchmark
class TestStressTests(unittest.TestCase):
    """Stress tests for the HypeRate library."""

    def setUp(self):
        """Set up stress test fixtures."""
        # Use token from conftest or fallback to test token
        api_token = get_api_token() or "test_token"
        self.client = HypeRate(api_token)
        # Store original logger disabled state to restore later
        self.original_logger_disabled = getattr(self.client.logger, 'disabled', False)
        # Disable all logging for stress tests
        self.client.logger.disabled = True

    def tearDown(self):
        """Restore test fixtures."""
        # Restore original logger disabled state
        self.client.logger.disabled = self.original_logger_disabled

    def test_memory_usage_under_load(self, benchmark=None):
        """Test memory usage under sustained load."""
        def memory_load_test():
            initial_memory = self._get_memory_usage()

            # Create handlers
            handlers = []
            for i in range(50):  # Reduced for benchmark
                handler = Mock()
                handlers.append(handler)
                self.client.on('heartbeat', handler)

            # Process messages
            for i in range(500):  # Reduced for benchmark
                message = json.dumps({
                    "topic": f"hr:device{i % 100}",
                    "payload": {"hr": 70 + (i % 30)}
                })
                self.client._handle_message(message)

                if i % 100 == 0:
                    gc.collect()

            gc.collect()
            final_memory = self._get_memory_usage()
            memory_growth = final_memory - initial_memory

            # Clean up
            handlers.clear()
            self.client._event_handlers = {key: [] for key in self.client._event_handlers}
            gc.collect()

            return memory_growth

        if benchmark:
            memory_growth = benchmark(memory_load_test)
            self.assertLess(memory_growth, 100.0)
        else:
            # Original fallback code
            initial_memory = self._get_memory_usage()

            handlers = []
            for i in range(100):
                handler = Mock()
                handlers.append(handler)
                self.client.on('heartbeat', handler)

            for i in range(1000):
                message = json.dumps({
                    "topic": f"hr:device{i % 100}",
                    "payload": {"hr": 70 + (i % 30)}
                })
                self.client._handle_message(message)

                if i % 100 == 0:
                    gc.collect()

            gc.collect()

            final_memory = self._get_memory_usage()
            memory_growth = final_memory - initial_memory

            print(f"\nMemory Usage Stress Test:")
            print(f"  Initial memory: {initial_memory:.2f} MB")
            print(f"  Final memory: {final_memory:.2f} MB")
            print(f"  Memory growth: {memory_growth:.2f} MB")

            self.assertLess(memory_growth, 100.0)

            handlers.clear()
            self.client._event_handlers = {key: [] for key in self.client._event_handlers}
            gc.collect()

    def test_concurrent_access_stress(self):
        """Test concurrent access from multiple threads."""
        results = {"messages_processed": 0, "events_fired": 0, "errors": 0}
        lock = threading.Lock()

        def thread_worker(thread_id, message_count):
            """Worker function for thread-based stress testing."""
            try:
                # Each thread processes messages
                for i in range(message_count):
                    message = json.dumps({
                        "topic": f"hr:thread{thread_id}",
                        "payload": {"hr": 70 + (i % 30), "thread": thread_id}
                    })

                    self.client._handle_message(message)

                    with lock:
                        results["messages_processed"] += 1

            except Exception as e:
                with lock:
                    results["errors"] += 1
                print(f"Thread {thread_id} error: {e}")

        # Add event handler to track fired events
        def track_events(payload):
            with lock:
                results["events_fired"] += 1

        self.client.on('heartbeat', track_events)

        # Run concurrent threads
        thread_count = 10
        messages_per_thread = 1000

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = []
            for thread_id in range(thread_count):
                future = executor.submit(thread_worker, thread_id, messages_per_thread)
                futures.append(future)

            # Wait for all threads to complete
            for future in futures:
                future.result()

        end_time = time.perf_counter()
        total_time = end_time - start_time

        expected_messages = thread_count * messages_per_thread

        print(f"\nConcurrent Access Stress Test:")
        print(f"  Threads: {thread_count}")
        print(f"  Messages per thread: {messages_per_thread}")
        print(f"  Total time: {total_time:.4f} seconds")
        print(f"  Messages processed: {results['messages_processed']}")
        print(f"  Events fired: {results['events_fired']}")
        print(f"  Errors: {results['errors']}")
        print(f"  Messages/second: {results['messages_processed'] / total_time:.0f}")

        # Verify all messages were processed
        self.assertEqual(results["messages_processed"], expected_messages)
        self.assertEqual(results["events_fired"], expected_messages)
        self.assertEqual(results["errors"], 0)

    def test_large_payload_stress(self):
        """Test handling of very large payloads."""
        payload_sizes = [1024, 10240, 102400, 1024000]  # 1KB to 1MB
        processing_times = []

        def large_payload_handler(payload):
            # Just verify we can access the payload
            self.assertIn("hr", payload)
            self.assertIn("large_data", payload)

        self.client.on('heartbeat', large_payload_handler)

        for size in payload_sizes:
            # Create large payload
            large_data = "x" * size
            message = json.dumps({
                "topic": "hr:stress_test",
                "payload": {
                    "hr": 75,
                    "large_data": large_data
                }
            })

            # Measure processing time
            start_time = time.perf_counter()
            self.client._handle_message(message)
            end_time = time.perf_counter()

            processing_time = end_time - start_time
            processing_times.append(processing_time)

            print(f"Payload size: {size:7d} bytes, Processing time: {processing_time:.6f} seconds")

        print(f"\nLarge Payload Stress Test:")
        print(f"  Tested payload sizes: {payload_sizes}")
        print(f"  Processing times: {[f'{t:.6f}' for t in processing_times]}")
        print(f"  Average time: {statistics.mean(processing_times):.6f} seconds")
        print(f"  Max time: {max(processing_times):.6f} seconds")

        # Even the largest payload should process quickly (increased threshold to 200ms)
        self.assertLess(max(processing_times), 0.2)

    def test_handler_exception_storm(self):
        """Test behavior when many handlers throw exceptions."""
        exception_count = 0
        successful_count = 0

        # Create handlers that fail at different rates
        def failing_handler_25(payload):
            if hash(str(payload)) % 4 == 0:  # Fail 25% of the time
                raise ValueError("Handler failure")

        def failing_handler_50(payload):
            if hash(str(payload)) % 2 == 0:  # Fail 50% of the time
                raise RuntimeError("Handler failure")

        def successful_handler(payload):
            nonlocal successful_count
            successful_count += 1

        def exception_counting_handler(payload):
            nonlocal exception_count
            try:
                # This handler always fails
                raise Exception("Always fails")
            except:
                exception_count += 1
                raise

        # Register all handlers
        self.client.on('heartbeat', failing_handler_25)
        self.client.on('heartbeat', failing_handler_50)
        self.client.on('heartbeat', successful_handler)
        self.client.on('heartbeat', exception_counting_handler)

        # Process many messages
        message_count = 10000
        start_time = time.perf_counter()

        for i in range(message_count):
            message = json.dumps({
                "topic": "hr:exception_test",
                "payload": {"hr": 70 + (i % 30), "iteration": i}
            })

            self.client._handle_message(message)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        print(f"\nHandler Exception Storm Test:")
        print(f"  Processed {message_count} messages in {total_time:.4f} seconds")
        print(f"  Successful handler calls: {successful_count}")
        print(f"  Exception counting handler calls: {exception_count}")
        print(f"  Messages/second: {message_count / total_time:.0f}")

        # Despite exceptions, the successful handler should have been called for every message
        self.assertEqual(successful_count, message_count)
        self.assertEqual(exception_count, message_count)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            # Fallback if psutil is not available - estimate based on object sizes
            import sys
            total_size = 0
            total_size += sys.getsizeof(self.client)
            total_size += sys.getsizeof(self.client._event_handlers)
            for handlers in self.client._event_handlers.values():
                total_size += sys.getsizeof(handlers)
                for handler in handlers:
                    total_size += sys.getsizeof(handler)
            return total_size / 1024 / 1024


class TestAsyncPerformance(unittest.IsolatedAsyncioTestCase):
    """Async performance tests."""

    async def test_async_task_performance(self, benchmark=None):
        """Test performance of async task creation and management."""
        api_token = get_api_token() or "test_token"
        client = HypeRate(api_token)

        mock_ws = AsyncMock()
        async def empty_iterator():
            return
            yield

        mock_ws.__aiter__ = lambda: empty_iterator()
        mock_ws.close = AsyncMock()

        async def connection_cycle():
            cycle_count = 10  # Reduced for benchmark
            
            with patch('websockets.connect') as mock_connect:
                async def mock_connect_func(*args, **kwargs):
                    return mock_ws

                mock_connect.side_effect = mock_connect_func

                for i in range(cycle_count):
                    await client.connect()
                    await asyncio.sleep(0.001)
                    await client.disconnect()
                    await asyncio.sleep(0.001)
            
            return cycle_count

        if benchmark:
            # For async benchmarks, we need to handle them specially
            # Since pytest-benchmark doesn't directly support async, we'll time manually
            start_time = time.perf_counter()
            result = await connection_cycle()
            end_time = time.perf_counter()
            
            total_time = end_time - start_time
            cycles_per_second = result / total_time
            
            print(f"\nAsync Task Performance Test (Benchmark):")
            print(f"  Completed {result} connect/disconnect cycles")
            print(f"  Total time: {total_time:.4f} seconds")
            print(f"  Rate: {cycles_per_second:.1f} cycles/second")
            
            self.assertGreater(cycles_per_second, 1)  # At least 1 cycle per second
        else:
            # Original fallback code
            cycle_count = 100
            start_time = time.perf_counter()

            with patch('websockets.connect') as mock_connect:
                async def mock_connect_func(*args, **kwargs):
                    return mock_ws

                mock_connect.side_effect = mock_connect_func

                for i in range(cycle_count):
                    await client.connect()
                    self.assertIsNotNone(client._receive_task)
                    self.assertIsNotNone(client._heartbeat_task)
                    await asyncio.sleep(0.001)
                    await client.disconnect()
                    await asyncio.sleep(0.001)

                    if client._receive_task:
                        self.assertTrue(client._receive_task.cancelled() or client._receive_task.done())
                    if client._heartbeat_task:
                        self.assertTrue(client._heartbeat_task.cancelled() or client._heartbeat_task.done())

            end_time = time.perf_counter()
            total_time = end_time - start_time
            cycles_per_second = cycle_count / total_time

            print(f"\nAsync Task Performance Test:")
            print(f"  Completed {cycle_count} connect/disconnect cycles")
            print(f"  Total time: {total_time:.4f} seconds")
            print(f"  Rate: {cycles_per_second:.1f} cycles/second")

            self.assertGreater(cycles_per_second, 5)


def run_performance_suite():
    """Run the complete performance test suite with reporting."""
    print("=" * 80)
    print("HYPERATE LIBRARY PERFORMANCE TEST SUITE")
    print("=" * 80)

    # Run performance tests
    suite = unittest.TestSuite()

    # Add performance benchmark tests
    suite.addTest(unittest.makeSuite(TestPerformanceBenchmarks))
    suite.addTest(unittest.makeSuite(TestStressTests))
    suite.addTest(unittest.makeSuite(TestAsyncPerformance))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 80)
    print(f"PERFORMANCE TESTS COMPLETED")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 80)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_performance_suite()
    sys.exit(0 if success else 1)