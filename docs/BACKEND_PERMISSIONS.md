# Capture Backend Permissions Guide

## Overview

The LLDP Analyzer supports multiple capture backends, each with different permission requirements:

1. **PCAPBackend** (pcapy-ng) - Cross-platform, requires Npcap/libpcap
2. **AFPacketBackend** (Linux AF_PACKET) - Linux-only, requires raw socket permissions
3. **Scapy Fallback** - Cross-platform, requires administrator/root privileges

---

## PCAPBackend (pcapy-ng)

### Windows

**Requirements:**
- Npcap (recommended) or WinPcap
- Administrator privileges (or Npcap installed with "Install Npcap in Service Mode")

**Installation:**
1. Download Npcap from https://npcap.com/#download
2. During installation, enable:
   - ✅ Install Npcap in Service Mode (recommended)
   - ✅ Support raw 802.11 traffic (optional, for wireless capture)

**Running without Administrator:**
If Npcap is installed in Service Mode, you may run without administrator privileges.

### Linux

**Requirements:**
- libpcap development files
- pcapy-ng Python package

**Installation:**
```bash
# Ubuntu/Debian
sudo apt-get install libpcap-dev
pip install pcapy-ng

# RHEL/CentOS
sudo yum install libpcap-devel
pip install pcapy-ng

# Fedora
sudo dnf install libpcap-devel
pip install pcapy-ng
```

**Permissions:**
```bash
# Option 1: Run as root (simple but not recommended)
sudo python your_script.py

# Option 2: Grant CAP_NET_RAW capability (recommended)
sudo setcap cap_net_raw+ep $(which python)

# Verify capability
getcap $(which python)
# Expected output: /usr/bin/python3 cap_net_raw+ep
```

### macOS

**Requirements:**
- libpcap (usually pre-installed)
- pcapy-ng Python package

**Installation:**
```bash
pip install pcapy-ng
```

**Permissions:**
```bash
# Must run as root
sudo python your_script.py
```

---

## AFPacketBackend (Linux AF_PACKET)

**Platform:** Linux only

**Requirements:**
- Linux kernel 2.2+
- Raw socket permissions (CAP_NET_RAW)

**Advantages:**
- ✅ No external dependencies (pure Python + standard library)
- ✅ Lightweight (no libpcap/pcapy required)
- ✅ Good performance on Linux

**Permissions Setup:**

### Option 1: Capability-based (Recommended)
```bash
# Grant CAP_NET_RAW capability to Python
sudo setcap cap_net_raw+ep $(which python)

# Verify capability
getcap $(which python)
# Expected output: /usr/bin/python3 cap_net_raw+ep

# Now you can run without root
python your_script.py
```

### Option 2: SetUID (Not Recommended)
```bash
# ⚠️ Security risk: Avoid this method
sudo chmod +s $(which python)
```

### Option 3: Run as Root
```bash
# Simple but not recommended for security
sudo python your_script.py
```

**Checking Permissions:**
```python
import os
if os.geteuid() != 0:
    print("Warning: Not running as root. May lack raw socket permissions.")
```

**Troubleshooting:**
```bash
# Check if Python has CAP_NET_RAW
getcap $(which python)

# Check current user capabilities
capsh --print

# Check if you can create raw sockets
python3 -c "import socket; s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW); print('OK')"
```

---

## Scapy Fallback

**Requirements:**
- Scapy Python package
- Administrator/root privileges

**Installation:**
```bash
pip install scapy
```

**Permissions:**
Same as PCAPBackend requirements for your platform.

**Windows:**
- Run as Administrator
- Install Npcap with "Install Npcap in Service Mode"

**Linux/macOS:**
```bash
sudo python your_script.py
```

---

## Backend Selection Logic

The LLDP Analyzer automatically selects the best available backend:

1. **PCAPBackend** (if pcapy-ng available)
2. **AFPacketBackend** (if on Linux and pcapy not available)
3. **Scapy Fallback** (if Scapy available)

