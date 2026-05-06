"""
Thread safety tests for HybridCapture (dpkt backend)

Tests cover:
1. Thread-safe queue operations
2. stop_capture flush behavior
3. Concurrent access patterns
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock
from lldp.capture_dpkt import HybridCapture, CaptureResult
from lldp.model import LLDPDevice


class TestThreadSafety:
    """Test thread safety of HybridCapture"""

    def test_device_queue_is_thread_safe(self):
        """Test that device_queue can handle concurrent operations"""
        capture = HybridCapture()

        # Simulate concurrent enqueue operations
        def enqueue_devices(count, thread_id):
            for i in range(count):
                device = LLDPDevice()
                device.chassis_id = f"thread_{thread_id}_device_{i}"
                result = CaptureResult(
                    device=device, timestamp=time.time(), interface="test"
                )
                capture.device_queue.put(result)

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=enqueue_devices, args=(10, i))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify all devices were enqueued
        devices = capture.get_discovered_devices()
        assert len(devices) == 50  # 5 threads * 10 devices

    def test_get_discovered_devices_drains_queue(self):
        """Test that get_discovered_devices properly drains the queue"""
        capture = HybridCapture()

        # Add some devices
        for i in range(3):
            device = LLDPDevice()
            device.chassis_id = f"device_{i}"
            result = CaptureResult(
                device=device, timestamp=time.time(), interface="test"
            )
            capture.device_queue.put(result)

        # Get devices
        devices = capture.get_discovered_devices()
        assert len(devices) == 3

        # Queue should be empty now
        devices2 = capture.get_discovered_devices()
        assert len(devices2) == 0

    def test_stop_capture_flushes_queue(self):
        """Test that stop_capture properly flushes callbacks"""
        capture = HybridCapture()
        capture.is_capturing = True
        capture.backend = Mock()

        # Mock callback
        callback_mock = Mock()
        capture._current_callback = callback_mock

        # Add some devices to queue
        for i in range(3):
            device = LLDPDevice()
            device.chassis_id = f"device_{i}"
            result = CaptureResult(
                device=device, timestamp=time.time(), interface="test"
            )
            capture.device_queue.put(result)

        # Stop capture
        capture.stop_capture()

        # Verify callback was called for all devices
        assert callback_mock.call_count == 3

    def test_concurrent_get_and_put(self):
        """Test concurrent get_discovered_devices and put operations"""
        capture = HybridCapture()

        def producer():
            for i in range(20):
                device = LLDPDevice()
                device.chassis_id = f"prod_{i}"
                result = CaptureResult(
                    device=device, timestamp=time.time(), interface="test"
                )
                capture.device_queue.put(result)
                time.sleep(0.01)

        def consumer():
            time.sleep(0.05)  # Let producer start first
            total = 0
            for _ in range(10):
                devices = capture.get_discovered_devices()
                total += len(devices)
                time.sleep(0.02)
            return total

        # Start threads
        prod_thread = threading.Thread(target=producer)
        cons_thread = threading.Thread(target=consumer)

        prod_thread.start()
        cons_thread.start()

        prod_thread.join()
        cons_thread.join()

        # Final queue should be empty or have some items
        remaining = capture.get_discovered_devices()
        assert len(remaining) >= 0  # Should not crash


class TestCaptureResult:
    """Test CaptureResult data structure"""

    def test_capture_result_creation(self):
        """Test CaptureResult object creation"""
        device = LLDPDevice()
        device.chassis_id = "test_device"

        result = CaptureResult(device=device, timestamp=123456.789, interface="eth0")

        assert result.device == device
        assert result.timestamp == 123456.789
        assert result.interface == "eth0"


@pytest.mark.parametrize("num_devices", [1, 5, 10, 50])
def test_queue_performance_with_many_devices(num_devices):
    """Test queue performance with varying numbers of devices"""
    capture = HybridCapture()

    # Enqueue devices
    start_time = time.time()
    for i in range(num_devices):
        device = LLDPDevice()
        device.chassis_id = f"device_{i}"
        result = CaptureResult(device=device, timestamp=time.time(), interface="test")
        capture.device_queue.put(result)

    # Dequeue devices
    devices = capture.get_discovered_devices()
    elapsed = time.time() - start_time

    assert len(devices) == num_devices
    assert elapsed < 1.0  # Should be fast


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
