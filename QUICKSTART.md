# LLDP Network Analyzer - Quick Start Guide

## 🚀 30 Second Quick Start

### Prerequisites

- Python 3.8+
- Scapy (`pip install scapy`)
- Npcap (Windows) or libpcap (Linux/Mac)

### Installation

```bash
# Navigate to directory
cd lldp_analyzer

# Install dependencies
pip install -r requirements.txt

# (Optional) Install as package
pip install -e .
```

---

## 📱 Usage

### GUI Mode (Windows)

```bash
python main_gui.py
```

**Or if installed:**
```bash
lldp-gui
```

**Steps:**
1. Select network adapter
2. Click "开始捕获" (Start Capture)
3. Wait for LLDP devices to appear
4. Click "导出" (Export) to save results

### CLI Mode (All Platforms)

```bash
python main.py
```

**Or if installed:**
```bash
lldp-analyzer
```

**Common Options:**

```bash
# Specify interface
lldp-analyzer -i eth0

# Custom duration (60 seconds)
lldp-analyzer -d 60

# Export to JSON
lldp-analyzer -f json -o discovery.json

# Export to CSV
lldp-analyzer -f csv -o discovery.csv

# List available interfaces
lldp-analyzer --list-interfaces
```

---

## 📊 Output Examples

### Table Output (Default)

```
╔════════════════════════════════════════════════════════════════════╗
║                        Device Details                              ║
╚════════════════════════════════════════════════════════════════════╝

📋 Device #1
──────────────────────────────────────────────────────────────────────
设备MAC地址: aa:bb:cc:dd:ee:ff
系统名称: Core-Switch-01
系统描述: Huawei S5735-L48T4S-A
端口标识: GigabitEthernet1/0/1
管理地址: 192.168.1.254
端口VLAN: 2011
PoE: 支持 (Class 0)
能力: BRIDGE, ROUTER
```

### JSON Output

```json
{
  "timestamp": "2026-04-17T14:30:00",
  "device_count": 1,
  "devices": [
    {
      "chassis_id": {
        "value": "aa:bb:cc:dd:ee:ff",
        "type": "MAC_ADDRESS"
      },
      "system_name": "Core-Switch-01",
      "management_ip": "192.168.1.254",
      "port_vlan": {
        "vlan_id": 2011,
        "tagged": false
      }
    }
  ]
}
```

---

## 🎯 Key Features

### ✅ Real-time Discovery
- Devices appear as soon as they're discovered
- No need to wait for full capture duration
- Progress bar shows capture status

### ✅ Multiple Export Formats
- **JSON** - For APIs and databases
- **CSV** - For spreadsheets
- **XML** - For legacy systems
- **Zabbix** - For monitoring integration

### ✅ Professional Architecture
- Clean 3-tier separation
- Thread-safe capture
- Pure function parser
- Type-safe models

---

## 🔧 Troubleshooting

### "No interfaces found"

**Windows:**
- Install Npcap: https://npcap.com/
- Run as Administrator
- Check network connection

**Linux:**
```bash
# Check permissions
sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)
```

### "No LLDP devices found"

- Check physical connection
- Verify switch supports LLDP
- Confirm LLDP is enabled on switch
- Try different port

### "Permission denied"

```bash
# Linux/Mac: Run with sudo
sudo lldp-analyzer

# Windows: Run as Administrator
right-click → Run as Administrator
```

---

## 📚 Next Steps

1. **Read the full documentation**: [README.md](README.md)
2. **Understand the architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
3. **Check source code**: Explore `lldp/`, `ui/`, `core/` directories
4. **Build EXE**: Run `python build.py`

---

## 🆚 Comparison with Old Version

| Feature | Old Version | New Version |
|---------|-------------|-------------|
| Architecture | Mixed (UI+Parser+Capture) | Clean 3-tier |
| Thread Safety | ❌ Shared state | ✅ Queue-based |
| Testability | ❌ Hard to test | ✅ Pure functions |
| CLI Mode | ❌ No | ✅ Yes |
| Export | ❌ Limited | ✅ JSON/CSV/XML/Zabbix |
| Data Model | ❌ Dict | ✅ Structured classes |
| Extensibility | ❌ Monolithic | ✅ Modular |

---

## 💡 Tips

1. **Use CLI for automation**:
   ```bash
   lldp-analyzer -f json -o discovery.json
   # Parse JSON in your scripts
   ```

2. **Use GUI for interactive use**:
   ```bash
   lldp-gui
   # Real-time updates, export to any format
   ```

3. **Monitor continuously**:
   ```bash
   # Run in background
   lldp-analyzer -d 3600 -f json -o discovery.json &
   ```

4. **Integrate with monitoring**:
   ```bash
   # Export to Zabbix format
   lldp-analyzer -f zabbix -o zabbix_lldp.json
   ```

---

**Need Help?**
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Run `lldp-analyzer --help` for CLI options
- See source code comments for implementation details

---

**Version**: 1.0.0
**Status**: Production Ready
**Architecture**: Industrial Grade
