"""Occasional cumulative gas meter readings. No device or control interface."""
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
import math
import json
import sqlite3
import time
from zoneinfo import ZoneInfo


class MeterError(ValueError):
    def __init__(self,message,status=400):super().__init__(message);self.status=status


def parse_reading(body,now=None):
    if not isinstance(body,dict) or set(body)!={'measured_at','volume_m3'}:
        raise MeterError('Datum, Uhrzeit und Zählerstand werden benötigt.')
    value=body['volume_m3']
    if isinstance(value,bool) or not isinstance(value,(str,int,float)):
        raise MeterError('Zählerstand als Zahl mit höchstens drei Nachkommastellen eingeben.')
    raw=str(value).strip().replace(',','.')
    if not re.fullmatch(r'\d{1,9}(?:\.\d{1,3})?',raw):
        raise MeterError('Zählerstand ohne Tausendertrennzeichen eingeben, z. B. 1234,567.')
    try:units=int(Decimal(raw)*1000)
    except (InvalidOperation,OverflowError):raise MeterError('Ungültiger Zählerstand.')
    try:
        stamp=body['measured_at']
        if not isinstance(stamp,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::00)?(?:[+-]\d{2}:\d{2}|Z)?',stamp):raise ValueError()
        date=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        if date.tzinfo is None:
            berlin=ZoneInfo('Europe/Berlin');local=date.replace(tzinfo=berlin)
            if local.utcoffset()!=date.replace(tzinfo=berlin,fold=1).utcoffset():
                raise MeterError('Diese Uhrzeit liegt in einer Zeitumstellung. Bitte einen eindeutigen Zeitpunkt mit Zeitzonenoffset angeben.')
            date=local
        ts=int(date.timestamp())
        if date.astimezone(timezone.utc).astimezone(date.tzinfo).replace(tzinfo=None)!=date.replace(tzinfo=None):raise ValueError()
    except MeterError:raise
    except (ValueError,OverflowError,TypeError):raise MeterError('Gültiges Datum und Uhrzeit angeben (Europe/Berlin).')
    if ts<946684800 or ts>(time.time() if now is None else now)+300:
        raise MeterError('Der Messzeitpunkt muss seit 2000 liegen und darf nicht in der Zukunft liegen.')
    return ts,units


def fit_meter_calibration(readings,reference):
    """Non-overlapping long meter intervals; no inference of flame-on time."""
    ordered=sorted(readings,key=lambda r:r['ts']);blocks=[];anchor=ordered[0] if ordered else None
    for reading in ordered[1:]:
        seconds=reading['ts']-anchor['ts']
        if seconds<3600:continue
        ref=reference(anchor['ts'],reading['ts']);minutes=ref.get('relay_minutes');coverage=ref.get('coverage_percent',0)
        delta=round(reading['volume_m3']-anchor['volume_m3'],3)
        reason='Messabdeckung unter 95 %' if coverage<95 else 'Weniger als 10 Relaisminuten' if minutes is None or minutes<10 else None
        rate=delta*60/minutes if reason is None and minutes>0 else None
        blocks.append({'from':anchor['ts'],'to':reading['ts'],'hours':seconds/3600,'measured_m3':delta,
                       'relay_minutes':minutes,'coverage_percent':coverage,'eligible':reason is None,
                       'excluded_reason':reason,'m3_per_relay_hour':rate})
        anchor=reading
    used=[b for b in blocks if b['eligible']];total=sum(b['relay_minutes'] for b in used)
    measured=sum(b['measured_m3'] for b in used);candidate=measured*60/total if total else None
    rates=[b['m3_per_relay_hour'] for b in used]
    spread=(max(rates)-min(rates))/candidate*100 if candidate and rates else None
    inconsistent=bool(used) and (any(r<=0 or not math.isfinite(r) for r in rates) or spread is not None and spread>25)
    state='inconsistent' if inconsistent else 'provisional' if len(used)>=2 and total>=60 else 'collecting'
    factor=candidate if state=='provisional' else None;check=None
    if len(used)>=2 and sum(b['relay_minutes'] for b in used[:-1])>0:
        prior=sum(b['measured_m3'] for b in used[:-1])*60/sum(b['relay_minutes'] for b in used[:-1]);last=used[-1]
        predicted=prior*last['relay_minutes']/60
        check={'from':last['from'],'to':last['to'],'predicted_m3':predicted,'measured_m3':last['measured_m3'],
               'relative_error_percent':abs(predicted-last['measured_m3'])/last['measured_m3']*100 if last['measured_m3']>0 else None}
    return {'version':1,'state':state,'coefficient_m3_per_relay_hour':factor,'used_intervals':len(used),
            'total_relay_minutes':total,'total_measured_m3':measured,'factor_spread_percent':spread,
            'cross_check':check,'blocks':blocks,'minimum_interval_hours':1,'minimum_coverage_percent':95,
            'pending_since':anchor['ts'] if anchor and ordered[-1]['ts']>anchor['ts'] else None,
            'limits':'Vorläufiger empirischer Abgleich des Gesamtzählers mit K4/K5-Relaiszeiten. Keine Flammenlaufzeit, keine gemessene Brennerleistung, keine Aufteilung auf EG, OG oder Warmwasser.'}


