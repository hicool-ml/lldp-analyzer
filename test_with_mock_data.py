#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLDP Analyzer with Mock Data - Test UI without network
"""

import sys
sys.path.insert(0, "d:/nanopi/yunwei/lldp_analyzer")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.pro_window import LLDPProfessionalWindow
from lldp.model import (
    LLDPDevice, LLDPChassisID, LLDPPortID,
    ChassisIDType, PortIDType, VLANInfo
)

print("="*70)
print("LLDP Analyzer - Mock Data Test")
print("="*70)

app = QApplication(sys.argv)
window = LLDPProfessionalWindow()
window.show()

print("[INFO] Window opened")
print("[INFO] Will inject mock LLDP device in 3 seconds...")

def inject_mock_data():
    print("\n" + "="*70)
    print("[MOCK] Injecting simulated LLDP device...")
    print("="*70)

    # Create realistic LLDP device
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
    device.system_description = "Ruijie S2910-24GT4XS-L Gigabit Ethernet Switch"
    device.port_description = "Uplink Port to Core"
    device.management_ip = "192.168.1.1"
    device.port_vlan = VLANInfo(vlan_id=2011, tagged=False)

    print(f"[MOCK] Device: {device.get_display_name()}")
    print(f"[MOCK] Chassis ID: {device.chassis_id.value}")
    print(f"[MOCK] Port ID: {device.port_id.value}")
    print(f"[MOCK] System Name: {device.system_name}")
    print(f"[MOCK] Management IP: {device.management_ip}")
    print(f"[MOCK] VLAN: {device.port_vlan.vlan_id}")
    print("="*70 + "\n")

    # Inject into UI
    window.on_device_discovered(device)

    print("[SUCCESS] Mock data injected!")
    print("[INFO] Check the UI - it should show device information")
    print("[INFO] Close window to exit\n")

QTimer.singleShot(3000, inject_mock_data)

print("[INFO] Waiting 3 seconds...\n")
sys.exit(app.exec())
