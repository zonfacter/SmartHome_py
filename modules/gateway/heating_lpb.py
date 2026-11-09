"""Read-only, checksum-verified legacy LPB decoding for Eurocontrol K and M."""
import base64
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Point:
    area: str
    key: str
    label: str
    target: int
    coid: str
    kind: str = 'temperature'
    unit: str = '°C'
    slow: bool = False


def points():
    result = []
    def add(area, target, key, label, coid, kind='temperature', unit='°C', slow=False):
        result.append(Point(area, key, label, target, coid, kind, unit, slow))
    for area, target in [('eg', 1), ('og', 0)]:
        add(area, target, 'mode', 'Betriebsart', '05000074', 'mode', '')
        add(area, target, 'pump', 'Heizkreispumpe', '05000488', 'relay2', '')
        add(area, target, 'room_setpoint', 'Aktueller Raumsollwert', '05000593')
        add(area, target, 'nominal', 'Komfortsollwert', '05000458', slow=True)
        add(area, target, 'curve', 'Heizkurve · alte Reglerskala', '050005F7', 'curve', '', True)
        add(area, target, 'parallel', 'Parallelverschiebung', '05000610', unit='K', slow=True)
        add(area, target, 'room_influence', 'Raumeinfluss', '05000603', 'enable', '', True)
        add(area, target, 'room_gain', 'Gespeicherter Einflussfaktor', '05000603', 'gain', '', True)
        add(area, target, 'differential', 'Raumschaltdifferenz', '0500060F', unit='K', slow=True)
        add(area, target, 'adaptation', 'Heizkurvenadaption', '0500060B', 'boolean', '', True)
        add(area, target, 'summer', 'Sommer-/Wintergrenze', '050005FD', slow=True)
    for key, label, coid, slow in [
        ('flow_actual', 'Vorlauftemperatur', '05000464', False),
        ('flow_setpoint', 'Vorlaufsollwert', '05000667', False),
        ('room_actual', 'Raumfühler am Regler', '0500051E', False),
        ('outside', 'Außentemperatur', '05000521', False),
        ('reduced', 'Reduziertsollwert', '05000590', True),
        ('frost', 'Frostschutzsollwert', '05000592', True),
        ('flow_min', 'Vorlauf · Minimum', '05000663', True),
        ('flow_max', 'Vorlauf · Maximum', '05000662', True),
    ]:
        add('eg', 1, key, label, coid, slow=slow)
    add('eg', 1, 'boost', 'Mischerüberhöhung', '0500065D', unit='K', slow=True)
    add('eg', 1, 'overrun', 'Pumpennachlauf', '05000BCC', 'minutes', 'min', True)
    add('eg', 1, 'mixer_open', 'Mischer öffnet · Y1', '05000488', 'relay0', '')
    add('eg', 1, 'mixer_close', 'Mischer schließt · Y2', '05000488', 'relay1', '')
    add('anlage', 0, 'boiler', 'Kesseltemperatur', '05000468')
    add('anlage', 0, 'dhw', 'Warmwassertemperatur', '05000462')
    add('anlage', 0, 'dhw_setpoint', 'Warmwassersollwert', '050006B9', slow=True)
    add('anlage', 0, 'burner', 'Brennerrelais Stufe 1 · K4', '05000488', 'relay0', '')
    add('anlage', 0, 'burner_stage2', 'Brennerrelais Stufe 2 · K5', '05000488', 'relay1', '')
    add('anlage', 0, 'dhw_pump', 'Warmwasserpumpenrelais · Q3', '05000488', 'relay3', '')
    add('anlage', 0, 'starts', 'Brennerstarts', '0500093F', 'counter', '')
    for area, target in [('eg', 1), ('og', 0)]:
        add(area,target,'clock','Regleruhr','0500000B','clock','')
        add(area,target,'error_code','Fehlercode','0500006B','error_code','')
        add(area,target,'error_priority','Fehlerpriorität','0500006B','error_priority','')
        add(area,target,'relay_test','Relaistest · Einstellung','05000073','relay_test','',True)
        add(area,target,'lpb_power','LPB-Speisungsstatus','05000072','boolean','',True)
        add(area,target,'plant_frost','Anlagenfrostschutz · Einstellung','050005FE','boolean','',True)
        add(area,target,'building','Gebäudebauweise · Einstellung','05000601','building','',True)
        add(area,target,'outside_local','Außenfühler am Regler','0500021F',slow=True)
        add(area,target,'outside_attenuated','Außentemperatur · gedämpft','050005F0',slow=True)
        add(area,target,'outside_composite','Außentemperatur · gemischt','050005F2',slow=True)
        add(area,target,'changeover_source','Sommer-/Winterumschaltung','05000611','changeover_'+area,'',True)
        add(area,target,'quick_setback','Schnellabsenkungsfaktor · KON','050005FB','factor','',True)
        add(area,target,'remote_switch','Telefon-/Fernschaltkontakt','050004B8','boolean','')
        add(area,target,'startup_boost','Raumsollwertüberhöhung · Schnellaufheizung','05000602',unit='K',slow=True)
        add(area,target,'adaptation_zaf1','Adaptionsempfindlichkeit · ZAF1','0500060D','integer8','',True)
        add(area,target,'adaptation_zaf2','Adaptionsempfindlichkeit · ZAF2','0500060E','integer8','',True)
        add(area,target,'plant_type','Anlagentyp · Reglercode','05000067','code8','',True)
        add(area,target,'clock_source','Uhrzeitquelle','0500006D','clock_source','',True)
        add(area,target,'outside_source','Außentemperaturquelle · LPB','05000082','outside_source','',True)
        for key,label,command,kind in [
            ('space_request_raw','Heizungsanforderung · Rohdaten','210001F4','raw4'),
            ('producer_lock_raw','Erzeuger-Sperrsignal · Rohdaten','110001F7','raw2'),
            ('mixing_lock_raw','Mischerkreis-Sperrsignal · Rohdaten','190001F9','raw2'),
            ('forced_producer_raw','Erzeuger-Zwangssignal · Rohdaten','110001FA','raw2'),
            ('producer_status_raw','Erzeugerstatus · Rohdaten','11000209','raw9'),
            ('mixer_status_raw','Mischerstatus · Rohdaten','1500020A','raw5'),
            ('forced_mixer_raw','Mischer-Zwangssignal · Rohdaten','150001FB','raw2'),
            ('mixer_request_raw','Mischeranforderung · Rohdaten','190001F4','raw4'),
            ('transfer_lock_raw','Übertragungs-Sperrsignal · Rohdaten','150001F8','raw2'),
        ]:
            add(area,target,key,label,command,kind,'',key in ('producer_status_raw','mixer_status_raw'))
        add(area,target,'status_level_raw','Betriebsniveau · Rohdaten','2D00020B','raw2','')
    add('og',0,'dhw_request_raw','Warmwasseranforderung · Rohdaten','250001F4','raw4','')
    add('eg',1,'producer_request_raw','Erzeugeranforderung · Rohdaten','150001F5','raw5','')
    for key,label,command in [
        ('reduced','Reduziertsollwert','05000590'),('frost','Frostschutzsollwert','05000592'),
        ('flow_min','Vorlauf · Minimum','05000663'),('flow_max','Vorlauf · Maximum','05000662'),
        ('outside','Außentemperatur','05000521'),('room_actual','Raumfühler am Regler','0500051E'),
        ('flow_setpoint','Resultierender Vorlaufsollwert','05000667'),
    ]:
        add('og',0,key,label,command,slow=key not in ('room_actual','flow_setpoint'))
    add('og',0,'overrun','Pumpennachlauf','05000BCC','minutes','min',True)
    add('og',0,'pump_function','Pumpenfunktion','05000BCE','pump_function','',True)
    add('anlage',0,'burner_hours','Brenner-Betriebsstunden','11000209','burner_hours','h')
    for key,label,command,unit in [
        ('boiler_min','Kessel · Minimum','0500092C','°C'),('boiler_max','Kessel · Maximum','0500092B','°C'),
        ('boiler_differential','Kesselschaltdifferenz','05000928','K'),
        ('burner_on_threshold','Berechnete Brenner-Einschalttemperatur','05000944','°C'),
        ('burner_off_threshold','Berechnete Brenner-Ausschalttemperatur','05000945','°C'),
        ('dhw_reduced','Warmwasser · Reduziertsollwert','050006BA','°C'),
        ('dhw_max','Warmwasser · maximaler Nennsollwert','050006B8','°C'),
        ('dhw_differential','Warmwasserschaltdifferenz','0500071D','K'),
        ('dhw_boost','Temperaturüberhöhung zur Warmwasserladung','05000720','K'),
    ]:
        add('anlage',0,key,label,command,unit=unit,slow=True)
    add('anlage',0,'burner_min_run','Mindestbrennerlaufzeit · Einstellung','05000939','minutes','min',True)
    add('anlage',0,'dhw_enabled','Warmwasser-Betriebsart','05000723','boolean','',True)
    add('anlage',0,'dhw_program','Warmwasserprogramm','05000722','dhw_program','',True)
    add('anlage',0,'dhw_priority','Warmwasserpriorität','05000721','dhw_priority','',True)
    add('anlage',0,'dhw_charging','Warmwasser-Ladeart','0500071F','dhw_charging','',True)
    add('anlage',0,'dhw_request_source','Warmwasser-Anforderungsart','0500071E','dhw_request_source','',True)
    add('anlage',0,'dhw_dedicated','Warmwasser-Trennschaltung','05000727','boolean','',True)
    add('anlage',0,'boiler_min_oem','Kesselminimum · OEM-Grenze','0500092D',slow=True)
    add('anlage',0,'burner_type','Brennerart · Konfiguration','05000930','burner_type','',True)
    add('anlage',0,'stage2_release_integral','Stufe 2 · Freigabeintegral','05000932','integral','K·min',True)
    add('anlage',0,'stage2_reset_integral','Stufe 2 · Rückstellintegral','05000933','integral','K·min',True)
    add('anlage',0,'chimney_sweep','Schornsteinfegerfunktion','05000925','boolean','')
    add('anlage',0,'boiler_mode','Kesselbetriebsart · Einstellung','05000924','boiler_mode','',True)
    return tuple(result)


