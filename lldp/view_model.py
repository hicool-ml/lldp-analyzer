"""
LLDP Device View Model
Clean separation between raw device data and UI/export formatting
Enhanced with Network Intent Analysis
"""

from dataclasses import dataclass
from typing import Optional

from .utils import safe_get
from .port_profile import (
    PortIntentProfile,
    infer_port_intent,
    format_intent_profile,
    PortRole,
    NetworkIntent,
    DeviceType  # 新增导入
)


@dataclass
class DeviceView:
    """Clean view model for UI/export - no raw device objects"""
    # Protocol
    protocol: str
    protocol_style: str

    # 🔥 ENHANCED: Port Intent Profile (Network Intent Analysis)
    port_intent: PortIntentProfile
    port_role_badge: str
    port_role_summary: str

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


def format_vlan(device, intent_profile=None) -> str:
    """
    🔥 ENHANCED: Format VLAN information with network intent awareness

    修复: 安全处理intent_profile，避免向后兼容问题
    """
    # 🔥 NEW: 如果有intent_profile，使用网络意图推断结果
    if intent_profile and hasattr(intent_profile, 'role') and intent_profile.role:
        port_vlan = safe_get(device, 'port_vlan')
        protocol_vlan = safe_get(device, 'protocol_vlan_id')

        # 🔥 语义增强：根据端口角色调整VLAN显示
        if intent_profile.role in [PortRole.TRUNK_NATIVE, PortRole.TRUNK_NO_NATIVE]:
            # Trunk端口强调Tagged/Untagged语义
            if protocol_vlan:
                return f"Trunk (Native + {protocol_vlan} Tagged)"
            elif port_vlan:
                return f"Trunk ({port_vlan.vlan_id} Native)"
            else:
                return "Trunk (无VLAN信息)"

        elif intent_profile.role in [PortRole.ACCESS_TERMINAL, PortRole.ACCESS_WIRELESS, PortRole.ACCESS_VOICE]:
            # Access端口强调Untagged语义
            if port_vlan:
                tagged = safe_get(port_vlan, 'tagged')
                tagged_text = "Tagged" if tagged else "Untagged"
                return f"Access ({port_vlan.vlan_id} {tagged_text})"
            else:
                return "Access (未分配VLAN)"

        elif intent_profile.role in [PortRole.UPLINK_LAG, PortRole.UPLINK_SINGLE]:
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
    """
    Format MAC/PHY configuration

    修复: 安全处理Ruijie等厂商缺失macphy_config的情况
    """
    macphy = safe_get(device, 'macphy_config')
    if not macphy:
        return "未提供"

    # All supported speeds
    # 🔥 安全检查: supported_speeds可能是None或不存在
    if hasattr(macphy, 'supported_speeds') and macphy.supported_speeds:
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
    """
    Format device capabilities

    修复: 安全处理Ruijie等厂商缺失Capabilities TLV的情况
    """
    caps = safe_get(device, 'capabilities')
    if not caps:
        return "未知"

    # 🔥 安全检查: get_all_capabilities可能返回None或抛出异常
    try:
        all_caps = caps.get_all_capabilities()
        if all_caps and isinstance(all_caps, list):
            return " / ".join(all_caps)
        else:
            return "未知"
    except (AttributeError, TypeError):
        return "未知"


