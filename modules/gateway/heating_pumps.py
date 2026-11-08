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
    zero_locks = [s for s in signals if s['key'] in ('producer_lock_raw', 'transfer_lock_raw', 'mixing_lock_raw')
                  and s['quality'] == 'valid' and s.get('value_field') == 0 and s['attributes_hex'] == '0x00']
    if len(zero_locks) == 3:
        facts.append('Alle drei gelesenen Sperrblöcke enthalten 00 00. Das bestätigt keine aktive Sperre; die Attributbedeutung bleibt offen.')
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
