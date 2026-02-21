"""
Routing Example Plugin

Demonstriert die Nutzung des Universal Data Routers (v4.6.0)
"""

from .main import RoutingExamplePlugin

__version__ = "1.0.0"
__author__ = "TwinCAT Team"

# Export Plugin-Klasse für Auto-Discovery
__all__ = ['RoutingExamplePlugin']
