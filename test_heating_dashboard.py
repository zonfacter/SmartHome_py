"""No-network regressions for read integrity, quality, caching and isolation."""
import base64
import json
from pathlib import Path
import tempfile
import time
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from flask import Flask
from modules.gateway.heating import HeatingService, IoBroker, register_heating_routes
from modules.gateway.heating_lpb import POINTS, Point, checksum_valid, decode, read_frame


def packet(destination, source, kind, command, payload=b''):
    frame = bytearray([0x78, 0, destination, source, 0x0C, 2, 0, 0x14, kind])
    frame.extend(bytes.fromhex(command))
    frame.extend(payload)
    frame.extend(b'\0\0')
    frame[1] = len(frame)-1
    length = len(frame)-1
    checksum = ((257-length)*256 + length-2 + sum(frame[:length-1])) & 0xffff
    frame[-2:] = checksum.to_bytes(2, 'big')
    return bytes(frame)


def response(target=1, coid='05000464', payload=b'\0\7\x09', kind=7):
    c = bytes.fromhex(coid)
    query = bytes([c[1], c[0], c[2], c[3]]).hex()
    return {'tx_msg': base64.b64encode(packet(target,66,6,query)).decode(),
            'rx_msg': base64.b64encode(packet(66,target,kind,coid,payload)).decode()}


class HeatingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_frame_checks_checksum_source_object_and_read_type(self):
        r = response()
        self.assertEqual(read_frame(r,1,'05000464',66), b'\0\7\x09')
        self.assertTrue(checksum_valid(base64.b64decode(r['rx_msg'])))
        for field in ('tx_msg','rx_msg'):
            bad = dict(r)
            frame = bytearray(base64.b64decode(r[field])); frame[-1] ^= 1
            bad[field] = base64.b64encode(frame).decode()
            with self.assertRaises(ValueError): read_frame(bad,1,'05000464',66)
        with self.assertRaises(ValueError): read_frame(r,0,'05000464',66)
        with self.assertRaises(ValueError): read_frame(r,1,'05000462',66)

    def test_rejected_objects_remain_unavailable(self):
        self.assertIsNone(read_frame(response(payload=b'\7',kind=8),1,'05000464',66))

    def test_temperatures_curve_and_disabled_room_sensor(self):
        p = next(p for p in POINTS if p.area=='eg' and p.key=='flow_actual')
        self.assertAlmostEqual(decode(p,b'\0\7\x09'),28.140625)
        self.assertEqual(decode(p,b'\0\xff\xc0'),-1)
        self.assertIsNone(decode(p,b'\1\0\0'))
        with self.assertRaises(ValueError): decode(p,b'\0\7')
        curve = next(p for p in POINTS if p.area=='eg' and p.key=='curve')
        self.assertEqual(decode(curve,b'\0\x1c'),14)

    def test_relay_offsets_are_independent_and_have_no_scalar_prefix(self):
        definitions = {p.key:p for p in POINTS if p.area=='eg'}
        payload = b'\0\0\xff\0\0\0\0\0'
        self.assertIs(decode(definitions['pump'],payload),True)
        self.assertIs(decode(definitions['mixer_open'],payload),False)
        self.assertIs(decode(definitions['mixer_close'],payload),False)
        self.assertIs(decode(definitions['mixer_open'],b'\xff\0\xff\0\0\0\0\0'),True)
        with self.assertRaises(ValueError): decode(definitions['pump'],payload[:3])
        with self.assertRaises(ValueError): decode(definitions['pump'],b'\0\0\2\0\0\0\0\0')

    def test_enable_and_retained_gain_are_separate(self):
        definitions = {p.key:p for p in POINTS if p.area=='eg'}
        self.assertIs(decode(definitions['room_influence'],b'\1\4'),False)
        self.assertEqual(decode(definitions['room_gain'],b'\1\4'),4)

    def test_k_burner_stages_and_dhw_pump_use_the_output_block(self):
        definitions={p.key:p for p in POINTS if p.area=='anlage'}
        payload=b'\xff\xff\0\xff\0\0\0\0'
        for key in ('burner','burner_stage2','dhw_pump'):
            self.assertEqual(definitions[key].coid,'05000488')
            self.assertIs(decode(definitions[key],payload),True)
        self.assertNotIn('05000926',{p.coid for p in POINTS})

    def test_poll_is_readonly_and_shared_snapshots_do_not_poll_the_bus(self):
        calls = []
        def fetch(path):
            calls.append(path)
            if path=='/JI':
                return {'bus':'LPB','busaddr':66,'busdevices':[{'dev_id':0,'dev_fam':22,'dev_var':254},{'dev_id':1,'dev_fam':23,'dev_var':254}]}
            self.assertTrue(path.startswith('/JY06,'))
            coid,target=path.split(',')[1].split('!'); target=int(target)
            p=next(p for p in POINTS if p.target==target and p.coid==coid)
            payload = b'\0\5\0' if p.kind=='temperature' else b'\0\0\xff\0\0\0\0\0' if p.kind.startswith('relay') else b'\0\xff' if p.kind=='boolean' else b'\0\1' if p.kind=='mode' else b'\0\x63\x48' if p.kind=='counter' else b'\0\4'
            return response(target,coid,payload)
        service = HeatingService(self.root,config={'enabled':True},fetch=fetch)
        service.poll()
        count=len(calls)
        for _ in range(15):self.assertTrue(service.snapshot()['read_only'])
        self.assertEqual(count,len(calls))
        self.assertEqual(calls.count('/JY06,05000488!1'),1)
        self.assertEqual(service.snapshot()['floors']['eg']['metrics']['pump']['value'],True)
        self.assertEqual(len(service.history(1)),1)

    def test_wrong_controller_identity_stops_reads(self):
        calls=[]
        def fetch(path): calls.append(path); return {'bus':'PPS','busdevices':[]}
        service=HeatingService(self.root,config={},fetch=fetch);service.poll()
        self.assertEqual(calls,['/JI'])
        self.assertFalse(service.snapshot()['connection']['connected'])

    def test_cache_marks_old_values_stale(self):
        service=HeatingService(self.root,config={})
        service.metrics['eg.flow_actual'].update(value=28.1,quality='valid',updated_at=time.time()-200)
        metric=service.snapshot()['floors']['eg']['metrics']['flow_actual']
        self.assertEqual(metric['quality'],'stale')
        self.assertEqual(metric['value'],28.1)

    def test_history_downsampling_preserves_gaps_and_counter_types(self):
        service=HeatingService(self.root,config={})
        now=int(time.time())
        with sqlite3.connect(service.db_path) as db:
            for i in range(800):
                payload={'eg.flow_actual':None if 100<=i<110 else 28.1,
                         'anlage.burner':bool(i%2),'anlage.starts':100+i}
                db.execute('INSERT INTO heating_samples VALUES (?,?)',(now-800+i,json.dumps(payload)))
        samples=service.history(1)
        self.assertLessEqual(len(samples),360)
        self.assertTrue(any(r['eg.flow_actual'] is None for r in samples))
        self.assertTrue(all(isinstance(r['anlage.burner'],bool) for r in samples))
        self.assertEqual(samples[-1]['anlage.starts'],899)
        db.close()

    def test_iobroker_writes_cannot_escape_namespace_or_be_commands(self):
        bridge=IoBroker('ws://example.invalid')
        with self.assertRaises(ValueError):bridge.call('setState','tado.0.thermostat',{'val':30,'ack':True})
        with self.assertRaises(ValueError):bridge.call('setState','0_userdata.0.heizung.eg.pump',{'val':True,'ack':False})
        with self.assertRaises(ValueError):bridge.call('setObject','0_userdata.0.unrelated',{})
        with self.assertRaises(ValueError):bridge.call('delObject','0_userdata.0.heizung.eg.pump')

    def test_api_has_no_write_routes_and_history_is_bounded(self):
        repo=Path(__file__).parent
        app=Flask(__name__,template_folder=str(repo/'web/templates'))
        service=register_heating_routes(SimpleNamespace(app=app),self.root)
        client=app.test_client()
        self.assertEqual(client.get('/heizung').status_code,200)
        state=client.get('/api/heating/state')
        self.assertTrue(state.json['read_only'])
        self.assertFalse(state.json['enabled'])
        self.assertEqual(state.headers['Cache-Control'],'no-store')
        self.assertEqual(client.post('/api/heating/state',json={}).status_code,405)
        self.assertEqual(client.get('/api/heating/history?hours=900').status_code,400)
        self.assertEqual(client.get('/api/heating/history?hours=invalid').status_code,400)
        self.assertEqual(client.get('/api/heating/history?hours=6').json['samples'],[])
        self.assertIsNone(service.thread)


if __name__=='__main__':
    unittest.main()
