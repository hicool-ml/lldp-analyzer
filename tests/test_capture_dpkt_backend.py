"""
Backend loop tests for HybridCapture (dpkt backend)

Tests cover:
1. Mock dpkt.ethernet.Ethernet frame handling
2. LLDP/CDP packet detection
3. Callback invocation
4. Error handling in packet processing
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from lldp.capture_dpkt import HybridCapture
from lldp.model import LLDPDevice


class TestBackendLoop:
    """Test backend loop packet processing"""

    @pytest.fixture
    def capture(self):
        """Create a HybridCapture instance for testing"""
        capture = HybridCapture()
        capture._current_callback = Mock()
        return capture

    def test_handle_lldp_packet(self, capture):
        """Test handling of LLDP packets"""
        # Create mock LLDP packet
        mock_eth = MagicMock()
        mock_eth.type = 0x88CC  # LLDP Ethertype
        mock_eth.data = b"\x02\x07\x04\x00\x11\x22\x33\x44\x55"  # Minimal chassis ID

        # Mock parser to return a device
        mock_device = LLDPDevice()
        mock_device.chassis_id = "00:11:22:33:44:55"
        mock_device._is_valid = True
        capture.lldp_parser.parse_packet = Mock(return_value=mock_device)

        # Process packet
        capture._handle_dpkt_eth(mock_eth)

        # Verify device was queued
        devices = capture.get_discovered_devices()
        assert len(devices) == 1
        assert devices[0].device.chassis_id == "00:11:22:33:44:55"

    def test_handle_cdp_packet(self, capture):
        """Test handling of CDP packets"""
        # Create mock CDP packet
        mock_eth = MagicMock()
        mock_eth.dst = b"\x01\x00\x0c\xcc\xcc\xcc"  # CDP multicast MAC
        mock_eth.type = 0x2000  # CDP SNAP
        mock_eth.data = b"\x02\x00\x00\x78"  # Minimal CDP data

        # Mock parser to return a device
        from lldp.cdp.model import CDPDevice

        mock_device = CDPDevice()
        mock_device.device_id = "Cisco-Switch"
        mock_device._is_valid = True
        capture.cdp_parser.parse_packet = Mock(return_value=mock_device)

        # Process packet
        capture._handle_dpkt_eth(mock_eth)

        # Verify device was queued
        devices = capture.get_discovered_devices()
        assert len(devices) == 1

    def test_handle_unknown_packet(self, capture):
        """Test that unknown packets are ignored"""
        # Create mock non-LLDP/CDP packet
        mock_eth = MagicMock()
        mock_eth.type = 0x0800  # IPv4
        mock_eth.dst = b"\xff\xff\xff\xff\xff\xff"

        # Process packet
        capture._handle_dpkt_eth(mock_eth)

        # Verify no device was queued
        devices = capture.get_discovered_devices()
        assert len(devices) == 0

    def test_callback_invoked_on_device_discovery(self, capture):
        """Test that callback is invoked when device is discovered"""
        # Create mock LLDP packet
        mock_eth = MagicMock()
        mock_eth.type = 0x88CC
        mock_eth.data = b"\x02\x07\x04\x00\x11\x22\x33\x44\x55"

        # Mock parser
        mock_device = LLDPDevice()
        mock_device.chassis_id = "00:11:22:33:44:55"
        mock_device._is_valid = True
        capture.lldp_parser.parse_packet = Mock(return_value=mock_device)

        # Process packet
        capture._handle_dpkt_eth(mock_eth)

        # Verify callback was invoked
        assert capture._current_callback.call_count == 1
        capture._current_callback.assert_called_with(mock_device)

    def test_invalid_device_not_queued(self, capture):
        """Test that invalid devices are not queued"""
        # Create mock LLDP packet
        mock_eth = MagicMock()
        mock_eth.type = 0x88CC
        mock_eth.data = b"\x02\x07\x04\x00\x11\x22\x33\x44\x55"

        # Mock parser to return invalid device
        mock_device = LLDPDevice()
        mock_device._is_valid = False
        capture.lldp_parser.parse_packet = Mock(return_value=mock_device)

        # Process packet
        capture._handle_dpkt_eth(mock_eth)

        # Verify no device was queued
        devices = capture.get_discovered_devices()
        assert len(devices) == 0

    def test_parser_exception_handling(self, capture):
        """Test that parser exceptions are handled gracefully"""
        # Create mock packet
        mock_eth = MagicMock()
        mock_eth.type = 0x88CC
        mock_eth.data = b"malformed data"

        # Mock parser to raise exception
        capture.lldp_parser.parse_packet = Mock(side_effect=Exception("Parse error"))

        # Process packet - should not raise
        capture._handle_dpkt_eth(mock_eth)

        # Verify no device was queued and callback not called
        devices = capture.get_discovered_devices()
        assert len(devices) == 0
        assert capture._current_callback.call_count == 0

    def test_protocol_field_set_correctly(self, capture):
        """Test that protocol field is set correctly"""
        # Test LLDP
        mock_lldp = MagicMock()
        mock_lldp.type = 0x88CC
        mock_lldp.data = b"data"

        mock_lldp_device = LLDPDevice()
        mock_lldp_device.chassis_id = "lldp_device"
        mock_lldp_device.is_valid = Mock(return_value=True)
        capture.lldp_parser.parse_packet = Mock(return_value=mock_lldp_device)

        capture._handle_dpkt_eth(mock_lldp)
        devices = capture.get_discovered_devices()
        assert len(devices) == 1
        assert devices[0].device.protocol == "LLDP"

        # Test CDP
        import queue

        capture.device_queue = queue.Queue()  # Clear queue

        mock_cdp = MagicMock()
        mock_cdp.dst = b"\x01\x00\x0c\xcc\xcc\xcc"
        mock_cdp.type = 0x2000
        mock_cdp.data = b"data"

        from lldp.cdp.model import CDPDevice

        mock_cdp_device = CDPDevice()
        mock_cdp_device.device_id = "cdp_device"
        mock_cdp_device.is_valid = Mock(return_value=True)
        capture.cdp_parser.parse_packet = Mock(return_value=mock_cdp_device)

        capture._handle_dpkt_eth(mock_cdp)
        devices = capture.get_discovered_devices()
        assert len(devices) == 1
        assert devices[0].device.protocol == "CDP"


class TestBackendIntegration:
    """Integration tests for backend selection and initialization"""

    def test_backend_initialization(self):
        """Test that capture can be initialized"""
        capture = HybridCapture()
        assert capture.is_active() is False
        assert capture.get_discovered_devices() == []

    def test_capture_interface_attribute_exists(self):
        """Test that captured devices have interface attribute"""
        capture = HybridCapture()

        mock_eth = MagicMock()
        mock_eth.type = 0x88CC
        mock_eth.data = b"data"

        mock_device = LLDPDevice()
        mock_device.chassis_id = "test_device"
        mock_device.is_valid = Mock(return_value=True)
        capture.lldp_parser.parse_packet = Mock(return_value=mock_device)

        # Mock backend with interface attribute
        capture.backend = MagicMock()
        capture.backend.interface = "eth0"

        capture._handle_dpkt_eth(mock_eth)

        devices = capture.get_discovered_devices()
        assert len(devices) == 1
        assert devices[0].interface == "eth0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
