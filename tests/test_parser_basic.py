"""
LLDP Parser - Basic Unit Tests
测试LLDP解析器的基本功能和边界情况
"""

import pytest
from lldp.parser import LLDPParser
from lldp.model import DeviceCapabilities, ChassisIDType, PortIDType


class TestLLDPParserBasics:
    """LLDP解析器基础测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.parser = LLDPParser()

    def test_parse_empty_packet(self):
        """测试空包"""
        result = self.parser.parse_packet(b"")
        assert result is None

    def test_parse_incomplete_header(self):
        """测试不完整的TLV header (只有1字节)"""
        result = self.parser.parse_packet(b"\x00")
        assert result is None

    def test_parse_tlv_length_exceeds_packet(self):
        """测试TLV长度超过包长度 - 边界检查"""
        # 构造一个声称有100字节长度但实际只有10字节的包
        packet = bytes(
            [
                0x02,
                0x64,  # Type=2, Length=100 (声称100字节)
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,  # 只有8字节数据
            ]
        )
        result = self.parser.parse_packet(packet)
        # 应该安全返回None，不会崩溃
        assert result is None

    def test_parse_tlv_max_length_protection(self):
        """测试超大TLV长度 - DoS防护"""
        # 构造一个声称有MAX_TLV_LENGTH+1字节的包
        from lldp.parser import MAX_TLV_LENGTH

        large_length = MAX_TLV_LENGTH + 1
        packet = bytes(
            [
                0x02,
                (large_length >> 8) & 0xFF,
                large_length & 0xFF,  # 超大长度
            ]
        ) + bytes(
            10
        )  # 少量数据
        result = self.parser.parse_packet(packet)
        # 应该被拒绝，防止DoS攻击
        assert result is None

    def test_parse_end_tlv_stops_parsing(self):
        """测试End TLV (type=0) 立即停止解析"""
        # 构造一个包含End TLV的包
        packet = bytes(
            [
                0x02,
                0x03,
                0x01,
                0x02,
                0x03,  # 一个有效TLV
                0x00,
                0x00,  # End of LLDPDU
                0xFF,
                0xFF,
                0xFF,
                0xFF,  # 垃圾数据（应该被忽略）
            ]
        )
        result = self.parser.parse_packet(packet)
        # 应该成功解析，不读取垃圾数据
        assert result is not None


class TestSystemCapabilities:
    """System Capabilities TLV测试"""

    def setup_method(self):
        self.parser = LLDPParser()

    def test_parse_capabilities_standard_4_bytes(self):
        """测试标准4字节Capabilities TLV"""
        # 前2字节：supported (Bridge + Router)
        # 后2字节：enabled (只有Bridge)
        tlv_value = bytes(
            [
                0x00,
                0x14,  # supported: Bit 2(Bridge) + Bit 4(Router) = 0x0014
                0x00,
                0x04,  # enabled: Bit 2(Bridge) = 0x0004
            ]
        )

        caps = self.parser._parse_capabilities(tlv_value)

        assert caps.bridge is True
        assert caps.router is True
        assert caps.wlan is False

        assert caps.bridge_enabled is True
        assert caps.router_enabled is False

    def test_parse_capabilities_too_short(self):
        """测试过短的Capabilities TLV"""
        tlv_value = bytes([0x00, 0x01])  # 只有2字节
        caps = self.parser._parse_capabilities(tlv_value)

        # 应该返回空的capabilities对象，不崩溃
        assert caps.bridge is False
        assert caps.router is False

    def test_parse_capabilities_all_bits(self):
        """测试所有能力位"""
        # 所有位都设为1
        tlv_value = bytes([0xFF, 0xFF, 0xFF, 0xFF])

        caps = self.parser._parse_capabilities(tlv_value)

        assert caps.bridge is True
        assert caps.router is True
        assert caps.wlan is True
        assert caps.repeater is True
        assert caps.telephone is True


class TestManagementAddress:
    """Management Address TLV测试"""

    def setup_method(self):
        self.parser = LLDPParser()

    def test_parse_management_address_ipv4(self):
        """测试IPv4管理地址解析"""
        # 按照IEEE 802.1AB标准：
        # octet 0: address length = 4
        # octets 1-4: IPv4 address
        tlv_value = bytes(
            [
                0x04,  # length = 4
                192,
                168,
                1,
                1,  # IPv4 address
            ]
        )

        result = self.parser._parse_management_address(tlv_value)

        assert result == "192.168.1.1"

    def test_parse_management_address_ipv6(self):
        """测试IPv6管理地址解析"""
        # IPv6 address (16字节)
        ipv6_bytes = bytes.fromhex("2001 0db8 85a3 0000 0000 8a2e 0370 7334")
        tlv_value = bytes([0x10]) + ipv6_bytes  # length = 16

        result = self.parser._parse_management_address(tlv_value)

        # 应该返回IPv6地址
        assert ":" in result
        assert "2001" in result

    def test_parse_management_address_mac(self):
        """测试MAC地址管理地址"""
        mac_bytes = bytes.fromhex("00 11 22 33 44 55")
        tlv_value = bytes([0x06]) + mac_bytes  # length = 6

        result = self.parser._parse_management_address(tlv_value)

        # 应该返回格式化的MAC地址
        assert ":" in result or "-" in result

    def test_parse_management_address_zero_length(self):
        """测试地址长度为0"""
        tlv_value = bytes([0x00])  # length = 0

        result = self.parser._parse_management_address(tlv_value)

        # 应该安全返回None
        assert result is None

    def test_parse_management_address_incomplete(self):
        """测试不完整的管理地址"""
        tlv_value = bytes([0x04, 0x01])  # 声称4字节，但只有1字节

        result = self.parser._parse_management_address(tlv_value)

        # 应该安全返回None，不崩溃
        assert result is None


class TestStandardLLDPStructure:
    """标准LLDP包结构测试"""

    def setup_method(self):
        self.parser = LLDPParser()

    def test_minimal_valid_lldp_packet(self):
        """测试最小有效LLDP包"""
        # 构造一个最小的有效LLDP包
        packet = bytes(
            [
                # Chassis ID TLV (Type=1, Length=7)
                0x02,
                0x07,  # Type=1, Length=7
                0x04,  # Chassis ID subtype = MAC address
                0x00,
                0x11,
                0x22,
                0x33,
                0x44,
                0x55,  # MAC address
                # Port ID TLV (Type=2, Length=3)
                0x04,
                0x03,  # Type=2, Length=3
                0x05,  # Port ID subtype = locally assigned
                0x31,
                0x32,  # Port ID = "12"
                # Time to Live TLV (Type=3, Length=2)
                0x06,
                0x02,  # Type=3, Length=2
                0x00,
                0x78,  # TTL = 120 seconds
                # End of LLDPDU TLV (Type=0, Length=0)
                0x00,
                0x00,
            ]
        )

        result = self.parser.parse_packet(packet)

        # 应该成功解析
        assert result is not None
        assert result.is_valid() is True

    def test_lldp_packet_without_end_tlv(self):
        """测试没有End TLV的包"""
        packet = bytes(
            [
                # Chassis ID TLV
                0x02,
                0x07,
                0x04,
                0x00,
                0x11,
                0x22,
                0x33,
                0x44,
                0x55,
                # Port ID TLV
                0x04,
                0x03,
                0x05,
                0x31,
                0x32,
                # Time to Live TLV
                0x06,
                0x02,
                0x00,
                0x78,
                # 故意省略End TLV
            ]
        )

        result = self.parser.parse_packet(packet)

        # 应该仍然成功解析（容错处理）
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
