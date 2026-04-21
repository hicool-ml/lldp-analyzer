#!/usr/bin/env python3
"""
Build script for PyQt6 Professional UI
Creates standalone EXE with modern interface
"""

import os
import sys
import subprocess


def check_pyqt6():
    """Check if PyQt6 is installed"""
    try:
        import PyQt6
        print("[OK] PyQt6 found")
        return True
    except ImportError:
        print("[ERROR] PyQt6 not found!")
        print("Install with: pip install PyQt6")
        return False


def build_pro_gui():
    """Build PyQt6 GUI EXE"""
    print("\n" + "="*70)
    print("Building LLDP Network Analyzer - Professional UI (PyQt6)")
    print("="*70 + "\n")

    if not check_pyqt6():
        return False

    # PyInstaller command for PyQt6
    cmd = [
        "python", "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=LLDP_Analyzer_Pro",
        "--hidden-import=scapy.all",
        "--hidden-import=scapy.layers.l2",
        "--hidden-import=PyQt6",
        "--collect-all=PyQt6",
        "--noconfirm",
        "main_pro.py"
    ]

    print(f"[CMD] {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True
        )

        if result.returncode == 0:
            print("\n" + "="*70)
            print("[SUCCESS] Build completed!")
            print("="*70)
            print("\n[INFO] Output file: dist/LLDP_Analyzer_Pro.exe")

            # Get file size
            exe_path = "dist/LLDP_Analyzer_Pro.exe"
            if os.path.exists(exe_path):
                size_mb = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"[INFO] File size: {size_mb:.1f} MB")

            return True
        else:
            print("[ERROR] Build failed!")
            return False

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] PyInstaller failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Build error: {e}")
        return False


def main():
    """Main build function"""
    print("="*70)
    print("LLDP Network Analyzer - Professional Build")
    print("="*70)

    success = build_pro_gui()

    if success:
        print("\n[INFO] You can now run:")
        print("  python main_pro.py")
        print("  Or use the EXE: dist/LLDP_Analyzer_Pro.exe")
        print()
    else:
        print("\n[ERROR] Build failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
