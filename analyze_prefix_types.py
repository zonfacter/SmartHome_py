import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

tree = ET.parse('plc_data/HausAutomation.tpy')
root = tree.getroot()

symbols = root.findall('.//Symbol')

# Gruppiere Symbole nach Präfix (erster Teil vor ".")
prefixes = {}

for s in symbols:
    name_elem = s.find('Name')
    name = name_elem.text if name_elem is not None and name_elem.text else ""

    type_elem = s.find('Type')
    typ = type_elem.text if type_elem is not None and type_elem.text else "N/A"

    if '.' in name:
        prefix = name.split('.')[0]
    else:
        prefix = "NO_DOT"

    if prefix not in prefixes:
        prefixes[prefix] = []

    prefixes[prefix].append((name, typ))

# Zeige Statistik
print(f'\nGefundene Präfixe: {len(prefixes)}\n')

for prefix in list(prefixes.keys())[:15]:
    items = prefixes[prefix]
    print(f'Prefix: "{prefix}" ({len(items)} Symbole)')

    # Zähle wie viele Types es gibt
    types_count = {}
    for name, typ in items:
        types_count[typ] = types_count.get(typ, 0) + 1

    print(f'  Types: {dict(sorted(types_count.items(), key=lambda x: -x[1])[:3])}')

    # Zeige erste 2 Beispiele
    for name, typ in items[:2]:
        print(f'    "{name}" -> {typ}')

    print()
