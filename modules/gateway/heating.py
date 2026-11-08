"""Shared LPB cache, local history, ioBroker and bounded native schedule transfers."""
from copy import deepcopy
from contextlib import closing
import json
import logging
import math
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import urllib.request

from flask import jsonify, render_template, request
from .heating_lpb import POINTS, WEEKDAYS, TEXT_KINDS, RELAY_KINDS, decode, decode_schedule, read_frame
from .heating_schedule_write import ScheduleWriter, ScheduleError
from .heating_statistics import summarize

logger = logging.getLogger(__name__)


class IoBroker:
    """Sequential RPC connection using ioBroker's native WebSocket protocol."""
    PREFIX = '0_userdata.0.heizung'

    def __init__(self, url):
        self.url = url
        self.ws = None
        self.sequence = 0

    def connect(self):
        from simple_websocket import Client
        separator = '&' if '?' in self.url else '?'
        self.ws = Client.connect(self.url + separator + 'sid=' + str(time.time_ns()), max_message_size=8*1024*1024)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            message = self._receive()
            if len(message) > 2 and message[2] == '___ready___':
                return self
        raise TimeoutError('ioBroker handshake')

    def _receive(self):
        data = self.ws.receive(timeout=8)
        if data is None:
            raise TimeoutError('ioBroker response')
        message = json.loads(data)
        if message[0] == 1:
            self.ws.send('[2]')
        return message

    def call(self, method, *args):
        if method not in ('getStates', 'getState', 'getObjectView', 'getObject', 'setObject', 'setState'):
            raise ValueError('unsupported ioBroker method')
        if method in ('setObject', 'setState'):
            key = args[0]
            if not re.fullmatch(r'0_userdata\.0\.heizung(?:\.[a-zA-Z0-9_]+)+', key):
                raise ValueError('write outside heating namespace')
            if method == 'setState' and args[1].get('ack') is not True:
                raise ValueError('telemetry must be acknowledged')
        self.sequence += 1
        sequence = self.sequence
        self.ws.send(json.dumps([3, sequence, method, list(args)]))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            message = self._receive()
            if message[0] == 3 and message[1] == sequence:
                values = message[3]
                if values and values[0] is not None:
                    raise RuntimeError('ioBroker rejected request')
                return values[1] if len(values) > 1 else None
        raise TimeoutError('ioBroker RPC')

    def close(self):
        if self.ws:
            self.ws.close()
            self.ws = None


