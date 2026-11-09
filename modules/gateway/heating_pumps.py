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
    ('mixer_status_raw', 'Erzeugerstatus im Verbund · EM', 'status', 5),
)

# Only these exact object/layout combinations are covered by the reference.
# No propagation to producer-group 503/506, VM 505, EM request 501 or level 523.
LPB_DEFINITION_SOURCE = {
    'title': 'Brötje ISR MODBM · 7715040-06 (24.07.2019), Seiten 34–35',
    'url': 'https://polo.broetje.de/pdf/7715040%3D6%3Dpdf_%28bdr_a4_manual%29%3Dde-de_ma_modbm.pdf',
    'scope': 'LPB-Objektdefinition aus späterer Herstellerunterlage; Feldaufbau mit K/M-Profil abgeglichen. Keine unabhängige Bestätigung sämtlicher Wirkungen der alten Regler.',
}


def valid(metrics, key):
    item = metrics.get(key, {})
    return item.get('value') if item.get('quality') == 'valid' else None


def split_signal(key, label, kind, size, item):
    """Exact APW offsets; only explicitly covered LPB bits receive meanings."""
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
    if kind == 'status':
        attribute = int.from_bytes(payload[:2], 'big')
        result['attributes_hex'] = f'0x{attribute:04X}'
    elif kind == 'request':
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
    result['attribute_bits'] = [bit for bit in range(16 if kind in ('request','status') else 8) if attribute & (1 << bit)]
    definition = {'space_request_raw': (500, 'request', 4),
                  'dhw_request_raw': (500, 'request', 4),
                  'mixer_request_raw': (500, 'request', 4),
                  'transfer_lock_raw': (504, 'percent', 2),
                  'forced_mixer_raw': (507, 'percent', 2),
                  'mixer_status_raw': (522, 'status', 5)}.get(key)
    if definition and (kind, size) == definition[1:]:
        result['lpb_object'] = definition[0]
        result['definition_source'] = LPB_DEFINITION_SOURCE
        if kind == 'status':
            # G in status 522 means "producer present", NOT generic validity.
            result['producer_present'] = bool(attribute & 1)
            names = {1:('eco','Außentemperaturgrenze / ECO'),2:('fault','Erzeugerstörung'),
                     3:('chimney','Schornsteinfegerfunktion'),4:('manual_lock','manuelle Erzeugersperre'),
                     5:('dhw_unavailable','Erzeuger für Raumheizung wegen Warmwasserladung nicht verfügbar'),
                     8:('manual_mode','Handbetrieb')}
            result['status_flags'] = {name: bool(attribute & (1 << bit)) if attribute & 1 else None
                                      for bit,(name,_) in names.items()}
            result['unknown_attribute_bits'] = [bit for bit in result['attribute_bits'] if bit not in (0,*names)]
            labels = [label for bit,(_,label) in names.items() if attribute & (1 << bit)]
            result['interpretation'] = ('Nach LPB-Definition Erzeuger vorhanden' + (': ' + '; '.join(labels) if labels else '; keine der zugeordneten Sperr-/Sonderbetriebsanzeigen gesetzt.')
                                        if attribute & 1 else 'Nach LPB-Definition kein Erzeuger als vorhanden bestätigt; die übrigen Statusbits werden nicht als aktive Zustände verwendet.')
            return result
        result['protocol_valid'] = bool(attribute & 1)
        known_bits = (0,1,2,3) if kind == 'request' else (0,1)
        result['unknown_attribute_bits'] = [bit for bit in result['attribute_bits'] if bit not in known_bits]
        if kind == 'request':
            result['transport_pump_requested'] = bool(attribute & 2) if attribute & 1 else None
            result['absolute_dhw_priority'] = bool(attribute & 4) if attribute & 1 else None
            result['shifting_dhw_priority'] = bool(attribute & 8) if attribute & 1 else None
            result['interpretation'] = ('Nach LPB-Definition gültige Wärmeanforderung.' if attribute & 1 else
                                        'Nach LPB-Definition keine gültige Wärmeanforderung; das Temperaturfeld allein ist kein Bedarf.')
            if attribute & 1:
                if attribute & 4: result['interpretation'] += ' Kennzeichen für absoluten Warmwasservorrang gesetzt.'
                if attribute & 8: result['interpretation'] += ' Kennzeichen für gleitenden Warmwasservorrang gesetzt.'
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


