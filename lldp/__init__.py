"""
LLDP Network Analyzer - Industrial Grade Architecture
"""

__version__ = "3.0.0-copilot"
__author__ = "LLDP Network Team"

from .model import LLDPDevice, LLDPChassisID, LLDPPortID
from .parser import LLDPParser

# Force use of Copilot's capture adapter (ignore old capture module)
from .capture_adapter import LLDPCaptureListener
from .capture_dpkt import HybridCapture as LLDPCapture

__all__ = [
    "LLDPDevice",
    "LLDPCapture",
    "LLDPCaptureListener",
    "LLDPChassisID",
    "LLDPParser",
    "LLDPPortID",
]
