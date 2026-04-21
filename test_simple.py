"""
Simple test - verify basic functionality
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50, flush=True)
print("Simple Startup Test", flush=True)
print("=" * 50, flush=True)

print("Step 1: Import test...", flush=True)
try:
    from PyQt6.QtWidgets import QApplication
    from ui.pro_window import LLDPProfessionalWindow
    print("✅ Imports successful", flush=True)
except Exception as e:
    print(f"❌ Import failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

print("Step 2: Create application...", flush=True)
try:
    app = QApplication(sys.argv)
    print("✅ Application created", flush=True)
except Exception as e:
    print(f"❌ App creation failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

print("Step 3: Create main window...", flush=True)
try:
    window = LLDPProfessionalWindow()
    print("✅ Main window created", flush=True)
except Exception as e:
    print(f"❌ Window creation failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

print("Step 4: Show window...", flush=True)
try:
    window.show()
    print("✅ Window shown", flush=True)
    print("", flush=True)
    print("✅ ALL TESTS PASSED!", flush=True)
    print("Window should now be visible", flush=True)
    print("If you don't see the window, there may be a display issue", flush=True)
except Exception as e:
    print(f"❌ Show window failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

print("Step 5: Enter event loop...", flush=True)
print("(The window should be visible now)", flush=True)
print("", flush=True)

try:
    sys.exit(app.exec())
except Exception as e:
    print(f"❌ Event loop error: {e}", flush=True)
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)