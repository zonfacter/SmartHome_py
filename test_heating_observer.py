"""Observation, separate thermal models, and explicitly uncalibrated gas references."""
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from flask import Flask
from modules.gateway.heating import HeatingService,register_heating_routes,tado_number
from modules.gateway.heating_observer import HeatingObserver,fit_models,learn,observation,runtime_reference,thermal_pairs,merge_bucket


def item(value,quality='valid',stamp=1):return {'value':value,'quality':quality,'updated_at':stamp}


def fixture():
    return {'floors':{a:{'metrics':{'pump':item(False),'outside':item(5),'flow_actual':item(30)}} for a in ('eg','og')},
            'plant':{'dhw':item(50),'boiler':item(55),'dhw_pump':item(False),'burner':item(False),'burner_stage2':item(False)},
            'rooms':[{'id':'tado.0.test.Rooms.1','name':'Living','floor':'eg','type':'HEATING','temperature':20,
                      'setpoint':21,'humidity':45,'demand':0,'quality':{'temperature':'valid','setpoint':'valid','humidity':'valid','demand':'valid'},
                      'timestamp':1,'stale':False}],
            'connection':{'connected':True},'iobroker':{'connected':True,'tado_connected':True}}


def synthetic_records():
    rows=[];t=20
    for i in range(3*24*12+1):
        outside=4+4*math.sin(i/48);pump=i%24<12;source=35
        snapshot=fixture();snapshot['floors']['eg']['metrics'].update(pump=item(pump),outside=item(outside),flow_actual=item(source))
        snapshot['rooms'][0]['temperature']=t
        snapshot['rooms'][0]['demand']=100 if pump else 0
        rows.append({'ts':i*300,'data':observation(snapshot)})
        t+=(0.025*(outside-t)+0.04*(source-t)*pump)*300/3600
    return rows


