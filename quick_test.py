#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick LLDP test with 10 second capture
"""

import sys

sys.path.insert(0, "d:/nanopi/yunwei/lldp_analyzer")

from PyQt6.QtWidgets import QApplication
from ui.pro_window import LLDPProfessionalWindow
from scapy.all import get_working_ifaces

print("[TEST] Starting...")

app = QApplication(sys.argv)
window = LLDPProfessionalWindow()
window.show()

# Select interface
selected = None
for iface in get_working_ifaces():
    desc = iface.description.lower()
    if "ethernet" in desc and "virtual" not in desc:
        selected = iface
        print(f"[TEST] Selected: {iface.description}")
        break

if not selected:
    print("[ERROR] No interface found")
    sys.exit(1)

# Auto-start capture after 2 seconds
def start_capture():
    print("[TEST] Starting 10-second capture...")
    window.listener.start(
        interface=selected,
        duration=10,
        on_device_discovered=window.on_device_discovered,
        on_capture_complete=lambda devs: print(f"[TEST] Capture complete! Found {len(devs)} devices")
    )

from PyQt6.QtCore import QTimer
QTimer.singleShot(2000, start_capture)

print("[TEST] Close window to exit\n")
sys.exit(app.exec())
