"""Distance is movement within Omega and the horizon, not a departure reward."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import tempfile
import xml.etree.ElementTree as ET

from evaluation.controllers import omega_distance as distance
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary, LaneResolvedRampBoundary


def ramp(cls=PhysicalRampBoundary, **changes):
    spec = dict(connector_id='12', length_m=100., head_position_m=40.,
                lanes=1, spacing_m=5., travel_speed_kmh=36.,
                time_sec=20., initial_cohorts=((20., 0., 1), (40., 0., 1),
                                             (95., 36., 1), (100., 0., 1)))
    spec.update(changes)
    return cls(**spec)


class OmegaDistanceTests(unittest.TestCase):
    def test_boundary_gate_clips_actual_path_to_omega_and_horizon(self):
        observer=distance.TravelReservations(10.,20.,{'outside':False,'inside':True})
        observer.ordinary_catalog={'boundary_paths':{'gate':[[
            {'link':'outside','start':0.,'stop':100.},
            {'link':'inside','start':0.,'stop':100.}]]},'boundary_errors':{}}
        state=NS(_omega_travel_reservations=observer)
        cfg=NS(simulation=NS(T_u_sec=1.))
        distance.record_boundary_gate(state,cfg,'gate',2.,10.,30.)
        self.assertEqual(observer.by_provider_stock[('boundary_gate','transit:gate:gate')],0.)
        distance.record_boundary_gate(state,cfg,'gate',2.,10.,20.)
        self.assertAlmostEqual(observer.by_provider_stock[('boundary_gate','transit:gate:gate')],.2)
        self.assertEqual(observer.reservation_counts['boundary_gate'],2)

    def test_active_unmapped_boundary_is_not_silently_zero(self):
        observer=distance.TravelReservations(0.,10.,{})
        observer.ordinary_catalog={'boundary_paths':{},'boundary_errors':{'missing':'unmapped'}}
        state=NS(_omega_travel_reservations=observer);cfg=NS(simulation=NS(T_u_sec=1.))
        distance.record_boundary_gate(state,cfg,'missing',0.,0.,5.)
        with self.assertRaises(distance.DistanceCoverageError):
            distance.record_boundary_gate(state,cfg,'missing',1.,0.,5.)

    def test_local_initial_seed_uses_existing_eta_and_no_extra_population(self):
        local=NS(origin='s',initial_travel_paths=[dict(due=10,vehicles=1.,
            segments=[dict(link='a',start=10.,stop=60.)])])
        observer=distance.TravelReservations(0.,5.,{'a':True})
        state=NS(time_sec=0.,lane_urban_runtime=local,urban_storage_release_buffer={'s':{10:1.}},
                 _omega_travel_reservations=observer)
        cfg=NS(simulation=NS(T_u_sec=1.))
        self.assertEqual(distance.seed_local_upstream(state,cfg),1)
        self.assertAlmostEqual(observer.by_provider_stock['local_upstream','storage:s'],.025)
        self.assertEqual(state.urban_storage_release_buffer,{'s':{10:1.}})
        state.urban_storage_release_buffer['s'][10]=2.
        with self.assertRaises(distance.DistanceCoverageError):distance.seed_local_upstream(state,cfg)

    def test_local_future_travel_is_clipped_before_lane_cell_admission(self):
        from evaluation.controllers.lane_urban_runtime import LaneUrbanRuntime
        local=NS(origin='s',future_shares={'city':{'m':1.}},exits_by_movement={'m':10634},
            entry_paths={'city':100.},entry_segments={'city':[dict(link='a',start=0.,stop=100.)]},
            port=NS(urban=NS(speed=10.)),arrival_tags={})
        observer=distance.TravelReservations(0.,5.,{'a':True})
        state=NS(urban_arrival_buffer={},urban_storage_release_buffer={},_omega_travel_reservations=observer)
        cfg=NS(simulation=NS(T_u_sec=1.))
        due=LaneUrbanRuntime.schedule_upstream(local,state,cfg,0,2.,entry='city')
        self.assertEqual(due,10)
        self.assertEqual(state.urban_arrival_buffer,{'s':{10:2.}})
        self.assertAlmostEqual(observer.by_provider_stock['local_upstream','storage:s'],.1)

    def test_cumulative_interior_moves_before_exit_and_stops_at_queue(self):
        from evaluation.controllers.physical_urban_transport import CumulativeLane
        lane=CumulativeLane(20.,100.,36.,[(20.,36.,5.)],0.,5.)
        for t in range(30):lane.release(float(t),1.,0.)
        before=copy.deepcopy(vars(lane))
        # The jam-density initial packet releases at qmax=2/3 veh/s, not
        # as a rigid car travelling immediately at free speed. At t3 its
        # centroid is42.5m vs initial17.5m:25 vehicle-metres of travel.
        self.assertAlmostEqual(distance.cumulative_lane_distance(lane,0.,3.,'a',{'a':True}),.025,places=4)
        # It queues at [95,100]m:80m displacement, despite no outlet discharge.
        self.assertAlmostEqual(distance.cumulative_lane_distance(lane,0.,30.,'a',{'a':True}),.08,places=5)
        self.assertAlmostEqual(distance.cumulative_lane_distance(lane,20.,30.,'a',{'a':True}),0.,places=8)
        self.assertEqual(vars(lane).keys(),before.keys())
        self.assertEqual(lane.departure_history,before['departure_history'])

    def test_cumulative_full_jam_does_not_earn_free_speed_distance(self):
        from evaluation.controllers.physical_urban_transport import CumulativeLane
        lane=CumulativeLane(20.,100.,36.,[(float(x),0.,5.) for x in range(5,101,5)],0.,5.)
        for t in range(10):lane.release(float(t),1.,0.)
        self.assertAlmostEqual(distance.cumulative_lane_distance(lane,0.,10.,'a',{'a':True}),0.,places=10)
        self.assertEqual(distance.cumulative_lane_distance(lane,0.,10.,'a',{'a':False}),0.)
        with self.assertRaises(distance.DistanceCoverageError):
            distance.cumulative_lane_distance(lane,0.,10.,'a',{})

    def test_cumulative_distance_window_additivity_and_quadrature(self):
        from evaluation.controllers.physical_urban_transport import CumulativeLane
        lane=CumulativeLane(20.,100.,36.,[(20.,36.,5.)],0.,5.)
        for t in range(20):lane.release(float(t),1.,3600.)
        area={'a':[(10.,90.)]}
        full=distance.cumulative_lane_distance(lane,0.,20.,'a',area)
        self.assertAlmostEqual(full,sum(distance.cumulative_lane_distance(lane,a,b,'a',area)
            for a,b in ((0.,3.),(3.,20.))),places=10)
        self.assertAlmostEqual(full,.0725,places=4)
        fine=distance.cumulative_lane_distance(lane,0.,20.,'a',area,spatial_step_m=1.)
        self.assertLess(abs(full-fine),2e-5)

    def test_geometric_family_retains_bounds_without_new_vehicle_split(self):
        r=distance.TravelReservations(0.,5.,{'a':True})
        paths=[[dict(link='a',start=0.,stop=100.)],[dict(link='a',start=0.,stop=102.)]]
        value=r.reserve_family('ordinary','storage:s',paths,2.,0.,10.)
        self.assertAlmostEqual(value,.101)
        self.assertEqual(r.geometry_bounds_by_stock['ordinary','storage:s'],[.1,.102])
        self.assertEqual(r.reservation_counts['ordinary'],1)
        self.assertAlmostEqual(r.by_provider_stock['ordinary','storage:s'],.101)

    def test_ordinary_positive_unresolved_path_is_not_zero_fallback(self):
        observer=distance.TravelReservations(0.,10.,{})
        observer.ordinary_catalog=dict(path_families={},errors={'m':['No physical path']})
        state=NS(_omega_travel_reservations=observer)
        cfg=NS(network=NS(urban_movements={'m':dict(receiving_link='s')}),simulation=NS(T_u_sec=1.))
        distance.record_ordinary_movement(state,cfg,'m',0.,0.,5.)
        with self.assertRaises(distance.DistanceCoverageError):
            distance.record_ordinary_movement(state,cfg,'m',1.,0.,5.)

    def test_ordinary_path_stops_at_next_head_and_includes_turn_connector(self):
        root=ET.Element('network'); links=ET.SubElement(root,'links')
        for key,length,connection in [('a',100.,None),('c',10.,('a',100.,'b',0.)),
                                      ('b',200.,None),('d',12.,('b',200.,'z',0.)),('z',100.,None)]:
            node=ET.SubElement(links,'link',no=key)
            points=ET.SubElement(ET.SubElement(node,'geometry'),'linkPolyPts')
            for pos in (0.,length):ET.SubElement(points,'linkPolyPoint',x=str(pos),y='0',z='0')
            if connection:
                source,sp,target,tp=connection
                ET.SubElement(node,'fromLinkEndPt',lane=source+' 1',pos=str(sp))
                ET.SubElement(node,'toLinkEndPt',lane=target+' 1',pos=str(tp))
        heads=ET.SubElement(root,'signalHeads')
        ET.SubElement(heads,'signalHead',lane='a 1',sg='1 1',pos='90')
        ET.SubElement(heads,'signalHead',lane='b 1',sg='2 1',pos='180')
        def turn(a,c,b):return dict(from_link=a,connector=c,to_link=b,source_evidence=dict(canonical_approach_leg=True))
        net=NS(urban_movements={'m':dict(origin='u',receiving_link='v',signal='SC1'),
                               'n':dict(origin='v',receiving_link='outside',signal='SC2',kind='boundary_out')},
               urban_link_storage_veh={'u':100.,'v':100.,'outside':100.},
               control_area_routes={'movement:m':dict(physical_turns=[turn('a','c','b')]),
                                    'movement:n':dict(target_inside=False,physical_turns=[turn('b','d','z')])})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'network.inpx'; ET.ElementTree(root).write(path)
            catalog=distance.urban_path_catalog(path,NS(network=net))
        self.assertEqual(catalog['paths']['m'],[dict(link='a',start=90.,stop=100.),
            dict(link='c',start=0.,stop=10.),dict(link='b',start=0.,stop=180.)])
        self.assertEqual(catalog['path_length_bounds_m']['m'],[200.,200.])
        self.assertEqual(catalog['paths']['n'],[dict(link='b',start=180.,stop=200.),
            dict(link='d',start=0.,stop=12.),dict(link='z',start=0.,stop=100.)])
        observer=distance.TravelReservations(0.,132.,{'b':True,'d':False,'z':False})
        observer.ordinary_catalog=catalog
        distance.record_ordinary_movement(NS(_omega_travel_reservations=observer),
            NS(network=net,simulation=NS(T_u_sec=1.)),'n',2.,0.,132.)
        self.assertAlmostEqual(observer.by_provider_stock['ordinary_movement','storage:outside'],.04)

    def test_gate_retains_different_link_speeds_and_partial_horizon(self):
        spec=dict(source='s',geometry={'1':[dict(link='a',start=0.,stop=100.),dict(link='b',start=0.,stop=100.)]},
            timings={'1':dict(parts=[dict(link='a',speed_kph=36.),dict(link='b',speed_kph=18.)])})
        cfg=NS(simulation=NS(T_u_sec=1.),network=NS(physical_gate_travel=spec))
        state=NS(_omega_travel_reservations=distance.TravelReservations(0.,20.,{'a':False,'b':True}))
        distance.record_gate(state,cfg,'1',2.,0.,30.)
        self.assertAlmostEqual(state._omega_travel_reservations.by_provider_stock['gate_future','transit:gate:s'],.1)

    def test_direct_receipt_begins_after_offramp_not_at_road_origin(self):
        spec=dict(storage='s',travel=dict(paths={'free':[dict(link='124',start=0.,stop=100.)]}))
        cfg=NS(simulation=NS(T_u_sec=1.),network=NS(direct_exit_legsplit=spec))
        state=NS(_omega_travel_reservations=distance.TravelReservations(0.,4.,{'124':True}))
        distance.record_direct(state,cfg,'free',2.,0.,8.,'124',20.)
        self.assertAlmostEqual(state._omega_travel_reservations.by_provider_stock['direct_exit','storage:s'],.08)

    def test_positive_initial_native_remaining_travel(self):
        stage=dict(origin='s',segments=[dict(link='a',start=0.,stop=100.)])
        record=dict(link_no='a',position_m=20.,speed_kph=36.)
        cfg=NS(simulation=NS(T_u_sec=1.),network=NS(urban_avg_speed_km_h=36.,native_internal_inputs={
            'inputs':{'A':dict(kind='native_route_queue',route_stages=[stage],physical_projection_links=['a'])}}))
        state=NS(time_sec=100.,_omega_travel_reservations=distance.TravelReservations(100.,104.,{'a':True}),
            native_input_route_state=dict(received_veh=0.,completed_veh=0.,cohorts=[
                dict(input='A',stage=0,vehicles=1.,due=108,queued=False)]))
        with patch('evaluation.controllers.projection_support.complete_records',return_value=[record]):
            self.assertEqual(distance.seed_native_routes(state,cfg,{}),1)
        self.assertAlmostEqual(state._omega_travel_reservations.by_provider_stock['native_input_routes','storage:s'],.04)

    def test_positive_initial_prehead_remaining_travel(self):
        spec=dict(origin='s',segments_to_decision=[dict(link='a',start=0.,stop=100.)])
        cfg=NS(simulation=NS(T_u_sec=1.),network=NS(urban_avg_speed_km_h=36.,native_internal_inputs={
            'inputs':{'A':dict(kind='native_choice_prehead',prehead_spec=spec,physical_projection_links=['a'])}}))
        state=NS(time_sec=100.,_omega_travel_reservations=distance.TravelReservations(100.,104.,{'a':True}),
            native_input_prehead_state=dict(generated_veh=0.,departed_scope_veh=0.,cohorts=[
                dict(input='A',vehicles=1.,stage='decision',route=None,due=108)]))
        with patch('evaluation.controllers.projection_support.complete_records',return_value=[
                dict(link_no='a',position_m=20.,speed_kph=36.)]):
            self.assertEqual(distance.seed_native_prehead(state,cfg,{}),1)
        self.assertAlmostEqual(state._omega_travel_reservations.by_provider_stock['native_input_prehead','storage:s'],.04)

    def test_sc2001_outside_entry_consumes_time_but_earns_no_distance(self):
        spec=dict(storage='s',branches={'exit':dict(travel_segments=[dict(link='78',start_m=0.,stop_m=100.)])},
            incoming_movements={'m':dict(origin='o',entry_connector='c',pre_78_distance_m=100.,entry_78_position_m=0.)})
        cfg=NS(simulation=NS(T_u_sec=1.),network=NS(sc2001_corridor=spec))
        state=NS(_omega_travel_reservations=distance.TravelReservations(0.,15.,{'c':False,'78':True}))
        distance.record_sc2001(state,cfg,'exit',2.,'78',0.,'o',100.,0.,20.)
        self.assertAlmostEqual(state._omega_travel_reservations.by_provider_stock['sc2001_corridor','storage:s'],.1)

    def test_known_prechoice_does_not_credit_the_next_leg(self):
        spec=dict(storage='s',physical_travel=dict(
            prefix={'68':[dict(link='68',start=0.,stop=20.)]},
            destinations={'free':[dict(link='68',start=0.,stop=100.)]}))
        cfg=NS(simulation=NS(T_u_sec=1.),network=NS(known_legsplit_routes=spec))
        state=NS(_omega_travel_reservations=distance.TravelReservations(0.,5.,{'68':True}))
        distance.record_known(state,cfg,'prechoice',2.,0.,2.,'68',0.)
        self.assertEqual(state._omega_travel_reservations.by_provider_stock['known_legsplit','storage:s'],.04)
        distance.record_known(state,cfg,'free',2.,3.,11.,'68',20.)
        self.assertEqual(state._omega_travel_reservations.by_provider_stock['known_legsplit','storage:s'],.08)

    def test_choice_stages_only_earn_their_current_physical_path(self):
        spec = dict(decision_link='a',decision_position_m=100.,
            prefix_travel_segments={'a':[dict(link='a',start=0.,stop=100.)]},
            branches={'L':dict(branch_position_m=150.)},
            local_travel_segments={'L':{'c':[dict(link='c',start=0.,stop=20.),dict(link='b',start=30.,stop=80.)]}})
        self.assertEqual(distance.choice_path(spec,'prechoice','a',80.,None),
                         [dict(link='a',start=80.,stop=100.)])
        self.assertEqual(distance.choice_path(spec,'prefix_tagged','a',120.,'L'),
                         [dict(link='a',start=120.,stop=150.)])
        self.assertEqual(distance.choice_path(spec,'local_tagged','c',10.,'L'),
                         [dict(link='c',start=10.,stop=20.),dict(link='b',start=30.,stop=80.)])
        self.assertEqual(distance.choice_path(spec,'prefix_tagged','a',160.,'L'), [])
        with self.assertRaises(distance.DistanceCoverageError):
            distance.choice_path(spec,'unknown','a',80.,None)

    def test_route_slicing_retains_physical_coordinates(self):
        route = [dict(link='a', start=20., stop=70.), dict(link='b', start=5., stop=105.)]
        self.assertEqual(distance.slice_path(route, 40., 80.),
                         [dict(link='a', start=60., stop=70.), dict(link='b', start=5., stop=35.)])
        path = distance.schedule_path(distance.slice_path(route, 40., 80.), 10., 14.)
        self.assertEqual(path, [('a', 60., 70., 10., 11.), ('b', 5., 35., 11., 14.)])

    def test_future_arrival_retains_only_in_horizon_partial_travel(self):
        r = distance.TravelReservations(100., 110., {'a': True})
        route = [dict(link='a', start=0., stop=1000.)]
        self.assertEqual(r.reserve('route', 'storage:s', route, 2., 105., 205.), .1)
        # The far ETA has not yet matured; it still contributes its first50m.
        self.assertEqual(r.by_provider_stock[('route', 'storage:s')], .1)
        before = copy.deepcopy(r)
        changed = copy.deepcopy(r)
        changed.reserve('route', 'storage:s', route, 1., 110., 210.)
        self.assertEqual(vars(r), vars(before))

    def test_native_gate_wait_does_not_book_postgate_path_early(self):
        route = [dict(link='a', start=0., stop=100.)]
        stage = dict(origin='s', segments=route,
                     native_fixed_gate=dict(pre_gate_distance_m=40., post_gate_distance_m=60.))
        cfg = NS(simulation=NS(T_u_sec=1.), network=NS(native_internal_inputs={
            'inputs':{'A':dict(route_stages=[stage])}}))
        s = NS(_omega_travel_reservations=distance.TravelReservations(0., 10., {'a':True}))
        distance.record_native_route(s,cfg,'A',0,2.,0,4)
        self.assertAlmostEqual(s._omega_travel_reservations.by_provider_stock['native_input_routes','storage:s'], .08)
        distance.record_native_route(s,cfg,'A',0,2.,8,14,after_gate=True)
        self.assertAlmostEqual(s._omega_travel_reservations.by_provider_stock['native_input_routes','storage:s'], .12)
        # Four seconds at the gate are stopped time; travel after t10 excluded.

    def test_native_prehead_interhead_belongs_to_existing_movement_stock(self):
        spec = dict(origin='s',left_movement='left',segments_interhead=[dict(link='a',start=40.,stop=60.)])
        cfg = NS(simulation=NS(T_u_sec=1.),network=NS(native_internal_inputs={
            'inputs':{'A':dict(kind='native_choice_prehead',prehead_spec=spec)}}))
        s = NS(_omega_travel_reservations=distance.TravelReservations(0.,10.,{'a':True}))
        distance.record_native_prehead(s,cfg,'A','release',3.,9,11)
        self.assertAlmostEqual(s._omega_travel_reservations.by_provider_stock['native_input_prehead','movement:left'], .03)

    def test_partial_journey_and_partial_omega_no_future_credit(self):
        p = [('a', 0., 100., 10., 20.), ('b', 0., 200., 25., 45.)]
        area = {'a': [(20., 80.)], 'b': True}
        self.assertEqual(distance.timed_path_distance(p, 2., 0., 10., area), 0.)
        self.assertAlmostEqual(distance.timed_path_distance(p, 2., 10., 15., area), .06)
        self.assertAlmostEqual(distance.timed_path_distance(p, 2., 10., 30., area), .22)
        self.assertEqual(distance.timed_path_distance(p, 2., 20., 25., area), 0.)
        self.assertAlmostEqual(distance.timed_path_distance(p, 2., 10., 45., area), .52)

    def test_window_additivity_and_empty_initial_stock(self):
        p = [('a', 0., 100., -5., 5.)]
        area = {'a': True}
        whole = distance.timed_path_distance(p, 3., 0., 10., area)
        split = sum(distance.timed_path_distance(p, 3., a, b, area)
                    for a, b in ((0., 2.3), (2.3, 5.), (5., 10.)))
        self.assertAlmostEqual(whole, .15)
        self.assertAlmostEqual(whole, split)
        self.assertEqual(distance.timed_path_distance(p, 0., 0., 10., area), 0.)

    def test_missing_membership_even_beyond_horizon_fails(self):
        with self.assertRaises(distance.DistanceCoverageError):
            distance.timed_path_distance([('unknown', 0., 100., 100., 110.)], 1., 0., 10., {})
        for support in ([(10., 40.), (30., 60.)], [(10., 10.)], None):
            with self.assertRaises(distance.DistanceCoverageError):
                distance.inside_length_m('a', 0., 100., {'a': support})

    def test_nonphysical_or_overlapping_paths_fail(self):
        for path in ([('a', 20., 10., 0., 1.)], [('a', 0., 20., 1., 1.)],
                     [('a', 0., 20., 0., 2.), ('b', 0., 10., 1., 3.)]):
            with self.assertRaises(ValueError):
                distance.timed_path_distance(path, 1., 0., 10., {'a': True, 'b': True})
        for n in (-1., float('inf'), float('nan'), True):
            with self.assertRaises(ValueError):
                distance.timed_path_distance([], n, 0., 1., {})

    def test_ramp_partial_travel_ready_queues_and_no_mutation(self):
        p = ramp(); before = copy.deepcopy(vars(p))
        self.assertAlmostEqual(distance.ramp_distance(p, 20., 21., {'12': True}), .015)
        self.assertEqual(before, vars(p))
        # Two waiting vehicles (at head and merge) contribute no distance.
        self.assertAlmostEqual(distance.ramp_distance(p, 20., 21., {'12': [(30., 100.)]}), .005)
        self.assertEqual(distance.ramp_distance(p, 20., 21., {'12': False}), 0.)

    def test_lane_mirror_is_not_an_extra_population(self):
        p = ramp(LaneResolvedRampBoundary, lanes=2, lane_arrival_shares=(.5, .5),
                 initial_cohorts=((20., 0., 1), (95., 36., 2)))
        self.assertAlmostEqual(distance.ramp_distance(p, 20., 21., {'12': True}), .015)
        # The aggregate parent retains an old initialization representation.
        p._upstream.append((22., 999.))
        self.assertAlmostEqual(distance.ramp_distance(p, 20., 21., {'12': True}), .015)

    def test_meter_service_moves_only_on_following_interval(self):
        p = ramp(initial_cohorts=((40., 0., 1),))
        self.assertEqual(distance.ramp_distance(p, 20., 21., {'12': True}), 0.)
        p.begin_interval(20., 1.)
        p.commit_merge(0.)
        p.apply_head_service(1., mode='GREEN')
        p.finish_interval(0.)
        self.assertAlmostEqual(distance.ramp_distance(p, 21., 22., {'12': True}), .01)

    def test_port_travel_and_waiting_are_distinct(self):
        p = NS(entry_accel_mps2=None, last_time_s=20., length_m=100., travel_s=10.,
               pending=[[20.5, 2.], [25., 3.]], ready=77.)
        self.assertAlmostEqual(distance.delayed_port_distance(p, '9', 20., 21., {'9': True}), .04)
        p.entry_accel_mps2 = 1.
        with self.assertRaises(distance.DistanceCoverageError):
            distance.delayed_port_distance(p, '9', 20., 21., {'9': True})

    def test_ctm_distance_counts_forward_not_lateral_or_future_link(self):
        u = NS(edges={71: [0., 10., 30.]}, last_transfers=[
            (('external', 'in'), (71, 1, 0), ((None, 4.),)),
            ((71, 1, 0), (71, 2, 0), ((None, 3.),)),
            ((71, 1, 0), (71, 1, 1), ((None, 2.),)),
            ((71, 1, 1), ('exit', 8), ((None, 1.),))])
        self.assertEqual(distance.local_cell_distance(u, {'71': True}),
                         {'storage:lane_urban_71': .04})
        self.assertEqual(distance.local_cell_distance(u, {'71': [(5., 25.)]}),
                         {'storage:lane_urban_71': .025})

    def test_incomplete_subtotal_cannot_be_scored(self):
        receipt = dict(scope='full_control_area_omega', coverage_complete=False,
                       distance_by_stock_veh_km={'freeway:FW_E': 8.}, tvd_omega_veh_km=8.,
                       unresolved_transport=['urban_route_cohorts'], unresolved_positive_stocks=[])
        with self.assertRaises(distance.DistanceCoverageError):
            distance.require_complete_coverage(receipt)
        receipt.update(coverage_complete=True, unresolved_transport=[])
        self.assertEqual(distance.require_complete_coverage(receipt), 8.)
        receipt['tvd_omega_veh_km'] += 1.
        with self.assertRaises(distance.DistanceCoverageError):
            distance.require_complete_coverage(receipt)

    def test_real_tangent_preserves_cohort_and_timing_derivative(self):
        from evaluation.controllers.sdmpc_tangent_runtime import Transform, namespace
        from evaluation.controllers import sdmpc_dual as ad
        env = dict(__name__='distance_tangent_test', **namespace())
        tree = ast.fix_missing_locations(Transform().visit(ast.parse(Path(distance.__file__).read_text())))
        exec(compile(tree, distance.__file__, 'exec'), env)
        trace = ad.Trace([.001, .001])
        n = ad.Dual(3., {0: 1.}, trace)
        eta = ad.Dual(25., {1: 1.}, trace)
        value = env['timed_path_distance']([('a', 0., 100., eta-10., eta)],
                                           n, 20., 30., {'a': True})
        self.assertAlmostEqual(ad.primal(value), .15)
        self.assertAlmostEqual(ad.derivative(value)[0], .05)
        self.assertAlmostEqual(ad.derivative(value)[1], .03)


if __name__ == '__main__':
    unittest.main()
