"""Known destinations, future priors, and shared residual reservations."""
import copy
import json
import math
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from evaluation.controllers import observation_projection as op
from evaluation.controllers import physical_movement_routes as pmr
from evaluation.controllers.vehicle_routes import ATTRIBUTES
from evaluation.controllers.physical_ramp_branches import split_tagged_arrival

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SOURCE='SC1003_to_SC1004'
W='SC1004_N_SC1003_to_W';S='SC1004_N_SC1003_to_S';E='SC1004_N_SC1003_to_E_SC1005'

class NativeRoutes(unittest.TestCase):
    def setUp(self):
        self.f=json.loads((HERE/'fixture900.json').read_bytes())
        self.doc=json.loads((HERE/'contract_test.json').read_bytes())
        specs={m:copy.deepcopy(row['expected_spec']) for m,row in self.doc['sources'][SOURCE]['movements'].items()}
        self.cfg=NS(network=NS(urban_movements=specs,physical_ramp_branches={}),simulation=NS(T_u_sec=1.))
        self.state=NS(time_sec=900.,urban_movement_queue=copy.deepcopy(self.f['queue']),
            local_observation_summary={'projection_diagnostics':{'physical_stock_assignment_by_link':{'46':copy.deepcopy(self.f['projection'])}}},
            urban_arrival_buffer={SOURCE:{int(k):v for k,v in self.f['arrivals'].items()}},
            urban_storage_release_buffer={SOURCE:{int(k):v for k,v in self.f['releases'].items()}})
        self.raw=dict(sim_sec=900.,vehicle_records=dict(complete=True,records=copy.deepcopy(self.f['records']),
            collection_count_before=7,collection_count_after=7,record_count=7,
            capture_sim_sec_before=900.,capture_sim_sec_after=900.,full_network_link_counts={'46':7}),
            vehicle_routes=dict(schema_version='vissim-vehicle-routes-v1',complete=True,source_attributes=ATTRIBUTES,
                records=list(copy.deepcopy(self.f['routes']).values()),record_count=7,
                collection_count_before=7,collection_count_after=7,sim_sec_before=900.,sim_sec_after=900.),
            local_observation={'queue_bins':{'46|any|0':[7,3]}})
        self.adapter=NS(_ARRIVAL_TAU_MOVING_SEC=15.,_ARRIVAL_TAU_STOPPED_SEC=105.,
            _contiguous_stopline_queue=lambda raw,per_lane:{('46','3'):1.,('46','4'):2.})
        self.detectors={'link_to_origins':{'46':[SOURCE],'68':['SC1004_W_out'],'67':['SC1004_S_out'],'56':['SC1004_E_choice']}}
        self.tuning={'urban':{'arrival':{'kinematic_contract':str(HERE/'contract_test.json')},'queue':{'contiguous':True}}}

    def run_projection(self):
        with patch('evaluation.controllers.network_provenance.snapshot_network_sha256',return_value=self.f['network']['sha256']), \
             patch('src.models.urban_queue_model.approach_routing',return_value={SOURCE:[(m,s['beta']) for m,s in self.cfg.network.urban_movements.items()]}):
            return op.initialize_kinematic_arrivals(self.adapter,self.state,self.cfg,self.tuning,self.raw,self.detectors)

    def test_known_routes_keep_four_w_and_three_other_queues(self):
        meta=self.run_projection()['kinematic_arrivals'][SOURCE]
        self.assertEqual(self.state.urban_movement_queue,{W:0.,S:1.,E:2.})
        tags=self.state.gate_initial_route_tags[SOURCE]
        self.assertAlmostEqual(sum(sum(r.values()) for r in tags.values()),4.)
        self.assertTrue(all(set(r)=={W} for r in tags.values()))
        self.assertEqual(meta['known_destination_veh'],7)
        self.assertEqual(self.state.urban_arrival_buffer[SOURCE][915],.5)
        self.assertAlmostEqual(sum(self.state.urban_arrival_buffer[SOURCE].values()),4.5)
        self.assertEqual(self.state.urban_arrival_buffer,self.state.urban_storage_release_buffer)
        # Vehicle2532 is still in lane2, though its known turn leaves lane1.
        self.assertIn(2532,[v['veh_no'] for v in self.raw['vehicle_records']['records'] if v['lane_no']==2])

    def test_tag_consumer_does_not_resplit_known_route(self):
        self.run_projection()
        total=0.
        for step,row in list(self.state.gate_initial_route_tags[SOURCE].items()):
            n=sum(row.values());total+=n
            result=dict(split_tagged_arrival(self.state,self.cfg,SOURCE,step,n,[(W,.1),(S,.8),(E,.1)]))
            self.assertEqual(result,{W:n,S:0.,E:0.})
        self.assertEqual(total,4.)

    def test_missing_route_after_decision_rejected(self):
        self.raw['vehicle_routes']['records'][0].update(route_decision_no=None,route_no=None,route_decision_type=None)
        with self.assertRaisesRegex(op.ProjectionError,'cannot redraw'):self.run_projection()

    def test_before_decision_uses_native_prior_only_for_that_vehicle(self):
        self.raw['vehicle_records']['records'][0]['position_m']=1.
        self.raw['vehicle_routes']['records'][0].update(route_decision_no=None,route_no=None,route_decision_type=None)
        meta=self.run_projection()['kinematic_arrivals'][SOURCE]
        tags=self.state.gate_initial_route_tags[SOURCE]
        totals={m:math.fsum(x.get(m,0.) for x in tags.values()) for m in (W,S,E)}
        self.assertEqual(totals,{W:3.75,S:.125,E:.125})
        self.assertEqual((meta['known_destination_veh'],meta['before_choice_veh']),(6,1))

    def test_native_prior_uses_pinned1125_without_other_parameter_change(self):
        for s in self.cfg.network.urban_movements.values():s['beta']=1/3
        old=copy.deepcopy(self.cfg.network.urban_movements)
        with patch('evaluation.controllers.network_provenance.snapshot_network_sha256',return_value=self.f['network']['sha256']), \
             patch.object(pmr,'snapshot_network_sha256',return_value=self.f['network']['sha256']):
            op.configure_kinematic_queue_projection(self.cfg,self.tuning,self.raw,self.detectors)
        self.assertEqual({m:s['beta'] for m,s in self.cfg.network.urban_movements.items()},{W:.75,S:.125,E:.125})
        for m,s in self.cfg.network.urban_movements.items():
            self.assertEqual({k:v for k,v in s.items() if k!='beta'},{k:v for k,v in old[m].items() if k!='beta'})

    def test_changed_receiver_or_stock_rejected(self):
        self.detectors['link_to_origins']['46']=['wrong']
        with self.assertRaises(op.ProjectionError):self.run_projection()

    def test_disabled_no_change(self):
        old=copy.deepcopy(vars(self.state));self.tuning={}
        self.assertEqual(self.run_projection(),{});self.assertEqual(old,vars(self.state))

if __name__=='__main__':unittest.main()
