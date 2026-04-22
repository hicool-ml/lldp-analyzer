"""
LLDP/CDP Port Semantic Inference Engine
Inferring network role from TLV combinations
"""

from dataclasses import dataclass
from typing import List
from enum import Enum

from .utils import safe_get


class PortRole(Enum):
    """Port role types - Enhanced with professional network inference"""
    ACCESS = "Access"                    # 普通接入口
    TERMINAL = "Terminal"                # 终端设备（AP/Phone/PC）
    TRUNK = "Trunk"                      # 干道口
    UPLINK = "Uplink"                    # 上联口
    UPLINK_LAG = "Uplink (LAG)"          # 聚合上联
    CORE_INFRA = "Core Infrastructure"    # 核心基础设施
    WIRELESS_AP = "Wireless AP"          # 无线接入点
    VOIP_PHONE = "VoIP Phone"            # IP电话
    HYPERVISOR = "Hypervisor"            # 虚拟化主机
    ANOMALY = "Anomaly Detected"         # 异常检测
    UNKNOWN = "Unknown"                  # 未知


class DeviceType(Enum):
    """Device type inference - Critical for semantic engine"""
    SWITCH = "Switch"                    # 交换机
    ROUTER = "Router"                    # 路由器
    WIRELESS_AP = "Wireless AP"          # 无线接入点
    VOIP_PHONE = "VoIP Phone"            # IP电话
    HYPERVERVISOR = "Hypervisor"         # 虚拟化主机
    SERVER = "Server"                    # 服务器
    TERMINAL = "Terminal"                # 终端（PC/打印机等）
    UNKNOWN = "Unknown"                  # 未知


@dataclass
class PortProfile:
    """
    Port Semantic Profile - True semantic inference engine
    Infers the role and purpose of a network port from LLDP/CDP TLV combinations
    """
    role: PortRole                      # 推断的端口角色
    device_type: DeviceType              # 推断的设备类型
    confidence: int                     # 置信度 (0-100)
    reasons: List[str]                  # 推断依据
    suggested_color: str                # 建议的显示颜色

    def __str__(self) -> str:
        """Human-readable description"""
        if self.confidence >= 90:
            level = "高置信度"
        elif self.confidence >= 70:
            level = "中置信度"
        else:
            level = "低置信度"

        reasons_str = " / ".join(self.reasons)
        # Show both port role and device type
        return f"{self.role.value} / {self.device_type.value} ({level}, {self.confidence}%) - {reasons_str}"


