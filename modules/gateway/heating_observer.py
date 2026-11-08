"""Local recording and thermal response learning. No bus, network or actuator API."""
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import threading
import time

VERSION = 1
FLOOR_KEYS = ('pump','mode','flow_actual','flow_setpoint','room_setpoint','outside','outside_composite',
              'nominal','reduced','curve','parallel','flow_min','flow_max','room_influence','adaptation','quick_setback')
PLANT_KEYS = ('boiler','dhw','dhw_setpoint','dhw_pump','burner','burner_stage2','burner_hours','starts')


def numeric(value):
    return type(value) in (int,float) and math.isfinite(value)


def measured(metrics, key):
    item=metrics.get(key,{})
    return item.get('v') if item.get('q')=='valid' else None


def compact(metrics, keys):
    result={}
    for key in keys:
        item=metrics.get(key,{})
        value=item.get('value')
        if type(value) is float and not math.isfinite(value):value=None
        result[key]={'v':value,'q':item.get('quality','pending'),'ts':item.get('updated_at')}
    return result


def observation(snapshot):
    rooms=[]
    connected=snapshot.get('iobroker',{}).get('connected',False) and snapshot.get('iobroker',{}).get('tado_connected',False)
    for room in snapshot.get('rooms',[]):
        quality=dict(room.get('quality',{}))
        for key in ('temperature','setpoint','humidity','demand'):
            quality.setdefault(key,'valid' if numeric(room.get(key)) else 'unavailable')
            if not connected or room.get('stale'):quality[key]='stale'
        rooms.append({'id':room['id'],'name':room['name'],'floor':room.get('floor','unassigned'),
                      'type':room.get('type'),'temperature':room.get('temperature'),
                      'setpoint':room.get('setpoint'),'humidity':room.get('humidity'),'demand':room.get('demand'),
                      'power':room.get('power'),'ac_power':room.get('ac_power'),'quality':quality,'timestamps':room.get('timestamps',{}),
                      'timestamp':room.get('timestamp')})
    result={'schema':VERSION,'floors':{area:compact(snapshot['floors'][area]['metrics'],FLOOR_KEYS) for area in ('eg','og')},
            'plant':compact(snapshot['plant'],PLANT_KEYS),'rooms':rooms,
            'sources':{'lpb_connected':bool(snapshot.get('connection',{}).get('connected')),'tado_connected':bool(connected)}}
    if not result['sources']['lpb_connected']:
        for metrics in [result['plant'],*result['floors'].values()]:
            for item in metrics.values():
                if item['q']=='valid':item['q']='stale'
    return result


def ridge_fit(rows):
    """Small standardized ridge regression with a pivoted linear solve."""
    x=[r['x'] for r in rows];y=[r['y'] for r in rows];n=len(rows);p=len(x[0])
    means=[0.0]+[sum(row[j] for row in x)/n for j in range(1,p)]
    scales=[1.0]+[max(1e-6,math.sqrt(sum((row[j]-means[j])**2 for row in x)/n)) for j in range(1,p)]
    normalized=[[1.0]+[(row[j]-means[j])/scales[j] for j in range(1,p)] for row in x]
    matrix=[[sum(row[i]*row[j] for row in normalized)+(0.1 if i==j and i else 0.0) for j in range(p)]
            +[sum(row[i]*target for row,target in zip(normalized,y))] for i in range(p)]
    for i in range(p):
        pivot=max(range(i,p),key=lambda k:abs(matrix[k][i]))
        matrix[i],matrix[pivot]=matrix[pivot],matrix[i]
        if abs(matrix[i][i])<1e-10:raise ValueError('singular training matrix')
        factor=matrix[i][i];matrix[i]=[v/factor for v in matrix[i]]
        for k in range(p):
            if k==i:continue
            factor=matrix[k][i];matrix[k]=[a-factor*b for a,b in zip(matrix[k],matrix[i])]
    weights=[matrix[i][-1]/scales[i] for i in range(p)]
    weights[0]=matrix[0][-1]-sum(weights[j]*means[j] for j in range(1,p))
    return weights