class HeatingService:
    def __init__(self, root, config=None, fetch=None):
        self.root = Path(root)
        path = self.root / 'config' / 'heating.json'
        self.config = config if config is not None else (json.loads(path.read_text(encoding='utf-8')) if path.exists() else {})
        self.enabled = bool(self.config.get('enabled', False))
        self.url = str(self.config.get('bsb_url', 'http://bsb-lan.local')).rstrip('/')
        self.interval = max(15, int(self.config.get('poll_seconds', 30)))
        self.fetch = fetch or self._fetch
        self.lock = threading.RLock()
        self.bus_lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.metrics = {p.area + '.' + p.key: self._empty(p) for p in POINTS}
        self.rooms = []
        self.io_status = {'connected': False, 'tado_connected': False}
        self.connection = {'connected': False, 'message': 'Verbindung wird aufgebaut' if self.enabled else 'Noch nicht eingerichtet'}
        self.last_slow = 0
        self.last_schedule = 0
        self.schedules = {area:[{'day':day,'label':label,'periods':None,'quality':'pending','updated_at':None}
                                for day,label in WEEKDAYS] for area in ('eg','og')}
        self.last_rooms = 0
        self.own_address = None
        self.objects_created = set()
        self.db_path = self.root / 'config' / 'heating_history.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS heating_samples (ts INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
        self.schedule_writer = ScheduleWriter(self.root, self.config, self.fetch, self._send_schedule, self.bus_lock, self._update_schedule_cache)

    @staticmethod
    def _empty(point):
        return {'value': None, 'quality': 'pending', 'updated_at': None,
                'label': point.label, 'unit': point.unit, 'kind': point.kind}

    def _fetch(self, path):
        req = urllib.request.Request(self.url + path, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=6) as response:
            return json.loads(response.read(256*1024))

    def _send_schedule(self, path):
        # The writer constructs this bounded path; arbitrary user URLs never reach it.
        with urllib.request.urlopen(self.url + path, timeout=12) as response:
            return response.read(256*1024).decode('utf-8', 'replace')

    def _update_schedule_cache(self, area, payloads):
        with self.lock:
            for day,item in enumerate(self.schedules[area]):
                item.update(periods=decode_schedule(payloads[day]) if payloads is not None else item['periods'],
                            quality='valid' if payloads is not None else 'error', updated_at=time.time())
            self.last_schedule=0

    def start(self):
        with self.lock:
            if self.enabled and self.thread is None:
                self.thread = threading.Thread(target=self._run, name='heating-cache', daemon=True)
                self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self.poll()
            except Exception as error:
                logger.warning('Heating collection interrupted (%s)', type(error).__name__)
            self.stop_event.wait(self.interval)

    def poll(self):
        with self.bus_lock:
            try:
                self.schedule_writer.recover()
            except Exception:
                logger.warning('Heating schedule recovery is still pending')
            self._poll_bus()
        self._save_history()
        self._sync_iobroker()

    def _poll_bus(self):
        now = time.time()
        try:
            if self.own_address is None:
                info = self.fetch('/JI')
                devices = {d['dev_id']: (d['dev_fam'], d['dev_var']) for d in info.get('busdevices', [])}
                if info.get('bus') != 'LPB' or devices.get(0) != (22, 254) or devices.get(1) != (23, 254):
                    raise ValueError('unexpected heating controller identity')
                self.own_address = int(info['busaddr'])
            slow = now - self.last_slow > 300
            groups = {}
            for point in POINTS:
                if not point.slow or slow:
                    groups.setdefault((point.target, point.coid), []).append(point)
            successful = 0
            for (target, coid), definitions in groups.items():
                if self.stop_event.is_set():
                    return
                response = self.fetch(f'/JY06,{coid}!{target}')
                payload = read_frame(response, target, coid, self.own_address)
                for point in definitions:
                    try:
                        value = decode(point, payload)
                        quality = 'valid' if value is not None else 'unavailable'
                    except ValueError:
                        value, quality = None, 'error'
                    with self.lock:
                        self.metrics[point.area + '.' + point.key].update(value=value, quality=quality, updated_at=time.time())
                successful += payload is not None
            if slow:
                self.last_slow = now
            if now - self.last_schedule > 900:
                for area,target in (('eg',1),('og',0)):
                    for day in range(7):
                        if self.stop_event.is_set():
                            return
                        coid=f'05000A{0x8C+day:02X}'
                        payload=read_frame(self.fetch(f'/JY06,{coid}!{target}'),target,coid,self.own_address)
                        try:
                            periods=decode_schedule(payload)
                            quality='valid' if periods is not None else 'unavailable'
                        except ValueError:
                            periods,quality=None,'error'
                        with self.lock:
                            self.schedules[area][day].update(periods=periods,quality=quality,updated_at=time.time())
                self.last_schedule=now
            with self.lock:
                self.connection = {'connected': True, 'message': 'LPB verbunden', 'last_success': time.time(), 'objects': successful}
        except Exception as error:
            with self.lock:
                self.connection.update(connected=False, message='Heizungsbrücke nicht erreichbar' if not isinstance(error, ValueError) else 'Heizungsdaten konnten nicht bestätigt werden')
            logger.warning('Heating bridge read failed (%s)', type(error).__name__)

    def snapshot(self):
        now = time.time()
        with self.lock:
            metrics = deepcopy(self.metrics)
            for point in POINTS:
                item = metrics[point.area + '.' + point.key]
                age = now - item['updated_at'] if item['updated_at'] else None
                item['age_seconds'] = round(age) if age is not None else None
                if item['quality'] == 'valid' and age is not None and age > (900 if point.slow else max(90, self.interval*3)):
                    item['quality'] = 'stale'
            rooms = deepcopy(self.rooms)
            schedules=deepcopy(self.schedules)
            for days in schedules.values():
                for day in days:
                    if day['quality']=='valid' and now-day['updated_at']>1860:
                        day['quality']='stale'
            for room in rooms:
                room['stale'] = not self.io_status.get('tado_connected') or now - room.get('timestamp', 0) > 900
            return {'enabled': self.enabled, 'read_only': not self.schedule_writer.enabled, 'server_time': now,
                    'schedule_control': {'enabled': self.schedule_writer.enabled, 'recovery_required': bool(self.schedule_writer.pending)},
                    'connection': deepcopy(self.connection), 'iobroker': deepcopy(self.io_status),
                    'floors': {area: {'name': name, 'controller': model,
                                      'metrics': {k.split('.')[1]: v for k, v in metrics.items() if k.startswith(area + '.')}}
                               for area, name, model in [('eg', 'Erdgeschoss', 'Eurocontrol M'), ('og', 'Obergeschoss', 'Eurocontrol K')]},
                    'plant': {k.split('.')[1]: v for k, v in metrics.items() if k.startswith('anlage.')},
                    'rooms': rooms, 'schedules': schedules}

    def _sync_iobroker(self):
        url = self.config.get('iobroker_url')
        if not url:
            return
        bridge = IoBroker(url)
        try:
            bridge.connect()
            connection = bridge.call('getStates', 'tado.*.info.connection') or {}
            alive = bridge.call('getStates', 'system.adapter.tado.*.alive') or {}
            tado_connected = any(v.get('val') is True for v in connection.values()) and any(v.get('val') is True for v in alive.values())
            readings = {}
            for suffix in ('sensorDataPoints.insideTemperature.celsius', 'sensorDataPoints.humidity.percentage', 'setting.temperature.celsius', 'name'):
                readings.update(bridge.call('getStates', 'tado.*.Rooms.*.' + suffix) or {})
            names = self.config.get('room_names', {})
            floors = self.config.get('room_floors', {})
            rooms = []
            for key, state in readings.items():
                match = re.fullmatch(r'(tado\.\d+\.[^.]+\.Rooms\.([^.]+))\.sensorDataPoints\.insideTemperature\.celsius', key)
                if not match:
                    continue
                prefix, number = match.groups()
                native_name = readings.get(prefix + '.name', {}).get('val')
                name = names.get(prefix) or native_name or ('Raum ' + number)
                floor = floors.get(prefix)
                if floor not in ('eg', 'og', 'kg'):
                    floor = 'eg' if str(name).strip().lower() == 'wohnzimmer' else 'unassigned'
                value = state.get('val')
                if not native_name and value is None:
                    continue
                rooms.append({'id': prefix, 'name': str(name), 'floor': floor,
                              'temperature': value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and not state.get('q') else None,
                              'setpoint': readings.get(prefix + '.setting.temperature.celsius', {}).get('val'),
                              'humidity': readings.get(prefix + '.sensorDataPoints.humidity.percentage', {}).get('val'),
                              'timestamp': state.get('ts', 0)/1000})
            with self.lock:
                self.rooms = sorted(rooms, key=lambda r: r['name'].casefold())
                self.io_status = {'connected': True, 'tado_connected': tado_connected, 'namespace': IoBroker.PREFIX}
            snapshot = self.snapshot()
            for point in POINTS:
                item = snapshot['plant'][point.key] if point.area == 'anlage' else snapshot['floors'][point.area]['metrics'][point.key]
                key = f'{IoBroker.PREFIX}.{point.area}.{point.key}'
                if key not in self.objects_created:
                    existing = bridge.call('getObject', key)
                    if existing and existing.get('native', {}).get('managed_by') != 'smarthome-heating':
                        raise ValueError('existing ioBroker state belongs to another integration')
                    common = {'name': point.label, 'type': 'boolean' if point.kind in RELAY_KINDS or point.kind in ('boolean', 'enable') else 'string' if point.kind in TEXT_KINDS or point.kind.startswith('raw') else 'number',
                              'role': 'indicator' if point.kind in RELAY_KINDS or point.kind in ('boolean', 'enable') else 'text' if point.kind in TEXT_KINDS or point.kind.startswith('raw') else 'value.temperature' if point.unit == '°C' else 'value',
                              'read': True, 'write': False}
                    if point.unit:
                        common['unit'] = point.unit
                    if not existing or any(existing.get('common',{}).get(k) != v for k,v in common.items()):
                        obj = existing or {'type': 'state', 'common': {}, 'native': {}}
                        obj['common'] = {**obj['common'], **common}
                        obj['native']['managed_by'] = 'smarthome-heating'
                        bridge.call('setObject', key, obj)
                    self.objects_created.add(key)
                valid = item['quality'] == 'valid'
                bridge.call('setState', key, {'val': item['value'] if valid else None, 'ack': True, 'q': 0 if valid else 0x40})
            stats=self.statistics(24)
            for key,label,unit in [('starts','Beobachtete Brennerstarts · 24 h',''),
                                   ('relay_runtime_minutes','Beobachtete Relaislaufzeit · 24 h','min'),
                                   ('starts_per_hour','Starts je beobachteter Stunde · 24 h',''),
                                   ('relay_minutes_per_start','Relaisminuten je beobachtetem Start · 24 h','min'),
                                   ('coverage_percent','Datenabdeckung · 24 h','%')]:
                state_key=f'{IoBroker.PREFIX}.statistik.{key}_24h'
                if state_key not in self.objects_created:
                    existing=bridge.call('getObject',state_key)
                    if existing and existing.get('native',{}).get('managed_by')!='smarthome-heating':
                        raise ValueError('existing statistics state belongs to another integration')
                    if not existing:
                        bridge.call('setObject',state_key,{'type':'state','common':{'name':label,'type':'number','role':'value',
                            'read':True,'write':False,**({'unit':unit} if unit else {})},'native':{'managed_by':'smarthome-heating'}})
                    self.objects_created.add(state_key)
                valid=stats[key] is not None
                bridge.call('setState',state_key,{'val':stats[key],'ack':True,'q':0 if valid else 0x40})
            for area,days in snapshot['schedules'].items():
                for day in days:
                    key=f'{IoBroker.PREFIX}.{area}.schedule_{day["day"]}'
                    if key not in self.objects_created:
                        existing=bridge.call('getObject',key)
                        if existing and existing.get('native',{}).get('managed_by')!='smarthome-heating':
                            raise ValueError('existing schedule state belongs to another integration')
                        if not existing:
                            bridge.call('setObject',key,{'type':'state','common':{'name':f'{day["label"]} · Komfortzeiten · {area.upper()}',
                                        'type':'string','role':'text','read':True,'write':False},'native':{'managed_by':'smarthome-heating'}})
                        self.objects_created.add(key)
                    valid=day['quality']=='valid'
                    text=' · '.join(p['start']+'–'+p['end'] for p in (day['periods'] or [])) or 'Keine Komfortphase'
                    bridge.call('setState',key,{'val':text if valid else None,'ack':True,'q':0 if valid else 0x40})
        except Exception as error:
            with self.lock:
                self.io_status.update(connected=False, message='ioBroker-Verbindung unterbrochen')
            logger.warning('Heating ioBroker sync failed (%s)', type(error).__name__)
        finally:
            bridge.close()

    def _save_history(self):
        snapshot = self.snapshot()
        data = {}
        for area in ('eg', 'og'):
            for key in ('flow_actual', 'flow_setpoint', 'room_setpoint','outside','outside_attenuated','outside_composite'):
                item = snapshot['floors'][area]['metrics'].get(key)
                data[f'{area}.{key}'] = item['value'] if item and item['quality'] == 'valid' else None
        for key in ('boiler', 'dhw', 'burner', 'burner_stage2', 'starts','burner_hours'):
            item = snapshot['plant'][key]
            data['anlage.' + key] = item['value'] if item['quality'] == 'valid' else None
        with closing(sqlite3.connect(self.db_path, timeout=5)) as db, db:
            now = int(time.time())
            db.execute('INSERT OR REPLACE INTO heating_samples VALUES (?, ?)', (now, json.dumps(data, allow_nan=False)))
            db.execute('DELETE FROM heating_samples WHERE ts < ?', (now - 30*86400,))

    def history(self, hours):
        cutoff = int(time.time()) - hours*3600
        with closing(sqlite3.connect(self.db_path, timeout=5)) as db:
            rows = db.execute('SELECT ts,payload FROM heating_samples WHERE ts>=? ORDER BY ts', (cutoff,)).fetchall()
        # Bound response size and average into time buckets, preserving gaps.
        width = max(1, (len(rows)+359)//360)
        result = []
        parsed = [json.loads(row[1]) for row in rows]
        keys = sorted(set().union(*(entry.keys() for entry in parsed)))
        for start in range(0, len(rows), width):
            bucket = rows[start:start+width]
            entries = parsed[start:start+width]
            merged = {}
            for key in keys:
                values = [e[key] for e in entries if isinstance(e.get(key), (int, float))]
                if len(values) != len(entries):
                    merged[key] = None
                elif key in ('anlage.burner', 'anlage.burner_stage2', 'anlage.starts', 'anlage.burner_hours', 'eg.flow_setpoint', 'eg.room_setpoint', 'og.room_setpoint'):
                    merged[key] = entries[-1][key]
                else:
                    merged[key] = sum(values)/len(values)
            result.append({'ts': bucket[-1][0], **merged})
        return result

    def statistics(self, hours):
        now=time.time()
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            rows=db.execute('SELECT ts,payload FROM heating_samples WHERE ts>=? ORDER BY ts',(int(now-hours*3600),)).fetchall()
        return summarize([{'ts':ts,**json.loads(data)} for ts,data in rows],hours,now,
                         max_gap=max(120,self.interval*3))



def register_heating_routes(manager, root=None):
    app = manager.app
    service = HeatingService(root or os.getcwd())

    @app.route('/heizung')
    def heating_page():
        service.start()
        return render_template('heating.html')

    @app.route('/api/heating/state')
    def heating_state():
        service.start()
        response = jsonify(service.snapshot())
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.route('/api/heating/history')
    def heating_history():
        try:
            hours = int(request.args.get('hours', '6'))
        except ValueError:
            return jsonify({'error': 'invalid_hours'}), 400
        if hours not in (1, 6, 24):
            return jsonify({'error': 'invalid_hours'}), 400
        return jsonify({'hours': hours, 'samples': service.history(hours)})

    @app.route('/api/heating/statistics')
    def heating_statistics():
        try:
            hours=int(request.args.get('hours','6'))
        except ValueError:
            return jsonify({'error':'invalid_hours'}),400
        if hours not in (1,6,24):
            return jsonify({'error':'invalid_hours'}),400
        return jsonify(service.statistics(hours))

    def schedule_guard():
        if request.headers.get('X-Heating-Schedule') != '1' or not request.is_json:
            raise ScheduleError('Übertragung benötigt eine bestätigte JSON-Anfrage.', 403)
        origin=request.headers.get('Origin')
        if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
            raise ScheduleError('Diese Anfrage stammt nicht von der SmartHome-Oberfläche.', 403)

    def schedule_request(action):
        try:
            schedule_guard()
            body=request.get_json(silent=True)
            owner=str(request.remote_addr or '')
            if action == 'preview':
                result=service.schedule_writer.preview(body,owner)
            else:
                if not isinstance(body,dict) or set(body) != {'token'}:
                    raise ScheduleError('Ungültige Übernahmebestätigung.')
                result=service.schedule_writer.apply(body['token'],owner)
            return jsonify(result)
        except ScheduleError as error:
            return jsonify({'success':False,'message':str(error),**error.details}),error.status
        except Exception as error:
            logger.warning('Heating schedule request failed (%s)',type(error).__name__)
            return jsonify({'success':False,'message':'Die Heizungsbrücke konnte nicht bestätigt werden. Bitte den Reglerstand erneut prüfen.'}),503

    @app.route('/api/heating/schedule/preview',methods=['POST'])
    def heating_schedule_preview():
        return schedule_request('preview')

    @app.route('/api/heating/schedule/apply',methods=['POST'])
    def heating_schedule_apply():
        return schedule_request('apply')

    return service
