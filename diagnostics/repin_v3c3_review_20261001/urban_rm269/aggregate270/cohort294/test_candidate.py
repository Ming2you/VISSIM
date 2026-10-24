import copy,hashlib,json,pickle,unittest
from pathlib import Path
from candidate import eta_steps,initialize
HERE=Path(__file__).resolve().parent
A=HERE.parent;ROOT=HERE.parents[4]
class CurrentCohortTests(unittest.TestCase):
    def test_time_units_and_bounds(self):
        self.assertEqual(eta_steps(100.,36.,0.,10.),1)
        self.assertEqual(eta_steps(100.,0.,0.,10.),2)
        self.assertEqual(eta_steps(0.,0.,0.,10.),1)
        for args in [(-1.,10.,0.,10.),(100.,-1.,0.,10.),(10.,1.,0.,0.),(float('nan'),1.,0.,10.)]:
            with self.assertRaises(ValueError):eta_steps(*args)
    def test_disabled_is_noop(self):
        marker=object()
        self.assertEqual(initialize(None,marker,None,None,None,None),{'enabled':False})
    def test_current_mass_ownership_and_other_reservations(self):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        cfg,state,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
        raw=json.loads(Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29/state_002400.json').read_bytes())
        geom=json.loads((A/'sourcepath292/forecast2400_r3/geometry.json').read_bytes())
        old=copy.deepcopy(state)
        result=initialize(adapter,state,cfg,raw,geom,'current_residual_geometry_u7')
        self.assertEqual(result['physical_vehicles'],82)
        self.assertEqual(result['residual_vehicles'],64)
        self.assertEqual(result['unchanged_ready_vehicles'],18)
        for field in ('urban_arrival_buffer','urban_storage_release_buffer','gate_initial_route_tags'):
            drop=lambda v:{k:n for k,n in getattr(v,field,{}).items() if k!='SC12_to_SC6'}
            self.assertEqual(drop(old),drop(state))
        self.assertEqual(old.urban_movement_queue,state.urban_movement_queue)
        self.assertTrue(result['initial_inventory_unchanged'])
        with self.assertRaises(AssertionError):initialize(adapter,state,cfg,raw,geom,'current_residual_geometry_u7')
if __name__=='__main__':unittest.main()
