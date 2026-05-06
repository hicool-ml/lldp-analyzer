"""
Capture backends for lightweight packet capture

Provides two backends:
- PCAPBackend: uses pcapy-ng (libpcap) and dpkt for parsing (cross-platform)
- AFPacketBackend: uses Linux AF_PACKET raw socket + dpkt (lightweight, Linux-only)

Backends implement a small common API used by capture modules.
"""

import time
import logging
import platform
from typing import Callable, Optional

log = logging.getLogger("lldp.capture_backends")

# Optional imports
try:
    import pcapy

    HAS_PCAPY = True
except Exception:
    pcapy = None
    HAS_PCAPY = False

try:
    import dpkt

    HAS_DPKT = True
except Exception:
    dpkt = None
    HAS_DPKT = False

import socket

from .capture_utils import normalize_interface_name


class BaseBackend:
    """Backend interface"""

    def open(self, interface: str, bpf_filter: str = "") -> None:
        raise NotImplementedError

    def loop(self, on_packet: Callable, timeout: Optional[int] = None) -> None:
        """Run packet loop and call on_packet(eth) for each received frame

        eth is a dpkt.ethernet.Ethernet instance (or raw bytes if dpkt not available)
        """
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class PCAPBackend(BaseBackend):
    """PCAP backend using pcapy (pcapy-ng) + dpkt for parsing"""

    def __init__(
        self,
        interface: str,
        snaplen: int = 65535,
        promisc: bool = True,
        timeout_ms: int = 1000,
    ):
        if not HAS_PCAPY:
            raise RuntimeError("pcapy is not installed")
        if not HAS_DPKT:
            raise RuntimeError("dpkt is required for PCAPBackend")

        self.interface = normalize_interface_name(interface)
        self.snaplen = snaplen
        self.promisc = promisc
        self.timeout_ms = timeout_ms
        self.pcap = None
        self._stop = False

    def open(self, bpf_filter: str = "") -> None:
        # open_live(iface, snaplen, promisc, read_timeout_ms)
        self.pcap = pcapy.open_live(
            self.interface, self.snaplen, int(self.promisc), int(self.timeout_ms)
        )
        log.info(
            "✅ Opened pcap on %s, snaplen=%d, promisc=%d, timeout_ms=%d",
            self.interface,
            self.snaplen,
            self.promisc,
            self.timeout_ms,
        )
        if bpf_filter:
            try:
                self.pcap.setfilter(bpf_filter)
                log.info("✅ BPF filter set: %s", bpf_filter)
            except Exception:
                log.exception("Failed to set BPF filter: %s", bpf_filter)

    def loop(self, on_packet: Callable, timeout: Optional[int] = None) -> None:
        start = time.time()
        self._stop = False
        while not self._stop:
            if timeout and (time.time() - start) >= timeout:
                break
            try:
                header, payload = self.pcap.next()
            except pcapy.PcapError:
                # timeout or no packet
                continue
            except Exception:
                log.exception("pcapy next() failed")
                continue

            if not payload or len(payload) < 14:
                continue

            # 🚀 性能优化：快速字节级过滤，避免频繁构造dpkt对象
            # 检查EtherType (offset 12-13): LLDP=0x88cc, CDP=0x2000
            ethertype = payload[12:14]
            if ethertype not in (b"\x88\xcc", b"\x20\x00"):
                # 检查CDP目的MAC (offset 0-5): 01:00:0c:cc:cc:cc
                if payload[0:6] != b"\x01\x00\x0c\xcc\xcc\xcc":
                    continue  # 非目标流量，快速跳过

            try:
                eth = dpkt.ethernet.Ethernet(payload)
            except Exception:
                log.exception("dpkt failed to parse packet")
                continue

            try:
                on_packet(eth)
            except Exception:
                log.exception("on_packet callback raised")

    def stop(self) -> None:
        self._stop = True

    def close(self) -> None:
        try:
            if self.pcap:
                # pcapy has no explicit close in some versions
                try:
                    self.pcap.close()
                except Exception:
                    pass
        except Exception:
            pass


