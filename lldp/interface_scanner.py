"""
无Scapy网卡扫描引擎
使用pcapy-ng + psutil替代scapy.get_working_ifaces
支持Windows和Linux平台
"""

import sys
import platform
from typing import List, Optional, NamedTuple
from dataclasses import dataclass

class NetworkInterface(NamedTuple):
    """网络接口信息（兼容scapy接口对象）"""
    name: str
    description: str
    mac: Optional[str] = None
    ips: List[str] = []

    def __repr__(self):
        return f"<Interface {self.name}: {self.description}>"


class InterfaceScanner:
    """无Scapy的网络接口扫描器"""

    def __init__(self):
        self.os_type = platform.system().lower()

    def get_interfaces(self) -> List[NetworkInterface]:
        """
        获取所有可用的网络接口

        Returns:
            网络接口列表
        """
        try:
            if self.os_type == "windows":
                return self._scan_windows()
            elif self.os_type == "linux":
                return self._scan_linux()
            elif self.os_type == "darwin":
                return self._scan_macos()
            else:
                print(f"[InterfaceScanner] 不支持的平台: {self.os_type}")
                return []
        except Exception as e:
            print(f"[InterfaceScanner] 扫描失败: {e}")
            return []

    def _scan_windows(self) -> List[NetworkInterface]:
        """Windows平台：使用pcapy-ng + psutil"""
        interfaces = []

        try:
            import pcapy
            import psutil
            import re

            # 1. 获取pcapy设备列表（底层设备名）
            pcap_devs = pcapy.findalldevs()

            # 2. 获取psutil接口信息（友好名称和IP）
            net_if_addrs = psutil.net_if_addrs()
            net_io_counters = psutil.net_io_counters(pernic=True)

            # 3. 匹配pcapy设备名和psutil友好名称
            for pcap_dev in pcap_devs:
                # Windows上pcapy返回的是 \Device\NPF_{GUID} 格式
                # 需要找到对应的友好名称

                # 提取GUID
                match = re.search(r'\{[A-F0-9-]+\}', pcap_dev, re.IGNORECASE)
                if not match:
                    continue

                guid = match.group(0).upper()

                # 在psutil中查找匹配的接口
                friendly_name = None
                ips = []
                mac = None

                for if_name, if_addrs in net_if_addrs.items():
                    # 检查GUID是否匹配（通过注册表或其他方式）
                    # 这里简化处理：使用接口名称映射
                    if self._guid_matches(if_name, guid):
                        friendly_name = if_name
                        # 获取IP地址
                        for addr in if_addrs:
                            if addr.family == 2:  # AF_INET
                                ips.append(addr.address)
                            elif addr.family == 17:  # AF_PACKET
                                mac = addr.address
                        break

                # 如果找不到友好名称，使用GUID
                if not friendly_name:
                    friendly_name = f"{{PCAP: {guid}}}"

                # 应用过滤逻辑
                if self._should_include_interface(pcap_dev, friendly_name):
                    interface = NetworkInterface(
                        name=pcap_dev,
                        description=friendly_name or pcap_dev,
                        mac=mac,
                        ips=ips
                    )
                    interfaces.append(interface)

        except ImportError as e:
            print(f"[InterfaceScanner] 缺少依赖: {e}")
            print("  请安装: pip install pcapy-ng psutil")
        except Exception as e:
            print(f"[InterfaceScanner] Windows扫描失败: {e}")

        return interfaces

    def _scan_linux(self) -> List[NetworkInterface]:
        """Linux平台：使用psutil + socket"""
        interfaces = []

        try:
            import psutil
            import socket
            import fcntl
            import struct

            # 获取所有网络接口
            net_if_addrs = psutil.net_if_addrs()
            net_io_counters = psutil.net_io_counters(pernic=True)

            for if_name, if_addrs in net_if_addrs.items():
                # 应用过滤逻辑
                if not self._should_include_interface(if_name, if_name):
                    continue

                # 获取IP和MAC
                ips = []
                mac = None

                for addr in if_addrs:
                    if addr.family == 2:  # AF_INET
                        ips.append(addr.address)
                    elif addr.family == 17:  # AF_PACKET
                        mac = addr.address

                # 获取接口描述
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', if_name.encode()[:15]))
                    s.close()
                except:
                    info = if_name

                interface = NetworkInterface(
                    name=if_name,
                    description=if_name,
                    mac=mac,
                    ips=ips
                )
                interfaces.append(interface)

        except ImportError as e:
            print(f"[InterfaceScanner] 缺少依赖: {e}")
            print("  请安装: pip install psutil")
        except Exception as e:
            print(f"[InterfaceScanner] Linux扫描失败: {e}")

        return interfaces

    def _scan_macos(self) -> List[NetworkInterface]:
        """macOS平台：使用psutil"""
        interfaces = []

        try:
            import psutil

            net_if_addrs = psutil.net_if_addrs()

            for if_name, if_addrs in net_if_addrs.items():
                # 应用过滤逻辑
                if not self._should_include_interface(if_name, if_name):
                    continue

                # 获取IP和MAC
                ips = []
                mac = None

                for addr in if_addrs:
                    if addr.family == 2:  # AF_INET
                        ips.append(addr.address)
                    elif addr.family == 18:  # AF_LINK (macOS)
                        mac = addr.address

                # macOS特殊处理：识别接口类型
                desc = if_name
                if if_name == "en0":
                    desc = "en0 (Wi-Fi)"
                elif if_name in ["en1", "en2", "en3", "en4", "en5"]:
                    desc = f"{if_name} (Ethernet)"

                interface = NetworkInterface(
                    name=if_name,
                    description=desc,
                    mac=mac,
                    ips=ips
                )
                interfaces.append(interface)

        except ImportError as e:
            print(f"[InterfaceScanner] 缺少依赖: {e}")
            print("  请安装: pip install psutil")
        except Exception as e:
            print(f"[InterfaceScanner] macOS扫描失败: {e}")

        return interfaces

    def _guid_matches(self, if_name: str, guid: str) -> bool:
        """
        检查接口名是否匹配GUID

        这是一个简化版本，实际应该查询注册表
        HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002BE10318}\{guid}\Connection
        """
        # 简化处理：如果if_name包含数字或特定特征，认为匹配
        # 实际应该通过注册表查询
        return True  # 临时返回True，实际需要实现GUID匹配

    def _should_include_interface(self, dev_name: str, friendly_name: str) -> bool:
        """
        判断是否应该包含此接口（过滤逻辑）

        Args:
            dev_name: 设备名
            friendly_name: 友好名称

        Returns:
            True表示包含，False表示过滤
        """
        dev_lower = dev_name.lower()
        friendly_lower = friendly_name.lower()

        # 过滤掉虚拟接口
        virtual_keywords = [
            "virtual", "vmware", "virtualbox", "vbox",
            "tunnel", "hyper-v", "docker", "bridge",
            "loopback", "pseudo", "veth", "virbr"
        ]

        for keyword in virtual_keywords:
            if keyword in dev_lower or keyword in friendly_lower:
                return False

        # 过滤掉Loopback
        if "loopback" in dev_lower or "loopback" in friendly_lower:
            return False

        # 包含物理接口
        physical_keywords = [
            "ethernet", "eth", "en", "intel", "realtek",
            "broadcom", "cisco", "usb", "thunderbolt",
            "ax88179", "rtl8153", "ue300"
        ]

        # 如果包含物理接口关键字，优先包含
        for keyword in physical_keywords:
            if keyword in dev_lower or keyword in friendly_lower:
                return True

        # 默认包含（除了明确过滤的）
        return True


def get_working_interfaces() -> List[NetworkInterface]:
    """
    获取所有可用的网络接口（替代scapy.all.get_working_ifaces）

    Returns:
        网络接口列表
    """
    scanner = InterfaceScanner()
    return scanner.get_interfaces()


if __name__ == "__main__":
    """测试网卡扫描"""
    print("=== 无Scapy网卡扫描测试 ===")

    interfaces = get_working_interfaces()

    print(f"\n找到 {len(interfaces)} 个网络接口:\n")

    for i, iface in enumerate(interfaces, 1):
        print(f"{i}. {iface.name}")
        print(f"   描述: {iface.description}")
        if iface.mac:
            print(f"   MAC: {iface.mac}")
        if iface.ips:
            print(f"   IP: {', '.join(iface.ips)}")
        print()
