#!/usr/bin/env python3
"""
Build script for LLDP Network Analyzer
Creates standalone executables
"""

import os
import sys
import subprocess
from pathlib import Path


def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def install_pyinstaller():
    """Install PyInstaller"""
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build_gui_exe():
    """Build Windows GUI EXE"""
    print("\n" + "="*70)
    print("Building LLDP Network Analyzer - GUI")
    print("="*70 + "\n")

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=LLDP_Analyzer_GUI",
        "--icon=NONE",
        "--hidden-import=scapy.all",
        "--hidden-import=scapy.layers.l2",
        "--noconfirm",
        "main_gui.py"
    ]

    print(f"Running: {' '.join(cmd)}\n")

    subprocess.check_call(cmd)

    print("\n✅ GUI EXE built successfully!")
    print("Location: dist/LLDP_Analyzer_GUI.exe")


def build_cli_exe():
    """Build CLI EXE"""
    print("\n" + "="*70)
    print("Building LLDP Network Analyzer - CLI")
    print("="*70 + "\n")

    cmd = [
        "pyinstaller",
        "--onefile",
        "--name=lldp-analyzer",
        "--hidden-import=scapy.all",
        "--hidden-import=scapy.layers.l2",
        "--noconfirm",
        "main.py"
    ]

    print(f"Running: {' '.join(cmd)}\n")

    subprocess.check_call(cmd)

    print("\n✅ CLI EXE built successfully!")
    print("Location: dist/lldp-analyzer.exe")


def build_portable_package():
    """Create portable package with both EXEs"""
    print("\n" + "="*70)
    print("Creating Portable Package")
    print("="*70 + "\n")

    # Check if EXEs exist
    gui_exe = Path("dist/LLDP_Analyzer_GUI.exe")
    cli_exe = Path("dist/lldp-analyzer.exe")

    if not gui_exe.exists() or not cli_exe.exists():
        print("❌ EXEs not found. Please build first.")
        return

    # Create portable directory
    portable_dir = Path("LLDP_Analyzer_Portable")
    portable_dir.mkdir(exist_ok=True)

    # Copy EXEs
    import shutil
    shutil.copy2(gui_exe, portable_dir / "LLDP_Analyzer_GUI.exe")
    shutil.copy2(cli_exe, portable_dir / "lldp-analyzer.exe")

    # Copy README
    if Path("README.md").exists():
        shutil.copy2("README.md", portable_dir / "README.md")

    # Create quick start guide
    quick_start = """LLDP Network Analyzer - Portable Package
========================================

Quick Start:

GUI Mode:
  Double-click: LLDP_Analyzer_GUI.exe

CLI Mode:
  Double-click: lldp-analyzer.exe
  Or run from command line for options

Requirements:
  - Windows 7/10/11 (64-bit)
  - Npcap driver (https://npcap.com/)

Features:
  - Real-time LLDP device discovery
  - Export to JSON/CSV/XML
  - Professional architecture
  - Thread-safe capture

For more information, see README.md
"""
    (portable_dir / "快速开始.txt").write_text(quick_start, encoding='utf-8')

    print("✅ Portable package created!")
    print(f"Location: {portable_dir}/")


def main():
    """Main build function"""
    print("\n" + "="*70)
    print("LLDP Network Analyzer - Build Script")
    print("="*70)

    # Check PyInstaller
    if not check_pyinstaller():
        print("\n⚠️  PyInstaller not found.")
        install = input("Install PyInstaller now? (y/n): ").lower()
        if install == 'y':
            install_pyinstaller()
        else:
            print("❌ Cannot build without PyInstaller.")
            sys.exit(1)

    # Build options
    print("\nBuild Options:")
    print("1. Build GUI EXE")
    print("2. Build CLI EXE")
    print("3. Build Both")
    print("4. Create Portable Package")
    print("5. All (Build + Package)")

    choice = input("\nSelect option (1-5): ").strip()

    if choice == '1':
        build_gui_exe()
    elif choice == '2':
        build_cli_exe()
    elif choice == '3':
        build_gui_exe()
        build_cli_exe()
    elif choice == '4':
        build_portable_package()
    elif choice == '5':
        build_gui_exe()
        build_cli_exe()
        build_portable_package()
    else:
        print("❌ Invalid choice.")
        sys.exit(1)

    print("\n" + "="*70)
    print("✅ Build Complete!")
    print("="*70)


if __name__ == "__main__":
    main()
