"""Check the actual saved configuration and reject changed route semantics."""
import copy
import pickle
import unittest
from candidate import A, MOVEMENT, install


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.state, cls.forecast = pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())

    def test_only_one_rate_changes(self):
        cfg=copy.deepcopy(self.cfg)
        original=vars(cfg.network).copy()
        before=copy.deepcopy(cfg.network.movement_capacity_by_movement_veh_h)
        r=install(cfg)
        self.assertEqual({k for k,v in vars(cfg.network).items() if v is not original[k]}, {'movement_capacity_by_movement_veh_h'})
        self.assertEqual({k for k,v in before.items() if v!=cfg.network.movement_capacity_by_movement_veh_h[k]}, {MOVEMENT})
        self.assertEqual(r['after_veh_h'],2000.)
        self.assertEqual((cfg.simulation.T_f_sec,cfg.simulation.T_u_sec),(5.,10.))

    def test_changed_receiver_rejected(self):
        cfg=copy.deepcopy(self.cfg)
        cfg.network.urban_movements[MOVEMENT]['receiving_link']='SC12_to_SC6'
        with self.assertRaises(AssertionError): install(cfg)

    def test_other_snapshot_not_silently_given_same_floor(self):
        with self.assertRaises(AssertionError): install(copy.deepcopy(self.cfg),3300)


if __name__=='__main__': unittest.main()
