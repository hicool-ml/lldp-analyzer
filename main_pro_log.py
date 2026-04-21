"""
LLDP Network Analyzer - Professional UI Entry Point with FILE LOGGING
Fallback version if console output has issues
"""

import sys
import os
from datetime import datetime

# 创建日志文件
log_file = f"lldp_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_file)

# 重定向print到文件
class Logger:
    def __init__(self, file_path):
        self.log_file = open(file_path, "w", encoding="utf-8", buffering=1)
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # 重定向stdout和stderr
        sys.stdout = self
        sys.stderr = self

    def write(self, text):
        self.log_file.write(text)
        self.log_file.flush()
        # 同时输出到原始控制台（如果有的话）
        try:
            self.original_stdout.write(text)
            self.original_stdout.flush()
        except:
            pass

    def flush(self):
        self.log_file.flush()
        try:
            self.original_stdout.flush()
        except:
            pass

    def close(self):
        self.log_file.close()

# 初始化日志
logger = Logger(log_path)

print(f"=== LLDP/CDP Network Analyzer Debug Log ===")
print(f"Log file: {log_path}")
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.pro_window import main as pro_main

if __name__ == "__main__":
    print("🚀 Starting LLDP/CDP Network Analyzer...")
    print("✅ CDP Protocol Support: ENABLED")
    print("✅ Native VLAN Discovery: READY")
    print("=" * 50)

    try:
        pro_main()
        print("✅ Program completed successfully")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Check log file for full details:", log_path)