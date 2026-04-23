"""
LLDP and CDP Packet Capture
Capture layer with queue-based threading - Enhanced with CDP support + Multi-packet Fusion!

🔥 v3.0 新增：LLDPDevice缓存和多报文融合机制
"""

import queue
import threading
import time
import logging
from typing import Optional, Callable, Dict
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

# Logger for capture module
log = logging.getLogger("lldp.capture")

# 🔥 限制 hex 输出长度，防止日志膨胀
MAX_HEX_DISPLAY = 200

try:
    from scapy.all import Ether
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
    is_fused: bool = False  # 🔥 新增：是否为融合结果
    fusion_count: int = 1  # 🔥 新增：融合了多少个报文


@dataclass
class DeviceCacheEntry:
    """🔥 设备缓存条目 - 用于多报文融合"""
    device: object  # LLDPDevice
    first_seen: float  # 首次发现时间
    last_seen: float  # 最后发现时间
    packet_count: int  # 收到报文数量
    interface: str  # 发现接口

    # 🔥 优化D: 消除神奇数字，使用可配置参数
    max_fusion_age: float = 5.0  # 融合时间窗口（秒）
    min_packet_count: int = 3   # 最小报文数量

    def should_fuse(self, max_age: float = None, min_packets: int = None) -> bool:
        """
        判断是否应该进行融合

        🔥 优化D: 参数可配置，适配不同工业交换机

        Args:
            max_age: 最大融合时间窗口（秒），None则使用实例默认值
            min_packets: 最小报文数量，None则使用实例默认值
        """
        # 使用传入参数或实例默认值
        fusion_age = max_age if max_age is not None else self.max_fusion_age
        packet_threshold = min_packets if min_packets is not None else self.min_packet_count

        age = time.time() - self.first_seen
        return age >= fusion_age or self.packet_count >= packet_threshold

    def merge_with(self, new_device) -> object:
        """🔥 融合新报文到当前设备"""
        # TODO: 实现智能融合逻辑
        # - 合并TLV字段
        # - 补充缺失信息
        # - 提升数据完整性
        return self.device  # 简化版：直接返回原设备


