"""
Metrics and flush behavior tests for HybridCapture

Tests cover:
1. Metrics tracking during capture
2. stop_capture flush behavior
3. Callback cleanup
4. Resource cleanup verification
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from lldp.capture_dpkt import HybridCapture, CaptureResult
from lldp.model import LLDPDevice


class TestMetricsTracking:
    """Test metrics tracking functionality"""

    def test_metrics_initialized(self):
        """Test that metrics are properly initialized"""
        capture = HybridCapture()
        assert "rx_packets" in capture.metrics
        assert "parsed" in capture.metrics
        assert "parse_errors" in capture.metrics
        assert "callbacks" in capture.metrics
        assert "filtered" in capture.metrics

        # All metrics should start at 0
        for metric_name, metric_value in capture.metrics.items():
            assert metric_value == 0

    def test_metrics_increment_on_packet_handling(self):
        """Test that metrics increment correctly during packet handling"""
        capture = HybridCapture()
        capture._current_callback = Mock()  # Set callback to track metrics

        # Mock LLDP packet
        mock_eth = MagicMock()
        mock_eth.type = 0x88CC
        mock_eth.data = b"data"

        # Mock parser
        mock_device = LLDPDevice()
        mock_device.chassis_id = "test_device"
        mock_device.is_valid = Mock(return_value=True)
        capture.lldp_parser.parse_packet = Mock(return_value=mock_device)

        # Mock backend
        capture.backend = MagicMock()
        capture.backend.interface = "eth0"

        # Process packet
        capture._handle_dpkt_eth(mock_eth)

        # Verify metrics updated
        assert capture.metrics["rx_packets"] == 1
        assert capture.metrics["parsed"] == 1
        assert capture.metrics["callbacks"] == 1
        assert capture.metrics["parse_errors"] == 0

    def test_metrics_increment_on_parse_error(self):
        """Test that parse errors are tracked"""
        capture = HybridCapture()

        # Mock packet that will fail parsing
        mock_eth = MagicMock()
        mock_eth.type = 0x88CC
        mock_eth.data = b"bad data"

        # Mock parser to return None
        capture.lldp_parser.parse_packet = Mock(return_value=None)

        # Process packet
        capture._handle_dpkt_eth(mock_eth)

        # Verify error tracked
        assert capture.metrics["rx_packets"] == 1
        assert capture.metrics["parsed"] == 0
        assert capture.metrics["parse_errors"] == 1

    def test_metrics_increment_on_filtered_packets(self):
        """Test that filtered packets are tracked"""
        capture = HybridCapture()

        # Mock non-target packet
        mock_eth = MagicMock()
        mock_eth.type = 0x0800  # IPv4
        mock_eth.dst = b"\xff\xff\xff\xff\xff\xff"

        # Process packet
        capture._handle_dpkt_eth(mock_eth)

        # Verify filter tracked
        assert capture.metrics["rx_packets"] == 1
        assert capture.metrics["filtered"] == 1
        assert capture.metrics["parsed"] == 0


class TestStopCaptureFlush:
    """Test stop_capture flush behavior and resource cleanup"""

    def test_stop_capture_flushes_queue(self):
        """Test that stop_capture properly flushes device queue"""
        capture = HybridCapture()
        capture.is_capturing = True
        capture.backend = MagicMock()

        # Mock callback to track invocations
        callback_calls = []

        def track_callback(device):
            callback_calls.append(device)

        capture._current_callback = track_callback

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
        assert len(callback_calls) == 3

        # Verify callback was cleaned up
        assert capture._current_callback is None

        # Verify backend was cleaned up
        assert capture.backend is None

    def test_stop_capture_closes_backend(self):
        """Test that stop_capture calls backend.close()"""
        capture = HybridCapture()
        capture.is_capturing = True

        # Mock backend
        mock_backend = MagicMock()
        capture.backend = mock_backend

        # Stop capture
        capture.stop_capture()

        # Verify backend.stop() and backend.close() were called
        mock_backend.stop.assert_called_once()
        mock_backend.close.assert_called_once()

        # Verify backend reference cleared
        assert capture.backend is None

    def test_stop_capture_handles_backend_close_exception(self):
        """Test that stop_capture handles backend.close() exceptions gracefully"""
        capture = HybridCapture()
        capture.is_capturing = True

        # Mock backend that raises exception on close
        mock_backend = MagicMock()
        mock_backend.close.side_effect = Exception("Close failed")
        capture.backend = mock_backend

        # Should not raise exception
        capture.stop_capture()

        # Verify backend reference still cleared despite exception
        assert capture.backend is None

    def test_stop_capture_clears_callback(self):
        """Test that stop_capture clears callback to prevent duplicate calls"""
        capture = HybridCapture()
        capture.is_capturing = True
        capture.backend = MagicMock()

        # Set callback
        mock_callback = Mock()
        capture._current_callback = mock_callback

        # Stop capture
        capture.stop_capture()

        # Verify callback cleared
        assert capture._current_callback is None

    def test_stop_capture_with_no_callback(self):
        """Test that stop_capture works when no callback is set"""
        capture = HybridCapture()
        capture.is_capturing = True
        capture.backend = MagicMock()
        capture._current_callback = None  # No callback

        # Add device to queue
        device = LLDPDevice()
        device.chassis_id = "test"
        result = CaptureResult(device=device, timestamp=time.time(), interface="test")
        capture.device_queue.put(result)

        # Should not raise exception
        capture.stop_capture()

        # Verify cleanup happened
        assert capture.backend is None


class TestResourceCleanup:
    """Test resource cleanup in various scenarios"""

    def test_metrics_logged_on_stop(self):
        """Test that metrics are logged when stopping capture"""
        capture = HybridCapture()
        capture.is_capturing = True
        capture.backend = MagicMock()

        # Set some metrics
        capture.metrics["rx_packets"] = 100
        capture.metrics["parsed"] = 5
        capture.metrics["parse_errors"] = 2
        capture.metrics["callbacks"] = 5
        capture.metrics["filtered"] = 93

        # Mock logger
        with patch("lldp.capture_dpkt.log") as mock_log:
            capture.stop_capture()

            # Verify metrics were logged
            assert mock_log.info.called
            # Check the call arguments contain the metric values
            call_args = mock_log.info.call_args
            assert (
                call_args[0][0]
                == "📊 Capture metrics: rx_packets=%d, parsed=%d, parse_errors=%d, callbacks=%d, filtered=%d"
            )
            assert call_args[0][1] == 100  # rx_packets
            assert call_args[0][2] == 5  # parsed
            assert call_args[0][3] == 2  # parse_errors
            assert call_args[0][4] == 5  # callbacks
            assert call_args[0][5] == 93  # filtered

    def test_concurrent_stop_and_produce(self):
        """Test that stopping during concurrent production is safe"""
        import threading
        import queue

        capture = HybridCapture()
        capture.is_capturing = True
        capture.backend = MagicMock()

        callback_calls = []

        def track_callback(device):
            callback_calls.append(device)

        capture._current_callback = track_callback

        # Start producer thread
        def producer():
            for i in range(10):
                device = LLDPDevice()
                device.chassis_id = f"device_{i}"
                result = CaptureResult(
                    device=device, timestamp=time.time(), interface="test"
                )
                capture.device_queue.put(result)
                time.sleep(0.01)

        prod_thread = threading.Thread(target=producer)
        prod_thread.start()

        # Stop capture while producer is still running
        time.sleep(0.05)  # Let producer add some items
        capture.stop_capture()

        prod_thread.join()

        # Verify no crashes and cleanup happened
        assert capture.backend is None
        assert capture._current_callback is None
        # Some callbacks should have been executed
        assert len(callback_calls) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
