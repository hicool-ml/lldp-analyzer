"""
LLDP Port Semantic Inference Engine - Professional NMS Implementation
专业网络管理系统实现 - 基于特征抽象和规则引擎

🔥 质变升级：
从简单if-else判断 → Feature抽象 + 规则引擎 + 二次推断

架构层次：
TLV → Feature Extraction → Rule Engine (Priority-based) → Secondary Inference → PortRole/DeviceType

核心改进：
1. Feature抽象层：TLV语义特征提取
2. 规则优先级：强规则直接返回，弱规则参与推断
3. 二次推断：特征相互影响，reasons作为语义集合
4. 设备类型：DeviceType参与PortRole推断
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Set
from enum import Enum

from .utils import safe_get


class PortRole(Enum):
    """Port roles based on network intent"""
    ACCESS_TERMINAL = "Access Terminal"        # 终端接入（PC/打印机）
    ACCESS_WIRELESS = "Access Wireless"        # 无线接入（AP）
    ACCESS_VOICE = "Access Voice"              # 语音接入（IP电话）
    TRUNK_NATIVE = "Trunk (Native)"            # 干道口（带Native VLAN）
    TRUNK_NO_NATIVE = "Trunk (No Native)"      # 纯干道（无Native VLAN）
    UPLINK_LAG = "Uplink (LAG)"                # 聚合上联
    UPLINK_SINGLE = "Uplink (Single)"          # 单链路上联
    CORE_DISTRIBUTION = "Core/Distribution"    # 核心/分发层
    STORAGE_NETWORK = "Storage Network"        # 存储网络
    INFRASTRUCTURE = "Infrastructure"          # 基础设施
    UNKNOWN = "Unknown"


class DeviceType(Enum):
    """Device types based on capabilities and TLV"""
    ACCESS_POINT = "Access Point"              # 无线接入点
    IP_PHONE = "IP Phone"                      # IP电话
    SWITCH = "Switch"                          # 交换机
    ROUTER = "Router"                          # 路由器
    FIREWALL = "Firewall"                      # 防火墙
    SERVER = "Server"                          # 服务器
    STORAGE = "Storage"                        # 存储设备
    TERMINAL = "Terminal"                      # 终端设备（PC/打印机等）
    UNKNOWN = "Unknown"


class NetworkIntent(Enum):
    """Network intent inferred from TLV combination"""
    TERMINAL_ACCESS = "Terminal Access"        # 终端接入意图
    WIRELESS_ACCESS = "Wireless Access"        # 无线覆盖意图
    VOICE_PROVISIONING = "Voice Provisioning"  # 语音部署意图
    TRUNK_TRANSPORT = "Trunk Transport"        # 多VLAN传输意图
    UPLINK_REDUNDANCY = "Uplink Redundancy"    # 上联冗余意图
    HIGH_SPEED_STORAGE = "High-Speed Storage"  # 高速存储意图
    NETWORK_MANAGEMENT = "Network Management"  # 网络管理意图


@dataclass
class PortFeatures:
    """
    Feature抽象层：TLV语义特征提取

    🔥 关键创新：将TLV原始数据转换为语义特征集合
    这些特征是规则引擎的输入，也是二次推断的基础
    """
    # VLAN特征
    has_port_vlan: bool = False           # 有Port VLAN ID
    has_protocol_vlan: bool = False       # 有Protocol VLAN ID
    port_vlan_tagged: bool = False        # Port VLAN是Tagged

    # 链路聚合特征
    is_aggregated: bool = False           # 启用链路聚合
    aggregation_id: Optional[int] = None  # 聚合组ID

    # MTU特征
    high_mtu: bool = False               # MTU > 2000 (存储网络特征)
    jumbo_frame: bool = False            # MTU > 9000 (巨帧)

    # PoE特征
    has_poe: bool = False                # 支持PoE供电
    poe_power_allocated: Optional[int] = None  # 分配功率(mW)

    # 设备能力特征
    is_router: bool = False              # 具备路由能力
    is_bridge: bool = False              # 具备桥接能力
    is_wlan: bool = False                # 无线能力
    is_repeater: bool = False            # 中继器能力

    # 速率特征
    speed_1g_plus: bool = False          # 速率 >= 1G
    speed_10g_plus: bool = False         # 速率 >= 10G
    duplex_full: bool = False            # 全双工

    # 管理特征
    has_management_ip: bool = False      # 有管理地址
    has_system_description: bool = False # 有系统描述

    # VLAN名称特征（业务识别）
    has_mgmt_vlan: bool = False          # 管理网络VLAN
    has_data_vlan: bool = False          # 数据网络VLAN
    has_voice_vlan: bool = False         # 语音网络VLAN
    has_storage_vlan: bool = False       # 存储网络VLAN


@dataclass
class PortIntentProfile:
    """
    Port Intent Profile - 基于网络管理意图的端口分析

    🔥 质变升级：reasons现在是语义特征集合，参与二次推断
    """
    role: PortRole                      # 端口角色
    device_type: DeviceType              # 设备类型（新增）
    intent: NetworkIntent               # 网络意图
    confidence: int                     # 置信度 (0-100)
    features: PortFeatures              # 特征抽象层（新增）
    tlv_evidence: List[str]             # TLV证据（哪些TLV支持这个推断）
    operational_insight: str            # 运维洞察（这对NMS有什么价值）
    configuration_suggestion: str       # 配置建议（网络应该怎么配置）
    is_managed: bool                    # 是否受管设备（有Management Address）
    auto_discovery_issues: List[str]    # 自动发现的问题（性能瓶颈、配置错误等）
    semantic_reasons: Set[str]          # 🔥 新增：语义原因集合，参与二次推断


def extract_features(device) -> PortFeatures:
    """
    🔥 Feature抽象层：TLV语义特征提取

    这一步将原始TLV数据转换为结构化的语义特征
    是整个推断引擎的基础

    修复: 统一处理TLV缺失，建立厂商差异容错机制
    """
    features = PortFeatures()

    # ========== 设备能力特征提取（优先处理，厂商差异最大）==========
    # 🔥 关键修复: Ruijie等厂商可能不发送Capabilities TLV
    caps_obj = safe_get(device, 'capabilities')

    # 🔥 统一容错: 确保caps永远是list，绝不会是None
    if caps_obj and hasattr(caps_obj, 'get_all_capabilities'):
        try:
            all_caps = caps_obj.get_all_capabilities()
            capabilities_list = all_caps if all_caps else []
        except:
            capabilities_list = []
    else:
        capabilities_list = []

    # 🔥 安全的特征提取: 基于list而不是对象
    features.is_router = "Router" in capabilities_list
    features.is_bridge = "Bridge" in capabilities_list
    features.is_wlan = "WLAN" in capabilities_list or "Wlan" in capabilities_list
    features.is_repeater = "Repeater" in capabilities_list

    # ========== VLAN特征提取 ==========
    port_vlan = safe_get(device, 'port_vlan')
    protocol_vlan = safe_get(device, 'protocol_vlan_id')

    features.has_port_vlan = port_vlan is not None
    features.has_protocol_vlan = protocol_vlan is not None

    if port_vlan:
        features.port_vlan_tagged = safe_get(port_vlan, 'tagged', False)

    # ========== 链路聚合特征提取 ==========
    link_agg = safe_get(device, 'link_aggregation')
    if link_agg and safe_get(link_agg, 'enabled'):
        features.is_aggregated = True
        features.aggregation_id = safe_get(link_agg, 'aggregation_id')

    # ========== MTU特征提取 ==========
    max_frame = safe_get(device, 'max_frame_size')
    if max_frame:
        features.high_mtu = max_frame > 2000
        features.jumbo_frame = max_frame > 9000

    # ========== PoE特征提取 ==========
    poe = safe_get(device, 'poe')
    if poe and safe_get(poe, 'supported'):
        features.has_poe = True
        features.poe_power_allocated = safe_get(poe, 'power_allocated')

    # ========== 速率特征提取（修复macphy缺失）==========
    # 🔥 关键修复: Ruijie等厂商可能不发送macphy_config
    macphy = safe_get(device, 'macphy_config')

    # 🔥 安全的速率提取: 处理macphy为None的情况
    if macphy:
        speed = safe_get(macphy, 'speed', '')
        if speed:  # 确保speed不是None
            if '10G' in speed or '25G' in speed or '40G' in speed:
                features.speed_10g_plus = True
                features.speed_1g_plus = True
            elif '1000' in speed or '1G' in speed:
                features.speed_1g_plus = True

        duplex = safe_get(macphy, 'duplex', '')
        if duplex:  # 确保duplex不是None
            features.duplex_full = 'Full' in duplex

    # ========== 管理特征提取 ==========
    management_ip = safe_get(device, 'management_ip')
    features.has_management_ip = management_ip and management_ip != "未提供"

    system_desc = safe_get(device, 'system_description')
    features.has_system_description = bool(system_desc)

    # ========== VLAN名称特征提取（业务网络识别）==========
    vlan_names = safe_get(device, 'vlans', [])
    for vlan_info in vlan_names:
        if hasattr(vlan_info, 'vlan_name') and vlan_info.vlan_name:
            name_upper = vlan_info.vlan_name.upper()
            if any(kw in name_upper for kw in ['MGMT', 'ADMIN', 'MGT']):
                features.has_mgmt_vlan = True
            elif any(kw in name_upper for kw in ['DATA', 'USER', 'OFFICE']):
                features.has_data_vlan = True
            elif any(kw in name_upper for kw in ['VOICE', 'PHONE']):
                features.has_voice_vlan = True
            elif any(kw in name_upper for kw in ['STOR', 'SAN', 'NAS']):
                features.has_storage_vlan = True

    return features


def infer_device_type(features: PortFeatures, device) -> DeviceType:
    """
    🔥 新增：DeviceType推断

    设备类型会反向影响PortRole推断
    """
    # 1. 绝对规则（直接返回）

    # PoE + 无线能力 = AP
    if features.has_poe and features.is_wlan:
        return DeviceType.ACCESS_POINT

    # PoE + 无无线能力 = IP电话
    if features.has_poe and not features.is_wlan:
        return DeviceType.IP_PHONE

    # 路由能力 = Router
    if features.is_router:
        return DeviceType.ROUTER

    # 桥接能力 + 聚合 = Switch
    if features.is_bridge and features.is_aggregated:
        return DeviceType.SWITCH

    # 高MTU + 10G+速率 = Storage
    if features.jumbo_frame and features.speed_10g_plus:
        return DeviceType.STORAGE

    # 2. 推断规则

    # 桥接能力 = Switch
    if features.is_bridge:
        return DeviceType.SWITCH

    # 管理IP + 系统描述 = 服务器类设备
    if features.has_management_ip and features.has_system_description:
        return DeviceType.SERVER

    # 默认 = Terminal
    return DeviceType.TERMINAL


def run_priority_rules(features: PortFeatures, device_type: DeviceType) -> Optional[PortRole]:
    """
    🔥 规则引擎：优先级规则（绝对规则）

    这些规则一旦匹配，直接返回，不参与后续推断
    """

    # ========== 优先级1：绝对规则（直接返回）==========

    # 规则1：链路聚合 = UPLINK_LAG（无条件）
    if features.is_aggregated:
        return PortRole.UPLINK_LAG

    # 规则2：Protocol VLAN存在 = TRUNK（无条件）
    if features.has_protocol_vlan:
        if features.has_port_vlan:
            return PortRole.TRUNK_NATIVE
        else:
            return PortRole.TRUNK_NO_NATIVE

    # 规则3：高MTU (>2000) + 1G+速率 = UPLINK或Storage
    if features.high_mtu and features.speed_1g_plus:
        if features.jumbo_frame:
            return PortRole.STORAGE_NETWORK
        else:
            return PortRole.UPLINK_SINGLE

    # 规则4：路由能力 = UPLINK
    if features.is_router:
        return PortRole.UPLINK_SINGLE

    # 规则5：设备类型修正规则
    if device_type == DeviceType.ACCESS_POINT:
        return PortRole.ACCESS_WIRELESS

    if device_type == DeviceType.IP_PHONE:
        return PortRole.ACCESS_VOICE

    # 🔥 修复: 安全检查device_type，避免None值错误
    if device_type and device_type in [DeviceType.ROUTER, DeviceType.SWITCH]:
        return PortRole.CORE_DISTRIBUTION

    # 没有绝对规则匹配，返回None继续后续推断
    return None


def run_secondary_inference(features: PortFeatures, device_type: DeviceType, semantic_reasons: Set[str]) -> PortRole:
    """
    🔥 二次推断：特征相互影响

    这里semantic_reasons不只是展示文本，而是参与推断的语义特征集合
    """

    # 基础推断
    if features.has_port_vlan and not features.has_protocol_vlan:
        # 有Port VLAN但无Protocol VLAN = Access口
        if device_type == DeviceType.TERMINAL:
            return PortRole.ACCESS_TERMINAL
        else:
            return PortRole.ACCESS_TERMINAL

    # 🔥 二次推断：特征组合推断

    # 特征组合1：PoE + 低速率 = 终端接入
    if features.has_poe and not features.speed_1g_plus:
        semantic_reasons.add("PoE_LowSpeed_Terminal")
        return PortRole.ACCESS_TERMINAL

    # 特征组合2：高速率 + 桥接 = 核心设备
    if features.speed_10g_plus and features.is_bridge:
        semantic_reasons.add("HighSpeed_Bridge_Core")
        return PortRole.CORE_DISTRIBUTION

    # 特征组合3：多VLAN名称 + 桥接 = 核心交换机
    if features.is_bridge:
        vlan_count = sum([
            features.has_mgmt_vlan,
            features.has_data_vlan,
            features.has_voice_vlan,
            features.has_storage_vlan
        ])
        if vlan_count >= 2:
            semantic_reasons.add("MultiVLAN_CoreSwitch")
            return PortRole.CORE_DISTRIBUTION

    # 特征组合4：管理IP + 高速率 = 基础设施
    if features.has_management_ip and features.speed_1g_plus:
        semantic_reasons.add("MgmtIP_HighSpeed_Infra")
        return PortRole.INFRASTRUCTURE

    # 默认推断
    if features.has_management_ip:
        return PortRole.ACCESS_TERMINAL
    else:
        return PortRole.UNKNOWN


def infer_port_intent(device) -> PortIntentProfile:
    """
    🔥 质变升级：专业NMS推断引擎

    架构：TLV → Feature → Priority Rules → Secondary Inference → PortRole/DeviceType
    """

    # ========== 第1层：Feature抽象 ==========
    features = extract_features(device)

    # ========== 第2层：DeviceType推断 ==========
    device_type = infer_device_type(features, device)

    # ========== 第3层：优先级规则引擎 ==========
    priority_result = run_priority_rules(features, device_type)

    # ========== 第4层：二次推断 ==========
    semantic_reasons = set()

    if priority_result:
        # 绝对规则匹配，直接使用
        final_role = priority_result
        confidence = 98  # 高置信度
    else:
        # 无绝对规则，进行二次推断
        final_role = run_secondary_inference(features, device_type, semantic_reasons)

        # 根据特征数量计算置信度
        evidence_count = sum([
            features.has_port_vlan,
            features.has_protocol_vlan,
            features.is_aggregated,
            features.high_mtu,
            features.has_poe,
            features.speed_1g_plus
        ])
        confidence = min(95, 60 + evidence_count * 5)

    # ========== 生成语义原因集合 ==========
    if features.is_aggregated:
        semantic_reasons.add("Aggregation_Uplink")
    if features.has_protocol_vlan:
        semantic_reasons.add("ProtocolVLAN_Trunk")
    if features.high_mtu:
        semantic_reasons.add("HighMTU_Storage")
    if features.speed_10g_plus:
        semantic_reasons.add("HighSpeed_Core")
    if features.has_poe:
        semantic_reasons.add("PoE_Terminal")

    # ========== 生成运维洞察和建议 ==========
    insight, suggestion = generate_insight_and_suggestion(final_role, device_type, features, semantic_reasons)

    # ========== 生成TLV证据 ==========
    evidence = generate_tlv_evidence(features, device_type)

    # ========== 自动发现的问题 ==========
    issues = discover_issues(features)

    return PortIntentProfile(
        role=final_role,
        device_type=device_type,
        intent=map_role_to_intent(final_role),
        confidence=confidence,
        features=features,
        tlv_evidence=evidence,
        operational_insight=insight,
        configuration_suggestion=suggestion,
        is_managed=features.has_management_ip,
        auto_discovery_issues=issues,
        semantic_reasons=semantic_reasons
    )


def map_role_to_intent(role: PortRole) -> NetworkIntent:
    """PortRole到NetworkIntent的映射"""
    intent_map = {
        PortRole.ACCESS_TERMINAL: NetworkIntent.TERMINAL_ACCESS,
        PortRole.ACCESS_WIRELESS: NetworkIntent.WIRELESS_ACCESS,
        PortRole.ACCESS_VOICE: NetworkIntent.VOICE_PROVISIONING,
        PortRole.TRUNK_NATIVE: NetworkIntent.TRUNK_TRANSPORT,
        PortRole.TRUNK_NO_NATIVE: NetworkIntent.TRUNK_TRANSPORT,
        PortRole.UPLINK_LAG: NetworkIntent.UPLINK_REDUNDANCY,
        PortRole.UPLINK_SINGLE: NetworkIntent.UPLINK_REDUNDANCY,
        PortRole.STORAGE_NETWORK: NetworkIntent.HIGH_SPEED_STORAGE,
        PortRole.CORE_DISTRIBUTION: NetworkIntent.NETWORK_MANAGEMENT,
        PortRole.INFRASTRUCTURE: NetworkIntent.NETWORK_MANAGEMENT,
        PortRole.UNKNOWN: NetworkIntent.TERMINAL_ACCESS,
    }
    return intent_map.get(role, NetworkIntent.TERMINAL_ACCESS)


def generate_insight_and_suggestion(role: PortRole, device_type: DeviceType, features: PortFeatures, semantic_reasons: Set[str]):
    """生成运维洞察和配置建议"""

    # 基于角色和设备类型的组合生成洞察
    if role == PortRole.UPLINK_LAG:
        insight = f"上联链路聚合，提供冗余和带宽扩展"
        if features.aggregation_id:
            insight += f"（聚合组ID: {features.aggregation_id}）"
        suggestion = "验证LACP配置，确保负载均衡正确，监控链路状态"

    elif role == PortRole.TRUNK_NATIVE:
        insight = f"Trunk端口，承载多个VLAN流量，对端设备: {device_type.value}"
        suggestion = "检查Native VLAN配置，确保VLAN路由正确，监控VLAN tagged流量"

    elif role == PortRole.ACCESS_WIRELESS:
        insight = "无线AP接入端口，支持PoE供电"
        suggestion = f"配置为Access VLAN，启用PoE+，检查AP管理VLAN，优化无线漫游"

    elif role == PortRole.ACCESS_VOICE:
        insight = "IP电话接入端口，支持QoS保障"
        suggestion = "配置Voice VLAN + Data VLAN，启用PoE，配置QoS优先级"

    elif role == PortRole.STORAGE_NETWORK:
        insight = "存储网络端口，启用Jumbo Frame以提升传输效率"
        suggestion = "确保路径MTU一致，验证巨帧配置，监控存储流量"

    elif role == PortRole.CORE_DISTRIBUTION:
        insight = f"核心/分发层设备，类型: {device_type.value}"
        suggestion = "检查VLAN路由配置，确保业务隔离，监控核心链路负载"

    else:
        insight = f"{role.value}端口，对端设备: {device_type.value}"
        suggestion = "根据实际业务需求配置端口参数，监控端口状态和流量"

    return insight, suggestion


def generate_tlv_evidence(features: PortFeatures, device_type: DeviceType) -> List[str]:
    """生成TLV证据列表"""
    evidence = []

    if features.has_port_vlan:
        evidence.append(f"Port VLAN ID存在（Access口特征）")
    if features.has_protocol_vlan:
        evidence.append(f"Protocol VLAN ID存在（Trunk口特征）")
    if features.is_aggregated:
        evidence.append(f"链路聚合启用（上联特征）")
    if features.high_mtu:
        evidence.append(f"MTU > 2000（存储网络特征）")
    if features.has_poe:
        evidence.append(f"PoE支持（终端供电特征）")
    if features.speed_10g_plus:
        evidence.append(f"速率 >= 10G（核心设备特征）")
    if features.is_router:
        evidence.append(f"路由能力（三层设备特征）")

    evidence.append(f"设备类型推断: {device_type.value}")

    return evidence


def discover_issues(features: PortFeatures) -> List[str]:
    """自动发现配置问题"""
    issues = []

    if not features.has_management_ip:
        issues.append("设备无管理地址，NMS无法管理")

    if features.speed_1g_plus and not features.duplex_full:
        issues.append("高速率但非全双工，存在性能瓶颈")

    if features.is_aggregated and not features.speed_1g_plus:
        issues.append("链路聚合但速率较低，可能配置不当")

    return issues


def format_intent_profile(profile: PortIntentProfile) -> str:
    """格式化意图配置文件为可读文本"""
    lines = [
        f"端口角色: {profile.role.value}",
        f"设备类型: {profile.device_type.value}",  # 新增
        f"网络意图: {profile.intent.value if profile.intent else '未知'}",
        f"置信度: {profile.confidence}%",
        f"受管设备: {'是' if profile.is_managed else '否'}",
        "",
        "🔍 TLV证据:"
    ] + [f"  • {evidence}" for evidence in profile.tlv_evidence] + [
        "",
        "💡 运维洞察:",
        f"  {profile.operational_insight}",
        "",
        "📋 配置建议:",
        f"  {profile.configuration_suggestion}",
    ]

    if profile.semantic_reasons:
        lines.extend([
            "",
            "🧠 语义推断原因:"
        ] + [f"  • {reason}" for reason in profile.semantic_reasons])

    if profile.auto_discovery_issues:
        lines.extend([
            "",
            "⚠️ 发现问题:"
        ] + [f"  • {issue}" for issue in profile.auto_discovery_issues])

    return "\n".join(lines)