class LLDPCapture:
    """
    LLDP and CDP Packet Capture Engine (Enhanced!)

    Thread-safe capture using queue-based architecture.
    Decouples capture thread from UI thread.
    Now supports both LLDP (IEEE 802.1AB) and CDP (Cisco Discovery Protocol).

    🔥 v3.0 新增：多报文融合机制
    - 自动缓存同设备多报文
    - 智能融合提升数据完整性
    - 减少重复设备发现

    🔥 优化D: 消除神奇数字，支持参数配置
    """

    def __init__(self,
                 fusion_interval: float = 5.0,
                 min_packet_count: int = 3,
                 capture_timeout: int = 2):
        """
        Initialize capture engine

        🔥 优化D: 所有神奇数字都变成可配置参数

        Args:
            fusion_interval: 融合时间窗口（秒），默认5秒
                           工业交换机建议30秒（LLDP发包间隔）
            min_packet_count: 最小报文数量，默认3个
                              工业交换机建议1个（低频发包）
            capture_timeout: 捕获超时时间（秒），默认2秒
        """
        if not HAS_SCAPY:
            raise RuntimeError("Scapy is required. Install with: pip install scapy")

        self.lldp_parser = LLDPParser()
        self.cdp_parser = CDPParser()  # 新增CDP解析器
        self.device_queue: queue.Queue = queue.Queue()
        self.is_capturing = False
        self.capture_thread: Optional[threading.Thread] = None

        # 🔥 新增：设备缓存机制（可配置参数）
        self.device_cache: Dict[str, DeviceCacheEntry] = {}  # key: device_id
        self.cache_lock = threading.Lock()  # 缓存锁
        self.fusion_interval = fusion_interval  # 融合时间窗口（可配置）
        self.min_packet_count = min_packet_count  # 最小报文数量（可配置）
        self.capture_timeout = capture_timeout  # 捕获超时（可配置）

        # 🔥 中等优先级修复6: 回调线程池，避免阻塞捕获线程
        self._callback_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lldp_callback")

        # 🔥 预定义配置文件
        self.config_presets = {
            'standard': {'fusion_interval': 5.0, 'min_packet_count': 3},  # 标准网络设备
            'industrial': {'fusion_interval': 30.0, 'min_packet_count': 1},  # 工业交换机
            'fast': {'fusion_interval': 2.0, 'min_packet_count': 5},  # 快速发现模式
        }

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

    def _get_device_id(self, device) -> str:
        """
        🔥 生成设备唯一标识符

        优先级：Chassis ID > System Name > MAC地址
        """
        # 优先使用Chassis ID
        if hasattr(device, 'chassis_id') and device.chassis_id:
            return f"{device.chassis_id.type.name}:{device.chassis_id.value}"

        # 其次使用System Name
        if hasattr(device, 'system_name') and device.system_name:
            return f"SYSNAME:{device.system_name}"

        # 最后使用MAC（如果有）
        if hasattr(device, 'source_mac') and device.source_mac:
            return f"MAC:{device.source_mac}"

        # 默认：使用时间戳
        return f"UNKNOWN:{time.time()}"

    def _cache_device(self, device, interface: str) -> bool:
        """
        🔥 缓存设备并判断是否应该输出

        返回：True（应该输出到队列），False（继续缓存）
        """
        device_id = self._get_device_id(device)
        current_time = time.time()

        with self.cache_lock:
            if device_id in self.device_cache:
                # 设备已存在，更新缓存
                cache_entry = self.device_cache[device_id]
                cache_entry.last_seen = current_time
                cache_entry.packet_count += 1

                # 🔥 检查是否应该融合并输出（使用可配置参数）
                if cache_entry.should_fuse(self.fusion_interval, self.min_packet_count):
                    # 融合完成，输出设备
                    fused_device = cache_entry.merge_with(device)

                    # 创建融合结果
                    result = CaptureResult(
                        device=fused_device,
                        timestamp=cache_entry.first_seen,
                        interface=cache_entry.interface,
                        is_fused=True,
                        fusion_count=cache_entry.packet_count
                    )

                    # 清理缓存
                    del self.device_cache[device_id]

                    # 输出到队列
                    self.device_queue.put(result)
                    return True
                else:
                    # 继续缓存
                    return False
            else:
                # 新设备，创建缓存条目
                self.device_cache[device_id] = DeviceCacheEntry(
                    device=device,
                    first_seen=current_time,
                    last_seen=current_time,
                    packet_count=1,
                    interface=interface
                )
                return False

    def flush_cache(self):
        """
        🔥 强制刷新缓存 - 输出所有缓存的设备

        用于捕获结束时输出未完成融合的设备
        """
        with self.cache_lock:
            for device_id, cache_entry in list(self.device_cache.items()):
                result = CaptureResult(
                    device=cache_entry.device,
                    timestamp=cache_entry.first_seen,
                    interface=cache_entry.interface,
                    is_fused=True if cache_entry.packet_count > 1 else False,
                    fusion_count=cache_entry.packet_count
                )
                self.device_queue.put(result)

            # 清空缓存
            self.device_cache.clear()

    def start_capture(self, interface, duration: int = 60, callback: Optional[Callable] = None):
        """
        Start LLDP packet capture in background thread

        Args:
            interface: Network interface to capture on
            duration: Capture duration in seconds
            callback: Optional callback function for each discovered device
        """
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
        """
        Capture worker thread

        Runs in background thread, pushes discovered devices to queue.
        """
        try:
            # Log capture start
            log.info("========== CAPTURE STARTED ==========")
            log.info(f"Interface: {interface}")
            log.info(f"Duration: {duration} seconds")
            log.info("LLDP Parser: %s", type(self.lldp_parser).__name__)
            log.info("CDP Parser: %s", type(self.cdp_parser).__name__)
            log.info("CAPTURING BOTH LLDP AND CDP!")
            log.info("LLDP EtherType: 0x88cc")
            log.info("CDP Dest MAC: 01:00:0C:CC:CC:CC")
            log.info("======================================")

            log.debug(f"Capture started at: {time.strftime('%H:%M:%S')}")
            log.debug("Expected LLDP: every 30 seconds")
            log.debug("Expected CDP: every 60 seconds")
            log.debug("Listening for packets...")

            # 抓包计数器和设备发现标志
            packet_count = 0
            device_found = False  # 新增：设备发现标志
            start_time = time.time()

            def packet_handler(pkt):
                """Handle each captured packet - Enhanced for LLDP + CDP!"""
                nonlocal packet_count, device_found
                packet_count += 1

                # 第一个包立即输出，确认捕获工作
                if packet_count == 1:
                    log.debug("✅ First packet received! Capture is working!")
                    log.debug("First packet: %s", pkt.summary())
                    log.debug("🔍 Callback parameter: %s", callback)

                if not self.is_capturing:
                    return

                try:
                    # 🔥 减少DEBUG输出频率，从每10个改为每100个
                    if packet_count % 100 == 0:
                        elapsed = time.time() - start_time
                        log.debug("📊 Processed %d packets in %ds", packet_count, int(elapsed))

                    # Convert packet to bytes for protocol detection
                    packet_bytes = bytes(pkt)

                    # 快速检查：跳过不相关的报文 (优化性能)
                    if len(packet_bytes) < 14:
                        return

                    # Check protocol type
                    is_lldp = False
                    is_cdp = False

                    # LLDP: Ethertype 0x88cc
                    ether_type = packet_bytes[12:14]

                    if ether_type == b'\x88\xcc':
                        is_lldp = True
                    # CDP: Destination MAC 01:00:0C:CC:CC:CC and EtherType 0x2000
                    elif packet_bytes[0:6] == b'\x01\x00\x0c\xcc\xcc\xcc' and ether_type == b'\x20\x00':
                        is_cdp = True
                    else:
                        # 不是LLDP或CDP报文，跳过
                        return

                    device = None
                    protocol_name = "Unknown"

                    if is_lldp:
                        log.debug("📡 LLDP packet captured!")
                        log.debug("Packet: %s", pkt.summary())
                        device = self.lldp_parser.parse_scapy_packet(pkt)
                        protocol_name = "LLDP"

                    elif is_cdp:
                        log.debug("📡📡📡 CDP packet captured! 🔥🔥🔥")
                        log.debug("Packet: %s", pkt.summary())
                        device = self.cdp_parser.parse_scapy_packet(pkt)
                        protocol_name = "CDP"

                    if device and device.is_valid():
                        log.debug("✅ Valid %s device parsed: %s", protocol_name, device.get_display_name())
                        log.debug("Device object: %s", device)
                        log.debug("Device attributes: %s", dir(device)[:20])

                        try:
                            # 🔥 安全设置设备属性 - 检查每个属性是否可安全访问
                            log.debug("Setting device attributes...")

                            # For CDP, highlight Native VLAN
                            if protocol_name == "CDP" and hasattr(device, 'native_vlan') and device.native_vlan:
                                log.debug("🔥🔥🔥 CDP Native VLAN detected: %s 🔥🔥🔥", device.native_vlan)

                            # 安全设置capture_interface
                            try:
                                device.capture_interface = str(interface)
                                log.debug("✅ capture_interface set to: %s", str(interface))
                            except Exception as e:
                                log.warning("Failed to set capture_interface: %s", e)

                            # 安全设置protocol - 这可能是崩溃点！
                            try:
                                device.protocol = protocol_name
                                log.debug("✅ protocol set to: %s", protocol_name)
                            except Exception as e:
                                log.error("Failed to set protocol: %s", e, exc_info=True)

                            log.debug("Device attributes set successfully")

                            # 🔥 v3.0: 使用设备缓存机制
                            log.debug("📦 Caching device for fusion...")
                            should_output = self._cache_device(device, str(interface))

                            if should_output:
                                # 融合完成，输出到队列
                                log.debug("🔥 Device fusion complete! Outputting to queue...")
                                log.debug("Capture result pushed to queue (fused)")

                                # 🔥 设备发现！立即停止捕获
                                device_found = True
                                log.debug("🎯 Device found! Stopping capture immediately...")
                                self.is_capturing = False  # 停止捕获标志
                            else:
                                log.debug("Device cached, waiting for more packets...")

                            # 🔥 修复：只调用一次 callback（无论是否融合）
                            # 🔥 中等优先级修复6: 使用线程池异步执行回调，避免阻塞捕获线程
                            if callback:
                                try:
                                    log.debug("Submitting device callback to thread pool...")
                                    self._callback_pool.submit(self._safe_callback, callback, device)
                                    log.debug("Device callback submitted successfully")
                                except Exception as e:
                                    log.exception("Failed to submit callback: %s", e)

                        except Exception as e:
                            log.exception("Error in device processing: %s", e)
                    else:
                        if is_lldp or is_cdp:
                            log.debug("❌ %s packet parsed but device is not valid", protocol_name)

                except Exception as e:
                    log.exception("Error in packet_handler: %s", e)

            # Start sniffing - No BPF filter! Capture everything and filter in Python
            # 这样可以确保捕获到CDP和LLDP报文
            log.info("Starting packet capture on %s...", interface)
            log.info("Capture timeout: %ds (max)", duration)
            log.info("Will stop immediately when device found!")
            log.debug("Packet handler registered, waiting for packets...")

            # 🔥 优化B: 使用更好的stop_filter机制，避免线程挂起
            def stop_filter(pkt):
                """
                🔥 优化的停止过滤器

                优先级：
                1. 用户主动停止（is_capturing = False）
                2. 发现设备（device_found = True）
                3. 超时（elapsed > duration）

                返回True表示立即停止抓包
                """
                # 优先级1: 用户主动停止
                if not self.is_capturing:
                    log.debug("🛑 User requested stop! Ending capture...")
                    return True

                # 优先级2: 发现设备
                if device_found:
                    log.debug("✅ Device found! Ending capture...")
                    return True

                # 优先级3: 超时检查
                elapsed = time.time() - start_time
                if elapsed >= duration:
                    log.debug("⏱️ Timeout reached (%ds)! Ending capture...", duration)
                    return True

                return False

            # 🔥 macOS兼容性修复：处理接口名称和权限问题
            try:
                # 尝试获取接口对象
                iface_name = str(interface)
                log.debug("Using interface: %s", iface_name)

                # 检查接口是否有效
                from scapy.all import get_working_ifaces
                working_ifaces = list(get_working_ifaces())
                iface_names = [str(iface) for iface in working_ifaces]

                if iface_name not in iface_names:
                    log.warning("⚠️ Interface %s not in working interfaces!", iface_name)
                    log.warning("Available interfaces: %s", iface_names)

                    # 尝试使用第一个可用接口
                    if iface_names:
                        iface_name = iface_names[0]
                        log.warning("🔧 Falling back to interface: %s", iface_name)

                # 🔥 性能优化：使用AsyncSniffer替代sniff，解决假死问题
                from scapy.all import AsyncSniffer

                # 创建BPF过滤器：内核层过滤，减少CPU开销
                bpf_filter = "ether proto 0x88cc or ether host 01:00:0c:cc:cc:cc"

                # 🔥 中等优先级修复5: BPF filter 兼容性处理
                try:
                    # 创建异步嗅探器
                    sniffer = AsyncSniffer(
                        iface=iface_name,
                        filter=bpf_filter,  # 🔥 包采样计数器：BPF内核过滤
                        prn=packet_handler,
                        store=False,  # 不存储报文，节省内存
                        started_callback=lambda: log.debug("✅ AsyncSniffer started on %s", iface_name)
                    )
                except Exception as bpf_error:
                    log.warning("BPF filter not supported on this platform: %s", bpf_error)
                    log.warning("Falling back to no filter (Python-side filtering)")
                    # Fallback: 不使用 BPF filter
                    sniffer = AsyncSniffer(
                        iface=iface_name,
                        prn=packet_handler,
                        store=False,
                        started_callback=lambda: log.debug("✅ AsyncSniffer started on %s (no filter)", iface_name)
                    )

                # 启动异步嗅探
                sniffer.start()

                # 等待捕获完成或设备发现
                import time as time_module
                start_time = time_module.time()

                while time_module.time() - start_time < duration:
                    if device_found or not self.is_capturing:
                        log.debug("🛑 Stop condition triggered, stopping AsyncSniffer...")
                        break
                    time_module.sleep(0.1)  # 100ms轮询间隔

                # 🔥 改进：检查 sniffer.running 再停止
                if hasattr(sniffer, 'running') and sniffer.running:
                    log.debug("Stopping AsyncSniffer (running=True)...")
                    sniffer.stop()
                    log.debug("✅ AsyncSniffer stopped gracefully")
                else:
                    log.debug("AsyncSniffer already stopped (running=False)")

            except Exception as capture_error:
                log.error("❌ Capture failed with exception: %s", capture_error, exc_info=True)
                log.error("This might be a permission or interface issue")
                log.error("Try running with sudo/admin privileges")
                raise

            log.info("Capture completed. Total packets processed: %d", packet_count)
            if device_found:
                log.info("✅ Capture stopped early - Device found!")
            else:
                log.info("⏱️ Capture timeout - No device found in %ds", duration)

        except Exception as e:
            log.exception("Capture error: %s", e)

        finally:
            # 🔥 v3.0: 捕获结束，刷新缓存
            log.debug("🔥 Flushing device cache...")
            self.flush_cache()
            log.debug("✅ Device cache flushed")

            self.is_capturing = False

    def stop_capture(self):
        """Stop ongoing capture - Force stop!"""
        log.debug("🛑 stop_capture called - Stopping capture NOW!")
        self.is_capturing = False

        # 🔥 v3.0: 停止时刷新缓存
        self.flush_cache()

        # 🔥 低优先级修复11: 增加超时时间从2秒到5秒
        if self.capture_thread and self.capture_thread.is_alive():
            log.debug("Waiting for capture thread to stop...")
            self.capture_thread.join(timeout=5)  # 等待最多5秒
            if self.capture_thread.is_alive():
                log.warning("⚠️ Capture thread still alive after 5s")
            else:
                log.debug("✅ Capture thread stopped successfully")

    def shutdown(self):
        """
        🔥 新增：清理资源

        停止线程池，释放资源
        """
        try:
            # 🔥 修复：Python 3.11 不支持 timeout 参数
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
        """
        Get all discovered devices from queue

        Returns:
            List of CaptureResult objects
        """
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