def infer_port_profile(device) -> PortProfile:
    """
    Infer port profile from LLDP/CDP device data

    This is the core semantic inference engine that analyzes TLV combinations
    to determine the port's role in the network topology.

    Args:
        device: LLDPDevice or CDP device object

    Returns:
        PortProfile with role, confidence, and reasoning
    """
    reasons = []
    score = 0
    role = PortRole.UNKNOWN

    # Extract key attributes
    port_vlan = safe_get(device, 'port_vlan')
    protocol_vlan = safe_get(device, 'protocol_vlan_id')
    link_agg = safe_get(device, 'link_aggregation')
    poe = safe_get(device, 'poe')
    macphy = safe_get(device, 'macphy_config')
    capabilities = safe_get(device, 'capabilities')

    # ========== Rule 1: Trunk Port Detection ==========
    # Key indicators:
    # - Has Port VLAN (Native VLAN)
    # - Has Protocol VLAN (Tagged VLANs for services)
    # - High speed (1G+)
    # - No PoE (typically)
    if port_vlan and protocol_vlan:
        reasons.append("同时存在Port VLAN与Protocol VLAN（干道特征）")
        score += 4

        # Confirm with speed
        if macphy and macphy.speed:
            speed = macphy.speed
            if '1G' in speed or '10G' in speed or '25G' in speed:
                reasons.append(f"高速率({speed})符合干道特征")
                score += 2
            elif '100M' in speed:
                reasons.append(f"速率{speed}，可能是小型网络干道")
                score += 1

        # Confirm no PoE (trunks typically don't power devices)
        if poe and not poe.supported:
            reasons.append("无PoE（符合干道特征）")
            score += 1

        if score >= 5:
            role = PortRole.TRUNK
            return PortProfile(
                role=role,
                device_type=DeviceType.UNKNOWN,
                confidence=min(95, 70 + score * 5),
                reasons=reasons,
                suggested_color="#3b82f6"  # Blue for Trunk
            )

    # ========== Rule 2: Uplink with LAG Detection ==========
    # Key indicators:
    # - Link aggregation enabled
    # - High speed
    # - Router capability
    if link_agg and safe_get(link_agg, 'enabled'):
        reasons.append("启用链路聚合（LAG）")

        # Confirm with router capability
        if capabilities and safe_get(capabilities, 'router'):
            reasons.append("具备路由能力（上联特征）")
            score += 3
        else:
            score += 2

        # Confirm with speed
        if macphy and macphy.speed:
            speed = macphy.speed
            if '10G' in speed or '25G' in speed or '40G' in speed:
                reasons.append(f"高速率({speed})")
                score += 2

        if score >= 4:
            role = PortRole.UPLINK_LAG
            return PortProfile(
                role=role,
                device_type=DeviceType.UNKNOWN,
                confidence=min(98, 80 + score * 3),
                reasons=reasons,
                suggested_color="#8b5cf6"  # Purple for Uplink LAG
            )

    # ========== Rule 3: Terminal Port Detection ==========
    # Key indicators:
    # - PoE supported (powers AP/Phone/IP Camera)
    # - 100M or 1G speed
    # - Single VLAN (no Protocol VLAN)
    # - Switch capability on the other end
    score = 0
    reasons = []

    if poe and safe_get(poe, 'supported'):
        reasons.append("支持PoE供电（终端特征）")
        score += 3

        # Check power type
        power_source = safe_get(poe, 'power_source')
        if power_source and 'PSE' in power_source:
            reasons.append("供电设备(PSE) - 为终端供电")
            score += 1

    if macphy and macphy.speed:
        speed = macphy.speed
        if '100M' in speed:
            reasons.append("百兆速率（典型终端速率）")
            score += 2
        elif '1G' in speed:
            reasons.append("千兆速率（现代终端速率）")
            score += 1

    # Confirm: No Protocol VLAN (terminals typically don't need it)
    if port_vlan and not protocol_vlan:
        reasons.append("单一VLAN（终端通常不需要Protocol VLAN）")
        score += 1

    # Check device capabilities on the other end
    if capabilities:
        if safe_get(capabilities, 'bridge') or safe_get(capabilities, 'station'):
            reasons.append("对端为桥接/终端设备")
            score += 1

    if score >= 4:
        role = PortRole.TERMINAL
        return PortProfile(
            role=role,
            device_type=DeviceType.UNKNOWN,
            confidence=min(90, 70 + score * 3),
            reasons=reasons,
            suggested_color="#f59e0b"  # Orange for Terminal
        )

    # ========== Rule 4: Access Port Detection ==========
    # Key indicators:
    # - Single Port VLAN
    # - No Protocol VLAN
    # - No PoE or PoE not supported
    # - Switch capability
    score = 0
    reasons = []

    if port_vlan and not protocol_vlan:
        reasons.append("单一Port VLAN（接入特征）")
        score += 2

    if not protocol_vlan:
        reasons.append("无Protocol VLAN（非干道）")
        score += 1

    # Check if no PoE (regular access port)
    if poe and not safe_get(poe, 'supported'):
        reasons.append("无PoE（普通接入）")
        score += 1

    # Check speed
    if macphy and macphy.speed:
        speed = macphy.speed
        if '1G' in speed:
            reasons.append("千兆接入")
            score += 1

    if score >= 3:
        role = PortRole.ACCESS
        return PortProfile(
            role=role,
            device_type=DeviceType.UNKNOWN,
            confidence=min(85, 65 + score * 3),
            reasons=reasons,
            suggested_color="#22c55e"  # Green for Access
        )

    # ========== Rule 5: Uplink Port Detection ==========
    # Key indicators:
    # - High speed
    # - Router capability
    # - May have VLANs
    score = 0
    reasons = []

    if capabilities and safe_get(capabilities, 'router'):
        reasons.append("具备路由能力（上联特征）")
        score += 3

    if macphy and macphy.speed:
        speed = macphy.speed
        if '10G' in speed or '25G' in speed or '40G' in speed:
            reasons.append(f"高速率({speed})符合上联特征")
            score += 2
        elif '1G' in speed:
            reasons.append("千兆速率（可能是小型网络上联）")
            score += 1

    if port_vlan or protocol_vlan:
        reasons.append("携带VLAN信息")
        score += 1

    if score >= 4:
        role = PortRole.UPLINK
        return PortProfile(
            role=role,
            device_type=DeviceType.UNKNOWN,
            confidence=min(90, 70 + score * 3),
            reasons=reasons,
            suggested_color="#a855f7"  # Light purple for Uplink
        )

    # ========== Rule 6: Core Infrastructure Detection ==========
    # Key indicators:
    # - Bridge + Router capabilities
    # - Trunk/Port-channel in description
    # - High speed (10G+)
    score = 0
    reasons = []

    if capabilities:
        if safe_get(capabilities, 'bridge') and safe_get(capabilities, 'router'):
            reasons.append("具备桥接+路由能力（核心设备特征）")
            score += 4

    # Check system description for infrastructure keywords
    system_desc = safe_get(device, 'system_description', '').lower()
    port_desc = safe_get(device, 'port_description', '').lower()

    infra_keywords = ['trunk', 'port-channel', 'eth-channel', 'bundle', 'ten', 'forty', 'hundred']
    if any(kw in system_desc or kw in port_desc for kw in infra_keywords):
        reasons.append("端口描述包含基础设施关键词")
        score += 3

    if macphy and macphy.speed:
        speed = macphy.speed
        if '10G' in speed or '25G' in speed or '40G' in speed or '100G' in speed:
            reasons.append(f"高速率({speed})符合核心设备特征")
            score += 2

    if score >= 6:
        role = PortRole.CORE_INFRA
        return PortProfile(
            role=role,
            device_type=DeviceType.UNKNOWN,
            confidence=min(98, 80 + score * 2),
            reasons=reasons,
            suggested_color="#7c3aed"  # Deep purple for Core Infrastructure
        )

    # ==========  Rule 7: VoIP Phone Detection ==========
    # Key indicators:
    # - Bridge capability only (phones have small switches)
    # - PoE powered
    # - System name/description contains phone keywords
    score = 0
    reasons = []

    if capabilities and safe_get(capabilities, 'bridge') and not safe_get(capabilities, 'router'):
        reasons.append("仅桥接能力（电话特征）")
        score += 2

    if poe and safe_get(poe, 'supported'):
        power_type = safe_get(poe, 'power_type', '').lower()
        if 'pd' in power_type:  # Power Device
            reasons.append("PoE受电设备（IP电话通常为PD）")
            score += 3

    # Check device name for phone keywords
    system_name = safe_get(device, 'system_name', '').lower()
    phone_keywords = ['phone', '7960', '7970', '7841', '8851', 'avaya', 'cisco ip phone']
    if any(kw in system_name for kw in phone_keywords):
        reasons.append("系统名称包含IP电话关键词")
        score += 4

    # Check LLDP-MED for network connectivity device class
    lldp_med_caps = safe_get(device, 'lldp_med_capabilities')
    if lldp_med_caps:
        device_class = safe_get(lldp_med_caps, 'device_class', '')
        if 'network connectivity' in str(device_class).lower():
            reasons.append("LLDP-MED标识为网络连接设备")
            score += 2

    if score >= 5:
        role = PortRole.VOIP_PHONE
        return PortProfile(
            role=role,
            device_type=DeviceType.UNKNOWN,
            confidence=min(95, 75 + score * 2),
            reasons=reasons,
            suggested_color="#fbbf24"  # Yellow for VoIP phones
        )

    # ==========  Rule 8: Wireless AP Detection ==========
    # Key indicators:
    # - WLAN Access Point capability
    # - System name contains AP keywords
    score = 0
    reasons = []

    if capabilities:
        if 'wlan access point' in str(safe_get(capabilities, 'get_all_capabilities', [])).lower():
            reasons.append("具备WLAN接入点能力")
            score += 4

    # Check for AP keywords in system name
    ap_keywords = ['ap', 'aruba', 'ubiquiti', 'ruckus', 'aeroscout', 'meraki']
    if any(kw in system_name for kw in ap_keywords):
        reasons.append("系统名称包含无线AP关键词")
        score += 3

    if poe and safe_get(poe, 'supported'):
        reasons.append("支持PoE供电（AP常见配置）")
        score += 1

    if score >= 4:
        role = PortRole.WIRELESS_AP
        return PortProfile(
            role=role,
            device_type=DeviceType.UNKNOWN,
            confidence=min(92, 75 + score * 2),
            reasons=reasons,
            suggested_color="#10b981"  # Green for Wireless AP
        )

    # ==========  Rule 9: Hypervisor Detection ==========
    # Key indicators:
    # - Chassis ID MAC belongs to VMware/Microsoft/Xen
    # - System name contains ESXi/vswitch keywords
    score = 0
    reasons = []

    # Check chassis ID MAC OUI for virtualization vendors
    chassis_id = safe_get(device, 'chassis_id')
    if chassis_id:
        mac_value = str(safe_get(chassis_id, 'value', ''))

        # VMware OUI: 00:05:69, 00:0c:29, 00:50:56
        if any(oui in mac_value for oui in ['00:05:69', '00:0c:29', '00:50:56']):
            reasons.append("MAC地址属于VMware虚拟化平台")
            score += 4

        # Microsoft OUI: 00:15:5d
        elif '00:15:5d' in mac_value:
            reasons.append("MAC地址属于Microsoft Hyper-V")
            score += 4

    # Check system name for hypervisor keywords
    hypervisor_keywords = ['esxi', 'vswitch', 'hyperv', 'xen', 'kvm']
    if any(kw in system_name for kw in hypervisor_keywords):
        reasons.append("系统名称包含虚拟化平台关键词")
        score += 3

    if score >= 4:
        role = PortRole.HYPERVISOR
        return PortProfile(
            role=role,
            device_type=DeviceType.UNKNOWN,
            confidence=min(90, 75 + score * 2),
            reasons=reasons,
            suggested_color="#0891b2"  # Cyan for Hypervisor
        )

    # ==========  Rule 10: Anomaly Detection ==========
    # Detect potential network issues
    score = 0
    reasons = []

    # Check for half-duplex (anomaly)
    if macphy:
        duplex = safe_get(macphy, 'duplex', '').lower()
        if 'half' in duplex:
            reasons.append("检测到半双工模式（性能瓶颈）")
            score += 5

    # Check for missing management address (unmanaged device)
    mgmt_ip = safe_get(device, 'management_ip')
    if not mgmt or mgmt == '未提供':
        reasons.append("缺少管理地址（非受管设备）")
        score += 2

    if score >= 3:
        role = PortRole.ANOMALY
        return PortProfile(
            role=role,
            device_type=DeviceType.UNKNOWN,
            confidence=min(85, 70 + score * 2),
            reasons=reasons,
            suggested_color="#ef4444"  # Red for anomalies
        )

    # ========== Default: Unknown ==========
    return PortProfile(
        role=PortRole.UNKNOWN,
        device_type=DeviceType.UNKNOWN,
        confidence=50,
        reasons=["特征不明显，无法确定端口角色"],
        suggested_color="#94a3b8"  # Gray for Unknown
    )