POINTS = points()
WEEKDAYS = tuple(zip(('monday','tuesday','wednesday','thursday','friday','saturday','sunday'),
                    ('Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag')))
TEXT_KINDS = frozenset(('mode','clock','relay_test','building','changeover_eg','changeover_og',
                        'pump_function','dhw_program','dhw_priority','dhw_charging',
                        'dhw_request_source','burner_type','boiler_mode','clock_source','outside_source'))
RELAY_KINDS = frozenset(f'relay{i}' for i in range(8))


def decode_schedule(payload):
    """Native daily array: three hour/minute pairs, no scalar validity prefix."""
    if payload is None:
        return None
    if len(payload) != 12:
        raise ValueError('daily program must contain twelve bytes')
    periods = []
    for offset in range(0, 12, 4):
        sh, sm, eh, em = payload[offset:offset+4]
        start_hour, end_hour = sh & 0x7F, eh & 0x7F
        if start_hour > 24 or end_hour > 24 or sm > 59 or em > 59:
            raise ValueError('invalid switch-point time')
        if (start_hour == 24 and sm) or (end_hour == 24 and em):
            raise ValueError('invalid midnight')
        if sh & 0x80 or eh & 0x80:
            continue  # observed 80 and 98 markers disable unused pairs
        start, end = start_hour*60+sm, end_hour*60+em
        if start == end:
            continue
        if start >= 1440 or end < start or (periods and start < periods[-1]['end_minute']):
            raise ValueError('unordered or overlapping daily intervals')
        periods.append({'start':f'{start_hour:02}:{sm:02}', 'end':f'{end_hour:02}:{em:02}',
                        'start_minute':start,'end_minute':end})
    return periods


