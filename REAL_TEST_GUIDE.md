# 真实LLDP设备环境测试指南

## 📋 测试准备清单

### 硬件要求
- [ ] 至少一个网络接口卡 (NIC)
- [ ] 网络线缆 (以太网线)
- [ ] LLDP/CDP 设备 (交换机、路由器、IP电话等)

### 软件要求
- [ ] Python 3.11+
- [ ] dpkt 已安装 (`pip install dpkt`)
- [ ] scapy 已安装 (`pip install scapy`)
- [ ] 管理员/root 权限

### 网络环境
- [ ] 网络线缆已连接
- [ ] 目标设备已开机并启用 LLDP/CDP
- [ ] 防火墙允许协议捕获

---

## 🚀 测试方法

### 方法1: 交互式测试 (推荐)

```bash
cd D:/lldp3
python real_lldp_test.py
```

**特点**:
- ✅ 用户友好的交互界面
- ✅ 自动检测网络接口
- ✅ 让用户选择测试参数
- ✅ 实时显示发现的设备
- ✅ 自动保存测试结果
- ✅ 生成详细报告

**流程**:
1. 环境检查
2. 接口发现
3. 选择接口
4. 设置捕获时长
5. 开始捕获
6. 结果分析
7. 保存报告

### 方法2: 自动化测试

```bash
cd D:/lldp3
python auto_lldp_test.py
```

**特点**:
- ✅ 无需用户交互
- ✅ 自动选择最佳接口
- ✅ 固定30秒捕获
- ✅ 适合批处理和脚本化

### 方法3: 快速测试

```bash
cd D:/lldp3
python -c "
from lldp.capture_dpkt import HybridCapture
from scapy.all import get_working_ifaces
import time

# Auto-select interface
interfaces = [iface for iface in get_working_ifaces()
             if 'ethernet' in iface.description.lower() or '以太网' in iface.description]

if interfaces:
    iface = interfaces[0]
    print(f'Testing on: {iface.description}')

    capture = HybridCapture()
    devices_found = []

    capture.start_capture(iface, duration=10, callback=lambda d: devices_found.append(d))

    while capture.is_active():
        time.sleep(0.5)

    print(f'Found {len(devices_found)} devices')
    for d in devices_found:
        print(f'  - {d.get_display_name()}')
else:
    print('No suitable interface found')
"
```

---

## 🔧 故障排除

### 问题1: 没有发现设备

**可能原因**:
1. 网络线缆未连接
2. 目标设备未启用 LLDP/CDP
3. 权限不足
4. 防火墙阻止

**解决方案**:
```bash
# 检查网络连接
ipconfig /all           # Windows
ifconfig                # Linux/macOS

# 检查权限 (以管理员身份运行)
# Windows: 右键 -> 以管理员身份运行
# Linux: sudo python real_lldp_test.py

# 检查防火墙 (Windows)
# 暂时关闭防火墙或允许 Npcap
```

### 问题2: 接口发现失败

**可能原因**:
1. Npcap/WinPcap 未安装
2. 网络适配器被禁用
3. Scapy 安装问题

**解决方案**:
```bash
# 重新安装 Scapy
pip uninstall scapy
pip install scapy

# Windows: 安装 Npcap
# 下载: https://nmap.org/npcap/
```

### 问题3: 权限错误

**Windows**:
```bash
# 以管理员身份运行命令提示符
# 然后执行测试脚本
```

**Linux**:
```bash
# 使用 sudo 运行
sudo python real_lldp_test.py

# 或者设置 capabilities
sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/python3.11
```

---

## 📊 测试结果分析

### 成功案例

**预期输出**:
```
[CAPTURE] Capture completed!
  Total devices discovered: 2

[ANALYSIS] Analyzing 2 discovered device(s)...

  Device #1:
    Name: H3C-5120-Switch
    Protocol: LLDP
    Chassis ID: 00:1f:2e:3d:4c:5b (MAC address)
    Port ID: GigabitEthernet1/0/1 (Interface name)
    System Name: H3C-5120-Core
    System Description: H3C Comware Platform Software...
    Capabilities: Bridge, Router
    Management IP: 192.168.1.1
    VLAN: 1

  Device #2:
    Name: Cisco-2960-Switch
    Protocol: CDP
    Chassis ID: 00:2a:3f:4e:5d:6c (MAC address)
    Port ID: FastEthernet0/1 (Interface name)
    System Name: CISCO2960-Access
    System Description: Cisco IOS Software...
    Capabilities: Switch, IGMP snooping
    Management IP: 192.168.1.2
```

### 失败案例

**无设备发现**:
```
[CAPTURE] Capture completed!
  Total devices discovered: 0

[ANALYSIS] Analyzing 0 discovered device(s)...
  [INFO] No devices found. Possible reasons:
    - No LLDP/CDP devices connected to the interface
    - Network cable not connected
    - LLDP/CDP disabled on connected devices
    - Firewall or security software blocking packets
    - Insufficient permissions (try running as admin/root)
```

