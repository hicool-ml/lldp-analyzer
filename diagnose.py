"""
Network Interface Diagnostic Tool
Helps diagnose network interface detection issues
"""

print("=" * 60)
print("LLDP/CDP Analyzer - Network Interface Diagnostic")
print("=" * 60)
print()

# Step 1: Check Npcap installation
print("🔍 Step 1: Checking Npcap installation...")
try:
    from scapy.all import get_working_ifaces
    print("✅ Scapy is installed and working!")
except ImportError as e:
    print(f"❌ Scapy import failed: {e}")
    print("❌ Please install scapy: pip install scapy")
    input("Press Enter to exit...")
    exit(1)

# Step 2: Scan all network interfaces
print()
print("🔍 Step 2: Scanning all network interfaces...")
print("-" * 60)

all_interfaces = list(get_working_ifaces())
print(f"Found {len(all_interfaces)} total interfaces")
print()

if len(all_interfaces) == 0:
    print("❌ No network interfaces found!")
    print("❌ Please install Npcap: https://npcap.com/")
    input("Press Enter to exit...")
    exit(1)

# Step 3: Analyze each interface
print("🔍 Step 3: Analyzing network interfaces...")
print("-" * 60)

valid_interfaces = []
for i, iface in enumerate(all_interfaces, 1):
    print(f"Interface #{i}: {iface.name}")
    print(f"  Description: {iface.description}")

    # Check if this would be selected by our app
    desc = iface.description.lower()
    is_valid = (
        "ethernet" in desc or
        "network" in desc or
        "lan" in desc or
        "intel" in desc or
        "realtek" in desc or
        " Broadcom" in desc or
        "controller" in desc or
        "connection" in desc or
        ("adapter" in desc and "virtual" not in desc) or
        iface.name.startswith("eth") or
        iface.name.startswith("以太网")
    )

    if is_valid:
        print(f"  ✅ VALID - would be selected by LLDP analyzer")
        valid_interfaces.append(iface)
    else:
        print(f"  ❌ SKIPPED - doesn't match selection criteria")

    print()

# Step 4: Summary
print("=" * 60)
print("📊 Diagnostic Summary")
print("=" * 60)
print(f"Total interfaces found: {len(all_interfaces)}")
print(f"Valid interfaces: {len(valid_interfaces)}")
print()

if len(valid_interfaces) == 0:
    print("❌ ERROR: No valid network interfaces found!")
    print()
    print("Possible causes:")
    print("1. No physical network cable connected")
    print("2. Network adapter is disabled")
    print("3. Npcap driver not properly installed")
    print("4. Running as non-admin user")
    print()
    print("Solutions:")
    print("1. Check if network cable is connected")
    print("2. Enable network adapter in Windows Settings")
    print("3. Reinstall Npcap with admin privileges")
    print("4. Run this program as Administrator")
elif len(valid_interfaces) < 3:
    print(f"⚠️  WARNING: Only {len(valid_interfaces)} valid interface(s) found")
    print("This is normal if you only have one physical network connection")
else:
    print(f"✅ SUCCESS: {len(valid_interfaces)} valid network interfaces found")
    print("The LLDP analyzer should work correctly!")

print()
print("Valid interfaces:")
for iface in valid_interfaces:
    print(f"  - {iface.description} ({iface.name})")

print()
print("=" * 60)
print("Diagnostic complete!")
print("=" * 60)
print()

if len(valid_interfaces) > 0:
    print("✅ Your network interfaces look good. Try running the main program:")
    print("   D:\\nanopi\\yunwei\\lldp_analyzer\\dist\\main_pro.exe")
else:
    print("❌ Please fix the network interface issues first.")

print()
input("Press Enter to exit...")