class GasMeter:
    def __init__(self,db_path):
        self.db_path=db_path
        with closing(sqlite3.connect(db_path,timeout=5)) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS heating_gas_readings(ts INTEGER PRIMARY KEY,volume_milli_m3 INTEGER NOT NULL CHECK(volume_milli_m3>=0),created_at INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS heating_gas_calibration(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL)')

    def calibration(self,reference,readings=None):
        result=fit_meter_calibration(self.summary()['readings'] if readings is None else readings,reference)
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db,db:
            if result['state']=='provisional':
                payload=json.dumps(result,allow_nan=False)
                old=db.execute('SELECT payload FROM heating_gas_calibration WHERE id=1').fetchone()
                if not old or old[0]!=payload:db.execute('INSERT OR REPLACE INTO heating_gas_calibration VALUES (1,?)',(payload,))
            elif result['state']=='collecting' and any(b['coverage_percent']<95 for b in result['blocks']):
                old=db.execute('SELECT payload FROM heating_gas_calibration WHERE id=1').fetchone()
                if old:
                    saved=json.loads(old[0]);saved.update(state='historical',current_blocks=result['blocks'])
                    return saved
        return result

    def add(self,body,now=None):
        ts,units=parse_reading(body,now)
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            existing=db.execute('SELECT volume_milli_m3 FROM heating_gas_readings WHERE ts=?',(ts,)).fetchone()
            if existing:
                if existing[0]!=units:raise MeterError('Für diesen Zeitpunkt ist bereits ein anderer Stand gespeichert.',409)
                return {'inserted':False,'reading':self.reading(ts,units)}
            previous=db.execute('SELECT volume_milli_m3 FROM heating_gas_readings WHERE ts<? ORDER BY ts DESC LIMIT 1',(ts,)).fetchone()
            following=db.execute('SELECT volume_milli_m3 FROM heating_gas_readings WHERE ts>? ORDER BY ts LIMIT 1',(ts,)).fetchone()
            if previous and previous[0]>units or following and following[0]<units:
                raise MeterError('Der Stand passt nicht zur zeitlichen Reihenfolge der vorhandenen Zählerstände. Bitte Datum und Zahl prüfen; einen Zählerwechsel separat behandeln.',409)
            db.execute('INSERT INTO heating_gas_readings VALUES (?,?,?)',(ts,units,int(time.time())))
        return {'inserted':True,'reading':self.reading(ts,units)}

    @staticmethod
    def reading(ts,units):return {'ts':ts,'volume_m3':units/1000,'volume_text':f'{units//1000},{units%1000:03d}'}

    def summary(self):
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            count=db.execute('SELECT COUNT(*) FROM heating_gas_readings').fetchone()[0]
            rows=db.execute('SELECT ts,volume_milli_m3 FROM heating_gas_readings ORDER BY ts DESC LIMIT 100').fetchall()
        readings=[self.reading(ts,units) for ts,units in rows]
        interval=None
        if len(rows)>1:
            interval={'from':rows[1][0],'to':rows[0][0],'hours':(rows[0][0]-rows[1][0])/3600,
                      'measured_m3':(rows[0][1]-rows[1][1])/1000}
        return {'count':count,'readings':readings,'latest':readings[0] if readings else None,'latest_interval':interval,
                'retention':'Dauerhaft, unabhängig vom 90-Tage-Messarchiv','interpolation':False,
                'scope':'Kumulativer Gaszähler der gesamten Anlage; keine gemessene Aufteilung auf EG, OG oder Warmwasser.'}
