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

    🔥 v3.0升级：reasons现在是规则ID集合（RuleID），支持统计分析
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
    semantic_reasons: Set["RuleID"]       # 🔥 v3.0: 规则ID集合，支持统计和二次推断（前向引用）


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


# ========== 规则定义表 ==========
class RuleID(Enum):
    """🔥 规则ID枚举 - 用于reasons规则记录（v3.0优化）"""

    def __new__(cls, value, description):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = description
        return obj

    # 绝对规则 (Priority 1)
    RULE_AGGREGATION = ("RULE_AGGREGATION", "链路聚合 → 上联口")
    RULE_PROTOCOL_VLAN = ("RULE_PROTOCOL_VLAN", "Protocol VLAN → Trunk口")
    RULE_HIGH_MTU_SPEED = ("RULE_HIGH_MTU_SPEED", "高MTU+高速率 → 存储/上联")
    RULE_ROUTER_CAPABILITY = ("RULE_ROUTER_CAPABILITY", "路由能力 → 上联口")
    RULE_DEVTYPE_AP = ("RULE_DEVTYPE_AP", "设备类型AP → 无线接入")
    RULE_DEVTYPE_PHONE = ("RULE_DEVTYPE_PHONE", "设备类型电话 → 语音接入")
    RULE_DEVTYPE_SWITCH = ("RULE_DEVTYPE_SWITCH", "设备类型交换机 → 核心设备")

    # 二次推断规则 (Priority 2)
    RULE_PORT_VLAN_ONLY = ("RULE_PORT_VLAN_ONLY", "Port VLAN → Access口")
    RULE_POE_LOWSPEED = ("RULE_POE_LOWSPEED", "PoE+低速 → 终端接入")
    RULE_HIGHSPEED_BRIDGE = ("RULE_HIGHSPEED_BRIDGE", "10G+桥接 → 核心设备")
    RULE_MULTIVLAN_BRIDGE = ("RULE_MULTIVLAN_BRIDGE", "多VLAN桥接 → 核心交换机")
    RULE_MGMTIP_HIGHSPEED = ("RULE_MGMTIP_HIGHSPEED", "管理IP+高速 → 基础设施")

    # DeviceType推断规则
    RULE_DEVTYPE_POE_WLAN = ("RULE_DEVTYPE_POE_WLAN", "PoE+无线 → AP")
    RULE_DEVTYPE_POE_NOWLAN = ("RULE_DEVTYPE_POE_NOWLAN", "PoE+无无线 → 电话")
    RULE_DEVTYPE_ROUTER = ("RULE_DEVTYPE_ROUTER", "路由能力 → Router")
    RULE_DEVTYPE_BRIDGE_AGG = ("RULE_DEVTYPE_BRIDGE_AGG", "桥接+聚合 → Switch")
    RULE_DEVTYPE_JUMBO = ("RULE_DEVTYPE_JUMBO", "巨帧+10G → Storage")
    RULE_DEVTYPE_BRIDGE = ("RULE_DEVTYPE_BRIDGE", "桥接能力 → Switch")
    RULE_DEVTYPE_MGMTIP = ("RULE_DEVTYPE_MGMTIP", "管理IP+描述 → Server")
    RULE_DEVTYPE_MGMTIP_TLV = ("RULE_DEVTYPE_MGMTIP_TLV", "🔥 Management Address TLV → 网络设备")


@dataclass
class InferenceRule:
    """推断规则数据结构"""
    rule_id: RuleID
    name: str
    priority: int  # 1=绝对规则, 2=二次推断
    condition_fn: callable  # 判断函数
    action_fn: callable  # 执行函数
    description: str


