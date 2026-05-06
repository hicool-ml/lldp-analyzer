"""
Cross-platform compatibility layer for LLDP Analyzer

Handles platform-specific differences between Windows, macOS, and Linux.
"""

import sys
import platform
import subprocess
import logging
from typing import List, Tuple, Optional
from enum import Enum

log = logging.getLogger("lldp.platform")


class OSType(Enum):
    """Operating system types"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class PlatformConfig:
    """Platform-specific configuration"""

    def __init__(self):
        self.os_type = self._detect_os()
        self.is_admin = self._check_admin_privileges()
        self.interface_hints = self._get_interface_hints()

    def _detect_os(self) -> OSType:
        """Detect operating system"""
        system = platform.system().lower()
        if system == "windows":
            return OSType.WINDOWS
        elif system == "darwin":
            return OSType.MACOS
        elif system == "linux":
            return OSType.LINUX
        else:
            return OSType.UNKNOWN

    def _check_admin_privileges(self) -> bool:
        """Check if running with admin/root privileges"""
        try:
            if self.os_type == OSType.WINDOWS:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                # Unix-like systems (macOS/Linux)
                return __import__('os').getuid() == 0
        except Exception as e:
            log.warning(f"Could not check admin privileges: {e}")
            return False

    def _get_interface_hints(self) -> dict:
        """Get platform-specific interface naming hints"""
        if self.os_type == OSType.WINDOWS:
            return {
                "physical_keywords": ["Ethernet", "Local Area Connection", "Intel", "Realtek"],
                "virtual_keywords": ["VMware", "VirtualBox", "Tunnel", "Hyper-V"],
                "wireless_keywords": ["Wi-Fi", "Wireless", "802.11"],
                "loopback_keywords": ["Loopback", "Loopback Pseudo-Interface"]
            }
        elif self.os_type == OSType.MACOS:
            return {
                # macOS便携系统通常需要USB/Thunderbolt扩展
                "physical_keywords": ["en", "eth", "usb", "thunderbolt", "ax"],  # en0, en1, en2... ax88179 (USB Ethernet)
                "virtual_keywords": ["bridge", "vbox", "vmnet", "tun", "tap"],
                "wireless_keywords": ["wi-fi"],
                "loopback_keywords": ["lo", "loopback"],
                # USB/Thunderbolt适配器优先级最高（便携macOS常见）
                "preferred_physical": ["en1", "en2", "en3", "en4", "en5"],  # 通常en0是Wi-Fi，en1+是USB/Thunderbolt以太网
                "usb_adapter_keywords": ["usb", "ax88179", "rtl8153", "cisco", "starlink"],  # 常见USB网卡型号
                "thunderbolt_keywords": ["thunderbolt", "tb"]
            }
        elif self.os_type == OSType.LINUX:
            return {
                "physical_keywords": ["eth", "enp", "ens"],
                "virtual_keywords": ["virbr", "vnet", "docker", "br-"],
                "wireless_keywords": ["wlan", "wl"],
                "loopback_keywords": ["lo"]
            }
        else:
            return {}

    def get_capture_command_prefix(self) -> List[str]:
        """Get command prefix for packet capture (sudo, etc.)"""
        if self.os_type == OSType.MACOS or self.os_type == OSType.LINUX:
            if not self.is_admin:
                return ["sudo"]
        return []

    def get_permission_instructions(self) -> str:
        """Get platform-specific permission instructions"""
        if self.os_type == OSType.WINDOWS:
            return (
                "Windows网络捕获要求:\n"
                "1. 安装Npcap驱动: https://npcap.com/\n"
                "2. 安装时勾选 'Support raw 802.11 traffic'\n"
                "3. 以管理员身份运行此应用"
            )
        elif self.os_type == OSType.MACOS:
            return (
                "macOS网络捕获要求:\n"
                "1. 🔌 硬件要求：macOS便携系统需要USB或Thunderbolt以太网适配器\n"
                "   - 推荐USB 3.0转千兆以太网适配器\n"
                "   - 或Thunderbolt扩展坞\n"
                "   - Wi-Fi接口(en0)通常无法捕获LLDP报文\n"
                "2. 首次运行需要授予网络捕获权限\n"
                "   - 系统会提示授予网络访问权限\n"
                "   - 在 '系统设置 > 隐私与安全性 > 本地网络' 中确认\n"
                "3. 如需管理员权限，请使用终端运行：\n"
                "   sudo \"LLDP Analyzer v2.app/Contents/MacOS/LLDP Analyzer v2\"\n"
                "4. 选择正确的网络接口：\n"
                "   - 优先选择en1, en2等（通常是有线适配器）\n"
                "   - 避免选择en0（通常是Wi-Fi）"
            )
        elif self.os_type == OSType.LINUX:
            return (
                "Linux网络捕获要求:\n"
                "1. 需要root权限或CAP_NET_RAW能力\n"
                "2. 运行: sudo ./lldp_analyzer\n"
                "3. 或设置能力: sudo setcap cap_net_raw+ep $(which python3)"
            )
        else:
            return "未知平台，可能需要特殊权限"

    def get_preferred_interface(self, interfaces: List) -> Optional[str]:
        """
        Get preferred network interface for capture

        Args:
            interfaces: List of scapy interface objects

        Returns:
            Preferred interface name or None

        macOS特殊处理:
        - en0 通常是Wi-Fi (不建议用于LLDP捕获)
        - en1, en2, en3+ 通常是USB/Thunderbolt以太网适配器 (优先推荐)
        - 扫描描述信息中的"USB"或"Thunderbolt"关键字
        """
        if not interfaces:
            return None

        hints = self.interface_hints

        # macOS特殊处理：优先选择USB/Thunderbolt适配器
        if self.os_type == OSType.MACOS:
            # 第一优先级：USB/Thunderbolt适配器
            for iface in interfaces:
                name = iface.name.lower()
                desc = iface.description.lower()

                # 检查是否为USB/Thunderbolt适配器
                usb_keywords = hints.get("usb_adapter_keywords", [])
                thunderbolt_keywords = hints.get("thunderbolt_keywords", [])

                if any(kw in name or kw in desc for kw in usb_keywords + thunderbolt_keywords):
                    log.info("检测到USB/Thunderbolt适配器: %s (%s)", iface.description, iface.name)
                    return iface.name

            # 第二优先级：en1+ (通常是有线以太网)
            preferred_physical = hints.get("preferred_physical", [])
            for iface in interfaces:
                if iface.name in preferred_physical:
                    log.info("选择推荐接口: %s (%s)", iface.description, iface.name)
                    return iface.name

            # 避免en0 (通常是Wi-Fi)
            for iface in interfaces:
                name = iface.name.lower()
                desc = iface.description.lower()
                if name != "en0" and "wi-fi" not in desc:
                    return iface.name

        # 通用处理：其他平台或macOS的fallback逻辑
        # Try to find physical interfaces
        for iface in interfaces:
            name = iface.name.lower()

            # Skip loopback
            if any(kw in name for kw in hints.get("loopback_keywords", [])):
                continue

            # Skip virtual interfaces
            if any(kw in name for kw in hints.get("virtual_keywords", [])):
                continue

            # Look for physical interface keywords
            for kw in hints.get("physical_keywords", []):
                if kw in name:
                    return iface.name

        # Fallback: first non-loopback interface
        for iface in interfaces:
            name = iface.name.lower()
            if not any(kw in name for kw in hints.get("loopback_keywords", [])):
                return iface.name

        # Last resort: first interface
        return interfaces[0].name if interfaces else None

    def check_scapy_support(self) -> Tuple[bool, str]:
        """
        Check if Scapy packet capture is supported

        Returns:
            (is_supported, message)
        """
        try:
            from scapy.all import get_working_ifaces

            interfaces = list(get_working_ifaces())
            if not interfaces:
                return False, "未找到可用的网络接口"

            return True, f"找到 {len(interfaces)} 个网络接口"

        except ImportError:
            return False, "Scapy未安装，请运行: pip install scapy"
        except PermissionError:
            return False, f"权限不足\n{self.get_permission_instructions()}"
        except Exception as e:
            return False, f"错误: {str(e)}"

    def get_system_info(self) -> dict:
        """Get system information for debugging"""
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "os_type": self.os_type.value,
            "is_admin": self.is_admin,
        }

        # Add macOS-specific info
        if self.os_type == OSType.MACOS:
            try:
                import subprocess
                result = subprocess.run(['sw_vers'], capture_output=True, text=True)
                info["macos_version"] = result.stdout.strip()
            except Exception:
                pass

        return info


# Global platform config instance
_platform_config = None


def get_platform_config() -> PlatformConfig:
    """Get global platform configuration instance"""
    global _platform_config
    if _platform_config is None:
        _platform_config = PlatformConfig()
    return _platform_config


def is_macos() -> bool:
    """Check if running on macOS"""
    return get_platform_config().os_type == OSType.MACOS


def is_windows() -> bool:
    """Check if running on Windows"""
    return get_platform_config().os_type == OSType.WINDOWS


def is_linux() -> bool:
    """Check if running on Linux"""
    return get_platform_config().os_type == OSType.LINUX


def is_admin() -> bool:
    """Check if running with admin privileges"""
    return get_platform_config().is_admin
