"""Window evidence, ventilation filtering and read-only integration regressions."""
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from modules.gateway.heating import HeatingService
from modules.gateway.heating_observer import HeatingObserver, fit_models, merge_bucket, observation, thermal_pairs
from modules.gateway.heating_windows import WINDOW_POLICY, exclusion, fresh, observe, refresh
from test_heating_observer import fixture, synthetic_records


NOW = 200000


def state(value, stamp=NOW, changed=NOW-1800, **fields):
    return {'val': value, 'ts': stamp*1000, 'lc': changed*1000, 'q': 0, 'ack': True, **fields}


CONTACT = {'id': 'zigbee.0.test.opened', 'open_value': True, 'availability_id': 'zigbee.0.test.available'}


def contact(opened=False, **kwargs):
    return observe({}, [CONTACT], {CONTACT['id']:state(opened, **kwargs), CONTACT['availability_id']:state(True)}, NOW)


class WindowEvidenceTests(unittest.TestCase):
    def test_contact_polarity_and_all_contacts_must_be_closed(self):
        self.assertIs(contact()['training_allowed'], True)
        self.assertEqual(contact(True)['state'], 'open')
        inverted = {'id':'zigbee.0.test.contact','open_value':False}
        self.assertEqual(observe({}, [inverted], {inverted['id']:state(True)}, NOW)['state'], 'closed')
        self.assertEqual(observe({}, [inverted], {inverted['id']:state(False)}, NOW)['state'], 'open')
        sources = {CONTACT['id']:state(False), CONTACT['availability_id']:state(True)}
        self.assertEqual(observe({}, [CONTACT, inverted], sources, NOW)['state'], 'unknown')
        sources[CONTACT['id']] = state(True)
        self.assertEqual(observe({}, [CONTACT, inverted], sources, NOW)['state'], 'open')

    def test_unknown_old_bad_pending_and_offline_are_never_closed(self):
        for invalid in [state(None),state('false'),state(False, stamp=1),state(False, stamp=NOW+100),
                        state(False,q=64),state(False,ack=False),state(False,ts=float('nan'))]:
            sources={CONTACT['id']:invalid,CONTACT['availability_id']:state(True)}
            result=observe({},[CONTACT],sources,NOW)
            self.assertEqual(result['state'],'unknown',invalid)
            self.assertFalse(result['training_allowed'])
        result=observe({},[CONTACT],{CONTACT['id']:state(False),CONTACT['availability_id']:state(False)},NOW)
        self.assertEqual(result['state'],'unknown')
        for config in [{'id':'x'}, {'id':'x','open_value':'true'}, {'id':'x','open_value':True,'max_age_seconds':float('inf')},
                       {'id':'x','open_value':True,'availability_id':[]}]:
            self.assertFalse(observe({},[config],{'x':state(False)},NOW)['training_allowed'])

    def test_tado_negative_null_and_expired_pause_never_confirm_closure(self):
        for detected in [False,None,'false']:
            result=observe({'openWindowDetected':state(detected)},None,{},NOW)
            self.assertEqual(result['state'],'unknown')
            self.assertFalse(result['training_allowed'])
        stamp=lambda value:datetime.fromtimestamp(value,timezone.utc).isoformat()
        tado={'openWindow.detectedTime':state(stamp(NOW-120)),
              'openWindow.expiry':state(stamp(NOW+60))}
        self.assertEqual(observe(tado,None,{},NOW)['state'],'open')
        # Both re-reading and ageing the pause must return unknown, never closed.
        self.assertEqual(observe(tado,None,{},NOW+61)['state'],'unknown')
        self.assertEqual(refresh(observe(tado,None,{},NOW),NOW+61)['state'],'unknown')
        self.assertEqual(observe({'openWindowDetected':state(True)},None,{},NOW)['state'],'open')
        self.assertEqual(observe({'openWindow.remainingTimeInSeconds':state(60)},None,{},NOW)['state'],'open')

    def test_recovery_and_staleness_are_evaluated_after_collection(self):
        result=contact(False,changed=NOW-30)
        self.assertEqual(result['state'],'closed')
        self.assertEqual(exclusion(result,NOW),'recovery')
        self.assertIsNone(exclusion(result,NOW+900))
        self.assertEqual(exclusion(result,NOW+86401),'unknown')
        self.assertEqual(refresh(contact(),NOW,False)['state'],'unknown')

    def test_tado_positive_overrules_closed_contacts_without_claiming_a_contact(self):
        result=observe({'openWindowDetected':state(True)},[CONTACT],
                       {CONTACT['id']:state(False),CONTACT['availability_id']:state(True)},NOW)
        self.assertEqual((result['state'],result['source']),('open','tado_detection'))
        self.assertFalse(result['training_allowed'])

    def test_window_collection_reads_sources_and_only_publishes_heating_telemetry(self):
        now=time.time();prefix='tado.0.example.Rooms.1'
        states={prefix+'.'+k:state(v,stamp=now,changed=now-1800) for k,v in {
            'name':'Example room','type':'HEATING','sensorDataPoints.insideTemperature.celsius':20,
            'sensorDataPoints.humidity.percentage':45,'setting.temperature.celsius':21,
            'activityDataPoints.heatingPower.percentage':50,'setting.power':'ON','openWindowDetected':False}.items()}
        states.update({'tado.0.info.connection':state(True,stamp=now),
                       'system.adapter.tado.0.alive':state(True,stamp=now),
                       CONTACT['id']:state(True,stamp=now),CONTACT['availability_id']:state(True,stamp=now)})
        writes=[]
        class Bridge:
            PREFIX='0_userdata.0.heizung'
            def __init__(self,_):pass
            def connect(self):return self
            def close(self):pass
            def call(self,method,*args):
                if method=='getStates':return {k:v for k,v in states.items() if fnmatchcase(k,args[0])}
                if method=='getState':return states.get(args[0])
                if method=='getObject':return None
                if method in ('setState','setObject'):writes.append((method,*args));return None
                raise AssertionError(method)
        with tempfile.TemporaryDirectory() as root:
            service=HeatingService(root,config={'iobroker_url':'ws://example.invalid','room_floors':{prefix:'eg'},'window_contacts':{prefix:[CONTACT]}})
            with patch('modules.gateway.heating.IoBroker',Bridge):service._sync_iobroker()
            self.assertTrue(service.io_status['connected'])
            self.assertEqual(service.snapshot()['rooms'][0]['window']['state'],'open')
            recorded=observation(service.snapshot())
            self.assertEqual(recorded['schema'],2)
            self.assertEqual(recorded['rooms'][0]['window']['state'],'open')
        self.assertTrue(writes)
        self.assertTrue(all(args[1].startswith('0_userdata.0.heizung.') for args in writes))
        self.assertTrue(all(args[2].get('ack') is True for args in writes if args[0]=='setState'))


