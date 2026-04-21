"""
LLDP Device View Model
Clean separation between raw device data and UI/export formatting
"""

from dataclasses import dataclass
from typing import Optional

from .utils import safe_get
from .port_profile import PortProfile, infer_port_profile, get_port_role_badge, format_port_profile_summary, infer_device_type


@dataclass
class DeviceView:
    """Clean view model for UI/export - no raw device objects"""
    # Protocol
    protocol: str
    protocol_style: str

    # 🔥 NEW: Port Semantic Profile (核心创新)
    port_profile: PortProfile
    port_role_badge: str
    port_role_summary: str
    device_type: str  # 🔥 NEW: 设备类型

    # Device Info
    system_name: str
    device_model: str
    serial_number: str
    mac: str
    id_type: str
    ip: str
    software_version: str
    lldp_med: str

    # Port Info
    port_id: str
    port_type: str
    port_desc: str

    # VLAN Info
    vlan: str
    vlan_style: str
    protocol_vlan: str
    protocol_vlan_style: str

    # Technical Info
    macphy: str
    link_agg: str
    mtu: str
    poe: str
    capabilities: str


# CSS Style Constants
GREEN_BADGE = "color:#22c55e; font-weight:600; background:#dcfce7; padding:4px; border-radius:4px;"
BLUE_BADGE = "color:#3b82f6; font-weight:600; background:#dbeafe; padding:4px; border-radius:4px;"
YELLOW_BADGE = "color:#f59e0b; font-weight:600; background:#fef3c7; padding:4px; border-radius:4px;"
PURPLE_BADGE = "color:#8b5cf6; font-weight:600; background:#f3e8ff; padding:4px; border-radius:4px;"
RED_BADGE = "color:#ef4444; font-weight:600; background:#fee2e2; padding:4px; border-radius:4px;"
EMERALD_BADGE = "color:#10b981; font-weight:700; background:#d1fae5; padding:4px; border-radius:4px;"


def format_vlan(device, profile=None) -> str:
    """🔥 ENHANCED: Format VLAN information with semantic awareness"""
    # 🔥 NEW: 如果有profile，使用语义推断结果
    if profile:
        port_vlan = safe_get(device, 'port_vlan')
        protocol_vlan = safe_get(device, 'protocol_vlan_id')

        # 🔥 语义增强：根据端口角色调整VLAN显示
        if profile.role == PortRole.TRUNK:
            # Trunk端口强调Tagged/Untagged语义
            if protocol_vlan:
                return f"Trunk (Native + {protocol_vlan} Tagged)"
            elif port_vlan:
                return f"Trunk ({port_vlan.vlan_id} Native)"
            else:
                return "Trunk (无VLAN信息)"

        elif profile.role == PortRole.ACCESS:
            # Access端口强调Untagged语义
            if port_vlan:
                tagged = safe_get(port_vlan, 'tagged')
                tagged_text = "Tagged" if tagged else "Untagged"
                return f"Access ({port_vlan.vlan_id} {tagged_text})"
            else:
                return "Access (未分配VLAN)"

        elif profile.role == PortRole.UPLINK or profile.role == PortRole.UPLINK_LAG:
            # Uplink强调路由VLAN
            if protocol_vlan:
                return f"Uplink (Native + {protocol_vlan} Tagged)"
            elif port_vlan:
                return f"Uplink ({port_vlan.vlan_id} Native)"
            else:
                return "Uplink (无VLAN信息)"

    # Original logic (fallback)
    # Check for CDP Native VLAN
    native_vlan = safe_get(device, 'native_vlan')
    if native_vlan:
        return f"{native_vlan} (Native VLAN)"

    # Check for H3C private TLV
    h3c_vlan = safe_get(device, 'h3c_native_vlan')
    if h3c_vlan:
        return f"{h3c_vlan} (H3C私有TLV)"

    # Standard LLDP port VLAN
    port_vlan = safe_get(device, 'port_vlan')
    if not port_vlan:
        return "未提供"

    vlan_text = str(port_vlan.vlan_id)

    # VLAN name
    vlan_name = safe_get(port_vlan, 'vlan_name')
    if not vlan_name:
        vlans = safe_get(device, 'vlans', [])
        for v in vlans:
            if safe_get(v, 'vlan_id') == port_vlan.vlan_id:
                vlan_name = safe_get(v, 'vlan_name')
                break

    if vlan_name:
        vlan_text += f" ({vlan_name})"

    # Tagged/Untagged
    tagged = safe_get(port_vlan, 'tagged')
    vlan_text += " (Tagged)" if tagged else " (Untagged)"

    return vlan_text


