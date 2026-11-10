"""External, read-only thermometry and local drawing metadata. No actuator API."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime
import json
import math
import re
import sqlite3
import statistics
import threading
import time

CHANNELS = tuple((f'sensor_{i}',f'S{i}',f'Fühler {i} · Zuordnung offen') for i in range(1,8))
ROLES = {'unknown':'Zuordnung offen','charge_supply':'Speicherlade-Vorlauf','charge_return':'Speicherlade-Rücklauf',
         'og_supply':'OG-Vorlauf','og_return':'OG-Rücklauf','eg_return':'EG-Rücklauf',
         'circulation_return':'Trinkwasser-Zirkulationsrücklauf','ambient':'Heizungsraum · Luft'}
KINDS = ('boiler','tank','pump','circulation_pump','valve','check_valve','mixer','radiator',
         'floor_heating','manifold','junction','sensor','label','expansion_vessel','heat_exchanger')
EVENT_KINDS = ('circulation_open','circulation_closed','draw','no_draw','pump_test','sensor_test')


class SetupError(ValueError):
    def __init__(self, message, status=400):super().__init__(message);self.status=status


def number(v):return type(v) in (int,float) and math.isfinite(v)
def text(v, maximum=120, multiline=False):
    if not isinstance(v,str) or len(v)>maximum or any(ord(c)<32 and (not multiline or c not in '\n\r\t') for c in v):raise SetupError('Ungültiger Text.')
    return v.strip()
def object_id(v):
    v=text(v,240)
    if v and (not re.fullmatch(r'[\w][\w.:\- /]*',v) or '*' in v):raise SetupError('Bitte eine konkrete ioBroker-ID angeben.')
    return v
def default_channels():
    return [{'key':key,'tag':tag,'label':label,'role':'unknown','hardware_id':'','state_id':'','timestamp_id':'',
             'availability_id':'','availability_value':True,'max_age_seconds':60} for key,tag,label in CHANNELS]


def validate_config(data):
    if not isinstance(data,dict) or not isinstance(data.get('channels'),list) or len(data['channels'])!=len(CHANNELS):raise SetupError('Genau sieben Messkanäle werden benötigt.')
    result=[];seen=set();keys=set();roles=set()
    for c in data['channels']:
        if not isinstance(c,dict) or not isinstance(c.get('key'),str) or c.get('key') not in {k for k,_,_ in CHANNELS} or c['key'] in keys:raise SetupError('Ungültiger Messkanal.')
        keys.add(c['key']);base=next(d for d in default_channels() if d['key']==c['key'])
        base.update(label=text(c.get('label',base['label']),80),state_id=object_id(c.get('state_id','')),
                    timestamp_id=object_id(c.get('timestamp_id','')),availability_id=object_id(c.get('availability_id','')))
        role=c.get('role','unknown')
        if not isinstance(role,str) or role not in ROLES or (role!='unknown' and role in roles):raise SetupError('Eine bestätigte Funktion darf nur einmal zugeordnet sein.')
        roles.add(role);base['role']=role;base['hardware_id']=text(c.get('hardware_id',''),40)
        online=c.get('availability_value',True)
        if type(online) is not bool and (not isinstance(online,str) or not online or len(online)>40):raise SetupError('Ungültiger Online-Zustand.')
        base['availability_value']=online
        age=c.get('max_age_seconds',60)
        if type(age) is not int or not 20<=age<=3600:raise SetupError('Das Gültigkeitsalter muss zwischen 20 und 3600 Sekunden liegen.')
        base['max_age_seconds']=age
        if not base['label']:raise SetupError('Die Messstelle benötigt einen Namen.')
        if base['state_id']:
            if base['state_id'] in seen:raise SetupError('Eine Temperatur-ID darf nur einer Messstelle zugeordnet sein.')
            seen.add(base['state_id'])
            if base['state_id'] in (base['timestamp_id'],base['availability_id']):raise SetupError('Temperatur, Zeit und Verfügbarkeit benötigen unterschiedliche IDs.')
        result.append(base)
    return {'channels':sorted(result,key=lambda c:next(i for i,d in enumerate(CHANNELS) if d[0]==c['key']))}


def validate_plan(data):
    if not isinstance(data,dict):raise SetupError('Ungültiger Anlagenplan.')
    nodes=data.get('nodes',[]);edges=data.get('edges',[])
    if not isinstance(nodes,list) or len(nodes)>180 or not isinstance(edges,list) or len(edges)>360:raise SetupError('Der Plan ist zu groß.')
    result={'schema':1,'title':text(data.get('title','Meine Heizungsanlage'),100),'nodes':[],'edges':[]}
    ids=set();sensors=set()
    def ident(v):
        if not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',v) or v in ids:raise SetupError('Bauteil-/Leitungs-IDs müssen eindeutig sein.')
        ids.add(v);return v
    def coordinate(v):
        if not number(v) or not 0<=v<=4000:raise SetupError('Koordinate außerhalb der Zeichenfläche.')
        return round(v,1)
    for n in nodes:
        if not isinstance(n,dict) or n.get('type') not in KINDS:raise SetupError('Unbekanntes Bauteil.')
        rotation=n.get('rotation',0)
        if type(rotation) is not int or rotation not in (0,90,180,270):raise SetupError('Ungültige Drehung.')
        c={'id':ident(n.get('id')),'type':n['type'],'label':text(n.get('label',''),100),'x':coordinate(n.get('x')),
           'y':coordinate(n.get('y')),'rotation':rotation,'sensor':text(n.get('sensor',''),30),'note':text(n.get('note',''),500,True)}
        if c['sensor']:
            if c['type']!='sensor' or c['sensor'] not in {k for k,_,_ in CHANNELS} or c['sensor'] in sensors:raise SetupError('Eine Messstelle darf nur einer Fühlermarkierung zugeordnet sein.')
            sensors.add(c['sensor'])
        result['nodes'].append(c)
    node_ids={n['id'] for n in result['nodes']}
    for e in edges:
        if not isinstance(e,dict):raise SetupError('Ungültige Leitung.')
        c={'id':ident(e.get('id')),'label':text(e.get('label',''),80),'medium':e.get('medium','neutral'),'points':[]}
        if c['medium'] not in ('hot','cold','neutral','potable'):raise SetupError('Ungültiger Leitungstyp.')
        for end in ('from','to'):
            a=e.get(end)
            if not isinstance(a,dict) or not isinstance(a.get('node'),str) or a.get('node') not in node_ids or a.get('port') not in ('n','e','s','w'):raise SetupError('Leitung benötigt zwei vorhandene Anschlüsse.')
            c[end]={'node':a['node'],'port':a['port']}
        if c['from']==c['to']:raise SetupError('Eine Leitung benötigt verschiedene Anschlüsse.')
        points=e.get('points',[])
        if not isinstance(points,list) or len(points)>12:raise SetupError('Zu viele Leitungsknicke.')
        for p in points:
            if not isinstance(p,dict):raise SetupError('Ungültiger Leitungsknick.')
            c['points'].append({'x':coordinate(p.get('x')),'y':coordinate(p.get('y'))})
        result['edges'].append(c)
    return result


def read_channel(config, states, now):
    result={**config,'value':None,'quality':'unconfigured' if not config['state_id'] else 'unavailable',
            'measurement_ts':None,'received_ts':None,'time_basis':'measurement_state' if config['timestamp_id'] else 'iobroker_state'}
    if not config['state_id']:return result
    def checked(key,allow_old=False):
        s=states.get(key) or {};stamp=s.get('ts')
        if s.get('q') or s.get('ack') is not True:return None,'error',None
        if not number(stamp) or stamp<=0 or stamp/1000>now+30:return None,'error',None
        stamp/=1000
        if not allow_old and now-stamp>config['max_age_seconds']:return None,'stale',stamp
        return s.get('val'),'valid',stamp
    if config['availability_id']:
        available,aq,_=checked(config['availability_id'],allow_old=True)
        target=config.get('availability_value',True)
        if aq!='valid' or type(available) is not type(target) or available!=target:
            result['quality']=aq if aq!='valid' else 'offline';return result
    v,q,received=checked(config['state_id']);result.update(received_ts=received,quality=q)
    if q!='valid':return result
    low,high=(-30,70) if config.get('role')=='ambient' else (-55,125)
    if not number(v) or not low<=v<=high:result['quality']='error';return result
    measured=received
    if config['timestamp_id']:
        stamp,sq,_=checked(config['timestamp_id'])
        if sq!='valid':result['quality']=sq;return result
        try:
            if number(stamp):measured=stamp/1000 if stamp>1e11 else stamp
            elif isinstance(stamp,str):
                date=datetime.fromisoformat(stamp.replace('Z','+00:00'))
                if date.tzinfo is None:raise ValueError()
                measured=date.timestamp()
            else:raise ValueError()
        except (ValueError,OverflowError,OSError):result['quality']='error';return result
    if not number(measured) or measured<=0 or measured>now+30:result['quality']='error';return result
    result['measurement_ts']=measured
    if now-measured>config['max_age_seconds']:result['quality']='stale';return result
    if config['availability_id']:
        # MQTT LWT is a latched session state, not a periodic measurement heartbeat.
        available,aq,_=checked(config['availability_id'],allow_old=True)
        target=config.get('availability_value',True)
        if aq!='valid' or type(available) is not type(target) or available!=target:result['quality']=aq if aq!='valid' else 'offline';return result
    result.update(value=v,quality='valid');return result


class Instrumentation:
    def __init__(self, db_path, url, bridge_factory, context):
        self.db_path=db_path;self.url=url;self.bridge_factory=bridge_factory;self.context=context
        self.lock=threading.RLock();self.stop_event=threading.Event();self.thread=None;self.last_poll=None;self.error=None
        with closing(sqlite3.connect(db_path,timeout=5)) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS heating_setup(kind TEXT PRIMARY KEY,revision INTEGER NOT NULL,payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS heating_sensor_samples(ts INTEGER PRIMARY KEY,payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS heating_experiment_notes(id INTEGER PRIMARY KEY,ts INTEGER NOT NULL,ended_at INTEGER,kind TEXT NOT NULL,note TEXT NOT NULL)')
        self.config=self.document('sensors')['data'];self.live=[read_channel(c,{},time.time()) for c in self.config['channels']]

    def document(self,kind):
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            row=db.execute('SELECT revision,payload FROM heating_setup WHERE kind=?',(kind,)).fetchone()
        default={'channels':default_channels()} if kind=='sensors' else {'schema':1,'title':'Meine Heizungsanlage','nodes':[],'edges':[]}
        return {'revision':row[0] if row else 0,'data':json.loads(row[1]) if row else default}

    def save(self,kind,body):
        if not isinstance(body,dict) or type(body.get('revision')) is not int:raise SetupError('Die Dokumentversion fehlt.')
        data=validate_config(body.get('data')) if kind=='sensors' else validate_plan(body.get('data'))
        with self.lock,closing(sqlite3.connect(self.db_path,timeout=5)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT revision FROM heating_setup WHERE kind=?',(kind,)).fetchone()
            revision=row[0] if row else 0
            if revision!=body['revision']:raise SetupError('Zwischenzeitlich wurde ein neuer Stand gespeichert. Bitte deinen Entwurf exportieren und den aktuellen Stand neu laden.',409)
            db.execute('INSERT OR REPLACE INTO heating_setup VALUES (?,?,?)',(kind,revision+1,json.dumps(data,allow_nan=False)))
            if kind=='sensors':
                self.config=data;self.live=[read_channel(c,{},time.time()) for c in data['channels']]
        return {'revision':revision+1,'data':data}

    def start(self):
        with self.lock:
            if self.thread is None and any(c['state_id'] for c in self.config['channels']):
                self.thread=threading.Thread(target=self._run,name='heating-external-sensors',daemon=True);self.thread.start()
    def stop(self):self.stop_event.set()
    def _run(self):
        while not self.stop_event.is_set():
            started=time.monotonic()
            try:self.poll()
            except Exception as error:
                with self.lock:self.error=type(error).__name__;self.live=[read_channel(c,{},time.time()) for c in self.config['channels']]
            self.stop_event.wait(max(1,10-(time.monotonic()-started)))

    def poll(self,now=None):
        supplied_now=now
        now=time.time() if now is None else now
        with self.lock:config=deepcopy(self.config)
        ids={c[k] for c in config['channels'] for k in ('state_id','timestamp_id','availability_id') if c[k]}
        states={};error=None
        if ids and self.url:
            bridge=self.bridge_factory(self.url)
            try:
                bridge.connect()
                for key in sorted(ids):states[key]=bridge.call('getState',key) or {}
            except Exception as e:error=type(e).__name__;states={}
            finally:bridge.close()
        elif ids:error='NoIoBrokerURL'
        # Freshness is evaluated after the network reads, never at their start.
        at=supplied_now if supplied_now is not None else time.time()
        channels=[read_channel(c,states,at) for c in config['channels']]
        with self.lock:
            if config!=self.config:return
            self.live=channels;self.error=error;self.last_poll=at
        if ids:
            payload={'channels':{c['key']:{k:c[k] for k in ('value','quality','measurement_ts','received_ts','time_basis','state_id','role','hardware_id')} for c in channels},
                     'context':self.context_data(self.context(),at)}
            with closing(sqlite3.connect(self.db_path,timeout=5)) as db,db:
                db.execute('INSERT OR IGNORE INTO heating_sensor_samples VALUES (?,?)',(int(at),json.dumps(payload,allow_nan=False)))
                db.execute('DELETE FROM heating_sensor_samples WHERE ts<?',(int(at)-90*86400,))

    @staticmethod
    def context_data(s,now):
        result={}
        for key,item in {**{k:s.get('plant',{}).get(k,{}) for k in ('dhw','boiler','dhw_pump','burner')},
                         **{a+'_pump':s.get('floors',{}).get(a,{}).get('metrics',{}).get('pump',{}) for a in ('eg','og')}}.items():
            stamp=item.get('updated_at');valid=s.get('connection',{}).get('connected') and item.get('quality')=='valid' and number(stamp) and 0<=now-stamp<=90
            result[key]={'value':item.get('value') if valid else None,'quality':'valid' if valid else 'unavailable','measurement_ts':stamp}
        return result

    def snapshot(self,now=None):
        now=time.time() if now is None else now
        with self.lock:channels=deepcopy(self.live);last=self.last_poll;error=self.error
        for c in channels:
            c['age_seconds']=round(now-c['measurement_ts'],1) if number(c['measurement_ts']) else None
            if c['quality']=='valid' and (c['age_seconds']< -30 or c['age_seconds']>c['max_age_seconds']):c.update(value=None,quality='stale')
        return {'channels':channels,'last_poll':last,'error':error,'poll_seconds':10,'retention_days':90,'read_only':True,
                'configured':sum(bool(c['state_id']) for c in channels),'identified':sum(c.get('role','unknown')!='unknown' for c in channels)}

    def history(self,hours,now=None):
        now=int(time.time() if now is None else now);start=now-hours*3600
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            first=db.execute('SELECT MIN(ts) FROM heating_sensor_samples WHERE ts>=? AND ts<=?',(start,now)).fetchone()[0]
        seconds=max(10,math.ceil((now-first+1)/720)) if first is not None else 10
        fields=[]
        for key,_,_ in CHANNELS:
            p=f'$.channels.{key}'
            value=f"CASE WHEN json_extract(payload,'{p}.quality')='valid' AND json_type(payload,'{p}.value') IN ('integer','real') THEN json_extract(payload,'{p}.value') END"
            fields.extend([f'AVG({value})',f'MIN({value})',f'MAX({value})',f'COUNT({value})',f"MAX(json_extract(payload,'{p}.measurement_ts'))"])
        # Aggregate in SQLite so 90 days never become a huge Python response/list.
        query="""WITH ordered AS (
            SELECT ts,payload,ts-LAG(ts) OVER (ORDER BY ts) AS gap
            FROM heating_sensor_samples WHERE ts>=? AND ts<=?
        ), aggregated AS (
            SELECT (ts-?)/? AS bucket,MIN(ts) AS first_ts,MAX(ts) AS last_ts,
                   COUNT(*) AS count,MAX(COALESCE(gap,31)) AS max_gap,"""+','.join(fields)+"""
            FROM ordered GROUP BY bucket
        ) SELECT a.*,json_extract(s.payload,'$.context') FROM aggregated a
          JOIN heating_sensor_samples s ON s.ts=a.last_ts ORDER BY a.bucket"""
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            rows=db.execute(query,(start,now,start,seconds)).fetchall()
        samples=[];previous=None
        for row in rows:
            _,first,last,count,gap,*values=row;context=values.pop()
            item={'ts':last,'channels':{},'context':json.loads(context) if context else {}}
            for i,(key,_,_) in enumerate(CHANNELS):
                mean,low,high,valid,measured=values[i*5:i*5+5];complete=valid==count
                item['channels'][key]={'value':mean if complete else None,'minimum':low,'maximum':high,
                    'quality':'valid' if complete else 'gap','break_before':previous is None or first-previous>30 or gap>30,
                    'measurement_ts':measured}
            samples.append(item);previous=last
        return {'hours':hours,'bucket_seconds':seconds,'samples':samples,'retention_days':90}

    def notes(self,hours=2160):
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            rows=db.execute('SELECT id,ts,ended_at,kind,note FROM heating_experiment_notes ORDER BY ts DESC,id DESC LIMIT 500').fetchall()
        return [{'id':i,'ts':ts,'ended_at':end,'kind':kind,'note':note,'source':'user_report'} for i,ts,end,kind,note in rows]

    def add_note(self,body,now=None):
        now=time.time() if now is None else now
        if not isinstance(body,dict) or body.get('kind') not in EVENT_KINDS:raise SetupError('Ungültige Versuchsnotiz.')
        start=body.get('ts');end=body.get('ended_at');kind=body['kind']
        if not number(start) or not 0<start<=now+60:raise SetupError('Bitte einen vergangenen Zeitpunkt mit Zeitzone angeben.')
        if kind in ('draw','no_draw','pump_test','sensor_test') and (not number(end) or not start<end<=now+60 or end-start>7*86400):raise SetupError('Für diesen Versuch werden Beginn und Ende benötigt (maximal sieben Tage).')
        if kind.startswith('circulation_'):end=None
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db,db:
            cursor=db.execute('INSERT INTO heating_experiment_notes(ts,ended_at,kind,note) VALUES (?,?,?,?)',(int(start),int(end) if end else None,kind,text(body.get('note',''),300)))
        return {'id':cursor.lastrowid,'saved':True,'source':'user_report'}

    def diagnosis(self,hours=24,now=None):
        now=int(time.time() if now is None else now)
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            rows=db.execute('SELECT ts,payload FROM heating_sensor_samples WHERE ts>=? AND ts<=? ORDER BY ts',(now-hours*3600,now)).fetchall()
        return loss_diagnosis([{'ts':ts,**json.loads(p)} for ts,p in rows],self.notes(),hours)


def loss_diagnosis(rows,notes,hours):
    """Describe cooling conditional on pump/valve state; never infer measured flow."""
    result={'state':'collecting','hours':hours,'windows':0,'groups':[],'excluded':{'gaps':0,'invalid':0,'charging':0,'pump_change':0,'draw':0,'manual_test':0},
            'source':'Speicherfühler, externe Rohrfühler, Pumpenrelais und manuelle Versuchsnotizen.',
            'limits':'Beobachtete Zusammenhänge; keine Durchflussmessung, keine bestätigte Strömungsrichtung, keine Verlustleistung oder Gasersparnis. Unbekannte Entnahmen bleiben unbekannt.'}
    buckets={}
    for row in rows:buckets.setdefault(row['ts']//600,[]).append(row)
    groups={}
    def metric(r,key):
        v=r['context'].get(key,{})
        return v.get('value') if v.get('quality')=='valid' else None
    def channel(r,key):
        matches=[c for c in r['channels'].values() if c.get('role')==key]
        v=matches[0] if len(matches)==1 else {}
        return v.get('value') if v.get('quality')=='valid' else None
    for entries in buckets.values():
        a,b=entries[0]['ts'],entries[-1]['ts']
        if len(entries)<5 or b-a<480 or any(y['ts']-x['ts']>30 for x,y in zip(entries,entries[1:])):result['excluded']['gaps']+=1;continue
        temps=[metric(r,'dhw') for r in entries]
        loads=[metric(r,'dhw_pump') for r in entries]
        states=[(metric(r,'eg_pump'),metric(r,'og_pump')) for r in entries]
        if not all(number(t) for t in temps) or any(type(v) is not bool for state in states for v in state) or any(type(v) is not bool for v in loads):result['excluded']['invalid']+=1;continue
        if any(loads):result['excluded']['charging']+=1;continue
        if len(set(states))!=1:result['excluded']['pump_change']+=1;continue
        overlapping=[n for n in notes if n['ts']<=b and (n.get('ended_at') or n['ts'])>=a]
        if any(n['kind']=='draw' for n in overlapping):result['excluded']['draw']+=1;continue
        if any(n['kind'] in ('pump_test','sensor_test') for n in overlapping):result['excluded']['manual_test']+=1;continue
        valve=[]
        for t in (a,b):
            candidates=[n for n in notes if n['kind'].startswith('circulation_') and n['ts']<=t]
            valve.append(max(candidates,key=lambda n:(n['ts'],n.get('id',0)))['kind'] if candidates else 'unknown')
        if valve[0]!=valve[1] or any(n['kind'].startswith('circulation_') and a<n['ts']<=b for n in notes):result['excluded']['manual_test']+=1;continue
        supply=[channel(r,'charge_supply') for r in entries];ret=[channel(r,'charge_return') for r in entries]
        if not all(number(v) for v in supply+ret):result['excluded']['invalid']+=1;continue
        # Mapping changes cannot silently join measurements from different pipes.
        signatures=[]
        for role in ('charge_supply','charge_return'):
            signatures.append({tuple((k,c.get('state_id'),c.get('hardware_id')) for k,c in r['channels'].items() if c.get('role')==role) for r in entries})
        if any(len(s)!=1 for s in signatures):result['excluded']['invalid']+=1;continue
        no_draw=any(n['kind']=='no_draw' and n['ts']<=a and n.get('ended_at',0)>=b for n in notes)
        band=int(statistics.mean(temps)//5)*5
        key=(states[0],valve[0],no_draw,band,tuple(next(iter(s)) for s in signatures))
        g=groups.setdefault(key,{'eg':states[0][0],'og':states[0][1],'circulation':valve[0],'draw_status':'none_reported' if no_draw else 'unknown',
            'tank_band':[band,band+5],'windows':0,'rates':[],'coil_deltas':[],'boiler_deltas':[],'sensor_means':{k:[] for k in ROLES if k!='unknown'}})
        mx=statistics.mean(r['ts'] for r in entries);my=statistics.mean(temps)
        slope=-3600*sum((r['ts']-mx)*(v-my) for r,v in zip(entries,temps))/sum((r['ts']-mx)**2 for r in entries)
        g['windows']+=1;g['rates'].append(slope);g['coil_deltas'].append(statistics.mean(supply)-statistics.mean(ret))
        boiler=[metric(r,'boiler') for r in entries]
        if all(number(v) for v in boiler):g['boiler_deltas'].append(statistics.mean(boiler)-my)
        for k in g['sensor_means']:
            vv=[channel(r,k) for r in entries]
            if all(number(v) for v in vv):g['sensor_means'][k].append(statistics.mean(vv))
    for g in groups.values():
        g['median_cooling_c_per_hour']=round(statistics.median(g.pop('rates')),3)
        g['median_charge_supply_minus_return_c']=round(statistics.median(g.pop('coil_deltas')),3)
        vv=g.pop('boiler_deltas');g['median_boiler_minus_tank_c']=round(statistics.median(vv),3) if vv else None
        g['sensor_means']={k:round(statistics.mean(v),3) if v else None for k,v in g['sensor_means'].items()}
        result['groups'].append(g);result['windows']+=g['windows']
    if result['windows']:result['state']='observations_available'
    result['reason']='Noch keine zusammenhängenden Messfenster mit gültigem Speicherfühler, bestätigtem Lade-Vorlauf/-Rücklauf und ausgeschalteter Ladepumpe. Nicht zugeordnete Fühler bleiben ausschließlich im Verlauf.' if not result['windows'] else 'Messfenster nach Pumpenstatus, Zirkulationshahn, Entnahmeangabe und Speichertemperatur gruppiert. Keine unabhängigen kontrollierten Versuche.'
    return result