class WindowTrainingTests(unittest.TestCase):
    def test_open_unknown_and_stale_endpoints_are_excluded(self):
        baseline=synthetic_records()[:4]
        self.assertEqual(len(thermal_pairs(baseline,'eg','tado.0.test.Rooms.1')),1)
        for endpoint in [0,1,3]:
            for bad in [None,{'state':'open','quality':'valid','source':'contact','valid_until':1e12},
                        {'state':'closed','quality':'stale','source':'contact','valid_until':1e12}]:
                rows=deepcopy(baseline);rows[endpoint]['data']['rooms'][0]['window']=bad
                stats={}
                self.assertEqual(thermal_pairs(rows,'eg','tado.0.test.Rooms.1',stats),[])
                self.assertEqual(stats['candidate_windows'],1)

    def test_short_opening_survives_bucket_and_does_not_mutate_last_sample(self):
        rows=deepcopy(synthetic_records()[:4])
        minute=[deepcopy(rows[0]) for _ in range(3)]
        for i,r in enumerate(minute):r['ts']=i*60
        minute[1]['data']['rooms'][0]['window'].update(state='open',training_allowed=False)
        merged=merge_bucket(minute)
        self.assertIn('open',merged['data']['rooms'][0]['window']['excluded_in_bucket'])
        self.assertTrue(minute[-1]['data']['rooms'][0]['window']['training_allowed'])
        self.assertNotIn('excluded_in_bucket',minute[-1]['data']['rooms'][0]['window'])
        rows=[merged,*rows[1:],deepcopy(rows[-1])];rows[-1]['ts']=1200
        self.assertEqual(thermal_pairs(rows,'eg','tado.0.test.Rooms.1'),[])

    def test_legacy_history_is_retained_but_no_longer_used_for_room_learning(self):
        rows=synthetic_records()[:13]
        for row in rows:row['data']['rooms'][0].pop('window')
        result=fit_models(rows)['eg']
        self.assertEqual(result['window_policy'],WINDOW_POLICY)
        self.assertEqual(result['rooms'][0]['pairs'],0)
        self.assertGreater(result['rooms'][0]['window_filter']['excluded_unknown'],0)

    def test_window_filter_does_not_change_dhw_training_pairs(self):
        rows=synthetic_records()[:4]
        before=thermal_pairs(rows,'dhw')
        self.assertEqual(len(before),1)
        for row in rows:row['data']['rooms'][0]['window'].update(state='open',training_allowed=False)
        self.assertEqual(thermal_pairs(rows,'dhw'),before)

    def test_cached_pre_filter_room_models_are_invalidated_without_deleting_data(self):
        with tempfile.TemporaryDirectory() as root:
            db=Path(root)/'data.db';observer=HeatingObserver(root,db,{'enabled':True})
            observer.record(fixture(),1000,False)
            with closing(sqlite3.connect(db)) as c,c:
                for area in ('eg','dhw'):
                    c.execute('INSERT INTO heating_learning VALUES (?,?,?)',(area,1060,json.dumps({'state':'validated','coefficients':{'old':1}})))
            restarted=HeatingObserver(root,db,{'enabled':True});status=restarted.status()
            self.assertEqual(restarted.last_fit,0)
            self.assertTrue(status['training_update_required'])
            self.assertEqual(status['models']['eg']['state'],'collecting')
            self.assertNotIn('coefficients',status['models']['eg'])
            self.assertEqual(status['models']['dhw']['state'],'validated')
            self.assertEqual(status['sample_count'],1)


if __name__=='__main__':unittest.main()
