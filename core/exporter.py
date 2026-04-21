"""
LLDP Data Exporter
Export discovered devices to various formats
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List

from lldp.model import LLDPDevice


class LLDPExporter:
    """
    Export LLDP device data to various formats
    """

    @staticmethod
    def to_json(devices: List[LLDPDevice], filepath: str, pretty: bool = True):
        """
        Export devices to JSON file

        Args:
            devices: List of LLDPDevice objects
            filepath: Output file path
            pretty: Pretty-print JSON
        """
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "device_count": len(devices),
            "devices": [device.to_dict() for device in devices]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)

    @staticmethod
    def to_csv(devices: List[LLDPDevice], filepath: str):
        """
        Export devices to CSV file

        Args:
            devices: List of LLDPDevice objects
            filepath: Output file path
        """
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "System Name",
                "Chassis ID",
                "Chassis Type",
                "Port ID",
                "Port Type",
                "Management IP",
                "Port VLAN",
                "PoE Supported",
                "PoE Type",
                "PoE Class",
                "802.1X Enabled",
                "Capabilities",
                "Last Seen"
            ])

            # Rows
            for device in devices:
                writer.writerow([
                    device.system_name or "",
                    device.chassis_id.value if device.chassis_id else "",
                    device.chassis_id.type.name if device.chassis_id else "",
                    device.port_id.value if device.port_id else "",
                    device.port_id.type.name if device.port_id else "",
                    device.management_ip or "",
                    str(device.port_vlan.vlan_id) if device.port_vlan else "",
                    "Yes" if device.poe.supported else "No",
                    device.poe.power_type or "",
                    device.poe.power_class or "",
                    "Yes" if device.dot1x.enabled else "No",
                    ",".join(device.capabilities.get_enabled_capabilities()),
                    device.last_seen.isoformat()
                ])

    @staticmethod
    def to_xml(devices: List[LLDPDevice], filepath: str):
        """
        Export devices to XML file

        Args:
            devices: List of LLDPDevice objects
            filepath: Output file path
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<lldp_discovery>\n')
            f.write(f'  <export_timestamp>{datetime.now().isoformat()}</export_timestamp>\n')
            f.write(f'  <device_count>{len(devices)}</device_count>\n')
            f.write('  <devices>\n')

            for device in devices:
                f.write('    <device>\n')

                if device.system_name:
                    f.write(f'      <system_name>{device.system_name}</system_name>\n')

                if device.chassis_id:
                    f.write(f'      <chassis_id>\n')
                    f.write(f'        <value>{device.chassis_id.value}</value>\n')
                    f.write(f'        <type>{device.chassis_id.type.name}</type>\n')
                    f.write(f'      </chassis_id>\n')

                if device.port_id:
                    f.write(f'      <port_id>\n')
                    f.write(f'        <value>{device.port_id.value}</value>\n')
                    f.write(f'        <type>{device.port_id.type.name}</type>\n')
                    f.write(f'      </port_id>\n')

                if device.management_ip:
                    f.write(f'      <management_ip>{device.management_ip}</management_ip>\n')

                if device.port_vlan:
                    f.write(f'      <port_vlan>{device.port_vlan.vlan_id}</port_vlan>\n')

                if device.poe.supported:
                    f.write(f'      <poe>\n')
                    f.write(f'        <supported>true</supported>\n')
                    if device.poe.power_type:
                        f.write(f'        <type>{device.poe.power_type}</type>\n')
                    if device.poe.power_class:
                        f.write(f'        <class>{device.poe.power_class}</class>\n')
                    f.write(f'      </poe>\n')

                f.write('    </device>\n')

            f.write('  </devices>\n')
            f.write('</lldp_discovery>\n')

    @staticmethod
    def to_zabbix(devices: List[LLDPDevice], filepath: str):
        """
        Export to Zabbix LLD format

        Args:
            devices: List of LLDPDevice objects
            filepath: Output file path
        """
        # Zabbix Low-Level Discovery format
        lld_data = []

        for device in devices:
            item = {
                "{#LLDP_SYSNAME}": device.system_name or "",
                "{#LLDP_CHASSIS_ID}": device.chassis_id.value if device.chassis_id else "",
                "{#LLDP_MGMT_IP}": device.management_ip or "",
                "{#LLDP_PORT}": device.port_description or "",
            }
            lld_data.append(item)

        zabbix_data = {
            "data": lld_data
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(zabbix_data, f, indent=2, ensure_ascii=False)