def get_vlan_style(device) -> str:
    """Get VLAN display style"""
    # CDP Native VLAN
    if safe_get(device, 'native_vlan'):
        return EMERALD_BADGE

    # H3C private TLV
    if safe_get(device, 'h3c_native_vlan'):
        return YELLOW_BADGE

    # Standard LLDP
    if safe_get(device, 'port_vlan'):
        return GREEN_BADGE

    return ""


def format_macphy(device) -> str:
    """Format MAC/PHY configuration"""
    macphy = safe_get(device, 'macphy_config')
    if not macphy:
        return "未提供"

    # All supported speeds
    if macphy.supported_speeds:
        return " / ".join(macphy.supported_speeds)

    # Current speed + duplex
    speed = safe_get(macphy, 'speed')
    if speed:
        phy_text = speed
        duplex = safe_get(macphy, 'duplex')
        if duplex:
            phy_text += f" {duplex}"
        return phy_text

    # Autonegotiation
    autoneg = safe_get(device, 'autonegotiation')
    if autoneg and safe_get(autoneg, 'supported'):
        return "自动协商"

    return "未提供"


def format_link_agg(device) -> str:
    """Format link aggregation info"""
    link_agg = safe_get(device, 'link_aggregation')
    if not link_agg:
        return "未提供"

    if not safe_get(link_agg, 'supported'):
        return "不支持"

    if safe_get(link_agg, 'enabled'):
        agg_text = "已启用"
        agg_id = safe_get(link_agg, 'aggregation_id')
        if agg_id:
            agg_text += f" (组ID: {agg_id})"
        return agg_text

    return "支持"


def format_poe(device) -> str:
    """Format PoE information"""
    poe = safe_get(device, 'poe')
    if not poe or not safe_get(poe, 'supported'):
        return "不支持"

    parts = []

    # Power source
    power_source = safe_get(poe, 'power_source')
    if power_source:
        if 'PSE' in power_source:
            parts.append("供电设备")
        elif 'PD' in power_source:
            parts.append("受电设备")

    # Power allocated
    power_allocated = safe_get(poe, 'power_allocated')
    if power_allocated:
        power_w = power_allocated / 1000
        if power_w >= 1:
            parts.append(f"{power_w:.1f}W")
        else:
            parts.append(f"{power_allocated}mW")

    # Priority
    priority = safe_get(poe, 'power_priority')
    if priority:
        parts.append(f"优先级:{priority}")

    # Class and Type
    power_class = safe_get(poe, 'power_class')
    if power_class:
        parts.append(f"({power_class})")

    power_type = safe_get(poe, 'power_type')
    if power_type:
        parts.append(f"[{power_type}]")

    return " / ".join(parts) if parts else "支持"


def format_capabilities(device) -> str:
    """Format device capabilities"""
    caps = safe_get(device, 'capabilities')
    if not caps:
        return "未知"

    all_caps = caps.get_all_capabilities()
    return " / ".join(all_caps) if all_caps else "未知"


