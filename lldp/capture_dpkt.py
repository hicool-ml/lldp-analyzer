"""
Hybrid LLDP/CDP Capture using dpkt + selectable backends (pcapy / AF_PACKET)

This module provides a capture engine that prefer lightweight backends
(pcappy-ng or AF_PACKET) and falls back to Scapy only if neither backend
is available. It keeps the public API compatible with previous LLDPCapture
so the UI code does not need to change.
"""
import logging
import queue
import time
import threading
from typing import Optional, Callable, List

log = logging.getLogger("lldp.capture_dpkt")

# optional dependencies
try:
    import dpkt
    HAS_DPKT = True
except Exception:
    dpkt = None
    HAS_DPKT = False

try:
    import pcapy
    HAS_PCAPY = True
except Exception:
    pcapy = None
    HAS_PCAPY = False

try:
    from scapy.all import sniff
    HAS_SCAPY = True
except Exception:
    sniff = None
    HAS_SCAPY = False

from .parser import LLDPParser
from .cdp.parser import CDPParser
from .capture_backends import choose_backend, BaseBackend


class CaptureResult:
    def __init__(self, device, timestamp: float, interface: str):
        self.device = device
        self.timestamp = timestamp
        self.interface = interface


class HybridCapture:
    """Capture engine that uses the best available backend and dpkt for parsing."""

    def __init__(self):
        self.lldp_parser = LLDPParser()
        self.cdp_parser = CDPParser()
        self.device_queue: queue.Queue = queue.Queue()  # Thread-safe queue
        self.is_capturing = False
        self.capture_thread: Optional[threading.Thread] = None
        self._callback_pool = threading.Thread  # placeholder for API compatibility

        # backend instance (set in start_capture)
        self.backend: Optional[BaseBackend] = None
        self._current_callback: Optional[Callable] = None

        # 📊 运行指标（可观测性）
        self.metrics = {
            "rx_packets": 0,        # 接收的总包数
            "parsed": 0,            # 成功解析的设备数
            "parse_errors": 0,      # 解析失败数
            "callbacks": 0,         # 回调触发次数
            "filtered": 0           # 快速过滤跳过的包数
        }

        # lightweight thread pool replacement using concurrent.futures if available
        try:
            from concurrent.futures import ThreadPoolExecutor

            self._callback_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lldp_dpkt_callback")
        except Exception:
            self._callback_pool = None

    def _safe_callback(self, callback, device):
        try:
            callback(device)
        except Exception:
            log.exception("Device callback raised exception")

    def start_capture(self, interface, duration: int = 60, callback: Optional[Callable] = None):
        if self.is_capturing:
            raise RuntimeError("Capture already in progress")

        # choose backend
        backend = choose_backend(interface)
        if backend is None:
            # fallback to scapy if available
            if not HAS_SCAPY:
                raise RuntimeError("No capture backend available. Install pcapy (pcapy-ng) or run on Linux with dpkt installed or install Scapy.")
            log.info("No lightweight backend available; falling back to Scapy")
            # use old scapy-based flow in a separate thread (simpler to reuse existing logic)
            self._current_callback = callback
            self.is_capturing = True
            self.capture_thread = threading.Thread(target=self._scapy_worker, args=(interface, duration, callback), daemon=True)
            self.capture_thread.start()
            return

        self.backend = backend
        try:
            self.backend.open(bpf_filter="ether proto 0x88cc or ether host 01:00:0c:cc:cc:cc")
        except Exception:
            log.exception("Backend failed to open; falling back to Scapy if available")
            if HAS_SCAPY:
                self.backend = None
                self._current_callback = callback
                self.is_capturing = True
                self.capture_thread = threading.Thread(target=self._scapy_worker, args=(interface, duration, callback), daemon=True)
                self.capture_thread.start()
                return
            raise

        self._current_callback = callback
        self.is_capturing = True
        # start worker thread that drives backend.loop
        self.capture_thread = threading.Thread(target=self._backend_worker, args=(duration,), daemon=True)
        self.capture_thread.start()

    def _handle_dpkt_eth(self, eth):
        """Common handler for dpkt.ethernet.Ethernet frames"""
        self.metrics["rx_packets"] += 1

        try:
            # LLDP Ethertype 0x88cc
            if getattr(eth, "type", None) == 0x88cc:
                payload = bytes(eth.data)
                device = self.lldp_parser.parse_packet(payload)
                protocol = "LLDP"
            # CDP: detect by destination MAC 01:00:0c:cc:cc:cc (Cisco) and eth.type 0x2000
            elif getattr(eth, "dst", None) == b"\x01\x00\x0c\xcc\xcc\xcc" or getattr(eth, "type", None) == 0x2000:
                payload = bytes(eth.data)
                device = self.cdp_parser.parse_packet(payload) if hasattr(self.cdp_parser, 'parse_packet') else None
                protocol = "CDP"
            else:
                self.metrics["filtered"] += 1
                return

            if device and device.is_valid():
                self.metrics["parsed"] += 1
                device.capture_interface = getattr(self.backend, 'interface', 'unknown')
                device.protocol = protocol
                result = CaptureResult(device=device, timestamp=time.time(), interface=device.capture_interface)
                # enqueue to thread-safe queue
                self.device_queue.put(result)

                # async callback
                if self._current_callback:
                    self.metrics["callbacks"] += 1
                    if hasattr(self._callback_pool, 'submit'):
                        try:
                            self._callback_pool.submit(self._safe_callback, self._current_callback, device)
                        except Exception:
                            log.exception("Failed to submit callback")
                    else:
                        # fallback direct call
                        try:
                            self._safe_callback(self._current_callback, device)
                        except Exception:
                            log.exception("Callback failed")
            else:
                self.metrics["parse_errors"] += 1

        except Exception:
            self.metrics["parse_errors"] += 1
            log.exception("Error handling dpkt ethernet frame")

    def _backend_worker(self, duration: int):
        assert self.backend is not None
        try:
            self.backend.loop(self._handle_dpkt_eth, timeout=duration)
        except Exception:
            log.exception("Backend loop failed")
        finally:
            try:
                self.backend.close()
            except Exception:
                pass
            self.is_capturing = False

    def _scapy_worker(self, interface, duration: int, callback: Optional[Callable]):
        # minimal scapy fallback (keeps compatibility)
        from scapy.all import sniff, Ether

        def pkt_handler(pkt):
            try:
                # reuse existing parser methods that accept scapy packets
                device = None
                if pkt.haslayer(Ether) and pkt[Ether].type == 0x88CC:
                    device = self.lldp_parser.parse_scapy_packet(pkt)
                elif pkt.haslayer(Ether) and pkt[Ether].dst == "01:00:0c:cc:cc:cc":
                    device = self.cdp_parser.parse_scapy_packet(pkt)

                if device and device.is_valid():
                    device.capture_interface = str(interface)
                    # 🔥 修复：使用解析器设置的协议，不要覆盖
                    # 如果解析器已经设置了protocol，使用它；否则基于设备类型推断
                    if hasattr(device, 'protocol') and device.protocol:
                        # 使用解析器设置的协议标识
                        pass  # 保持原有的protocol设置
                    else:
                        # 根据设备类型推断协议
                        device.protocol = 'LLDP' if hasattr(device, 'chassis_id') else 'CDP'
                    res = CaptureResult(device=device, timestamp=time.time(), interface=str(interface))
                    self.device_queue.put(res)  # Thread-safe enqueue
                    if callback:
                        if hasattr(self._callback_pool, 'submit'):
                            self._callback_pool.submit(self._safe_callback, callback, device)
                        else:
                            try:
                                callback(device)
                            except Exception:
                                log.exception("Callback raised")
            except Exception:
                log.exception("Error in scapy pkt_handler")

        # start sniffing
        sniff(iface=interface, prn=pkt_handler, timeout=duration, store=False)
        self.is_capturing = False

    def stop_capture(self):
        self.is_capturing = False

        # 🔧 资源泄露防护：确保backend.close()在所有路径被调用
        try:
            if self.backend:
                self.backend.stop()
                self.backend.close()
        except Exception:
            log.exception("Failed to stop/close backend")
        finally:
            # 清理backend引用，防止重复调用
            self.backend = None

        # flush queue and submit callbacks for queued devices (thread-safe)
        if self._current_callback:
            flushed = self.get_discovered_devices()
            for res in flushed:
                try:
                    if hasattr(self._callback_pool, 'submit'):
                        self._callback_pool.submit(self._safe_callback, self._current_callback, res.device)
                    else:
                        self._safe_callback(self._current_callback, res.device)
                except Exception:
                    log.exception("Failed to submit flush callback")

            # 🔧 防止重复提交：清理callback引用
            self._current_callback = None

        # 📊 打印运行指标
        log.info("📊 Capture metrics: rx_packets=%d, parsed=%d, parse_errors=%d, callbacks=%d, filtered=%d",
                 self.metrics["rx_packets"], self.metrics["parsed"],
                 self.metrics["parse_errors"], self.metrics["callbacks"],
                 self.metrics["filtered"])

        # wait for thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=5)
            if self.capture_thread.is_alive():
                log.warning("Capture thread still alive after timeout")

    def shutdown(self):
        try:
            if hasattr(self._callback_pool, 'shutdown'):
                self._callback_pool.shutdown(wait=True)
        except Exception:
            log.exception("Error shutting down callback pool")

    def get_discovered_devices(self) -> List[CaptureResult]:
        """Drain queue and return all discovered devices (thread-safe)"""
        devices = []
        try:
            while True:
                devices.append(self.device_queue.get_nowait())
        except queue.Empty:
            pass
        return devices

    def is_active(self):
        return self.is_capturing


# Backwards compatibility alias
LLDPCapture = HybridCapture
LLDPCaptureListener = None
