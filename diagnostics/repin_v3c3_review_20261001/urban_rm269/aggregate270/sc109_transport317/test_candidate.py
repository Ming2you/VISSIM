from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import copy,pickle,unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317 import candidate as c

class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.state,_=pickle.loads((c.HERE.parent/'citysplit287/forecast2400/initial.pickle').read_bytes())

    def test_geometry_covers_all_sources_from_current_network(self):
        g=c.geometry(self.cfg)
        self.assertEqual(set(g['sources']),c.EXPECTED)
        self.assertAlmostEqual(g['lane_factor'],3.661468454173944)
        self.assertTrue(all(500<x['distance_m']<650 for x in g['sources'].values()))
        self.assertLess(g['sources']['SC108_W_to_E_SC109']['distance_m'],g['sources']['SC108_W_SC107_to_E_SC109']['distance_m'])
        self.assertTrue(all(x['segments'][0][0]['start']>0 for x in g['sources'].values()))

    def test_install_preserves_all_current_stock_and_calendars(self):
        cfg=copy.deepcopy(self.cfg);s=copy.deepcopy(self.state);before=pickle.dumps(s,protocol=5)
        g=c.install(cfg,s)
        self.assertEqual(before,pickle.dumps(s,protocol=5))
        self.assertAlmostEqual(g['current_physical_speed_kph'],38.765778707317075)
        self.assertTrue(all(50<=v<=70 for v in g['delay_sec'].values()))
        with self.assertRaises(ValueError):c.install(cfg,s)

    def test_time_units_and_ceil(self):
        self.assertEqual(c.steps(500,36,50,10),5)
        self.assertEqual(c.steps(501,36,50,10),6)
        self.assertEqual(c.steps(500,36,50,5),10)
        with self.assertRaises(ValueError):c.steps(500,float('nan'),50,10)

    def test_receipt_schedules_accepted_mass_once_and_restores(self):
        from evaluation.controllers import urban_flow_accounting as ufa
        cfg=copy.deepcopy(self.cfg);g=c.install(cfg,copy.deepcopy(self.state));m='SC108_W_SC107_to_E_SC109'
        states=[NS(urban_arrival_buffer={},urban_storage_release_buffer={},urban_link_speed_kph={c.TARGET:self.state.urban_link_speed_kph[c.TARGET]},urban_link_storage={c.TARGET:n}) for n in (10,400)]
        original=ufa._receive_corridor
        with patch.object(ufa,'_receive_corridor',return_value=False) as old,patch('evaluation.controllers.omega_distance.record_ordinary_movement') as distance:
            with c.enabled() as rows:
                for s in states:self.assertTrue(ufa._receive_corridor(s,cfg,m,3.25,240))
                self.assertEqual(rows[0]['due_sec'],rows[1]['due_sec'])
                self.assertEqual(states[0].urban_arrival_buffer,states[1].urban_arrival_buffer)
                self.assertEqual(states[0].urban_arrival_buffer,states[0].urban_storage_release_buffer)
                self.assertAlmostEqual(sum(states[0].urban_arrival_buffer[c.TARGET].values()),3.25)
                self.assertEqual(distance.call_count,2)
            self.assertIs(ufa._receive_corridor,old)
        self.assertIs(ufa._receive_corridor,original)

    def test_other_source_is_forwarded(self):
        from evaluation.controllers import urban_flow_accounting as ufa
        cfg=copy.deepcopy(self.cfg);c.install(cfg,copy.deepcopy(self.state))
        with patch.object(ufa,'_receive_corridor',return_value=False) as old:
            with c.enabled() as rows:
                self.assertFalse(ufa._receive_corridor(self.state,cfg,'SC107_W_SC1004_to_E_SC108',2,240))
                self.assertFalse(rows)
            self.assertEqual(old.call_count,1)

    def test_existing_owner_rejected_and_restored_on_failure(self):
        from evaluation.controllers import urban_flow_accounting as ufa
        cfg=copy.deepcopy(self.cfg);c.install(cfg,copy.deepcopy(self.state))
        with patch.object(ufa,'_receive_corridor',return_value=True) as old:
            with self.assertRaises(ValueError):
                with c.enabled():ufa._receive_corridor(self.state,cfg,'SC108_W_SC107_to_E_SC109',2,240)
            self.assertIs(ufa._receive_corridor,old)

if __name__=='__main__':unittest.main()
