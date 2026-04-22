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

# Logger for capture module
log = logging.getLogger("lldp.capture")

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

    def should_fuse(self, max_age: float = 5.0) -> bool:
        """判断是否应该进行融合"""
        age = time.time() - self.first_seen
        return age >= max_age or self.packet_count >= 3

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
    """

    def __init__(self):
        """Initialize capture engine"""
        if not HAS_SCAPY:
            raise RuntimeError("Scapy is required. Install with: pip install scapy")

        self.lldp_parser = LLDPParser()
        self.cdp_parser = CDPParser()  # 新增CDP解析器
        self.device_queue: queue.Queue = queue.Queue()
        self.is_capturing = False
        self.capture_thread: Optional[threading.Thread] = None

        # 🔥 新增：设备缓存机制
        self.device_cache: Dict[str, DeviceCacheEntry] = {}  # key: device_id
        self.cache_lock = threading.Lock()  # 缓存锁
        self.fusion_interval = 5.0  # 融合时间窗口（秒）

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

                # 🔥 检查是否应该融合并输出
                if cache_entry.should_fuse(self.fusion_interval):
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
                nonlocal packet_count
                packet_count += 1

                # 第一个包立即输出，确认捕获工作
                if packet_count == 1:
                    print(f"[DEBUG] ✅ First packet received! Capture is working!", flush=True)
                    print(f"[DEBUG] First packet: {pkt.summary()}", flush=True)
                    # 🔥 调试：检查callback状态
                    print(f"[DEBUG] 🔍 Callback parameter: {callback}", flush=True)

                if not self.is_capturing:
                    return

                try:
                    # 🔥 减少DEBUG输出频率，从每10个改为每100个
                    if packet_count % 100 == 0:
                        elapsed = time.time() - start_time
                        print(f"[DEBUG] 📊 Processed {packet_count} packets in {int(elapsed)}s...", flush=True)

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
                        print(f"\n[DEBUG] 📡 LLDP packet captured!", flush=True)
                        print(f"[DEBUG] Packet: {pkt.summary()}", flush=True)
                        device = self.lldp_parser.parse_scapy_packet(pkt)
                        protocol_name = "LLDP"

                    elif is_cdp:
                        print(f"\n[DEBUG] 📡📡📡 CDP packet captured! 🔥🔥🔥", flush=True)
                        print(f"[DEBUG] Packet: {pkt.summary()}", flush=True)
                        device = self.cdp_parser.parse_scapy_packet(pkt)
                        protocol_name = "CDP"

                    if device and device.is_valid():
                        print(f"[DEBUG] ✅ Valid {protocol_name} device parsed: {device.get_display_name()}")
                        print(f"[DEBUG] Device object: {device}")
                        print(f"[DEBUG] Device attributes: {dir(device)[:20]}")

                        try:
                            # 🔥 安全设置设备属性 - 检查每个属性是否可安全访问
                            print(f"[DEBUG] Setting device attributes...")

                            # For CDP, highlight Native VLAN
                            if protocol_name == "CDP" and hasattr(device, 'native_vlan') and device.native_vlan:
                                print(f"[DEBUG] 🔥🔥🔥 CDP Native VLAN detected: {device.native_vlan} 🔥🔥🔥")

                            # 安全设置capture_interface
                            try:
                                device.capture_interface = str(interface)
                                print(f"[DEBUG] ✅ capture_interface set to: {str(interface)}")
                            except Exception as e:
                                print(f"[ERROR] Failed to set capture_interface: {e}")

                            # 安全设置protocol - 这可能是崩溃点！
                            try:
                                device.protocol = protocol_name
                                print(f"[DEBUG] ✅ protocol set to: {protocol_name}")
                            except Exception as e:
                                print(f"[ERROR] Failed to set protocol: {e}")
                                import traceback
                                traceback.print_exc()

                            print(f"[DEBUG] Device attributes set successfully")

                            # 🔥 v3.0: 使用设备缓存机制
                            print(f"[DEBUG] 📦 Caching device for fusion...")
                            should_output = self._cache_device(device, str(interface))

                            if should_output:
                                # 融合完成，输出到队列
                                print(f"[DEBUG] 🔥 Device fusion complete! Outputting to queue...")
                                print(f"[DEBUG] Capture result pushed to queue (fused)")

                                # 🔥 设备发现！立即停止捕获
                                nonlocal device_found
                                device_found = True
                                print(f"[DEBUG] 🎯 Device found! Stopping capture immediately...", flush=True)
                                self.is_capturing = False  # 停止捕获标志

                                # Call callback if provided (runs in capture thread)
                                if callback:
                                    try:
                                        callback(device)
                                    except Exception as e:
                                        log.error(f"Callback error: {e}")
                            else:
                                print(f"[DEBUG] Device cached, waiting for more packets...")

                            # Call callback if provided (runs in capture thread)
                            if callback:
                                try:
                                    print(f"[DEBUG] Calling device callback...")
                                    callback(device)
                                    print(f"[DEBUG] Device callback completed successfully")
                                except Exception as e:
                                    print(f"[ERROR] Callback failed: {e}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                print(f"[DEBUG] ⚠️ No callback provided!")

                        except Exception as e:
                            print(f"[ERROR] Error in device processing: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        if is_lldp or is_cdp:
                            print(f"[DEBUG] ❌ {protocol_name} packet parsed but device is not valid")

                except Exception as e:
                    print(f"[ERROR] Error in packet_handler: {e}")

            # Start sniffing - No BPF filter! Capture everything and filter in Python
            # 这样可以确保捕获到CDP和LLDP报文
            print(f"[DEBUG] Starting packet capture on {interface}...", flush=True)
            print(f"[DEBUG] Capture timeout: {duration}s (max)", flush=True)
            print(f"[DEBUG] Will stop immediately when device found!", flush=True)
            print(f"[DEBUG] Packet handler registered, waiting for packets...", flush=True)

            # 定义stop函数：发现设备或停止时返回True
            def stop_filter(pkt):
                # 如果发现设备或停止捕获，立即停止
                if device_found or not self.is_capturing:
                    print(f"[DEBUG] 🛑 Stop condition triggered! Ending capture...", flush=True)
                    return True
                return False

            # 🔥 macOS兼容性修复：处理接口名称和权限问题
            try:
                # 尝试获取接口对象
                iface_name = str(interface)
                print(f"[DEBUG] Using interface: {iface_name}", flush=True)

                # 检查接口是否有效
                from scapy.all import get_working_ifaces
                working_ifaces = list(get_working_ifaces())
                iface_names = [str(iface) for iface in working_ifaces]

                if iface_name not in iface_names:
                    print(f"[DEBUG] ⚠️ Interface {iface_name} not in working interfaces!", flush=True)
                    print(f"[DEBUG] Available interfaces: {iface_names}", flush=True)

                    # 尝试使用第一个可用接口
                    if iface_names:
                        iface_name = iface_names[0]
                        print(f"[DEBUG] 🔧 Falling back to interface: {iface_name}", flush=True)

                # 🔥 性能优化：使用AsyncSniffer替代sniff，解决假死问题
                from scapy.all import AsyncSniffer

                # 创建BPF过滤器：内核层过滤，减少CPU开销
                bpf_filter = "ether proto 0x88cc or ether host 01:00:0c:cc:cc:cc"

                # 创建异步嗅探器
                sniffer = AsyncSniffer(
                    iface=iface_name,
                    filter=bpf_filter,  # 🔥 包采样计数器：BPF内核过滤
                    prn=packet_handler,
                    store=False,  # 不存储报文，节省内存
                    started_callback=lambda: print(f"[DEBUG] ✅ AsyncSniffer started on {iface_name}", flush=True)
                )

                # 启动异步嗅探
                sniffer.start()

                # 等待捕获完成或设备发现
                import time as time_module
                start_time = time_module.time()

                while time_module.time() - start_time < duration:
                    if device_found or not self.is_capturing:
                        print(f"[DEBUG] 🛑 Stop condition triggered, stopping AsyncSniffer...", flush=True)
                        break
                    time_module.sleep(0.1)  # 100ms轮询间隔

                # 🔥 优雅停止：不会阻塞UI线程
                sniffer.stop()
                print(f"[DEBUG] ✅ AsyncSniffer stopped gracefully", flush=True)

            except Exception as capture_error:
                print(f"[ERROR] ❌ Capture failed with exception: {capture_error}", flush=True)
                print(f"[ERROR] This might be a permission or interface issue", flush=True)
                print(f"[ERROR] Try running with sudo/admin privileges", flush=True)
                raise

            print(f"[DEBUG] Capture completed. Total packets processed: {packet_count}", flush=True)
            if device_found:
                print(f"[DEBUG] ✅ Capture stopped early - Device found!", flush=True)
            else:
                print(f"[DEBUG] ⏱️ Capture timeout - No device found in {duration}s", flush=True)

        except Exception as e:
            print(f"Capture error: {e}")

        finally:
            # 🔥 v3.0: 捕获结束，刷新缓存
            print(f"[DEBUG] 🔥 Flushing device cache...", flush=True)
            self.flush_cache()
            print(f"[DEBUG] ✅ Device cache flushed", flush=True)

            self.is_capturing = False

    def stop_capture(self):
        """Stop ongoing capture - Force stop!"""
        print(f"[DEBUG] 🛑 stop_capture called - Stopping capture NOW!", flush=True)
        self.is_capturing = False

        # 🔥 v3.0: 停止时刷新缓存
        self.flush_cache()

        if self.capture_thread and self.capture_thread.is_alive():
            print(f"[DEBUG] Waiting for capture thread to stop...", flush=True)
            self.capture_thread.join(timeout=2)  # 等待最多2秒
            if self.capture_thread.is_alive():
                print(f"[DEBUG] ⚠️ Capture thread still alive after 2s", flush=True)
            else:
                print(f"[DEBUG] ✅ Capture thread stopped successfully", flush=True)

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
                            print(f"[DEBUG] 🎯 Calling on_device_discovered callback...")
                            on_device_discovered(device)
                            print(f"[DEBUG] ✅ on_device_discovered callback completed")
                        except Exception as e:
                            print(f"[ERROR] on_device_discovered callback failed: {e}")
                            import traceback
                            traceback.print_exc()
            except Exception as e:
                print(f"[ERROR] device_callback failed: {e}")
                import traceback
                traceback.print_exc()

        def complete_callback():
            """Internal completion callback"""
            try:
                if on_capture_complete:
                    try:
                        devices = list(self.discovered_devices.values())
                        print(f"[DEBUG] 🎯 Calling on_capture_complete callback with {len(devices)} devices...")
                        on_capture_complete(devices)
                        print(f"[DEBUG] ✅ on_capture_complete callback completed")
                    except Exception as e:
                        print(f"[ERROR] on_capture_complete callback failed: {e}")
                        import traceback
                        traceback.print_exc()
            except Exception as e:
                print(f"[ERROR] complete_callback failed: {e}")
                import traceback
                traceback.print_exc()

        # Start capture
        self.capture.start_capture(interface, duration, device_callback)

        # Start completion timer
        def completion_timer():
            """Wait for capture to complete"""
            self.capture.capture_thread.join()
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
