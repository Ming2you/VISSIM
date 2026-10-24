"""A terminal-road ETA repair must preserve the rest of its physical origin."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import patch

from evaluation.controllers.observation_projection import initialize_kinematic_arrivals, ProjectionError
from evaluation.controllers.physical_ramp_branches import split_tagged_arrival


class PartialKinematicCohortTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        folder=Path(tmp.name)
        net=folder/'network.inpx'
        net.write_text('<network><links><link no="1"/><link no="2"><fromLinkEndPt lane="1 1" pos="100"/><lanes><lane/></lanes></link><link no="3"><fromLinkEndPt lane="1 2" pos="100"/><lanes><lane/></lanes></link></links></network>')
        digest=hashlib.sha256(net.read_bytes()).hexdigest()
        moves={m:dict(origin='corridor',beta=.5,kind='internal') for m in ('through','left')}
        self.doc=dict(schema='kinematic-urban-arrival/v1',network=dict(path=str(net),sha256=digest),speed_floor_kph=20.,
            sources={'corridor':dict(link='1',movements={m:dict(connector=c,expected_spec=moves[m])
                for m,c in [('through','2'),('left','3')]})})
        self.contract=folder/'contract.json'
        self.cfg=NS(network=NS(urban_movements=moves,physical_ramp_branches={},urban_boundary_travel_time_sec={'other':90.}),simulation=NS(T_u_sec=1.))
        self.tuning={'urban':{'arrival':{'kinematic_contract':str(self.contract)}}}
        self.raw={'vehicle_records':{'complete':True,'records':[
            dict(veh_no=1,link_no=1,lane_no=1,position_m=99.,speed_kph=0.,stopped=True),
            dict(veh_no=2,link_no=1,lane_no=1,position_m=95.,speed_kph=0.,stopped=True),
            dict(veh_no=3,link_no=1,lane_no=2,position_m=25.,speed_kph=20.,stopped=False),
            dict(veh_no=4,link_no=1,lane_no=1,position_m=0.,speed_kph=36.,stopped=False)]}}
        self.state=NS(time_sec=1000.,urban_movement_queue={'through':7.,'left':0.,'unrelated':9.},
            urban_arrival_buffer={'corridor':{1015:5.},'other':{1040:3.}},
            urban_storage_release_buffer={'corridor':{1015:5.},'other':{1040:3.}},
            local_observation_summary={'projection_diagnostics':{'physical_stock_assignment_by_link':{
                '1':{'storage:corridor':2.,'movement:through':2.}}}})
        self.adapter=NS(_ARRIVAL_TAU_MOVING_SEC=15.,_ARRIVAL_TAU_STOPPED_SEC=105.,
            _contiguous_stopline_queue=lambda raw,per_lane:{('1','1'):2.})
        self.detectors={'link_to_origins':{'1':['corridor']}}
        p=patch('evaluation.controllers.network_provenance.snapshot_network_sha256',return_value=digest)
        p.start();self.addCleanup(p.stop)

    def run_projection(self):
        self.contract.write_text(json.dumps(self.doc))
        return initialize_kinematic_arrivals(self.adapter,self.state,self.cfg,self.tuning,self.raw,self.detectors)

    def test_internal_partial_cohort_keeps_upstream_stock_reservations_and_future_travel(self):
        before=sum(self.state.urban_movement_queue.values())+sum(self.state.urban_arrival_buffer['corridor'].values())
        report=self.run_projection()['kinematic_arrivals']['corridor']
        self.assertEqual(self.state.urban_arrival_buffer['corridor'],{1015:3.,1014:1.,1010:1.})
        self.assertEqual(self.state.urban_arrival_buffer,self.state.urban_storage_release_buffer)
        self.assertEqual(self.cfg.network.urban_boundary_travel_time_sec,{'other':90.})
        self.assertEqual(self.state.urban_arrival_buffer['other'],{1040:3.})
        self.assertEqual(self.state.urban_movement_queue,{'through':7.,'left':0.,'unrelated':9.})
        after=sum(self.state.urban_movement_queue.values())+sum(self.state.urban_arrival_buffer['corridor'].values())
        self.assertEqual(before,after)
        self.assertIsNone(report['gate_travel_sec'])
        # Only the observed cohort is tagged. Concurrent upstream arrivals
        # retain their routing; tags cannot create an additional vehicle.
        split=dict(split_tagged_arrival(self.state,self.cfg,'corridor',1014,3.,[('through',.5),('left',.5)]))
        self.assertEqual(split,{'through':1.,'left':2.})

    def test_existing_boundary_source_still_sets_geometry_delay(self):
        for m in self.cfg.network.urban_movements.values():m['kind']='boundary_in'
        result=self.run_projection()['kinematic_arrivals']['corridor']
        self.assertGreater(result['gate_travel_sec'],0.)
        self.assertEqual(self.cfg.network.urban_boundary_travel_time_sec['corridor'],result['gate_travel_sec'])

    def test_already_owned_cohort_fails_instead_of_double_seeding(self):
        self.state.gate_initial_route_tags={'corridor':{1014:{'left':1.}}}
        with self.assertRaises(ProjectionError):self.run_projection()

    def test_missing_original_reservation_is_not_recreated(self):
        self.state.urban_arrival_buffer['corridor']={1015:1.}
        self.state.urban_storage_release_buffer['corridor']={1015:1.}
        with self.assertRaises(ProjectionError):self.run_projection()


if __name__=='__main__':unittest.main()
