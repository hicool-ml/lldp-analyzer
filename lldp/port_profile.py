"""
LLDP/CDP Port Semantic Inference Engine
Inferring network role from TLV combinations
"""

from dataclasses import dataclass
from typing import List
from enum import Enum

from .utils import safe_get


class PortRole(Enum):
    """Port role types"""
    ACCESS = "Access"                    # 普通接入口
    TERMINAL = "Terminal"                # 终端设备（AP/Phone/PC）
    TRUNK = "Trunk"                      # 干道口
    UPLINK = "Uplink"                    # 上联口
    UPLINK_LAG = "Uplink (LAG)"          # 聚合上联
    UNKNOWN = "Unknown"                  # 未知


@dataclass
class PortProfile:
    """
    Port Semantic Profile
    Infers the role and purpose of a network port from LLDP/CDP TLV combinations
    """
    role: PortRole                      # 推断的角色
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
        return f"{self.role.value} ({level}, {self.confidence}%) - {reasons_str}"


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
            confidence=min(90, 70 + score * 3),
            reasons=reasons,
            suggested_color="#a855f7"  # Light purple for Uplink
        )

    # ========== Default: Unknown ==========
    return PortProfile(
        role=PortRole.UNKNOWN,
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
        PortRole.UNKNOWN: "color:#94a3b8;font-weight:600;background:#f1f5f9;padding:4px;border-radius:4px;",
    }
    return color_map.get(profile.role, color_map[PortRole.UNKNOWN])


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
