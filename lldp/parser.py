"""
LLDP Protocol Parser
Pure function parser - No side effects, no UI dependencies

🔥 安全修复：TLV边界检查、标准兼容性、Management Address解析
"""

import logging
from typing import Optional, List
from .model import (
    LLDPDevice,
    LLDPChassisID,
    LLDPPortID,
    VLANInfo,
    PoEInfo,
    Dot1XInfo,
    DeviceCapabilities,
    ChassisIDType,
    PortIDType,
)

# 🔥 新增：日志记录器替代print
logger = logging.getLogger(__name__)

# 🔥 新增：安全配置常量
MAX_TLV_LENGTH = 4096  # 最大TLV长度，防止恶意包攻击


class LLDPParser:
    """
    LLDP Protocol Parser

    Pure function parser that converts raw LLDP packets to LLDPDevice objects.
    Thread-safe, no side effects, no UI dependencies.
    """

    # OUI constants
    OUI_IEEE_802_1Q = b'\x00\x80\xc2'
    OUI_IEEE_802_3 = b'\x00\x12\x0f'

    # Vendor OUIs - Major network equipment manufacturers
    OUI_VENDOR_CISCO = b'\x00\x00\x0c'      # Cisco Systems
    OUI_VENDOR_HUAWEI = b'\x00\x1e\xec'     # Huawei Technologies
    OUI_VENDOR_H3C = b'\x00\x12\xbb'        # H3C (New H3C Technologies)
    OUI_VENDOR_H3C_ALT = b'\x00\xe0\xfc'    # H3C (Alternative OUI)
    OUI_VENDOR_JUNIPER = b'\x00\x05\x85'    # Juniper Networks
    OUI_VENDOR_ARISTA = b'\x00\x1e\x67'     # Arista Networks
    OUI_VENDOR_DELL = b'\x00\x1e\xc9'       # Dell/Force10
    OUI_VENDOR_BROCADE = b'\x00\x05\x85'    # Brocade/Foundry
    OUI_VENDOR_ALCATEL = b'\x00\x0f\xe2'    # Alcatel-Lucent
    OUI_VENDOR_ZTE = b'\x00\x24\xf8'        # ZTE Corporation
    OUI_VENDOR_RUIJIE = b'\x00\x25\xf3'     # Ruijie Networks
    OUI_VENDOR_FORTINET = b'\x00\x0f\xe2'   # Fortinet
    OUI_VENDOR_NETGEAR = b'\x00\x09\x4e'    # NETGEAR
    OUI_VENDOR_TP_LINK = b'\x00\x1b\xa5'    # TP-Link
    OUI_VENDOR_D_LINK = b'\x00\x05\x5d'     # D-Link

    # Vendor OUI mapping table
    VENDOR_OUI_MAP = {
        b'\x00\x00\x0c': "Cisco",
        b'\x00\x1e\xec': "Huawei",
        b'\x00\x25\x9e': "Huawei",
        b'\x00\x12\xbb': "H3C",
        b'\x00\xe0\xfc': "H3C",
        b'\x00\x05\x85': "Juniper",
        b'\x00\x0f\x24': "Juniper",
        b'\x00\x1e\x67': "Arista",
        b'\x00\x1e\xc9': "Dell",
        b'\x00\x0f\xe2': "Alcatel/Fortinet",
        b'\x00\x24\xf8': "ZTE",
        b'\x08\x13\x15': "ZTE",
        b'\x00\x25\xf3': "Ruijie",
        b'\x00\x09\x4e': "NETGEAR",
        b'\x00\x1b\xa5': "TP-Link",
        b'\x00\x05\x5d': "D-Link",
    }

    def __init__(self):
        """Initialize parser"""
        pass

    def parse_packet(self, packet_data: bytes) -> Optional[LLDPDevice]:
        """
        🔥 安全修复版：Parse LLDP packet data with proper boundary checking

        Args:
            packet_data: Raw LLDP packet bytes (after Ether header)

        Returns:
            LLDPDevice object or None if parsing fails
        """
        device = LLDPDevice()

        logger.debug("========== LLDP Packet Parsing ==========")
        logger.debug(f"Total packet length: {len(packet_data)} bytes")
        logger.debug(f"Raw packet: {packet_data.hex()}")

        try:
            ptr = 0
            tlv_count = 0
            remaining = len(packet_data)

            # 🔥 安全修复：更严格的边界检查
            while remaining >= 2:  # 至少需要TLV header (2 bytes)
                # Parse TLV header
                typ = (packet_data[ptr] >> 1) & 0x7F
                length = ((packet_data[ptr] & 1) << 8) | packet_data[ptr + 1]

                # 🔥 安全修复：检查TLV长度是否合法
                if length > MAX_TLV_LENGTH:
                    logger.error(f"TLV length {length} exceeds maximum {MAX_TLV_LENGTH}")
                    return None

                # 🔥 安全修复：检查是否有足够的数据读取完整TLV
                if remaining < 2 + length:
                    logger.error(f"Incomplete TLV: need {2 + length} bytes, only {remaining} remaining")
                    return None

                val = packet_data[ptr + 2:ptr + 2 + length]

                # 🔥 安全修复：End of LLDPDU (type=0) 立即停止解析
                if typ == 0:
                    logger.debug(f"TLV #{tlv_count}: End of LLDPDU, stopping parsing")
                    break

                ptr += 2 + length
                remaining -= 2 + length
                tlv_count += 1

                # Debug: Show all TLVs
                tlv_names = {
                    1: "Chassis ID",
                    2: "Port ID",
                    3: "Time To Live",
                    4: "Port Description",
                    5: "System Name",
                    6: "System Description",
                    7: "System Capabilities",
                    8: "Management Address",
                    127: "Organizationally Specific"
                }
                tlv_name = tlv_names.get(typ, f"Unknown ({typ})")
                logger.debug(f"TLV #{tlv_count}: Type={typ} ({tlv_name}), Length={length}, Value={val.hex()[:50]}...")

                # Process TLV
                self._parse_tlv(device, typ, val)

            logger.debug(f"Total TLVs parsed: {tlv_count}")
            logger.debug("=======================================")

            # 🔧 修复：在所有TLV解析完成后，重新关联VLAN名称
            self._associate_vlan_names(device)

            return device if device.is_valid() else None

        except Exception as e:
            logger.error(f"Parse error: {e}", exc_info=True)  # 🔥 新增：记录完整traceback
            return None

    def parse_scapy_packet(self, scapy_pkt) -> Optional[LLDPDevice]:
        """
        Parse LLDP packet from Scapy packet object

        Args:
            scapy_pkt: Scapy Ether packet with LLDP payload

        Returns:
            LLDPDevice object or None if parsing fails
        """
        try:
            # Extract LLDP payload
            from scapy.all import Ether

            if not scapy_pkt.haslayer(Ether) or scapy_pkt[Ether].type != 0x88CC:
                return None

            # Get payload after Ether header
            data = bytes(scapy_pkt.payload)

            return self.parse_packet(data)

        except Exception:
            return None

    def _parse_tlv(self, device: LLDPDevice, typ: int, val: bytes):
        """Parse individual TLV and update device model"""

        # TLV 0: End of LLDPDU
        if typ == 0:
            return

        # TLV 1: Chassis ID
        elif typ == 1:
            device.chassis_id = self._parse_chassis_id(val)

        # TLV 2: Port ID
        elif typ == 2:
            device.port_id = self._parse_port_id(val)

        # TLV 3: Time To Live
        elif typ == 3:
            if len(val) >= 2:
                device.ttl = int.from_bytes(val, 'big')

        # TLV 4: Port Description
        elif typ == 4:
            device.port_description = val.decode("utf-8", errors="ignore").strip()

        # TLV 5: System Name
        elif typ == 5:
            device.system_name = val.decode("utf-8", errors="ignore").strip()

        # TLV 6: System Description
        elif typ == 6:
            system_desc = val.decode("utf-8", errors="ignore").strip()
            device.system_description = system_desc

            # Extract device model from system description
            self._extract_device_model(device, system_desc)

        # TLV 7: System Capabilities
        elif typ == 7:
            device.capabilities = self._parse_capabilities(val)

        # TLV 8: Management Address
        elif typ == 8:
            device.management_ip = self._parse_management_address(val)

        # TLV 127: Organizationally Specific
        elif typ == 127:
            self._parse_org_specific_tlv(device, val)

    def _extract_device_model(self, device: LLDPDevice, system_description: str):
        """Extract device model from system description"""
        if not system_description:
            return

        try:
            # Common patterns for device model extraction
            # H3C format: "H3C S5130S-52S-PWR-HI" or "H3C Comware..."
            # Huawei format: "Huawei ..."
            # Cisco format: "Cisco ..." etc.

            lines = system_description.split('\n')
            for line in lines:
                line = line.strip()

                # H3C device model pattern (typically on second line)
                if 'H3C' in line and 'Comware' not in line and len(line) > 10:
                    model = line.strip()
                    print(f"[DEBUG] Extracted H3C device model: {model}")
                    if not hasattr(device, 'device_model'):
                        device.device_model = model
                    break

                # Huawei device model pattern
                elif 'Huawei' in line and 'Technologies' not in line and len(line) > 10:
                    model = line.strip()
                    print(f"[DEBUG] Extracted Huawei device model: {model}")
                    if not hasattr(device, 'device_model'):
                        device.device_model = model
                    break

                # Cisco device model pattern
                elif 'Cisco' in line and len(line) > 10:
                    model = line.strip()
                    print(f"[DEBUG] Extracted Cisco device model: {model}")
                    if not hasattr(device, 'device_model'):
                        device.device_model = model
                    break

            # If no model found in specific lines, try extracting from the full description
            if not hasattr(device, 'device_model') or not device.device_model:
                # Generic extraction: look for model-like strings
                import re
                # Match patterns like "S5130S-52S-PWR-HI", "WS-C3850-24T-S", etc.
                model_patterns = [
                    r'[A-Z]{2,}-?\d{4}[A-Z_-]*',  # H3C/Huawei pattern
                    r'WS-[A-Z0-9-]+',              # Cisco pattern
                    r'[A-Z]{2,}\d{3,}[A-Z-]*',    # Generic model pattern
                ]

                for pattern in model_patterns:
                    matches = re.findall(pattern, system_description)
                    if matches:
                        device_model = matches[0]
                        print(f"[DEBUG] Extracted device model via pattern: {device_model}")
                        if not hasattr(device, 'device_model'):
                            device.device_model = device_model
                        break

        except Exception as e:
            print(f"[DEBUG] Error extracting device model: {e}")

    def _parse_chassis_id(self, val: bytes) -> Optional[LLDPChassisID]:
        """Parse Chassis ID TLV"""
        if len(val) < 2:
            return None

        subtype = val[0]
        value = val[1:]

        try:
            chassis_type = ChassisIDType(subtype)
        except ValueError:
            chassis_type = ChassisIDType.LOCALLY_ASSIGNED

        # Format value based on type
        if chassis_type == ChassisIDType.MAC_ADDRESS:
            formatted_value = self._format_mac(value.hex())
        elif chassis_type == ChassisIDType.LOCALLY_ASSIGNED:
            formatted_value = value.decode("utf-8", errors="ignore").strip()
        elif chassis_type == ChassisIDType.INTERFACE_NAME:
            formatted_value = value.decode("utf-8", errors="ignore").strip()
        else:
            formatted_value = value.hex()

        return LLDPChassisID(value=formatted_value, type=chassis_type)

    def _parse_port_id(self, val: bytes) -> Optional[LLDPPortID]:
        """Parse Port ID TLV"""
        if len(val) < 2:
            return None

        subtype = val[0]
        value = val[1:]

        try:
            port_type = PortIDType(subtype)
        except ValueError:
            port_type = PortIDType.LOCALLY_ASSIGNED

        # Format value based on type
        if port_type == PortIDType.MAC_ADDRESS:
            formatted_value = self._format_mac(value.hex())
        elif port_type == PortIDType.LOCALLY_ASSIGNED:
            formatted_value = value.decode("utf-8", errors="ignore").strip()
        elif port_type == PortIDType.INTERFACE_NAME:
            formatted_value = value.decode("utf-8", errors="ignore").strip()
        elif port_type == PortIDType.INTERFACE_ALIAS:
            formatted_value = str(int.from_bytes(value, 'big'))
        else:
            formatted_value = value.hex()

        return LLDPPortID(value=formatted_value, type=port_type)

    def _parse_capabilities(self, val: bytes) -> DeviceCapabilities:
        """
        🔥 RFC标准修复版：Parse System Capabilities TLV

        按照IEEE 802.1AB标准：
        - 前2字节 = supported capabilities
        - 后2字节 = enabled capabilities (如果存在)
        总共4字节，不是8字节！
        """
        caps = DeviceCapabilities()

        logger.debug(f"_parse_capabilities called, TLV length: {len(val)}")
        logger.debug(f"Raw TLV bytes: {val.hex()}")
        logger.debug(f"Individual bytes: {[f'0x{b:02x}' for b in val[:12]]}")

        # 🔥 RFC标准修复：至少需要4字节（2字节supported + 2字节enabled）
        if len(val) >= 4:
            # 🔥 修复：按照RFC标准，前2字节是supported capabilities
            supported = int.from_bytes(val[0:2], 'big')
            logger.debug(f"Supported Capabilities (hex): 0x{supported:04x}")
            logger.debug(f"Supported Capabilities (bin): {supported:016b}")

            # IEEE 802.1AB标准能力位定义
            # Bit 0: Other
            # Bit 1: Repeater
            # Bit 2: Bridge/Switch ← 标准的交换机位
            # Bit 3: WLAN Access Point
            # Bit 4: Router
            # Bit 5: Telephone
            # Bit 6: DOCSIS
            # Bit 7: Station
            # Bit 8: Customer VLAN
            # Bit 9: Customer Bridge
            # Bit 10: Service VLAN
            # Bit 11-15: Reserved

            caps.bridge = bool(supported & (1 << 2))      # Bit 2 = Bridge (交换机)
            caps.repeater = bool(supported & (1 << 1))
            caps.wlan = bool(supported & (1 << 3))        # Bit 3 = WLAN
            caps.router = bool(supported & (1 << 4))      # Bit 4 = Router
            caps.telephone = bool(supported & (1 << 5))   # Bit 5 = Telephone
            caps.docsis = bool(supported & (1 << 6))
            caps.station = bool(supported & (1 << 7))
            caps.c_vlan = bool(supported & (1 << 8))
            caps.c_bridge = bool(supported & (1 << 9))
            caps.s_vlan = bool(supported & (1 << 10))

            logger.debug(f"Parsed capabilities (per IEEE 802.1AB):")
            logger.debug(f"  - Other (bit 0): {bool(supported & 1)}")
            logger.debug(f"  - Repeater (bit 1): {caps.repeater}")
            logger.debug(f"  - Bridge/Switch (bit 2): {caps.bridge}")
            logger.debug(f"  - WLAN Access Point (bit 3): {caps.wlan}")
            logger.debug(f"  - Router (bit 4): {caps.router}")
            logger.debug(f"  - Telephone (bit 5): {caps.telephone}")
            logger.debug(f"  - DOCSIS (bit 6): {caps.docsis}")
            logger.debug(f"  - Station (bit 7): {caps.station}")
            logger.debug(f"  - Customer VLAN (bit 8): {caps.c_vlan}")
            logger.debug(f"  - Customer Bridge (bit 9): {caps.c_bridge}")
            logger.debug(f"  - Service VLAN (bit 10): {caps.s_vlan}")

            # 🔥 RFC标准修复：后2字节是enabled capabilities
            enabled = int.from_bytes(val[2:4], 'big')
            logger.debug(f"Enabled Capabilities (hex): 0x{enabled:04x}")
            logger.debug(f"Enabled Capabilities (bin): {enabled:016b}")

            caps.bridge_enabled = bool(enabled & (1 << 2))      # Bit 2
            caps.repeater_enabled = bool(enabled & (1 << 1))
            caps.wlan_enabled = bool(enabled & (1 << 3))
            caps.router_enabled = bool(enabled & (1 << 4))
            caps.telephone_enabled = bool(enabled & (1 << 5))
            caps.docsis_enabled = bool(enabled & (1 << 6))
            caps.station_enabled = bool(enabled & (1 << 7))
            caps.c_vlan_enabled = bool(enabled & (1 << 8))
            caps.c_bridge_enabled = bool(enabled & (1 << 9))
            caps.s_vlan_enabled = bool(enabled & (1 << 10))

        else:
            logger.warning(f"Capabilities TLV too short: {len(val)} bytes (need at least 4)")

        return caps
                caps.twamp_enabled = caps.twamp

        # Debug: Show what will be displayed
        print(f"[DEBUG] Capabilities to display: {caps.get_all_capabilities()}")
        print(f"[DEBUG] Enabled capabilities: {caps.get_enabled_capabilities()}")

        return caps

    def _parse_management_address(self, val: bytes) -> Optional[str]:
        """
        🔥 IEEE 802.1AB标准修复版：Parse Management Address TLV

        按照IEEE 802.1AB标准：
        - octet 0: management address string length (1 byte)
        - octets 1..N: management address (variable, length = previous value)
        - following: interface subtype (1 octet), interface number (4 octets), OID string length (1 octet), OID (variable)
        """
        if len(val) < 1:
            return None

        logger.debug(f"Management Address TLV raw: {val.hex()}")
        logger.debug(f"Management Address TLV length: {len(val)}")

        try:
            # 🔥 修复：按照IEEE 802.1AB标准
            addr_str_len = val[0]  # 第1字节：地址字符串长度

            # 边界检查
            if addr_str_len == 0 or 1 + addr_str_len > len(val):
                logger.warning(f"Invalid management address length: {addr_str_len}")
                return None

            # 提取管理地址
            addr_bytes = val[1:1 + addr_str_len]

            # 根据长度判断地址类型
            # IPv4: 4字节
            if addr_str_len == 4:
                ipv4 = ".".join(map(str, addr_bytes))
                logger.debug(f"Management IPv4 address: {ipv4}")
                return ipv4

            # IPv6: 16字节
            elif addr_str_len == 16:
                ipv6_groups = [addr_bytes[i:i+2].hex() for i in range(0, 16, 2)]
                ipv6 = ":".join(ipv6_groups)
                logger.debug(f"Management IPv6 address: {ipv6}")
                return ipv6

            # MAC地址: 6字节
            elif addr_str_len == 6:
                mac = self._format_mac(addr_bytes.hex())
                logger.debug(f"Management MAC address: {mac}")
                return mac

            else:
                logger.warning(f"Unknown management address type, length: {addr_str_len}")
                return None

        except (IndexError, ValueError) as e:
            logger.error(f"Failed to parse management address: {e}", exc_info=True)
            return None

    def _parse_org_specific_tlv(self, device: LLDPDevice, val: bytes):
        """Parse Organizationally Specific TLV (TLV 127)"""
        if len(val) < 4:
            return

        oui = val[:3]
        subtype = val[3]

        # IEEE 802.1Q - VLAN 和 LLDP-MED (共用同一个OUI)
        if oui == self.OUI_IEEE_802_1Q:
            # ⚠️ 关键修正：IEEE 802.1Q标准定义中，subtype 1是Port VLAN ID TLV
            # LLDP-MED subtype范围也是1-8，但这是两个不同的标准！
            # 正确的做法：优先尝试解析为IEEE 802.1Q标准TLV（这是大部分厂商使用的）
            # 只有在明确检测到LLDP-MED特征时才使用MED解析器

            print(f"[DEBUG] IEEE 802.1Q OUI detected, subtype={subtype}")

            # 优先使用IEEE 802.1Q标准解析器（包括Port VLAN ID subtype 1）
            self._parse_802_1q_tlv(device, subtype, val)

        # IEEE 802.3 - PoE, MAC/PHY
        elif oui == self.OUI_IEEE_802_3:
            self._parse_802_3_tlv(device, subtype, val)

        # Vendor-specific TLVs (including H3C, Cisco, Huawei, etc.)
        elif oui in self.VENDOR_OUI_MAP:
            vendor_name = self.VENDOR_OUI_MAP[oui]
            print(f"[DEBUG] {vendor_name} Private TLV - OUI: {oui.hex()}, subtype: {subtype}")

            # Route to vendor-specific parser
            if oui == self.OUI_VENDOR_H3C or oui == self.OUI_VENDOR_H3C_ALT:
                self._parse_h3c_private_tlv(device, subtype, val)
            elif oui == self.OUI_VENDOR_CISCO:
                self._parse_cisco_private_tlv(device, subtype, val)
            elif oui == self.OUI_VENDOR_HUAWEI:
                self._parse_huawei_private_tlv(device, subtype, val)
            else:
                # Generic vendor TLV parsing
                self._parse_vendor_private_tlv(device, vendor_name, subtype, val)

        # Unknown OUI
        else:
            print(f"[DEBUG] Unknown OUI: {oui.hex()}, subtype: {subtype}")

    def _parse_802_1q_tlv(self, device: LLDPDevice, subtype: int, val: bytes):
        """Parse IEEE 802.1Q specific TLV"""
        print(f"[DEBUG] IEEE 802.1Q TLV - subtype={subtype}, length={len(val)}")
        print(f"[DEBUG] Raw TLV data: {val.hex()}")

        # IEEE 802.1Q标准TLV subtype定义：
        # Subtype 1: Port VLAN ID (TLV) ← 这是标准的端口VLAN ID！
        # Subtype 2: Port Protocol VLAN ID
        # Subtype 3: VLAN Name
        # Subtype 4: Protocol Identity
        # Subtype 5: VID Usage Digest
        # Subtype 6: Management VLAN
        # Subtype 7: Link Aggregation
        # Subtype 8-11: Reserved
        # Subtype 12: Maximum Frame Size

        # Subtype 1: Port VLAN ID TLV (IEEE 802.1Q标准)
        if subtype == 1:
            print(f"[DEBUG] 🎯 Port VLAN ID TLV detected (IEEE 802.1Q subtype 1)!")
            if len(val) >= 6:
                # TLV格式：
                # Byte 0-2: OUI (00:80:c2)
                # Byte 3: Subtype (1)
                # Byte 4-5: VLAN ID (2-byte big-endian)
                # Byte 6+: Optional flags

                vlan_id = int.from_bytes(val[4:6], 'big')
                print(f"[DEBUG] ✅ Extracted VLAN ID: {vlan_id}")

                tagged = False
                is_pvid = False

                if len(val) >= 7:
                    flags_byte = val[6]
                    print(f"[DEBUG] Flags byte: 0x{flags_byte:02x}")
                    tagged = bool(flags_byte & 0x01)
                    is_pvid = bool(flags_byte & 0x02)
                    print(f"[DEBUG] Tagged: {tagged}, Is PVID: {is_pvid}")

                # 🔧 修复：不在此时查找VLAN名称（因为VLAN Name TLV可能还没解析）
                # VLAN名称关联将在所有TLV解析完成后进行
                device.port_vlan = VLANInfo(
                    vlan_id=vlan_id,
                    vlan_name=None,  # 稍后关联
                    tagged=tagged,
                    is_pvid=is_pvid
                )
                print(f"[DEBUG] ✅✅✅ Port VLAN ID {vlan_id} stored to device.port_vlan!")
            else:
                print(f"[DEBUG] ❌ Port VLAN ID TLV too short: {len(val)} bytes")
            return

        # Subtype 2: Port Protocol VLAN ID
        elif subtype == 2:
            print(f"[DEBUG] Port Protocol VLAN ID TLV")
            if len(val) >= 6:
                protocol_vlan_id = int.from_bytes(val[4:6], 'big')
                print(f"[DEBUG] Protocol VLAN ID: {protocol_vlan_id}")
                # 存储到设备对象
                device.protocol_vlan_id = protocol_vlan_id

        # Subtype 3: VLAN Name
        elif subtype == 3:
            print(f"[DEBUG] VLAN Name TLV")
            if len(val) >= 6:
                vlan_id = int.from_bytes(val[4:6], 'big')
                vlan_name_bytes = val[6:]

                print(f"[DEBUG] VLAN Name raw bytes: {vlan_name_bytes.hex()}")

                # 🔍 修复VLAN名称编码问题 - 逐步清理
                vlan_name = None

                # 方法1：尝试ASCII清理（移除不可打印字符）
                try:
                    cleaned = []
                    for byte in vlan_name_bytes:
                        if 32 <= byte <= 126:  # 可打印ASCII范围
                            cleaned.append(chr(byte))
                    ascii_result = ''.join(cleaned).strip()
                    if ascii_result and len(ascii_result) > 0:
                        vlan_name = ascii_result
                        print(f"[DEBUG] VLAN {vlan_id}: {vlan_name} (ASCII cleaned)")
                except Exception as e:
                    print(f"[DEBUG] ASCII cleaning failed: {e}")

                # 方法2：如果ASCII清理失败，尝试UTF-8
                if not vlan_name:
                    try:
                        vlan_name = vlan_name_bytes.decode('utf-8', errors='ignore').strip()
                        # 再次清理，移除任何控制字符
                        vlan_name = ''.join(c for c in vlan_name if c.isprintable() or c.isspace()).strip()
                        print(f"[DEBUG] VLAN {vlan_id}: {vlan_name} (UTF-8 cleaned)")
                    except Exception as e:
                        print(f"[DEBUG] UTF-8 decoding failed: {e}")

                # 最终回退：使用原始字节表示
                if not vlan_name:
                    vlan_name = f"<{vlan_name_bytes.hex()}>"
                    print(f"[DEBUG] VLAN {vlan_id}: {vlan_name} (hex fallback)")

                device.vlans.append(VLANInfo(
                    vlan_id=vlan_id,
                    vlan_name=vlan_name
                ))

        # Subtype 4: Protocol Identity
        elif subtype == 4:
            print(f"[DEBUG] Protocol Identity TLV")
            # Protocol identity - could parse specific protocols

        # Subtype 5: VID Usage Digest
        elif subtype == 5:
            print(f"[DEBUG] VID Usage Digest TLV")

        # Subtype 6: Management VLAN
        elif subtype == 6:
            print(f"[DEBUG] Management VLAN TLV")

        # Subtype 7: Link Aggregation
        elif subtype == 7:
            print(f"[DEBUG] Link Aggregation TLV (802.1Q)")
            # Link aggregation info

        # Subtype 8-11: Reserved
        elif 8 <= subtype <= 11:
            print(f"[DEBUG] Reserved 802.1Q subtype {subtype}")

        # Subtype 12: Maximum Frame Size
        elif subtype == 12:
            print(f"[DEBUG] Maximum Frame Size TLV")
            if len(val) >= 6:
                device.max_frame_size = int.from_bytes(val[4:6], 'big')
                print(f"[DEBUG] Max frame size: {device.max_frame_size} bytes")

        # Unknown subtypes
        else:
            print(f"[DEBUG] Unknown IEEE 802.1Q subtype {subtype}")

    def _parse_802_3_tlv(self, device: LLDPDevice, subtype: int, val: bytes):
        """Parse IEEE 802.3 specific TLV"""
        from .model import MACPHYConfig, LinkAggregationInfo

        # Subtype 1: MAC/PHY Configuration/Status
        if subtype == 1 and len(val) >= 5:
            autoneg_support = (val[4] >> 1) & 0x01
            autoneg_status = val[4] & 0x01

            # Store old format for compatibility
            device.autonegotiation = {
                "supported": bool(autoneg_support),
                "enabled": bool(autoneg_status)
            }

            # Enhanced MAC/PHY configuration
            if len(val) >= 5:
                macphy = MACPHYConfig()
                macphy.autoneg_support = bool(autoneg_support)
                macphy.autoneg_enabled = bool(autoneg_status)

                # Parse operational MAU type if available (byte 5)
                if len(val) >= 6:
                    mau_type = val[5]
                    macphy.operational_mau_type = mau_type
                    macphy.speed, macphy.duplex = self._parse_mau_type(mau_type)

                # Parse supported speeds from capabilities
                if len(val) >= 5:
                    macphy.supported_speeds = self._parse_supported_speeds(val)

                device.macphy_config = macphy

        # Subtype 2: Power Via MDI (PoE) - H3C使用subtype 2而不是标准的subtype 3
        elif subtype == 2 and len(val) >= 4:
            device.poe = self._parse_poe_tlv(val)

        # Subtype 4: Link Aggregation (IEEE 802.3ad)
        elif subtype == 4 and len(val) >= 5:
            link_agg = LinkAggregationInfo()
            link_agg.supported = True

            # Status byte (byte 4)
            status_byte = val[4]
            link_agg.enabled = bool(status_byte & 0x01)  # bit 0: aggregation status

            # Aggregation capability (bit 1-2)
            agg_capability = (status_byte >> 1) & 0x03
            if agg_capability == 1 and len(val) >= 7:
                # Ready and has aggregation ID
                link_agg.aggregation_id = int.from_bytes(val[5:7], 'big')
                link_agg.aggregation_port_count = len(val) - 7  # Approximate

            device.link_aggregation = link_agg

        # Subtype 5: Maximum Frame Size
        elif subtype == 5 and len(val) >= 6:
            device.max_frame_size = int.from_bytes(val[4:6], 'big')

    def _parse_h3c_private_tlv(self, device: LLDPDevice, subtype: int, val: bytes):
        """Parse H3C Private TLV (OUI: 00:12:bb)"""
        print(f"[DEBUG] H3C Private TLV - subtype={subtype}, length={len(val)}")
        print(f"[DEBUG] H3C Private TLV raw data: {val.hex()}")

        # H3C Private TLV subtype mapping table (修正版本)
        H3C_SUBTYPE_MAP = {
            0x01: {"name": "实际功率信息", "field": "actual_power"},  # 修正：不是VLAN！
            0x04: {"name": "未知", "field": None},
            0x05: {"name": "硬件版本(简短)", "field": "hw_version_short"},
            0x06: {"name": "硬件版本(数字)", "field": "hw_version_numeric"},
            0x07: {"name": "软件版本", "field": "software_version"},
            0x08: {"name": "序列号", "field": "serial_number"},
            0x09: {"name": "厂商", "field": "manufacturer"},
            0x0a: {"name": "产品型号", "field": "product_model"},
            0x0b: {"name": "未知", "field": None},
        }

        try:
            if subtype in H3C_SUBTYPE_MAP:
                subtype_info = H3C_SUBTYPE_MAP[subtype]
                field_name = subtype_info["field"]

                print(f"[DEBUG] H3C subtype {subtype} ({subtype_info['name']})")
                print(f"[DEBUG] Raw bytes: {val.hex()}")

                # 提取字符串值 - 修复编码问题
                # 跳过OUI和subtype字节 (前4字节)
                payload = val[4:] if len(val) > 4 else b''

                # 尝试多种编码方式
                string_value = None
                for encoding in ['utf-8', 'gbk', 'ascii', 'latin-1']:
                    try:
                        decoded = payload.decode(encoding, errors='strict').strip()
                        if decoded and len(decoded) > 0:
                            # 检查是否包含可打印字符
                            if any(c.isprintable() and not c.isspace() for c in decoded):
                                string_value = decoded
                                print(f"[DEBUG] String value ({encoding}): {string_value}")
                                break
                    except (UnicodeDecodeError, UnicodeError):
                        continue

                # 如果所有编码都失败，尝试忽略错误的ASCII解码
                if not string_value:
                    string_value = payload.decode('ascii', errors='ignore').strip()
                    print(f"[DEBUG] String value (fallback): {string_value}")

                if field_name:
                    setattr(device, field_name, string_value if string_value else val.hex())

            else:
                print(f"[DEBUG] H3C Unknown subtype {subtype}: {val.hex()}")

        except Exception as e:
            print(f"[DEBUG] Error parsing H3C private TLV: {e}")

    def _parse_cisco_private_tlv(self, device: LLDPDevice, subtype: int, val: bytes):
        """Parse Cisco Private TLV (OUI: 00:00:0c)"""
        print(f"[DEBUG] Cisco Private TLV - subtype={subtype}, length={len(val)}")
        # TODO: Implement Cisco-specific TLV parsing

    def _parse_huawei_private_tlv(self, device: LLDPDevice, subtype: int, val: bytes):
        """Parse Huawei Private TLV (OUI: 00:1e:ec)"""
        print(f"[DEBUG] Huawei Private TLV - subtype={subtype}, length={len(val)}")
        # TODO: Implement Huawei-specific TLV parsing

    def _parse_vendor_private_tlv(self, device: LLDPDevice, vendor_name: str, subtype: int, val: bytes):
        """Parse Generic Vendor Private TLV"""
        print(f"[DEBUG] {vendor_name} Private TLV - subtype={subtype}, length={len(val)}")

        try:
            # Generic parsing for unknown vendor TLVs
            if len(val) >= 4:
                # Try to extract string values - 修复编码问题
                payload = val[4:] if len(val) > 4 else b''
                string_value = None

                # 尝试多种编码方式
                for encoding in ['utf-8', 'gbk', 'ascii', 'latin-1']:
                    try:
                        decoded = payload.decode(encoding, errors='strict').strip()
                        if decoded and len(decoded) > 0:
                            if any(c.isprintable() and not c.isspace() for c in decoded):
                                string_value = decoded
                                break
                    except (UnicodeDecodeError, UnicodeError):
                        continue

                # Fallback to ASCII with error ignoring
                if not string_value:
                    string_value = payload.decode('ascii', errors='ignore').strip()

                if string_value and len(string_value) > 0:
                    print(f"[DEBUG] {vendor_name} subtype {subtype}: {string_value}")

                    # Store as vendor-specific attribute
                    field_name = f"{vendor_name.lower()}_subtype_{subtype}"
                    setattr(device, field_name, string_value)

        except Exception as e:
            print(f"[DEBUG] Error parsing {vendor_name} private TLV: {e}")

    def _parse_poe_tlv(self, val: bytes) -> PoEInfo:
        """Parse PoE TLV (IEEE 802.3 or H3C custom format)"""
        poe = PoEInfo()
        poe.supported = True

        print(f"[DEBUG] PoE TLV raw data: {val.hex()}")

        if len(val) >= 4:
            # 第4个字节（index 3）是Port Power Status/Control byte
            port_power_byte = val[3]
            print(f"[DEBUG] Port Power byte: 0x{port_power_byte:02x}")

            # 解析Port Power字节（IEEE 802.3at标准）
            # Bit 0-1: Power type (00=Type 1, 01=Type 2, 10-11=Reserved)
            power_type_val = (port_power_byte >> 0) & 0x03
            if power_type_val == 0:
                poe.power_type = "Type 1"
            elif power_type_val == 1:
                poe.power_type = "Type 2"
            else:
                poe.power_type = f"Type {power_type_val}"

            # Bit 2-3: Dual signature flags
            dual_sig = (port_power_byte >> 2) & 0x03
            if dual_sig == 1:
                poe.power_source = "Primary PSE (主供电)"
            elif dual_sig == 2:
                poe.power_source = "Backup PSE (备用供电)"

            # Bit 4-5: Pair control (Signal/Spare)
            pair_control = (port_power_byte >> 4) & 0x03
            if pair_control == 1:
                poe.pair_control = "Signal pair (信号对)"
            elif pair_control == 2:
                poe.pair_control = "Spare pair (备用对)"

            # Bit 6-7: Power class
            power_class = (port_power_byte >> 6) & 0x03
            if power_class in [1, 2, 3, 4]:
                poe.power_class = f"Class {power_class}"
            elif power_class == 0:
                poe.power_class = "Class 0 (低功率)"

            # 检查是否有功率值（某些厂商格式可能包含）
            if len(val) >= 8:
                # 尝试解析功率值（可能是big-endian 2字节）
                power_mw = int.from_bytes(val[4:6], 'big')
                if power_mw > 0 and power_mw < 100000:  # 合理的功率范围
                    poe.power_allocated = power_mw
                    print(f"[DEBUG] Power value: {power_mw}mW ({power_mw/1000}W)")

            print(f"[DEBUG] PoE parsed - Type: {poe.power_type}, Class: {poe.power_class}, Source: {poe.power_source}")

        return poe

    @staticmethod
    def _format_mac(mac_hex: str) -> str:
        """Format MAC address to standard format"""
        if not mac_hex or len(mac_hex) < 12:
            return mac_hex

        # Remove existing separators
        clean_hex = mac_hex.replace(":", "").replace("-", "").replace(".", "")

        # Ensure we have exactly 12 hex digits
        if len(clean_hex) != 12:
            return mac_hex

        # Format as XX:XX:XX:XX:XX:XX
        return ":".join([clean_hex[i:i+2] for i in range(0, 12, 2)]).lower()

    @staticmethod
    def _parse_mau_type(mau_type: int) -> tuple:
        """Parse MAU type to speed and duplex"""
        # Extended MAU type mapping (IEEE 802.3)
        mau_mapping = {
            # 10 Mbps
            0x0000: ("10M", "Half"),
            0x0001: ("10M", "Full"),
            0x0002: ("100M", "Half"),
            0x0003: ("100M", "Full"),
            0x0004: ("1G", "Half"),
            0x0005: ("1G", "Full"),
            # 10 Gbps
            0x0006: ("10G", "Full"),
            0x0007: ("2.5G", "Full"),
            0x0008: ("5G", "Full"),
            0x0009: ("40G", "Full"),
            0x000A: ("100G", "Full"),
            # Common operational types
            0x0016: ("10G", "Full"),  # 10GBASE-R
            0x001E: ("10G", "Full"),  # 10GBASE-T
            0x001D: ("1G", "Full"),   # 1000BASE-T
            0x0015: ("1G", "Full"),   # 1000BASE-X
            0x000F: ("100M", "Full"), # 100BASE-TX
            0x0010: ("10G", "Full"),  # 10GBASE-SR
            0x0011: ("10G", "Full"),  # 10GBASE-LR
            0x0017: ("40G", "Full"),  # 40GBASE-SR4
            0x0018: ("40G", "Full"),  # 40GBASE-LR4
            # Common copper types
            0x001A: ("10G", "Full"),  # 10GBASE-CX4
            0x001C: ("25G", "Full"),  # 25GBASE-CR
            0x001F: ("25G", "Full"),  # 25GBASE-SR
        }

        return mau_mapping.get(mau_type, (None, None))

    def _parse_lldp_med_tlv(self, device: LLDPDevice, subtype: int, val: bytes):
        """Parse LLDP-MED specific TLV (ANSI/TIA-1057)"""
        print(f"[DEBUG] LLDP-MED TLV detected, subtype={subtype}")

        # Subtype 1: LLDP-MED Capabilities
        if subtype == 1 and len(val) >= 5:
            print(f"[DEBUG] LLDP-MED Capabilities: {val.hex()}")
            self._parse_med_capabilities_tlv(device, val)

        # Subtype 2: Network Policy
        elif subtype == 2 and len(val) >= 5:
            print(f"[DEBUG] LLDP-MED Network Policy: {val.hex()}")
            # 可以解析网络策略（VLAN, QoS等），包含VLAN ID和应用类型

        # Subtype 3: Power via MDI (PoE信息！)
        elif subtype == 3 and len(val) >= 5:
            print(f"[DEBUG] LLDP-MED Power via MDI (PoE): {val.hex()}")
            self._parse_med_power_tlv(device, val)

        # Subtype 4: Inventory (硬件/固件版本)
        elif subtype == 4 and len(val) >= 4:
            print(f"[DEBUG] LLDP-MED Inventory: {val.hex()}")

        # Subtype 5-7: Location Identification
        elif 5 <= subtype <= 7:
            print(f"[DEBUG] LLDP-MED Location (type={subtype}): {val.hex()}")

        # Subtype 8: Extended Power via MDI (PoE+)
        elif subtype == 8 and len(val) >= 5:
            print(f"[DEBUG] LLDP-MED Extended Power via MDI (PoE+): {val.hex()}")
            self._parse_med_extended_power_tlv(device, val)

        # 未知subtype
        else:
            print(f"[DEBUG] LLDP-MED unknown subtype {subtype}: {val.hex()}")

    def _parse_med_capabilities_tlv(self, device: LLDPDevice, val: bytes):
        """Parse LLDP-MED Capabilities TLV (Subtype 1)"""
        if len(val) < 5:
            return

        try:
            # LLDP-MED Capabilities TLV format (ANSI/TIA-1057):
            # Byte 0-2: OUI (00:80:c2 for IEEE)
            # Byte 3: Subtype (1)
            # Byte 4: LLDP-MED Version
            # Byte 5: Device Capabilities (bit field)

            med_version = val[4]
            capabilities_byte = val[5] if len(val) > 5 else 0

            # LLDP-MED capability bits
            capabilities = []
            if capabilities_byte & 0x01:  # Bit 0
                capabilities.append("能力交换")
            if capabilities_byte & 0x02:  # Bit 1
                capabilities.append("网络策略")
            if capabilities_byte & 0x04:  # Bit 2
                capabilities.append("网络策略配置")
            if capabilities_byte & 0x08:  # Bit 3
                capabilities.append("PoE供电")
            if capabilities_byte & 0x10:  # Bit 4
                capabilities.append("库存信息")
            if capabilities_byte & 0x20:  # Bit 5
                capabilities.append("位置识别")

            print(f"[DEBUG] LLDP-MED Version: {med_version}")
            print(f"[DEBUG] LLDP-MED Capabilities: {', '.join(capabilities) if capabilities else '无'}")

            # Store MED capabilities as device attribute
            if not hasattr(device, 'lldp_med_capabilities'):
                device.lldp_med_capabilities = {
                    'version': med_version,
                    'capabilities': capabilities
                }
            else:
                device.lldp_med_capabilities = {
                    'version': med_version,
                    'capabilities': capabilities
                }

        except Exception as e:
            print(f"[DEBUG] Error parsing LLDP-MED capabilities: {e}")

    def _parse_med_power_tlv(self, device: LLDPDevice, val: bytes):
        """Parse LLDP-MED Power via MDI TLV (Subtype 3)"""
        if len(val) < 5:
            return

        # LLDP-MED Power via MDI TLV格式：
        # Byte 0-2: OUI + Subtype (已在调用时处理)
        # Byte 3: Length (已在调用时处理)
        # Byte 4: Power Type and Priority
        power_byte = val[4]

        # Bit 7-6: Power source
        power_source = (power_byte >> 6) & 0x03
        # Bit 5-4: Power priority
        power_priority = (power_byte >> 4) & 0x03
        # Bit 3-0: Power value (0-15.4W in 0.1W increments)
        power_value = power_byte & 0x0F

        # 更新PoE信息
        if not device.poe or not device.poe.supported:
            device.poe = PoEInfo()
            device.poe.supported = True

        # 解析电源类型
        if power_source == 0:
            device.poe.power_source = "电源设备(PSE)"
        elif power_source == 1:
            device.poe.power_source = "受电设备(PD)"
        else:
            device.poe.power_source = "未知"

        # 解析电源优先级
        priority_map = {0: "未知", 1: "低", 2: "高", 3: "关键"}
        device.poe.power_priority = priority_map.get(power_priority, "未知")

        # 解析功率值
        if power_value > 0:
            device.poe.power_requested = power_value * 100  # 转换为毫瓦
            device.poe.power_allocated = power_value * 100

        # 检查是否有扩展功率信息 (PoE+)
        if len(val) >= 7:
            # Byte 5-6: Power source in milliwatts (big-endian)
            power_mw = int.from_bytes(val[5:7], 'big')
            if power_mw > 0:
                device.poe.power_allocated = power_mw
                print(f"[DEBUG] MED PoE+ - Total Power: {power_mw}mW ({power_mw/1000}W)")

        print(f"[DEBUG] MED PoE - Type: {device.poe.power_source}, Priority: {device.poe.power_priority}, Power: {power_value * 0.1}W")

    def _parse_med_extended_power_tlv(self, device: LLDPDevice, val: bytes):
        """Parse LLDP-MED Extended Power via MDI TLV (PoE+)"""
        if len(val) < 7:
            return

        # Byte 3-4: Total power in milliwatts
        total_power = int.from_bytes(val[3:5], 'big')

        if not device.poe or not device.poe.supported:
            device.poe = PoEInfo()
            device.poe.supported = True

        device.poe.power_allocated = total_power
        print(f"[DEBUG] MED Extended PoE+ - Total Power: {total_power}mW ({total_power/1000}W)")

    def _associate_vlan_names(self, device: 'LLDPDevice'):
        """
        在所有TLV解析完成后，重新关联VLAN名称到Port VLAN ID
        修复解析顺序导致的VLAN名称关联失败问题
        """
        if hasattr(device, 'port_vlan') and device.port_vlan and hasattr(device, 'vlans') and device.vlans:
            port_vlan_id = device.port_vlan.vlan_id

            # 从vlans列表中查找匹配的VLAN名称
            for v in device.vlans:
                if hasattr(v, 'vlan_id') and v.vlan_id == port_vlan_id:
                    if hasattr(v, 'vlan_name') and v.vlan_name and not device.port_vlan.vlan_name:
                        device.port_vlan.vlan_name = v.vlan_name
                        print(f"[DEBUG] 🔧 Post-parse associated VLAN name: {port_vlan_id} -> {v.vlan_name}")
                        break

    @staticmethod
    def _parse_supported_speeds(val: bytes) -> List[str]:
        """Parse supported speeds from MAC/PHY capabilities"""
        speeds = []

        # Check common speed capabilities based on operational type
        # This is a simplified approach - real implementation would parse capability bits
        if len(val) >= 6:
            mau_type = val[5]

            # Map common MAU types to their supported speeds
            mau_speed_map = {
                # 100M devices typically support 10M as well
                0x000F: ["10M", "100M"],           # 100BASE-TX
                0x0003: ["10M", "100M"],           # 100BASE-FX

                # 1G devices typically support 10M/100M/1G
                0x0005: ["10M", "100M", "1G"],      # 1000BASE-T
                0x0015: ["1G"],                    # 1000BASE-X
                0x001D: ["10M", "100M", "1G"],      # 1000BASE-T

                # 10G devices
                0x001E: ["10M", "100M", "1G", "10G"],  # 10GBASE-T
                0x0016: ["10G"],                   # 10GBASE-R
                0x0010: ["10G"],                   # 10GBASE-SR
                0x0011: ["10G"],                   # 10GBASE-LR

                # Higher speed devices
                0x001C: ["10G", "25G"],             # 25GBASE-CR
                0x001F: ["10G", "25G"],             # 25GBASE-SR
                0x0017: ["10G", "40G"],             # 40GBASE-SR4
                0x0018: ["10G", "40G"],             # 40GBASE-LR4
                0x0009: ["40G"],                   # 40GBASE
                0x000A: ["40G", "100G"],            # 100GBASE
            }

            if mau_type in mau_speed_map:
                speeds = mau_speed_map[mau_type]
            else:
                # Fallback: try to determine from MAU type
                if mau_type >= 0x0016:  # Generally 10G+
                    speeds = ["10M", "100M", "1G", "10G"]
                elif mau_type >= 0x0005:  # 1G+
                    speeds = ["10M", "100M", "1G"]
                elif mau_type >= 0x0002:  # 100M+
                    speeds = ["10M", "100M"]
                else:
                    speeds = ["10M"]

        return speeds
