import copy
import pickle
import unittest
from pathlib import Path
from candidate import install,MOVEMENT

class ServiceFloor(unittest.TestCase):
    def setUp(self):
        self.cfg,_,_=pickle.loads((Path(__file__).resolve().parent.parent/'citysplit287/forecast2400/initial.pickle').read_bytes())

    def test_changes_only_supported_rate_and_preserves_higher_estimate(self):
        before=copy.deepcopy(vars(self.cfg.network));installed=install(self.cfg,2400)
        self.assertEqual({k for k in before if before[k]!=vars(self.cfg.network)[k]}, {'movement_capacity_by_movement_veh_h'})
        rates=self.cfg.network.movement_capacity_by_movement_veh_h
        self.assertEqual({k for k in rates if rates[k]!=before['movement_capacity_by_movement_veh_h'][k]}, {MOVEMENT})
        self.assertGreater(installed['after_veh_h'],installed['before_veh_h'])
        rates[MOVEMENT]=2200.
        self.assertEqual(install(self.cfg,3300)['after_veh_h'],2200.)

    def test_future_observations_rejected(self):
        with self.assertRaises(AssertionError): install(self.cfg,2250)

    def test_other_receiving_route_rejected(self):
        self.cfg.network.urban_movements[MOVEMENT]['receiving_link']='SC108_to_SC7'
        with self.assertRaises(AssertionError): install(self.cfg,2400)

if __name__=='__main__':unittest.main()
