#!/usr/bin/env python3
"""
macOS网络捕获快速诊断工具
检查LLDP Analyzer运行所需的权限和接口状态
"""

import sys
import platform
import subprocess
import os

def check_platform():
    """检查操作系统"""
    print("🔍 检查操作系统...")
    system = platform.system()
    print(f"   操作系统: {system}")
    if system == "Darwin":
        print(f"   macOS版本: {platform.mac_ver()[0]}")
        return True
    else:
        print("   ❌ 这不是macOS系统")
        return False

def check_admin_privileges():
    """检查管理员权限"""
    print("\n🔍 检查管理员权限...")
    try:
        is_admin = os.getuid() == 0
        if is_admin:
            print("   ✅ 运行在root权限下")
        else:
            print("   ⚠️ 没有root权限")
            print("   💡 建议: sudo python3 main_pro.py")
        return is_admin
    except Exception as e:
        print(f"   ❌ 权限检查失败: {e}")
        return False

def check_network_interfaces():
    """检查网络接口"""
    print("\n🔍 检查网络接口...")
    try:
        from scapy.all import get_working_ifaces
        interfaces = list(get_working_ifaces())

        print(f"   找到 {len(interfaces)} 个网络接口:")

        physical_interfaces = []
        for i, iface in enumerate(interfaces):
            # 判断是否为物理接口
            name = iface.name.lower()
            desc = iface.description.lower()

            # 跳过虚拟和回环接口
            if any(kw in name for kw in ['lo', 'loopback', 'vmnet', 'vbox', 'bridge']):
                continue

            physical_interfaces.append(iface)
            print(f"   [{len(physical_interfaces)}] {iface.name}")
            print(f"       描述: {iface.description}")

            if hasattr(iface, 'ip') and iface.ip:
                print(f"       IP地址: {iface.ip}")

        if physical_interfaces:
            print(f"\n   ✅ 找到 {len(physical_interfaces)} 个可用物理接口")
            return physical_interfaces
        else:
            print("   ❌ 没有找到物理网络接口")
            return []

    except ImportError:
        print("   ❌ Scapy未安装")
        print("   💡 安装: pip3 install scapy")
        return []
    except Exception as e:
        print(f"   ❌ 接口检查失败: {e}")
        return []

def check_bpf_devices():
    """检查BPF设备"""
    print("\n🔍 检查BPF设备...")
    try:
        result = subprocess.run(['ls', '-la', '/dev/bpf*'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("   ✅ BPF设备存在:")
            print("   " + result.stdout.replace('\n', '\n   '))
            return True
        else:
            print("   ❌ BPF设备不存在")
            return False
    except Exception as e:
        print(f"   ❌ BPF检查失败: {e}")
        return False

def test_raw_socket():
    """测试原始套接字"""
    print("\n🔍 测试原始套接字权限...")
    try:
        from scapy.all import IP, ICMP, sr1
        print("   发送测试ICMP包...")
        # 尝试发送一个ping包（不等待响应）
        packet = IP(dst="8.8.8.8")/ICMP()
        print("   ✅ 原始套接字可用")
        return True
    except PermissionError:
        print("   ❌ 权限不足")
        print("   💡 需要使用sudo运行")
        return False
    except Exception as e:
        print(f"   ⚠️ 原始套接字测试失败: {e}")
        return False

def check_tcpdump():
    """检查tcpdump是否可用"""
    print("\n🔍 检查tcpdump...")
    try:
        result = subprocess.run(['which', 'tcpdump'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"   ✅ tcpdump可用: {result.stdout.strip()}")
            return True
        else:
            print("   ⚠️ tcpdump未安装")
            print("   💡 安装: brew install tcpdump")
            return False
    except Exception as e:
        print(f"   ❌ tcpdump检查失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("LLDP Analyzer - macOS网络诊断工具")
    print("=" * 60)

    # 运行所有检查
    is_macos = check_platform()
    if not is_macos:
        print("\n❌ 此工具仅用于macOS系统")
        return 1

    has_admin = check_admin_privileges()
    interfaces = check_network_interfaces()
    has_bpf = check_bpf_devices()
    has_socket = test_raw_socket()
    has_tcpdump = check_tcpdump()

    # 总结
    print("\n" + "=" * 60)
    print("诊断总结:")
    print("=" * 60)

    issues = []
    if not has_admin:
        issues.append("❌ 需要管理员权限（使用sudo）")
    if not interfaces:
        issues.append("❌ 没有可用的物理网络接口")
    if not has_bpf:
        issues.append("❌ BPF设备不可用")
    if not has_socket:
        issues.append("❌ 原始套接字权限不足")

    if issues:
        print("\n发现问题:")
        for issue in issues:
            print(f"  {issue}")

        print("\n推荐解决方案:")
        print("  1. 使用sudo运行: sudo python3 main_pro.py")
        print("  2. 安装USB/Thunderbolt以太网适配器")
        print("  3. 检查网线连接")
        print("  4. 确保连接到支持LLDP的网络设备")

        return 1
    else:
        print("\n✅ 所有检查通过！")
        print("\n推荐接口:")
        for iface in interfaces[:3]:  # 显示前3个推荐接口
            print(f"  - {iface.name} ({iface.description})")

        print("\n可以运行: sudo python3 main_pro.py")
        return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 诊断被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