**Manual Backend Selection:**
```python
from lldp.capture_dpkt import HybridCapture

capture = HybridCapture()

# Force specific backend (advanced usage)
from lldp.capture_backends import PCAPBackend, AFPacketBackend

# Use PCAPBackend
capture.backend = PCAPBackend()

# Use AFPacketBackend (Linux only)
capture.backend = AFPacketBackend()
```

---

## Security Considerations

### CAP_NET_RAW Capability
**What it does:**
- Allows creation of raw sockets
- Required for packet capture and injection
- Less privileged than full root access

**Risks:**
- Can capture network traffic
- Can inject arbitrary packets
- Should only be granted to trusted applications

**Best Practices:**
- ✅ Grant CAP_NET_RAW only to specific Python interpreter used
- ✅ Remove capability when not needed: `sudo setcap -r $(which python)`
- ✅ Use virtual environments to isolate permissions
- ❌ Avoid running production services as root

### Service Mode Installation
**Npcap Service Mode (Windows):**
- Installs Npcap as a Windows service
- Allows non-administrators to capture packets
- Convenient but may expose network traffic to all users

**Recommendation:**
- Development: ✅ Service Mode (convenient)
- Production: ❌ Install without Service Mode, require Administrator

---

## Troubleshooting

### "Permission denied" or "Operation not permitted"
```bash
# Linux: Grant CAP_NET_RAW
sudo setcap cap_net_raw+ep $(which python)

# Windows: Run as Administrator
# Right-click -> Run as Administrator

# macOS: Run as root
sudo python your_script.py
```

### "No capture backend available"
```bash
# Install missing dependencies
pip install pcapy-ng  # For PCAPBackend
pip install scapy     # For Scapy fallback

# Linux: Install libpcap development files
sudo apt-get install libpcap-dev  # Ubuntu/Debian
sudo yum install libpcap-devel    # RHEL/CentOS
```

### "pcapy not found" but pcapy-ng is installed
```bash
# Uninstall old pcapy (if installed)
pip uninstall pcapy

# Install pcapy-ng
pip install pcapy-ng
```

### AF_PACKET backend not working on Linux
```bash
# Check if running on Linux
python -c "import platform; print(platform.system())"

# Verify Python has CAP_NET_RAW
getcap $(which python)

# Grant capability if missing
sudo setcap cap_net_raw+ep $(which python)
```

---

## Development and Testing

### Unit Tests (No Permissions Required)
```bash
# Run unit tests (no actual packet capture)
pytest tests/test_capture_dpkt_threading.py -v
pytest tests/test_capture_dpkt_backend.py -v
```

### Integration Tests (Requires Permissions)
```bash
# Run integration tests with real packet capture
pytest tests/test_lldp_capture.py -v

# May require CAP_NET_RAW or root privileges
sudo pytest tests/test_lldp_capture.py -v
```

### CI/CD Considerations
```yaml
# GitHub Actions example
- name: Run tests
  run: |
    # Unit tests (no permissions needed)
    pytest tests/test_parser.py -v
    pytest tests/test_capture_dpkt_threading.py -v

    # Integration tests (skip in CI or use sudo)
    # pytest tests/test_lldp_capture.py -v  # Skip in CI
```

---

## Summary Table

| Backend | Platform | Dependencies | Permissions | Performance |
|---------|----------|--------------|-------------|-------------|
| PCAPBackend | Cross | pcapy-ng, libpcap/Npcap | Admin or CAP_NET_RAW | ⭐⭐⭐⭐ |
| AFPacketBackend | Linux only | None (stdlib) | CAP_NET_RAW or root | ⭐⭐⭐⭐⭐ |
| Scapy Fallback | Cross | scapy, libpcap/Npcap | Admin or CAP_NET_RAW | ⭐⭐⭐ |

**Recommended Setup:**
- **Development:** Use CAP_NET_RAW (Linux) or Service Mode (Windows)
- **Production:** Use specific user with CAP_NET_RAW, avoid root
- **CI/CD:** Run unit tests only, skip integration tests requiring privileges
