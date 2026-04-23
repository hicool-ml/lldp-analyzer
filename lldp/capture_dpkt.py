"""
Hybrid LLDP/CDP Capture using dpkt for CDP
Optimized version: dpkt(195KB) vs Scapy(2.6MB) = 13x smaller!

⚠️ Current Implementation:
- Requires Scapy for packet capture (AsyncSniffer)
- dpkt-only capture is not yet implemented
- Uses AsyncSniffer for reliable stop behavior

🔥 Recent Improvements:
- Consistent Scapy requirement in __init__ and start_capture
- Replaced sniff with AsyncSniffer for better platform compatibility
- Replaced all print statements with logging
- Added ThreadPoolExecutor for async callback execution
- Improved exception handling with log.exception
- Increased stop_capture timeout to 5 seconds
"""

from typing import Optional, Callable, Any, Union
import queue
import threading
import time
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# Logger for capture_dpkt module
log = logging.getLogger("lldp.capture_dpkt")

# Type aliases for better type hints
LLDPDevice = Any  # Would be lldp.models.LLDPDevice if imported
CDPDevice = Any   # Would be lldp.cdp.models.CDPDevice if imported

try:
    import dpkt
    HAS_DPKT = True
except ImportError:
    HAS_DPKT = False

try:
    from scapy.all import AsyncSniffer  # 🔥 改用 AsyncSniffer
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False

from .parser import LLDPParser
from .cdp.parser import CDPParser


@dataclass
class CaptureResult:
    """
    Result of LLDP packet capture

    Attributes:
        device: LLDPDevice or CDPDevice instance
        timestamp: Capture timestamp (Unix timestamp)
        interface: Network interface name
    """
    device: Union[LLDPDevice, CDPDevice]
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
        """
        Initialize capture engine

        ⚠️ 当前实现要求 Scapy 必须可用

        Raises:
            RuntimeError: 如果 Scapy 不可用
        """
        # 🔥 修复 dpkt 路径一致性：init 也要求 Scapy
        if not HAS_SCAPY:
            raise RuntimeError(
                "Scapy is required for HybridCapture; "
                "install with `pip install scapy`. "
                "dpkt-only capture is not yet implemented."
            )

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
        """
        Capture worker thread using AsyncSniffer

        🔥 改进：使用 AsyncSniffer 替代 sniff，提供更可靠的停止机制
        """
        try:
            log.info("========== HYBRID CAPTURE STARTED ==========")
            log.info("Interface: %s", interface)
            log.info("Has dpkt: %s, Has Scapy: %s", HAS_DPKT, HAS_SCAPY)
            log.info("======================================")

            packet_count = 0
            device_found = False
            start_time = time.time()

            def packet_handler(pkt):
                """Handle each captured packet"""
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

                        # 使用线程池异步执行回调
                        if callback:
                            try:
                                log.debug("Submitting device callback to thread pool...")
                                self._callback_pool.submit(self._safe_callback, callback, device)
                                log.debug("Device callback submitted successfully")
                            except Exception as e:
                                log.exception("Failed to submit callback: %s", e)

                except Exception as e:
                    log.exception("Error in packet_handler: %s", e)

            # 🔥 改进：使用 AsyncSniffer 而不是 sniff
            log.info("Starting packet capture on %s...", interface)
            log.info("Capture timeout: %ds (max)", duration)
            log.debug("Packet handler registered, waiting for packets...")

            # 创建 BPF 过滤器
            bpf_filter = "ether proto 0x88cc or ether host 01:00:0c:cc:cc:cc"

            # 创建异步嗅探器
            sniffer = AsyncSniffer(
                iface=interface,
                filter=bpf_filter,
                prn=packet_handler,
                store=False,
                started_callback=lambda: log.debug("AsyncSniffer started on %s", interface)
            )

            # 启动异步嗅探
            sniffer.start()

            # 等待捕获完成或设备发现
            import time as time_module
            start_time = time_module.time()

            while time_module.time() - start_time < duration:
                if device_found or not self.is_capturing:
                    log.debug("Stop condition triggered, stopping AsyncSniffer...")
                    break
                time_module.sleep(0.1)  # 100ms轮询间隔

            # 🔥 优雅停止：检查 running 状态
            if hasattr(sniffer, 'running') and sniffer.running:
                log.debug("Stopping AsyncSniffer (running=True)...")
                sniffer.stop()
                log.debug("AsyncSniffer stopped gracefully")
            else:
                log.debug("AsyncSniffer already stopped (running=False)")

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
