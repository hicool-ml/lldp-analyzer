#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct UI update test - no QTimer
"""

import sys

sys.path.insert(0, "d:/nanopi/yunwei/lldp_analyzer")

from PyQt6.QtWidgets import QApplication
from ui.pro_window import LLDPProfessionalWindow
from lldp.model import LLDPDevice, LLDPChassisID, LLDPPortID, ChassisIDType, PortIDType
from PyQt6.QtCore import QTimer

print("[TEST] Creating application...")
app = QApplication(sys.argv)

print("[TEST] Creating window...")
window = LLDPProfessionalWindow()
window.show()

# Test device
device = LLDPDevice()
device.chassis_id = LLDPChassisID(
    value="c0:b8:e6:3e:3b:fc",
    type=ChassisIDType.MAC_ADDRESS
)
device.port_id = LLDPPortID(
    value="GigabitEthernet0/11",
    type=PortIDType.INTERFACE_NAME
)
device.system_name = "Ruijie Switch"
device.management_ip = "192.168.1.1"

print(f"[TEST] Test device: {device.get_display_name()}")

# Direct update after 2 seconds (no QTimer.singleShot)
def test_direct_update():
    print("[TEST] Direct UI update...")

    # Direct label update
    window.sw_name.setText("Ruijie Switch")
    window.sw_mac.setText("c0:b8:e6:3e:3b:fc")
    window.sw_ip.setText("192.168.1.1")
    window.port_id.setText("GigabitEthernet0/11")

    print("[TEST] UI updated directly")
    print(f"[TEST] sw_name text: {window.sw_name.text()}")
    print(f"[TEST] sw_mac text: {window.sw_mac.text()}")

QTimer.singleShot(2000, test_direct_update)

print("[TEST] Window should update in 2 seconds...")
print("[TEST] Close window to exit\n")

sys.exit(app.exec())
