#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulated LLDP discovery test - no network needed
"""

import sys

sys.path.insert(0, "d:/nanopi/yunwei/lldp_analyzer")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.pro_window import LLDPProfessionalWindow
from lldp.model import LLDPDevice, LLDPChassisID, LLDPPortID, ChassisIDType, PortIDType

print("="*70)
print("SIMULATED LLDP DISCOVERY TEST")
print("="*70)

app = QApplication(sys.argv)
window = LLDPProfessionalWindow()
window.show()

print("[INFO] Window opened")
print("[INFO] Will simulate device discovery in 3 seconds...")

def simulate_discovery():
    print("\n" + "="*70)
    print("[SIMULATION] Creating simulated LLDP device...")
    print("="*70)

    # Create a realistic LLDP device
    device = LLDPDevice()
    device.chassis_id = LLDPChassisID(
        value="c0:b8:e6:3e:3b:fc",
        type=ChassisIDType.MAC_ADDRESS
    )
    device.port_id = LLDPPortID(
        value="GigabitEthernet0/11",
        type=PortIDType.INTERFACE_NAME
    )
    device.system_name = "Ruijie_S2910"
    device.system_description = "Ruijie S2910-24GT4XS-L Switch"
    device.port_description = "Uplink Port"
    device.management_ip = "192.168.1.1"

    print(f"[SIMULATION] Device created: {device.get_display_name()}")
    print(f"[SIMULATION] Chassis ID: {device.chassis_id.value}")
    print(f"[SIMULATION] Port ID: {device.port_id.value}")
    print(f"[SIMULATION] System Name: {device.system_name}")
    print(f"[SIMULATION] Management IP: {device.management_ip}")
    print(f"[SIMULATION] Device is valid: {device.is_valid()}")

    print("\n[SIMULATION] Calling window.on_device_discovered()...")
    print("="*70 + "\n")

    # Call the discovery callback
    try:
        window.on_device_discovered(device)
        print("[SUCCESS] Callback completed without exceptions")
    except Exception as e:
        print(f"[ERROR] Callback failed: {e}")
        import traceback
        traceback.print_exc()

QTimer.singleShot(3000, simulate_discovery)

print("\n[INFO] Waiting 3 seconds for simulated discovery...")
print("[INFO] Watch the UI window for changes")
print("[INFO] Close window to exit\n")

sys.exit(app.exec())
