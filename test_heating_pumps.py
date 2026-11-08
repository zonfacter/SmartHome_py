"""Read-only pump context must not promote unknown LPB flags to causes."""
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from flask import Flask
from modules.gateway.heating import HeatingService, register_heating_routes
from modules.gateway.heating_lpb import POINTS, decode
from modules.gateway.heating_pumps import SIGNALS, diagnose, split_signal, schedule_phase


def item(value, quality='valid', stamp=None):
    return {'value':value,'quality':quality,'updated_at':stamp or time.time()}


def days():
    labels=('Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag')
    return [{'label':label,'quality':'valid','periods':[{'start_minute':360,'end_minute':1200}]} for label in labels]


class PumpTests(unittest.TestCase):
    def test_request_offsets_endianness_signedness_and_priority(self):
        s=split_signal('request','Request','request',5,item('08 40 00 12 07'))
        self.assertEqual(s['temperature_field'],33)
        self.assertEqual(s['attributes_hex'],'0x0012')
        self.assertEqual(s['attribute_bits'],[1,4])
        self.assertEqual(s['priority_field'],7)
        self.assertIsNone(s['effective'])
        s=split_signal('request','Request','request',4,item('FF C0 80 00'))
        self.assertEqual(s['temperature_field'],-1)
        self.assertEqual(s['attribute_bits'],[15])

    def test_no_attribute_byte_is_silently_declared_valid_or_active(self):
        for attribute in range(256):
            s=split_signal('forced','Forced','percent',2,item(f'32 {attribute:02X}'))
            self.assertEqual(s['percent_field'],50)
            self.assertIsNone(s['effective'])
        s=split_signal('lock','Lock','percent',2,item('00 00'))
        self.assertEqual(s['percent_field'],0)
        self.assertIsNone(s['effective'])

    def test_malformed_and_stale_fields_never_turn_into_zero(self):
        for raw in ('bad','00',None,'00 00 00'):
            s=split_signal('lock','Lock','percent',2,item(raw))
            self.assertEqual(s['quality'],'error')
            self.assertNotIn('percent_field',s)
        for quality in ('pending','stale','error','unavailable'):
            s=split_signal('lock','Lock','percent',2,item('00 00',quality))
            self.assertNotIn('percent_field',s)
        s=split_signal('lock','Lock','percent',2,item('FF 01'))
        self.assertEqual(s['value_field'],-1)
        self.assertIsNone(s['percent_field'])

    def test_phase_uses_controller_weekday_and_half_open_intervals(self):
        for clock,expected in [('Sonntag 05:59','reduced'),('Sonntag 06:00','comfort'),('Sonntag 20:00','reduced')]:
            self.assertEqual(schedule_phase({'clock':item(clock)},days())['phase'],expected)
        for clock in ('Sonntag 25:00','Notaday 10:00',None):
            self.assertIsNone(schedule_phase({'clock':item(clock)},days()))
        self.assertIsNone(schedule_phase({'clock':item('Sonntag 12:00','stale')},days()))
        self.assertIsNone(schedule_phase({'clock':item('Sonntag 12:00')},days()[:6]))

    def test_reduced_and_kon_are_hints_not_proven_stop_reason(self):
        metrics={'pump':item(False),'mode':item('Automatik'),'clock':item('Sonntag 22:00'),
                 'room_setpoint':item(14),'quick_setback':item(2)}
        result=diagnose('og',metrics,{'dhw_pump':item(False)},days(),time.time())
        self.assertEqual(result['phase']['phase'],'reduced')
        self.assertTrue(any('Schnellabsenkung' in hint for hint in result['hints']))
        self.assertEqual(result['cause_status'],'unresolved')
        self.assertFalse(result['pump_contact'])
        metrics['mode']=item('Handbetrieb')
        result=diagnose('og',metrics,{},days(),time.time())
        self.assertIsNone(result['phase'])
        self.assertFalse(any('Schnellabsenkung' in hint for hint in result['hints']))

    def test_running_dhw_and_zero_locks_do_not_prove_causation(self):
        metrics={'pump':item(False),'mode':item('Automatik')}
        for key in ('producer_lock_raw','mixing_lock_raw','transfer_lock_raw'):
            metrics[key]=item('00 00')
        result=diagnose('eg',metrics,{'dhw_pump':item(True)},[],time.time())
        self.assertEqual(result['cause_status'],'unresolved')
        self.assertTrue(any('bestätigt keine aktive Sperre' in fact for fact in result['facts']))
        self.assertTrue(any('beweist keine' in hint for hint in result['hints']))
        self.assertTrue(all(s['effective'] is None for s in result['signals']))

    def test_missing_contact_and_stale_fields_are_unknown(self):
        result=diagnose('eg',{'pump':item(True,'stale')},{},[],time.time())
        self.assertIsNone(result['pump_contact'])
        self.assertEqual(result['summary'],'Q1 unbekannt')

    def test_live_signals_are_fast_and_settings_slow_with_unique_keys(self):
        points={(p.area,p.key):p for p in POINTS}
        self.assertEqual(len(points),len(POINTS))
        for area in ('eg','og'):
            for key,*_ in SIGNALS:
                if (area,key) in points:self.assertFalse(points[area,key].slow)
            self.assertTrue(points[area,'quick_setback'].slow)
            self.assertEqual(decode(points[area,'quick_setback'],bytes.fromhex('00 0A')),10)
            self.assertFalse(decode(points[area,'remote_switch'],bytes.fromhex('00 00')))

    def test_event_dedup_preserves_contact_transitions_and_raw_attributes(self):
        with tempfile.TemporaryDirectory() as directory:
            service=HeatingService(directory,config={})
            for area in ('eg','og'):
                service.metrics[area+'.pump'].update(item(False))
                service.metrics[area+'.space_request_raw'].update(item('08 40 00 02'))
            service._save_history();service._save_history()
            self.assertEqual(len(service.pump_events(1)['eg']),1)
            service.metrics['eg.pump'].update(item(True))
            service.metrics['eg.space_request_raw'].update(item('08 40 00 03'))
            service._save_history()
            events=service.pump_events(1)
            self.assertEqual(len(events['eg']),2)
            self.assertEqual(len(events['og']),1)
            self.assertTrue(events['eg'][0]['metrics']['pump']['value'])
            self.assertEqual(events['eg'][0]['metrics']['space_request_raw']['value'],'08 40 00 03')
            restarted=HeatingService(directory,config={})
            self.assertEqual(restarted.pump_events(1),events)

    def test_api_is_bounded_and_never_queries_bus(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Flask(__name__)
            service=register_heating_routes(SimpleNamespace(app=app),Path(directory))
            def forbidden(_):raise AssertionError('Unexpected hardware request')
            service.fetch=forbidden
            client=app.test_client()
            for hours in ('bad','0','7','999'):
                self.assertEqual(client.get('/api/heating/pumps?hours='+hours).status_code,400)
            response=client.get('/api/heating/pumps?hours=6')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json['event_limit_per_floor'],40)
            self.assertEqual(response.json['events'],{'eg':[],'og':[]})
            self.assertEqual(response.json['floors']['eg']['cause_status'],'unresolved')


if __name__=='__main__':unittest.main()
