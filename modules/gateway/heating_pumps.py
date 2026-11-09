"""Explain observed contacts and LPB field layouts without inventing attribute bits."""
import math
import re

WEEKDAYS = ('Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag')
SIGNALS = (
    ('space_request_raw', 'Heizungsanforderung · VG-RH', 'request', 4),
    ('dhw_request_raw', 'Warmwasseranforderung · VG-BW', 'request', 4),
    ('mixer_request_raw', 'Anforderung Verbrauchermischer · VM', 'request', 4),
    ('producer_request_raw', 'Anforderung Erzeugermischer · EM', 'request', 5),
    ('producer_lock_raw', 'Sperrsignal Erzeugergruppe · EG', 'percent', 2),
    ('transfer_lock_raw', 'Sperrsignal Erzeugermischer · EM', 'percent', 2),
    ('mixing_lock_raw', 'Sperrsignal Verbrauchermischer · VM', 'percent', 2),
    ('forced_producer_raw', 'Zwangssignal Erzeugergruppe · EG', 'percent', 2),
    ('forced_mixer_raw', 'Zwangssignal Erzeugermischer · EM', 'percent', 2),
    ('status_level_raw', 'Betriebsniveau Verbraucher · VE', 'level', 2),
)

# Only these exact object/layout combinations are covered by the reference.
# No propagation to producer-group 503/506, VM 505, EM request 501 or level 523.
LPB_DEFINITION_SOURCE = {
    'title': 'Brötje ISR MODBM · 7715040-06 (24.07.2019), Seiten 34–35',
    'url': 'https://forum.iobroker.net/assets/uploads/files/1676708238143-7715040-06-24072019-montageanleitung-modbus-busmodul-isr-modbm.pdf',
    'scope': 'LPB-Objektdefinition aus späterer Herstellerunterlage; Feldaufbau mit K/M-Profil abgeglichen. Keine unabhängige Bestätigung sämtlicher Wirkungen der alten Regler.',
}


def valid(metrics, key):
    item = metrics.get(key, {})
    return item.get('value') if item.get('quality') == 'valid' else None


def split_signal(key, label, kind, size, item):
    """Offsets/types come from the exact K/M APW; attribute semantics stay unknown."""
    result = {'key': key, 'label': label, 'quality': item.get('quality', 'pending'),
              'updated_at': item.get('updated_at'), 'raw': item.get('value'),
              'effective': None, 'attributes_hex': None, 'attribute_bits': [],
              'interpretation': 'Feldaufteilung bestätigt; Gültigkeit und Wirksamkeit offen.'}
    if result['quality'] != 'valid':
        return result
    try:
        payload = bytes.fromhex(result['raw'])
    except (ValueError, TypeError):
        result['quality'] = 'error'
        return result
    if len(payload) != size:
        result['quality'] = 'error'
        return result
    if kind == 'request':
        result['temperature_field'] = int.from_bytes(payload[:2], 'big', signed=True) / 64
        attribute = int.from_bytes(payload[2:4], 'big')
        result['attributes_hex'] = f'0x{attribute:04X}'
        if size == 5:
            result['priority_field'] = payload[4]
    else:
        result['value_field'] = int.from_bytes(payload[:1], 'big', signed=kind == 'percent')
        attribute = payload[1]
        result['attributes_hex'] = f'0x{attribute:02X}'
        if kind == 'percent':
            result['percent_field'] = result['value_field'] if 0 <= result['value_field'] <= 100 else None
    result['attribute_bits'] = [bit for bit in range(16 if kind == 'request' else 8) if attribute & (1 << bit)]
    definition = {'space_request_raw': (500, 'request', 4),
                  'transfer_lock_raw': (504, 'percent', 2),
                  'forced_mixer_raw': (507, 'percent', 2)}.get(key)
    if definition and (kind, size) == definition[1:]:
        result['lpb_object'] = definition[0]
        result['definition_source'] = LPB_DEFINITION_SOURCE
        result['protocol_valid'] = bool(attribute & 1)
        result['unknown_attribute_bits'] = [bit for bit in result['attribute_bits'] if bit > 1]
        if kind == 'request':
            result['transport_pump_requested'] = bool(attribute & 2) if attribute & 1 else None
            result['interpretation'] = ('Nach LPB-Definition gültige Wärmeanforderung.' if attribute & 1 else
                                        'Nach LPB-Definition keine gültige Wärmeanforderung; das Temperaturfeld allein ist kein Bedarf.')
        else:
            mandatory = bool(attribute & 2) if attribute & 1 else None
            result['mandatory'] = mandatory
            if not attribute & 1:
                result['interpretation'] = 'Nach LPB-Definition kein gültiges ' + ('Reduktionssignal.' if definition[0] == 504 else 'Zwangssignal.')
            elif result['percent_field'] is None:
                result['interpretation'] = 'Gültigkeitsbit gesetzt; Prozentfeld außerhalb des dokumentierten Bereichs. Wirkung offen.'
            elif definition[0] == 504:
                result['interpretation'] = f'Nach LPB-Definition gültige Reduktionsanforderung: {result["percent_field"]} %' + (' · zwingend.' if mandatory else ' · nicht zwingend.')
            else:
                result['interpretation'] = (f'Nach LPB-Definition Zwang an alle Verbraucher: {result["percent_field"]} %.' if mandatory else
                                            'Nach LPB-Definition nur Nachlauf angefordert; das Prozentfeld allein ist kein zwingender Prozentbefehl.')
        # effective deliberately remains None: a protocol flag does not establish
        # the physical effect or a unique pump switching cause.
    return result