def checksum_valid(packet):
    if len(packet) < 15 or packet[0] != 0x78 or packet[1] != len(packet) - 1:
        return False
    length = len(packet) - 1
    value = ((257-length)*256 + length-2 + sum(packet[:length-1])) & 0xffff
    return value == int.from_bytes(packet[-2:], 'big')


def read_frame(response, target, coid, own_address):
    tx = base64.b64decode(response['tx_msg'], validate=True)
    rx = base64.b64decode(response['rx_msg'], validate=True)
    if not checksum_valid(tx) or not checksum_valid(rx):
        raise ValueError('invalid LPB checksum')
    if len(tx) != 15 or tx[8] != 6 or tx[2:4] != bytes([target, own_address]):
        raise ValueError('not the expected payload-free read')
    command = bytes.fromhex(coid)
    if tx[9:13] != bytes([command[1], command[0], command[2], command[3]]):
        raise ValueError('outgoing object mismatch')
    if rx[2:4] != bytes([own_address, target]) or rx[9:13] != command:
        raise ValueError('incoming object or source mismatch')
    if rx[8] == 8:
        return None
    if rx[8] != 7:
        raise ValueError('unexpected response type')
    return rx[13:-2]


def decode(point, payload):
    if payload is None:
        return None
    kind = point.kind
    if kind.startswith('raw'):
        if len(payload) != int(kind[3:]):
            raise ValueError('truncated diagnostic block')
        return payload.hex(' ').upper()
    if kind == 'outside_source':
        # Exact K/M APW: a two-field block, NOT a scalar validity byte + value.
        if len(payload) != 2:
            raise ValueError('truncated outside-source block')
        segment, device = payload
        if segment > 14 or device > 16:
            return 'Quelle nicht zugeordnet · ' + payload.hex(' ').upper()
        return f'Segment S{segment} · Gerät G{device}' if device else f'Segment S{segment} · Gerät nicht angegeben'
    if kind in ('error_code','error_priority'):
        if len(payload) != 2:
            raise ValueError('truncated error block')
        return payload[0 if kind=='error_code' else 1]
    if kind == 'burner_hours':
        if point.target != 0 or len(payload) != 9:
            raise ValueError('hours field only verified in K producer block')
        seconds=int.from_bytes(payload[5:9],'big',signed=True)
        return seconds/3600 if seconds>=0 else None
    if kind == 'clock':
        if len(payload)!=9 or payload[0] not in (0,1):
            raise ValueError('invalid weekly clock')
        if payload[0]:
            return None
        day,hour,minute,second=payload[4:8]
        if not 1<=day<=7 or hour>23 or minute>59 or second>59:
            raise ValueError('invalid clock fields')
        return f'{WEEKDAYS[day-1][1]} {hour:02}:{minute:02}'
    if kind in RELAY_KINDS:
        if len(payload) != 8:
            raise ValueError('truncated relay block')
        value = payload[int(kind[-1])]
        if value not in (0, 255):
            raise ValueError('invalid contact')
        return value == 255
    length = 3 if kind in ('temperature', 'counter', 'integral') else 2
    if len(payload) != length or payload[0] not in (0, 1):
        raise ValueError('invalid scalar layout')
    if kind == 'enable':
        return payload[0] == 0
    if kind == 'gain':
        return payload[1]
    if payload[0] != 0:
        return None
    if kind == 'temperature':
        value = int.from_bytes(payload[1:], 'big', signed=True) / 64
        return value if math.isfinite(value) else None
    if kind == 'boolean':
        if payload[1] not in (0, 255):
            raise ValueError('invalid boolean')
        return payload[1] == 255
    if kind == 'mode':
        return {0: 'Bereitschaft', 1: 'Automatik', 4: 'Handbetrieb'}.get(payload[1], 'Unbekannt')
    enums={
        'relay_test':{0:'Inaktiv'},
        'building':{0:'Schwer',255:'Leicht'},
        'changeover_og':{0:'Lokal',255:'Zentral'},
        'changeover_eg':{0:'Kein Einfluss',255:'Zentrale Umschaltung'},
        'pump_function':{0:'Keine Pumpe',1:'Kessel-/Heizkreispumpe',2:'Primärpumpe'},
        'dhw_program':{0:'24 Stunden',1:'Lokales Heizprogramm',2:'Lokales Heizprogramm − 1 h',3:'System-Heizprogramm − 1 h'},
        'dhw_priority':{0:'Absolut',1:'Gleitend',2:'Parallel'},
        'dhw_charging':{0:'Ladepumpe',255:'Umschaltventil'},
        # Legacy COzwValB uses 00/FF on the wire, not panel values 0/1.
        'dhw_request_source':{0:'Speicherfühler',255:'Thermostat'},
        'burner_type':{0:'Einstufig',255:'Zweistufig'},
        'boiler_mode':{0:'Dauerbetrieb',255:'Automatik'},
        'clock_source':{0:'Eigene Regleruhr',1:'LPB · ohne Ferneinstellung',
                        2:'LPB · mit Ferneinstellung',3:'Zeitmaster am LPB'},
    }
    if kind in enums:
        return enums[kind].get(payload[1],f'Code {payload[1]}')
    if kind == 'curve':
        return payload[1] / 2
    if kind in ('counter', 'minutes'):
        return int.from_bytes(payload[1:], 'big')
    if kind == 'integral':
        value = int.from_bytes(payload[1:], 'big', signed=True)
        if not 0 <= value <= 500:
            raise ValueError('invalid stage-two integral')
        return value
    if kind == 'integer8':
        return int.from_bytes(payload[1:], 'big', signed=True)
    if kind == 'code8':
        return payload[1]
    if kind == 'factor':
        if payload[1] > 20:
            raise ValueError('invalid quick setback factor')
        return payload[1]
    raise ValueError('unknown point type')
