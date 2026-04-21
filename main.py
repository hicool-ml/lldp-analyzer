"""
LLDP Network Analyzer - CLI Entry Point
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.cli import main

if __name__ == "__main__":
    main()
