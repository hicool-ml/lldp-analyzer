"""
Simple startup test - to verify the program can start
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("TEST 1: Basic import test")
print("=" * 50)

try:
    print("Importing PyQt6...", flush=True)
    from PyQt6.QtWidgets import QApplication
    print("✅ PyQt6 imported successfully", flush=True)
except Exception as e:
    print(f"❌ PyQt6 import failed: {e}", flush=True)

try:
    print("Importing UI module...", flush=True)
    from ui.pro_window import LLDPProfessionalWindow
    print("✅ UI module imported successfully", flush=True)
except Exception as e:
    print(f"❌ UI module import failed: {e}", flush=True)
    import traceback
    traceback.print_exc()

try:
    print("Creating application...", flush=True)
    app = QApplication(sys.argv)
    print("✅ Application created successfully", flush=True)

    print("Creating main window...", flush=True)
    window = LLDPProfessionalWindow()
    print("✅ Main window created successfully", flush=True)

    print("Showing window...", flush=True)
    window.show()
    print("✅ Window shown successfully", flush=True)

    print("")
    print("=" * 50)
    print("✅ ALL TESTS PASSED!")
    print("=" * 50)
    print("Starting event loop...")
    print("(Window should be visible now)")

    sys.exit(app.exec())

except Exception as e:
    print(f"❌ ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
    print("")
    print("Press Enter to exit...")
    input()