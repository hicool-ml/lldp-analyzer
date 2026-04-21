# LLDP Analyzer - 协议语义推断引擎

**从"字段展示工具"到"端口语义推断引擎"的质变**

## 升级概述

本次升级实现了从传统LLDP抓包工具到**二层网络自动建模引擎**的跨越。

### 核心创新：PortProfile（端口语义层）

在原有架构基础上，新增了协议语义推断层：

```
LLDPDevice (原始数据)
    ↓
PortProfile (协议语义推断) ← NEW! 核心创新
    ↓
DeviceView (展示层)
    ↓
UI / CSV / Topology
```

## 架构分层

### Before: 字段展示工具
```
TLV解析 → 字符串 → QLabel显示
```
**价值**: 只是把LLDP字段给人看

### After: 语义推断引擎
```
TLV组合 → 协议语义推断 → 端口角色 → 智能决策
```
**价值**: 让系统自动理解网络拓扑与端口设计意图

## PortProfile 推断规则

### 规则1: Trunk口检测 (置信度90%+)
**特征组合**:
- Port VLAN存在（Native VLAN）
- Protocol VLAN存在（Tagged VLANs）
- 高速（1G+）
- 无PoE

**推断**: 干道口，用于设备间互联

### 规则2: 聚合上联检测 (置信度95%+)
**特征组合**:
- 链路聚合启用（LAG）
- 路由能力
- 高速（10G+）

**推断**: 核心上联口，高带宽主干道

### 规则3: 终端接入口检测 (置信度85%+)
**特征组合**:
- PoE供电
- 100M或1G速率
- 单一VLAN（无Protocol VLAN）

**推断**: 连接AP/Phone/IP Camera等终端设备

**示例**:
```
Port VLAN = 2011
Protocol VLAN = None
PoE = 支持
速率 = 100M Full

↓ 语义推断

🟢 Terminal / Access Port (置信度85%)
原因: PoE供电 / 百兆速率 / 无Protocol VLAN
```

### 规则4: Access口检测 (置信度70%+)
**特征组合**:
- 单一Port VLAN
- 无Protocol VLAN
- 无PoE

**推断**: 普通接入端口

### 规则5: 上联口检测 (置信度80%+)
**特征组合**:
- 路由能力
- 高速（10G+）
- 携带VLAN

**推断**: 路由上联口

## 实际应用价值

### 1. UI可视化升级

**Before**:
```
VLAN: 10 (Untagged)
PoE: 支持
速率: 100M Full
```
用户需要自己脑补端口角色

**After**:
```
🟢 Terminal / Access Port (置信度85%)
原因: PoE供电 / 百兆速率 / 单一VLAN

VLAN: 10 (Untagged)
PoE: 支持
速率: 100M Full
```
系统自动告知用户端口在网络中的角色

### 2. CSV导出升级

**Before**:
```csv
系统名称 | VLAN | PoE | 速率
Ruijie  | 10   | 支持 | 100M
```

**After**:
```csv
端口角色 | 置信度 | 推断依据 | 系统名称 | VLAN | PoE
Terminal | 85%    | PoE供电/百兆/单VLAN | Ruijie | 10 | 支持
```
运维人员可以快速理解网络结构

### 3. 网络拓扑自动着色

未来Graphviz拓扑图可以实现：
- **绿色** - Access口
- **蓝色** - Trunk口
- **紫色** - 聚合上联
- **橙色** - 终端接入口（AP/Phone）

**完全自动化，无需人工标注！**

### 4. 运维决策支持

系统可以自动发现：
- 哪些端口是核心链路（Uplink LAG）
- 哪些端口接入了终端（Terminal）
- 哪些端口是干道（Trunk）
- 网络是否按照设计意图配置

## 代码实现

### 核心文件

**lldp/port_profile.py** (350行)
- `PortProfile` 数据类
- `PortRole` 枚举
- `infer_port_profile()` 推断引擎
- 样式生成函数

**lldp/view_model.py** (更新)
- 集成PortProfile
- `to_view()` 调用推断引擎

**ui/pro_window.py** (更新)
- 显示端口角色
- 导出包含角色信息

### 推断引擎示例

```python
def infer_port_profile(device) -> PortProfile:
    """
    协议语义推断引擎

    通过分析TLV组合，推断端口在网络中的角色
    """
    reasons = []
    score = 0

    # 提取关键属性
    port_vlan = safe_get(device, 'port_vlan')
    protocol_vlan = safe_get(device, 'protocol_vlan_id')
    link_agg = safe_get(device, 'link_aggregation')
    poe = safe_get(device, 'poe')
    macphy = safe_get(device, 'macphy_config')

    # Trunk口检测
    if port_vlan and protocol_vlan:
        reasons.append("同时存在Port VLAN与Protocol VLAN")
        score += 4
        # 更多判断...

    # 终端口检测
    if poe and poe.supported:
        reasons.append("支持PoE供电")
        score += 3
        # 更多判断...

    # 返回推断结果
    return PortProfile(
        role=PortRole.TRUNK,
        confidence=95,
        reasons=reasons,
        suggested_color="#3b82f6"
    )
```

## 质变对比

| 维度 | Before | After |
|------|--------|-------|
| **定位** | LLDP抓包工具 | 二层网络自动建模引擎 |
| **能力** | 显示字段 | 语义推断 + 拓扑理解 |
| **价值** | 网络发现 | 网络自动建模 + 运维决策支持 |
| **技术** | TLV解析 | TLV组合语义分析 |
| **目标用户** | 网络工程师 | 网管系统（NMS） |
| **商业价值** | 低 | 高（接近商业NMS能力） |

## 与商业NMS对比

### 商业NMS才有的能力

1. ✅ 自动发现网络拓扑
2. ✅ 识别端口角色
3. ✅ 推断网络设计意图
4. ✅ 拓扑可视化
5. ✅ 运维决策支持

### 我们已实现

1. ✅ 端口角色推断（5种角色）
2. ✅ 置信度计算
3. ✅ 推断依据可视化
4. ✅ 导出包含语义信息

### 待实现

- [ ] 自动拓扑图生成
- [ ] 拓扑自动着色
- [ ] 批量设备分析
- [ ] 配置一致性检查

## 下一步计划

### 短期
1. 完善推断规则（更多TLV组合）
2. 提高推断准确度
3. 添加更多端口角色类型
4. 用户反馈学习机制

### 中期
1. Graphviz自动拓扑生成
2. 拓扑图自动着色
3. 网络结构可视化分析
4. 异常配置检测

### 长期
1. 网络自动建模
2. 配置建议生成
3. 容量规划分析
4. 故障根因分析

## 总结

这次升级是从"功能堆砌"到"智能系统"的关键转变：

**Before**:
- 程序员视角：TLV解析 + UI显示
- 用户价值：网络发现工具

**After**:
- 算法工程师视角：协议语义推断 + 智能决策
- 用户价值：网络自动建模引擎

这不仅仅是代码重构，而是**产品定位的升级**。

---

**作者**: Claude + 用户协作
**日期**: 2026-04-21
**版本**: v2.0 - Semantic Inference Engine
