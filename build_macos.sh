#!/bin/bash
# 🍎 macOS M芯片构建脚本
# 用于在Apple Silicon (M1/M2/M3/M4) Mac上构建LLDP Analyzer

set -e  # 遇到错误立即退出

echo "=== 🍎 macOS M芯片构建脚本 ==="
echo ""

# 检测系统架构
ARCH=$(uname -m)
echo "检测到架构: $ARCH"

if [[ "$ARCH" == "arm64" ]]; then
    echo "✅ Apple Silicon (M1/M2/M3/M4) 检测成功"
else
    echo "⚠️  警告: 非ARM架构，构建的是Intel版本"
fi

# 检查Python版本
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Python版本: $PYTHON_VERSION"

# 检查是否安装了依赖
echo ""
echo "📦 检查依赖..."

if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo "❌ PyQt6未安装，正在安装..."
    python3 -m pip install PyQt6
else
    echo "✅ PyQt6已安装"
fi

if ! python3 -c "import scapy" 2>/dev/null; then
    echo "❌ Scapy未安装，正在安装..."
    python3 -m pip install scapy
else
    echo "✅ Scapy已安装"
fi

if ! python3 -c "import dpkt" 2>/dev/null; then
    echo "❌ dpkt未安装，正在安装..."
    python3 -m pip install dpkt
else
    echo "✅ dpkt已安装"
fi

# 安装PyInstaller（如需要）
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "❌ PyInstaller未安装，正在安装..."
    python3 -m pip install pyinstaller
else
    echo "✅ PyInstaller已安装"
fi

echo ""
echo "🔨 开始构建macOS应用..."

# 创建macOS特定的spec文件
cat > LLDP_Analyzer_macOS.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main_pro.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('lldp', 'lldp'),
        ('ui', 'ui'),
        ('lldp_icon.png', '.'),
    ],
    hiddenimports=[
        'scapy',
        'dpkt',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'test',
        'IPython',
    ],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LLDP Analyzer v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI应用，无控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LLDP Analyzer v2',
)

# macOS .app bundle
app = BUNDLE(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LLDP Analyzer v2.app',
    icon=None,
    bundle_identifier='com.hicool.lldpanalyzer',
    info_plist={
        'CFBundleName': 'LLDP Analyzer v2',
        'CFBundleDisplayName': 'LLDP Network Analyzer',
        'CFBundleVersion': '2.0.0',
        'CFBundleShortVersionString': '2.0.0',
        'NSHighResolutionCapable': 'True',
        'NSRequiresAquaSystemAppearance': 'False',
        'NSLocalNetworkUsageDescription': '需要访问本地网络以捕获LLDP报文',
        'CFBundleExecutable': 'LLDP Analyzer v2',
    },
)
EOF

# 构建应用
python3 -m PyInstaller --noconfirm LLDP_Analyzer_macOS.spec

echo ""
echo "✅ 构建完成！"
echo ""
echo "📦 构建产物:"
echo "  - dist/LLDP Analyzer v2.app (macOS应用包)"
echo "  - dist/LLDP Analyzer v2 (应用内容)"
echo ""
echo "🚀 运行应用:"
echo "  open 'dist/LLDP Analyzer v2.app'"
echo ""
echo "🔐 以管理员权限运行:"
echo "  sudo 'dist/LLDP Analyzer v2.app/Contents/MacOS/LLDP Analyzer v2'"
echo ""
echo "⚠️  重要提示:"
echo "  1. 首次运行需要授予网络访问权限"
echo "  2. 可能需要设置BPF设备权限: sudo chmod 777 /dev/bpf*"
echo "  3. MacBook用户建议使用USB以太网适配器"
echo "  4. Mac mini用户可直接使用内置以太网"
echo ""

# 询问是否立即运行
read -p "是否立即运行应用？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "正在启动应用..."
    if [ -e "dist/LLDP Analyzer v2.app" ]; then
        open "dist/LLDP Analyzer v2.app"
    else
        echo "❌ 找不到构建的应用"
    fi
fi

echo "=== 构建脚本完成 ==="