# ========== 规则表 ==========
PRIORITY_RULES = [
    InferenceRule(
        rule_id=RuleID.RULE_AGGREGATION,
        name="链路聚合规则",
        priority=1,
        condition_fn=lambda f, dt: f.is_aggregated,
        action_fn=lambda f, dt: PortRole.UPLINK_LAG,
        description="检测到链路聚合 → 上联口"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_PROTOCOL_VLAN,
        name="Protocol VLAN规则",
        priority=1,
        condition_fn=lambda f, dt: f.has_protocol_vlan,
        action_fn=lambda f, dt: PortRole.TRUNK_NATIVE if f.has_port_vlan else PortRole.TRUNK_NO_NATIVE,
        description="Protocol VLAN存在 → Trunk口"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_HIGH_MTU_SPEED,
        name="高MTU+高速率规则",
        priority=1,
        condition_fn=lambda f, dt: f.high_mtu and f.speed_1g_plus,
        action_fn=lambda f, dt: PortRole.STORAGE_NETWORK if f.jumbo_frame else PortRole.UPLINK_SINGLE,
        description="高MTU+高速率 → 存储网络或上联口"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_ROUTER_CAPABILITY,
        name="路由能力规则",
        priority=1,
        condition_fn=lambda f, dt: f.is_router,
        action_fn=lambda f, dt: PortRole.UPLINK_SINGLE,
        description="路由能力 → 上联口"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_AP,
        name="AP设备修正规则",
        priority=1,
        condition_fn=lambda f, dt: dt == DeviceType.ACCESS_POINT,
        action_fn=lambda f, dt: PortRole.ACCESS_WIRELESS,
        description="设备类型为AP → 无线接入口"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_PHONE,
        name="IP电话修正规则",
        priority=1,
        condition_fn=lambda f, dt: dt == DeviceType.IP_PHONE,
        action_fn=lambda f, dt: PortRole.ACCESS_VOICE,
        description="设备类型为IP电话 → 语音接入口"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_SWITCH,
        name="交换机修正规则",
        priority=1,
        condition_fn=lambda f, dt: dt and dt in [DeviceType.ROUTER, DeviceType.SWITCH],
        action_fn=lambda f, dt: PortRole.CORE_DISTRIBUTION,
        description="设备类型为交换机/路由器 → 核心设备"
    ),
]

SECONDARY_RULES = [
    InferenceRule(
        rule_id=RuleID.RULE_PORT_VLAN_ONLY,
        name="Port VLAN单独规则",
        priority=2,
        condition_fn=lambda f, dt: f.has_port_vlan and not f.has_protocol_vlan,
        action_fn=lambda f, dt: PortRole.ACCESS_TERMINAL,
        description="仅Port VLAN → Access口"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_POE_LOWSPEED,
        name="PoE低速规则",
        priority=2,
        condition_fn=lambda f, dt: f.has_poe and not f.speed_1g_plus,
        action_fn=lambda f, dt: PortRole.ACCESS_TERMINAL,
        description="PoE+低速 → 终端接入"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_HIGHSPEED_BRIDGE,
        name="高速桥接规则",
        priority=2,
        condition_fn=lambda f, dt: f.speed_10g_plus and f.is_bridge,
        action_fn=lambda f, dt: PortRole.CORE_DISTRIBUTION,
        description="10G+桥接 → 核心设备"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_MULTIVLAN_BRIDGE,
        name="多VLAN桥接规则",
        priority=2,
        condition_fn=lambda f, dt: f.is_bridge and (
            f.has_mgmt_vlan + f.has_data_vlan + f.has_voice_vlan + f.has_storage_vlan >= 2
        ),
        action_fn=lambda f, dt: PortRole.CORE_DISTRIBUTION,
        description="多VLAN桥接 → 核心交换机"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_MGMTIP_HIGHSPEED,
        name="管理IP高速规则",
        priority=2,
        condition_fn=lambda f, dt: f.has_management_ip and f.speed_1g_plus,
        action_fn=lambda f, dt: PortRole.INFRASTRUCTURE,
        description="管理IP+高速 → 基础设施"
    ),
]

