"""
LLDP Analyzer - Ultra Optimized Build Script
超级优化构建：目标体积 < 40MB
"""
import subprocess
import os

def clean_build():
    """清理构建文件"""
    import shutil
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    print("✅ 清理完成")

def build_ultra_optimized():
    """构建超级优化版本"""

    # 超级优化参数
    cmd = [
        "python -m PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--strip",                         # 移除调试符号
        "--optimize=2",                    # Python优化
        "--name=LLDP_Analyzer_Ultra",

        # 🚫 排除大体积模块
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=scipy",
        "--exclude-module=PIL",
        "--exclude-module=test",
        "--exclude-module=unittest",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=pydoc",
        "--exclude-module=doctest",
        "--exclude-module=argparse",
        "--exclude-module=traceback",

        # 🔍 隐式导入优化
        "--hidden-import=scapy",
        "--hidden-import=dpkt",
        "--hidden-import=pcapy",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",

        # 📦 数据文件
        "--add-data=lldp;lldp",
        "--add-data=ui;ui",

        # 🎨 图标
        "--icon=lldp_icon.ico",

        # 🎯 主程序
        "main_pro.py"
    ]

    build_cmd = " ".join(cmd)

    print("🔨 开始超级优化构建...")
    print(f"构建命令: {build_cmd}\n")

    try:
        result = subprocess.run(build_cmd, shell=True, check=True,
                              capture_output=False, text=True)
        print("\n✅ 超级优化构建成功！")

        # 检查结果
        exe_path = "dist/LLDP_Analyzer_Ultra.exe"
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n📊 构建结果:")
            print(f"   文件: {exe_path}")
            print(f"   大小: {size_mb:.1f} MB")

            if size_mb < 40:
                print(f"   🎉 体积优化优秀！")
            elif size_mb < 50:
                print(f"   ✅ 体积优化良好")
            else:
                print(f"   ⚠️  体积仍有优化空间")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        return False

def analyze_dependencies():
    """分析依赖关系，找出大体积模块"""
    print("\n🔍 分析依赖关系...")

    try:
        # 检查主要依赖
        result = subprocess.run(
            ["pip", "list", "--format=freeze"],
            capture_output=True, text=True, check=True
        )

        # 找出大体积包
        big_packages = []
        for line in result.stdout.split('\n'):
            if any(pkg in line.lower() for pkg in ['pyqt6', 'scapy', 'numpy', 'pandas', 'matplotlib']):
                big_packages.append(line)

        print("\n📦 检测到的大体积依赖:")
        for pkg in big_packages:
            print(f"   {pkg}")

    except Exception as e:
        print(f"⚠️ 依赖分析失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("LLDP Analyzer - 超级优化构建")
    print("目标: 体积 < 40MB + 图标集成")
    print("=" * 60)

    # 分析依赖
    analyze_dependencies()

    # 清理旧构建
    print("\n🧹 清理旧构建文件...")
    clean_build()

    # 构建超级优化版本
    success = build_ultra_optimized()

    if success:
        print("\n" + "=" * 60)
        print("超级优化构建完成！")
        print("=" * 60)
    else:
        print("\n❌ 构建失败")
