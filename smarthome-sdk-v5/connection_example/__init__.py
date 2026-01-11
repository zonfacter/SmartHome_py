"""
Custom Connection Example

Zeigt wie man eigene Verbindungstypen erstellt
"""

from .main import CustomTCPConnection, register_with_connection_manager

__version__ = "1.0.0"
__author__ = "TwinCAT Team"

# Export
__all__ = ['CustomTCPConnection', 'register_with_connection_manager']
