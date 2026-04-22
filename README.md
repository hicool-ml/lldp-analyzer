# LLDP Analyzer v3.0 - 专业NMS推断引擎

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-Latest-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/hicool-ml/lldp-analyzer/actions)
[![Build macOS](https://github.com/hicool-ml/lldp-analyzer/actions/workflows/build-macos.yml/badge.svg)](https://github.com/hicool-ml/lldp-analyzer/actions/workflows/build-macos.yml)

> **从传统LLDP抓包工具到二层网络自动建模引擎的质变**

🎯 **核心特性**: 协议语义推断 | 智能端口角色识别 | 双协议支持 (LLDP/CDP)

---

## 🚀 项目简介

LLDP Analyzer v3.0 是一个专业的二层网络自动发现与分析工具，实现了**专业NMS推断引擎**能力。

### 💡 专业NMS推断能力

**Feature + Rule架构**: 17个语义特征 + 规则优先级引擎

自动识别10种端口角色（附带置信度和推断依据）：

| 端口角色 | 置信度 | 特征 | 应用场景 |
|---------|--------|------|---------|
| 🟢 **Access Terminal** | 98% | PoE + 千兆 + 单VLAN | PC/Printer接入 |
| 🟢 **Access Wireless** | 95% | PoE + 千兆 + 无线TLV | AP接入 |
| 🟡 **Access Voice** | 92% | PoE + 百兆 + LLDP-MED | IP Phone接入 |
| 🔵 **Trunk Native** | 90% | Port VLAN + Protocol VLAN | 设备间干道互联 |
| 🔵 **Trunk No Native** | 88% | Protocol VLAN Only | 纯Tagged干道 |
| 🟣 **Uplink LAG** | 95% | 链路聚合 + 高速 | 核心聚合上联 |
| 🟣 **Uplink Single** | 85% | 高速 + 路由能力 | 单路上联 |
| 🟣 **Core/Distribution** | 98% | 路由/交换能力 + 高速 | 核心设备互联 |
| 🔵 **Storage Network** | 90% | 高MTU + 万兆 + Jumbo | 存储网络 |
| ⚙️ **Infrastructure** | 85% | 交换能力 + 管理地址 | 基础设施设备 |

---

## ✨ 主要功能

### 1. 协议支持
- ✅ **LLDP** (IEEE 802.1AB)
- ✅ **CDP** (Cisco Discovery Protocol)
- ✅ **双协议自动识别**

### 2. 专业NMS推断引擎
- 🔥 **Feature抽象层** - 17个语义特征提取
- 🔥 **规则优先级引擎** - 绝对规则直接返回
- 🔥 **DeviceType推断** - AP/Phone/Switch/Router参与判断
- 🔥 **厂商兼容性** - 统一TLV安全访问机制
- 🔥 **置信度机制** - 动态计算 + 可解释性

### 3. 现代化UI
- 🎨 **卡片式设计** - 清晰的信息展示
- 🎨 **实时发现** - 设备自动捕获
- 🎨 **线程安全** - 稳定的多线程架构

---

## 📦 下载与安装

### 🪟 Windows版本

**方式1: 直接下载（推荐）**

下载最新发布版本：[Releases页面](https://github.com/hicool-ml/lldp-analyzer/releases)

**要求**:
- Windows 10/11
- [Npcap驱动](https://npcap.com/) (安装时勾选"Support raw 802.11 traffic")

**方式2: 源码运行**

\`\`\`bash
git clone https://github.com/hicool-ml/lldp-analyzer.git
cd lldp-analyzer
pip install -r requirements.txt
python main_pro.py
\`\`\`

---

### 🍎 macOS版本 (支持M1/M2/M3芯片)

**方式1: 下载构建产物**

从[GitHub Actions](https://github.com/hicool-ml/lldp-analyzer/actions)下载最新构建：
1. 点击最新的Actions运行记录
2. 在"Artifacts"部分下载 \`LLDP-Analyzer-macOS\`
3. 解压后获得 \`LLDP Analyzer v2.app\` 和 \`LLDP_Analyzer_v2_macos.dmg\`

**方式2: 使用DMG安装**
1. 下载 \`LLDP_Analyzer_v2_macos.dmg\`
2. 双击DMG文件挂载磁盘映像
3. 将 \`LLDP Analyzer v2.app\` 拖到"应用程序"文件夹

**要求**:
- macOS 10.13+ (High Sierra或更高版本)
- **🔌 硬件要求**: macOS便携系统需要USB或Thunderbolt以太网适配器
  - 推荐USB 3.0转千兆以太网适配器
  - 或Thunderbolt扩展坞
  - **注意**: Wi-Fi接口无法捕获LLDP报文

**权限设置** (⚠️ **重要**: macOS网络捕获需要特殊权限):

### 🔧 首次运行前的权限配置

macOS需要root权限才能访问BPF设备进行网络数据包捕获。**必须先设置权限，否则无法捕获LLDP报文！**

#### 方法1: 一次性权限修复（推荐）⭐

**运行一次这个命令，之后就可以直接点击图标运行：**

\`\`\`bash
# 修复BPF设备权限
sudo chgrp wheel /dev/bpf* && sudo chmod 660 /dev/bpf*
\`\`\`

**然后**：
1. 直接双击 \`LLDP Analyzer v2.app\` 图标
2. 在Launchpad或Spotlight中搜索并运行
3. 像普通macOS应用一样使用

#### 方法2: 永久权限修复（重启后仍有效）

**如果你希望重启后仍然可以直接点击运行：**

\`\`\`bash
# 创建系统服务，每次启动时自动修复权限
sudo tee /Library/LaunchDaemons/com.bpf.fix.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bpf.fix</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/chmod</string>
        <string>660</string>
        <string>/dev/bpf0</string>
        <string>/dev/bpf1</string>
        <string>/dev/bpf2</string>
        <string>/dev/bpf3</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

# 加载服务
sudo launchctl load -w /Library/LaunchDaemons/com.bpf.fix.plist
\`\`\`

#### 方法3: 命令行启动（临时）

**如果不想修改权限，可以每次用sudo启动：**

\`\`\`bash
# 进入Applications目录
cd /Applications

# 使用sudo运行
sudo "LLDP Analyzer v2.app/Contents/MacOS/LLDP Analyzer v2"
\`\`\`

或者创建一个桌面启动器：

\`\`\`bash
# 在桌面创建启动器
cat > ~/Desktop/LLDP\ Analyzer\ 启动器.command << 'EOF'
#!/bin/bash
cd /Applications
sudo "LLDP Analyzer v2.app/Contents/MacOS/LLDP Analyzer v2"
EOF

chmod +x ~/Desktop/LLDP\ Analyzer\ 启动器.command

# 之后双击桌面上的"LLDP Analyzer 启动器"即可
\`\`\`

### ⚠️ 常见权限问题

**问题**: \`Permission denied: could not open /dev/bpf0\`
- **原因**: BPF设备权限不足
- **解决**: 运行 \`sudo chgrp wheel /dev/bpf* && sudo chmod 660 /dev/bpf*\`

**问题**: 每次重启后需要重新设置权限
- **解决**: 使用上面的"方法2: 永久权限修复"

**问题**: 仍然无法捕获设备
- **检查**: 是否选择了正确的网络接口（避免en0 Wi-Fi）
- **检查**: 是否连接了支持LLDP的网络设备
- **诊断**: 运行 \`python3 macos_network_check.py\` 诊断工具

---

### 🧪 macOS诊断工具

LLDP Analyzer包含了专门的macOS诊断工具，可以帮助快速定位问题：

\`\`\`bash
# 运行诊断工具
python3 macos_network_check.py

# 诊断内容：
# ✅ 操作系统版本检查
# ✅ 管理员权限检查
# ✅ 网络接口扫描
# ✅ BPF设备状态
# ✅ 原始套接字权限测试
# ✅ 推荐合适的网络接口
\`\`\`

**推荐使用流程**：
1. 遇到捕获问题时先运行诊断工具
2. 根据诊断输出修复发现的问题
3. 重新运行LLDP Analyzer

---

### 📱 macOS系统偏好设置

某些情况下，需要在系统设置中手动授予权限：

**完全磁盘访问权限**（如果应用无法启动）：
1. 打开"系统设置 > 隐私与安全性"
2. 选择"完全磁盘访问权限"
3. 点击"+"添加"终端"或"LLDP Analyzer v2"

**本地网络权限**（如果应用无法访问网络）：
1. 打开"系统设置 > 隐私与安全性 > 本地网络"
2. 确保LLDP Analyzer已启用

**防火墙设置**（如果仍然无法捕获）：
1. 打开"系统设置 > 网络 > 防火墙"
2. 确保防火墙允许LLDP Analyzer或已关闭

**方式3: 源码运行**

\`\`\`bash
git clone https://github.com/hicool-ml/lldp-analyzer.git
cd lldp-analyzer
pip3 install -r requirements.txt
python3 main_pro.py
\`\`\`

---

### 🐧 Linux版本

**源码运行**:

\`\`\`bash
git clone https://github.com/hicool-ml/lldp-analyzer.git
cd lldp-analyzer
pip3 install -r requirements.txt
sudo python3 main_pro.py  # 需要root权限或CAP_NET_RAW能力
\`\`\`

---

## 🎖️ 使用指南

### 🪟 Windows 快速开始

1. 选择网络适配器（有线网卡，避免选择虚拟网卡）
2. 点击"开始捕获"
3. **推荐**: 先点击"开始捕获"，再插入网线
4. 等待3-5秒自动发现设备
5. 查看端口角色推断结果

---

### 🍎 macOS 快速开始

#### 📋 前提条件检查

**在开始之前，请确认：**

1. ✅ **已完成BPF权限设置**（见上面的"权限设置"章节）
2. ✅ **已连接网络适配器**（USB/Thunderbolt以太网）
3. ✅ **网线连接到支持LLDP的网络设备**

#### 🚀 操作步骤

1. **启动应用**
   - 直接双击 \`LLDP Analyzer v2.app\` 图标
   - 或在Launchpad中搜索"LLDP Analyzer"
   - 如果出现权限提示，输入macOS密码

2. **选择正确的网络接口**
   - **优先选择**: \`en1\`, \`en2\`, \`en3\` 等接口（通常是有线适配器）
   - **避免选择**: \`en0\`（通常是Wi-Fi，无法捕获LLDP）
   - **识别方法**: 接口描述包含"USB"、"Thunderbolt"、"Ethernet"
   - **检查IP**: 有IP地址的接口说明物理链路已连接

3. **开始捕获**
   - 点击"开始捕获"按钮
   - 等待3-5秒自动发现设备
   - 查看端口角色推断结果

#### 💡 网络接口选择指南

**Mac mini M4/M2/M1内置万兆网卡：**
- ⚠️ **已知问题**: 某些内置万兆网卡驱动可能不支持混杂模式
- ✅ **推荐方案**: 使用USB/Thunderbolt以太网适配器
- 📝 **接口名称**: 通常显示为 \`bridge0\` 或 \`tgten0\`
- 🔧 **临时解决**: \`sudo ifconfig bridge0 mtu 1500\`（降低MTU）

**MacBook Pro/Air便携系统：**
- 🔌 **必需**: USB-C或Thunderbolt以太网适配器
- ✅ **推荐**: Apple Thunderbolt至千兆以太网适配器
- 📝 **接口名称**: 通常为 \`en1\`、\`en2\`
- 🚫 **避免**: \`en0\`（Wi-Fi，无法捕获LLDP）

**接口识别参考：**
\`\`\`
en0   Wi-Fi                    ❌ 避免选择
en1   USB Ethernet             ✅ 优先选择
en2   Thunderbolt Ethernet     ✅ 优先选择
en3   USB 10GbE Adapter        ✅ 优先选择
bridge0 Thunderbolt Bridge     ⚠️  可能不工作
\`\`\`

#### 🔍 macOS常见问题排查

**❓ 未发现设备（已开启DEBUG日志）**
- ✅ **检查物理连接**: 网线是否插好，LED灯是否亮起
- ✅ **检查网络接口**: 是否选择了正确的有线接口
- ✅ **检查目标设备**: 确认连接的是交换机/路由器，不是电脑
- ✅ **检查LLDP状态**: 某些交换机端口默认关闭LLDP，需要在管理界面启用

**❓ 权限被拒绝 (\`Permission denied: could not open /dev/bpf0\`)**
- 🔧 **立即解决**: \`sudo chgrp wheel /dev/bpf* && sudo chmod 660 /dev/bpf*\`
- 🔧 **永久解决**: 使用"方法2: 永久权限修复"（见权限设置章节）

**❓ 捕获立即失败，无错误信息**
- 🔍 **运行诊断**: \`python3 macos_network_check.py\`
- 🔍 **手动测试**: \`sudo tcpdump -i en1 -v ether[12:2] == 0x88cc\`
- 🔍 **检查接口**: \`ifconfig -a | grep -A 5 "flags=8863"\`

**❓ Mac mini M4万兆网卡无法捕获**
- 💡 **已知限制**: 某些万兆网卡驱动不支持混杂模式
- ✅ **推荐方案**: 使用USB或Thunderbolt以太网适配器
- 🔧 **临时测试**: 降低MTU \`sudo ifconfig bridge0 mtu 1500\`
- 📝 **接口名称**: 检查 \`networksetup -listallhardwareports\` 输出

---

### 💡 捕获技巧

**最佳实践**:
- ✅ 先启动捕获，再插入网线（可以看到完整的LLDP交互）
- ✅ 捕获时间建议5-10秒（LLDP每30秒发送一次）
- ✅ 选择物理网卡，避免虚拟网卡（VMware、VirtualBox等）
- ✅ Windows选择Realtek/Intel等物理网卡
- ✅ macOS选择en1+接口（USB/Thunderbolt适配器）

**协议识别**:
- 📘 **LLDP**: 标准协议，大多数网络设备支持
- 📗 **CDP**: Cisco私有协议，思科设备专用

---

## 🏆 项目亮点

### 🔧 自动构建系统
- ✅ **GitHub Actions CI/CD** - 自动构建多平台版本
- ✅ **macOS M芯片优化** - 原生支持Apple Silicon (M1/M2/M3)
- ✅ **自动化测试** - 每次提交自动构建验证

### 核心创新
不只是显示TLV字段，而是**理解TLV组合的含义**：
- PoE + 百兆 + 单VLAN = 终端接入口
- Port VLAN + Protocol VLAN = 干道口
- 链路聚合 + 高速 = 核心上联

这是开源工具中罕见的**协议语义推断**能力，已接近商业网络管理系统(NMS)的核心功能。

---

## 📄 许可证

MIT License

Copyright (c) 2026 hicool-ml

---

## 👨‍💻 作者

**hicool-ml** 
- Email: hicool.ml@gmail.com
- GitHub: [@hicool-ml](https://github.com/hicool-ml)

---

## 🚀 自动构建状态

### 最新构建

[![macOS Build](https://github.com/hicool-ml/lldp-analyzer/actions/workflows/build-macos.yml/badge.svg)](https://github.com/hicool-ml/lldp-analyzer/actions/workflows/build-macos.yml)

**获取最新构建版本**:
1. 访问 [Actions页面](https://github.com/hicool-ml/lldp-analyzer/actions)
2. 选择最新的"Build macOS Application"运行记录
3. 在页面底部的"Artifacts"区域下载构建产物
4. 解压后即可使用

**支持的平台**:
- 🪟 Windows 10/11 (x64)
- 🍎 macOS 10.13+ (Universal Binary / Apple Silicon)
- 🐧 Linux (源码构建)

---

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**
