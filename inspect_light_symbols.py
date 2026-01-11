import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

tree = ET.parse('plc_data/HausAutomation.tpy')
root = tree.getroot()

# Finde alle Symbole die "Light" enthalten
all_symbols = root.findall('.//Symbol')
light_symbols = [s for s in all_symbols if 'Light' in (s.find('Name').text or '')]

print(f'\nGefunden: {len(light_symbols)} Symbole mit "Light"\n')

for i, s in enumerate(light_symbols[:5], 1):
    name_elem = s.find('Name')
    name = name_elem.text if name_elem is not None and name_elem.text else "N/A"

    type_elem = s.find('Type')
    typ = type_elem.text if type_elem is not None and type_elem.text else "N/A"

    print(f'{i}. Name: "{name}"')
    print(f'   Type: "{typ}"')
    print()

# Suche nach "Light" DataType
datatypes = root.findall('.//DataTypes/DataType')
for dt in datatypes:
    dt_name_elem = dt.find('Name')
    dt_name = dt_name_elem.text if dt_name_elem is not None else ""

    if 'Light' in dt_name or 'FB_Light' in dt_name:
        print(f'\n=== DataType: {dt_name} ===')
        subitems = dt.findall('./SubItem')
        print(f'SubItems: {len(subitems)}')
        for si in subitems[:5]:
            si_name_elem = si.find('Name')
            si_name = si_name_elem.text if si_name_elem is not None else "N/A"
            si_type_elem = si.find('Type')
            si_type = si_type_elem.text if si_type_elem is not None else "N/A"
            print(f'  - {si_name}: {si_type}')
