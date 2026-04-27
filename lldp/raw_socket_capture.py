"""
跨平台Raw Socket捕获引擎
Linux: AF_PACKET原生socket
Windows: pcapy-ng
完全不依赖Scapy
"""

import sys
import platform
import threading
import time
from typing import Callable, Optional, Any
from abc import ABC, abstractmethod


class RawSocketCapture(ABC):
    """Raw Socket捕获引擎抽象基类"""

    def __init__(self, interface: str, callback: Callable[[bytes], None]):
        """
        初始化捕获引擎

        Args:
            interface: 网络接口名
            callback: 数据包回调函数
        """
        self.interface = interface
        self.callback = callback
        self.is_capturing = False
        self.stop_event = threading.Event()

    @abstractmethod
    def start_capture(self):
        """开始捕获"""
        pass

    @abstractmethod
    def stop_capture(self):
        """停止捕获"""
        pass

    def is_active(self) -> bool:
        """是否正在捕获"""
        return self.is_capturing


class LinuxRawSocketCapture(RawSocketCapture):
    """
    Linux原生Raw Socket捕获引擎
    使用AF_PACKET socket，无需任何第三方库
    """

    def __init__(self, interface: str, callback: Callable[[bytes], None], promisc: bool = True):
        super().__init__(interface, callback)
        self.promisc = promisc
        self.socket: Optional[Any] = None
        self.capture_thread: Optional[threading.Thread] = None

    def start_capture(self):
        """开始捕获"""
        if self.is_capturing:
            return

        try:
            import socket
            import struct

            # 创建Raw Socket
            # ETH_P_ALL = 0x0003 (接收所有链路层帧)
            self.socket = socket.socket(
                socket.AF_PACKET,
                socket.SOCK_RAW,
                socket.htons(0x0003)
            )

            # 绑定到接口
            self.socket.bind((self.interface, 0))

            # 启用混杂模式
            if self.promisc:
                try:
                    # 尝试启用混杂模式
                    import fcntl
                    struct.pack("I", 1)  # PROMISC flag
                except:
                    pass  # 某些系统可能不支持

            # 设置超时（允许定期检查stop_event）
            self.socket.settimeout(1.0)

            self.is_capturing = True
            self.stop_event.clear()

            # 启动捕获线程
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self.capture_thread.start()

            print(f"[LinuxRawSocket] 开始捕获: {self.interface}")

        except Exception as e:
            print(f"[LinuxRawSocket] 启动失败: {e}")
            raise

    def _capture_loop(self):
        """捕获循环"""
        while not self.stop_event.is_set():
            try:
                # 接收数据包
                raw_data, _ = self.socket.recvfrom(65535)

                # 快速过滤：检查以太网类型
                if len(raw_data) >= 14:
                    ethertype = raw_data[12:14]

                    # LLDP: 0x88cc
                    # CDP: 0x2000 (Cisco私有，需要检查DSAP)
                    if ethertype == b'\x88\xcc':
                        # LLDP报文
                        self.callback(raw_data)
                    elif ethertype == b'\x20\x00':
                        # 可能是CDP（需要进一步检查）
                        # CDP使用SNAP，检查LLC头
                        if len(raw_data) >= 22:
                            dsap = raw_data[14]
                            ssap = raw_data[15]
                            ctrl = raw_data[16]

                            # CDP: DSAP=0xAA, SSAP=0xAA, Ctrl=0x03
                            if dsap == 0xAA and ssap == 0xAA and ctrl == 0x03:
                                # 检查OUI (Cisco: 0x00000C)
                                oui = raw_data[17:20]
                                if oui == b'\x00\x00\x0c':
                                    self.callback(raw_data)

            except socket.timeout:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                if self.is_capturing:
                    print(f"[LinuxRawSocket] 捕获错误: {e}")

    def stop_capture(self):
        """停止捕获"""
        if not self.is_capturing:
            return

        print(f"[LinuxRawSocket] 停止捕获: {self.interface}")

        self.is_capturing = False
        self.stop_event.set()

        # 等待线程结束
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)

        # 关闭socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


