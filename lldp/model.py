"""
LLDP Data Models
Structured data models for LLDP protocol
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime


class ChassisIDType(Enum):
    """Chassis ID subtypes"""

    NETWORK_ADDRESS = 1
    INTERFACE_NAME = 2
    CHASSIS_COMPONENT = 3
    MAC_ADDRESS = 4
    INTERFACE_ALIAS = 5
    PORT_COMPONENT = 6
    LOCALLY_ASSIGNED = 7


class PortIDType(Enum):
    """Port ID subtypes"""

    INTERFACE_ALIAS = 1
    PORT_COMPONENT = 2
    MAC_ADDRESS = 3
    NETWORK_ADDRESS = 4
    INTERFACE_NAME = 5
    AGENT_CIRCUIT_ID = 6
    LOCALLY_ASSIGNED = 7


@dataclass
class LLDPChassisID:
    """Chassis ID model"""

    value: str
    type: ChassisIDType

    def __str__(self) -> str:
        type_names = {
            ChassisIDType.MAC_ADDRESS: "设备MAC地址",
            ChassisIDType.LOCALLY_ASSIGNED: "设备名称",
            ChassisIDType.INTERFACE_NAME: "接口名称",
            ChassisIDType.NETWORK_ADDRESS: "网络地址",
        }
        name = type_names.get(self.type, "设备标识")
        return f"{name}: {self.value}"

    def is_mac_address(self) -> bool:
        """Check if this is a MAC address"""
        return self.type == ChassisIDType.MAC_ADDRESS


@dataclass
class LLDPPortID:
    """Port ID model"""

    value: str
    type: PortIDType

    def __str__(self) -> str:
        type_names = {
            PortIDType.MAC_ADDRESS: "端口MAC地址",
            PortIDType.LOCALLY_ASSIGNED: "端口名称",
            PortIDType.INTERFACE_NAME: "接口名称",
            PortIDType.INTERFACE_ALIAS: "接口别名",
        }
        name = type_names.get(self.type, "端口标识")
        return f"{name}: {self.value}"

    def is_mac_address(self) -> bool:
        """Check if this is a MAC address"""
        return self.type == PortIDType.MAC_ADDRESS


@dataclass
class VLANInfo:
    """VLAN configuration"""

    vlan_id: int
    vlan_name: Optional[str] = None
    tagged: bool = False
    is_pvid: bool = False


@dataclass
class PoEInfo:
    """Power over Ethernet information"""

    supported: bool = False
    enabled: bool = False
    power_type: Optional[str] = None  # Type 1 / Type 2
    power_class: Optional[str] = None  # Class 0-4
    power_source: Optional[str] = None  # Primary / Backup / PSE / PD
    power_priority: Optional[str] = None  # Low / Medium / High / Critical (LLDP-MED)
    pair_control: Optional[str] = None  # Signal / Spare
    power_requested: Optional[int] = None  # milliwatts
    power_allocated: Optional[int] = None  # milliwatts


@dataclass
class LinkAggregationInfo:
    """Link Aggregation information (IEEE 802.3)"""

    supported: bool = False
    enabled: bool = False
    aggregation_id: Optional[int] = None  # Aggregation group ID
    aggregation_port_count: Optional[int] = None  # Number of ports in group


@dataclass
class MACPHYConfig:
    """MAC/PHY Configuration and Status (IEEE 802.3)"""

    autoneg_support: bool = False
    autoneg_enabled: bool = False
    operational_mau_type: Optional[int] = None  # Operational MAU type
    speed: Optional[str] = None  # Current speed: "10M", "100M", "1G", "10G", etc.
    duplex: Optional[str] = None  # Current duplex: "Half", "Full"
    supported_speeds: List[str] = field(default_factory=list)  # All supported speeds
    power_capability: Optional[str] = None  # Power class capability


@dataclass
class Dot1XInfo:
    """802.1X authentication information"""

    enabled: bool = False
    auth_mode: Optional[str] = None
    auth_status: Optional[str] = None


@dataclass
class DeviceCapabilities:
    """System capabilities"""

    bridge: bool = False
    repeater: bool = False
    router: bool = False
    wlan: bool = False
    station: bool = False
    telephone: bool = False
    docsis: bool = False
    c_vlan: bool = False
    c_bridge: bool = False
    s_vlan: bool = False
    twamp: bool = False

    # Enabled capabilities (当前启用的能力)
    bridge_enabled: bool = False
    repeater_enabled: bool = False
    router_enabled: bool = False
    wlan_enabled: bool = False
    station_enabled: bool = False
    telephone_enabled: bool = False
    docsis_enabled: bool = False
    c_vlan_enabled: bool = False
    c_bridge_enabled: bool = False
    s_vlan_enabled: bool = False
    twamp_enabled: bool = False

    def get_all_capabilities(self) -> List[str]:
        """Get list of all capability names (supported capabilities)"""
        caps = []
        if self.bridge:
            caps.append("交换机")
        if self.repeater:
            caps.append("中继器")
        if self.router:
            caps.append("路由器")
        if self.telephone:
            caps.append("IP电话")
        if self.docsis:
            caps.append("线缆调制")
        if self.station:
            caps.append("终端站")
        if self.wlan:
            caps.append("无线接入点")
        if self.c_vlan:
            caps.append("客户VLAN")
        if self.c_bridge:
            caps.append("客户桥接")
        if self.s_vlan:
            caps.append("服务VLAN")
        if self.twamp:
            caps.append("双向测量")
        return caps

    def get_enabled_capabilities(self) -> List[str]:
        """Get list of enabled capability names (当前启用的能力)"""
        caps = []
        if self.bridge_enabled:
            caps.append("交换机")
        if self.repeater_enabled:
            caps.append("中继器")
        if self.router_enabled:
            caps.append("路由器")
        if self.telephone_enabled:
            caps.append("IP电话")
        if self.docsis_enabled:
            caps.append("线缆调制")
        if self.station_enabled:
            caps.append("终端站")
        if self.c_vlan_enabled:
            caps.append("客户VLAN")
        if self.c_bridge_enabled:
            caps.append("客户桥接")
        if self.s_vlan_enabled:
            caps.append("服务VLAN")
        if self.twamp_enabled:
            caps.append("双向测量")
        return caps


@dataclass
class LLDPDevice:
    """
    Complete LLDP Device Model
    Structured representation of a discovered LLDP device
    """

    # Basic identification
    chassis_id: Optional[LLDPChassisID] = None
    port_id: Optional[LLDPPortID] = None
    port_description: Optional[str] = None
    system_name: Optional[str] = None
    system_description: Optional[str] = None

    # Network configuration
    management_ip: Optional[str] = None
    port_vlan: Optional[VLANInfo] = None
    vlans: List[VLANInfo] = field(default_factory=list)

    # Power and authentication
    poe: PoEInfo = field(default_factory=PoEInfo)
    dot1x: Dot1XInfo = field(default_factory=Dot1XInfo)

    # Capabilities
    capabilities: DeviceCapabilities = field(default_factory=DeviceCapabilities)

    # Additional info
    ttl: Optional[int] = None
    max_frame_size: Optional[int] = None
    autonegotiation: Optional[Dict] = None
    link_aggregation: LinkAggregationInfo = field(default_factory=LinkAggregationInfo)
    macphy_config: MACPHYConfig = field(default_factory=MACPHYConfig)

    # Metadata
    last_seen: datetime = field(default_factory=datetime.now)
    capture_interface: Optional[str] = None
    protocol: Optional[str] = None  # 🔥 添加协议标识（LLDP/CDP）

    def is_valid(self) -> bool:
        """Check if device has minimum required information"""
        return self.chassis_id is not None or self.system_name is not None

    def get_display_name(self) -> str:
        """Get human-readable device name"""
        if self.system_name:
            return self.system_name
        if self.chassis_id:
            return str(self.chassis_id.value)
        return "Unknown Device"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "chassis_id": {
                "value": self.chassis_id.value if self.chassis_id else None,
                "type": self.chassis_id.type.name if self.chassis_id else None,
            },
            "port_id": {
                "value": self.port_id.value if self.port_id else None,
                "type": self.port_id.type.name if self.port_id else None,
            },
            "port_description": self.port_description,
            "system_name": self.system_name,
            "system_description": self.system_description,
            "management_ip": self.management_ip,
            "port_vlan": (
                {
                    "vlan_id": self.port_vlan.vlan_id if self.port_vlan else None,
                    "vlan_name": self.port_vlan.vlan_name if self.port_vlan else None,
                    "tagged": self.port_vlan.tagged if self.port_vlan else None,
                }
                if self.port_vlan
                else None
            ),
            "poe": {
                "supported": self.poe.supported,
                "enabled": self.poe.enabled,
                "power_type": self.poe.power_type,
                "power_class": self.poe.power_class,
            },
            "dot1x": {
                "enabled": self.dot1x.enabled,
                "auth_mode": self.dot1x.auth_mode,
                "auth_status": self.dot1x.auth_status,
            },
            "capabilities": self.capabilities.get_enabled_capabilities(),
            "last_seen": self.last_seen.isoformat(),
        }

    def __repr__(self) -> str:
        return f"LLDPDevice(name={self.get_display_name()}, ip={self.management_ip})"
