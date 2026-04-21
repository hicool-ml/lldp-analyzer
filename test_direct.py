#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct test of PyQt6 UI with simulated data
"""

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

# Add path
sys.path.insert(0, "d:/nanopi/yunwei/lldp_analyzer")

from ui.pro_window import LLDPProfessionalWindow
from lldp.model import (
    LLDPDevice, LLDPChassisID, LLDPPortID,
    ChassisIDType, PortIDType, PoEInfo,
    VLANInfo, DeviceCapabilities
)


def main():
    print("[TEST] Starting PyQt6 UI with simulated data...")

    app = QApplication(sys.argv)
    window = LLDPProfessionalWindow()
    window.show()

    # Simulate capture sequence
    def test_sequence():
        print("[TEST] 1. Showing initial state...")
        window.show_initial_state()

        # After 2 seconds, simulate device discovery
        def simulate_device():
            print("[TEST] 2. Creating test device...")

            # Create device with your actual data
            device = LLDPDevice(
                chassis_id=LLDPChassisID(
                    value="C0:B8:E6:3E:3B:FC",
                    type=ChassisIDType.MAC_ADDRESS
                ),
                port_id=LLDPPortID(
                    value="GigabitEthernet 0/11",
                    type=PortIDType.INTERFACE_NAME
                ),
                system_name="Ruijie",
                system_description="Ruijie Full Gigabit Security Switch",
                management_ip="192.168.1.1",
                port_description="Uplink Port",
                port_vlan=VLANInfo(vlan_id=2011, tagged=False),
                poe=PoEInfo(supported=True, power_class="Class 0"),
            )

            # Enable capabilities
            device.capabilities = DeviceCapabilities(bridge=True)

            print(f"[TEST] Device created: {device.get_display_name()}")
            print(f"[TEST] Chassis ID: {device.chassis_id.value}")
            print(f"[TEST] Port ID: {device.port_id.value}")
            print(f"[TEST] System name: {device.system_name}")

            # Update UI
            print("[TEST] Updating UI...")
            window.update_device_display(device)
            print("[TEST] UI update complete")

        QTimer.singleShot(2000, simulate_device)

    # Start test sequence
    QTimer.singleShot(500, test_sequence)

    print("[TEST] UI launched, waiting for user interaction...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