---

## 📝 测试记录模板

### 测试环境
- **测试时间**: 2026-04-24 10:30
- **测试平台**: Windows 11 / Ubuntu 22.04
- **Python版本**: 3.11.6
- **网络接口**: Intel Ethernet I219-V (169.254.183.156)
- **连接设备**: H3C S5120 交换机

### 测试参数
- **捕获时长**: 30秒
- **BPF过滤器**: ether proto 0x88cc or ether host 01:00:0c:cc:cc:cc
- **后端选择**: Scapy (fallback)

### 测试结果
- **发现设备数**: 2
- **设备详情**:
  1. H3C-5120-Core (LLDP)
  2. CISCO2960-Access (CDP)
- **捕获成功率**: 100%
- **解析成功率**: 100%

### 性能指标
- **首包捕获时间**: 2.3秒
- **总捕获包数**: 1,247
- **LLDP/CDP包数**: 4
- **CPU使用率**: 15%
- **内存使用**: 45MB

---

## 🎯 测试场景

### 场景1: 单设备测试
**设置**: 直接连接电脑到单个LLDP设备
**预期**: 发现1个设备，信息完整
**验证**: 检查系统名称、端口信息、VLAN等

### 场景2: 多设备测试
**设置**: 连接到有多个LLDP设备的网络
**预期**: 发现多个设备，可能有重复
**验证**: 检查去重逻辑、信息准确性

### 场景3: CDP设备测试
**设置**: 连接到Cisco设备
**预期**: 使用CDP协议发现设备
**验证**: CDP特有字段解析正确

### 场景4: 混合环境测试
**设置**: 同时有LLDP和CDP设备
**预期**: 两种协议都能正常工作
**验证**: 协议识别准确，无冲突

---

## 🔬 高级测试

### 性能对比测试

**目的**: 对比Copilot版本与稳定版的性能差异

**方法**:
```bash
# 测试Copilot版本
cd D:/lldp3
time python real_lldp_test.py

# 测试稳定版本
cd D:/LLDP
time python real_lldp_test.py
```

**指标**:
- 启动时间
- 首包捕获时间
- 内存使用
- CPU使用
- 总运行时间

### 压力测试

**目的**: 测试长时间运行的稳定性

**方法**:
```bash
# 运行5分钟捕获
python real_lldp_test.py
# 输入duration: 300
```

**验证**:
- 无内存泄漏
- 无性能下降
- 稳定运行

### 边界测试

**目的**: 测试极端条件下的行为

**场景**:
1. 空网络环境
2. 高流量网络
3. 恶意包构造
4. 无权限运行

---

## 📈 结果评估

### 评分标准

**优秀 (90-100分)**:
- ✅ 快速发现设备 (<5秒)
- ✅ 信息完整准确
- ✅ 无错误或警告
- ✅ 性能表现良好

**良好 (70-89分)**:
- ✅ 能发现设备
- ⚠️ 部分信息缺失
- ⚠️ 有轻微警告
- ✅ 基本功能正常

**及格 (50-69分)**:
- ⚠️ 勉强发现设备
- ❌ 信息不完整
- ❌ 有明显问题
- ⚠️ 功能受限

**不及格 (<50分)**:
- ❌ 无法发现设备
- ❌ 严重错误
- ❌ 功能缺失
- ❌ 无法使用

### 测试报告

每次测试后，填写以下报告：

```markdown
## 测试报告

**测试日期**: 2026-04-24
**测试版本**: Copilot feat/dpkt-pcap-backend
**测试环境**: [详细描述]

**测试结果**: [优秀/良好/及格/不及格]
**得分**: [0-100]

**功能测试**:
- 设备发现: ✅/❌
- 信息解析: ✅/❌
- 协议支持: ✅/❌
- 错误处理: ✅/❌

**性能测试**:
- 响应时间: [秒]
- 资源使用: [MB/%]
- 稳定性: [描述]

**问题记录**:
- [问题1描述]
- [问题2描述]

**建议改进**:
- [改进建议1]
- [改进建议2]
```

---

## 🎓 学习资源

### LLDP/CDP 协议
- [LLDP IEEE 802.1AB 标准](https://standards.ieee.org/)
- [Cisco CDP 文档](https://www.cisco.com/)

### 网络测试
- [Scapy 文档](https://scapy.net/)
- [dpkt 文档](https://dpkt.readthedocs.io/)

### 故障排除
- [Wireshark 抓包分析](https://www.wireshark.org/)
- [Npcap 安装指南](https://nmap.org/npcap/)

---

*最后更新: 2026-04-24*
*测试工具版本: Copilot feat/dpkt-pcap-backend*
