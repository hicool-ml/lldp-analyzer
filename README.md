# LLDP Analyzer

LLDP Analyzer 是一个面向二层网络现场排查的 LLDP/CDP 发现与端口角色推断工具。它通过抓取链路层发现协议报文，解析设备、端口、VLAN、能力、PoE、MTU 等信息，并给出面向 NMS 场景的端口角色、设备类型、置信度和推断依据。

## 主要能力

- LLDP 与 CDP 双协议识别
- PyQt6 图形界面，实时显示发现结果
- 端口角色推断：Access、Trunk、Uplink、Core/Distribution、Storage、Infrastructure 等
- 设备类型推断：Switch、Router、AP、IP Phone、Storage、Terminal 等
- 多报文融合：同一设备的后续报文会补齐缺失 TLV 字段
- Windows Npcap/Scapy 接口枚举与抓包支持
- macOS/Linux 源码运行支持

## 环境要求

- Python 3.11+
- Windows 10/11 推荐安装 [Npcap](https://npcap.com/)
- macOS/Linux 抓包通常需要相应系统权限

Windows 使用前请确认：

- 已安装 Npcap
- 有线网卡已启用并连接到支持 LLDP/CDP 的设备
- 如抓包失败，可尝试以管理员身份运行

## 安装与运行

```bash
git clone https://github.com/hicool-ml/lldp-analyzer.git
cd lldp-analyzer
python -m pip install -r requirements.txt
python main_pro.py
```

## 测试

```bash
python -m pip install -r requirements-test.txt
pytest
```

## Windows 打包

项目可用 PyInstaller 打包为单文件 exe。示例：

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name LLDP_Analyzer `
  --add-data "lldp;lldp" `
  --add-data "ui;ui" `
  --add-data "lldp_icon.ico;." `
  --add-data "lldp_icon.png;." `
  --hidden-import scapy.all `
  --hidden-import dpkt `
  --hidden-import psutil `
  --hidden-import PyQt6.QtCore `
  --hidden-import PyQt6.QtGui `
  --hidden-import PyQt6.QtWidgets `
  --icon lldp_icon.ico `
  main_pro.py
```

构建产物会输出到 `dist/`。`build/`、`dist/`、`*.spec`、`*.exe` 默认不进入 Git。

## 项目结构

```text
lldp/                 LLDP/CDP 解析、抓包、平台适配、端口推断
ui/                   PyQt6 专业界面
tests/                单元测试
docs/                 保留的工程文档
main_pro.py           图形界面入口
macos_network_check.py macOS 网络抓包诊断工具
requirements.txt      运行依赖
requirements-test.txt 测试依赖
```

## 开发说明

- `lldp.port_profile` 是端口语义推断核心
- `lldp.capture_dpkt.HybridCapture` 是当前 UI 使用的抓包实现
- `lldp.interface_scanner` 负责跨平台网络接口枚举
- `lldp.view_model` 负责把协议模型转换为 UI 展示模型

## 许可证

MIT License
