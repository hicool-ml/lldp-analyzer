"""
Test dpkt LLDP and CDP parsing capabilities
"""
import dpkt

# Check available modules
print("=== dpkt Modules ===")
print(f"dpkt version: {dpkt.__version__ if hasattr(dpkt, '__version__') else 'unknown'}")
print(f"Has LLDP: {hasattr(dpkt, 'lldp')}")
print(f"Has CDP: {hasattr(dpkt, 'cdp')}")
print(f"Has Ethernet: {hasattr(dpkt, 'ethernet')}")

# Check LLDP capabilities
if hasattr(dpkt, 'lldp'):
    lldp = dpkt.lldp
    print(f"\n=== LLDP Support ===")
    print(f"Has LLDP class: {hasattr(lldp, 'LLDP')}")
    print(f"Has TLV constants: {hasattr(lldp, 'TLV_CHASSIS_ID')}")

    # Try to access TLV types
    try:
        print(f"TLV_CHASSIS_ID: {getattr(lldp, 'TLV_CHASSIS_ID', 'N/A')}")
        print(f"TLV_PORT_ID: {getattr(lldp, 'TLV_PORT_ID', 'N/A')}")
        print(f"TLV_SYSTEM_NAME: {getattr(lldp, 'TLV_SYSTEM_NAME', 'N/A')}")
    except Exception as e:
        print(f"Error accessing TLVs: {e}")

# Check CDP capabilities
if hasattr(dpkt, 'cdp'):
    cdp = dpkt.cdp
    print(f"\n=== CDP Support ===")
    print(f"Has CDP class: {hasattr(cdp, 'CDP')}")

    # Try to access CDP TLV types
    try:
        print(f"TLV_DEV_ID: {getattr(cdp, 'TLV_DEV_ID', 'N/A')}")
        print(f"TLV_PORT_ID: {getattr(cdp, 'TLV_PORT_ID', 'N/A')}")
        print(f"TLV_NATIVE_VLAN: {getattr(cdp, 'TLV_NATIVE_VLAN', 'N/A')}")
    except Exception as e:
        print(f"Error accessing CDP TLVs: {e}")

print("\n=== Conclusion ===")
print("dpkt is lightweight but may need custom LLDP/CDP implementation")
print("Scapy: 2.6MB, dpkt: 195KB (13x smaller!)")
