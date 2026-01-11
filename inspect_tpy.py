import xml.etree.ElementTree as ET

tree = ET.parse('plc_data/TwinCAT_Project.tpy')
root = tree.getroot()

symbols = root.findall('.//Symbol')[:5]

for i, s in enumerate(symbols):
    name_elem = s.find('Name')
    name = name_elem.text if name_elem is not None else "N/A"

    print(f'\n=== Symbol {i+1}: {name} ===')
    print(f'Direct children tags: {[child.tag for child in s]}')
    print(f'SubItems found: {len(s.findall("./SubItem"))}')

    # Zeige ersten SubItem
    first_subitem = s.find('./SubItem')
    if first_subitem is not None:
        sub_name_elem = first_subitem.find('Name')
        sub_name = sub_name_elem.text if sub_name_elem is not None else "N/A"
        print(f'First SubItem: {sub_name}')
        print(f'SubItem tags: {[child.tag for child in first_subitem]}')
