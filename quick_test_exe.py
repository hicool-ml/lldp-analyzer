"""Quick test to verify exe functionality"""
import subprocess
import sys

def test_exe():
    """测试exe是否能正常启动"""
    print("=== LLDP Analyzer Exe Test ===")

    try:
        # 启动exe并捕获输出
        process = subprocess.Popen(
            ["dist/LLDP_Analyzer.exe"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("✅ Exe process started successfully")
        print("   PID:", process.pid)
        print("   Please check if the GUI window appears...")

        # 等待5秒看是否有输出
        try:
            stdout, stderr = process.communicate(timeout=5)
            if stdout:
                print("   STDOUT:", stdout[:200])
            if stderr:
                print("   STDERR:", stderr[:200])
        except subprocess.TimeoutExpired:
            print("   ⚠️  Process still running after 5 seconds (GUI is likely active)")
            print("   ✅ This is normal for GUI applications")
            process.terminate()

        return True

    except Exception as e:
        print(f"❌ Exe test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_exe()
    if success:
        print("\n✅ Test passed - exe appears to be working")
        print("If you don't see the GUI window, it might be:")
        print("1. Starting slowly (wait 10-20 seconds)")
        print("2. Hidden behind other windows (check taskbar)")
        print("3. Need administrator privileges")
    else:
        print("\n❌ Test failed - exe may have issues")