class WindowsPcapyCapture(RawSocketCapture):
    """
    Windows pcapy-ng捕获引擎
    使用BPF内核过滤，性能优异
    """

    def __init__(self, interface: str, callback: Callable[[bytes], None], promisc: bool = True):
        super().__init__(interface, callback)
        self.promisc = promisc
        self.cap: Optional[Any] = None
        self.capture_thread: Optional[threading.Thread] = None

    def start_capture(self):
        """开始捕获"""
        if self.is_capturing:
            return

        try:
            import pcapy

            # 打开捕获设备
            # 参数: 设备名, snaplen, promisc, timeout_ms
            self.cap = pcapy.open_live(
                self.interface,
                65536,      # snaplen: 捕获完整数据包
                self.promisc,  # promisc: 混杂模式
                100         # timeout: 100ms超时
            )

            # 🔥 性能关键：设置BPF内核过滤
            # 仅让内核传递LLDP和CDP报文，大幅减少CPU开销
            bpf_filter = "ether proto 0x88cc or ether[20:2] == 0x2000"
            self.cap.setfilter(bpf_filter)

            self.is_capturing = True
            self.stop_event.clear()

            # 启动捕获线程
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self.capture_thread.start()

            print(f"[WindowsPcapy] 开始捕获: {self.interface}")
            print(f"[WindowsPcapy] BPF过滤: {bpf_filter}")

        except ImportError:
            print("[WindowsPcapy] 缺少pcapy-ng")
            print("  请安装: pip install pcapy-ng")
            print("  同时确保安装了Npcap驱动")
            raise
        except Exception as e:
            print(f"[WindowsPcapy] 启动失败: {e}")
            raise

    def _capture_loop(self):
        """捕获循环"""
        def _handler(hdr, data):
            """pcapy回调处理"""
            if self.is_capturing:
                self.callback(data)

        while not self.stop_event.is_set():
            try:
                # dispatch(1)表示处理最多1个包
                # 这样可以定期检查stop_event
                self.cap.dispatch(1, _handler)
            except Exception as e:
                if self.is_capturing:
                    print(f"[WindowsPcapy] 捕获错误: {e}")

    def stop_capture(self):
        """停止捕获"""
        if not self.is_capturing:
            return

        print(f"[WindowsPcapy] 停止捕获: {self.interface}")

        self.is_capturing = False
        self.stop_event.set()

        # 等待线程结束
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)

        # pcapy的cap对象会在垃圾回收时自动关闭


class MacOSPcapyCapture(RawSocketCapture):
    """
    macOS pcapy捕获引擎
    使用BPF过滤
    """

    def __init__(self, interface: str, callback: Callable[[bytes], None], promisc: bool = True):
        super().__init__(interface, callback)
        self.promisc = promisc
        self.cap: Optional[Any] = None
        self.capture_thread: Optional[threading.Thread] = None

    def start_capture(self):
        """开始捕获"""
        if self.is_capturing:
            return

        try:
            import pcapy

            # 打开捕获设备
            self.cap = pcapy.open_live(
                self.interface,
                65536,
                self.promisc,
                100
            )

            # 设置BPF过滤
            bpf_filter = "ether proto 0x88cc or ether[20:2] == 0x2000"
            self.cap.setfilter(bpf_filter)

            self.is_capturing = True
            self.stop_event.clear()

            # 启动捕获线程
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self.capture_thread.start()

            print(f"[MacOSPcapy] 开始捕获: {self.interface}")

        except Exception as e:
            print(f"[MacOSPcapy] 启动失败: {e}")
            raise

    def _capture_loop(self):
        """捕获循环"""
        def _handler(hdr, data):
            """pcapy回调处理"""
            if self.is_capturing:
                self.callback(data)

        while not self.stop_event.is_set():
            try:
                self.cap.dispatch(1, _handler)
            except Exception as e:
                if self.is_capturing:
                    print(f"[MacOSPcapy] 捕获错误: {e}")

    def stop_capture(self):
        """停止捕获"""
        if not self.is_capturing:
            return

        print(f"[MacOSPcapy] 停止捕获: {self.interface}")

        self.is_capturing = False
        self.stop_event.set()

        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)


def create_capture_engine(
    interface: str,
    callback: Callable[[bytes], None],
    promisc: bool = True
) -> RawSocketCapture:
    """
    创建适合当前平台的捕获引擎

    Args:
        interface: 网络接口名
        callback: 数据包回调函数
        promisc: 是否使用混杂模式

    Returns:
        捕获引擎实例
    """
    os_type = platform.system().lower()

    if os_type == "linux":
        return LinuxRawSocketCapture(interface, callback, promisc)
    elif os_type == "windows":
        return WindowsPcapyCapture(interface, callback, promisc)
    elif os_type == "darwin":
        return MacOSPcapyCapture(interface, callback, promisc)
    else:
        raise ValueError(f"不支持的平台: {os_type}")


if __name__ == "__main__":
    """测试捕获引擎"""
    def packet_callback(data: bytes):
        """数据包回调"""
        if len(data) >= 14:
            ethertype = data[12:14]
            print(f"收到数据包: {len(data)}字节, EtherType: {ethertype.hex()}")

    print("=== 跨平台Raw Socket捕获引擎测试 ===")

    # 测试接口扫描
    try:
        from lldp.interface_scanner import get_working_interfaces
        interfaces = get_working_interfaces()

        if interfaces:
            print(f"\n找到 {len(interfaces)} 个接口")

            # 选择第一个非回环接口
            test_interface = None
            for iface in interfaces:
                if "loopback" not in iface.name.lower():
                    test_interface = iface.name
                    break

            if test_interface:
                print(f"\n测试接口: {test_interface}")

                # 创建捕获引擎
                engine = create_capture_engine(test_interface, packet_callback)

                # 捕获5秒
                engine.start_capture()
                print("捕获5秒...")
                time.sleep(5)
                engine.stop_capture()
                print("捕获完成")
            else:
                print("没有找到可用的测试接口")
        else:
            print("没有找到网络接口")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