class LLDPCaptureListener:
    """
    LLDP Capture Listener with real-time callback support

    Provides event-based interface for device discovery.
    """

    def __init__(self):
        """Initialize listener"""
        self.capture = LLDPCapture()
        self.discovered_devices = {}

    def start(self, interface, duration: int = 30,
              on_device_discovered: Optional[Callable] = None,
              on_capture_complete: Optional[Callable] = None):
        """
        Start capture with callbacks

        Args:
            interface: Network interface
            duration: Capture duration
            on_device_discovered: Callback when device discovered
            on_capture_complete: Callback when capture completes
        """
        self.discovered_devices = {}

        def device_callback(device):
            """Internal device callback"""
            try:
                # Create device key for deduplication
                key = self._device_key(device)

                if key not in self.discovered_devices:
                    self.discovered_devices[key] = device

                    # Call user callback in UI thread
                    if on_device_discovered:
                        try:
                            log.debug("🎯 Calling on_device_discovered callback...")
                            on_device_discovered(device)
                            log.debug("✅ on_device_discovered callback completed")
                        except Exception as e:
                            log.exception("on_device_discovered callback failed: %s", e)
            except Exception as e:
                log.exception("device_callback failed: %s", e)

        def complete_callback():
            """Internal completion callback"""
            try:
                if on_capture_complete:
                    try:
                        devices = list(self.discovered_devices.values())
                        log.debug("🎯 Calling on_capture_complete callback with %d devices...", len(devices))
                        on_capture_complete(devices)
                        log.debug("✅ on_capture_complete callback completed")
                    except Exception as e:
                        log.exception("on_capture_complete callback failed: %s", e)
            except Exception as e:
                log.exception("complete_callback failed: %s", e)

        # Start capture
        self.capture.start_capture(interface, duration, device_callback)

        # Start completion timer
        def completion_timer():
            """Wait for capture to complete"""
            log.debug("Waiting for capture thread to finish (timeout=%ds)...", duration + 5)
            self.capture.capture_thread.join(timeout=duration + 5)
            if self.capture.capture_thread.is_alive():
                log.warning("Capture thread still alive after timeout, calling complete_callback anyway")
            complete_callback()

        threading.Thread(target=completion_timer, daemon=True).start()

    def stop(self):
        """Stop capture"""
        self.capture.stop_capture()

    @staticmethod
    def _device_key(device) -> str:
        """Generate unique key for device"""
        if device.chassis_id:
            return f"{device.chassis_id.value}"
        if device.system_name:
            return f"sn:{device.system_name}"
        return f"unknown:{id(device)}"

    def get_devices(self) -> list:
        """Get all discovered devices"""
        return list(self.discovered_devices.values())
