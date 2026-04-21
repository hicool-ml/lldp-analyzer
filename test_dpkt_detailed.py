"""
Test dpkt CDP and raw packet parsing
"""
import dpkt
import struct

print("=== dpkt CDP Class Test ===")
try:
    # Check CDP class structure
    cdp_obj = dpkt.cdp.CDP()
    print(f"CDP object created: {cdp_obj}")
    print(f"CDP attributes: {dir(cdp_obj)}")

    # Check for TLV access
    if hasattr(cdp_obj, 'data'):
        print(f"CDP has data attribute: Yes")

    # Try to understand CDP structure
    print(f"\nCDP class dict: {cdp_obj.__dict__}")

except Exception as e:
    print(f"Error creating CDP object: {e}")

print("\n=== Raw Ethernet Parsing Test ===")
try:
    # Create a sample LLDP packet (simplified)
    # Ethernet header: DST(6) + SRC(6) + TYPE(2)
    lldp_dst = b'\x01\x80\xc2\x00\x00\x0e'  # LLDP multicast
    lldp_src = b'\x00\x11\x22\x33\x44\x55'
    lldp_etype = b'\x88\xcc'  # LLDP EtherType

    # Create Ethernet frame
    eth_data = lldp_dst + lldp_src + lldp_etype
    eth = dpkt.ethernet.Ethernet(eth_data)

    print(f"Ethernet parsed successfully")
    print(f"Ethernet dst: {':'.join(f'{b:02x}' for b in eth.dst)}")
    print(f"Ethernet src: {':'.join(f'{b:02x}' for b in eth.src)}")
    print(f"Ethernet type: {eth.type:#06x}")

    # Check if data is accessible
    print(f"Ethernet data: {eth.data}")
    print(f"Ethernet data type: {type(eth.data)}")

except Exception as e:
    print(f"Error parsing Ethernet: {e}")

print("\n=== Manual LLDP TLV Parsing ===")
try:
    # Sample LLDP TLV: Chassis ID TLV
    # Type(7bit) + Length(9bit) + Value
    # Chassis ID = TLV type 1
    tlv_type = 1  # Chassis ID
    tlv_length = 7  # Length
    chassis_id_subtype = 4  # MAC address
    chassis_id = b'\xaa\xbb\xcc\xdd\xee\xff'

    # Build TLV: (type << 9) | length
    tlv_header = struct.pack('>H', (tlv_type << 9) | tlv_length)
    tlv_data = tlv_header + bytes([chassis_id_subtype]) + chassis_id

    print(f"TLV header: {tlv_header.hex()}")
    print(f"TLV data: {tlv_data.hex()}")

    # Parse back
    parsed_type_length = struct.unpack('>H', tlv_header)[0]
    parsed_type = parsed_type_length >> 9
    parsed_length = parsed_type_length & 0x01FF

    print(f"Parsed TLV type: {parsed_type}")
    print(f"Parsed TLV length: {parsed_length}")

    print("\n✅ Manual LLDP TLV parsing works!")
    print("We can implement LLDP parser using dpkt's Ethernet layer")

except Exception as e:
    print(f"Error in manual TLV parsing: {e}")