DEVTYPE_RULES = [
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_POE_WLAN,
        name="PoE+无线=AP",
        priority=1,
        condition_fn=lambda f: f.has_poe and f.is_wlan,
        action_fn=lambda f: DeviceType.ACCESS_POINT,
        description="PoE+无线能力 → AP"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_POE_NOWLAN,
        name="PoE+无无线=电话",
        priority=1,
        condition_fn=lambda f: f.has_poe and not f.is_wlan,
        action_fn=lambda f: DeviceType.IP_PHONE,
        description="PoE+无无线 → IP电话"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_ROUTER,
        name="路由能力=Router",
        priority=1,
        condition_fn=lambda f: f.is_router,
        action_fn=lambda f: DeviceType.ROUTER,
        description="路由能力 → Router"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_BRIDGE_AGG,
        name="桥接+聚合=Switch",
        priority=1,
        condition_fn=lambda f: f.is_bridge and f.is_aggregated,
        action_fn=lambda f: DeviceType.SWITCH,
        description="桥接+聚合 → Switch"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_JUMBO,
        name="巨帧+10G=Storage",
        priority=1,
        condition_fn=lambda f: f.jumbo_frame and f.speed_10g_plus,
        action_fn=lambda f: DeviceType.STORAGE,
        description="巨帧+10G → Storage"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_BRIDGE,
        name="桥接=Switch",
        priority=2,
        condition_fn=lambda f: f.is_bridge,
        action_fn=lambda f: DeviceType.SWITCH,
        description="桥接能力 → Switch"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_MGMTIP,
        name="管理IP+描述=Server",
        priority=2,
        condition_fn=lambda f: f.has_management_ip and f.has_system_description,
        action_fn=lambda f: DeviceType.SERVER,
        description="管理IP+系统描述 → Server"
    ),
    InferenceRule(
        rule_id=RuleID.RULE_DEVTYPE_MGMTIP_TLV,
        name="🔥 Management Address TLV大杀器",
        priority=1,
        condition_fn=lambda f: f.has_management_ip,
        action_fn=lambda f: DeviceType.SWITCH,  # 🔥 有Management Address的基本都是网络设备
        description="Management Address TLV → 网络设备（优先Switch）"
    ),
]


def infer_device_type(features: PortFeatures, device) -> DeviceType:
    """
    🔥 新增：DeviceType推断（基于规则表）

    🔥 优化：利用Management Address TLV提升精度
    """
    # 按优先级执行规则
    for rule in DEVTYPE_RULES:
        if rule.condition_fn(features):
            return rule.action_fn(features)

    # 默认
    return DeviceType.TERMINAL


def run_priority_rules(features: PortFeatures, device_type: DeviceType) -> tuple[Optional[PortRole], Optional[RuleID]]:
    """
    🔥 规则引擎：优先级规则（绝对规则）- 基于规则表

    返回: (PortRole, RuleID)
    """
    for rule in PRIORITY_RULES:
        if rule.condition_fn(features, device_type):
            return rule.action_fn(features, device_type), rule.rule_id

    return None, None


def run_secondary_inference(features: PortFeatures, device_type: DeviceType) -> tuple[PortRole, RuleID]:
    """
    🔥 二次推断：基于规则表的特征组合推断

    返回: (PortRole, RuleID)
    """
    for rule in SECONDARY_RULES:
        if rule.condition_fn(features, device_type):
            return rule.action_fn(features, device_type), rule.rule_id

    # 默认推断
    if features.has_management_ip:
        return PortRole.ACCESS_TERMINAL, RuleID.RULE_PORT_VLAN_ONLY
    else:
        return PortRole.UNKNOWN, RuleID.RULE_PORT_VLAN_ONLY


