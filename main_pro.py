"""
LLDP Network Analyzer - Professional UI Entry Point
Modern PyQt6-based interface with CDP Support!
Cross-platform support for Windows, macOS, and Linux
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.pro_window import main as pro_main


def check_platform_requirements():
    """Check platform-specific requirements before starting"""
    try:
        from lldp.platform import get_platform_config, is_macos

        config = get_platform_config()

        # Print platform info for debugging
        print(f"Platform: {config.os_type.value}")
        print(f"Admin privileges: {config.is_admin}")
        print(f"Python: {sys.version}")

        # Check if Scapy is available
        supported, message = config.check_scapy_support()
        if not supported:
            print(f"❌ Scapy support check failed: {message}")
            if is_macos():
                print(f"\n{config.get_permission_instructions()}")
            return False
        else:
            print(f"✅ {message}")

        return True

    except Exception as e:
        print(f"⚠️ Platform check warning: {e}")
        return True  # Continue anyway


if __name__ == "__main__":
    # 检查平台要求
    if check_platform_requirements():
        # 启动主程序
        pro_main()
    else:
        print("\n❌ 平台检查失败，请解决上述问题后重试")
        sys.exit(1)
