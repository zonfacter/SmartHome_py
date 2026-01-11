"""
Bluetooth Module v5.0.0

Bluetooth Low Energy (BLE) Support
"""

from .bluetooth_manager import BluetoothConnection, register_bluetooth_connection

__version__ = "5.0.0"
__all__ = ['BluetoothConnection', 'register_bluetooth_connection']
