"""
Hybrid LLDP/CDP Capture using dpkt for CDP
Optimized version: dpkt(195KB) vs Scapy(2.6MB) = 13x smaller!

⚠️ Current Implementation:
- Requires Scapy for packet capture (sniff)
- dpkt support is planned but not yet implemented
- For dpkt-only capture, would need to implement raw socket or pcapy integration

🔥 Recent Improvements:
- Added Scapy availability check in start_capture
- Replaced all print statements with logging
- Added ThreadPoolExecutor for async callback execution
- Improved exception handling with log.exception
- Increased stop_capture timeout to 5 seconds
"""

import queue
import threading
import time
import logging
from typing import Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# Logger for capture_dpkt module
log = logging.getLogger("lldp.capture_dpkt")

# 🔥 限制 hex 输出长度，防止日志膨胀
MAX_HEX_DISPLAY = 200

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
    device: object  # LLDPDevice | CDPDevice (Any for flexibility)
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

        # 🔥 回调线程池，避免阻塞捕获线程
        self._callback_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lldp_dpkt_callback")

    def _safe_callback(self, callback, device):
        """
        🔥 安全包装回调函数，捕获并记录异常

        Args:
            callback: 用户回调函数
            device: 设备对象
        """
        try:
            callback(device)
        except Exception:
            log.exception("Device callback raised exception")

    def start_capture(self, interface, duration: int = 60, callback: Optional[Callable] = None):
        """Start LLDP packet capture in background thread"""
        if self.is_capturing:
            raise RuntimeError("Capture already in progress")

        # 🔥 高优先级修复1：检查 Scapy 是否可用
        if not HAS_SCAPY:
            raise RuntimeError(
                "Scapy is required for HybridCapture.start_capture; "
                "install with `pip install scapy` or use a dpkt-only capture implementation."
            )

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
            log.info("========== HYBRID CAPTURE STARTED ==========")
            log.info("Interface: %s", interface)
            log.info("Has dpkt: %s, Has Scapy: %s", HAS_DPKT, HAS_SCAPY)
            log.info("======================================")

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
                        log.debug("Processed %d packets in %ds...", packet_count, int(elapsed))

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
                        log.debug("LLDP packet captured!")
                        device = self.lldp_parser.parse_scapy_packet(pkt)
                        protocol_name = "LLDP"

                    elif is_cdp:
                        log.debug("CDP packet captured!")
                        device = self.cdp_parser_dpkt.parse_scapy_packet(pkt)
                        protocol_name = "CDP"

                    if device and device.is_valid():
                        log.debug("Valid %s device: %s", protocol_name, device.get_display_name())
                        device.capture_interface = str(interface)
                        device.protocol = protocol_name

                        result = CaptureResult(
                            device=device,
                            timestamp=time.time(),
                            interface=str(interface)
                        )
                        self.device_queue.put(result)

                        device_found = True
                        log.debug("Device found! Stopping capture...")
                        self.is_capturing = False

                        # 🔥 高优先级修复3：使用线程池异步执行回调，避免阻塞捕获线程
                        if callback:
                            try:
                                log.debug("Submitting device callback to thread pool...")
                                self._callback_pool.submit(self._safe_callback, callback, device)
                                log.debug("Device callback submitted successfully")
                            except Exception as e:
                                log.exception("Failed to submit callback: %s", e)

                except Exception as e:
                    log.exception("Error in packet_handler: %s", e)

            log.info("Starting packet capture on %s...", interface)
            log.info("Capture timeout: %ds (max)", duration)

            def stop_filter(pkt):
                if device_found or not self.is_capturing:
                    log.debug("Stop condition triggered!")
                    return True
                return False

            sniff(
                iface=interface,
                prn=packet_handler,
                timeout=duration,
                store=False,
                stop_filter=stop_filter
            )

            log.info("Capture completed. Total packets: %d", packet_count)
            if device_found:
                log.info("Stopped early - Device found!")
            else:
                log.info("Timeout - No device found in %ds", duration)

        except Exception as e:
            log.exception("Capture error: %s", e)

        finally:
            self.is_capturing = False

    def stop_capture(self):
        """Stop ongoing capture"""
        log.debug("Stopping capture NOW!")
        self.is_capturing = False

        if self.capture_thread and self.capture_thread.is_alive():
            log.debug("Waiting for capture thread to stop...")
            # 🔥 中等优先级修复6：增加超时时间并添加警告
            self.capture_thread.join(timeout=5)
            if self.capture_thread.is_alive():
                log.warning("Capture thread still alive after 5s")
            else:
                log.debug("Capture thread stopped successfully")

    def shutdown(self):
        """
        🔥 新增：清理资源

        停止线程池，释放资源
        """
        try:
            self._callback_pool.shutdown(wait=True)
            log.debug("Callback pool shutdown completed")
        except Exception as e:
            log.warning("Error shutting down callback pool: %s", e)

    def __del__(self):
        """析构函数：确保资源清理"""
        try:
            if hasattr(self, '_callback_pool'):
                self._callback_pool.shutdown(wait=False)
        except Exception:
            pass

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
