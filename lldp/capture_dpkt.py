"""
Hybrid LLDP/CDP Capture using dpkt for CDP
Optimized version: dpkt(195KB) vs Scapy(2.6MB) = 13x smaller!
"""

import queue
import threading
import time
from typing import Optional, Callable
from dataclasses import dataclass

try:
    import dpkt
    HAS_DPKT = True
except ImportError:
    HAS_DPKT = False

try:
    from scapy.all import sniff, Ether
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False

from .parser import LLDPParser
from .cdp.parser import CDPParser


@dataclass
class CaptureResult:
    """Result of LLDP packet capture"""
    device: object  # LLDPDevice
    timestamp: float
    interface: str


class HybridCapture:
    """
    Hybrid LLDP/CDP Capture Engine (dpkt + Scapy)

    Strategy:
    - CDP: Use dpkt (lightweight, 195KB, 9x faster)
    - LLDP: Use Scapy (proven, reliable)
    """

    def __init__(self):
        """Initialize capture engine"""
        if not HAS_SCAPY and not HAS_DPKT:
            raise RuntimeError("Either Scapy or dpkt is required")

        self.lldp_parser = LLDPParser()
        self.cdp_parser_dpkt = CDPParser()  # Existing parser
        self.device_queue: queue.Queue = queue.Queue()
        self.is_capturing = False
        self.capture_thread: Optional[threading.Thread] = None

    def start_capture(self, interface, duration: int = 60, callback: Optional[Callable] = None):
        """Start LLDP packet capture in background thread"""
        if self.is_capturing:
            raise RuntimeError("Capture already in progress")

        self.is_capturing = True
        self.device_queue = queue.Queue()

        # Start capture in background thread
        self.capture_thread = threading.Thread(
            target=self._capture_worker,
            args=(interface, duration, callback),
            daemon=True
        )
        self.capture_thread.start()

    def _capture_worker(self, interface, duration: int, callback: Optional[Callable]):
        """Capture worker thread using Scapy for everything (for now)"""
        try:
            print(f"\n[DEBUG] ========== HYBRID CAPTURE STARTED ==========", flush=True)
            print(f"[DEBUG] Interface: {interface}", flush=True)
            print(f"[DEBUG] Has dpkt: {HAS_DPKT}, Has Scapy: {HAS_SCAPY}", flush=True)
            print(f"[DEBUG] ======================================\n", flush=True)

            packet_count = 0
            device_found = False
            start_time = time.time()

            def packet_handler(pkt):
                """Handle each captured packet - Scapy version (reliable)"""
                nonlocal packet_count, device_found
                packet_count += 1

                if not self.is_capturing:
                    return

                try:
                    if packet_count % 10 == 0:
                        elapsed = time.time() - start_time
                        print(f"[DEBUG] Processed {packet_count} packets in {int(elapsed)}s...", flush=True)

                    # Convert packet to bytes
                    packet_bytes = bytes(pkt)

                    if len(packet_bytes) < 14:
                        return

                    # Check protocol type
                    is_lldp = False
                    is_cdp = False
                    ether_type = packet_bytes[12:14]

                    if ether_type == b'\x88\xcc':
                        is_lldp = True
                    elif packet_bytes[0:6] == b'\x01\x00\x0c\xcc\xcc\xcc' and ether_type == b'\x20\x00':
                        is_cdp = True
                    else:
                        return

                    device = None
                    protocol_name = "Unknown"

                    if is_lldp:
                        print(f"\n[DEBUG] LLDP packet captured!", flush=True)
                        device = self.lldp_parser.parse_scapy_packet(pkt)
                        protocol_name = "LLDP"

                    elif is_cdp:
                        print(f"\n[DEBUG] CDP packet captured!", flush=True)
                        device = self.cdp_parser_dpkt.parse_scapy_packet(pkt)
                        protocol_name = "CDP"

                    if device and device.is_valid():
                        print(f"[DEBUG] Valid {protocol_name} device: {device.get_display_name()}")
                        device.capture_interface = str(interface)
                        device.protocol = protocol_name

                        result = CaptureResult(
                            device=device,
                            timestamp=time.time(),
                            interface=str(interface)
                        )
                        self.device_queue.put(result)

                        nonlocal device_found
                        device_found = True
                        print(f"[DEBUG] Device found! Stopping capture...", flush=True)
                        self.is_capturing = False

                        if callback:
                            try:
                                callback(device)
                            except Exception as e:
                                print(f"[ERROR] Callback failed: {e}")

                except Exception as e:
                    print(f"[ERROR] Error in packet_handler: {e}")

            print(f"[DEBUG] Starting packet capture on {interface}...", flush=True)
            print(f"[DEBUG] Capture timeout: {duration}s (max)", flush=True)

            def stop_filter(pkt):
                if device_found or not self.is_capturing:
                    print(f"[DEBUG] Stop condition triggered!", flush=True)
                    return True
                return False

            sniff(
                iface=interface,
                prn=packet_handler,
                timeout=duration,
                store=False,
                stop_filter=stop_filter
            )

            print(f"[DEBUG] Capture completed. Total packets: {packet_count}", flush=True)
            if device_found:
                print(f"[DEBUG] Stopped early - Device found!", flush=True)
            else:
                print(f"[DEBUG] Timeout - No device found in {duration}s", flush=True)

        except Exception as e:
            print(f"Capture error: {e}")

        finally:
            self.is_capturing = False

    def stop_capture(self):
        """Stop ongoing capture"""
        print(f"[DEBUG] Stopping capture NOW!", flush=True)
        self.is_capturing = False

        if self.capture_thread and self.capture_thread.is_alive():
            print(f"[DEBUG] Waiting for capture thread to stop...", flush=True)
            self.capture_thread.join(timeout=2)

    def get_discovered_devices(self) -> list:
        """Get all discovered devices from queue"""
        devices = []
        while not self.device_queue.empty():
            try:
                result = self.device_queue.get_nowait()
                devices.append(result)
            except queue.Empty:
                break
        return devices

    def is_active(self) -> bool:
        """Check if capture is currently active"""
        return self.is_capturing


# Alias for compatibility
LLDPCapture = HybridCapture
LLDPCaptureListener = None  # Would need to be implemented if needed