def assess_context(area, metrics, plant, signals, phase, now):
    """Assess compatible observations; never claim the unique physical cause."""
    result = {'status':'insufficient','code':'incomplete','summary':'Für eine nähere Einordnung fehlen zusammenpassende aktuelle Messwerte.',
              'evidence':[], 'read_skew_seconds':None,
              'limit':'Ein Zusammenhang der Reglerdaten ist kein eindeutiger physischer Schaltgrund.'}
    by_key = {s['key']:s for s in signals}
    def coherent(entries):
        stamps = []
        for label, item in entries:
            stamp = item.get('updated_at')
            if item.get('quality') != 'valid' or type(stamp) not in (int,float) or not 0 <= now-stamp <= 90:
                return False
            stamps.append(stamp)
        span = max(stamps)-min(stamps)
        result['read_skew_seconds'] = round(span,1)
        if span > 30:
            result.update(code='time_skew',summary='Die relevanten Messwerte liegen zeitlich zu weit auseinander; kein gemeinsamer Schaltkontext abgeleitet.')
            return False
        return True
    def finish(code, text, evidence, status='consistent'):
        result.update(status=status,code=code,summary=text,evidence=evidence)
        return result
    pump, mode = valid(metrics,'pump'), valid(metrics,'mode')
    if type(pump) is not bool:
        return result
    base_context = [('pump',metrics.get('pump',{})),('mode',metrics.get('mode',{}))]
    if not coherent(base_context):
        return result
    if mode == 'Handbetrieb':
        return finish('manual_mode','Handbetrieb aktiv: Das normale Zeitprogramm erklärt den Pumpenkontakt nicht allein.',['Betriebsart Handbetrieb','Pumpenkontakt '+('Ein' if pump else 'Aus')], 'observed')
    status = by_key.get('mixer_status_raw',{})
    flags = status.get('status_flags',{})
    blocked = [name for name in ('eco','fault','manual_lock','dhw_unavailable') if flags.get(name) is True]
    if blocked:
        if not coherent(base_context + [('status',metrics.get('mixer_status_raw',{}))]):
            return result
        return finish('producer_restriction','Der Erzeugerstatus meldet eine Einschränkung der Wärmeversorgung.',
                      [status['interpretation']], 'indication')
    lock = by_key.get('transfer_lock_raw',{})
    q3 = valid(plant,'dhw_pump')
    if mode == 'Automatik' and q3 is True and lock.get('quality') != 'valid':
        return result
    if mode == 'Automatik' and lock.get('protocol_valid') and (lock.get('percent_field') or 0) > 0 and q3 is True:
        if not coherent(base_context + [('lock',metrics.get('transfer_lock_raw',{})),('Q3',plant.get('dhw_pump',{}))]):
            return result
        evidence = ['Warmwasser-Ladekontakt Q3 Ein',lock['interpretation']]
        if area == 'eg' and pump:
            return finish('mixing_restriction','Reduktionssignal bei laufender EG-Pumpe: Eine Begrenzung am Mischer ist möglich.',evidence)
        if not pump:
            return finish('dhw_restriction','Warmwasserladung und Reduktionssignal passen zum Pumpenstopp.',evidence)
        return finish('reduction_with_pump','Warmwasserladung und Reduktionssignal bei laufender Pumpe; die genaue Wirkung bleibt offen.',evidence,'observed')
    demand = by_key.get('space_request_raw',{})
    demand_context = base_context + [('demand',metrics.get('space_request_raw',{}))]
    if 'protocol_valid' not in demand or not coherent(demand_context):
        return result
    afterrun = by_key.get('forced_mixer_raw',{})
    afterrun_active = (afterrun.get('protocol_valid') is True and afterrun.get('mandatory') is False
                      and afterrun.get('percent_field') is not None)
    if afterrun_active and not coherent(demand_context + [('force',metrics.get('forced_mixer_raw',{}))]):
        return result
    if demand['protocol_valid'] and not 0 < demand.get('temperature_field',0) <= 140:
        return finish('request_value_uncertain','Das gültig markierte Temperaturfeld liegt außerhalb des verwendeten Anforderungsbereichs; Wirkung offen.',[], 'unresolved')
    if pump and afterrun_active:
        if demand['protocol_valid']:
            return finish('heat_and_afterrun','Heizanforderung und Nachlaufanforderung liegen gleichzeitig vor.',[demand['interpretation'],afterrun['interpretation']])
        return finish('afterrun','Eine Nachlaufanforderung passt zum laufenden Pumpenkontakt.',[afterrun['interpretation']])
    if demand['protocol_valid'] and pump:
        return finish('space_heating','Eine gültige Heizanforderung passt zum laufenden Pumpenkontakt.',[demand['interpretation']])
    if demand['protocol_valid'] and not pump:
        return finish('demand_without_pump','Heizanforderung vorhanden, Pumpenkontakt Aus: Weitere Freigaben und Sperren bleiben zu prüfen.',[demand['interpretation']],'unresolved')
    if not pump and phase and phase['phase'] == 'reduced':
        if not coherent(demand_context + [('clock',metrics.get('clock',{}))]):
            return result
        return finish('reduced_no_demand','Absenkphase ohne gültige lokale Heizanforderung passt zum Pumpenstopp.',[phase['label'],demand['interpretation']])
    return finish('unresolved','Der Pumpenkontakt lässt sich aus den bisher eingeordneten Signalen nicht näher erklären.',[], 'unresolved')


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
    assessment = assess_context(area, metrics, plant, signals, phase, now)
    return {'area': area, 'pump_contact': pump, 'pump_quality': metrics.get('pump', {}).get('quality', 'pending'),
            'observed_at': metrics.get('pump', {}).get('updated_at'), 'evaluated_at': now,
            'summary': 'Q1 eingeschaltet' if pump is True else 'Q1 ausgeschaltet' if pump is False else 'Q1 unbekannt',
            'cause_status': 'unresolved', 'cause': 'Der genaue Schaltgrund ist noch nicht eindeutig belegt.',
            'phase': phase, 'facts': facts, 'hints': hints, 'signals': signals, 'assessment':assessment, 'read_skew_seconds': skew,
            'limits': 'Q1 ist der gemeldete Relaiskontakt, keine Messung von Drehzahl oder Durchfluss. LPB-Kürzel EG bedeutet Erzeugergruppe, nicht Erdgeschoss. Unbekannte Attribute lösen keine Ursachenzuweisung aus.'}


def event_payload(metrics, plant):
    keys = ('pump', 'mode', 'room_setpoint', 'flow_setpoint', 'flow_actual','mixer_open','mixer_close',
            'remote_switch', 'quick_setback', 'room_actual', 'clock','producer_status_raw') + tuple(s[0] for s in SIGNALS)
    # Raw/quality changes are recorded; the ticking clock does not create events.
    return {**{key: {'value': metrics[key].get('value'), 'quality': metrics[key].get('quality'),
                     'updated_at': metrics[key].get('updated_at')} for key in keys if key in metrics},
            'dhw_pump': {k: plant.get('dhw_pump', {}).get(k) for k in ('value', 'quality', 'updated_at')}}


def fingerprint(payload):
    return {key: (item.get('value') if key != 'clock' else None, item.get('quality')) for key, item in payload.items()}
