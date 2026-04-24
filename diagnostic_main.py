"""Diagnostic main - step by step testing"""
import sys
import os

print("=== LLDP Analyzer Diagnostic Start ===")
print(f"Python: {sys.version}")
print(f"Directory: {os.getcwd()}")

try:
    print("\n[Step 1] Testing basic imports...")
    import PyQt6
    print("  PyQt6: OK")

    from PyQt6.QtWidgets import QApplication
    print("  QApplication: OK")

    print("\n[Step 2] Setting AppUserModelID...")
    if os.name == 'nt':
        try:
            import ctypes
            app_id = 'com.hicool.lldpanalyzer.300'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            print(f"  AppUserModelID: OK ({app_id})")
        except Exception as e:
            print(f"  AppUserModelID: FAILED ({e})")

    print("\n[Step 3] Creating QApplication...")
    app = QApplication(sys.argv)
    print("  QApplication: Created")

    print("\n[Step 4] Testing path setup...")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print(f"  Path: {sys.path[0]}")

    print("\n[Step 5] Testing UI imports...")
    from ui import pro_window
    print("  ui.pro_window: OK")

    print("\n[Step 6] Getting main function...")
    main_func = pro_window.main
    print("  pro_window.main: OK")

    print("\n[Step 7] Calling main function...")
    print("  Starting LLDP Analyzer...")
    main_func()

    print("\n[Step 8] Application started successfully!")

except Exception as e:
    print(f"\n[ERROR] Step failed: {e}")
    import traceback
    traceback.print_exc()

    # Keep console open on error
    if os.name == 'nt':
        input("\nPress Enter to exit...")