def infer_port_intent(device) -> PortIntentProfile:
    """
    🔥 质变升级：专业NMS推断引擎（v3.0优化版）

    架构：TLV → Feature → Rule Table (Priority Chain) → PortRole/DeviceType → Dynamic Confidence

    🔥 新增特性：
    1. 规则表驱动（RuleID枚举）
    2. reasons变成规则记录（RuleID格式）
    3. 动态置信度计算（基于reasons数量）
    4. Management Address TLV优先规则
    """
    # ========== 第1层：Feature抽象 ==========
    features = extract_features(device)

    # ========== 第2层：DeviceType推断（含Management Address TLV规则）==========
    device_type = infer_device_type(features, device)

    # ========== 第3层：规则表引擎 ==========
    priority_role, priority_rule_id = run_priority_rules(features, device_type)

    # ========== 第4层：规则ID收集与置信度计算 ==========
    rule_ids = set()  # 🔥 收集所有触发的规则ID

    if priority_role:
        # 绝对规则匹配
        final_role = priority_role
        rule_ids.add(priority_rule_id)
    else:
        # 二次推断
        final_role, secondary_rule_id = run_secondary_inference(features, device_type)
        rule_ids.add(secondary_rule_id)

    # ========== 🔥 动态置信度计算 ==========
    # confidence = len(reasons) * 15
    confidence = min(98, len(rule_ids) * 15)

    # ========== 生成运维洞察和建议 ==========
    insight, suggestion = generate_insight_and_suggestion(final_role, device_type, features, rule_ids)

    # ========== 生成TLV证据 ==========
    evidence = generate_tlv_evidence(features, device_type, rule_ids)

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
        semantic_reasons=rule_ids  # 🔥 改为规则ID集合
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


def generate_insight_and_suggestion(role: PortRole, device_type: DeviceType, features: PortFeatures, rule_ids: Set[RuleID]):
    """🔥 生成运维洞察和配置建议（基于规则ID）"""

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


def generate_tlv_evidence(features: PortFeatures, device_type: DeviceType, rule_ids: Set[RuleID]) -> List[str]:
    """🔥 生成TLV证据列表（基于规则ID）"""
    evidence = []

    # 将RuleID转换为可读描述
    rule_descriptions = {
        RuleID.RULE_AGGREGATION: "链路聚合启用（上联特征）",
        RuleID.RULE_PROTOCOL_VLAN: "Protocol VLAN ID存在（Trunk口特征）",
        RuleID.RULE_HIGH_MTU_SPEED: "高MTU+高速率（存储/上联特征）",
        RuleID.RULE_ROUTER_CAPABILITY: "路由能力（三层设备特征）",
        RuleID.RULE_DEVTYPE_AP: "设备类型推断: AP（无线能力）",
        RuleID.RULE_DEVTYPE_PHONE: "设备类型推断: IP电话（PoE特征）",
        RuleID.RULE_DEVTYPE_SWITCH: "设备类型推断: Switch（桥接能力）",
        RuleID.RULE_PORT_VLAN_ONLY: "Port VLAN ID存在（Access口特征）",
        RuleID.RULE_POE_LOWSPEED: "PoE支持+低速（终端接入特征）",
        RuleID.RULE_HIGHSPEED_BRIDGE: "10G+速率+桥接（核心设备特征）",
        RuleID.RULE_MULTIVLAN_BRIDGE: "多VLAN业务+桥接（核心交换机特征）",
        RuleID.RULE_MGMTIP_HIGHSPEED: "管理IP+高速（基础设施特征）",
        RuleID.RULE_DEVTYPE_MGMTIP_TLV: "🔥 Management Address TLV（网络设备特征）",
    }

    # 添加触发的规则描述
    for rule_id in rule_ids:
        if rule_id in rule_descriptions:
            evidence.append(rule_descriptions[rule_id])

    # 添加设备类型
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
    """🔥 格式化意图配置文件为可读文本（v3.0优化版）"""
    lines = [
        f"端口角色: {profile.role.value}",
        f"设备类型: {profile.device_type.value}",
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
            "🧠 触发规则 (RuleID):"
        ] + [f"  • {rule_id.value}: {rule_id.description}" for rule_id in profile.semantic_reasons])

    if profile.auto_discovery_issues:
        lines.extend([
            "",
            "⚠️ 发现问题:"
        ] + [f"  • {issue}" for issue in profile.auto_discovery_issues])

    return "\n".join(lines)