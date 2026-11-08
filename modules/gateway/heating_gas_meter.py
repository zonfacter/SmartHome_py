"""Occasional cumulative gas meter readings. No device or control interface."""
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
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


class GasMeter:
    def __init__(self,db_path):
        self.db_path=db_path
        with closing(sqlite3.connect(db_path,timeout=5)) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS heating_gas_readings(ts INTEGER PRIMARY KEY,volume_milli_m3 INTEGER NOT NULL CHECK(volume_milli_m3>=0),created_at INTEGER NOT NULL)')

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
