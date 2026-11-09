"""Protocol scope, temporal coherence and abstention for pump explanations."""
import unittest

from modules.gateway.heating_lpb import POINTS
from modules.gateway.heating_pumps import split_signal, diagnose
from test_heating_dashboard import response


def item(value, stamp=990, quality='valid'):
    return {'value':value,'quality':quality,'updated_at':stamp}


class PumpContextTests(unittest.TestCase):
    def context(self, area='og', pump=False, demand='08 40 00 02', lock='00 00', q3=False, **extra):
        metrics={'pump':item(pump),'mode':item('Automatik'),
                 'space_request_raw':item(demand),'transfer_lock_raw':item(lock),**extra}
        return diagnose(area,metrics,{'dhw_pump':item(q3)},[],1000)

    def test_500_priority_bits_are_conditional_on_validity_for_exact_namespaces(self):
        for key in ('space_request_raw','dhw_request_raw','mixer_request_raw'):
            inactive=split_signal(key,key,'request',4,item('0F 00 00 18'))
            self.assertFalse(inactive['protocol_valid'])
            self.assertIsNone(inactive['shifting_dhw_priority'])
            self.assertNotIn('Kennzeichen für',inactive['interpretation'])
            active=split_signal(key,key,'request',4,item('0F 00 00 1B'))
            self.assertTrue(active['shifting_dhw_priority'])
            self.assertFalse(active['absolute_dhw_priority'])
            self.assertEqual(active['unknown_attribute_bits'],[4])
        unknown=split_signal('producer_request_raw','EM501','request',5,item('0F 00 00 1B 01'))
        self.assertNotIn('protocol_valid',unknown)

    def test_status_522_g_means_presence_not_scalar_validity(self):
        s=split_signal('mixer_status_raw','Status','status',5,item('00 03 00 00 00'))
        self.assertTrue(s['producer_present']);self.assertTrue(s['status_flags']['eco'])
        self.assertNotIn('protocol_valid',s);self.assertIsNone(s['effective'])
        absent=split_signal('mixer_status_raw','Status','status',5,item('00 02 00 00 00'))
        self.assertFalse(absent['producer_present'])
        self.assertIsNone(absent['status_flags']['eco'])
        unknown=split_signal('mixer_status_raw','Status','status',5,item('01 41 00 00 00'))
        self.assertTrue(unknown['status_flags']['manual_mode'])
        self.assertEqual(unknown['unknown_attribute_bits'],[6])

    def test_context_distinguishes_og_pump_stop_and_eg_mixing_restriction(self):
        og=self.context(lock='64 01',q3=True)
        eg=self.context(area='eg',pump=True,lock='64 01',q3=True)
        self.assertEqual(og['assessment']['code'],'dhw_restriction')
        self.assertEqual(eg['assessment']['code'],'mixing_restriction')
        for d in (eg,og):self.assertEqual(d['cause_status'],'unresolved')
        self.assertIn('möglich',eg['assessment']['summary'])

    def test_no_warmwater_cause_from_just_a_percent_field_or_q3(self):
        self.assertNotEqual(self.context(lock='64 00',q3=True)['assessment']['code'],'dhw_restriction')
        self.assertNotEqual(self.context(lock='64 01',q3=False)['assessment']['code'],'dhw_restriction')
        self.assertNotEqual(self.context(lock='FF 01',q3=True)['assessment']['code'],'dhw_restriction')

    def test_incomplete_stale_future_and_temporally_mixed_contexts_abstain(self):
        for metric in (item('64 01',stamp=950),item('64 01',stamp=800),
                       item('64 01',stamp=1001),item('64 01',quality='stale')):
            d=self.context(lock='64 01',q3=True,transfer_lock_raw=metric)
            self.assertEqual(d['assessment']['status'],'insufficient')
            self.assertEqual(d['cause_status'],'unresolved')

    def test_heating_and_afterrun_are_not_forced_into_one_unique_cause(self):
        d=self.context(pump=True,demand='08 40 00 03',forced_mixer_raw=item('32 01'))
        self.assertEqual(d['assessment']['code'],'heat_and_afterrun')
        d=self.context(pump=True,demand='08 40 00 02',forced_mixer_raw=item('32 01'))
        self.assertEqual(d['assessment']['code'],'afterrun')
        d=self.context(pump=True,demand='FF C0 00 03')
        self.assertEqual(d['assessment']['code'],'request_value_uncertain')

    def test_context_checks_combined_span_not_just_pairwise_distances(self):
        metrics={'pump':item(False,970),'mode':item('Automatik',940),
                 'transfer_lock_raw':item('64 01',990),'space_request_raw':item('08 40 00 03',990)}
        d=diagnose('og',metrics,{'dhw_pump':item(True,990)},[],1000)
        self.assertEqual(d['assessment']['code'],'time_skew')
        self.assertEqual(d['assessment']['read_skew_seconds'],50)

    def test_present_producer_status_is_an_indication_not_a_proven_pump_stop(self):
        d=self.context(pump=True,demand='08 40 00 03',mixer_status_raw=item('00 05 00 00 00'))
        self.assertEqual(d['assessment']['code'],'producer_restriction')
        self.assertEqual(d['assessment']['status'],'indication')
        self.assertEqual(d['cause_status'],'unresolved')
        d=self.context(pump=True,demand='08 40 00 03',mixer_status_raw=item('00 04 00 00 00'))
        self.assertNotEqual(d['assessment']['code'],'producer_restriction')

    def test_poll_groups_keep_context_together_without_extra_queries(self):
        # Use a real collector with type-ERR responses; this checks query ordering
        # and deduplication rather than relying on the helper's implementation.
        from modules.gateway.heating import HeatingService
        import tempfile
        calls=[]
        def fetch(path):
            calls.append(path)
            if path=='/JI':return {'bus':'LPB','busaddr':66,'busdevices':[{'dev_id':0,'dev_fam':22,'dev_var':254},{'dev_id':1,'dev_fam':23,'dev_var':254}]}
            coid,target=path.split(',')[1].split('!')
            return response(int(target),coid,b'\7',kind=8)
        with tempfile.TemporaryDirectory() as root:
            service=HeatingService(root,config={},fetch=fetch);service._poll_bus()
        self.assertEqual(len(calls),len(set(calls)))
        self.assertLess(calls.index('/JY06,150001F8!0'),calls.index('/JY06,05000488!0'))
        self.assertEqual(calls.index('/JY06,05000488!1'),calls.index('/JY06,05000488!0')+1)
        self.assertLess(calls.index('/JY06,1500020A!1'),calls.index('/JY06,0500092D!0'))
        self.assertTrue(all(not p.slow for p in POINTS if p.key=='mixer_status_raw'))


if __name__=='__main__':unittest.main()
