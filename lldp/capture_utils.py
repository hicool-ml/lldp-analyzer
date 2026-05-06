"""Shared helpers for packet capture backends."""

from typing import Any


def normalize_interface_name(interface: Any) -> str:
    """Return the OS/backend interface name from a UI object or string."""
    if interface is None:
        raise ValueError("interface is required")

    name = getattr(interface, "name", None)
    if name:
        return str(name)

    return str(interface)


def describe_interface(interface: Any) -> str:
    """Return a human-friendly interface label for logs and UI metadata."""
    description = getattr(interface, "description", None)
    if description:
        return str(description)

    return normalize_interface_name(interface)
