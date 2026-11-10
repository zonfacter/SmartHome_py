"""Recorded legacy layouts: no hardware access or control writes."""
import tempfile
import time
import unittest
from unittest.mock import patch

from modules.gateway.heating import HeatingService
from modules.gateway.heating_lpb import POINTS, TEXT_KINDS, decode
from modules.gateway.heating_pumps import split_signal, diagnose


def item(value, quality='valid'):
    return {'value': value, 'quality': quality, 'updated_at': time.time()}


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.points = {(p.area, p.key): p for p in POINTS}

    def decode(self, key, raw, area='anlage'):
        return decode(self.points[area, key], bytes.fromhex(raw))

    def test_recorded_boolean_enums_use_ff_not_panel_one(self):
        for key, raw, expected in [('dhw_request_source', '00 00', 'Speicherfühler'),
                                   ('burner_type', '00 FF', 'Zweistufig'),
                                   ('boiler_mode', '00 FF', 'Automatik')]:
            self.assertEqual(self.decode(key, raw), expected)
            self.assertIsNone(self.decode(key, '01 FF'))
            self.assertEqual(self.decode(key, '00 01'), 'Code 1')
        self.assertEqual(self.decode('dhw_request_source', '00 FF'), 'Thermostat')
        self.assertFalse(self.decode('dhw_dedicated', '00 00'))
        self.assertFalse(self.decode('chimney_sweep', '00 00'))

    def test_integrals_are_not_temperature_scalars(self):
        for key in ('stage2_release_integral', 'stage2_reset_integral'):
            self.assertEqual(self.decode(key, '00 00 0A'), 10)
            self.assertIsNone(self.decode(key, '01 00 0A'))
            for raw in ('00 0A', '00 FF FF', '00 01 F5', '02 00 0A'):
                with self.assertRaises(ValueError): self.decode(key, raw)
        self.assertEqual(self.decode('boiler_min_oem', '00 09 80'), 38)

    def test_two_byte_source_is_a_block_without_validity_prefix(self):
        for area in ('eg', 'og'):
            self.assertEqual(self.decode('outside_source', '00 01', area), 'Segment S0 · Gerät G1')
            self.assertEqual(self.decode('outside_source', '01 02', area), 'Segment S1 · Gerät G2')
            self.assertIn('nicht zugeordnet', self.decode('outside_source', 'FF FF', area))
            with self.assertRaises(ValueError): self.decode('outside_source', '00', area)
            self.assertEqual(self.decode('startup_boost', '00 01 40', area), 5)
            self.assertEqual(self.decode('adaptation_zaf1', '00 0F', area), 15)
        self.assertEqual(self.decode('clock_source', '00 03', 'og'), 'Zeitmaster am LPB')
        self.assertEqual(self.decode('clock_source', '00 02', 'eg'), 'LPB · mit Ferneinstellung')

    def test_new_iobroker_states_are_readable_typed_and_acknowledged(self):
        class Bridge:
            PREFIX = '0_userdata.0.heizung'
            objects, states = {}, {}
            def __init__(self, _): pass
            def connect(self): return self
            def close(self): pass
            def call(self, method, *args):
                if method == 'getStates': return {}
                if method == 'getObject': return None
                if method == 'setObject': self.objects[args[0]] = args[1]
                if method == 'setState': self.states[args[0]] = args[1]
        with tempfile.TemporaryDirectory() as root:
            service = HeatingService(root, config={'iobroker_url': 'ws://example.invalid'})
            service.metrics['anlage.dhw_request_source'].update(item('Speicherfühler'))
            service.metrics['anlage.stage2_release_integral'].update(item(10))
            with patch('modules.gateway.heating.IoBroker', Bridge): service._sync_iobroker()
        for key, kind in [('anlage.dhw_request_source', 'string'), ('anlage.burner_type', 'string'),
                          ('anlage.dhw_dedicated', 'boolean'), ('anlage.stage2_release_integral', 'number'),
                          ('eg.outside_source', 'string'), ('og.adaptation_zaf1', 'number')]:
            obj = Bridge.objects[Bridge.PREFIX + '.' + key]
            self.assertEqual(obj['common']['type'], kind)
            self.assertTrue(obj['common']['read'])
            self.assertFalse(obj['common']['write'])
        self.assertTrue(all(s['ack'] for s in Bridge.states.values()))
        self.assertIsNone(Bridge.states[Bridge.PREFIX + '.anlage.burner_type']['val'])
        self.assertEqual(Bridge.states[Bridge.PREFIX + '.anlage.stage2_release_integral']['val'], 10)

    def test_504_reduction_requires_g_and_keeps_unknown_bits(self):
        for raw, valid, mandatory in [('64 01', True, False), ('05 03', True, True), ('64 00', False, None)]:
            s = split_signal('transfer_lock_raw', 'Lock', 'percent', 2, item(raw))
            self.assertIs(s['protocol_valid'], valid)
            self.assertIs(s['mandatory'], mandatory)
            self.assertIsNone(s['effective'])
        s = split_signal('transfer_lock_raw', 'Lock', 'percent', 2, item('64 81'))
        self.assertEqual(s['unknown_attribute_bits'], [7])
        bad = split_signal('transfer_lock_raw', 'Lock', 'percent', 2, item('FF 01'))
        self.assertIn('außerhalb', bad['interpretation'])

    def test_507_afterrun_is_not_a_fifty_percent_force(self):
        s = split_signal('forced_mixer_raw', 'Force', 'percent', 2, item('32 01'))
        self.assertTrue(s['protocol_valid'])
        self.assertFalse(s['mandatory'])
        self.assertIn('nur Nachlauf', s['interpretation'])
        s = split_signal('forced_mixer_raw', 'Force', 'percent', 2, item('32 03'))
        self.assertIn('Zwang an alle Verbraucher: 50 %', s['interpretation'])

    def test_no_generalization_to_uncovered_namespaces_or_stale_fields(self):
        for key in ('producer_lock_raw', 'mixing_lock_raw', 'forced_producer_raw'):
            s = split_signal(key, key, 'percent', 2, item('64 03'))
            self.assertNotIn('protocol_valid', s)
            self.assertIsNone(s['effective'])
        for quality in ('stale', 'pending', 'unavailable', 'error'):
            s = split_signal('transfer_lock_raw', 'Lock', 'percent', 2, item('64 03', quality))
            self.assertNotIn('protocol_valid', s)

    def test_500_validity_does_not_establish_a_pump_cause(self):
        s = split_signal('space_request_raw', 'Request', 'request', 4, item('08 40 00 02'))
        self.assertEqual(s['temperature_field'], 33)
        self.assertFalse(s['protocol_valid'])
        self.assertIsNone(s['transport_pump_requested'])
        metrics = {'pump': item(False), 'space_request_raw': item('08 40 00 02'),
                   'transfer_lock_raw': item('64 01')}
        d = diagnose('og', metrics, {'dhw_pump': item(True)}, [], time.time())
        self.assertEqual(d['cause_status'], 'unresolved')
        self.assertTrue(any('Reduktionsanforderung: 100 %' in s for s in d['facts']))
        self.assertTrue(any('nicht eindeutig belegt' in s for s in d['hints']))


if __name__ == '__main__': unittest.main()
