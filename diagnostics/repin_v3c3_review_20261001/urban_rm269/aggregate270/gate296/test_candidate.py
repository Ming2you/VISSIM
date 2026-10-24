import copy,json,pickle,unittest
from pathlib import Path
from candidate import step_gate,geometry,installed
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];A=HERE.parent
class GateTests(unittest.TestCase):
    def test_red_holds_and_green_caps_with_conservation(self):
        d=dict(pending={(0,3):20.},ready={},received=20.,discharged=0.,last_step=-1,history=[])
        release,r=step_gate(d,0,0.,5600.,10.)
        self.assertEqual(sum(release.values()),0.)
        self.assertEqual(r['remaining_ready'],20.)
        release,r=step_gate(d,1,10.,5600.,10.)
        self.assertAlmostEqual(sum(release.values()),5600/360.)
        self.assertTrue(r['positive_green_capacity_binding'])
        copied=copy.deepcopy(d)
        release,r=step_gate(copied,2,10.,5600.,10.)
        self.assertAlmostEqual(copied['discharged'],20.)
        self.assertAlmostEqual(sum(copied['pending'].values())+sum(copied['ready'].values()),0.)
        self.assertNotEqual(copied['last_step'],d['last_step'])
    def test_no_future_arrival_and_duplicate_tick(self):
        d=dict(pending={(2,3):5.},ready={},received=5.,discharged=0.,last_step=-1,history=[])
        release,r=step_gate(d,0,10.,5600.,10.)
        self.assertEqual(r['discharged'],0.)
        with self.assertRaises(AssertionError):step_gate(d,0,10.,5600.,10.)
    def test_geometry_clock_and_disabled_default(self):
        from plant.src.vissim_strict.signal_program import parse_sig
        from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
        cfg,state,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
        self.assertIsNone(getattr(state,'_omega_travel_reservations',None))
        geom=geometry(ROOT,cfg);g=geom['gate'];p=parse_sig(g['sig_file']['path'],g['program_no'])
        self.assertEqual(g['lanes'],4)
        self.assertEqual(g['nominal_service_veh_h'],5600.)
        self.assertEqual(_union_green_overlap(p,('8',),2560,2570,g['controller_offset_sec']),0.)
        self.assertEqual(_union_green_overlap(p,('8',),2600,2610,g['controller_offset_sec']),10.)
        for r in geom['sources'].values():
            self.assertAlmostEqual(r['pre_gate_distance_m']+r['post_gate_distance_m'],r['distance_m'])
        with installed(cfg,None,None) as receipts:self.assertEqual(receipts,[])
    def test_hook_restoration_after_error(self):
        from evaluation.controllers import urban_flow_accounting as u,native_internal_input as n,route_choice_corridor as r
        cfg,_,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes());g=geometry(ROOT,cfg)
        old=(u._receive_corridor,n.advance,r.advance)
        with self.assertRaises(RuntimeError):
            with installed(cfg,'aggregate_sc10_native_calendar',g):
                self.assertNotEqual(old,(u._receive_corridor,n.advance,r.advance))
                raise RuntimeError('test cleanup')
        self.assertEqual(old,(u._receive_corridor,n.advance,r.advance))
if __name__=='__main__':unittest.main()