class ObserverTests(unittest.TestCase):
    def test_numeric_source_quality_age_and_zero_demand(self):
        for value,expected in [(0,0),(50,50),(100,100)]:
            self.assertEqual(tado_number({'val':value,'ts':100000},0,100,now=101),(expected,'valid'))
        self.assertEqual(tado_number({'val':20,'ts':100000},0,100,now=1100),(None,'stale'))
        for bad in ({'val':True,'ts':100000},{'val':float('nan'),'ts':100000},{'val':20,'ts':100000,'q':64},{'val':20,'ts':200000}):
            self.assertEqual(tado_number(bad,0,100,now=101)[1],'error')

    def test_room_identity_quality_and_floor_remain_separate(self):
        snapshot=fixture();snapshot['rooms'].append({**snapshot['rooms'][0],'id':'tado.0.test.Rooms.2','floor':'og','temperature':24})
        data=observation(snapshot)
        self.assertEqual([r['temperature'] for r in data['rooms']],[20,24])
        self.assertEqual([r['floor'] for r in data['rooms']],['eg','og'])
        snapshot['iobroker']['tado_connected']=False
        self.assertTrue(all(r['quality']['temperature']=='stale' for r in observation(snapshot)['rooms']))

    def test_store_is_rate_limited_durable_and_does_not_backfill(self):
        with tempfile.TemporaryDirectory() as root:
            db=Path(root)/'data.db';observer=HeatingObserver(root,db,{'enabled':True})
            self.assertTrue(observer.record(fixture(),1000,False))
            self.assertFalse(observer.record(fixture(),1030,False))
            self.assertTrue(observer.record(fixture(),1060,False))
            restarted=HeatingObserver(root,db,{'enabled':True})
            self.assertEqual(restarted.status()['sample_count'],2)
            self.assertEqual(restarted.status()['mode'],'observe');self.assertFalse(restarted.status()['can_control'])

    def test_other_modes_are_rejected_and_disabled_records_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):HeatingObserver(root,Path(root)/'d.db',{'enabled':True,'mode':'auto'})
            observer=HeatingObserver(root,Path(root)/'off.db',{})
            self.assertFalse(observer.record(fixture()))
            self.assertFalse(observer.status()['can_control'])

    def test_reduced_buckets_preserve_internal_invalid_room_and_bus_values(self):
        a=observation(fixture());b=observation(fixture())
        a['rooms'][0]['quality']['temperature']='stale';a['floors']['eg']['pump']['q']='error'
        merged=merge_bucket([{'ts':1,'data':a},{'ts':60,'data':b}])
        self.assertIsNone(merged['data']['rooms'][0]['temperature'])
        self.assertNotEqual(merged['data']['floors']['eg']['pump']['q'],'valid')

    def test_floor_model_learns_on_synthetic_later_holdout_data(self):
        result=fit_models(synthetic_records())
        model=result['eg']['rooms'][0]
        self.assertEqual(model['state'],'validated',model)
        self.assertLess(model['validation_mae_c'],model['persistence_mae_c'])
        self.assertAlmostEqual(model['coefficients']['outside_delta'],0.025,delta=0.01)
        self.assertEqual(result['og']['state'],'collecting')
        self.assertEqual(result['dhw']['state'],'collecting')

    def test_ac_sensors_are_recorded_but_not_used_as_gas_room_models(self):
        records=synthetic_records()
        for row in records:row['data']['rooms'][0]['type']='AIR_CONDITIONING'
        self.assertEqual(fit_models(records)['eg']['rooms'][0]['state'],'record_only')

    def test_missing_stale_and_long_gaps_do_not_create_training_pairs(self):
        rows=synthetic_records()[:5]
        for row in rows:row['data']['rooms'][0]['quality']['temperature']='stale'
        self.assertEqual(thermal_pairs(rows,'eg','tado.0.test.Rooms.1'),[])
        rows=synthetic_records()[:5];rows[1]['ts']=1
        self.assertEqual(thermal_pairs(rows,'eg','tado.0.test.Rooms.1'),[])

    def test_insufficient_or_constant_data_never_claim_validated_learning(self):
        pairs=[{'ts':i*900,'x':[1,-15,0],'y':0,'hours':0.25,'active':False} for i in range(300)]
        self.assertEqual(learn(pairs,['drift','outside','heat'])['state'],'collecting')
        self.assertEqual(fit_models([])['dhw']['pairs'],0)

    def test_training_is_saved_and_restored_without_an_actuator(self):
        with tempfile.TemporaryDirectory() as root:
            observer=HeatingObserver(root,Path(root)/'data.db',{'enabled':True})
            observer.record(fixture(),int(time.time()),False);observer.train()
            self.assertEqual(set(observer.status()['models']),{'eg','og','dhw'})
            self.assertIsNotNone(observer.status()['trained_at'])

    def test_runtime_unions_stages_without_requiring_a_start_counter(self):
        samples=[{'ts':0,'anlage.burner':True,'anlage.burner_stage2':True},
                 {'ts':60,'anlage.burner':False,'anlage.burner_stage2':True},
                 {'ts':120,'anlage.burner':False,'anlage.burner_stage2':False}]
        reference={'rated_input_hi_kw':22.8,'rated_output_kw':20.8,'assumed_hi_kwh_per_nm3':10}
        r=runtime_reference(samples,1,3600,reference)
        self.assertEqual(r['relay_minutes'],2)
        self.assertEqual(r['stage1_minutes'],1);self.assertEqual(r['stage2_minutes'],2)
        self.assertAlmostEqual(r['rated_input_reference_kwh_hi'],0.76)
        self.assertAlmostEqual(r['gas_equivalent_nm3'],0.076)
        self.assertFalse(r['calibrated']);self.assertLess(r['coverage_percent'],4)

    def test_runtime_unknown_gaps_and_no_calorific_assumption_stay_unknown(self):
        for samples in ([],[{'ts':0},{'ts':60}],[{'ts':0,'anlage.burner':True,'anlage.burner_stage2':False},{'ts':400,'anlage.burner':True,'anlage.burner_stage2':False}]):
            r=runtime_reference(samples,1,3600,{})
            self.assertIsNone(r['relay_minutes']);self.assertIsNone(r['gas_equivalent_nm3'])

    def test_endpoints_are_read_only_and_do_not_make_hardware_calls(self):
        with tempfile.TemporaryDirectory() as root:
            app=Flask(__name__);service=register_heating_routes(SimpleNamespace(app=app),root)
            def forbidden(_):raise AssertionError('No hardware access allowed')
            service.fetch=forbidden;c=app.test_client()
            for path in ('/api/heating/observer','/api/heating/observer/history'):
                self.assertEqual(c.get(path).status_code,200)
                self.assertEqual(c.get(path+'?hours=999').status_code,400)
                self.assertEqual(c.post(path,json={}).status_code,405)
            for days in (1,7,30,90):
                self.assertEqual(c.get('/api/heating/observer/dhw-history?days='+str(days)).status_code,200)
            self.assertEqual(c.get('/api/heating/observer/dhw-history?days=999').status_code,400)
            self.assertEqual(c.get('/api/heating/observer/dhw-history?days=bad').status_code,400)
            self.assertEqual(c.post('/api/heating/observer/dhw-history').status_code,405)
            self.assertFalse(c.get('/api/heating/observer').json['can_control'])
            self.assertIsNone(service.thread)

    def test_dhw_history_joins_measured_legacy_and_observation_without_duplicates(self):
        with tempfile.TemporaryDirectory() as root:
            observer=HeatingObserver(root,Path(root)/'data.db',{'enabled':True})
            with closing(sqlite3.connect(observer.db_path)) as db,db:
                db.execute('CREATE TABLE heating_samples(ts INTEGER PRIMARY KEY,payload TEXT)')
                for ts,value in ((1000,42.015625),(1060,45.015625),(1120,99),(1180,99)):
                    db.execute('INSERT INTO heating_samples VALUES (?,?)',(ts,json.dumps({'anlage.dhw':value})))
                for ts,value,q in ((1120,50,'valid'),(1180,55,'valid'),(1240,60,'stale'),(1300,48,'valid'),(2000,40,'valid')):
                    db.execute('INSERT INTO heating_observations VALUES (?,?)',(ts,json.dumps({'plant':{'dhw':{'q':q,'v':value}}})))
            history=observer.dhw_history(1,now=2100)
            self.assertEqual(history['valid_samples'],6)
            self.assertEqual((history['minimum'],history['maximum']),(40,55))
            self.assertEqual(history['latest'],{'ts':2000,'temperature':40})
            self.assertTrue(all(s['temperature'] is None or s['minimum']<=s['temperature']<=s['maximum'] for s in history['samples']))
            self.assertTrue(history['samples'][-1]['break_before'])
            self.assertTrue(any(s['temperature'] is None or s['break_before'] for s in history['samples'][1:]))

    def test_dhw_history_bounds_response_and_preserves_short_temperature_peaks(self):
        with tempfile.TemporaryDirectory() as root:
            observer=HeatingObserver(root,Path(root)/'data.db',{'enabled':True})
            now=90*86400
            with closing(sqlite3.connect(observer.db_path)) as db,db:
                db.execute('CREATE TABLE heating_samples(ts INTEGER PRIMARY KEY,payload TEXT)')
                for i in range(8000):
                    value=65 if i==4001 else 40
                    db.execute('INSERT INTO heating_observations VALUES (?,?)',(now-i*900,json.dumps({'plant':{'dhw':{'q':'valid','v':value}}})))
            history=observer.dhw_history(90,now)
            self.assertLessEqual(len(history['samples']),720)
            self.assertEqual(history['maximum'],65)
            self.assertTrue(any(s['maximum']==65 and s['temperature']<65 for s in history['samples']))

    def test_enabled_observation_starts_collector_without_a_browser(self):
        with tempfile.TemporaryDirectory() as root:
            cfg=Path(root)/'config';cfg.mkdir();(cfg/'heating.json').write_text('{"enabled":true}')
            (cfg/'heating_observer.json').write_text('{"enabled":true,"mode":"observe"}')
            with patch.object(HeatingService,'start') as start:
                register_heating_routes(SimpleNamespace(app=Flask(__name__)),root)
                start.assert_called_once()

    def test_pump_history_preserves_switch_intervals_and_does_not_bridge_gaps(self):
        with tempfile.TemporaryDirectory() as root:
            observer=HeatingObserver(root,Path(root)/'data.db',{'enabled':True})
            for ts,pump in ((1000,False),(1060,False),(1120,True),(1180,True),(2000,False),(2060,False)):
                snapshot=fixture();snapshot['floors']['eg']['metrics']['pump']=item(pump)
                snapshot['plant']['dhw_pump']=item(True,'stale')
                observer.record(snapshot,ts,False)
            tracks={t['key']:t for t in observer.pump_history(1000,2060,2060)}
            eg=tracks['eg'];self.assertEqual(eg['events'],[{'from':1060,'to':1120,'state':True}])
            self.assertIs(eg['state'],False)
            self.assertEqual(sum(b['on_seconds'] for b in eg['buckets']),60)
            self.assertEqual(sum(b['off_seconds'] for b in eg['buckets']),120)
            self.assertEqual(sum(b['unknown_seconds'] for b in eg['buckets']),880)
            self.assertTrue(all(b['on_seconds']==b['off_seconds']==0 for b in tracks['dhw']['buckets']))
            self.assertIsNone(tracks['dhw']['state'])
            self.assertTrue(all(t['state'] is None for t in observer.pump_history(1000,2060,3000)))
            self.assertTrue(all(len(t['buckets'])<=720 for t in tracks.values()))

    def test_pump_history_rejects_numeric_boolean_and_clips_at_range_start(self):
        with tempfile.TemporaryDirectory() as root:
            observer=HeatingObserver(root,Path(root)/'data.db',{'enabled':True})
            for ts,value in ((1000,False),(1060,False),(1120,1),(1180,True)):
                snapshot=fixture();snapshot['floors']['eg']['metrics']['pump']=item(value)
                observer.record(snapshot,ts,False)
            eg=observer.pump_history(1030,1180,1180)[0]
            self.assertEqual(sum(b['off_seconds'] for b in eg['buckets']),30)
            self.assertEqual(eg['events'],[])


if __name__=='__main__':unittest.main()
