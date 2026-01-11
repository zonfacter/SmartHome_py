import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

tree = ET.parse('plc_data/HausAutomation.tpy')
root = tree.getroot()

# Zeige erste 10 Symbole mit Namen und Typ
symbols = root.findall('.//Symbol')[:10]

print(f'\nErste 10 Symbole:\n')
for i, s in enumerate(symbols, 1):
    name_elem = s.find('Name')
    name = name_elem.text if name_elem is not None and name_elem.text else "N/A"

    type_elem = s.find('Type')
    typ = type_elem.text if type_elem is not None and type_elem.text else "N/A"

    # Prüfe ob Symbol SubItems hat
    subitems = s.findall('./SubItem')

    print(f'{i}. Name: "{name}"')
    print(f'   Type: "{typ}"')
    print(f'   Hat SubItems: {len(subitems)}')
    print()
