"""Time refinement preserves commanded service and requested vehicles."""
from pathlib import Path
import sys,copy,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary,LaneResolvedRampBoundary


class RefinementTests(unittest.TestCase):
    def steps(self):
        return [dict(window_start_s=t,window_end_s=t+10,source_demand_vph={'FW_E':1234.},
            ramp_arrival_vph={'meter':3600.,'other':72.},ramp_arrival_profile={'meter':[0.,2.]*5},
            ramp_head_service={'meter':{'service_veh':7.,'mode':'GREEN','green_sec':4}},
            vsl_commands={'FW_E__seg8':80 if t<150 else 60},off_drain_vph={'10643':120.}) for t in (140,150)]

    def test_absent_refinement_keeps_original_objects(self):
        steps=self.steps();self.assertIs(e.refine_boundary_steps(steps,10),steps)

    def test_one_second_totals_and_command_times_are_preserved(self):
        steps=self.steps();before=copy.deepcopy(steps);fine=e.refine_boundary_steps(steps,1)
        self.assertEqual(steps,before);self.assertEqual(len(fine),20)
        self.assertEqual([r['window_start_s'] for r in fine],list(range(140,160)))
        for coarse in steps:
            sub=[r for r in fine if coarse['window_start_s']<=r['window_start_s']<coarse['window_end_s']]
            for r in sub:
                self.assertEqual(r['ramp_head_service'],coarse['ramp_head_service'])
                self.assertEqual(r['vsl_commands'],coarse['vsl_commands'])
                self.assertEqual(r['off_drain_vph'],coarse['off_drain_vph'])
            for ramp,rate in coarse['ramp_arrival_vph'].items():
                self.assertAlmostEqual(sum(r['ramp_arrival_vph'][ramp]/3600 for r in sub),rate*10/3600)
            self.assertAlmostEqual(sum(r['source_demand_vph']['FW_E']/3600 for r in sub),1234.*10/3600)
            self.assertEqual([n for r in sub for n in r['ramp_arrival_profile']['meter']],coarse['ramp_arrival_profile']['meter'])

    def test_invalid_or_inconsistent_boundaries_fail(self):
        for step in (0,3,.5,True):
            with self.subTest(step=step),self.assertRaises(ValueError):e.refine_boundary_steps(self.steps(),step)
        bad=self.steps();bad[0]['ramp_arrival_vph']['meter']=7200.
        with self.assertRaises(ValueError):e.refine_boundary_steps(bad,1)

    def test_partial_intervals_reproduce_the_same_meter_cycle(self):
        spec=dict(connector_id='test',length_m=120.,head_position_m=60.,lanes=2,
                  spacing_m=6.,travel_speed_kmh=36.,time_sec=0.,initial_cohorts=[(60.,0.,1)]*5+[(100.,0.,2)]*3)
        for cls in (PhysicalRampBoundary,LaneResolvedRampBoundary):
            for mode,green in (('OFF',None),('GREEN',4.),('GREEN',1.),('RED',0.)):
                for step in (1,2,5):
                    with self.subTest(cls=cls.__name__,mode=mode,green=green,step=step):
                        opts={'lane_arrival_shares':[.5,.5]} if cls is LaneResolvedRampBoundary else {}
                        a=cls(**spec,**opts);b=cls(**spec,**opts);service=0. if mode=='RED' else 6.
                        kwargs=dict(cycle_sec=10.,service_veh=service,mode=mode,green_sec=green)
                        coarse=a.advance_local_interval(start_sec=0.,duration_sec=10.,receiving_budget_veh=10.,request_arrivals_veh=10.,**kwargs)
                        fine=[b.advance_local_interval(start_sec=t,duration_sec=step,receiving_budget_veh=step,
                            request_arrivals_veh=step,allow_partial_cycle=True,**kwargs) for t in range(0,10,step)]
                        local=[row for r in fine for row in r['local_receipts']]
                        for old,new in zip(coarse['local_receipts'],local):
                            self.assertEqual(old['meter_mode'],new['meter_mode'])
                            for key in ('head_service_veh','accepted_merge_veh','connector_ttt_veh_h','requested_arrivals_veh'):
                                self.assertAlmostEqual(old[key],new[key])
                        self.assertAlmostEqual(coarse['head_service_limit_veh'],sum(r['head_service_limit_veh'] for r in fine))
                        for key,value in coarse['end'].items():
                            if isinstance(value,(int,float)):self.assertAlmostEqual(value,fine[-1]['end'][key])


if __name__=='__main__':unittest.main()
