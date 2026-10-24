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

    def test_link71_excess_moves_into_the_feeding_10641_lane(self):
        # V5 sdmpc31_v2_s31 1950 s: 14 vehicles on 71 lane 3 against 81.24/6 = 13.5 storage
        state={'time_s':1950,'vehicles':[vehicle(i,71,1.+5.8*i,lane=3) for i in range(14)]}
        before=copy.deepcopy(state);moved,proof=project(state,NETWORK,6.)
        self.assertEqual(state,before)
        self.assertEqual([(m['vehicle'],m['source_link'],m['source_lane'],m['target_link'],m['lane'])
                          for m in proof['moves']],[(0,71,3,10641,2)])
        self.assertEqual(sum(v['link']==71 and v['lane']==3 for v in moved['vehicles']),13)
        landed=[v for v in moved['vehicles'] if v['link']==10641]
        self.assertEqual([(v['vehicle'],v['lane']) for v in landed],[(0,2)])
        self.assertAlmostEqual(landed[0]['position_m'],proof['moves'][0]['target_position_m'])
        self.assertFalse(proof['capacities_changed'])

    def test_link71_excess_cascades_through_a_full_10641_into_126(self):
        state={'time_s':1950,'vehicles':[vehicle(i,71,1.+5.8*i,lane=3) for i in range(14)]
               +[vehicle(50+i,10641,5.+6*i,lane=2) for i in range(7)]}
        moved,proof=project(state,NETWORK,6.)
        self.assertEqual([(m['vehicle'],m['source_link'],m['target_link']) for m in proof['moves']],
                         [(0,71,10641),(50,10641,126)])
        count=lambda link,lane:sum(v['link']==link and v['lane']==lane for v in moved['vehicles'])
        self.assertEqual((count(71,3),count(10641,2),count(126,2)),(13,7,1))
        self.assertEqual(len(moved['vehicles']),len(state['vehicles']))

    def test_126_lane_excess_moves_sideways(self):
        # R-obs sdmpc31_v3b_nc_s31 3150 s: 26 vehicles on 126 lane 2 against 152.46/6 = 25.4, 6 on lane 1
        state={'time_s':3150,'vehicles':[vehicle(i,126,1.+5.8*i,lane=2) for i in range(26)]
               +[vehicle(100+i,126,100.+6*i,lane=1) for i in range(6)]}
        before=copy.deepcopy(state);moved,proof=project(state,NETWORK,6.)
        self.assertEqual(state,before)
        self.assertEqual([(m['vehicle'],m['source_link'],m['source_lane'],m['target_link'],m['lane'])
                          for m in proof['moves']],[(0,126,2,126,1)])
        count=lambda link,lane:sum(v['link']==link and v['lane']==lane for v in moved['vehicles'])
        self.assertEqual((count(126,1),count(126,2)),(7,25))
        self.assertEqual(moved['vehicles'][0]['position_m'],1.)
        self.assertFalse(proof['capacities_changed'])

    def test_10641_excess_into_a_full_126_lane_balances_sideways(self):
        state={'time_s':1950,'vehicles':[vehicle(i,10641,5.+5.4*i) for i in range(8)]
               +[vehicle(100+i,126,1.+6*i) for i in range(25)]}
        moved,proof=project(state,NETWORK,6.)
        self.assertEqual([(m['vehicle'],m['source_link'],m['target_link'],m['lane']) for m in proof['moves']],
                         [(0,10641,126,2),(100,126,126,1)])
        count=lambda link,lane:sum(v['link']==link and v['lane']==lane for v in moved['vehicles'])
        self.assertEqual((count(10641,2),count(126,1),count(126,2)),(7,1,25))

    def test_both_126_lanes_full_is_still_failure(self):
        state={'time_s':3150,'vehicles':[vehicle(i,126,1.+5.8*i,lane=2) for i in range(26)]
               +[vehicle(100+i,126,1.+6*i,lane=1) for i in range(25)]}
        with self.assertRaisesRegex(ValueError,'no physical upstream'):
            project(state,NETWORK,6.)

    def test_real_v5_1950_frame_keeps_every_local_vehicle(self):
        path=Path(r'D:\VISSIM_runs\20260924_sdmpc31\sdmpc31_v2_s31\decisions_sdmpc31_v2_s31\lane_observations\frame_001950.json')
        if not path.exists():
            self.skipTest('V5 1950 s frame not on this machine')
        raw=json.loads(path.read_text(encoding='utf-16'))
        rows=[dict(vehicle=v[0],link=v[1],lane=v[2],position_m=v[3],speed_kmh=v[4],length_m=v[5])
              for v in raw['vehicles'] if v[1] in (126,10641,71)]
        moved,proof=project({'time_s':1950,'vehicles':rows},NETWORK,6.)
        self.assertEqual(len(moved['vehicles']),len(rows))
        self.assertEqual([(m['source_link'],m.get('source_lane')) for m in proof['moves'] if m['source_link']==71],[(71,3)])
        count=lambda link,lane:sum(v['link']==link and v['lane']==lane for v in moved['vehicles'])
        self.assertEqual(count(71,3),13)
        self.assertTrue(count(10641,1)<=7 and count(10641,2)<=7)   # floor(45.3/6); any excess went on into 126
        self.assertEqual(sorted(v['vehicle'] for v in moved['vehicles']),sorted(r['vehicle'] for r in rows))

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
