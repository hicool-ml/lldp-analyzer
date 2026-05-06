"""
Hybrid LLDP/CDP Capture using dpkt + selectable backends (pcapy / AF_PACKET / Raw Socket)

This module provides a capture engine that prefer lightweight backends:
1.  Raw Socket Engine (Linux AF_PACKET, Windows/macOS pcapy-ng) - ZERO Scapy dependency
2.  Lightweight backends (pcapy-ng or AF_PACKET) with dpkt parsing
3.  Fallback to Scapy only if no other backend is available

Public API remains compatible with previous LLDPCapture, so UI code does not need to change.
"""
import logging
import queue
import time
import threading
from dataclasses import dataclass, is_dataclass
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
from .capture_utils import describe_interface, normalize_interface_name

#  新增：无Scapy的Raw Socket引擎
try:
    from .raw_socket_capture import create_capture_engine
    HAS_RAW_SOCKET = True
except Exception:
    HAS_RAW_SOCKET = False
    log.debug("Raw socket engine not available (will use Scapy fallback)")


@dataclass
class CaptureResult:
    device: object
    timestamp: float
    interface: str


def _is_meaningful(value) -> bool:
    if value is None:
        return False
    if value == "":
        return False
    if value == [] or value == {}:
        return False
    if is_dataclass(value):
        return any(_is_meaningful(item) for item in vars(value).values())
    return True


