import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

tree = ET.parse('plc_data/HausAutomation.tpy')
root = tree.getroot()

symbols = root.findall('.//Symbol')

# Gruppiere Light-Symbole nach Namen
light_symbols = {}

for s in symbols:
    name_elem = s.find('Name')
    name = name_elem.text if name_elem is not None and name_elem.text else ""

    if not name.startswith('Light.'):
        continue

    type_elem = s.find('Type')
    if type_elem is not None and type_elem.text:
        typ = type_elem.text.strip()
    else:
        typ = "NO_TYPE"

    if name not in light_symbols:
        light_symbols[name] = []

    light_symbols[name].append(typ)

# Zeige Symbole mit mehreren Type-Einträgen
print('Symbole mit mehreren Type-Einträgen:\n')
multi_type = {k: v for k, v in light_symbols.items() if len(v) > 1}
print(f'Gefunden: {len(multi_type)} von {len(light_symbols)}\n')

for name, types in list(multi_type.items())[:10]:
    print(f'{name}')
    print(f'  Types: {types}')

# Zähle Type-Kombinationen
print(f'\n\nType-Statistik für Light-Symbole:')
type_counts = {}
for name, types in light_symbols.items():
    type_key = tuple(sorted(types))
    type_counts[type_key] = type_counts.get(type_key, 0) + 1

for types, count in sorted(type_counts.items(), key=lambda x: -x[1])[:10]:
    print(f'{count:3d}x: {types}')