def learn(pairs, names):
    result={'state':'collecting','pairs':len(pairs),'required_pairs':48,'required_days':3,
            'algorithm':'ridge_thermal_response_v1','validation_split':'last_20_percent_chronological',
            'features':names,'reason':'Noch nicht genügend unterschiedliche, gültige Beobachtungen.'}
    if not pairs:return result
    days=len({int(r['ts']//86400) for r in pairs})
    result.update(days=days,span_hours=round((pairs[-1]['ts']-pairs[0]['ts'])/3600,1),
                  heated_pairs=sum(bool(r['active']) for r in pairs),cooling_pairs=sum(not r['active'] for r in pairs))
    if len(pairs)<48 or days<3 or pairs[-1]['ts']-pairs[0]['ts']<48*3600:return result
    if sum(r['active'] for r in pairs)<6 or sum(not r['active'] for r in pairs)<6:
        result['reason']='Es fehlen Heiz-/Ladephasen oder Abkühlphasen.';return result
    if any(max(r['x'][j] for r in pairs)-min(r['x'][j] for r in pairs)<1 for j in (1,2)):
        result['reason']='Die Eingangsgrößen ändern sich noch zu wenig.';return result
    # The final 20% are strictly later observations, never a shuffled validation set.
    split=int(len(pairs)*0.8);train,test=pairs[:split],pairs[split:]
    weights=ridge_fit(train)
    errors=[abs((sum(a*b for a,b in zip(weights,r['x']))-r['y'])*r['hours']) for r in test]
    baseline=sum(abs(r['y']*r['hours']) for r in test)/len(test)
    mae=sum(errors)/len(errors)
    result.update(validation_pairs=len(test),validation_mae_c=round(mae,4),persistence_mae_c=round(baseline,4))
    if weights[1]<0 or weights[2]<0 or not all(math.isfinite(w) for w in weights):
        result.update(state='not_validated',reason='Gelerntes Verhalten ist physikalisch noch nicht plausibel.');return result
    if baseline<0.01 or mae>=baseline:
        result.update(state='not_validated',reason='Auf späteren Daten noch kein Vorteil gegenüber unveränderter Temperatur.');return result
    final=ridge_fit(pairs)
    if final[1]<0 or final[2]<0:
        result.update(state='not_validated',reason='Gesamtmodell ist noch nicht plausibel.');return result
    result.update(state='validated',reason='Temperaturentwicklung auf späteren Beobachtungen besser als die Vergleichsbasis.',
                  coefficients={name:round(w,7) for name,w in zip(names,final)},
                  prediction_scope='Beobachtete Temperaturreaktion; keine Stellbefehle, keine Einspargarantie.')
    return result


def thermal_pairs(records, area, room_id=None):
    """Nonoverlapping 15–30 minute windows; exclude gaps and invalid endpoints."""
    pairs=[];start=0
    def temperature(row):
        if area=='dhw':return measured(row['data']['plant'],'dhw')
        room=next((r for r in row['data']['rooms'] if r['id']==room_id),None)
        return room.get('temperature') if room and room['quality'].get('temperature')=='valid' else None
    while start<len(records)-1:
        end=start+1
        while end<len(records) and records[end]['ts']-records[start]['ts']<900:end+=1
        if end==len(records):break
        group=records[start:end+1];a,b=group[0],group[-1];start=end
        seconds=b['ts']-a['ts']
        if seconds>1800 or any(y['ts']-x['ts']>420 for x,y in zip(group,group[1:])):continue
        temps=[temperature(r) for r in group]
        if not all(numeric(t) for t in temps):continue
        t=temps[0];hours=seconds/3600
        if abs(temps[-1]-t)>10:continue
        weather=[];heat=[];states=[]
        for row in group[:-1]:
            data=row['data']
            if area=='dhw':
                source=measured(data['plant'],'boiler');pump=measured(data['plant'],'dhw_pump')
                weather.append(20-t)  # ambient temperature is an explicit proxy, not a basement sensor
            else:
                m=data['floors'][area];outside=measured(m,'outside');pump=measured(m,'pump')
                source=measured(m,'flow_actual') if area=='eg' else measured(data['plant'],'boiler')
                weather.append(outside-t if numeric(outside) else None)
            demand=1
            if area!='dhw':
                room=next((r for r in data['rooms'] if r['id']==room_id),{})
                demand=room.get('demand') if room.get('quality',{}).get('demand')=='valid' else None
                demand=demand/100 if numeric(demand) else None
            heat.append(max(0,source-t)*demand if pump is True and numeric(source) and numeric(demand) else 0 if pump is False and numeric(demand) else None)
            states.append(pump if area=='dhw' else pump and numeric(demand) and demand>0)
        if not all(numeric(v) for v in weather+heat) or any(type(s) is not bool for s in states):continue
        # A large unexplained tank drop can be a draw-off; do not call it standing loss.
        if area=='dhw' and not any(states) and temps[-1]-t < -0.5:continue
        pairs.append({'ts':b['ts'],'x':[1,sum(weather)/len(weather),sum(heat)/len(heat)],
                      'y':(temps[-1]-t)/hours,'hours':hours,'active':any(states)})
    return pairs


def fit_models(records,tank_litres=None):
    models={}
    latest=records[-1]['data'] if records else {'rooms':[]}
    for area in ('eg','og'):
        rooms=[]
        for room in latest['rooms']:
            if room.get('floor')!=area:continue
            if room.get('type')!='HEATING':
                rooms.append({'id':room['id'],'name':room['name'],'state':'record_only',
                              'reason':'Klima-/unbekannter Gerätetyp: nur Aufzeichnung, kein Gas-Heizmodell.'});continue
            pairs=thermal_pairs(records,area,room['id'])
            rooms.append({'id':room['id'],'name':room['name'],**learn(pairs,['drift_c_per_h','outside_delta','heat_proxy'])})
        eligible=[r for r in rooms if r['state']!='record_only'];validated=sum(r['state']=='validated' for r in eligible)
        group_state='validated' if eligible and validated==len(eligible) else 'partly_validated' if validated else 'collecting'
        models[area]={'state':group_state,'rooms':rooms,
                      'input_note':'EG: Vorlauf; OG: Kesseltemperatur als Versorgungsproxy, jeweils mit Q1 und Tado-Heizbedarf gewichtet. Kein gemessener Wärmestrom; Fremdwärme kann das Ergebnis beeinflussen.'}
    models['dhw']={**learn(thermal_pairs(records,'dhw'),['drift_c_per_h','ambient_proxy_delta','charge_proxy']),
                   'input_note':'Speicherfühler und Q3; angenommene Umgebung 20 °C, keine Zapfmengenmessung. Keine hygienische Bewertung.',
                   'tank_litres':tank_litres}
    return models


def runtime_reference(samples,hours,now,reference,max_gap=180):
    """Sampled relay time, independent from the sometimes delayed start counter."""
    seconds=coverage=stage1=stage2=0
    def state(row):
        a,b=row.get('anlage.burner'),row.get('anlage.burner_stage2')
        return (a,b) if type(a) is bool and type(b) is bool else None
    for a,b in zip(samples,samples[1:]):
        dt=b['ts']-a['ts'];sa,sb=state(a),state(b)
        if a['ts']<now-hours*3600 or b['ts']>now or not 0<dt<=max_gap or sa is None or sb is None:continue
        coverage+=dt
        if any(sa):seconds+=dt
        if sa[0]:stage1+=dt
        if sa[1]:stage2+=dt
    active_hours=seconds/3600
    load=reference.get('rated_input_hi_kw');output=reference.get('rated_output_kw');hi=reference.get('assumed_hi_kwh_per_nm3')
    input_energy=active_hours*load if numeric(load) and load>0 and coverage else None
    return {'hours':hours,'coverage_seconds':coverage,'coverage_percent':round(coverage/(hours*36),1),
            'relay_minutes':round(seconds/60,2) if coverage else None,
            'stage1_minutes':round(stage1/60,2) if coverage else None,'stage2_minutes':round(stage2/60,2) if coverage else None,
            'rated_input_reference_kwh_hi':round(input_energy,3) if input_energy is not None else None,
            'rated_output_reference_kwh':round(active_hours*output,3) if numeric(output) and output>0 and coverage else None,
            'gas_equivalent_nm3':round(input_energy/hi,3) if input_energy is not None and numeric(hi) and hi>0 else None,
            'reference':reference,'calibrated':False,
            'limitations':'Abgetastete K4/K5-Kontakte, keine Flammenmessung. Vereinigung beider Stufen, nicht doppelt gezählt. '
                'Rechnung nimmt während jeder erfassten Relaisminute die volle Nennbelastung an; tatsächliche Stufenleistung und Gasmenge sind unbestätigt. '
                'Hi/Heizwertbasis und angenommener Heizwert in kWh/Nm³; kein Gaszählerwert und keine Abrechnungsenergie auf Brennwertbasis. '
                'Abgasverlust ist kein Jahresnutzungsgrad. Datenlücken sind nicht auf das ganze Zeitfenster hochgerechnet.'}


def merge_bucket(records):
    """Keep the last value, but preserve any invalid input within a reduced bucket."""
    entries=[r['data'] for r in records];data=entries[-1]
    if len(records)>1:
        for room in data['rooms']:
            source=[next((r for r in e['rooms'] if r['id']==room['id']),{}) for e in entries]
            for field in ('temperature','setpoint','humidity','demand'):
                if any(r.get('quality',{}).get(field)!='valid' for r in source):
                    room[field]=None;room['quality'][field]='unavailable'
        for area in ('plant','eg','og'):
            metrics=data['plant'] if area=='plant' else data['floors'][area]
            source=[e['plant'] if area=='plant' else e['floors'][area] for e in entries]
            for key in metrics:
                if any(m.get(key,{}).get('q')!='valid' for m in source):metrics[key].update(v=None,q='unavailable')
    return {'ts':records[-1]['ts'],'data':data}


class HeatingObserver:
    def __init__(self,root,db_path,config=None):
        path=Path(root)/'config/heating_observer.json'
        self.config=config if config is not None else json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        if self.config.get('mode','observe')!='observe':raise ValueError('Only observation mode is supported')
        self.enabled=self.config.get('enabled',False) is True
        self.db_path=Path(db_path);self.lock=threading.Lock();self.last_record=0;self.last_fit=0;self.worker=None
        self.error=None
        if self.enabled:
            with closing(sqlite3.connect(self.db_path,timeout=5)) as db,db:
                db.execute('CREATE TABLE IF NOT EXISTS heating_observations(ts INTEGER PRIMARY KEY,payload TEXT NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS heating_learning(area TEXT PRIMARY KEY,ts INTEGER NOT NULL,payload TEXT NOT NULL)')
                row=db.execute('SELECT MAX(ts) FROM heating_observations').fetchone();self.last_record=row[0] or 0
                row=db.execute('SELECT MAX(ts) FROM heating_learning').fetchone();self.last_fit=row[0] or 0

    def record(self,snapshot,now=None,schedule_training=True):
        if not self.enabled:return False
        now=int(time.time() if now is None else now)
        if now-self.last_record<60:return False
        data=observation(snapshot)
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db,db:
            db.execute('INSERT OR IGNORE INTO heating_observations VALUES (?,?)',(now,json.dumps(data,allow_nan=False)))
            db.execute('DELETE FROM heating_observations WHERE ts<?',(now-90*86400,))
        self.last_record=now
        if schedule_training and now-self.last_fit>=3600 and (not self.worker or not self.worker.is_alive()):
            self.worker=threading.Thread(target=self.train,name='heating-learning',daemon=True);self.worker.start()
        return True

    def train(self,now=None):
        if not self.enabled or not self.lock.acquire(blocking=False):return
        now=int(time.time() if now is None else now)
        try:
            cursor=now-28*86400-1;records=[];bucket=[]
            while True:
                # Short read transactions keep recording responsive during training.
                with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
                    rows=db.execute('SELECT ts,payload FROM heating_observations WHERE ts>? AND ts<=? ORDER BY ts LIMIT 500',(cursor,now)).fetchall()
                if not rows:break
                for ts,payload in rows:
                    if bucket and ts//300!=bucket[0]['ts']//300:
                        records.append(merge_bucket(bucket));bucket=[]
                    bucket.append({'ts':ts,'data':json.loads(payload)})
                cursor=rows[-1][0]
            if bucket:records.append(merge_bucket(bucket))
            models=fit_models(records,self.config.get('plant_reference',{}).get('dhw_tank_litres'))
            with closing(sqlite3.connect(self.db_path,timeout=5)) as db,db:
                for area,model in models.items():
                    db.execute('INSERT OR REPLACE INTO heating_learning VALUES (?,?,?)',(area,now,json.dumps(model,allow_nan=False)))
            self.last_fit=now;self.error=None
        except Exception as error:
            self.error=type(error).__name__;self.last_fit=now
        finally:self.lock.release()

    def status(self):
        result={'enabled':self.enabled,'mode':'observe','can_control':False,'retention_days':90,
                'model_window_days':28,'training_interval_seconds':3600,'error':self.error,
                'models':fit_models([],self.config.get('plant_reference',{}).get('dhw_tank_litres')),'assumptions':self.config.get('plant_reference',{})}
        if not self.enabled:return result
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            count,first,last=db.execute('SELECT COUNT(*),MIN(ts),MAX(ts) FROM heating_observations').fetchone()
            models=db.execute('SELECT area,ts,payload FROM heating_learning').fetchall()
            latest=db.execute('SELECT payload FROM heating_observations ORDER BY ts DESC LIMIT 1').fetchone()
        result.update(sample_count=count,first_sample=first,last_sample=last,span_hours=round((last-first)/3600,2) if count else 0,
                      trained_at=max((r[1] for r in models),default=None))
        for area,ts,payload in models:result['models'][area]=json.loads(payload)
        result['rooms']=json.loads(latest[0])['rooms'] if latest else []
        return result

    def history(self,hours):
        if not self.enabled:return []
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            rows=db.execute('SELECT ts,payload FROM heating_observations WHERE ts>=? ORDER BY ts',(int(time.time())-hours*3600,)).fetchall()
        width=max(1,(len(rows)+359)//360)
        result=[]
        for i in range(0,len(rows),width):
            merged=merge_bucket([{'ts':ts,'data':json.loads(payload)} for ts,payload in rows[i:i+width]])
            result.append({'ts':merged['ts'],**merged['data']})
        return result

    def energy_reference(self,hours):
        now=time.time()
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            rows=db.execute('SELECT ts,payload FROM heating_samples WHERE ts>=? ORDER BY ts',(int(now-hours*3600),)).fetchall()
        return runtime_reference([{'ts':ts,**json.loads(data)} for ts,data in rows],hours,now,
                                 self.config.get('plant_reference',{}))

    def dhw_history(self,days,now=None):
        """Measured tank temperatures only; bounded buckets retain extrema and gaps."""
        now=int(time.time() if now is None else now);cutoff=now-days*86400
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            if self.enabled:
                first=db.execute('SELECT MIN(ts) FROM heating_observations').fetchone()[0]
                rows=db.execute("SELECT ts,CASE WHEN json_extract(payload,'$.plant.dhw.q')='valid' THEN json_extract(payload,'$.plant.dhw.v') END FROM heating_observations WHERE ts>=? AND ts<=? ORDER BY ts",(cutoff,now)).fetchall()
            else:first=None;rows=[]
            # Older measured plant history is available before room observation began.
            legacy=db.execute("SELECT ts,json_extract(payload,'$.\"anlage.dhw\"') FROM heating_samples WHERE ts>=? AND ts<? ORDER BY ts",(cutoff,min(first,now+1) if first is not None else now+1)).fetchall()
        rows=legacy+rows;origin=rows[0][0] if rows else cutoff
        seconds=max(1,math.ceil((now-origin+1)/720));buckets={};previous=None;values=[]
        for ts,value in rows:
            if ts>now:continue
            index=min(719,(ts-origin)//seconds)
            bucket=buckets.setdefault(index,{'ts':ts,'from':ts,'to':ts,'values':[],'break_before':False})
            bucket['ts']=bucket['to']=ts
            valid=numeric(value) and 0<=value<=120
            if previous is None or ts-previous>180 or not valid:bucket['break_before']=True
            if valid:bucket['values'].append(value);values.append(value)
            previous=ts if valid else None
        samples=[]
        for bucket in buckets.values():
            measured_values=bucket.pop('values')
            bucket.update(temperature=sum(measured_values)/len(measured_values) if measured_values else None,
                          minimum=min(measured_values) if measured_values else None,maximum=max(measured_values) if measured_values else None,count=len(measured_values))
            samples.append(bucket)
        last=rows[-1] if rows else None
        latest={'ts':last[0],'temperature':last[1]} if last and numeric(last[1]) and 0<=last[1]<=120 else None
        return {'days':days,'retention_days':90,'bucket_seconds':seconds,'samples':samples,
                'first_sample':rows[0][0] if rows else None,'last_sample':last[0] if last else None,
                'minimum':min(values) if values else None,'maximum':max(values) if values else None,'latest':latest,
                'valid_samples':len(values),'source':'Gemessener Speicherfühler; ältere Anlagenhistorie bis 30 Tage, Beobachtungsarchiv bis 90 Tage. Keine rückwirkend erzeugten Werte.'}

    def energy_reference_between(self,start,end):
        with closing(sqlite3.connect(self.db_path,timeout=5)) as db:
            rows=db.execute("SELECT ts,json_extract(payload,'$.\"anlage.burner\"'),json_type(payload,'$.\"anlage.burner\"'),json_extract(payload,'$.\"anlage.burner_stage2\"'),json_type(payload,'$.\"anlage.burner_stage2\"') FROM heating_samples WHERE ts>=? AND ts<=? ORDER BY ts",(start,end)).fetchall()
        samples=[{'ts':ts,'anlage.burner':bool(a) if qa in ('true','false') else None,
                  'anlage.burner_stage2':bool(b) if qb in ('true','false') else None} for ts,a,qa,b,qb in rows]
        return runtime_reference(samples,(end-start)/3600,end,self.config.get('plant_reference',{}))
