#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test UI callback mechanism
"""

import sys

sys.path.insert(0, "d:/nanopi/yunwei/lldp_analyzer")

print("="*70)
print("UI Callback Mechanism Test")
print("="*70)

from PyQt6.QtWidgets import QApplication
from ui.pro_window import LLDPProfessionalWindow
from lldp.model import LLDPDevice, LLDPChassisID, LLDPPortID, ChassisIDType, PortIDType
from PyQt6.QtCore import QTimer

print("\n[STEP 1] Creating UI...")
app = QApplication(sys.argv)
window = LLDPProfessionalWindow()
window.show()

print("[STEP 2] Creating test device...")

# Create a test device
device = LLDPDevice()
device.chassis_id = LLDPChassisID(
    value="c0:b8:e6:3e:3b:fc",
    type=ChassisIDType.MAC_ADDRESS
)
device.port_id = LLDPPortID(
    value="GigabitEthernet0/11",
    type=PortIDType.INTERFACE_NAME
)
device.system_name = "Test Switch"
device.management_ip = "192.168.1.1"

print(f"[STEP 3] Test device created: {device.get_display_name()}")
print(f"[DEBUG] Device is valid: {device.is_valid()}")

# Test the callback directly
print("[STEP 4] Testing callback directly...")

try:
    window.on_device_discovered(device)
    print("[OK] Callback executed successfully")
except Exception as e:
    print(f"[FAIL] Callback failed: {e}")
    import traceback
    traceback.print_exc()

# Test UI update directly
print("[STEP 5] Testing UI update directly...")

try:
    window.update_device_display(device)
    print("[OK] UI update executed successfully")
except Exception as e:
    print(f"[FAIL] UI update failed: {e}")
    import traceback
    traceback.print_exc()

print("\n[INFO] Check the UI window - it should show device information")
print("[INFO] Close the window to exit\n")

sys.exit(app.exec())
