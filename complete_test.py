#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete test with real LLDP capture and debug output
Run this to verify UI and capture are working correctly
"""

import sys
import os

# Add path
sys.path.insert(0, "d:/nanopi/yunwei/lldp_analyzer")

print("="*70)
print("LLDP Network Analyzer - Complete Test")
print("="*70)

print("\n[TEST 1] Importing modules...")

try:
    from PyQt6.QtWidgets import QApplication
    from ui.pro_window import LLDPProfessionalWindow
    from lldp import LLDPCaptureListener
    from lldp.model import LLDPDevice
    print("[OK] PyQt6 and LLDP modules imported")
except ImportError as e:
    print(f"[FAIL] Import error: {e}")
    sys.exit(1)

print("\n[TEST 2] Checking Scapy...")

try:
    from scapy.all import get_working_ifaces
    print("[OK] Scapy available")

    # List interfaces
    print("\n[INFO] Available network interfaces:")
    count = 0
    selected = None
    for iface in get_working_ifaces():
        desc = iface.description.lower()
        if "ethernet" in desc and "virtual" not in desc:
            print(f"  [{count}] {iface.description}")
            if selected is None:
                selected = iface
            count += 1

    if selected:
        print(f"\n[INFO] Auto-selected: {selected.description}")
    else:
        print("[WARNING] No physical interface found!")
        sys.exit(1)

except Exception as e:
    print(f"[FAIL] Scapy error: {e}")
    sys.exit(1)

print("\n[TEST 3] Creating UI window...")

app = QApplication(sys.argv)
window = LLDPProfessionalWindow()
window.show()

print("[OK] UI window shown")

# Auto-start capture after 2 seconds
def auto_capture():
    print("\n[TEST 4] Auto-starting capture in 2 seconds...")
    print("="*70)

    def start_real_capture():
        print("\n[CAPTURE] Starting LLDP capture...")
        print(f"[CAPTURE] Interface: {selected.description}")
        print("[CAPTURE] Duration: 30 seconds")
        print("="*70)

        # Simulate button click
        window.start_btn.click()

    QTimer.singleShot(2000, start_real_capture)

from PyQt6.QtCore import QTimer
QTimer.singleShot(100, auto_capture)

print("\n[INFO] UI is now running...")
print("[INFO] Capture will start automatically in 2 seconds")
print("[INFO] Watch the console for debug output")
print("[INFO] Watch the UI for device information")
print("\n" + "="*70)
print("Press Ctrl+C to stop")
print("="*70 + "\n")

sys.exit(app.exec())
