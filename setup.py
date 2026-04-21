"""
LLDP Network Analyzer - Setup Script
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lldp-analyzer",
    version="1.0.0",
    author="LLDP Network Team",
    description="Professional LLDP Network Discovery Tool with Clean Architecture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/lldp-analyzer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Networking",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "scapy>=2.4.5",
    ],
    entry_points={
        "console_scripts": [
            "lldp-analyzer=ui.cli:main",
            "lldp-gui=main_gui:main",
        ],
    },
)
