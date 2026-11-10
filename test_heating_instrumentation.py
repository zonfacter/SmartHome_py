"""External sensor, graph validation, local-only writes and inference boundaries."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,sqlite3,tempfile,unittest
from contextlib import closing
from flask import Flask
from modules.gateway.heating import register_heating_routes
from modules.gateway.heating_instrumentation import (Instrumentation,SetupError,default_channels,read_channel,
                                                     validate_config,validate_plan,loss_diagnosis)
NOW=1700000000
def state(v,stamp=NOW,**kw):return {'val':v,'ts':stamp*1000,'ack':True,'q':0,**kw}
def configured():
    c=default_channels()[0];c.update(state_id='mqtt.0.test.temp',timestamp_id='mqtt.0.test.measured',availability_id='mqtt.0.test.online');return c
def plan():return {'title':'Test','nodes':[{'id':'tank','type':'tank','label':'Speicher','x':100,'y':100},{'id':'s1','type':'sensor','label':'S1','x':300,'y':100,'sensor':'sensor_1'}],
                  'edges':[{'id':'pipe','from':{'node':'tank','port':'e'},'to':{'node':'s1','port':'w'},'medium':'hot'}]}
def series():
    # One complete ten-minute bucket, plus a second independent bucket.
    start=NOW//600*600
    return [{'ts':start+i*10,'channels':{c['key']:{'value':60 if c['key']=='sensor_1' else 50,'quality':'valid','measurement_ts':start+i*10,'state_id':'source.'+c['key'],'role':('charge_supply' if c['key']=='sensor_1' else 'charge_return' if c['key']=='sensor_2' else 'unknown')} for c in default_channels()},
             'context':{k:{'value':v,'quality':'valid','measurement_ts':start+i*10} for k,v in {'dhw':55-i*.01,'boiler':40,'dhw_pump':False,'eg_pump':True,'og_pump':True}.items()}}
            for i in range(120)]

class Instruments(unittest.TestCase):
    def test_common_boiler_return_is_not_storage_coil_return(self):
        config={'channels':default_channels()}
        config['channels'][0]['role']='boiler_supply'
        config['channels'][1]['role']='boiler_return'
        self.assertEqual(validate_config(config)['channels'][1]['role'],'boiler_return')
        rr=series()
        for row in rr:
            row['channels']['sensor_2']['role']='boiler_return'
        self.assertEqual(loss_diagnosis(rr,[],24)['windows'],0)

    def test_sensor_freshness_actual_time_and_no_zero_fallback(self):
        c=configured();states={c['state_id']:state(42),c['timestamp_id']:state(NOW),c['availability_id']:state(True)}
        self.assertEqual(read_channel(c,states,NOW)['value'],42)
        for value in (False,'42',float('nan'),float('inf'),126,-56):
            ss=deepcopy(states);ss[c['state_id']]=state(value)
            self.assertIsNone(read_channel(c,ss,NOW)['value'])
        ss=deepcopy(states);ss[c['timestamp_id']]=state(NOW-100)
        self.assertEqual(read_channel(c,ss,NOW)['quality'],'stale') # retained temperature with fresh receipt
        for online in (False,None,'true'):
            ss=deepcopy(states);ss[c['availability_id']]=state(online)
            self.assertIsNone(read_channel(c,ss,NOW)['value'])
        for fields in ({'ack':False},{'q':64},{'ts':(NOW+100)*1000},{'ts':0}):
            ss=deepcopy(states);ss[c['state_id']].update(fields)
            self.assertIsNone(read_channel(c,ss,NOW)['value'])

    def test_timestamp_units_timezone_and_bad_source(self):
        c=configured()
        for stamp in (NOW,NOW*1000,'2023-11-14T22:13:20Z','2023-11-14T23:13:20+01:00'):
            r=read_channel(c,{c['state_id']:state(50),c['timestamp_id']:state(stamp),c['availability_id']:state(True)},NOW)
            self.assertEqual(r['measurement_ts'],NOW);self.assertEqual(r['value'],50)
        for stamp in ('2023-11-14T22:13:20','not a date',False,NOW+100):
            self.assertIsNone(read_channel(c,{c['state_id']:state(50),c['timestamp_id']:state(stamp),c['availability_id']:state(True)},NOW)['value'])
        self.assertEqual(read_channel(default_channels()[0],{},NOW)['quality'],'unconfigured')

    def test_latched_mqtt_lwt_string_and_unknown_roles(self):
        c=configured();c['availability_value']='Connected'
        states={c['state_id']:state(45),c['timestamp_id']:state(NOW),c['availability_id']:state('Connected',NOW-86400)}
        self.assertEqual(read_channel(c,states,NOW)['value'],45)
        states[c['availability_id']]=state('Connection Lost')
        self.assertEqual(read_channel(c,states,NOW)['quality'],'offline')
        rr=series()
        for r in rr:
            for channel in r['channels'].values():channel['role']='unknown'
        self.assertEqual(loss_diagnosis(rr,[],24)['windows'],0)
        d={'channels':default_channels()}
        for c in d['channels'][:2]:c['role']='charge_supply'
        with self.assertRaises(SetupError):validate_config(d)

    def test_config_rejects_ambiguous_and_injected_mapping(self):
        c={'channels':default_channels()};self.assertEqual(len(validate_config(c)['channels']),7)
        for mutate in (lambda d:d['channels'].pop(),lambda d:d['channels'][0].update(max_age_seconds=True),
                       lambda d:d['channels'][0].update(state_id='mqtt.*'),lambda d:d['channels'][1].update(key='sensor_1')):
            d=deepcopy(c);mutate(d)
            with self.assertRaises(SetupError):validate_config(d)
        for channel in c['channels'][:2]:channel['state_id']='same.value'
        with self.assertRaises(SetupError):validate_config(c)

    def test_graph_validation_and_preservation_of_labels(self):
        p=validate_plan(plan());self.assertEqual(p['edges'][0]['points'],[])
        for mutate in (lambda d:d['nodes'].append(deepcopy(d['nodes'][0])),
                       lambda d:d['edges'][0]['to'].update(node='missing'),lambda d:d['nodes'][0].update(x=float('nan')),
                       lambda d:d['nodes'][0].update(type='script'),lambda d:d['nodes'][0].update(rotation=45),
                       lambda d:d['nodes'].append({'id':'s2','type':'sensor','sensor':'sensor_1','x':5,'y':5})):
            d=plan();mutate(d)
            with self.assertRaises(SetupError):validate_plan(d)
        p=plan();p['nodes'][0]['label']='<img src=x onerror=alert(1)>'
        self.assertEqual(validate_plan(p)['nodes'][0]['label'],p['nodes'][0]['label']) # plain text, escaped in frontend

    def test_persistence_concurrency_and_history_without_fabrication(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'data.db';i=Instrumentation(path,None,None,lambda:{})
            self.assertFalse(i.history(1,NOW)['samples']);self.assertEqual(i.snapshot(NOW)['configured'],0)
            self.assertEqual(i.save('plan',{'revision':0,'data':plan()})['revision'],1)
            with self.assertRaises(SetupError) as e:i.save('plan',{'revision':0,'data':plan()})
            self.assertEqual(e.exception.status,409)
            self.assertEqual(Instrumentation(path,None,None,lambda:{}).document('plan')['revision'],1)
            rr=series();rr[1]['channels']['sensor_1'].update(value=None,quality='stale')
            with closing(sqlite3.connect(path)) as db,db:db.executemany('INSERT INTO heating_sensor_samples VALUES (?,?)',[(r['ts'],json.dumps({k:v for k,v in r.items() if k!='ts'})) for r in rr])
            h=i.history(24,rr[-1]['ts']);self.assertLessEqual(len(h['samples']),721)
            self.assertTrue(any(s['channels']['sensor_1']['quality']=='gap' for s in h['samples']))
            self.assertTrue(any(s['channels']['sensor_1']['minimum'] is not None for s in h['samples']))

    def test_rpc_is_read_only_and_not_called_when_unconfigured(self):
        calls=[]
        class Bridge:
            def __init__(self,url):calls.append(('url',url))
            def connect(self):pass
            def call(self,method,key):
                calls.append((method,key));selftest.assertEqual(method,'getState')
                return state(45)
            def close(self):pass
        selftest=self
        with tempfile.TemporaryDirectory() as root:
            i=Instrumentation(Path(root)/'db','ws://test',Bridge,lambda:{})
            i.poll(NOW);self.assertEqual(calls,[]);self.assertFalse(i.history(1,NOW)['samples'])
            d={'channels':default_channels()};d['channels'][0]['state_id']='mqtt.0.test.temperature';i.save('sensors',{'revision':0,'data':d})
            i.poll(NOW);self.assertIn(('getState','mqtt.0.test.temperature'),calls)
            self.assertEqual(i.snapshot(NOW)['channels'][0]['value'],45)
            self.assertEqual(i.snapshot(NOW+100)['channels'][0]['quality'],'stale')

    def test_context_requires_fresh_lpb_evidence(self):
        sample={'connection':{'connected':True},'plant':{'dhw':{'quality':'valid','value':55,'updated_at':NOW-10}},'floors':{}}
        self.assertEqual(Instrumentation.context_data(sample,NOW)['dhw']['value'],55)
        self.assertIsNone(Instrumentation.context_data(sample,NOW+100)['dhw']['value'])
        sample['connection']['connected']=False
        self.assertIsNone(Instrumentation.context_data(sample,NOW)['dhw']['value'])

    def test_loss_groups_keep_strong_losses_and_unknown_draws(self):
        rr=series();result=loss_diagnosis(rr,[],24)
        self.assertEqual(result['windows'],2);self.assertEqual(result['groups'][0]['draw_status'],'unknown')
        self.assertGreater(result['groups'][0]['median_cooling_c_per_hour'],0)
        self.assertEqual(result['groups'][0]['median_charge_supply_minus_return_c'],10)
        self.assertIn('keine Durchflussmessung',result['limits'])
        notes=[{'kind':'circulation_closed','ts':rr[0]['ts']-60,'ended_at':None},{'kind':'no_draw','ts':rr[0]['ts']-1,'ended_at':rr[-1]['ts']+1}]
        result=loss_diagnosis(rr,notes,24)
        self.assertEqual(result['groups'][0]['draw_status'],'none_reported')
        self.assertEqual(result['groups'][0]['circulation'],'circulation_closed')

    def test_diagnosis_excludes_draws_tests_charging_changes_and_bad_coil(self):
        rr=series()
        for kind in ('draw','pump_test'):
            result=loss_diagnosis(rr,[{'kind':kind,'ts':rr[0]['ts']-1,'ended_at':rr[-1]['ts']+1}],24)
            self.assertEqual(result['windows'],0)
        for field in ('dhw_pump','og_pump'):
            r=deepcopy(rr)
            for n in (10,70):r[n]['context'][field]['value']=True if field=='dhw_pump' else False
            self.assertEqual(loss_diagnosis(r,[],24)['windows'],0)
        r=deepcopy(rr)
        for n in (10,70):r[n]['channels']['sensor_1']['quality']='stale'
        self.assertEqual(loss_diagnosis(r,[],24)['windows'],0)
        r=deepcopy(rr)
        for n in (10,70):r[n]['channels']['sensor_1']['state_id']='different.source'
        self.assertEqual(loss_diagnosis(r,[],24)['windows'],0)

    def test_local_only_setup_routes_and_notes(self):
        with tempfile.TemporaryDirectory() as root:
            app=Flask(__name__,template_folder=str(Path(__file__).parent/'web/templates'))
            s=register_heating_routes(SimpleNamespace(app=app),root);s.fetch=lambda _:self.fail('No hardware access')
            client=app.test_client();headers={'X-Heating-Setup':'1'}
            self.assertEqual(client.get('/heizung/anlagenplan').status_code,200)
            self.assertIn(b'Anlagenplan',client.get('/heizung/lernen').data)
            payload={'revision':0,'data':plan()}
            self.assertEqual(client.put('/api/heating/piping-plan',json=payload).status_code,403)
            self.assertEqual(client.put('/api/heating/piping-plan',json=payload,headers={**headers,'Origin':'http://elsewhere'}).status_code,403)
            self.assertEqual(client.put('/api/heating/piping-plan',json=payload,headers=headers).status_code,200)
            self.assertEqual(client.put('/api/heating/piping-plan',json=payload,headers=headers).status_code,409)
            for url in ('/api/heating/instrumentation','/api/heating/instrumentation/history','/api/heating/instrumentation/diagnosis'):
                self.assertEqual(client.get(url).status_code,200)
            self.assertEqual(client.get('/api/heating/instrumentation/history?hours=999999').status_code,400)
            note={'kind':'draw','ts':NOW,'ended_at':NOW+600,'note':'User report'}
            self.assertEqual(client.post('/api/heating/instrumentation/notes',json=note,headers=headers).status_code,200)
            self.assertEqual(s.instrumentation.notes()[0]['source'],'user_report')
            s.stop()

if __name__=='__main__':unittest.main()