def get_port_role_badge(profile: PortProfile) -> str:
    """Generate CSS style for port role badge"""
    color_map = {
        PortRole.ACCESS: "color:#22c55e;font-weight:600;background:#dcfce7;padding:4px;border-radius:4px;",
        PortRole.TERMINAL: "color:#f59e0b;font-weight:600;background:#fef3c7;padding:4px;border-radius:4px;",
        PortRole.TRUNK: "color:#3b82f6;font-weight:600;background:#dbeafe;padding:4px;border-radius:4px;",
        PortRole.UPLINK: "color:#a855f7;font-weight:600;background:#f3e8ff;padding:4px;border-radius:4px;",
        PortRole.UPLINK_LAG: "color:#8b5cf6;font-weight:700;background:#ede9fe;padding:4px;border-radius:4px;",
        # : Enhanced role styles
        PortRole.CORE_INFRA: "color:#7c3aed;font-weight:700;background:#ddd6fe;padding:4px;border-radius:4px;border:1px solid #7c3aed;",
        PortRole.WIRELESS_AP: "color:#10b981;font-weight:600;background:#d1fae5;padding:4px;border-radius:4px;",
        PortRole.VOIP_PHONE: "color:#fbbf24;font-weight:600;background:#fef3c7;padding:4px;border-radius:4px;",
        PortRole.HYPERVISOR: "color:#0891b2;font-weight:600;background:#cffafe;padding:4px;border-radius:4px;",
        PortRole.ANOMALY: "color:#ef4444;font-weight:700;background:#fee2e2;padding:4px;border-radius:4px;border:1px solid #ef4444;",
        PortRole.UNKNOWN: "color:#94a3b8;font-weight:600;background:#f1f5f9;padding:4px;border-radius:4px;",
    }
    return color_map.get(profile.role, color_map[PortRole.UNKNOWN])


