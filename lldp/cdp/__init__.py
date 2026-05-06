"""
CDP Protocol Module
Cisco Discovery Protocol support
"""

from .model import CDPDevice
from .parser import CDPParser

__all__ = ["CDPDevice", "CDPParser"]
