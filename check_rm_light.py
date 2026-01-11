import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

tree = ET.parse('plc_data/HausAutomation.tpy')
root = tree.getroot()

symbols = root.findall('.//Symbol')
target = [s for s in symbols if 'RM_Light_OG_Bad' in (s.find('Name').text or '')]

print(f'Gefunden: {len(target)} Symbole mit "RM_Light_OG_Bad"\n')

for i, s in enumerate(target, 1):
    name_elem = s.find('Name')
    name = name_elem.text if name_elem is not None else "None"

    type_elem = s.find('Type')
    if type_elem is not None:
        typ = type_elem.text if type_elem.text else "(LEER)"
    else:
        typ = "(KEIN TYPE ELEMENT)"

    print(f'{i}. Name: "{name}"')
    print(f'   Type: "{typ}"')
    print(f'   Type stripped: "{typ.strip() if isinstance(typ, str) else typ}"')
    print()
