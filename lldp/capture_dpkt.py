"""
Hybrid LLDP/CDP Capture using dpkt + selectable backends (pcapy / AF_PACKET / Raw Socket)

This module provides a capture engine that prefer lightweight backends:
1. 🚀 Raw Socket Engine (Linux AF_PACKET, Windows/macOS pcapy-ng) - ZERO Scapy dependency
2. ⚡ Lightweight backends (pcapy-ng or AF_PACKET) with dpkt parsing
3. 🔄 Fallback to Scapy only if no other backend is available

Public API remains compatible with previous LLDPCapture, so UI code does not need to change.
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

# 🔥 新增：无Scapy的Raw Socket引擎
try:
    from .raw_socket_capture import create_capture_engine
    HAS_RAW_SOCKET = True
except Exception:
    HAS_RAW_SOCKET = False
    log.debug("Raw socket engine not available (will use Scapy fallback)")


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

    def _raw_socket_callback(self, raw_data: bytes):
        """
        Raw Socket引擎的回调处理
        使用dpkt解析原始数据包
        """
        try:
            if not HAS_DPKT:
                log.warning("dpkt未安装，无法解析Raw Socket数据包")
                return

            # 使用dpkt解析以太网帧
            eth = dpkt.ethernet.Ethernet(raw_data)
            self._handle_dpkt_eth(eth)

        except Exception as e:
            log.exception(f"Raw Socket回调处理失败: {e}")

    def _raw_socket_timeout_worker(self, duration: int):
        """
        Raw Socket引擎的超时工作线程
        在指定时间后停止捕获
        """
        try:
            # 等待指定时长
            time.sleep(duration)

            # 停止捕获
            if self.is_capturing:
                log.info(f"Raw Socket捕获超时 ({duration}秒)，停止捕获")
                self.stop_capture()

        except Exception as e:
            log.exception(f"Raw Socket超时工作线程异常: {e}")

    def start_capture(self, interface, duration: int = 60, callback: Optional[Callable] = None):
        if self.is_capturing:
            raise RuntimeError("Capture already in progress")

        # 🔧 重置metrics（支持多轮capture）
        for key in self.metrics:
            self.metrics[key] = 0

        self._current_callback = callback

        # 🚀 第一优先级：无Scapy的Raw Socket引擎
        if HAS_RAW_SOCKET:
            try:
                log.info(f"🚀 使用Raw Socket引擎 (零Scapy依赖): {interface}")
                self.is_capturing = True

                # 创建Raw Socket引擎
                self.raw_socket_engine = create_capture_engine(
                    interface,
                    self._raw_socket_callback,
                    promisc=True
                )

                # 启动捕获
                self.raw_socket_engine.start_capture()

                # 启动超时线程
                self.capture_thread = threading.Thread(
                    target=self._raw_socket_timeout_worker,
                    args=(duration,),
                    daemon=True
                )
                self.capture_thread.start()

                return
            except Exception as e:
                log.warning(f"Raw Socket引擎启动失败: {e}")
                self.is_capturing = False

        # ⚡ 第二优先级：现有的lightweight backend (pcapy/AF_PACKET + dpkt)
        backend = choose_backend(interface)
        if backend is not None:
            try:
                self.backend = backend
                self.backend.open(bpf_filter="ether proto 0x88cc or ether host 01:00:0c:cc:cc:cc")
                log.info(f"⚡ 使用Lightweight Backend (dpkt + pcapy/AF_PACKET): {interface}")

                self.is_capturing = True
                self.capture_thread = threading.Thread(target=self._backend_worker, args=(duration,), daemon=True)
                self.capture_thread.start()
                return
            except Exception as e:
                log.warning(f"Lightweight backend启动失败: {e}")
                self.backend = None

        # 🔄 最后的fallback：Scapy
        if HAS_SCAPY:
            log.info(f"🔄 使用Scapy fallback (仅用于兼容): {interface}")
            self.is_capturing = True
            self.capture_thread = threading.Thread(target=self._scapy_worker, args=(interface, duration, callback), daemon=True)
            self.capture_thread.start()
            return

        # 所有引擎都失败
        raise RuntimeError(
            "❌ 无可用的捕获引擎！\n"
            "请安装以下依赖之一：\n"
            "1. Linux: 无需额外依赖 (使用原生AF_PACKET)\n"
            "2. Windows: pip install pcapy-ng (需要安装Npcap驱动)\n"
            "3. macOS: pip install pcapy-ng\n"
            "4. 通用: pip install scapy (不推荐，仅作为fallback)"
        )

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
                # 🔧 避免覆盖解析器已设置的protocol字段
                if not getattr(device, 'protocol', None):
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
        """停止捕获并强制刷新缓存中的设备"""
        self.is_capturing = False

        # 🚀 停止Raw Socket引擎（如果使用）
        if hasattr(self, 'raw_socket_engine') and self.raw_socket_engine:
            try:
                log.info("🛑 停止Raw Socket引擎")
                self.raw_socket_engine.stop_capture()
            except Exception as e:
                log.exception(f"停止Raw Socket引擎失败: {e}")
            finally:
                self.raw_socket_engine = None

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

        # 🔥 关键新增：停止时强制刷新缓存，确保最后的设备能显示
        log.info("🔥 强制刷新设备缓存...")
        flushed_devices = self.get_discovered_devices()

        if self._current_callback and flushed_devices:
            log.info(f"📤 触发 {len(flushed_devices)} 个缓存设备的回调")
            for res in flushed_devices:
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
        """Shutdown capture and release all resources."""
        # 🔧 确保backend被stop/close（双重保险）
        try:
            if self.backend:
                self.backend.stop()
                self.backend.close()
                self.backend = None
        except Exception:
            log.exception("Error closing backend in shutdown")

        # 关闭线程池
        try:
            if hasattr(self._callback_pool, 'shutdown'):
                self._callback_pool.shutdown(wait=True)
        except Exception:
            log.exception("Error shutting down callback pool")

    def get_discovered_devices(self) -> List[CaptureResult]:
        """Drain queue and return all discovered devices (thread-safe).

        ⚠️  IMPORTANT: This call will clear the internal queue!
        All devices returned by this call are removed from the internal queue.
        Subsequent calls will only return newly discovered devices.

        Returns:
            List[CaptureResult]: List of discovered devices, cleared from internal queue
        """
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
