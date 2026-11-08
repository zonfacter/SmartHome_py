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
    return tuple(result)


POINTS = points()


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
    if kind.startswith('relay'):
        if len(payload) != 8:
            raise ValueError('truncated relay block')
        value = payload[int(kind[-1])]
        if value not in (0, 255):
            raise ValueError('invalid contact')
        return value == 255
    length = 3 if kind in ('temperature', 'counter') else 2
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
    if kind == 'curve':
        return payload[1] / 2
    if kind in ('counter', 'minutes'):
        return int.from_bytes(payload[1:], 'big')
    raise ValueError('unknown point type')
