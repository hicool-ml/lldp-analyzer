"""
LLDP Analyzer - Optimized Build Script
优化构建脚本：减小体积 + 正确集成图标
"""
import subprocess
import os
import sys

def build_optimized_exe():
    """构建优化的exe文件"""

    # 图标路径（使用正确的图标文件）
    icon_path = "lldp_analyzer/lldp_icon.ico"

    # 检查图标文件是否存在
    if not os.path.exists(icon_path):
        print(f"❌ 图标文件不存在: {icon_path}")
        print("使用默认图标...")
        icon_option = ""
    else:
        print(f"✅ 找到图标文件: {icon_path}")
        icon_option = f"--icon={icon_path}"

    # PyInstaller优化参数
    pyinstaller_args = [
        "python -m PyInstaller",
        "--noconfirm",                    # 覆盖现有构建
        "--onefile",                      # 单文件exe
        "--windowed",                     # 无控制台窗口
        "--name=LLDP_Analyzer",           # 输出文件名

        # 🔧 体积优化选项
        "--strip",                        # 移除调试符号
        "--noupx",                        # 禁用UPX压缩（避免兼容性问题）
        "--optimize=2",                   # Python优化级别

        # 🚫 排除不必要的模块（显著减小体积）
        "--exclude-module=tkinter",       # 排除tkinter
        "--exclude-module=matplotlib",    # 排除matplotlib
        "--exclude-module=numpy",         # 排除numpy
        "--exclude-module=pandas",        # 排除pandas
        "--exclude-module=scipy",         # 排除scipy
        "--exclude-module=PIL",           # 排除PIL（不使用图像处理）
        "--exclude-module=test",          # 排除测试模块
        "--exclude-module=unittest",      # 排除单元测试
        "--exclude-module=IPython",       # 排除IPython
        "--exclude-module=jupyter",       # 排除Jupyter

        # 📦 包含数据和代码
        "--add-data=lldp;lldp",           # LLDP模块
        "--add-data=ui;ui",               # UI模块

        # 🔍 关键导入（确保包含）
        "--hidden-import=scapy",
        "--hidden-import=scapy.all",
        "--hidden-import=dpkt",
        "--hidden-import=pcapy",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",

        # 📋 图标设置
        icon_option,

        # 🎯 主程序
        "main_pro.py"
    ]

    # 构建命令
    build_cmd = " ".join(pyinstaller_args)
    print(f"\n🔨 构建命令:")
    print(f"{build_cmd}\n")

    # 执行构建
    try:
        result = subprocess.run(build_cmd, shell=True, check=True,
                              capture_output=False, text=True)
        print("\n✅ 构建成功！")

        # 检查生成的文件大小
        exe_path = "dist/LLDP_Analyzer.exe"
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n📊 构建结果:")
            print(f"   文件: {exe_path}")
            print(f"   大小: {size_mb:.1f} MB")

            if size_mb < 50:
                print(f"   ✅ 体积优化成功！")
            elif size_mb < 70:
                print(f"   ✅ 体积可接受")
            else:
                print(f"   ⚠️  体积仍较大，可考虑进一步优化")

        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 构建失败: {e}")
        return False

def build_with_upx():
    """使用UPX压缩构建更小的exe"""
    print("\n🚀 尝试使用UPX压缩...")

    # 首先检查UPX是否可用
    try:
        subprocess.run(["upx", "--version"], capture_output=True, check=True)
        print("✅ UPX可用")
        upx_available = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ UPX不可用，跳过压缩")
        upx_available = False

    if upx_available:
        # 使用UPX压缩
        pyinstaller_args = [
            "python -m PyInstaller",
            "--noconfirm",
            "--onefile",
            "--windowed",
            "--name=LLDP_Analyzer_Min",
            "--strip",
            "--upx-dir=upx",                # 启用UPX压缩
            "--exclude-module=tkinter",
            "--exclude-module=matplotlib",
            "--exclude-module=numpy",
            "--exclude-module=pandas",
            "--add-data=lldp;lldp",
            "--add-data=ui;ui",
            "--hidden-import=scapy",
            "--hidden-import=dpkt",
            "--hidden-import=pcapy",
            "--hidden-import=PyQt6",
            f"--icon=lldp_analyzer/lldp_icon.ico" if os.path.exists("lldp_analyzer/lldp_icon.ico") else "",
            "main_pro.py"
        ]

        build_cmd = " ".join([arg for arg in pyinstaller_args if arg])
        try:
            subprocess.run(build_cmd, shell=True, check=True)
            print("\n✅ UPX压缩构建成功！")

            # 检查压缩后的大小
            exe_path = "dist/LLDP_Analyzer_Min.exe"
            if os.path.exists(exe_path):
                size_mb = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"\n📊 UPX压缩结果:")
                print(f"   文件: {exe_path}")
                print(f"   大小: {size_mb:.1f} MB")

            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ UPX构建失败: {e}")
            return False

    return False

if __name__ == "__main__":
    print("=" * 60)
    print("LLDP Analyzer - 优化构建")
    print("=" * 60)

    # 标准优化构建
    print("\n📦 开始标准优化构建...")
    success = build_optimized_exe()

    if success:
        print("\n" + "=" * 60)
        print("构建完成！文件位于 dist/ 目录")
        print("=" * 60)

        # 询问是否尝试UPX压缩
        try:
            response = input("\n是否尝试UPX压缩以进一步减小体积？(y/n): ").strip().lower()
            if response == 'y':
                build_with_upx()
        except:
            print("跳过UPX压缩")
    else:
        print("\n❌ 构建失败，请检查错误信息")
        sys.exit(1)
