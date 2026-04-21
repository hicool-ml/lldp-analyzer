# LLDP Analyzer v2.0 - 协议语义推断引擎

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-Latest-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

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

### 方式1: 直接下载（推荐）

下载最新发布版本：[LLDP Analyzer v2.exe](https://github.com/hicool-ml/lldp-analyzer/releases)

**要求**: Windows 10/11 + Npcap驱动

### 方式2: 源码运行

\`\`\`bash
git clone https://github.com/hicool-ml/lldp-analyzer.git
cd lldp-analyzer
pip install -r requirements.txt
python main_pro.py
\`\`\`

---

## 🎖️ 使用指南

### 快速开始

1. 选择网络适配器（有线网卡）
2. 点击"开始捕获"
3. **推荐**: 先点击"开始捕获"，再插入网线
4. 等待3-5秒自动发现设备
5. 查看端口角色推断结果

---

## 🏆 项目亮点

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

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**
