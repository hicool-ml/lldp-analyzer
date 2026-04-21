# LLDP Analyzer v2.0 - 协议语义推断引擎

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-Latest-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/hicool-ml/lldp-analyzer/actions)
[![Build macOS](https://github.com/hicool-ml/lldp-analyzer/actions/workflows/build-macos.yml/badge.svg)](https://github.com/hicool-ml/lldp-analyzer/actions/workflows/build-macos.yml)

> **从传统LLDP抓包工具到二层网络自动建模引擎的质变**

🎯 **核心特性**: 协议语义推断 | 智能端口角色识别 | 双协议支持 (LLDP/CDP)

---

## 🚀 项目简介

LLDP Analyzer v2.0 是一个专业的二层网络自动发现与分析工具，实现了**协议语义推断**能力。

### 💡 智能推断能力

自动识别5种端口角色（附带置信度和推断依据）：

| 端口角色 | 置信度 | 特征 | 应用场景 |
|---------|--------|------|---------|
| 🟠 **Terminal** | 85% | PoE + 百兆/千兆 + 单VLAN | AP/Phone/IP Camera接入 |
| 🔵 **Trunk** | 90% | Port VLAN + Protocol VLAN + 高速 | 设备间干道互联 |
| 🟢 **Access** | 70% | 单一VLAN + 无PoE | 普通接入端口 |
| 🟣 **Uplink** | 80% | 路由能力 + 高速 | 网络上联 |
| 🟣 **Uplink LAG** | 95% | 链路聚合 + 高速 | 核心聚合上联 |

---

## ✨ 主要功能

### 1. 协议支持
- ✅ **LLDP** (IEEE 802.1AB)
- ✅ **CDP** (Cisco Discovery Protocol)
- ✅ **双协议自动识别**

### 2. 智能推断
- 🔥 **PortProfile** - 端口语义推断引擎
- 🔥 **置信度机制** - 0-100%可信度评估
- 🔥 **可解释性** - 详细的推断依据

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

**权限设置**:
1. 首次运行需要授予网络捕获权限
2. 在"系统设置 > 隐私与安全性 > 本地网络"中允许
3. 如需管理员权限：
   \`\`\`bash
   sudo "LLDP Analyzer v2.app/Contents/MacOS/LLDP Analyzer v2"
   \`\`\`

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

1. **连接网络适配器**
   - 插入USB或Thunderbolt以太网适配器
   - 连接网线到目标网络

2. **选择正确的网络接口**
   - 优先选择 \`en1\`, \`en2\`, \`en3\` 等接口（通常是有线适配器）
   - **避免选择** \`en0\`（通常是Wi-Fi，无法捕获LLDP）
   - 程序会自动检测USB/Thunderbolt适配器并优先推荐

3. **授予权限**（首次运行）
   - 系统会提示授予网络访问权限
   - 点击"允许"以启用网络捕获功能

4. **开始捕获**
   - 点击"开始捕获"按钮
   - 等待3-5秒自动发现设备
   - 查看端口角色推断结果

**macOS常见问题**:
- ❗ **未发现设备**: 确认使用的是有线适配器，不是Wi-Fi
- ❗ **权限被拒绝**: 在系统设置中手动允许网络访问权限
- ❗ **USB适配器不工作**: 尝试更换USB口或重新拔插适配器

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