def to_view(device) -> DeviceView:
    """Convert raw LLDPDevice to clean DeviceView for UI/export"""

    # 🔥 KEY: Port Semantic Inference (协议语义推断) - Enhanced
    port_profile = infer_port_profile(device)
    port_role_badge = get_port_role_badge(port_profile)
    port_role_summary = format_port_profile_summary(port_profile)

    # 🔥 NEW: Device type inference (设备类型推断)
    device_type = infer_device_type(device)

    # 🔥 ENHANCED: 让语义推断影响port_profile
    if port_profile.device_type == DeviceType.UNKNOWN:
        # 如果port_profile没有推断出设备类型，使用专门的device_type推断
        port_profile.device_type = device_type

    # Detect protocol
    """Convert raw LLDPDevice to clean DeviceView for UI/export"""
    # Detect protocol
    protocol = safe_get(device, 'protocol', 'LLDP')
    is_cdp = (protocol == 'CDP')

    # Protocol display
    if is_cdp:
        protocol_text = "CDP (Cisco Discovery Protocol)"
        protocol_style = EMERALD_BADGE
    else:
        protocol_text = "LLDP (IEEE 802.1AB)"
        protocol_style = BLUE_BADGE

    # Device Info
    if is_cdp:
        system_name = (
            safe_get(device, 'system_name') or
            safe_get(device, 'device_id') or
            "未知CDP设备"
        )
        device_model = safe_get(device, 'platform') or "未提供"
        serial_number = "未提供"
        mac = "N/A (CDP协议)"
        id_type = "CDP"
        software_version = safe_get(device, 'software_version') or "未提供"
        lldp_med = "N/A (CDP协议)"

        # Management IP
        mgmt_addrs = safe_get(device, 'management_addresses')
        if mgmt_addrs:
            ipv4 = next((addr.address for addr in mgmt_addrs if safe_get(addr, 'address_type') == "IPv4"), None)
            ip = ipv4 or "未提供"
        else:
            ip = "未提供"

    else:
        # LLDP
        chassis_id = safe_get(device, 'chassis_id')
        mac = safe_get(chassis_id, 'value') if chassis_id else "未提供"
        id_type = safe_get(chassis_id, 'type', '未知').name if chassis_id else "未知"
        system_name = safe_get(device, 'system_name') or "未知设备"

        # Device model
        device_model = (
            safe_get(device, 'device_model') or
            safe_get(device, 'product_model') or
            "未提供"
        )

        # Extract from system description
        if device_model == "未提供":
            sys_desc = safe_get(device, 'system_description')
            if sys_desc:
                for line in sys_desc.split('\n'):
                    if 'H3C' in line and 'Comware' not in line and len(line.strip()) > 10:
                        device_model = line.strip()
                        break

        serial_number = safe_get(device, 'serial_number') or "未提供"
        software_version = safe_get(device, 'software_version') or "未提供"
        ip = safe_get(device, 'management_ip') or "未提供"

        # LLDP-MED
        lldp_med_caps = safe_get(device, 'lldp_med_capabilities')
        if lldp_med_caps and safe_get(lldp_med_caps, 'capabilities'):
            lldp_med = " / ".join(lldp_med_caps['capabilities'])
        else:
            lldp_med = "未提供"

    # Port Info
    if is_cdp:
        port_id = safe_get(device, 'port_id') or "未提供"
        port_type = "CDP端口标识"
        port_desc = "未提供"
    else:
        port_id_obj = safe_get(device, 'port_id')
        port_id = safe_get(port_id_obj, 'value') if port_id_obj else "未提供"
        port_type = safe_get(port_id_obj, 'type', '未知').name if port_id_obj else "未知"
        port_desc = safe_get(device, 'port_description') or "未知"

    # VLAN
    # 🔥 NEW: 让format_vlan依赖语义推断结果
    vlan = format_vlan(device, port_profile)
    vlan_style = get_vlan_style(device)

    # Protocol VLAN
    protocol_vlan_id = safe_get(device, 'protocol_vlan_id')
    if protocol_vlan_id:
        protocol_vlan = str(protocol_vlan_id)
        protocol_vlan_style = PURPLE_BADGE
    else:
        protocol_vlan = "未提供"
        protocol_vlan_style = ""

    # Technical Info
    macphy = format_macphy(device)
    link_agg = format_link_agg(device)

    # MTU
    max_frame = safe_get(device, 'max_frame_size')
    mtu = f"{max_frame} 字节" if max_frame else "未提供"

    poe = format_poe(device)
    capabilities = format_capabilities(device)

    return DeviceView(
        protocol=protocol_text,
        protocol_style=protocol_style,
        # 🔥 Port Semantic Profile (协议语义推断)
        port_profile=port_profile,
        port_role_badge=port_role_badge,
        port_role_summary=port_role_summary,
        device_type=device_type.value,  # 🔥 NEW: 设备类型
        # Device Info
        system_name=system_name,
        device_model=device_model,
        serial_number=serial_number,
        mac=mac,
        id_type=id_type,
        ip=ip,
        software_version=software_version,
        lldp_med=lldp_med,
        port_id=port_id,
        port_type=port_type,
        port_desc=port_desc,
        vlan=vlan,
        vlan_style=vlan_style,
        protocol_vlan=protocol_vlan,
        protocol_vlan_style=protocol_vlan_style,
        macphy=macphy,
        link_agg=link_agg,
        mtu=mtu,
        poe=poe,
        capabilities=capabilities,
    )