class AFPacketBackend(BaseBackend):
    """Linux AF_PACKET backend using raw socket + dpkt

    Lightweight; requires Linux and root privileges.
    """

    def __init__(self, interface: str, timeout: float = 1.0):
        if platform.system().lower() != "linux":
            raise RuntimeError("AFPacketBackend is supported only on Linux")
        if not HAS_DPKT:
            raise RuntimeError("dpkt is required for AFPacketBackend")

        self.interface = normalize_interface_name(interface)
        self.timeout = float(timeout)
        self.sock = None
        self._stop = False

    def open(self, bpf_filter: str = "") -> None:
        # create raw AF_PACKET socket
        self.sock = socket.socket(
            socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003)
        )
        try:
            self.sock.bind((self.interface, 0))
            log.info("✅ Opened AF_PACKET socket on %s", self.interface)
        except PermissionError:
            # 🔧 友好化异常消息：提供解决方案
            raise PermissionError(
                "Permission denied: AF_PACKET requires raw socket privileges. "
                "Run as root OR use: sudo setcap cap_net_raw+ep $(which python)"
            )
        except Exception as e:
            log.exception(
                "Failed to bind AF_PACKET socket to interface %s", self.interface
            )
            raise RuntimeError(
                f"Failed to bind AF_PACKET socket to {self.interface}: {e}\n"
                f"Hint: Ensure you have CAP_NET_RAW capability or run with sudo.\n"
                f"Command: sudo setcap cap_net_raw+ep $(which python)"
            )
        self.sock.settimeout(self.timeout)

    def loop(self, on_packet: Callable, timeout: Optional[int] = None) -> None:
        start = time.time()
        self._stop = False
        while not self._stop:
            if timeout and (time.time() - start) >= timeout:
                break
            try:
                pkt, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except Exception:
                log.exception("AF_PACKET recvfrom failed")
                continue

            if len(pkt) < 14:
                continue

            # 🚀 性能优化：快速字节级过滤，避免频繁构造dpkt对象
            # 检查EtherType (offset 12-13): LLDP=0x88cc, CDP=0x2000
            ethertype = pkt[12:14]
            if ethertype not in (b"\x88\xcc", b"\x20\x00"):
                # 检查CDP目的MAC (offset 0-5): 01:00:0c:cc:cc:cc
                if pkt[0:6] != b"\x01\x00\x0c\xcc\xcc\xcc":
                    continue  # 非目标流量，快速跳过

            try:
                eth = dpkt.ethernet.Ethernet(pkt)
            except Exception:
                log.exception("dpkt failed to parse AF_PACKET frame")
                continue

            try:
                on_packet(eth)
            except Exception:
                log.exception("on_packet callback raised")

    def stop(self) -> None:
        self._stop = True

    def close(self) -> None:
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass


def choose_backend(interface: str) -> Optional[BaseBackend]:
    """Choose the best available backend for the current environment.

    Priority: PCAPBackend (if pcapy present) -> AFPacketBackend (Linux) -> None
    """
    # Prefer pcapy if available
    if HAS_PCAPY and HAS_DPKT:
        try:
            log.info("🔧 Backend selection: PCAPBackend (pcapy-ng available)")
            return PCAPBackend(interface)
        except Exception:
            log.exception("Failed to initialize PCAPBackend")

    # Fallback to AF_PACKET on Linux
    if platform.system().lower() == "linux" and HAS_DPKT:
        try:
            log.info("🔧 Backend selection: AFPacketBackend (Linux, pcapy unavailable)")
            return AFPacketBackend(interface)
        except Exception:
            log.exception("Failed to initialize AFPacketBackend")

    # No lightweight backend available
    log.warning(
        "⚠️  No lightweight backend available (pcapy/AF_PACKET), will use Scapy fallback"
    )

    return None
