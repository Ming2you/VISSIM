from pathlib import Path
import copy,json,unittest
from types import SimpleNamespace
from unittest.mock import patch
from evaluation.controllers.lane_initial_projection import project
ROOT=Path(__file__).resolve().parents[1]
NETWORK=ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2/source_dsd/baseline.inpx'

def vehicle(no,link,pos,lane=2):
    return dict(vehicle=no,link=link,lane=lane,position_m=pos,connector=10634,
                route_decision=1140,route_number=1,speed_kmh=0.,length_m=4.1)

class InitialProjectionTests(unittest.TestCase):
    def test_offramp_landing_only_normalizes_roundoff(self):
        from evaluation.controllers.lane_offramp_runtime import LaneOfframpRuntime
        model=LaneOfframpRuntime.__new__(LaneOfframpRuntime)
        model.descriptions={'test':{'storage':'store','connector':'7','road':'FW_W'}}
        port=SimpleNamespace(stock=0.)
        port.accept=lambda time,amount:setattr(port,'stock',port.stock+amount)
        model.ports={'test':port}
        model.membership={'7':True}
        state=SimpleNamespace(urban_link_storage={'store':.1})
        cfg=SimpleNamespace(network=SimpleNamespace(urban_link_storage_veh={'store':.1}))
        with patch('evaluation.controllers.control_area_objective.get_ledger',return_value=SimpleNamespace(captures_response=False,complete_constraint_coverage=lambda scope:None)), \
             patch('evaluation.controllers.control_area_objective.emit_transfer'):
            model.land(state,cfg,1,{'test':.10000000000000002*3600},{})
            self.assertEqual(state.urban_link_storage['store'],0.)
            state.urban_link_storage['store']=.1
            with self.assertRaises(ArithmeticError):
                model.land(state,cfg,1,{'test':.10000001*3600},{})

    def test_underfull_is_identical(self):
        state={'time_s':1950,'vehicles':[vehicle(i,10641,5.+6*i) for i in range(7)]}
        moved,proof=project(state,NETWORK,6.)
        self.assertEqual(moved,state);self.assertEqual(proof['moves'],[])

    def test_overfull_preserves_labels_and_moves_only_upstreammost(self):
        state={'time_s':1950,'vehicles':[vehicle(i,10641,5.+5.4*i) for i in range(8)]}
        before=copy.deepcopy(state);moved,proof=project(state,NETWORK,6.)
        self.assertEqual(state,before)
        self.assertEqual(len(proof['moves']),1)
        self.assertEqual(proof['moves'][0]['vehicle'],0)
        self.assertEqual(sum(v['link']==10641 for v in moved['vehicles']),7)
        self.assertEqual(sum(v['link']==126 for v in moved['vehicles']),1)
        for original,projected in zip(state['vehicles'],moved['vehicles']):
            for key in ('vehicle','lane','connector','route_decision','route_number','length_m'):
                self.assertEqual(original[key],projected[key])
        self.assertFalse(proof['capacities_changed'])

    def test_no_space_is_still_failure(self):
        state={'time_s':1950,'vehicles':[vehicle(i,10641,5.+5.4*i) for i in range(8)]
               +[vehicle(100+i,126,float(i)) for i in range(1000)]}
        with self.assertRaisesRegex(ValueError,'no physical upstream'):
            project(state,NETWORK,6.)

    def test_real_1950_observation_keeps_all_47_local_vehicles(self):
        path=ROOT.parent/'sdmpc-lane-plant-20260921/evaluation/runs/lane_native_nc2850_s13_v3/decisions_lane_native_nc2850_s13_v3/lane_observations/frame_001950.json'
        raw=json.loads(path.read_text(encoding='utf-16'))
        rows=[dict(vehicle=v[0],link=v[1],lane=v[2],position_m=v[3],speed_kmh=v[4],length_m=v[5])
              for v in raw['vehicles'] if v[1] in (126,10641,71)]
        moved,proof=project({'time_s':1950,'vehicles':rows},NETWORK,6.)
        self.assertEqual(len(moved['vehicles']),47)
        self.assertEqual([r['vehicle'] for r in proof['moves']],[9277])
        self.assertAlmostEqual(proof['moves'][0]['backward_boundary_distance_m'],5.19451475226118)

if __name__=='__main__':unittest.main()
