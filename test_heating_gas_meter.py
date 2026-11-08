"""Manual cumulative meter readings are durable, ordered and never actuate devices."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from flask import Flask
from modules.gateway.heating import register_heating_routes
from modules.gateway.heating_gas_meter import GasMeter,MeterError,parse_reading


class GasMeterTests(unittest.TestCase):
    def test_decimal_precision_berlin_timestamp_and_optional_intervals(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'data.db';meter=GasMeter(path)
            first={'measured_at':'2024-05-05T12:00','volume_m3':'1234,567'}
            result=meter.add(first)
            self.assertEqual(result['reading']['volume_text'],'1234,567')
            self.assertEqual(result['reading']['ts'],1714903200)
            self.assertIsNone(meter.summary()['latest_interval'])
            self.assertFalse(meter.add(first)['inserted'])
            meter.add({'measured_at':'2024-05-08T19:00','volume_m3':'1240.789'})
            summary=GasMeter(path).summary()
            self.assertEqual(summary['count'],2)
            self.assertEqual(summary['latest_interval']['measured_m3'],6.222)
            self.assertEqual(summary['latest_interval']['hours'],79)
            self.assertFalse(summary['interpolation'])
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT volume_milli_m3 FROM heating_gas_readings ORDER BY ts').fetchone()[0],1234567)

    def test_reject_invalid_precision_future_and_dst_without_saving(self):
        for value in ('1.234,567','NaN','Infinity','-1','1.2345',True,{},'1e5'):
            with self.subTest(value=value),self.assertRaises(MeterError):
                parse_reading({'measured_at':'2024-05-05T12:00','volume_m3':value})
        for stamp in ('nonsense','2099-01-01T00:00','2024-03-31T02:30','2024-10-27T02:30','2024-05-05T12:00:59'):
            with self.subTest(stamp=stamp),self.assertRaises(MeterError):
                parse_reading({'measured_at':stamp,'volume_m3':'12,000'})
        a,_=parse_reading({'measured_at':'2024-10-27T02:30+02:00','volume_m3':'12'})
        b,_=parse_reading({'measured_at':'2024-10-27T02:30+01:00','volume_m3':'12'})
        self.assertEqual(b-a,3600)

    def test_historical_insert_obeys_both_neighbors_and_duplicates_are_safe(self):
        with tempfile.TemporaryDirectory() as root:
            meter=GasMeter(Path(root)/'db')
            for day,value in ((1,100),(3,120),(2,110)):
                meter.add({'measured_at':f'2024-05-0{day}T12:00','volume_m3':value})
            for stamp,value in (('2024-05-01T11:00',101),('2024-05-02T11:00',121),('2024-05-02T12:00',111)):
                with self.assertRaises(MeterError):meter.add({'measured_at':stamp,'volume_m3':value})
            self.assertEqual(meter.summary()['count'],3)

    def test_routes_only_write_local_meter_data_and_render_learning_page(self):
        with tempfile.TemporaryDirectory() as root:
            app=Flask(__name__,template_folder=str(Path(__file__).parent/'web/templates'))
            service=register_heating_routes(SimpleNamespace(app=app),root)
            service.fetch=lambda _:self.fail('No hardware access')
            client=app.test_client();body={'measured_at':'2024-05-05T12:00','volume_m3':'1234,567'}
            self.assertEqual(client.get('/heizung/lernen').status_code,200)
            self.assertIn(b'Machine Learning',client.get('/heizung').data)
            self.assertEqual(client.post('/api/heating/gas-readings',json=body).status_code,403)
            self.assertEqual(client.post('/api/heating/gas-readings',json=body,headers={'X-Heating-Meter':'1','Origin':'https://foreign.invalid'}).status_code,403)
            self.assertEqual(client.post('/api/heating/gas-readings',data=body,headers={'X-Heating-Meter':'1'}).status_code,403)
            self.assertEqual(client.post('/api/heating/gas-readings',json=body,headers={'X-Heating-Meter':'1'}).status_code,201)
            self.assertEqual(client.post('/api/heating/gas-readings',json=body,headers={'X-Heating-Meter':'1'}).status_code,200)
            client.post('/api/heating/gas-readings',json={**body,'measured_at':'2024-05-06T12:00','volume_m3':'1235,567'},headers={'X-Heating-Meter':'1'})
            summary=client.get('/api/heating/gas-readings').json
            self.assertEqual(summary['count'],2)
            self.assertEqual(summary['latest_interval']['measured_m3'],1)
            self.assertIsNone(summary['latest_interval']['relay_reference']['gas_equivalent_nm3'])
            self.assertEqual(client.delete('/api/heating/gas-readings').status_code,405)
            self.assertFalse(service.observer.status()['can_control'])

    def test_interval_reference_uses_only_observed_relay_coverage(self):
        with tempfile.TemporaryDirectory() as root:
            service=register_heating_routes(SimpleNamespace(app=Flask(__name__)),root)
            service.observer.config={'plant_reference':{'rated_input_hi_kw':22.8,'assumed_hi_kwh_per_nm3':10}}
            with closing(sqlite3.connect(service.db_path)) as db,db:
                for ts in (1000,1060,1120):
                    db.execute('INSERT INTO heating_samples VALUES (?,?)',(ts,json.dumps({'anlage.burner':True,'anlage.burner_stage2':False})))
            ref=service.observer.energy_reference_between(1000,2000)
            self.assertEqual(ref['relay_minutes'],2)
            self.assertEqual(ref['coverage_percent'],12)
            self.assertAlmostEqual(ref['gas_equivalent_nm3'],0.076)


if __name__=='__main__':unittest.main()
