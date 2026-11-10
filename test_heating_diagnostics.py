"""Diagnostic layouts and statistics are tested without hardware writes."""
import json
from contextlib import closing
import sqlite3
import tempfile
import time
from pathlib import Path
import unittest
from unittest.mock import patch

from modules.gateway.heating import HeatingService
from modules.gateway.heating_lpb import POINTS, Point, decode
from modules.gateway.heating_statistics import summarize


def sample(ts,count,stage1=True,stage2=False):
    return {'ts':ts,'anlage.starts':count,'anlage.burner':stage1,'anlage.burner_stage2':stage2}


class DiagnosticTests(unittest.TestCase):
    def test_errors_have_no_scalar_prefix(self):
        for kind,expected in [('error_code',10),('error_priority',7)]:
            p=Point('eg','test','Test',1,'0500006B',kind,'')
            self.assertEqual(decode(p,b'\x0a\x07'),expected)
            with self.assertRaises(ValueError):decode(p,b'\0')

    def test_hours_only_come_from_k_byte_five_and_are_seconds(self):
        p=next(p for p in POINTS if p.kind=='burner_hours')
        payload=b'\0\1\0\0\0'+(37800).to_bytes(4,'big')
        self.assertEqual(decode(p,payload),10.5)
        self.assertIsNone(decode(p,payload[:5]+b'\xff'*4))
        with self.assertRaises(ValueError):decode(p,payload[:-1])
        with self.assertRaises(ValueError):decode(Point('eg','bad','Bad',1,p.coid,'burner_hours','h'),payload)
        self.assertEqual(sum(p.kind=='burner_hours' for p in POINTS),1)

    def test_weekly_clock_ignores_calendar_placeholders_and_preserves_disabled(self):
        p=Point('og','clock','Clock',0,'0500000B','clock','')
        self.assertEqual(decode(p,bytes.fromhex('00 7F 0C 14 07 15 08 32 18')),'Sonntag 21:08')
        self.assertIsNone(decode(p,bytes.fromhex('01 00 00 00 00 00 00 00 00')))
        for raw in ['00 7F 0C 14 00 15 08 32 18','00 7F 0C 14 07 18 08 32 18']:
            with self.assertRaises(ValueError):decode(p,bytes.fromhex(raw))

    def test_raw_blocks_keep_attributes_and_do_not_claim_active_states(self):
        p=Point('eg','raw','Raw',1,'210001F4','raw4','')
        self.assertEqual(decode(p,bytes.fromhex('08 40 00 02')),'08 40 00 02')
        with self.assertRaises(ValueError):decode(p,b'\0\0')
        keys=[(p.area,p.key) for p in POINTS]
        self.assertEqual(len(keys),len(set(keys)))

    def test_legacy_text_values_and_unknown_codes(self):
        p=Point('anlage','priority','Priority',0,'05000721','dhw_priority','')
        self.assertEqual(decode(p,b'\0\1'),'Gleitend')
        self.assertEqual(decode(p,b'\0\x7f'),'Code 127')
        self.assertIsNone(decode(p,b'\1\0'))
        self.assertEqual(decode(Point('og','relay_test','Test',0,'05000073','relay_test',''),b'\0\0'),'Inaktiv')
        for kind,expected in [('changeover_eg','Zentrale Umschaltung'),('changeover_og','Zentral')]:
            self.assertEqual(decode(Point('eg','x','X',1,'05000611',kind,''),b'\0\xff'),expected)

    def test_counting_and_relay_time_share_the_same_coverage(self):
        result=summarize([sample(0,10),sample(60,11),sample(120,12,False)],1,3600)
        self.assertEqual(result['starts'],2)
        self.assertEqual(result['coverage_seconds'],120)
        self.assertEqual(result['relay_runtime_minutes'],2)
        self.assertEqual(result['starts_per_hour'],60)
        self.assertEqual(result['relay_minutes_per_start'],1)
        self.assertEqual(sum(b['starts'] or 0 for b in result['bins']),2)
        self.assertAlmostEqual(sum(b['coverage_seconds'] for b in result['bins']),120)

    def test_empty_and_missing_intervals_remain_unknown(self):
        for samples in [[],[sample(0,1),sample(121,2)],
                        [{'ts':0,'anlage.starts':1,'anlage.burner':False},{'ts':60,'anlage.starts':2,'anlage.burner':False}]]:
            result=summarize(samples,1,3600)
            self.assertIsNone(result['starts']);self.assertEqual(result['coverage_seconds'],0)
            self.assertTrue(all(b['starts'] is None for b in result['bins']))

    def test_counter_wrap_and_reset_are_not_confused(self):
        wrapped=summarize([sample(0,65535),sample(60,1)],1,3600)
        self.assertEqual(wrapped['starts'],2)
        reset=summarize([sample(0,100),sample(60,0),sample(120,1)],1,3600)
        self.assertEqual(reset['starts'],1);self.assertEqual(reset['counter_resets'],1)
        self.assertEqual(reset['coverage_seconds'],60)

    def test_second_stage_only_and_zero_starts(self):
        result=summarize([sample(0,5,False,True),sample(60,5,False,True)],1,3600)
        self.assertEqual(result['relay_runtime_minutes'],1)
        self.assertEqual(result['starts'],0)
        self.assertIsNone(result['relay_minutes_per_start'])

    def test_future_and_out_of_window_samples_are_ignored(self):
        result=summarize([sample(-60,1),sample(0,2),sample(60,3),sample(4000,4)],1,3600)
        self.assertEqual(result['starts'],1);self.assertEqual(result['coverage_seconds'],60)

    def test_history_handles_new_keys_without_averaging_counters(self):
        with tempfile.TemporaryDirectory() as directory:
            service=HeatingService(Path(directory),config={})
            now=int(time.time())
            with closing(sqlite3.connect(service.db_path)) as db, db:
                db.execute('INSERT INTO heating_samples VALUES (?,?)',(now-60,json.dumps({'anlage.starts':10})))
                db.execute('INSERT INTO heating_samples VALUES (?,?)',(now-30,json.dumps({'anlage.starts':11,'anlage.burner_hours':10.5})))
            data=service.history(1)
            self.assertIn('anlage.burner_hours',data[0]);self.assertIsNone(data[0]['anlage.burner_hours'])
            self.assertEqual(data[-1]['anlage.burner_hours'],10.5)
            self.assertEqual(data[-1]['anlage.starts'],11)

    def test_iobroker_preserves_text_boolean_and_numeric_types(self):
        class Bridge:
            PREFIX='0_userdata.0.heizung'
            objects={}
            states={}
            def __init__(self,url):pass
            def connect(self):return self
            def close(self):pass
            def call(self,method,*args):
                if method=='getStates':return {}
                if method=='getObject':return None
                if method=='setObject':self.objects[args[0]]=args[1]
                if method=='setState':self.states[args[0]]=args[1]
        with tempfile.TemporaryDirectory() as directory:
            service=HeatingService(Path(directory),config={'iobroker_url':'ws://example.invalid'})
            service.metrics['eg.relay_test'].update(value='Inaktiv',quality='valid',updated_at=time.time())
            with patch('modules.gateway.heating.IoBroker',Bridge):service._sync_iobroker()
        for key,type_name in [('eg.relay_test','string'),('og.space_request_raw','string'),('eg.lpb_power','boolean'),('eg.error_code','number')]:
            obj=Bridge.objects[Bridge.PREFIX+'.'+key]
            self.assertEqual(obj['common']['type'],type_name)
            self.assertFalse(obj['common']['write'])
        self.assertEqual(Bridge.states[Bridge.PREFIX+'.eg.relay_test']['val'],'Inaktiv')
        self.assertTrue(all(v['ack'] for v in Bridge.states.values()))


if __name__=='__main__':unittest.main()
