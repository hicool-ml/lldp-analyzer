# LLDP Network Analyzer v1.0.0

## 🏗️ Industrial Grade Architecture

**Professional LLDP Discovery Tool with Clean Architecture**

---

## ✨ Key Features

### Architecture Highlights

- **✅ Clean 3-Tier Separation**
  - Capture Layer → Parser Layer → UI Layer
  - Thread-safe queue-based design
  - Pure function protocol parser
  - No side effects, no UI dependencies

- **✅ Structured Data Models**
  - `LLDPDevice` dataclass
  - Type-safe enums
  - Immutable by design
  - Easy to serialize

- **✅ Multiple Interfaces**
  - Windows GUI (Tkinter)
  - CLI mode (Linux/Mac/Windows)
  - JSON/CSV/XML export
  - Zabbix LLD format

- **✅ Production Ready**
  - Thread-safe capture
  - Queue-based decoupling
  - Real-time updates
  - Device deduplication

---

## 📦 Installation

### Method 1: pip install (Recommended)

```bash
pip install -e .
```

This installs command-line tools:
- `lldp-analyzer` - CLI mode
- `lldp-gui` - GUI mode

### Method 2: Direct usage

```bash
# Clone repository
git clone https://github.com/yourusername/lldp-analyzer.git
cd lldp-analyzer

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Usage

### GUI Mode

```bash
python main_gui.py
```

Or if installed:
```bash
lldp-gui
```

**Features:**
- Real-time device discovery
- Progress tracking
- Multi-format export (JSON/CSV/XML/Zabbix)
- Device deduplication
- Structured display

### CLI Mode

```bash
python main.py
```

Or if installed:
```bash
lldp-analyzer
```

**Options:**
```bash
lldp-analyzer --help
```

**Examples:**

Discover LLDP devices:
```bash
lldp-analyzer
```

Specify interface:
```bash
lldp-analyzer -i eth0
```

Custom duration:
```bash
lldp-analyzer -d 60
```

Export to JSON:
```bash
lldp-analyzer -f json -o discovery.json
```

Export to CSV:
```bash
lldp-analyzer -f csv -o discovery.csv
```

List interfaces:
```bash
lldp-analyzer --list-interfaces
```

---

## 🏗️ Architecture

### Directory Structure

```
lldp_analyzer/
├── lldp/                    # Protocol layer (pure functions)
│   ├── __init__.py
│   ├── model.py             # Data models (LLDPDevice, etc.)
│   ├── parser.py            # Protocol parser (LLDPParser)
│   └── capture.py           # Packet capture (LLDPCapture)
│
├── ui/                      # Presentation layer
│   ├── __init__.py
│   ├── main_window.py       # GUI (Tkinter)
│   └── cli.py               # CLI interface
│
├── core/                    # Core functionality
│   ├── __init__.py
│   └── exporter.py          # Data export (JSON/CSV/XML)
│
├── main.py                  # CLI entry point
├── main_gui.py              # GUI entry point
├── setup.py                 # pip install support
└── README.md                # This file
```

### Data Flow

```
┌─────────────────┐
│  Capture Layer  │  Sniff packets → Queue
│  (capture.py)   │  Thread-safe, no UI deps
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Parser Layer   │  Raw bytes → LLDPDevice
│  (parser.py)    │  Pure function, no side effects
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Model Layer    │  Structured data models
│  (model.py)     │  Type-safe, serializable
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   UI Layer      │  Render device info
│ (main_window.py)│  GUI or CLI, read-only
└─────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**
   - Each layer has single responsibility
   - No cross-layer dependencies
   - Clean interfaces

2. **Thread Safety**
   - Capture thread → Queue → UI thread
   - No shared state
   - No race conditions

3. **Testability**
   - Parser is pure function
   - Models are dataclasses
   - Easy to unit test

4. **Extensibility**
   - Add new export formats
   - Add new UI modes
   - Add new protocol parsers

---

## 📊 Supported LLDP Features

### TLV Types

| TLV | Type | Support |
|-----|------|---------|
| Chassis ID | 1 | ✅ Full (all subtypes) |
| Port ID | 2 | ✅ Full (all subtypes) |
| Time to Live | 3 | ✅ Full |
| Port Description | 4 | ✅ Full |
| System Name | 5 | ✅ Full |
| System Description | 6 | ✅ Full |
| System Capabilities | 7 | ✅ Full |
| Management Address | 8 | ✅ Full |
| Org Specific (802.1Q) | 127 | ✅ VLAN |
| Org Specific (802.3) | 127 | ✅ PoE, MAC/PHY |

### Information Extracted

- **Device Identification**
  - Chassis ID (MAC/Name/Interface)
  - Port ID (MAC/Name/Interface)
  - System Name & Description

- **Network Configuration**
  - Management IP
  - Port VLAN (PVID)
  - VLAN Name
  - Tagged/Untagged

- **Power over Ethernet**
  - PoE Type (1/2)
  - Power Class (0-4)
  - Power Source (Primary/Backup)
  - Pair Control (Signal/Spare)

- **Device Capabilities**
  - Bridge, Router, Station
  - Repeater, Telephone
  - VLAN capabilities

---

## 🔧 Development

### Running Tests

```bash
# TODO: Add pytest tests
python -m pytest tests/
```

### Building EXE

```bash
# Build Windows GUI EXE
pyinstaller --onefile --windowed --name=LLDP_Analyzer main_gui.py

# Build CLI EXE
pyinstaller --onefile --name=lldp-analyzer main.py
```

---

## 📝 License

MIT License

---

## 🤝 Contributing

Contributions welcome! Please follow:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📞 Support

- Issues: https://github.com/yourusername/lldp-analyzer/issues
- Documentation: https://github.com/yourusername/lldp-analyzer/wiki

---

## 🎯 Roadmap

- [ ] Add LLDP-MED support
- [ ] Add CDP (Cisco Discovery Protocol) support
- [ ] Add topology visualization
- [ ] Add historical data tracking
- [ ] Add web interface
- [ ] Add REST API
- [ ] Add database storage
- [ ] Add real-time monitoring mode

---

**Version**: 1.0.0
**Status**: Production Ready
**Architecture**: Industrial Grade
**License**: MIT