def to_view(device) -> DeviceView:
    """
    Convert raw LLDPDevice to clean DeviceView for UI/export

    🔥 ARCHITECTURE ENHANCEMENT: 彻底解耦协议判断逻辑
    所有的协议差异化（LLDP vs CDP）都在这里处理，UI层不再需要if/else
    """
    # 🔥 KEY: 协议类型判断（内部处理，UI层无感知）
    protocol = safe_get(device, 'protocol', 'LLDP')
    is_cdp = (protocol == 'CDP')

    # 🔥 KEY: Port Intent Analysis (Network Intent Analysis)
    port_intent = infer_port_intent(device)
    port_role_badge = _get_port_role_badge(port_intent)
    port_role_summary = _format_intent_summary(port_intent)

    # 🔥 修复：删除重复的CDP处理逻辑，使用后面统一的处理逻辑
    # 初始化默认值，后面会根据协议类型覆盖
    system_name = '未知设备'
    device_model = '未提供'
    serial_number = '未提供'
    mac = '未提供'
    id_type = '未知'
    ip = '未提供'
    software_version = '未提供'
    lldp_med = '未提供'
    port_id = '未提供'
    port_type = '未知'
    port_desc = '未知'

    # LLDP协议的初步处理（后面会被CDP逻辑覆盖如果是CDP）
    if not is_cdp:
        system_name = device.system_name or '未知设备'
        device_model = safe_get(device, 'device_model') or safe_get(device, 'product_model', '未提供')

        # 设备模型提取优化
        if device_model == '未提供' and device.system_description:
            desc_lines = device.system_description.split('\n')
            for line in desc_lines:
                if 'H3C' in line and 'Comware' not in line and len(line.strip()) > 10:
                    device_model = line.strip()
                    break

        serial_number = safe_get(device, 'serial_number', '未提供')

        # MAC地址处理
        if device.chassis_id:
            mac = device.chassis_id.value
            id_type = device.chassis_id.type.name
        else:
            mac = '未提供'
            id_type = '未知'

        ip = safe_get(device, 'management_ip', '未提供')
        software_version = safe_get(device, 'software_version', '未提供')
        lldp_med = '未提供'

        # 端口信息处理
        port_id_obj = safe_get(device, 'port_id')
        # 🔥 修复：确保 port_id 是字符串，而不是 LLDPPortID 对象
        if port_id_obj and hasattr(port_id_obj, 'value'):
            port_id = str(port_id_obj.value) if port_id_obj.value else '未提供'
        else:
            port_id = '未提供'
        port_type = safe_get(port_id_obj, 'type', '未知').name if port_id_obj else '未知'
        port_desc = safe_get(device, 'port_description', '未知')

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
        # 🔥 修复：确保 mac 是字符串，而不是 LLDPChassisID 对象
        if chassis_id and hasattr(chassis_id, 'value'):
            mac = str(chassis_id.value) if chassis_id.value else "未提供"
        else:
            mac = "未提供"
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
        # 🔥 修复：确保 CDP port_id 是字符串
        port_id_raw = safe_get(device, 'port_id')
        if port_id_raw:
            # CDP port_id 应该是字符串，但防止意外情况
            port_id = str(port_id_raw) if not isinstance(port_id_raw, str) else port_id_raw
        else:
            port_id = "未提供"
        port_type = "CDP端口标识"
        port_desc = "未提供"
    else:
        port_id_obj = safe_get(device, 'port_id')
        # 🔥 修复：确保 port_id 是字符串，而不是 LLDPPortID 对象
        if port_id_obj and hasattr(port_id_obj, 'value'):
            port_id = str(port_id_obj.value) if port_id_obj.value else '未提供'
        else:
            port_id = '未提供'
        port_type = safe_get(port_id_obj, 'type', '未知').name if port_id_obj else '未知'
        port_desc = safe_get(device, 'port_description') or "未知"

    # VLAN
    # 🔥 NEW: 让format_vlan依赖网络意图推断结果
    vlan = format_vlan(device, port_intent)
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
        # 🔥 Port Intent Profile (Network Intent Analysis)
        port_intent=port_intent,
        port_role_badge=port_role_badge,
        port_role_summary=port_role_summary,
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


def _get_port_role_badge(port_intent: PortIntentProfile) -> str:
    """Generate CSS style for port role badge based on intent"""
    color_map = {
        PortRole.ACCESS_TERMINAL: "color:#22c55e;font-weight:600;background:#dcfce7;padding:4px;border-radius:4px;",
        PortRole.ACCESS_WIRELESS: "color:#10b981;font-weight:600;background:#d1fae5;padding:4px;border-radius:4px;",
        PortRole.ACCESS_VOICE: "color:#fbbf24;font-weight:600;background:#fef3c7;padding:4px;border-radius:4px;",
        PortRole.TRUNK_NATIVE: "color:#3b82f6;font-weight:600;background:#dbeafe;padding:4px;border-radius:4px;",
        PortRole.TRUNK_NO_NATIVE: "color:#3b82f6;font-weight:600;background:#dbeafe;padding:4px;border-radius:4px;",
        PortRole.UPLINK_LAG: "color:#8b5cf6;font-weight:700;background:#ede9fe;padding:4px;border-radius:4px;",
        PortRole.UPLINK_SINGLE: "color:#a855f7;font-weight:600;background:#f3e8ff;padding:4px;border-radius:4px;",
        PortRole.CORE_DISTRIBUTION: "color:#7c3aed;font-weight:700;background:#ddd6fe;padding:4px;border-radius:4px;border:1px solid #7c3aed;",
        PortRole.STORAGE_NETWORK: "color:#0891b2;font-weight:600;background:#cffafe;padding:4px;border-radius:4px;",
        PortRole.INFRASTRUCTURE: "color:#64748b;font-weight:600;background:#f1f5f9;padding:4px;border-radius:4px;",
        PortRole.UNKNOWN: "color:#94a3b8;font-weight:600;background:#f1f5f9;padding:4px;border-radius:4px;",
    }
    return color_map.get(port_intent.role, color_map[PortRole.UNKNOWN])


def _format_intent_summary(port_intent: PortIntentProfile) -> str:
    """
    Generate human-readable intent summary

    🔥 修复: 安全处理新增的device_type字段，避免None错误
    """
    if port_intent.confidence >= 90:
        confidence_label = "高"
    elif port_intent.confidence >= 70:
        confidence_label = "中"
    else:
        confidence_label = "低"

    # 安全获取device_type，避免None错误
    device_type_text = ""
    if hasattr(port_intent, 'device_type') and port_intent.device_type:
        device_type_text = f" | {port_intent.device_type.value}"

    return f"{port_intent.role.value}{device_type_text} ({confidence_label}置信度 {port_intent.confidence}%)"