def merge_devices(base, new):
    """Merge later packet fields into the cached device without changing identity."""
    for key, value in vars(new).items():
        if key == "last_seen":
            setattr(base, key, value)
            continue

        current = getattr(base, key, None)
        if isinstance(current, list) and isinstance(value, list):
            seen = {repr(item) for item in current}
            for item in value:
                marker = repr(item)
                if marker not in seen:
                    current.append(item)
                    seen.add(marker)
            continue

        if is_dataclass(current) and is_dataclass(value) and type(current) is type(value):
            merge_devices(current, value)
            continue

        if current is False and value is True:
            setattr(base, key, value)
            continue

        if not _is_meaningful(current) and _is_meaningful(value):
            setattr(base, key, value)

    return base


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
        self._device_cache = {}
        self._cache_lock = threading.Lock()
        self._active_interface_name = "unknown"
        self._active_interface_desc = "unknown"

        #  运行指标（可观测性）
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
        with self._cache_lock:
            self._device_cache.clear()
        self._active_interface_name = normalize_interface_name(interface)
        self._active_interface_desc = describe_interface(interface)

        # 使用log.warning确保UI能够捕获并显示
        log.warning("[CAPTURE] Engine selection started...")
        log.warning(f"[CAPTURE] Raw Socket: {HAS_RAW_SOCKET}, Scapy: {HAS_SCAPY}")

        #  第一优先级：无Scapy的Raw Socket引擎
        if HAS_RAW_SOCKET:
            try:
                log.warning("[CAPTURE] [1/3] Trying Raw Socket engine...")
                self.is_capturing = True

                # 创建Raw Socket引擎
                self.raw_socket_engine = create_capture_engine(
                    self._active_interface_name,
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

                log.warning("[CAPTURE] Raw Socket engine started successfully")
                return
            except Exception as e:
                log.warning(f"[CAPTURE] Raw Socket engine failed: {e}")
                log.warning("[CAPTURE] Will try Lightweight Backend...")
                self.is_capturing = False

        #  第二优先级：现有的lightweight backend (pcapy/AF_PACKET + dpkt)
        log.warning("[CAPTURE] [2/3] Trying Lightweight Backend...")
        backend = choose_backend(self._active_interface_name)
        if backend is not None:
            try:
                log.warning(f"[CAPTURE] Backend created: {backend.__class__.__name__}")
                self.backend = backend
                self.backend.open(bpf_filter="ether proto 0x88cc or ether host 01:00:0c:cc:cc:cc")
                log.warning(f"[CAPTURE] Using Lightweight Backend: {self._active_interface_desc} ({self._active_interface_name})")

                self.is_capturing = True
                self.capture_thread = threading.Thread(target=self._backend_worker, args=(duration,), daemon=True)
                self.capture_thread.start()
                log.warning("[CAPTURE] Lightweight Backend started successfully")
                return
            except Exception as e:
                log.warning(f"[CAPTURE] Lightweight backend failed: {e}")
                log.warning("[CAPTURE] Will try Scapy fallback...")
                self.backend = None

        #  最后的fallback：Scapy
        if HAS_SCAPY:
            log.warning(f"[CAPTURE] [3/3] Using Scapy Fallback: {self._active_interface_desc} ({self._active_interface_name})")
            log.warning("[CAPTURE] Scapy mode has lower performance, Npcap recommended")
            log.warning("[CAPTURE] Starting Scapy worker thread...")
            self.is_capturing = True
            self.capture_thread = threading.Thread(target=self._scapy_worker, args=(interface, duration, callback), daemon=True)
            self.capture_thread.start()
            log.warning("[CAPTURE] Scapy worker thread started")
            return

        # 所有引擎都失败
        error_msg = """
 无法启动网络捕获！所有捕获引擎都不可用。

当前状态:
  - Raw Socket引擎: 失败 (缺少pcapy-ng或Npcap驱动)
  - Lightweight Backend: 失败 (缺少pcapy-ng或Npcap驱动)
  - Scapy Fallback: 失败 (Scapy未安装)

解决方案:
   推荐方案: 安装Npcap驱动 (性能最佳)
     1. 下载Npcap: https://npcap.com/#download
     2. 安装时勾选 "Install Npcap in Service Mode"
     3. 安装后重新运行此程序

   备用方案: 使用Scapy (已安装)
     pip install scapy

  📚 更多信息:
     - Windows性能对比: Npcap (30K pps) vs Scapy (3K pps)
     - Linux: 无需额外依赖，原生支持
     - macOS: 安装pcapy-ng
"""
        raise RuntimeError(error_msg)

    @staticmethod
    def _device_key(device) -> str:
        chassis_id = getattr(device, "chassis_id", None)
        if chassis_id:
            return f"chassis:{getattr(chassis_id, 'value', chassis_id)}"

        device_id = getattr(device, "device_id", None)
        if device_id:
            return f"cdp:{device_id}"

        system_name = getattr(device, "system_name", None)
        if system_name:
            return f"name:{system_name}"

        return f"unknown:{id(device)}"

    def _merge_or_cache_device(self, device):
        key = self._device_key(device)
        with self._cache_lock:
            cached = self._device_cache.get(key)
            if cached is None:
                self._device_cache[key] = device
                return device

            return merge_devices(cached, device)

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
                device = self._merge_or_cache_device(device)
                device.capture_interface = getattr(self.backend, 'interface', self._active_interface_name)
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
        import sys

        iface_name = normalize_interface_name(interface)
        iface_desc = describe_interface(interface)

        log.warning(f"[SCAPY] Scapy mode starting: {iface_desc}")
        log.warning(f"[SCAPY] Interface name: {iface_name}")
        log.warning(f"[SCAPY] Duration: {duration} seconds")

        #  数据包计数器（包括所有数据包，不只是LLDP/CDP）
        total_packets = [0]  # 使用列表以便在闭包中修改

        def pkt_handler(pkt):
            try:
                total_packets[0] += 1
                self.metrics["rx_packets"] += 1

                # 每100个包打印一次进度
                if total_packets[0] % 100 == 0:
                    log.warning(f"[SCAPY] Captured {total_packets[0]} packets so far...")

                # reuse existing parser methods that accept scapy packets
                device = None
                if pkt.haslayer(Ether) and pkt[Ether].type == 0x88CC:
                    log.warning(f"[SCAPY] Received LLDP packet #{self.metrics['rx_packets']}")
                    device = self.lldp_parser.parse_scapy_packet(pkt)
                elif pkt.haslayer(Ether) and pkt[Ether].dst == "01:00:0c:cc:cc:cc":
                    log.warning(f"[SCAPY] Received CDP packet #{self.metrics['rx_packets']}")
                    device = self.cdp_parser.parse_scapy_packet(pkt)
                else:
                    self.metrics["filtered"] += 1
                    return

                if device and device.is_valid():
                    self.metrics["parsed"] += 1
                    log.warning(f"[SCAPY] Parsed successfully #{self.metrics['parsed']}: {device.system_name}")
                    device = self._merge_or_cache_device(device)
                    device.capture_interface = iface_desc
                    #  修复：使用解析器设置的协议，不要覆盖
                    # 如果解析器已经设置了protocol，使用它；否则基于设备类型推断
                    if hasattr(device, 'protocol') and device.protocol:
                        # 使用解析器设置的协议标识
                        pass  # 保持原有的protocol设置
                    else:
                        # 根据设备类型推断协议
                        device.protocol = 'LLDP' if hasattr(device, 'chassis_id') else 'CDP'
                    res = CaptureResult(device=device, timestamp=time.time(), interface=iface_desc)
                    self.device_queue.put(res)  # Thread-safe enqueue
                    if callback:
                        self.metrics["callbacks"] += 1
                        if hasattr(self._callback_pool, 'submit'):
                            self._callback_pool.submit(self._safe_callback, callback, device)
                        else:
                            try:
                                callback(device)
                            except Exception:
                                log.exception("Callback raised")
                else:
                    self.metrics["parse_errors"] += 1
                    log.warning(f"[SCAPY] Parse failed #{self.metrics['parse_errors']}")
            except Exception:
                self.metrics["parse_errors"] += 1
                log.exception("Error in scapy pkt_handler")

        # start sniffing
        try:
            log.warning(f"[SCAPY] Starting packet capture...")
            sniff(iface=iface_name, prn=pkt_handler, timeout=duration, store=False)
            log.warning(f"[SCAPY] Capture completed")
            log.warning(f"[SCAPY] Stats: total={total_packets[0]}, LLDP/CDP={self.metrics['rx_packets']}, parsed={self.metrics['parsed']}")
        except Exception as e:
            error_str = str(e)
            log.warning(f"[SCAPY] Capture failed: {e}")

            # 特殊处理：winpcap/pcap驱动未安装
            if "winpcap is not installed" in error_str.lower() or "pcap" in error_str.lower():
                log.error("=" * 70)
                log.error("CRITICAL ERROR: Network capture driver not installed!")
                log.error("=" * 70)
                log.error("")
                log.error("LLDP/CDP packet capture requires a network capture driver.")
                log.error("")
                log.error("SOLUTION:")
                log.error("  Install Npcap driver (FREE, 15MB)")
                log.error("  1. Download: https://npcap.com/dist/npcap-1.87.exe")
                log.error("  2. Run installer")
                log.error("  3. CHECK 'Install Npcap in Service Mode'")
                log.error("  4. CHECK 'Support Raw 802.11 Traffic' (optional)")
                log.error("  5. Complete installation and restart this program")
                log.error("")
                log.error("ALTERNATIVE:")
                log.error("  Visit https://npcap.com/#download to choose version")
                log.error("")
                log.error("WHY Npcap is required:")
                log.error("  - LLDP/CDP are layer 2 protocols")
                log.error("  - Scapy needs raw socket access (layer 2)")
                log.error("  - Windows requires pcap driver for layer 2 access")
                log.error("  - No pcap driver = NO packet capture")
                log.error("=" * 70)
            else:
                log.warning(f"[SCAPY] Possible reasons:")
                log.warning(f"[SCAPY]   1. Incorrect interface name")
                log.warning(f"[SCAPY]   2. No admin rights")
                log.warning(f"[SCAPY]   3. Interface not connected or enabled")
                log.warning(f"[SCAPY]   4. Firewall blocking packet capture")
                log.warning(f"[SCAPY]   5. No devices connected to this interface")
        finally:
            self.is_capturing = False

    def stop_capture(self, emit_callbacks: bool = True):
        """停止捕获并强制刷新缓存中的设备"""
        self.is_capturing = False

        #  停止Raw Socket引擎（如果使用）
        if hasattr(self, 'raw_socket_engine') and self.raw_socket_engine:
            try:
                log.info(" 停止Raw Socket引擎")
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

        #  关键新增：停止时强制刷新缓存，确保最后的设备能显示
        log.info(" 强制刷新设备缓存...")
        flushed_devices = self.get_discovered_devices()

        if flushed_devices:
            log.info("缓存中有 %d 个设备", len(flushed_devices))
            if emit_callbacks and self._current_callback:
                for result in flushed_devices:
                    self._safe_callback(self._current_callback, result.device)

        # 🔧 防止重复提交：清理callback引用
        self._current_callback = None

        #  打印运行指标
        log.info("📊 Capture metrics: rx_packets=%d, parsed=%d, parse_errors=%d, callbacks=%d, filtered=%d",
                 self.metrics["rx_packets"], self.metrics["parsed"],
                 self.metrics["parse_errors"], self.metrics["callbacks"],
                 self.metrics["filtered"])

        # 🔥 修复假死问题：不阻塞等待线程结束，让线程自然退出
        # 线程会在daemon=True时随主进程退出，或在自己的超时后退出
        if self.capture_thread and self.capture_thread.is_alive():
            log.warning("Capture thread is still running (will exit naturally)")
            # Do not wait here; the daemon capture thread will exit naturally.

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

          IMPORTANT: This call will clear the internal queue!
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
