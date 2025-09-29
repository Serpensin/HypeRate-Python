"""
HypeRate package for connecting to HypeRate WebSocket API.

This package provides a client for connecting to HypeRate's real-time heartbeat
and clip data service via WebSocket.
"""

# __init__.py for hyperate package
from .hyperate import HypeRate, Device

__version__ = "1.0.0"
__all__ = ['HypeRate', 'Device']