def schedule_phase(metrics, days):
    """Use the controller's own weekday/time, never the VM's calendar or Tado plan."""
    clock = valid(metrics, 'clock')
    match = re.fullmatch(r'(\w+) (\d{2}):(\d{2})', clock or '')
    if not match or match[1] not in WEEKDAYS:
        return None
    hour, minute = int(match[2]), int(match[3])
    if hour > 23 or minute > 59:
        return None
    index = WEEKDAYS.index(match[1])
    if len(days) != 7:
        return None
    day = days[index]
    if day.get('quality') != 'valid' or day.get('label') != match[1] or not isinstance(day.get('periods'), list):
        return None
    current = hour * 60 + minute
    comfort = any(p['start_minute'] <= current < p['end_minute'] for p in day['periods'])
    return {'phase': 'comfort' if comfort else 'reduced', 'clock': clock,
            'label': 'Komfortphase' if comfort else 'Absenkphase'}


def diagnose(area, metrics, plant, days, now):
    pump = valid(metrics, 'pump')
    if type(pump) is not bool:
        pump = None
    mode = valid(metrics, 'mode')
    phase = schedule_phase(metrics, days) if mode == 'Automatik' else None
    facts, hints = [], []
    if mode:
        facts.append('Betriebsart: ' + mode + '.')
    if phase:
        facts.append('Zeitprogramm am Regler: ' + phase['label'] + ' (' + phase['clock'] + ').')
        if phase['phase'] == 'reduced':
            hints.append('Absenkphase bedeutet nicht automatisch Pumpen-Aus; der Regler kann weiterhin Wärme anfordern.')
    target = valid(metrics, 'room_setpoint')
    if type(target) in (int, float) and math.isfinite(target):
        facts.append(f'Aktueller Raumsollwert: {target:g} °C.')
    factor = valid(metrics, 'quick_setback')
    no_room_sensor = metrics.get('room_actual', {}).get('quality') == 'unavailable'
    if no_room_sensor and type(factor) in (int, float) and factor > 0 and pump is False and phase and phase['phase'] == 'reduced':
        hints.append(f'Schnellabsenkung ist möglich (KON-Einstellung {factor:g}). Nach einer Sollwertsenkung kann sie die Pumpe auch ohne Raumfühler anhalten. Ein aktiver Schnellabsenkungsstatus ist damit nicht bestätigt.')
    if valid(metrics, 'remote_switch') is True:
        facts.append('Der externe Telefon-/Fernschaltkontakt wird als Ein gemeldet; seine konkrete Wirkung ist nicht zugeordnet.')
    dhw = valid(plant, 'dhw_pump')
    if type(dhw) is bool:
        facts.append('Warmwasser-Ladekontakt Q3: ' + ('Ein.' if dhw else 'Aus.'))
        if dhw and pump is False:
            hints.append('Warmwasservorrang ist ein möglicher Einfluss. Q3 allein beweist keine Heizkreissperre.')
    if pump and mode == 'Automatik':
        hints.append('Neben Heizbedarf sind Nachlauf und Schutzfunktionen mögliche Auslöser. Der Relaiskontakt allein unterscheidet diese Gründe nicht.')
    signals = [split_signal(key, label, kind, size, metrics[key]) for key, label, kind, size in SIGNALS if key in metrics]
    for signal in signals:
        if 'protocol_valid' not in signal:
            continue
        if signal['key'] == 'space_request_raw':
            facts.append(signal['interpretation'])
        elif signal['protocol_valid'] and signal.get('percent_field') is not None:
            facts.append(signal['interpretation'])
            if signal['key'] == 'transfer_lock_raw' and dhw and signal['percent_field'] > 0:
                hints.append('Warmwasserladung und Reduktionssignal treten zusammen auf. Das passt zu einer Einschränkung der Raumheizung; die genaue Ursache und Wirkung auf Q1 sind noch nicht eindeutig belegt.')
    zero_locks = [s for s in signals if s['key'] in ('producer_lock_raw', 'transfer_lock_raw', 'mixing_lock_raw')
                  and s['quality'] == 'valid' and s.get('value_field') == 0 and s['attributes_hex'] == '0x00']
    if len(zero_locks) == 3:
        facts.append('Alle drei gelesenen Sperrblöcke enthalten 00 00. Das bestätigt keine aktive Sperre; die übrigen Attributbedeutungen bleiben offen.')
    signal_keys = {s[0] for s in SIGNALS}
    times = [m.get('updated_at') for k, m in metrics.items() if k in signal_keys or k in ('pump', 'mode', 'room_setpoint', 'clock')]
    times = [t for t in times if type(t) in (int, float)]
    skew = round(max(times) - min(times), 1) if times else None
    return {'area': area, 'pump_contact': pump, 'pump_quality': metrics.get('pump', {}).get('quality', 'pending'),
            'observed_at': metrics.get('pump', {}).get('updated_at'), 'evaluated_at': now,
            'summary': 'Q1 eingeschaltet' if pump is True else 'Q1 ausgeschaltet' if pump is False else 'Q1 unbekannt',
            'cause_status': 'unresolved', 'cause': 'Der genaue Schaltgrund ist noch nicht eindeutig belegt.',
            'phase': phase, 'facts': facts, 'hints': hints, 'signals': signals, 'read_skew_seconds': skew,
            'limits': 'Q1 ist der gemeldete Relaiskontakt, keine Messung von Drehzahl oder Durchfluss. LPB-Kürzel EG bedeutet Erzeugergruppe, nicht Erdgeschoss. Unbekannte Attribute lösen keine Ursachenzuweisung aus.'}


def event_payload(metrics, plant):
    keys = ('pump', 'mode', 'room_setpoint', 'flow_setpoint', 'remote_switch', 'quick_setback', 'room_actual', 'clock') + tuple(s[0] for s in SIGNALS)
    # Raw/quality changes are recorded; the ticking clock does not create events.
    return {**{key: {'value': metrics[key].get('value'), 'quality': metrics[key].get('quality'),
                     'updated_at': metrics[key].get('updated_at')} for key in keys if key in metrics},
            'dhw_pump': {k: plant.get('dhw_pump', {}).get(k) for k in ('value', 'quality', 'updated_at')}}


def fingerprint(payload):
    return {key: (item.get('value') if key != 'clock' else None, item.get('quality')) for key, item in payload.items()}
