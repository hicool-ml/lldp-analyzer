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

    def __init__(self, interface: str, snaplen: int = 65535, promisc: bool = True, timeout_ms: int = 1000):
        if not HAS_PCAPY:
            raise RuntimeError("pcapy is not installed")
        if not HAS_DPKT:
            raise RuntimeError("dpkt is required for PCAPBackend")

        self.interface = interface
        self.snaplen = snaplen
        self.promisc = promisc
        self.timeout_ms = timeout_ms
        self.pcap = None
        self._stop = False

    def open(self, bpf_filter: str = "") -> None:
        # open_live(iface, snaplen, promisc, read_timeout_ms)
        self.pcap = pcapy.open_live(self.interface, self.snaplen, int(self.promisc), int(self.timeout_ms))
        if bpf_filter:
            try:
                self.pcap.setfilter(bpf_filter)
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

            if not payload:
                continue

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

        self.interface = interface
        self.timeout = float(timeout)
        self.sock = None
        self._stop = False

    def open(self, bpf_filter: str = "") -> None:
        # create raw AF_PACKET socket
        self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
        try:
            self.sock.bind((self.interface, 0))
        except Exception:
            log.exception("Failed to bind AF_PACKET socket to interface %s", self.interface)
            raise
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
            return PCAPBackend(interface)
        except Exception:
            log.exception("Failed to initialize PCAPBackend")

    # Fallback to AF_PACKET on Linux
    if platform.system().lower() == "linux" and HAS_DPKT:
        try:
            return AFPacketBackend(interface)
        except Exception:
            log.exception("Failed to initialize AFPacketBackend")

    return None
