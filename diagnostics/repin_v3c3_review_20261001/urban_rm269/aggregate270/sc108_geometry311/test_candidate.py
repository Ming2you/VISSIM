import pickle
import unittest
from pathlib import Path
from candidate import geometry,install,delay_steps,clock,TARGET

class Geometry(unittest.TestCase):
    def setUp(self):
        self.cfg,self.state,_=pickle.loads((Path(__file__).resolve().parent.parent/'citysplit287/forecast2400/initial.pickle').read_bytes())

    def test_physical_capacity_preserves_observed_stock_and_pending_arrivals(self):
        result=install(self.cfg,self.state)
        self.assertAlmostEqual(result['new_capacity_veh'],(94.77788130622324+95.05020601926469)/6)
        self.assertAlmostEqual(result['occupied_veh'],6.)
        self.assertTrue(result['initial_stock_and_due_times_preserved'])

    def test_clock_uses_distance_not_lane_summed_free_space_and_restores(self):
        from src.models import urban_queue_model as uqm
        original=uqm._link_delay_steps
        self.assertEqual(original(self.state,self.cfg,TARGET),12)
        g=geometry(self.cfg)
        self.assertEqual(delay_steps(self.state,self.cfg,g),2)
        other=original(self.state,self.cfg,'SC107_to_SC108')
        with clock(self.cfg):
            self.assertEqual(uqm._link_delay_steps(self.state,self.cfg,TARGET),2)
            self.assertEqual(uqm._link_delay_steps(self.state,self.cfg,'SC107_to_SC108'),other)
        self.assertIs(uqm._link_delay_steps,original)

    def test_overfull_observation_is_not_silently_clipped(self):
        self.state.urban_link_storage[TARGET]=self.cfg.network.urban_link_storage_veh[TARGET]-40
        with self.assertRaises(ValueError):install(self.cfg,self.state)

if __name__=='__main__':unittest.main()
