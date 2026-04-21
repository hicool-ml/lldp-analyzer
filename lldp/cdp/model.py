"""
CDP Data Models
Structured data models for CDP protocol
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime


class CDPTLVType(Enum):
    """CDP TLV Types"""
    DEVICE_ID = 0x0001        # Device ID (hostname)
    ADDRESSES = 0x0002        # Network addresses
    PORT_ID = 0x0003          # Port ID
    CAPABILITIES = 0x0004     # Capabilities
    SOFTWARE_VERSION = 0x0005 # Software version
    PLATFORM = 0x0006         # Platform (hardware type)
    NATIVE_VLAN = 0x000A      # Native VLAN (关键！)
    DUPLEX = 0x000B           # Duplex setting
    VOICE_VLAN = 0x000E       # Voice VLAN
    POWER_AVAILABLE = 0x0010  # Power available (PoE)
    MTU = 0x0011              # MTU size
    TRUST = 0x0012            # Trust bitmap
    UNTRUSTED_COS = 0x0013    # Untrusted CoS
    SYSTEM_NAME = 0x0014      # System name
    SYSTEM_OID = 0x0015       # System OID
    MANAGEMENT_ADDRESSES = 0x0016  # Management addresses
    PHYSICAL_LOCATION = 0x0017   # Physical location


@dataclass
class CDPNetworkAddress:
    """Network address"""
    address_type: str  # IPv4, IPv6, etc.
    address: str
    subnet_mask: Optional[str] = None


@dataclass
class CDPCapabilities:
    """Device capabilities"""
    router: bool = False
    transparent_bridge: bool = False
    source_route_bridge: bool = False
    switch: bool = False
    host: bool = False
    igmp_filter: bool = False
    repeater: bool = False

    def get_all_capabilities(self) -> List[str]:
        """Get list of all capability names"""
        caps = []
        if self.router: caps.append("路由器")
        if self.switch: caps.append("交换机")
        if self.transparent_bridge: caps.append("透明桥接")
        if self.source_route_bridge: caps.append("源路由桥接")
        if self.host: caps.append("主机")
        if self.igmp_filter: caps.append("IGMP过滤")
        if self.repeater: caps.append("中继器")
        return caps


@dataclass
class CDPDevice:
    """
    Complete CDP Device Model
    Structured representation of a discovered CDP device
    """
    # Basic identification
    device_id: Optional[str] = None              # Device hostname
    port_id: Optional[str] = None                # Port ID
    system_name: Optional[str] = None            # System name
    platform: Optional[str] = None               # Platform/hardware type

    # Version and software
    software_version: Optional[str] = None       # Software version
    ios_version: Optional[str] = None            # IOS version (parsed)

    # Network configuration (关键信息)
    native_vlan: Optional[int] = None            # Native VLAN (CDP重点！)
    voice_vlan: Optional[int] = None             # Voice VLAN
    management_addresses: List[CDPNetworkAddress] = field(default_factory=list)

    # Capabilities and features
    capabilities: CDPCapabilities = field(default_factory=CDPCapabilities)

    # Physical layer
    duplex: Optional[str] = None                 # Full/Half
    mtu: Optional[int] = None                    # MTU size

    # PoE
    power_available: Optional[str] = None        # Power availability

    # Additional info
    addresses: List[CDPNetworkAddress] = field(default_factory=list)
    physical_location: Optional[str] = None

    # Metadata
    last_seen: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None                    # Time to Live
    capture_interface: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if device has minimum required information"""
        return self.device_id is not None or self.system_name is not None

    def get_display_name(self) -> str:
        """Get human-readable device name"""
        if self.system_name:
            return self.system_name
        if self.device_id:
            return self.device_id
        return "Unknown CDP Device"

    def has_native_vlan(self) -> bool:
        """Check if device has Native VLAN information"""
        return self.native_vlan is not None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "device_id": self.device_id,
            "port_id": self.port_id,
            "system_name": self.system_name,
            "platform": self.platform,
            "software_version": self.software_version,
            "native_vlan": self.native_vlan,
            "voice_vlan": self.voice_vlan,
            "duplex": self.duplex,
            "mtu": self.mtu,
            "capabilities": self.capabilities.get_all_capabilities(),
            "last_seen": self.last_seen.isoformat(),
        }

    def __repr__(self) -> str:
        vlan_info = f", VLAN={self.native_vlan}" if self.native_vlan else ""
        return f"CDPDevice(name={self.get_display_name()}{vlan_info})"