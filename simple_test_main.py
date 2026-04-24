"""Minimal test main for exe diagnosis"""
import sys
import os

# Set environment variables for high DPI
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'

print("=== LLDP Analyzer Minimal Test ===")
print("Step 1: Imports...")

try:
    # Set AppUserModelID BEFORE QApplication
    if os.name == 'nt':
        try:
            import ctypes
            app_id = 'com.hicool.lldpanalyzer.300'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            print(f"Step 2: AppUserModelID set: {app_id}")
        except Exception as e:
            print(f"Step 2: AppUserModelID failed: {e}")

    print("Step 3: Creating QApplication...")
    from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon

    app = QApplication(sys.argv)
    print("Step 4: QApplication created successfully")

    # Try to load icon
    try:
        from pathlib import Path
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent

        icon_path = base_path / 'lldp_icon.ico'
        if icon_path.exists():
            app_icon = QIcon(str(icon_path))
            app.setWindowIcon(app_icon)
            print(f"Step 5: Icon loaded: {icon_path}")
        else:
            print("Step 5: Icon not found, using default")
    except Exception as e:
        print(f"Step 5: Icon loading failed: {e}")

    # Create a simple test window
    print("Step 6: Creating test window...")
    window = QWidget()
    window.setWindowTitle("LLDP Analyzer - Test Window")
    window.resize(400, 300)

    # Add some widgets
    layout = QVBoxLayout()

    label = QLabel("LLDP Analyzer Test Window")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)

    button = QPushButton("Test Button")
    layout.addWidget(button)

    window.setLayout(layout)
    print("Step 7: Window created successfully")

    # Show window
    window.show()
    print("Step 8: Window shown - GUI should be visible now!")
    print("Step 9: Starting event loop...")

    # Run event loop
    result = app.exec()
    print(f"Step 10: Application exited with code: {result}")

except Exception as e:
    print(f"\n=== ERROR ===")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

    # Keep console open if there's an error
    if os.name == 'nt':
        input("\nPress Enter to exit...")
