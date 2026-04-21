"""
LLDP Network Analyzer - Professional UI Entry Point
Modern PyQt6-based interface with CDP Support!
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.pro_window import main as pro_main

if __name__ == "__main__":
    # 启动主程序
    pro_main()