def infer_device_type(device) -> DeviceType:
    """
    : Device type inference from TLV combinations

    This is the critical missing piece for true semantic inference.
    Analyzes Capabilities, PoE, MAC/PHY to determine device type.

    Args:
        device: LLDPDevice or CDP device object

    Returns:
        DeviceType with confidence
    """
    capabilities = safe_get(device, 'capabilities')
    poe = safe_get(device, 'poe')
    macphy = safe_get(device, 'macphy_config')
    system_name = safe_get(device, 'system_name', '').lower()

    score = 0
    reasons = []
    device_type = DeviceType.UNKNOWN

    # CRITICAL: Capabilities组合判断
    if capabilities:
        all_caps = capabilities.get_all_capabilities()

        # Bridge + Router = L3设备
        if safe_get(capabilities, 'router') and safe_get(capabilities, 'bridge'):
            reasons.append("具备路由+桥接能力（三层设备）")
            score += 8
            device_type = DeviceType.ROUTER

        # Bridge only = L2设备
        elif safe_get(capabilities, 'bridge'):
            device_type = DeviceType.SWITCH
            reasons.append("具备桥接能力（交换机特征）")
            score += 4

        # WLAN Access Point
        if 'wlan access point' in [cap.lower() for cap in all_caps]:
            device_type = DeviceType.WIRELESS_AP
            reasons.append("具备WLAN接入点能力")
            score += 6

    # PoE + MAC/PHY组合判断
    if poe and safe_get(poe, 'supported'):
        power_source = safe_get(poe, 'power_source', '')
        power_type = safe_get(poe, 'power_type', '')

        # PD = 受电设备，判断具体类型
        if 'PD' in power_source:
            # IP电话判断
            if 'phone' in str(power_type).lower() or '7960' in str(power_type).lower():
                device_type = DeviceType.VOIP_PHONE
                reasons.append("PoE受电 + 电话类型特征")
                score += 6
            # AP判断
            elif device_type != DeviceType.WIRELESS_AP:
                # 如果没有WLAN能力，可能是AP
                if not capabilities or 'wlan' not in str(capabilities.get_all_capabilities()).lower():
                    device_type = DeviceType.WIRELESS_AP
                    reasons.append("PoE受电 + 无WLAN能力（可能是AP）")
                    score += 4
                else:
                    device_type = DeviceType.TERMINAL
                    reasons.append("PoE受电终端设备")
                    score += 3

    # System Name模式匹配
    if 'esxi' in system_name or 'hyperv' in system_name:
        device_type = DeviceType.HYPERVISOR
        reasons.append("系统名称包含虚拟化平台关键词")
        score += 5
    elif 'ap' in system_name or 'aruba' in system_name or 'ubiquiti' in system_name:
        if device_type == DeviceType.UNKNOWN:
            device_type = DeviceType.WIRELESS_AP
            reasons.append("系统名称包含无线AP关键词")
            score += 4

    # MAC/PHY速度判断
    if macphy and macphy.speed:
        speed = macphy.speed
        if '10G' in speed or '25G' in speed:
            if device_type in [DeviceType.SWITCH, DeviceType.UNKNOWN]:
                device_type = DeviceType.ROUTER
                reasons.append(f"高速率({speed}) - 核心设备特征")
                score += 4

    # 最终确定设备类型
    if score >= 4:
        return device_type
    else:
        return DeviceType.UNKNOWN


def format_port_profile_summary(profile: PortProfile) -> str:
    """Generate human-readable profile summary"""
    role_name = profile.role.value

    if profile.confidence >= 90:
        confidence_label = "高"
    elif profile.confidence >= 70:
        confidence_label = "中"
    else:
        confidence_label = "低"

    return f"{role_name} ({confidence_label}置信度 {profile.confidence}%)"
