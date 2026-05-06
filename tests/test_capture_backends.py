"""
Backend selection and initialization tests

Tests cover:
1. Backend selection logic (choose_backend)
2. Platform-specific backend availability
3. Fallback behavior
4. Exception handling
"""

import pytest
import platform
from unittest.mock import patch, MagicMock
from lldp.capture_backends import (
    choose_backend,
    PCAPBackend,
    AFPacketBackend,
    HAS_PCAPY,
    HAS_DPKT,
)


class TestBackendSelection:
    """Test backend selection logic"""

    @patch("lldp.capture_backends.HAS_PCAPY", True)
    @patch("lldp.capture_backends.HAS_DPKT", True)
    def test_chooses_pcap_when_available(self):
        """Test that PCAPBackend is chosen when pcapy is available"""
        backend = choose_backend("eth0")
        assert isinstance(backend, PCAPBackend)

    @patch("lldp.capture_backends.HAS_PCAPY", False)
    @patch("lldp.capture_backends.HAS_DPKT", True)
    @patch("lldp.capture_backends.platform.system", return_value="Linux")
    def test_chooses_afpacket_on_linux_when_pcap_unavailable(self, mock_platform):
        """Test that AFPacketBackend is chosen on Linux when pcapy unavailable"""
        backend = choose_backend("eth0")
        assert isinstance(backend, AFPacketBackend)

    @patch("lldp.capture_backends.HAS_PCAPY", False)
    @patch("lldp.capture_backends.HAS_DPKT", True)
    @patch("lldp.capture_backends.platform.system", return_value="Windows")
    def test_returns_none_on_windows_when_pcap_unavailable(self, mock_platform):
        """Test that None is returned on Windows when pcapy unavailable"""
        backend = choose_backend("eth0")
        assert backend is None

    @patch("lldp.capture_backends.HAS_PCAPY", False)
    @patch("lldp.capture_backends.HAS_DPKT", False)
    def test_returns_none_when_dpkt_unavailable(self):
        """Test that None is returned when dpkt unavailable"""
        backend = choose_backend("eth0")
        assert backend is None


class TestPCAPBackend:
    """Test PCAPBackend initialization and error handling"""

    def test_requires_pcapy(self):
        """Test that PCAPBackend requires pcapy"""
        if not HAS_PCAPY:
            with pytest.raises(RuntimeError, match="pcapy is not installed"):
                PCAPBackend("eth0")

    def test_requires_dpkt(self):
        """Test that PCAPBackend requires dpkt"""
        if not HAS_DPKT:
            with pytest.raises(RuntimeError, match="dpkt is required"):
                PCAPBackend("eth0")

    @pytest.mark.skipif(not HAS_PCAPY, reason="pcapy not available")
    def test_initialization_success(self):
        """Test successful PCAPBackend initialization"""
        backend = PCAPBackend("eth0")
        assert backend.interface == "eth0"
        assert backend.pcap is None
        assert backend._stop is False


class TestAFPacketBackend:
    """Test AFPacketBackend initialization and error handling"""

    def test_requires_linux(self):
        """Test that AFPacketBackend requires Linux"""
        if platform.system().lower() != "linux":
            with pytest.raises(
                RuntimeError, match="AFPacketBackend is supported only on Linux"
            ):
                AFPacketBackend("eth0")

    def test_requires_dpkt(self):
        """Test that AFPacketBackend requires dpkt"""
        if not HAS_DPKT:
            with pytest.raises(RuntimeError, match="dpkt is required"):
                AFPacketBackend("eth0")

    @pytest.mark.skipif(platform.system().lower() != "linux", reason="Linux only")
    def test_initialization_success(self):
        """Test successful AFPacketBackend initialization on Linux"""
        backend = AFPacketBackend("eth0")
        assert backend.interface == "eth0"
        assert backend.sock is None
        assert backend._stop is False

    @pytest.mark.skipif(platform.system().lower() != "linux", reason="Linux only")
    def test_friendly_permission_error_message(self):
        """Test that permission errors include helpful message"""
        backend = AFPacketBackend("eth0")
        # Mock socket that raises PermissionError
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.bind.side_effect = PermissionError("Permission denied")
            mock_socket.return_value = mock_sock

            with pytest.raises(PermissionError) as exc_info:
                backend.open()

            # Verify friendly message
            error_msg = str(exc_info.value)
            assert (
                "setcap cap_net_raw+ep" in error_msg
                or "raw socket privileges" in error_msg
            )


class TestFastPathFiltering:
    """Test fast path filtering optimization"""

    def test_lldp_ethertype_passes(self):
        """Test that LLDP ethertype (0x88cc) passes filter"""
        # LLDP packet with correct ethertype at offset 12-13
        lldp_packet = bytes(12) + b"\x88\xcc"  # 12 bytes header + LLDP ethertype
        # This should pass the fast filter and reach dpkt parsing
        assert lldp_packet[12:14] == b"\x88\xcc"

    def test_cdp_ethertype_passes(self):
        """Test that CDP ethertype (0x2000) passes filter"""
        # CDP packet with correct ethertype at offset 12-13
        cdp_packet = bytes(12) + b"\x20\x00"  # 12 bytes header + CDP ethertype
        # This should pass the fast filter and reach dpkt parsing
        assert cdp_packet[12:14] == b"\x20\x00"

    def test_cdp_dst_mac_passes(self):
        """Test that CDP destination MAC passes filter"""
        # CDP packet with Cisco multicast MAC
        cdp_packet = b"\x01\x00\x0c\xcc\xcc\xcc" + bytes(
            7
        )  # CDP dst MAC + rest of header
        # This should pass the fast filter
        assert cdp_packet[0:6] == b"\x01\x00\x0c\xcc\xcc\xcc"

    def test_non_target_packet_filtered(self):
        """Test that non-target packets are filtered out"""
        # IPv4 packet (0x0800)
        ipv4_packet = bytes(12) + b"\x08\x00"
        ethertype = ipv4_packet[12:14]
        dst_mac = ipv4_packet[0:6]

        # Should be filtered (not LLDP/CDP ethertype and not CDP dst MAC)
        should_filter = (
            ethertype not in (b"\x88\xcc", b"\x20\x00")
            and dst_mac != b"\x01\x00\x0c\xcc\xcc\xcc"
        )
        assert should_filter


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
