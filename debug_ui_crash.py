"""
Debug script to capture UI crash during capture
"""
import sys
import traceback
from datetime import datetime

# Enable full traceback
sys.excepthook = lambda *args: ''.join(traceback.format_exception(*args))

def safe_ui_test():
    """Test UI capture with full error logging"""
    print("=" * 60)
    print("UI CAPTURE CRASH DEBUG")
    print("=" * 60)

    try:
        # Import UI modules
        print("[1/5] Importing UI modules...")
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from lldp import LLDPCaptureListener
        from lldp.model import LLDPDevice
        from scapy.all import get_working_ifaces
        print("[OK] UI modules imported")

        # Create application
        print("\n[2/5] Creating QApplication...")
        app = QApplication(sys.argv)
        print("[OK] QApplication created")

        # Test capture initialization
        print("\n[3/5] Testing capture initialization...")
        listener = LLDPCaptureListener()
        print(f"[OK] Capture listener initialized")
        print(f"  - Has start method: {hasattr(listener, 'start')}")
        print(f"  - Has stop method: {hasattr(listener, 'stop')}")
        print(f"  - Has thread attribute: {hasattr(listener, 'thread')}")

        # Get interface
        print("\n[4/5] Getting network interface...")
        interfaces = list(get_working_ifaces())
        print(f"[OK] Found {len(interfaces)} interfaces")

        # Select best interface
        best_interface = None
        for iface in interfaces:
            desc = iface.description.lower()
            if any(keyword in desc for keyword in ['ethernet', '以太网', 'intel', 'realtek']):
                if not any(keyword in desc for keyword in ['wi-fi', 'wifi', 'wireless', 'virtual']):
                    best_interface = iface
                    break

        if not best_interface and len(interfaces) > 0:
            best_interface = interfaces[0]

        if best_interface:
            print(f"[OK] Selected interface: {best_interface.name}")
            print(f"  Description: {best_interface.description}")

            # Test short capture
            print("\n[5/5] Testing 5-second capture...")

            devices_found = []

            def device_callback(device):
                """Device discovery callback"""
                try:
                    device_name = device.get_display_name() if hasattr(device, 'get_display_name') else str(device)
                    print(f"[DEVICE] Found: {device_name}")
                    devices_found.append(device)
                except Exception as e:
                    print(f"[ERROR] Device callback failed: {e}")
                    traceback.print_exc()

            def capture_complete_callback(devices):
                """Capture complete callback"""
                try:
                    print(f"[COMPLETE] Capture finished with {len(devices)} devices")
                except Exception as e:
                    print(f"[ERROR] Complete callback failed: {e}")
                    traceback.print_exc()

            # Start capture
            print("Starting capture...")
            listener.start(
                interface=best_interface,
                duration=5,
                on_device_discovered=device_callback,
                on_capture_complete=capture_complete_callback
            )

            # Monitor capture
            import time
            start_time = time.time()

            while listener.is_active():
                elapsed = time.time() - start_time
                if elapsed > 7:  # Safety timeout
                    print("[WARN] Safety timeout reached")
                    listener.stop()
                    break
                time.sleep(0.5)

            # Get results
            final_devices = listener.get_discovered_devices()
            print(f"\n[OK] Capture completed!")
            print(f"  - Devices found: {len(final_devices)}")

            return 0

        else:
            print("[ERROR] No suitable interface found")
            return 1

    except Exception as e:
        print(f"\n[FATAL] Error during UI test: {e}")
        print("\n=== FULL TRACEBACK ===")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = safe_ui_test()
        print(f"\n{'=' * 60}")
        print(f"Test completed with exit code: {exit_code}")
        print(f"{'=' * 60}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[FATAL] Unhandled exception: {e}")
        traceback.print_exc()
        sys.exit(1)
