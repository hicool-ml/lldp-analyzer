"""
CLI Interface for LLDP Network Analyzer
"""

import sys
import json
import time
from datetime import datetime
from typing import List, Optional

from lldp import LLDPParser, LLDPCaptureListener
from lldp.model import LLDPDevice


class LLDPCLI:
    """
    Command-line interface for LLDP discovery
    """

    def __init__(self):
        """Initialize CLI"""
        self.listener = LLDPCaptureListener()

    def discover(self, interface: str, duration: int = 30,
                 output_format: str = "table") -> List[LLDPDevice]:
        """
        Discover LLDP devices

        Args:
            interface: Network interface name
            duration: Capture duration in seconds
            output_format: Output format (table/json/csv)

        Returns:
            List of discovered devices
        """
        print(f"╔════════════════════════════════════════════════════════════════════╗")
        print(f"║           LLDP Network Analyzer - CLI v1.0.0                        ║")
        print(f"╚════════════════════════════════════════════════════════════════════╝")
        print()
        print(f"Interface: {interface}")
        print(f"Duration: {duration} seconds")
        print(f"Output Format: {output_format}")
        print()
        print(f"Starting capture...")
        print(f"─" * 70)

        devices = []
        last_device_count = 0

        def on_device(device: LLDPDevice):
            """Callback when device discovered"""
            nonlocal last_device_count
            last_device_count += 1

            print(f"[{last_device_count}] Discovered: {device.get_display_name()}")

            if device.system_name:
                print(f"    System: {device.system_name}")
            if device.management_ip:
                print(f"    IP: {device.management_ip}")
            if device.port_vlan:
                print(f"    VLAN: {device.port_vlan.vlan_id}")
            print()

        def on_complete(all_devices: List[LLDPDevice]):
            """Callback when capture completes"""
            nonlocal devices
            devices = all_devices

        # Start capture
        self.listener.start(
            interface=interface,
            duration=duration,
            on_device_discovered=on_device,
            on_capture_complete=on_complete
        )

        # Wait for completion
        try:
            while self.listener.capture.is_active():
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n⚠️  Capture interrupted by user")
            self.listener.stop()

        # Display results
        print()
        print(f"─" * 70)
        print(f"Capture complete. Discovered {len(devices)} device(s).")
        print()

        # Output results
        if output_format == "json":
            self._output_json(devices)
        elif output_format == "csv":
            self._output_csv(devices)
        else:
            self._output_table(devices)

        return devices

    def _output_table(self, devices: List[LLDPDevice]):
        """Output devices in table format"""
        if not devices:
            print("No devices discovered.")
            return

        print()
        print("╔════════════════════════════════════════════════════════════════════╗")
        print("║                        Device Details                              ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print()

        for i, device in enumerate(devices, 1):
            print(f"📋 Device #{i}")
            print(f"─" * 70)

            # Device identification
            if device.chassis_id:
                print(f"设备标识: {device.chassis_id}")
            if device.system_name:
                print(f"系统名称: {device.system_name}")
            if device.system_description:
                desc = device.system_description
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                print(f"系统描述: {desc}")

            # Port information
            if device.port_id:
                print(f"端口标识: {device.port_id}")
            if device.port_description:
                print(f"端口描述: {device.port_description}")

            # Network configuration
            if device.management_ip:
                print(f"管理地址: {device.management_ip}")
            if device.port_vlan:
                print(f"端口VLAN: {device.port_vlan.vlan_id}")

            # PoE
            if device.poe.supported:
                print(f"PoE: 支持 ({device.poe.power_class})")

            # Capabilities
            caps = device.capabilities.get_enabled_capabilities()
            if caps:
                print(f"能力: {', '.join(caps)}")

            print()

    def _output_json(self, devices: List[LLDPDevice]):
        """Output devices in JSON format"""
        output = {
            "timestamp": datetime.now().isoformat(),
            "device_count": len(devices),
            "devices": [device.to_dict() for device in devices]
        }

        print(json.dumps(output, indent=2, ensure_ascii=False))

    def _output_csv(self, devices: List[LLDPDevice]):
        """Output devices in CSV format"""
        if not devices:
            return

        # CSV header
        print("system_name,chassis_id,port_id,management_ip,vlan,poe")

        # CSV rows
        for device in devices:
            name = device.system_name or "Unknown"
            chassis = device.chassis_id.value if device.chassis_id else ""
            port = device.port_id.value if device.port_id else ""
            ip = device.management_ip or ""
            vlan = str(device.port_vlan.vlan_id) if device.port_vlan else ""
            poe = "Yes" if device.poe.supported else "No"

            print(f'"{name}","{chassis}","{port}","{ip}","{vlan}","{poe}"')


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="LLDP Network Analyzer - Discover LLDP devices on your network"
    )

    parser.add_argument(
        "-i", "--interface",
        help="Network interface to use",
        default=None
    )

    parser.add_argument(
        "-d", "--duration",
        type=int,
        help="Capture duration in seconds",
        default=30
    )

    parser.add_argument(
        "-f", "--format",
        choices=["table", "json", "csv"],
        help="Output format",
        default="table"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output file (JSON/CSV only)",
        default=None
    )

    parser.add_argument(
        "--list-interfaces",
        action="store_true",
        help="List available interfaces"
    )

    args = parser.parse_args()

    # List interfaces
    if args.list_interfaces:
        try:
            from scapy.all import get_working_ifaces

            print("Available interfaces:")
            for iface in get_working_ifaces():
                print(f"  - {iface.name}: {iface.description}")

        except Exception as e:
            print(f"Error listing interfaces: {e}")
            sys.exit(1)

        sys.exit(0)

    # Auto-detect interface
    interface = args.interface
    if not interface:
        try:
            from scapy.all import get_working_ifaces

            for iface in get_working_ifaces():
                desc = iface.description.lower()
                if "ethernet" in desc and "virtual" not in desc:
                    interface = iface
                    break

            if not interface:
                print("Error: Could not auto-detect interface. Use -i to specify.")
                sys.exit(1)

        except Exception as e:
            print(f"Error detecting interface: {e}")
            sys.exit(1)

    # Run discovery
    cli = LLDPCLI()

    # Capture output if needed
    if args.output:
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

    devices = cli.discover(
        interface=interface,
        duration=args.duration,
        output_format=args.format
    )

    # Save to file if requested
    if args.output:
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)

        print(f"Output saved to: {args.output}")

    # Exit code
    sys.exit(0 if devices else 1)


if __name__ == "__main__":
    main()
