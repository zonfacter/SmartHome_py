"""Exercise real transaction code with a stateful LPB transport, never hardware."""
import json
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest

from modules.gateway.heating_lpb import decode_schedule
from modules.gateway.heating_schedule_write import ScheduleWriter, ScheduleError, encode
from test_heating_dashboard import packet, response


class Bus:
    def __init__(self):
        self.days = {(t,d): encode([{'start':'06:00','end':'20:00'}]) for t in (0,1) for d in range(7)}
        self.reads, self.writes = [], []
        self.fail_day = None
        self.bad_readback = False
        self.rollback_failure = False
        self.fail_mac = False

    def fetch(self, path):
        self.reads.append(path)
        if path == '/JI':
            return {'MAC':'wrong' if self.fail_mac else '00:11:22:33:44:55', 'bus':'LPB','busaddr':66,'busdest':0,'buswritable':0,
                    'busdevices':[{'dev_id':0,'dev_fam':22,'dev_var':254,'dev_serial':2004},
                                  {'dev_id':1,'dev_fam':23,'dev_var':254,'dev_serial':2006}]}
        match = re.fullmatch(r'/JY06,(05000A[89][0-9A-F])!([01])',path)
        assert match,path
        command, target = match[1],int(match[2]); day=int(command[-2:],16)-0x8C
        assert 0<=day<7
        return response(target,command,self.days[target,day])

    def send(self,path):
        match=re.fullmatch(r'/Y03,(05000A[89][0-9A-F]),([0-9A-F]{24})!([01])',path)
        assert match,path
        command,value,target=match[1],bytes.fromhex(match[2]),int(match[3]);day=int(command[-2:],16)-0x8C
        assert 0<=day<7
        self.writes.append((target,day,value))
        original=encode([{'start':'06:00','end':'20:00'}])
        if self.rollback_failure and value==original:
            raise TimeoutError('restoration unavailable')
        self.days[target,day]=value
        if self.fail_day==day and value!=original:
            raise TimeoutError('lost HTTP response after controller stored the program')
        if self.bad_readback and value!=original:
            changed=bytearray(value);changed[3]-=1;self.days[target,day]=bytes(changed)
        c=bytes.fromhex(command);query=bytes([c[1],c[0],c[2],c[3]]).hex()
        tx=packet(target,66,3,query,value)
        rx=packet(66,target,4,command)
        return '<pre>'+tx.hex(' ').upper()+'<br>'+rx.hex(' ').upper()+'</pre>'


class ScheduleWriteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.bus=Bus();self.updates=[]
        self.config={'enabled':True,'schedule_writes_enabled':True,'bsb_mac':'00:11:22:33:44:55'}
        self.writer=self.make_writer()

    def tearDown(self):self.temp.cleanup()

    def make_writer(self):
        return ScheduleWriter(self.root,self.config,self.bus.fetch,self.bus.send,threading.RLock(),lambda a,v:self.updates.append((a,v)))

    def body(self,changed=(2,),area='og'):
        baseline=[decode_schedule(self.bus.days[self.writer.TARGETS[area],d]) for d in range(7)]
        days=json.loads(json.dumps(baseline))
        for d in changed:days[d]=[{'start':'06:00','end':'19:50'}]
        return {'area':area,'base':baseline,'days':days}

    def test_codec_empty_three_phases_and_midnight(self):
        self.assertEqual(encode([]),bytes.fromhex('98001800'*3))
        value=[{'start':'00:00','end':'06:00'},{'start':'08:10','end':'12:20'},{'start':'18:00','end':'24:00'}]
        self.assertEqual(len(encode(value)),12)
        self.assertEqual(decode_schedule(encode(value))[-1]['end'],'24:00')
        for v in [[{'start':'06:15','end':'20:00'}],[{'start':'20:00','end':'06:00'}],
                  [{'start':'06:00','end':'12:00'},{'start':'11:00','end':'13:00'}],value+[value[0]]]:
            with self.assertRaises(ScheduleError):encode(v)

    def test_preview_reads_fresh_without_writes_and_apply_skips_unchanged_days(self):
        body=self.body();p=self.writer.preview(body,'client')
        self.assertEqual([x['day'] for x in p['changes']],[2]);self.assertEqual(self.bus.writes,[])
        result=self.writer.apply(p['token'],'client')
        self.assertTrue(result['success']);self.assertEqual(len(self.bus.writes),1)
        self.assertEqual(self.bus.writes[0][:2],(0,2))
        self.assertEqual(result['verified_days'][2][0]['end'],'19:50')
        before=len(self.bus.reads)
        self.assertEqual(self.writer.apply(p['token'],'client'),result)
        self.assertEqual(before,len(self.bus.reads));self.assertEqual(len(self.bus.writes),1)
        self.assertEqual(json.loads(next(self.writer.directory.glob('*.json')).read_text())['status'],'verified')

    def test_eg_maps_only_to_m_target(self):
        p=self.writer.preview(self.body(area='eg'),'client');self.writer.apply(p['token'],'client')
        self.assertEqual([t for t,d,v in self.bus.writes],[1])

    def test_zero_changes_send_no_set(self):
        p=self.writer.preview(self.body(changed=()),'client');self.writer.apply(p['token'],'client')
        self.assertEqual(self.bus.writes,[])

    def test_stale_base_and_changes_after_preview_never_write(self):
        body=self.body();self.bus.days[0,0]=encode([{'start':'07:00','end':'20:00'}])
        with self.assertRaises(ScheduleError) as e:self.writer.preview(body,'client')
        self.assertEqual(e.exception.status,409)
        p=self.writer.preview(self.body(),'client');self.bus.days[0,1]=encode([])
        with self.assertRaises(ScheduleError):self.writer.apply(p['token'],'client')
        self.assertEqual(self.bus.writes,[])

    def test_lost_response_in_second_day_rolls_back_both_attempted_days(self):
        initial=dict(self.bus.days);p=self.writer.preview(self.body((0,1)),'client');self.bus.fail_day=1
        with self.assertRaises(ScheduleError) as e:self.writer.apply(p['token'],'client')
        self.assertEqual(e.exception.status,502);self.assertTrue(e.exception.details['restored'])
        self.assertEqual(initial,self.bus.days);self.assertFalse(self.writer.pending)
        count=len(self.bus.writes)
        with self.assertRaises(ScheduleError):self.writer.apply(p['token'],'client')
        self.assertEqual(len(self.bus.writes),count)

    def test_ack_without_correct_readback_is_not_success(self):
        initial=dict(self.bus.days);p=self.writer.preview(self.body(),'client');self.bus.bad_readback=True
        with self.assertRaises(ScheduleError) as e:self.writer.apply(p['token'],'client')
        self.assertTrue(e.exception.details['restored']);self.assertEqual(initial,self.bus.days)

    def test_failed_rollback_is_durable_and_restart_recovers_before_new_writes(self):
        initial=dict(self.bus.days);p=self.writer.preview(self.body(),'client')
        self.bus.fail_day=2;self.bus.rollback_failure=True
        with self.assertRaises(ScheduleError) as e:self.writer.apply(p['token'],'client')
        self.assertFalse(e.exception.details['restored']);self.assertTrue(self.writer.pending)
        restarted=self.make_writer();self.assertTrue(restarted.pending)
        self.bus.rollback_failure=False;self.bus.fail_day=None
        restarted.recover();self.assertFalse(restarted.pending);self.assertEqual(initial,self.bus.days)

    def test_identity_disabled_and_malformed_scope_are_rejected(self):
        self.bus.fail_mac=True
        with self.assertRaises(ScheduleError):self.writer.preview(self.body(),'client')
        self.bus.fail_mac=False;self.writer.enabled=False
        with self.assertRaises(ScheduleError):self.writer.preview(self.body(),'client')
        self.writer.enabled=True
        for body in [None,{},dict(self.body(),area='anlage'),dict(self.body(),command='05000603')]:
            with self.assertRaises(ScheduleError):self.writer.preview(body,'client')
        self.assertEqual(self.bus.writes,[])
        self.config['enabled']=False
        self.assertFalse(self.make_writer().enabled)

    def test_preview_owner_expiry_and_single_writer_lock(self):
        p=self.writer.preview(self.body(),'client')
        with self.assertRaises(ScheduleError):self.writer.apply(p['token'],'other')
        self.writer.active.acquire()
        try:
            with self.assertRaises(ScheduleError):self.writer.apply(p['token'],'client')
        finally:self.writer.active.release()
        self.writer.proposals[p['token']]['expires']=time.time()-1
        with self.assertRaises(ScheduleError):self.writer.apply(p['token'],'client')
        self.assertEqual(self.bus.writes,[])

    def test_corrupt_ack_rolls_back_even_if_controller_stored_the_value(self):
        initial=dict(self.bus.days);p=self.writer.preview(self.body(),'client')
        send=self.bus.send
        self.writer.send=lambda path:send(path).replace('</pre>','00</pre>')
        with self.assertRaises(ScheduleError) as e:self.writer.apply(p['token'],'client')
        self.assertTrue(e.exception.details['restored']);self.assertEqual(initial,self.bus.days)

    def test_rollback_preserves_an_external_operator_change(self):
        p=self.writer.preview(self.body((0,1)),'client');send=self.bus.send
        external=encode([{'start':'08:00','end':'18:00'}])
        def concurrent_change(path):
            result=send(path)
            if self.bus.writes[-1][:2]==(0,1) and self.bus.writes[-1][2]!=encode([{'start':'06:00','end':'20:00'}]):
                self.bus.days[0,0]=external
                raise TimeoutError('operator changed another day during transmission')
            return result
        self.writer.send=concurrent_change
        with self.assertRaises(ScheduleError) as e:self.writer.apply(p['token'],'client')
        self.assertFalse(e.exception.details['restored'])
        self.assertEqual(self.bus.days[0,0],external)
        self.assertTrue(self.writer.pending)

    def test_corrupt_journal_blocks_new_transfers(self):
        (self.writer.directory/'broken.json').write_text('not json')
        restarted=self.make_writer()
        with self.assertRaises(ScheduleError) as e:restarted.preview(self.body(),'client')
        self.assertEqual(e.exception.status,503);self.assertEqual(self.bus.writes,[])


if __name__=='__main__':unittest.main()
