"""
BMS Parsers v5.0.0

Sammlung von BMS-Protokoll-Parsern
"""

from .jbd_parser import JBDParser

__version__ = "5.0.0"
__all__ = ['JBDParser']

# Weitere Parser werden automatisch registriert beim Import:
# - DalyParser (später)
# - JKParser (später)
# - ANTParser (später)
