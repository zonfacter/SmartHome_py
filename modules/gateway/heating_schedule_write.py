"""Bounded native daily-program writes with readback, journal and rollback."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
import threading
import time

from .heating_lpb import WEEKDAYS, checksum_valid, decode_schedule, read_frame


class ScheduleError(Exception):
    def __init__(self, message, status=400, **details):
        super().__init__(message)
        self.status, self.details = status, details


def periods(value, step=False):
    if not isinstance(value, list) or len(value) > 3:
        raise ScheduleError('Pro Tag sind höchstens drei Komfortphasen möglich.')
    result, previous = [], 0
    for item in value:
        try:
            values = []
            for key in ('start', 'end'):
                text = item[key]
                if not isinstance(text, str) or not re.fullmatch(r'\d{2}:\d{2}', text):
                    raise ValueError()
                h, m = map(int, text.split(':'))
                if h > 24 or m > 59 or (h == 24 and m):
                    raise ValueError()
                values.append(h*60+m)
            start, end = values
            if start >= 1440 or end <= start or start < previous or (step and (start % 10 or end % 10)):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise ScheduleError('Ungültige Zeitfenster: aufsteigend, ohne Überschneidung und in Zehn-Minuten-Schritten eingeben.') from None
        previous = end
        result.append({'start': item['start'], 'end': item['end'], 'start_minute': start, 'end_minute': end})
    return result


def encode(value):
    data = bytearray()
    for item in periods(value, step=True):
        data.extend((*divmod(item['start_minute'], 60), *divmod(item['end_minute'], 60)))
    data.extend(bytes.fromhex('98001800') * (3-len(value)))
    return bytes(data)


def equivalent(a, b):
    return decode_schedule(a) == decode_schedule(b)


class ScheduleWriter:
    TARGETS = {'eg': 1, 'og': 0}

    def __init__(self, root, config, fetch, send, bus_lock, update):
        self.config, self.fetch, self.send = config, fetch, send
        self.bus_lock, self.update = bus_lock, update
        self.enabled = config.get('enabled') is True and config.get('schedule_writes_enabled') is True
        self.directory = Path(root) / 'config' / 'heating_schedule_transactions'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.proposals, self.guard = {}, threading.RLock()
        self.active = threading.Lock()
        self.pending = []
        for path in self.directory.glob('*.json'):
            try:
                row = json.loads(path.read_text(encoding='utf-8'))
                if row['status'] in ('applying', 'rollback_failed'):
                    self.pending.append(row)
            except (ValueError, KeyError):
                # Unknown/corrupt journals must be reviewed before further writes.
                self.pending.append({'id': path.stem, 'status': 'invalid_journal'})

    def _identity(self):
        if not self.enabled:
            raise ScheduleError('Übertragung ist auf dieser VM nicht aktiviert.', 403)
        info = self.fetch('/JI')
        mac = self.config.get('bsb_mac')
        devices = {d['dev_id']: (d['dev_fam'], d['dev_var'], d['dev_serial']) for d in info.get('busdevices', [])}
        if (not mac or info.get('MAC') != mac or info.get('bus') != 'LPB' or
                (info.get('busaddr'), info.get('busdest'), info.get('buswritable')) != (66, 0, 0) or
                devices.get(0) != (22, 254, 2004) or devices.get(1) != (23, 254, 2006)):
            raise ScheduleError('Die Identität von Heizungsadapter oder Reglern stimmt nicht mit der geprüften Anlage überein.', 503)

    def _read(self, area, day):
        target, command = self.TARGETS[area], f'05000A{0x8C+day:02X}'
        value = read_frame(self.fetch(f'/JY06,{command}!{target}'), target, command, 66)
        if value is None:
            raise ValueError('controller did not return daily program')
        decode_schedule(value)
        return value

    def _week(self, area):
        values = [self._read(area, d) for d in range(7)]
        self.update(area, values)
        return values

    def _write(self, area, day, value):
        assert area in self.TARGETS and type(day) is int and 0 <= day < 7 and len(value) == 12
        decode_schedule(value)
        target, command = self.TARGETS[area], f'05000A{0x8C+day:02X}'
        page = self.send(f'/Y03,{command},{value.hex().upper()}!{target}')
        frames = [bytes.fromhex(m.group()) for m in re.finditer(r'\b78(?: [0-9A-F]{2}){14,32}\b', page)]
        if len(frames) != 2:
            raise ValueError('write response did not contain two frames')
        tx, rx = frames
        coid = bytes.fromhex(command)
        if (not checksum_valid(tx) or not checksum_valid(rx) or len(tx) != 27 or
                tx[2:4] != bytes((target, 66)) or tx[8] != 3 or
                tx[9:13] != bytes((coid[1], coid[0], coid[2], coid[3])) or tx[13:-2] != value or
                rx[2:4] != bytes((66, target)) or rx[9:13] != coid or rx[8] != 4 or len(rx) != 15):
            raise ValueError('write acknowledgement could not be verified')

    def _journal(self, row):
        target = self.directory / (row['id'] + '.json')
        temporary = target.with_suffix('.tmp')
        # Flush intent to durable storage before the first SET or subsequent day.
        import os
        with temporary.open('w', encoding='utf-8') as f:
            json.dump(row, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        temporary.replace(target)

    def _rollback(self, row):
        errors = []
        for day in reversed(row['attempted']):
            try:
                original = bytes.fromhex(row['before'][day])
                current = self._read(row['area'], day)
                if not equivalent(current, original):
                    known = [row['desired'][day], row.get('observed', {}).get(str(day))]
                    if not any(x and equivalent(current, bytes.fromhex(x)) for x in known):
                        raise ValueError('program changed outside this transaction')
                    try:
                        self._write(row['area'], day, original)
                    except Exception:
                        # An HTTP timeout can occur after a successful SET; read independently.
                        pass
                    if not equivalent(self._read(row['area'], day), original):
                        raise ValueError('original program not restored')
            except Exception:
                errors.append(WEEKDAYS[day][1])
        row['status'] = 'rollback_failed' if errors else 'rolled_back'
        row['rollback_failed_days'] = errors
        self._journal(row)
        return not errors

    def recover(self):
        if not self.pending or not self.enabled:
            return
        with self.bus_lock:
            self._identity()
            for row in list(self.pending):
                if row['status'] != 'invalid_journal' and self._rollback(row):
                    self.pending.remove(row)

    def preview(self, body, owner):
        if self.pending:
            self.recover()
        if self.pending:
            raise ScheduleError('Eine frühere Übertragung konnte noch nicht wiederhergestellt werden. Neue Übertragungen sind gesperrt.', 503)
        if not isinstance(body, dict) or set(body) != {'area', 'base', 'days'} or body.get('area') not in self.TARGETS:
            raise ScheduleError('Ungültiger Heizkreis oder Entwurf.')
        if not all(isinstance(body[k], list) and len(body[k]) == 7 for k in ('base', 'days')):
            raise ScheduleError('Der Entwurf muss sieben vollständige Tage enthalten.')
        base = [periods(v) for v in body['base']]
        desired = [encode(v) for v in body['days']]
        area = body['area']
        with self.bus_lock:
            self._identity()
            before = self._week(area)
        if [decode_schedule(v) for v in before] != base:
            raise ScheduleError('Der Reglerstand hat sich seit dem Entwurf geändert. Bitte die aktuellen Zeiten vergleichen und den Entwurf neu erstellen.', 409)
        changed = [d for d in range(7) if not equivalent(before[d], desired[d])]
        changes = [{'day': d, 'label': WEEKDAYS[d][1], 'before': decode_schedule(before[d]),
                    'after': decode_schedule(desired[d])} for d in changed]
        token, now = secrets.token_urlsafe(32), time.time()
        row = {'id': secrets.token_hex(16), 'area': area, 'before': [v.hex() for v in before],
               'desired': [v.hex() for v in desired], 'changed': changed, 'changes': changes,
               'owner': owner, 'expires': now+180, 'status': 'prepared'}
        with self.guard:
            self.proposals = {k: v for k, v in self.proposals.items() if v['expires'] > now}
            if len(self.proposals) >= 32:
                raise ScheduleError('Zu viele offene Vorschauen. Bitte kurz warten.', 429)
            self.proposals[token] = row
        return {'token': token, 'area': area, 'changes': changes, 'expires_at': row['expires']}

    def apply(self, token, owner):
        with self.guard:
            row = self.proposals.get(token) if isinstance(token, str) else None
            if not row or row['owner'] != owner or row['expires'] < time.time():
                raise ScheduleError('Die Vorschau ist abgelaufen. Bitte die Übertragung erneut prüfen.', 409)
            if 'result' in row:
                return deepcopy(row['result'])
        if not self.active.acquire(blocking=False):
            raise ScheduleError('Eine Heizungsübertragung läuft bereits.', 409)
        try:
            with self.bus_lock:
                if 'result' in row:
                    return deepcopy(row['result'])
                if row['status'] != 'prepared' or self.pending:
                    raise ScheduleError('Diese Übertragung kann nicht erneut ausgeführt werden.', 409)
                self._identity()
                current = self._week(row['area'])
                if not all(equivalent(v, bytes.fromhex(row['before'][d])) for d, v in enumerate(current)):
                    row['status'] = 'conflict'
                    raise ScheduleError('Die Zeiten wurden nach der Vorschau geändert. Bitte eine neue Vorschau erstellen.', 409)
                row.update(status='applying', attempted=[], observed={}, utc=datetime.now(timezone.utc).isoformat())
                self._journal(row)
                try:
                    for day in row['changed']:
                        # Each actual SET gets a second immediate conflict check.
                        if not equivalent(self._read(row['area'], day), bytes.fromhex(row['before'][day])):
                            raise ValueError('program changed immediately before SET')
                        row['attempted'].append(day)
                        self._journal(row)
                        self._write(row['area'], day, bytes.fromhex(row['desired'][day]))
                        actual = self._read(row['area'], day)
                        row['observed'][str(day)] = actual.hex()
                        self._journal(row)
                        if not equivalent(actual, bytes.fromhex(row['desired'][day])):
                            raise ValueError('requested switch points were not returned')
                    after = self._week(row['area'])
                    if not all(equivalent(v, bytes.fromhex(row['desired'][d])) for d, v in enumerate(after)):
                        raise ValueError('final weekly program differs')
                    row['status'] = 'verified'
                    row['result'] = {'success': True, 'area': row['area'], 'changed_days': row['changed'],
                                     'transaction': row['id'], 'verified_days': [decode_schedule(v) for v in after]}
                    self._journal(row)
                    return deepcopy(row['result'])
                except Exception as error:
                    restored = self._rollback(row)
                    if not restored:
                        self.pending.append(row)
                    try:
                        self._week(row['area'])
                    except Exception:
                        self.update(row['area'], None)
                    raise ScheduleError('Übertragung fehlgeschlagen. Die ursprünglichen Zeiten wurden wiederhergestellt.' if restored else
                        'Übertragung fehlgeschlagen; Wiederherstellung nicht vollständig bestätigt. Bitte den Regler prüfen.',
                        502, restored=restored, transaction=row['id'], failed_days=row['rollback_failed_days']) from error
        finally:
            self.active.release()
