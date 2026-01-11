import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

tree = ET.parse('plc_data/TwinCAT_Project.tpy')
root = tree.getroot()

# Suche DataTypes
datatypes = root.findall('.//DataTypes/DataType')
print(f'\nGefundene DataTypes: {len(datatypes)}')

# Zeige erste 5 DataTypes mit SubItems
count = 0
for dt in datatypes:
    name_elem = dt.find('Name')
    name = name_elem.text if name_elem is not None else "N/A"

    subitems = dt.findall('./SubItem')
    if len(subitems) > 0:
        print(f'\n=== DataType: {name} ===')
        print(f'SubItems: {len(subitems)}')

        # Zeige erste 3 SubItems
        for i, si in enumerate(subitems[:3]):
            si_name_elem = si.find('Name')
            si_name = si_name_elem.text if si_name_elem is not None else "N/A"
            si_type_elem = si.find('Type')
            si_type = si_type_elem.text if si_type_elem is not None else "N/A"
            print(f'  - {si_name}: {si_type}')

        count += 1
        if count >= 5:
            break

# Zeige ein Symbol
print('\n\nBeispiel-Symbol:')
symbols = root.findall('.//Symbol')[:1]
for s in symbols:
    name_elem = s.find('Name')
    name = name_elem.text if name_elem is not None else "N/A"
    type_elem = s.find('Type')
    typ = type_elem.text if type_elem is not None else "N/A"
    print(f'Name: {name}')
    print(f'Type: {typ}')
    print(f'Tags: {[child.tag for child in s]}')
