"""
Debug protocol identification issue
"""
import sys

def test_protocol_detection():
    """Test why Ruijie device is detected as CDP"""
    print("=" * 60)
    print("PROTOCOL IDENTIFICATION DEBUG")
    print("=" * 60)

    try:
        from lldp import LLDPCaptureListener
        from scapy.all import get_working_ifaces, sniff, Ether
        import time

        # Get interface
        print("[1/4] Getting network interface...")
        interfaces = list(get_working_ifaces())

        best_interface = None
        for iface in interfaces:
            desc = iface.description.lower()
            if 'ethernet' in desc or '以太网' in desc:
                if 'wi-fi' not in desc:
                    best_interface = iface
                    break

        if not best_interface:
            best_interface = interfaces[0]

        print(f"[OK] Selected: {best_interface.name}")

        # Capture a few packets to analyze
        print("\n[2/4] Capturing packets for analysis...")

        packets_captured = []

        def packet_handler(pkt):
            """Analyze captured packets"""
            if len(packets_captured) >= 5:  # Only analyze first 5 packets
                return

            try:
                if pkt.haslayer(Ether):
                    eth_layer = pkt[Ether]
                    packet_info = {
                        'dst_mac': eth_layer.dst,
                        'src_mac': eth_layer.src,
                        'ethertype': hex(eth_layer.type) if hasattr(eth_layer, 'type') else 'N/A',
                        'raw_type': getattr(eth_layer, 'type', None)
                    }

                    # Check if it looks like LLDP or CDP
                    if eth_layer.type == 0x88cc:
                        packet_info['suspected_protocol'] = 'LLDP (0x88cc)'
                    elif eth_layer.type == 0x2000:
                        packet_info['suspected_protocol'] = 'CDP (0x2000)'
                    elif eth_layer.dst == '01:00:0c:cc:cc:cc':
                        packet_info['suspected_protocol'] = 'CDP (Cisco multicast)'
                    else:
                        packet_info['suspected_protocol'] = 'Unknown'

                    packets_captured.append(packet_info)
                    print(f"  [PACKET {len(packets_captured)}] {packet_info['suspected_protocol']}")
                    print(f"    - DST MAC: {eth_layer.dst}")
                    print(f"    - EtherType: {packet_info['ethertype']}")

            except Exception as e:
                print(f"  [ERROR] Failed to analyze packet: {e}")

        # Capture packets
        print("  Starting 5-second capture...")
        sniff(
            iface=best_interface.name,
            prn=packet_handler,
            timeout=5,
            store=False
        )

        print(f"\n[OK] Captured {len(packets_captured)} packets")

        # Now test with actual capture
        print("\n[3/4] Testing actual capture with listener...")

        listener = LLDPCaptureListener()
        discovered_devices = []

        def device_callback(device):
            """Device discovery callback with protocol analysis"""
            try:
                device_name = device.get_display_name()
                protocol = getattr(device, 'protocol', 'Unknown')

                print(f"  [DEVICE] {device_name}")
                print(f"    - Protocol: {protocol}")
                print(f"    - Device class: {type(device).__name__}")

                # Check device attributes
                if hasattr(device, 'device_id'):
                    print(f"    - Has device_id: {device.device_id}")
                if hasattr(device, 'port_id'):
                    print(f"    - Has port_id: {device.port_id}")

                discovered_devices.append(device)

            except Exception as e:
                print(f"  [ERROR] Device callback failed: {e}")
                import traceback
                traceback.print_exc()

        listener.start(
            interface=best_interface,
            duration=5,
            on_device_discovered=device_callback,
            on_capture_complete=lambda devs: print(f"  [COMPLETE] {len(devices)} devices")
        )

        # Monitor capture
        start_time = time.time()
        while listener.is_active():
            if time.time() - start_time > 7:
                listener.stop()
                break
            time.sleep(0.5)

        # Analysis
        print("\n[4/4] Protocol Analysis:")
        print(f"  Total packets captured: {len(packets_captured)}")
        print(f"  Total devices discovered: {len(discovered_devices)}")

        if len(packets_captured) > 0:
            print("\n  Packet Types:")
            proto_counts = {}
            for pkt in packets_captured:
                proto = pkt['suspected_protocol']
                proto_counts[proto] = proto_counts.get(proto, 0) + 1
            for proto, count in proto_counts.items():
                print(f"    - {proto}: {count} packets")

        if len(discovered_devices) > 0:
            print("\n  Device Protocols:")
            for device in discovered_devices:
                proto = getattr(device, 'protocol', 'Unknown')
                device_class = type(device).__name__
                print(f"    - {device.get_display_name()}: {proto} ({device_class})")

        # Diagnosis
        print("\n[DIAGNOSIS]")
        if len(discovered_devices) > 0:
            device = discovered_devices[0]
            actual_proto = getattr(device, 'protocol', 'Unknown')
            device_class = type(device).__name__

            print(f"  Device discovered: {device.get_display_name()}")
            print(f"  Device class: {device_class}")
            print(f"  Protocol field: {actual_proto}")

            if device_class == 'CDPDevice':
                print("  ⚠️  Device was parsed as CDPDevice")
                if len(packets_captured) > 0:
                    first_pkt = packets_captured[0]
                    if 'LLDP' in first_pkt['suspected_protocol']:
                        print("  ❌ ERROR: Packet looks like LLDP but parsed as CDP!")
            elif device_class == 'LLDPDevice':
                print("  ✅ Device was correctly parsed as LLDPDevice")
                if actual_proto == 'CDP':
                    print("  ⚠️  But protocol field was set to CDP incorrectly!")

        return 0

    except Exception as e:
        print(f"\n[FAIL] Protocol detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = test_protocol_detection()
    print(f"\n{'=' * 60}")
    print(f"Test exit code: {exit_code}")
    print(f"{'=' * 60}")
    sys.exit(exit_code)
