#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real LLDP capture test with full debug output
Run this to test actual LLDP packet capture
"""

import sys
import time

# Add path
sys.path.insert(0, "d:/nanopi/yunwei/lldp_analyzer")

print("="*70)
print("LLDP Network Analyzer - Real Capture Test")
print("="*70)

# Import
try:
    from PyQt6.QtWidgets import QApplication
    from lldp import LLDPCaptureListener
    from ui.pro_window import LLDPProfessionalWindow
    from scapy.all import get_working_ifaces
    print("[OK] All modules imported")
except ImportError as e:
    print(f"[FAIL] Import error: {e}")
    sys.exit(1)

# Select interface
print("\n[STEP 1] Selecting network interface...")
try:
    selected = None
    for iface in get_working_ifaces():
        desc = iface.description.lower()
        if "ethernet" in desc and "virtual" not in desc:
            selected = iface
            print(f"[OK] Selected: {iface.description}")
            break

    if not selected:
        print("[FAIL] No physical interface found!")
        sys.exit(1)

except Exception as e:
    print(f"[FAIL] Interface error: {e}")
    sys.exit(1)

# Create UI
print("\n[STEP 2] Creating UI window...")
app = QApplication(sys.argv)
window = LLDPProfessionalWindow()
window.show()
print("[OK] UI created and shown")

# Show initial state
print("\n[STEP 3] Showing initial state...")
window.show_initial_state()

# Callback
devices_found = []

def on_device(device):
    """Called when device discovered"""
    print(f"\n{'='*70}")
    print(f"[CAPTURE] ✓ Device discovered!")
    print(f"{'='*70}")
    print(f"  Name: {device.get_display_name()}")
    print(f"  Chassis: {device.chassis_id.value if device.chassis_id else 'N/A'}")
    print(f"  Port: {device.port_id.value if device.port_id else 'N/A'}")
    print(f"  SysName: {device.system_name}")
    print(f"  MgmtIP: {device.management_ip}")
    print(f"  VLAN: {device.port_vlan.vlan_id if device.port_vlan else 'N/A'}")
    print(f"  PoE: {device.poe.power_class if device.poe and device.poe.supported else 'N/A'}")
    print(f"{'='*70}\n")

    # Update UI
    print("[UI] Updating display...")
    window.update_device_display(device)
    print("[UI] Display updated")

    devices_found.append(device)
    window.device_count_label.setText(f"已发现: {len(devices_found)} 台设备")

def on_complete(devices):
    """Called when capture completes"""
    print(f"\n[COMPLETE] Capture finished!")
    print(f"  Total devices found: {len(devices)}")
    print(f"{'='*70}\n")

    window.capture_complete_update()

# Auto-start capture after 3 seconds
def auto_start():
    print("\n[STEP 4] Auto-starting capture in 3 seconds...")
    print("="*70)

    def start():
        print("\n[CAPTURE] Starting LLDP capture...")
        print(f"[CAPTURE] Interface: {selected.description}")
        print(f"[CAPTURE] Duration: 30 seconds")
        print(f"[CAPTURE] Listening for LLDP packets (0x88CC)...")
        print("="*70 + "\n")

        try:
            window.listener = LLDPCaptureListener()
            window.listener.start(
                interface=selected,
                duration=30,
                on_device_discovered=on_device,
                on_capture_complete=on_complete
            )
            print("[CAPTURE] Listener started - Waiting for LLDP packets...")
        except Exception as e:
            print(f"[ERROR] Capture failed: {e}")
            import traceback
            traceback.print_exc()

    from PyQt6.QtCore import QTimer
    QTimer.singleShot(3000, start)

from PyQt6.QtCore import QTimer
QTimer.singleShot(2000, auto_start)

print("\n[INFO] UI is running...")
print("[INFO] Capture will auto-start in 3 seconds")
print("[INFO] Watch console for capture progress")
print("[INFO] Close the window to exit\n")

sys.exit(app.exec())
