"""
Simple console test - to debug the issue
"""
import sys
import os

print("TEST 1: Basic print works")

try:
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.WinDLL('kernel32')
        kernel32.AllocConsole()
        kernel32.SetConsoleTitleW("Console Test")
        print("TEST 2: Console allocated")

        conout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        sys.stdout = conout
        sys.stderr = conout
        print("TEST 3: Output redirected")

except Exception as e:
    print(f"ERROR: {e}")

print("TEST 4: If you see this, basic output works")
input("Press Enter to exit...")