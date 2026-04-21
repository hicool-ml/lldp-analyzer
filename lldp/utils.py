"""
LLDP Analyzer Utility Functions
Common helper functions
"""


def safe_get(obj, attr, default=None):
    """
    Safe attribute access - eliminates hasattr spam

    Args:
        obj: Object to access
        attr: Attribute name
        default: Default value if attribute doesn't exist

    Returns:
        Attribute value or default
    """
    return getattr(obj, attr, default) if obj else default
