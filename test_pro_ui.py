#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test PyQt6 UI
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
    from ui.pro_window import LLDPProfessionalWindow
    from lldp.model import LLDPDevice, LLDPChassisID, LLDPPortID, ChassisIDType, PortIDType, PoEInfo, VLANInfo, DeviceCapabilities

    print("[OK] PyQt6 imported successfully")
    print("[OK] UI modules imported")

    # Create test device
    device = LLDPDevice(
        chassis_id=LLDPChassisID(
            value="C0:B8:E6:3E:3B:FC",
            type=ChassisIDType.MAC_ADDRESS
        ),
        port_id=LLDPPortID(
            value="GigabitEthernet 0/11",
            type=PortIDType.INTERFACE_NAME
        ),
        system_name="Ruijie S2910-24GT4XS-L",
        system_description="Ruijie Full Gigabit Security Switch",
        management_ip="192.168.1.1",
        port_description="Uplink to Core Switch",
        port_vlan=VLANInfo(vlan_id=2011, tagged=False),
        poe=PoEInfo(supported=True, power_class="Class 0"),
    )

    device.capabilities = DeviceCapabilities(bridge=True)

    print("[OK] Test device created")
    print(f"     System: {device.system_name}")
    print(f"     MAC: {device.chassis_id.value}")
    print(f"     IP: {device.management_ip}")
    print(f"     Port: {device.port_id.value}")
    print(f"     VLAN: {device.port_vlan.vlan_id}")

    # Launch UI with test data
    app = QApplication(sys.argv)
    window = LLDPProfessionalWindow()
    window.show()

    # Load test data after 1 second
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(1000, lambda: window.update_device_display(device))

    sys.exit(app.exec())

except ImportError as e:
    print(f"[FAIL] Import error: {e}")
    print("\nPlease install PyQt6:")
    print("  pip install PyQt6")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
