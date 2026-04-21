"""
LLDP and CDP Packet Capture
Capture layer with queue-based threading - Enhanced with CDP support!
"""

import queue
import threading
import time
import logging
from typing import Optional, Callable
from dataclasses import dataclass

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


class LLDPCapture:
    """
    LLDP and CDP Packet Capture Engine (Enhanced!)

    Thread-safe capture using queue-based architecture.
    Decouples capture thread from UI thread.
    Now supports both LLDP (IEEE 802.1AB) and CDP (Cisco Discovery Protocol).
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

                            # Push to queue
                            print(f"[DEBUG] Creating capture result...")
                            result = CaptureResult(
                                device=device,
                                timestamp=time.time(),
                                interface=str(interface)
                            )
                            self.device_queue.put(result)
                            print(f"[DEBUG] Capture result pushed to queue")

                            # 🔥 设备发现！立即停止捕获
                            nonlocal device_found
                            device_found = True
                            print(f"[DEBUG] 🎯 Device found! Stopping capture immediately...", flush=True)
                            self.is_capturing = False  # 停止捕获标志

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
            self.is_capturing = False

    def stop_capture(self):
        """Stop ongoing capture - Force stop!"""
        print(f"[DEBUG] 🛑 stop_capture called - Stopping capture NOW!", flush=True)
        self.is_capturing = False

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
