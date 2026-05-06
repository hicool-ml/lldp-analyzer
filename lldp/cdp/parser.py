"""
CDP Protocol Parser
Pure function parser - No side effects, no UI dependencies
"""

import logging
import struct
from typing import Optional
from .model import CDPDevice, CDPNetworkAddress, CDPCapabilities, CDPTLVType

logger = logging.getLogger(__name__)
MAX_HEX_DISPLAY = 200


class CDPParser:
    """
    CDP Protocol Parser

    Pure function parser that converts raw CDP packets to CDPDevice objects.
    Thread-safe, no side effects, no UI dependencies.
    """

    # CDP protocol constants
    CDP_DEST_MAC = bytes([0x01, 0x00, 0x0C, 0xCC, 0xCC, 0xCC])
    CDP_ETHERTYPE = bytes([0x20, 0x00])  # SNAP encapsulation

    def __init__(self):
        """Initialize parser"""
        logger.debug("CDP Parser initialized")
        logger.debug("CDP Destination MAC: %s", self.CDP_DEST_MAC.hex())
        logger.debug("CDP EtherType: %s", self.CDP_ETHERTYPE.hex())

    def is_cdp_packet(self, packet_data: bytes) -> bool:
        """
        Check if packet is CDP protocol

        Args:
            packet_data: Raw packet bytes (from Ethernet layer)

        Returns:
            True if packet is CDP
        """
        if len(packet_data) < 14:
            return False

        # Check destination MAC (CDP multicast address)
        dest_mac = packet_data[0:6]
        if dest_mac != self.CDP_DEST_MAC:
            return False

        # Check EtherType (should be 0x2000 for CDP SNAP)
        ether_type = packet_data[12:14]
        if ether_type != self.CDP_ETHERTYPE:
            return False

        return True

    def parse_packet(self, packet_data: bytes) -> Optional[CDPDevice]:
        """
        Parse CDP packet data

        Args:
            packet_data: Raw CDP packet bytes (after Ethernet header)

        Returns:
            CDPDevice object or None if parsing fails
        """
        if not self.is_cdp_packet(packet_data):
            return None

        # Skip Ethernet header (14 bytes)
        cdp_data = packet_data[14:]

        if len(cdp_data) < 4:
            return None

        device = CDPDevice()

        logger.debug("========== CDP Packet Parsing ==========")
        logger.debug("CDP packet length: %d bytes", len(cdp_data))
        logger.debug("Raw CDP data: %s", cdp_data[:MAX_HEX_DISPLAY].hex())

        try:
            # CDP header format:
            # Version (1 byte) - should be 2
            # TTL (1 byte) - holdtime in seconds
            # Checksum (2 bytes)

            version = cdp_data[0]
            ttl = cdp_data[1]
            # checksum = cdp_data[2:4]  # Skip checksum for now

            logger.debug("CDP Version: %d", version)
            logger.debug("CDP TTL: %d seconds", ttl)

            if version != 2:
                logger.debug("Unknown CDP version: %d", version)
                return None

            device.ttl = ttl

            # Parse TLVs starting from offset 4
            offset = 4
            tlv_count = 0

            while offset + 4 <= len(cdp_data):
                tlv_type = struct.unpack(">H", cdp_data[offset : offset + 2])[0]
                tlv_length = struct.unpack(">H", cdp_data[offset + 2 : offset + 4])[0]

                if tlv_length < 4:
                    logger.debug("Invalid TLV length: %d", tlv_length)
                    break

                tlv_value = cdp_data[offset + 4 : offset + tlv_length]

                tlv_count += 1
                logger.debug(
                    "TLV #%d: Type=0x%04X (%s), Length=%d",
                    tlv_count,
                    tlv_type,
                    self._get_tlv_name(tlv_type),
                    tlv_length,
                )

                # Parse the TLV
                self._parse_tlv(device, tlv_type, tlv_value)

                # Move to next TLV
                offset += tlv_length

                # Alignment: TLVs are aligned to 4-byte boundaries
                if offset % 4 != 0:
                    offset += 4 - (offset % 4)

            logger.debug("Total TLVs parsed: %d", tlv_count)
            logger.debug("=======================================")

            if device.is_valid():
                logger.debug("Valid CDP device parsed: %s", device.get_display_name())
                # 🔥 关键修复：设置协议标识，确保正确识别
                device.protocol = "CDP"
                return device
            else:
                logger.debug("CDP device is not valid")
                return None

        except Exception as e:
            logger.debug("Error parsing CDP packet: %s", e, exc_info=True)
            return None

    def _parse_tlv(self, device: CDPDevice, tlv_type: int, tlv_value: bytes):
        """Parse individual CDP TLV"""
        try:
            # Device ID (Hostname)
            if tlv_type == CDPTLVType.DEVICE_ID.value:
                device.device_id = tlv_value.decode("ascii", errors="ignore").strip()
                logger.debug("Device ID: %s", device.device_id)

            # Port ID
            elif tlv_type == CDPTLVType.PORT_ID.value:
                device.port_id = tlv_value.decode("ascii", errors="ignore").strip()
                logger.debug("Port ID: %s", device.port_id)

            # Software Version
            elif tlv_type == CDPTLVType.SOFTWARE_VERSION.value:
                device.software_version = tlv_value.decode(
                    "ascii", errors="ignore"
                ).strip()
                logger.debug("Software Version: %s...", device.software_version[:100])

            # Platform
            elif tlv_type == CDPTLVType.PLATFORM.value:
                device.platform = tlv_value.decode("ascii", errors="ignore").strip()
                logger.debug("Platform: %s", device.platform)

            # Native VLAN (关键！)
            elif tlv_type == CDPTLVType.NATIVE_VLAN.value:
                if len(tlv_value) >= 2:
                    device.native_vlan = struct.unpack(">H", tlv_value[:2])[0]
                    logger.debug("Native VLAN: %s", device.native_vlan)

            # Voice VLAN
            elif tlv_type == CDPTLVType.VOICE_VLAN.value:
                if len(tlv_value) >= 2:
                    device.voice_vlan = struct.unpack(">H", tlv_value[:2])[0]
                    logger.debug("Voice VLAN: %s", device.voice_vlan)

            # Capabilities
            elif tlv_type == CDPTLVType.CAPABILITIES.value:
                device.capabilities = self._parse_capabilities(tlv_value)

            # Duplex
            elif tlv_type == CDPTLVType.DUPLEX.value:
                if len(tlv_value) >= 1:
                    duplex_value = tlv_value[0]
                    device.duplex = "全双工" if duplex_value == 0x01 else "半双工"
                    logger.debug("Duplex: %s", device.duplex)

            # MTU
            elif tlv_type == CDPTLVType.MTU.value:
                if len(tlv_value) >= 4:
                    device.mtu = struct.unpack(">I", tlv_value[:4])[0]
                    logger.debug("MTU: %s", device.mtu)

            # System Name
            elif tlv_type == CDPTLVType.SYSTEM_NAME.value:
                device.system_name = tlv_value.decode("ascii", errors="ignore").strip()
                logger.debug("System Name: %s", device.system_name)

            # Management Addresses
            elif tlv_type == CDPTLVType.MANAGEMENT_ADDRESSES.value:
                addresses = self._parse_management_addresses(tlv_value)
                if addresses:
                    device.management_addresses.extend(addresses)
                    logger.debug(
                        "Management Addresses: %s", [addr.address for addr in addresses]
                    )

            # Network Addresses
            elif tlv_type == CDPTLVType.ADDRESSES.value:
                addresses = self._parse_network_addresses(tlv_value)
                if addresses:
                    device.addresses.extend(addresses)
                    logger.debug(
                        "Network Addresses: %s", [addr.address for addr in addresses]
                    )

            # Physical Location
            elif tlv_type == CDPTLVType.PHYSICAL_LOCATION.value:
                device.physical_location = tlv_value.decode(
                    "ascii", errors="ignore"
                ).strip()
                logger.debug("Physical Location: %s", device.physical_location)

            # Power Available
            elif tlv_type == CDPTLVType.POWER_AVAILABLE.value:
                if len(tlv_value) >= 2:
                    power_value = struct.unpack(">H", tlv_value[:2])[0]
                    device.power_available = f"{power_value} mW"
                    logger.debug("Power Available: %s", device.power_available)

            else:
                logger.debug(
                    "Unknown TLV type 0x%04X: %s...", tlv_type, tlv_value.hex()[:50]
                )

        except Exception as e:
            logger.debug("Error parsing TLV 0x%04X: %s", tlv_type, e, exc_info=True)

    def _parse_capabilities(self, tlv_value: bytes) -> CDPCapabilities:
        """Parse Capabilities TLV"""
        caps = CDPCapabilities()

        if len(tlv_value) < 4:
            return caps

        # Capabilities bitmap format:
        # Type (2 bytes) + Length (2 bytes) + Capabilities (4 bytes) + Enabled Capabilities (4 bytes)

        # First 4 bytes: supported capabilities
        supported = struct.unpack(">I", tlv_value[:4])[0]

        # Next 4 bytes: enabled capabilities (if present)
        (struct.unpack(">I", tlv_value[4:8])[0] if len(tlv_value) >= 8 else supported)

        # Parse capabilities bits
        caps.router = bool(supported & 0x01)
        caps.transparent_bridge = bool(supported & 0x02)
        caps.source_route_bridge = bool(supported & 0x04)
        caps.switch = bool(supported & 0x08)
        caps.host = bool(supported & 0x10)
        caps.igmp_filter = bool(supported & 0x20)
        caps.repeater = bool(supported & 0x40)

        logger.debug(
            "Capabilities: Router=%s, Switch=%s, Bridge=%s",
            caps.router,
            caps.switch,
            caps.transparent_bridge,
        )

        return caps

    def _parse_management_addresses(self, tlv_value: bytes) -> list:
        """Parse Management Addresses TLV"""
        addresses = []

        try:
            if len(tlv_value) < 4:
                return addresses

            # Number of addresses
            num_addresses = tlv_value[0]

            offset = 1
            for i in range(num_addresses):
                if offset + 4 > len(tlv_value):
                    break

                # Address type and length
                addr_type = tlv_value[offset]
                addr_len = tlv_value[offset + 1]

                # Parse IPv4
                if addr_type == 0x01 and addr_len == 4 and offset + 5 <= len(tlv_value):
                    ip_bytes = tlv_value[offset + 2 : offset + 6]
                    ip_address = ".".join(map(str, ip_bytes))
                    addresses.append(CDPNetworkAddress("IPv4", ip_address))
                    logger.debug("Management IPv4: %s", ip_address)

                offset += 2 + addr_len

        except Exception as e:
            logger.debug("Error parsing management addresses: %s", e, exc_info=True)

        return addresses

    def _parse_network_addresses(self, tlv_value: bytes) -> list:
        """Parse Network Addresses TLV"""
        addresses = []

        try:
            if len(tlv_value) < 4:
                return addresses

            # Number of addresses
            num_addresses = struct.unpack(">I", tlv_value[:4])[0]

            offset = 4
            for i in range(num_addresses):
                if offset + 4 > len(tlv_value):
                    break

                # Address type and length
                addr_type = tlv_value[offset]
                addr_len = tlv_value[offset + 1]

                # Parse IPv4
                if addr_type == 0x01 and addr_len == 4 and offset + 5 <= len(tlv_value):
                    ip_bytes = tlv_value[offset + 2 : offset + 6]
                    ip_address = ".".join(map(str, ip_bytes))
                    addresses.append(CDPNetworkAddress("IPv4", ip_address))

                offset += 2 + addr_len

        except Exception as e:
            logger.debug("Error parsing network addresses: %s", e, exc_info=True)

        return addresses

    def _get_tlv_name(self, tlv_type: int) -> str:
        """Get human-readable TLV name"""
        try:
            tlv_enum = CDPTLVType(tlv_type)
            return tlv_enum.name.replace("_", " ")
        except ValueError:
            return f"Unknown ({tlv_type})"

    def parse_scapy_packet(self, pkt) -> Optional[CDPDevice]:
        """
        Parse CDP packet from Scapy packet object

        Args:
            pkt: Scapy packet object

        Returns:
            CDPDevice object or None if parsing fails
        """
        try:
            # Convert Scapy packet to bytes
            packet_bytes = bytes(pkt)

            if self.is_cdp_packet(packet_bytes):
                return self.parse_packet(packet_bytes)

        except Exception as e:
            logger.debug("Error parsing Scapy CDP packet: %s", e, exc_info=True)

        return None
