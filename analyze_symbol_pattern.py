import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

tree = ET.parse('plc_data/HausAutomation.tpy')
root = tree.getroot()

# Analysiere Symbole mit Typ vs ohne Typ
all_symbols = root.findall('.//Symbol')

with_type = []
without_type = []

for s in all_symbols:
    name_elem = s.find('Name')
    name = name_elem.text if name_elem is not None and name_elem.text else ""

    type_elem = s.find('Type')
    typ = type_elem.text if type_elem is not None and type_elem.text else ""

    if typ and typ.strip() and typ != "N/A":
        with_type.append((name, typ))
    else:
        without_type.append(name)

print(f'Symbole MIT Type: {len(with_type)}')
print(f'Symbole OHNE Type: {len(without_type)}')

print(f'\nErste 10 MIT Type:')
for name, typ in with_type[:10]:
    print(f'  "{name}" → {typ}')

print(f'\nErste 10 OHNE Type:')
for name in without_type[:10]:
    print(f'  "{name}"')

# Prüfe ob Symbole mit "." im Namen direkte SubItems haben
print(f'\n\nPrüfe ob hierarchische Symbole SubItems haben:')
hierarchical = [s for s in all_symbols if '.' in (s.find('Name').text or '')]
print(f'Symbole mit "." im Namen: {len(hierarchical)}')

has_subitems = 0
for s in hierarchical[:10]:
    name_elem = s.find('Name')
    name = name_elem.text if name_elem is not None else ""
    subitems = s.findall('./SubItem')
    if len(subitems) > 0:
        has_subitems += 1
        print(f'  "{name}" hat {len(subitems)} SubItems')

print(f'\nVon ersten 10 hierarchischen Symbolen haben {has_subitems} SubItems')
