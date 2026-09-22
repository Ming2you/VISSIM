"""Bounded destination-aware downstream transport experiment, not an adapter.

Current route labels, finite lane storage, FIFO and native signal commands are
kept distinct. Lane access is a receiving constraint, never vehicle deletion.
The four-cell urban approximation is deliberately tested before adoption.
"""
from pathlib import Path
from collections import deque, Counter, defaultdict
import sys, math, copy, hashlib, unittest, argparse, json
import xml.etree.ElementTree as ET
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, MODEL, CASES, ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.route_access_observer import observe, geometry
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_spatial_transport import CumulativeLane, ReceivingEnvelope
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.urban_receiving_probe import dataset

HERE = Path(__file__).resolve().parent
EPS = 1e-9


from evaluation.controllers.physical_urban_transport import (FIFO, tagged, unassigned_continuation,
    UrbanTransport, CoupledPort, history_inputs)


class Contracts(unittest.TestCase):
    def toy(self, queues, green=True):
        class Signal:
            def state_at(self, *args, **kwargs):
                return 'GREEN' if green else 'RED'
        p = UrbanTransport.__new__(UrbanTransport)
        p.program, p.offset, p.time = Signal(), 0, 0
        p.speed, p.spacing, p.wave = 10., 6., 3.
        p.lateral_access = True
        p.continuation, p.exchange_rates = False, {}
        p.compact_equal_behavior = True
        p.unrouted_labels, p.fallback_exits = set(), {10634,10635,10642}
        p.capacity_rate = 10*3/(6*13)
        p.exits = {10634: {'lanes': [1,2,3], 'position_m': 96},
                   10635: {'lanes': [4,5], 'position_m': 95},
                   10642: {'lanes': [1], 'position_m': 48}}
        p.edges = {71: [0., 24.]}
        p.cells = {(71,lane,0): FIFO(rows) for lane, rows in queues.items()}
        p.cap = {key: 4. for key in p.cells}
        p.dx = {key: 24. for key in p.cells}
        p.initial = p.counts()
        p.admitted, p.departed = Counter(), Counter()
        p.movements, p.blocked_seconds = Counter(), Counter()
        p.vehicle_seconds, p.checks = 0., 0
        return p

    def test_prefix_and_unknown_conservation(self):
        q = FIFO([((10635, 1), 1), ((None, 2), 1), ((10634, 3), 1)])
        self.assertEqual(q.take(1.4), [((10635,1),1), ((None,2),.3999999999999999)])
        self.assertAlmostEqual(q.stock, 1.6)
        self.assertEqual(q.q[0][0], (None,2))

    def test_overdraw_rejected(self):
        q = FIFO([((None,1), .5)])
        with self.assertRaises(ArithmeticError): q.take(.6)

    def test_future_input_rejected(self):
        with self.assertRaises(ValueError): history_inputs({2401: {}}, 2400, {}, {})

    def test_blocked_adjacent_lane_does_not_close_an_open_lane(self):
        p = self.toy({2: [((10634,2), 2)], 3: [((10635,3), 2)], 4: [((10635,4), 4)]})
        p.step({})
        self.assertEqual(p.cells[71,3,0].stock, 2)
        self.assertGreater(p.departed[10634,2], 0)
        self.assertGreater(p.departed[10635,4], 0)
        # Downstream discharge creates a subsequent receiving opportunity.
        p.step({})
        self.assertLess(p.cells[71,3,0].stock, 2)
        self.assertGreater(p.cells[71,4,0].counts()[10635,3], 0)

    def test_two_full_lanes_cannot_swap_without_space(self):
        p = self.toy({3: [((10635,3), 4)], 4: [((10634,4), 4)]})
        for _ in range(10): p.step({})
        self.assertEqual(sum(p.departed.values()), 0)
        self.assertEqual(p.counts(), p.initial)

    def test_optional_body_start_space_prevents_red_trickle(self):
        p=self.toy({3:[((10635,1),1)],4:[((10635,2),3.5)]},green=False)
        p.lateral_start_footprints={1:6.,None:6.}
        for _ in range(5):p.step({})
        self.assertEqual(p.cells[71,3,0].stock,1)
        self.assertEqual(p.cells[71,4,0].stock,3.5)
        self.assertAlmostEqual(p.vehicle_seconds,22.5)

    def test_optional_body_space_does_not_discard_a_blocked_vehicle(self):
        p=self.toy({3:[((10635,1),1)],4:[((10635,2),3.5)]})
        p.lateral_start_footprints={1:6.,None:6.}
        for _ in range(20):p.step({})
        self.assertGreater(p.departed[10635,1],0)
        self.assertAlmostEqual(sum(p.counts().values())+sum(p.departed.values()),4.5)

    def test_compatible_follower_cannot_pass_blocked_head(self):
        p = self.toy({3: [((10635,3), 1), ((10634,5), 2)], 4: [((10634,4), 4)]})
        p.step({})
        self.assertEqual(p.departed[10634,5], 0)
        self.assertEqual(p.cells[71,3,0].q[0][0], (10635,3))

    def test_red_preserves_all_waiting_cost_and_mass(self):
        p = self.toy({3: [((10634,1), 4)]}, green=False)
        for _ in range(20): p.step({})
        self.assertEqual(p.vehicle_seconds, 80)
        self.assertEqual(p.departed, Counter())

    def test_two_sources_share_finite_receiving(self):
        p = self.toy({3: [((10634,1), 3)]}, green=False)
        a, b = FIFO([((10634,2), 1)]), FIFO([((10634,3), 1)])
        accepted = p.step({'a': ((71,3,0), a), 'b': ((71,3,0), b)})
        total = sum(n for rows in accepted.values() for label, n in rows)
        self.assertAlmostEqual(total, 3/24)
        self.assertAlmostEqual(a.stock, b.stock)
        self.assertAlmostEqual(sum(p.counts().values())+a.stock+b.stock, 5)

    def test_merge_allocation_is_not_a_function_of_packet_fragment_size(self):
        results = []
        for packets in ([((10634,2),1)], [((10634,2),.01),((10634,3),.99)]):
            p = self.toy({3:[((10634,1),3)]}, green=False)
            a,b = FIFO(packets), FIFO([((10634,4),1)])
            accepted = p.step({'a':((71,3,0),a), 'b':((71,3,0),b)})
            results.append([sum(n for label,n in accepted[name]) for name in ('a','b')])
        for a,b in zip(*results): self.assertAlmostEqual(a,b,places=12)
        self.assertAlmostEqual(results[1][0],3/48)

    def test_red_head_does_not_prevent_follower_lateral_access(self):
        p = self.toy({3: [((10634,1), 1), ((10635,2), 1)], 4: []}, green=False)
        p.step({})
        self.assertEqual(p.cells[71,3,0].q[0], [(10634,1), 1])
        self.assertGreater(p.cells[71,4,0].counts()[10635,2], 0)
        self.assertEqual(sum(p.departed.values()), 0)

    def test_deferred_change_prefers_feasible_forward_progress(self):
        p=self.toy({3:[((10635,1),1)],4:[]},green=False)
        p.edges[71]=[0.,24.,48.]
        for lane in (3,4):p.cells[71,lane,1]=FIFO();p.cap[71,lane,1]=4.;p.dx[71,lane,1]=24.
        p.defer_mandatory_while_forward_open=True;p.step({})
        self.assertEqual(p.cells[71,4,0].stock,0)
        self.assertGreater(p.cells[71,3,1].stock,0)

    def test_deferred_change_remains_available_when_forward_is_full(self):
        p=self.toy({3:[((10635,1),1)],4:[]},green=False)
        p.edges[71]=[0.,24.,48.]
        for lane in (3,4):p.cells[71,lane,1]=FIFO();p.cap[71,lane,1]=4.;p.dx[71,lane,1]=24.
        p.cells[71,3,1]=FIFO([((10634,2),4)]);p.initial=p.counts()
        p.defer_mandatory_while_forward_open=True;p.step({})
        self.assertGreater(p.cells[71,4,0].stock,0)

    def test_defer_destination_ablation_keeps_other_changes_available(self):
        for selected, should_change in (((10635,), False), ((10634,10642), True)):
            p=self.toy({3:[((10635,1),1)],4:[]},green=False)
            p.edges[71]=[0.,24.,48.]
            for lane in (3,4):p.cells[71,lane,1]=FIFO();p.cap[71,lane,1]=4.;p.dx[71,lane,1]=24.
            p.defer_mandatory_while_forward_open=True;p.defer_destinations=selected;p.step({})
            self.assertEqual(p.cells[71,4,0].stock>0,should_change)
            self.assertAlmostEqual(sum(p.counts().values()),1.)

    def test_deferred_change_does_not_lock_a_follower_behind_red_head(self):
        p=self.toy({3:[((10634,1),1),((10635,2),1)],4:[]},green=False)
        p.defer_mandatory_while_forward_open=True;p.step({})
        self.assertGreater(p.cells[71,4,0].counts()[10635,2],0)
        self.assertEqual(sum(p.departed.values()),0)

    def test_receiving_preference_avoids_early_entry_into_queued_lane(self):
        p=self.toy({3:[((10635,1),1)],4:[((10635,2),3.5)]},green=False)
        p.edges[71]=[0.,24.,48.]
        for lane in (3,4):p.cells[71,lane,1]=FIFO();p.cap[71,lane,1]=4.;p.dx[71,lane,1]=24.
        p.prefer_more_receiving_space=True;p.step({})
        self.assertEqual(p.cells[71,4,0].counts().get((10635,1),0.),0.)
        self.assertGreater(p.cells[71,3,1].stock,0.)

    def test_receiving_preference_keeps_equal_open_lane_access(self):
        p=self.toy({3:[((10635,1),1)],4:[]},green=False)
        p.edges[71]=[0.,24.,48.]
        for lane in (3,4):p.cells[71,lane,1]=FIFO();p.cap[71,lane,1]=4.;p.dx[71,lane,1]=24.
        p.prefer_more_receiving_space=True;p.step({})
        self.assertGreater(p.cells[71,4,0].stock,0.)

    def test_receiving_preference_cannot_pass_a_mandatory_exit_deadline(self):
        p=self.toy({3:[((10635,1),1)],4:[]})
        p.prefer_more_receiving_space=True;p.step({})
        self.assertGreater(p.cells[71,4,0].stock,0.)
        self.assertEqual(p.departed[10635,1],0.)

    def test_lateral_and_longitudinal_share_receiver(self):
        p = self.toy({3: [((10635,1), 3)], 4: [((10635,2), 3)]}, green=False)
        queue = FIFO([((10635,3), 1)])
        p.step({'in': ((71,4,0), queue)})
        self.assertLessEqual(p.cells[71,4,0].stock, 3+3/24+1e-9)
        self.assertAlmostEqual(sum(p.counts().values())+queue.stock, 7)

    def test_eligible_lane_change_uses_history_and_preserves_label(self):
        p = self.toy({4: [((10635,1), 2)], 5: []}, green=False)
        p.exchange_rates = {(71,4,5,10635): .1}
        p.step({})
        self.assertAlmostEqual(p.cells[71,5,0].counts()[10635,1], 2*-math.expm1(-.1))
        self.assertEqual(sum(p.departed.values()), 0)

    def test_unknown_source_is_not_automatically_a_fallback_vehicle(self):
        v = dict(connector=None, link=10643, route_decision=None, route_number=None)
        self.assertFalse(unassigned_continuation(v, {}))
        v.update(link=126, route_decision=1133, route_number=2)
        self.assertTrue(unassigned_continuation(v, {(1133,2): [120,70,126]}))
        v['route_next_link_conflict'] = True
        self.assertFalse(unassigned_continuation(v, {(1133,2): [120,70,126]}))

    def test_unrouted_eligible_side_exit_does_not_wait_for_downstream_signal(self):
        p = self.toy({1: [((None,1), 2)]}, green=False)
        p.cells[71,1,1] = p.cells.pop((71,1,0))
        p.cap, p.dx = {(71,1,1): 4.}, {(71,1,1): 24.}
        p.edges = {71: [0.,24.,48.,72.,96.]}
        p.continuation = True; p.unrouted_labels.add((None,1))
        p.step({})
        self.assertGreater(p.departed[None,1], 0)
        self.assertEqual(p.departed[10642,1], 0)  # no invented assigned destination

    def test_unrouted_side_exit_requires_an_accessible_lane(self):
        p = self.toy({2: [((None,1), 2)]}, green=False)
        p.cells = {(71,2,1): p.cells[71,2,0], (71,2,2): FIFO()}
        p.cap, p.dx = {k:4. for k in p.cells}, {k:24. for k in p.cells}
        p.edges = {71: [0.,24.,48.,72.,96.]}
        p.continuation = True; p.unrouted_labels.add((None,1))
        p.step({})
        self.assertEqual(sum(p.departed.values()), 0)
        self.assertGreater(p.cells[71,2,2].stock, 0)

    def test_compaction_cannot_cross_another_destination(self):
        a,b,c = (10634,1),(10634,2),(10635,3)
        q = FIFO([(a,.2),(b,.4),(a,.3),(c,.6),(a,.8)])
        before = q.counts()
        q.compact_runs(lambda label: label[0])
        self.assertEqual(list(q.q), [[a,.5],[b,.4],[c,.6],[a,.8]])
        self.assertEqual(q.counts(), before)

    def test_compaction_matches_analytic_reciprocal_flows(self):
        p = self.toy({3: [((10634,1),1),((10634,2),1)], 2: [((10634,3),1),((10634,4),1)]}, green=False)
        p.exchange_rates = {(71,3,2,10634):.02, (71,2,3,10634):.01}
        # Uncompacted fragments below EPS stop moving: by10s they understate
        # exchange by1.834e-7veh despite conserving mass. Test the actual linear
        # flux law, not that artifact of the failed numerical representation.
        n3, n2 = 2., 2.
        for t in range(450):
            to2, to3 = n3*-math.expm1(-.02), n2*-math.expm1(-.01)
            n3, n2 = n3-to2+to3, n2-to3+to2
            p.step({})
            self.assertAlmostEqual(p.cells[71,3,0].stock, n3, places=10)
            self.assertAlmostEqual(p.cells[71,2,0].stock, n2, places=10)
            self.assertAlmostEqual(p.vehicle_seconds, 4*(t+1), places=10)
            self.assertLessEqual(max(len(q.q) for q in p.cells.values()),4)

    def test_reciprocal_exchange_remains_bounded_without_losing_mass(self):
        p = self.toy({3: [((10634,1),1),((10634,2),1)], 2: [((10634,3),1),((10634,4),1)]}, green=False)
        p.exchange_rates = {(71,3,2,10634):.02, (71,2,3,10634):.01}
        for _ in range(450): p.step({})
        self.assertLessEqual(max(len(q.q) for q in p.cells.values()),4)
        for label, n in p.initial.items(): self.assertAlmostEqual(p.counts()[label], n)


@contextmanager
def trace_mainline_limits():
    """Observe actual transition locals without replacing a flow/speed value."""
    import inspect
    import canonical_harness as ch
    from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
    mn=ch.accounting._mn;original=mn.metanet_speed_update_kmh;rows=[]
    def observe_speed(*args,**kwargs):
        frame=inspect.currentframe().f_back
        if (frame.f_code is PhysicalLaneGroups.advance.__code__):
            # run_probe wraps advance for finite-wave receiving. The original
            # advance code is therefore explicitly supplied below as well.
            selected=True
        else:
            selected=(frame.f_code.co_name=='advance' and
                Path(frame.f_code.co_filename).resolve()==e.ROOT/'evaluation/controllers/physical_lane_groups.py')
        local=frame.f_locals
        if selected and local['road']=='FW_E' and local['i']==0 and local['g']==0:
            model=local['self'];dt=local['dt'];ports={}
            for off,request in local['offreq'].items():
                i=model.spec['off_access'][off]['cell']
                caps=local['offramp_group_capacity_veh_h'] or {}
                ports[off]=dict(cell=i,request_veh=list(request),accepted_veh=list(local['offsent'][off]),
                    group_capacity_veh=[x*dt for x in caps[off]] if off in caps else None,
                    total_capacity_veh=local['offramp_capacity_veh_h'][off]*dt,
                    fifo=list(local['fifo'][i]),through_request_veh=list(local['through_requests'][i]),
                    through_after_fifo_veh=list(local['through'][i]),mainline_out_veh=list(local['outgoing'][i]),
                    start_n=list(local['before'][i]),start_speed_kmh=list(local['oldv'][i]))
            rows.append(dict(time_s=local['state'].time_sec,step_s=model.sec,ports=ports))
        del frame
        return original(*args,**kwargs)
    mn.metanet_speed_update_kmh=observe_speed
    try:yield rows
    finally:mn.metanet_speed_update_kmh=original


def run_probe(lateral_access=False, history_exchange=False, continuation=False, nc_only=False, defer_mandatory=False,
              defer_destinations=None, prefer_receiving=False, trace_limits=False, network_exit_intent=False,
              current_exit_intent=False, branch_partition=None, branch_exchange=None, partition_context=None, transport_step=None,
              output_name=None, partition_ports=None):
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit
    from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
    import canonical_harness as ch

    if history_exchange and not lateral_access: raise ValueError('History exchange requires lateral access')
    if current_exit_intent and not network_exit_intent:raise ValueError('Current intent requires conserved network exit labels')
    if branch_partition is not None and (branch_partition not in ('off','on') or not current_exit_intent):
        raise ValueError('Partition comparison requires the identical current-route baseline')
    if branch_exchange not in (None,'off','on') or (branch_exchange=='on' and branch_partition!='on'):
        raise ValueError('Spatial exchange requires branch partition')
    if partition_context not in (None,'off','on') or (partition_context=='on' and branch_partition!='on'):
        raise ValueError('Physical speed context requires branch partition')
    if partition_ports is not None and (branch_partition!='on' or not isinstance(partition_ports,list)
            or not partition_ports or len(partition_ports)!=len(set(partition_ports)) or '10643' not in partition_ports):
        raise ValueError('Extra partition diagnostic retains the existing10643 partition')
    if transport_step is not None and (transport_step not in (1,2,5,10) or partition_context!='on'):
        raise ValueError('Time refinement requires consistent physical speed context')
    if continuation and not history_exchange: raise ValueError('Continuation probe includes receiving-limited lane exchange')
    if defer_mandatory and not lateral_access:raise ValueError('Deferred changes require lateral access')
    if prefer_receiving and (not lateral_access or defer_mandatory or defer_destinations is not None):
        raise ValueError('Receiving comparison requires lateral access without blanket/destination deferral')
    if defer_destinations is not None:
        if not defer_mandatory or not defer_destinations or not set(defer_destinations)<={10634,10635,10642}:
            raise ValueError('Destination ablation requires deferred changes and known nonempty exits')
        defer_destinations=tuple(sorted(set(defer_destinations)))
    name = ('urban_route_transport_space_v1' if prefer_receiving else
            'urban_route_transport_defer_v1' if defer_mandatory else
            'urban_route_transport_continuation_v3' if continuation else
            'urban_route_transport_exchange_v3' if history_exchange else
            'urban_route_transport_lateral_v3' if lateral_access else 'urban_route_transport_v3')
    if defer_destinations is not None: name += '_dest_'+'_'.join(map(str,defer_destinations))
    if network_exit_intent: name += '_network_intent'
    if current_exit_intent: name += '_current'
    if trace_limits: name += '_limits'
    if branch_partition is not None: name += '_partition_'+branch_partition+'_v4'
    if nc_only: name += '_nc'
    if branch_exchange is not None:
        name=('partition_exchange_v1' if branch_exchange=='on' else 'partition_exchange_off_partition_'+str(branch_partition)+'_v1')+('_nc' if nc_only else '')
    if partition_context is not None:
        name='partition_context_'+partition_context+'_exchange_'+str(branch_exchange)+'_part_'+str(branch_partition)+'_v1'+('_nc' if nc_only else '')
    if transport_step is not None:name='transport_step'+str(transport_step)+'_exchange_'+str(branch_exchange)+'_v2'+('_nc' if nc_only else '')
    if output_name is not None:
        if not output_name or Path(output_name).name!=output_name:raise ValueError('Diagnostic output must be a single directory name')
        name=output_name
    out = HERE/name
    out.mkdir(exist_ok=False)
    suite = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    if not suite.wasSuccessful(): raise AssertionError('Local transport contracts failed')
    e.save(out/'tests.json', dict(passed=True, tests=suite.testsRun))
    bank = HERE/'route_state_native_v1/none_s23'
    network = bank/'source/baseline.inpx'
    route_map, exits = geometry(network)
    raw = e.load(bank/'analysis/frames.json')
    past = {f['time_s']: f for f in raw['frames'] if 2250 <= f['time_s'] <= 2400}
    del raw
    current = observe(past[2400], route_map, exits)
    history = history_inputs(past, 2400, route_map, exits)
    evidence = HERE/'urban_drain_observations_v5/s23_none_evidence.json'
    _, program, offset = dataset(evidence.with_name('s23_none.csv'), evidence)
    wave = e.load(HERE/'off_spatial_supply_v1/result.json')['wave_m_s']
    # Urban free speed uses network50km/h as an explicit fixed structural
    # approximation, not a calibrated microscopic speed law.
    root = ET.parse(network).getroot()
    speed = float(next(x for x in root.findall('./links/link') if x.get('no') == '71').get('mesoSpeed'))/3.6
    cfg = e.load(HERE/'off_spatial_transport_cumulative_v1/config.json')
    route_fraction = None
    if network_exit_intent:
        # Test the existing destination-conservation implementation with this
        # coupled outlet. Demand comes from the network, not realised exits.
        decision=next(x for x in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')
                      if x.get('no')=='1130')
        assert decision.get('allVehTypes')=='true' and decision.get('link')=='74'
        relative={}
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            flow=route.get('relFlow','')
            intervals=flow.split()[1:] if flow else ['0:1']
            assert len(intervals)==1 and intervals[0].split(':')[0]=='0', 'Only constant first-exit routes supported here'
            relative[int(route.get('no'))]=float(intervals[0].split(':')[1])
            if route.get('no')=='1': assert route.get('destLink')=='10643'
        assert set(relative)=={1,2,3} and all(x>=0 for x in relative.values())
        route_fraction=relative[1]/sum(relative.values())
        cfg['freeway']['physical_upstream_exit_inventory']={'10643':route_fraction}
    if branch_partition=='on':cfg['freeway']['physical_branch_partition']=list(partition_ports or ['10643'])
    if branch_exchange is not None:cfg['freeway']['physical_partition_exchange']=branch_exchange=='on'
    if partition_context is not None:cfg['freeway']['physical_partition_speed_context']=partition_context=='on'
    if transport_step is not None:cfg['freeway']['physical_integration_step_sec']=transport_step
    config = out/'config.json'; e.save(config, cfg)
    seed, folder, candidate_bank, start = CASES[1]
    assert seed == 23 and start == 2400
    data = e.ObservationData(folder)
    model = e.load_base_model(data.geometry, config)
    original_config = model._config
    def configuration(road, values):
        conf = original_config(road, values)
        if road == 'FW_E': conf.network.terminal_zero_gradient = True
        return conf
    model._config = configuration
    parameters = e.load(HERE/'port_travel_fit_v1/selected_parameters.json')['parameters']
    profile = e.load(MODEL/'port_profile.json')
    lane = e.load(H/'lane_group_response_20260919/observations_v1/s23.json')
    origin = e.load(HERE/'port_positions_v1/s23.json')
    protocol = e.load(candidate_bank/'protocol.json')
    sources = [Path(__file__), network, bank/'analysis/frames.json', config,
               HERE/'off_spatial_transport.py', HERE/'off_spatial_supply.py', HERE/'route_access_observer.py',
               e.CAL/'canonical_harness.py', e.ROOT/'evaluation/controllers/physical_lane_groups.py',
               e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
               H/'evaluate_response.py',HERE/'ramp_lane_coupling_check.py',
               e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',
               HERE/'off_spatial_supply_v1/result.json', evidence, evidence.with_name('s23_none.csv'),
               HERE/'port_travel_fit_v1/selected_parameters.json', MODEL/'port_profile.json',
               H/'lane_group_response_20260919/observations_v1/s23.json', HERE/'port_positions_v1/s23.json',
               candidate_bank/'protocol.json']
    current_labels=None
    if current_exit_intent:
        intent_path=HERE/'current_mainline_route_v1/result.json';sources.append(intent_path)
        current_labels=e.load(intent_path)
        assert current_labels['information_cutoff_s']==start and not current_labels['future_route_observations_used']
    exchange_observation=None
    if branch_exchange=='on':
        exchange_path=HERE/'branch_flux_audit_v1/past_exchange.json';sources.append(exchange_path)
        exchange_observation=e.load(exchange_path)
        assert exchange_observation['observation_end_s']==start and not exchange_observation['future_inputs']
        assert exchange_observation['connector']=='10643' and exchange_observation['cell']==8
    pins = {str(p.relative_to(e.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    e.save(out/'protocol.json', dict(source_pins=pins, information_cutoff_s=start, future_traffic_inputs=False,
        wave_m_s=wave, urban_free_speed_m_s=speed, forecast_history=history, lateral_access=lateral_access,
        history_exchange=history_exchange, unrouted_continuation=continuation,
        defer_mandatory_while_forward_open=defer_mandatory,
        defer_destinations=defer_destinations,
        prefer_more_receiving_space=prefer_receiving,
        read_only_limit_observer=trace_limits,
        configured_first_exit_fraction=route_fraction,
        observed_current_exit_inventory=current_exit_intent,
        interior_branch_partition=branch_partition=='on',
        interior_branch_ports=list(partition_ports or ['10643']) if branch_partition=='on' else [],
        spatial_partition_exchange=branch_exchange=='on',
        physical_partition_speed_context=partition_context=='on',
        mainline_integration_step_sec=model.base.simulation.T_f_sec,
        evaluated_arms=['none'] if nc_only else list(ARMS),
        numerical_representation='Coalesce duplicate-ID fragments only within consecutive identical-destination/continuation runs; preserve labelled mass and destination FIFO. Per-fragment order inside an equivalent run is coalesced.',
        continuation_semantics='PTV2020 connector Direction=ALL; next reachable connector for a vehicle with no onward route',
        continuation_source='https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Strassennetz_Verb_str_Attr.htm',
        assumptions=['FIFO fluid queues in finite lane cells; lateral insertion at target cell tail.',
                     '126 off entry joins its final cell;10641 and71 entrance coordinates rounded to first cell.',
                     '71 end-cell discharge gated by native SG2/5; unknown exit labels remain unknown.',
                     'No vehicle loss; a missed side-turn remains in stock and cost.',
                     'Repeat past150s urban arrivals including phase; new off labels use past departure composition.',
                     'Both flow boundaries use existing NC13 wave and unchanged nominal6m spacing.',
                     'No explicit longitudinal gaps within urban cells, target-cell receiving is an approximation.',
                     'No new10700 traffic model: reject observed use instead of discarding it.'],
        no_gain_fitting=True, qualified=False))
    init, release = ch.LaneResolvedDelayedPort.__init__, ch.LaneResolvedDelayedPort.release
    accept, advance = CumulativeLane.accept, PhysicalLaneGroups.advance
    lane_initialize=PhysicalLaneGroups.__init__
    costs, summaries = {}, {}
    for arm in (['none'] if nc_only else ARMS):
        sequence = protocol['candidate_bank'].get(arm, dict(green=[], vsl=[]))
        def command(t):
            i = int((t-start)//150)
            return ({'RM_C10490': sequence['green'][i]} if sequence['green'] else {},
                    {d: sequence['vsl'][i] for d in protocol['dsd_ids']} if sequence['vsl'] else {})
        window = e.window(data, model, start, 'history_forecast', profile, command, port_origin_counts=origin['counts'])
        window['lane_group_dynamics'] = {'FW_E': {**lane['geometry'], **lane['cutoffs'][str(start)],
            'initial_ramp_origin': origin['counts'][str(start)], 'initial_off_eligible': origin['eligible_before_off'][str(start)]}}
        if branch_partition=='on':
            initial={side:[] for side in ('pre','post')}
            rows=[r for r in current_labels['current_vehicles'] if r['cell']==8]
            for side in ('pre','post'):
                for g in range(3):
                    selected=[r for r in rows if r['group']==g and r['pre_off10643']==(side=='pre')]
                    fallback=lane['cutoffs'][str(start)]['initial_groups'][8][g]['v_kmh']
                    initial[side].append(dict(n_veh=len(selected),v_kmh=sum(r['speed_kmh'] for r in selected)/len(selected) if selected else fallback))
            window['lane_group_dynamics']['FW_E']['branch_partition_initial']={'10643':initial}
            if branch_exchange=='on':initial['exchange']=copy.deepcopy(exchange_observation)
            for off in (partition_ports or ['10643']):
                if off=='10643':continue
                if branch_exchange=='on':raise ValueError('Extra partition requires its own observed exchange profile')
                spec=window['lane_group_dynamics']['FW_E']
                cell=spec['off_access'][off]['cell']
                cut=model.offramps[off]['chain_pos_m']
                vehicles=[r for r in current_labels['current_vehicles'] if r['cell']==cell]
                extra={side:[] for side in ('pre','post')}
                for side in ('pre','post'):
                    for group,row in enumerate(lane['cutoffs'][str(start)]['initial_groups'][cell]):
                        selected=[r for r in vehicles if r['group']==group and
                                  (r['chain_position_m']<cut)==(side=='pre')]
                        extra[side].append(dict(n_veh=len(selected),v_kmh=sum(r['speed_kmh'] for r in selected)/len(selected)
                                               if selected else row['v_kmh']))
                spec['branch_partition_initial'][off]=extra
        tracked, offers = [], []
        def initialize(self, capacity, length, speed_kmh, cohorts, time, rates):
            init(self, capacity, length, speed_kmh, cohorts, time, rates)
            expected = sorted([v['position_m'], v['speed_kmh'], v['lane']] for v in current['vehicles'] if v['link'] == 10643)
            if sorted(cohorts) != expected or any(x != 0 for row in rates for x in row):
                raise AssertionError('Current lane cohorts/exchange changed')
            self.lanes = [CumulativeLane(capacity/2, length, speed_kmh,
                [(v['position_m'], v['speed_kmh'], v['length_m']) for v in current['vehicles']
                 if v['link'] == 10643 and v['lane'] == g], time, wave) for g in (1,2)]
            self.initial = self.stock
            self.coupled = CoupledPort(self.lanes, current, history, network, program, offset, speed,
                                      2*length/capacity, wave, lateral_access, history_exchange, continuation)
            self.coupled.urban.defer_mandatory_while_forward_open=defer_mandatory
            self.coupled.urban.defer_destinations=defer_destinations
            self.coupled.urban.prefer_more_receiving_space=prefer_receiving
            tracked.append(self)
        def coupled_release(self, t, dt, services):
            if self not in tracked: return release(self, t, dt, services)
            return sum(self.coupled.step(t+i) for i in range(int(dt)))
        def labelled_accept(self, t, amount, **kw):
            accept(self, t, amount, **kw)
            for port in tracked:
                if self in port.lanes:
                    port.coupled.admit(port.lanes.index(self), amount)
                    return
        def supply(self, state, control, demand, config, **kw):
            if self.road == 'FW_E':
                assert len(tracked) == 1
                caps = copy.deepcopy(kw['offramp_group_capacity_veh_h'])
                old = caps['10643']
                new = [min(old[g], p.receiving()/self.dt) for g, p in enumerate(tracked[0].lanes)] + [0.]
                caps['10643'] = new
                kw['offramp_group_capacity_veh_h'] = caps
                offers.append(dict(time_s=state.time_sec, old=old, new=new, stock=[p.stock for p in tracked[0].lanes]))
            return advance(self, state, control, demand, config, **kw)
        def observed_lane_initialize(self,*args,**kwargs):
            lane_initialize(self,*args,**kwargs)
            if self.road!='FW_E':return
            assert current_labels is not None and self.upstream_exit_inventory=={'10643':route_fraction}
            for i in range(9):
                eligible=self.initial_off_eligible['10643'] if i==8 else self.n[i]
                values=[]
                for g,n in enumerate(eligible):
                    row=current_labels['current_pre_branch_groups'][f'{i}:{g}']
                    assert row['n']==n and row['known_off']+row['known_through']+row['unknown']==n
                    # Unassigned vehicles retain an explicit expectation from
                    # the configured route fraction, never a future route.
                    values.append(row['known_off']+route_fraction*row['unknown'])
                if i==8:self.off['10643']=values
                else:self.upstream_off['10643'][i]=values
            self.intent_initial['10643']=sum(map(sum,self.upstream_off['10643']))+sum(self.off['10643'])
        ch.LaneResolvedDelayedPort.__init__, ch.LaneResolvedDelayedPort.release = initialize, coupled_release
        CumulativeLane.accept, PhysicalLaneGroups.advance = labelled_accept, supply
        if current_exit_intent:PhysicalLaneGroups.__init__=observed_lane_initialize
        try:
            if trace_limits:
                with trace_mainline_limits() as limits:
                    prediction = e.simulate(model, window, parameters)
                assert len(limits)==450/model.base.simulation.T_f_sec, 'Missing mainline transition observations'
                e.save(out/f'limits_{arm}.json',limits)
            else:
                prediction = e.simulate(model, window, parameters)
        finally:
            ch.LaneResolvedDelayedPort.__init__, ch.LaneResolvedDelayedPort.release = init, release
            CumulativeLane.accept, PhysicalLaneGroups.advance = accept, advance
            PhysicalLaneGroups.__init__=lane_initialize
        base = e.load(HERE/f'off_spatial_transport_cumulative_v1/prediction_lane_reference_{arm}.json')
        checks = audit(prediction, base, same_time_step=model.base.simulation.T_f_sec==10)
        coupled = tracked[0].coupled
        for g, p in enumerate(coupled.lanes):
            assert abs(p.departed-sum(coupled.left[g].values())) < 1e-7
        costs[arm] = parts(prediction)
        if branch_partition=='off':
            reference=e.load(HERE/'urban_route_transport_space_v1_network_intent_current_limits'/f'prediction_{arm}.json')
            if json.loads(json.dumps(prediction))!=reference:
                e.save(out/f'failed_prediction_{arm}.json',prediction)
                raise AssertionError('Disabled partition changed the full prediction')
        if branch_exchange=='off' and branch_partition=='on' and partition_context!='on':
            reference=e.load(HERE/'urban_route_transport_space_v1_network_intent_current_limits_partition_on_v4'/f'prediction_{arm}.json')
            if json.loads(json.dumps(prediction))!=reference:
                e.save(out/f'failed_prediction_{arm}.json',prediction)
                raise AssertionError('Disabled spatial exchange changed the full prediction')
        summary = dict(checks=checks, off_departures=[p.departed for p in coupled.lanes],
            off_admitted=[p.admitted for p in coupled.lanes], off_n=[p.stock for p in coupled.lanes],
            urban_checks=coupled.urban.checks, urban_projection_m=coupled.urban.projection,
            local_urban_ttt_veh_h=coupled.urban.vehicle_seconds/3600,
            urban_unaccepted_end=sum(q.stock for q in coupled.pending.values()),
            initial_cohort_normal_off_exits=sum(n for counts in coupled.left for (dest, vid), n in counts.items() if vid is not None),
            initial10635_normal_off_exits=sum(n for counts in coupled.left for (dest, vid), n in counts.items() if vid is not None and dest == 10635),
            score=e.score_rollout(data, start, prediction, 'FW_E') if arm == 'none' else None)
        if transport_step is not None:
            summary['west_state_score']=e.score_rollout(data,start,prediction,'FW_W') if arm=='none' else None
        summaries[arm] = summary
        e.save(out/f'prediction_{arm}.json', prediction)
        e.save(out/f'local_{arm}.json', dict(summary=summary, trace=coupled.trace, offers=offers,
            off_left=[[[*label], n] for counts in coupled.left for label, n in counts.items()],
            urban_departed=[[[*label], n] for label, n in coupled.urban.departed.items()],
            blocked_seconds=[[str(key), n] for key, n in coupled.urban.blocked_seconds.items()],
            movements=[[str(key), n] for key, n in coupled.urban.movements.items()],
            final_cells=[[list(key), list(queue.q)] for key, queue in coupled.urban.cells.items()]))
        print(arm, {k:v for k,v in summary.items() if k != 'score'}, flush=True)
    deltas = {arm: {part: n-costs['none'][part] for part, n in value.items()} for arm, value in costs.items() if arm != 'none'}
    for row in deltas.values(): row['total'] = sum(row.values())
    for path, pin in pins.items(): assert hashlib.sha256((e.ROOT/path).read_bytes()).hexdigest() == pin
    e.save(out/'result.json', dict(costs=costs, deltas=deltas, summaries=summaries, source_pins_verified=True,
        future_traffic_inputs=False, production_adopted=False, qualified=False,
        scope='East mainline/on/off component gain; new local urban cost tracked separately, not Omega TTT.'))
    print('deltas', deltas, flush=True)


def local_recovery_probe(prefer_receiving=False):
    """Short causal subsystem forecasts; neither model fitting nor gain gate.

    Future on-road observations are labels only. External arrivals repeat the
    preceding150s, with rejected offers kept in explicit upstream queues.
    """
    out=HERE/('urban_local_recovery_space_v1' if prefer_receiving else 'urban_local_recovery_v2');out.mkdir(exist_ok=False)
    source=HERE/'route_state_native_v1'
    network=source/'none_s23/source/baseline.inpx'
    root=ET.parse(network).getroot()
    link71=next(x for x in root.findall('./links/link') if x.get('no')=='71')
    behavior=next(x for x in root.findall('./drivingBehaviors/drivingBehavior') if x.get('no')=='1')
    clearance=float(behavior.get('w74ax'))
    speed=float(link71.get('mesoSpeed'))/3.6
    routes,exits=geometry(network)
    evidence=HERE/'urban_drain_observations_v5/s23_none_evidence.json'
    _,program,offset=dataset(evidence.with_name('s23_none.csv'),evidence)
    wave=e.load(HERE/'off_spatial_supply_v1/result.json')['wave_m_s']
    config=(HERE/'off_spatial_transport_cumulative_v1/config.json').resolve()
    data=e.ObservationData(CASES[1][1]);model=e.load_base_model(data.geometry,config)
    port=model.offramps['10643'];profile=e.load(MODEL/'port_profile.json')
    sources=[Path(__file__),network,config,evidence,evidence.with_name('s23_none.csv'),
             HERE/'off_spatial_supply_v1/result.json',MODEL/'port_profile.json',
             HERE/'off_spatial_transport.py',HERE/'route_access_observer.py']
    summaries={}
    for case in ('none_s23','vsl_s23'):
        frame_path=source/case/'analysis/frames.json';raw=e.load(frame_path)
        frames={f['time_s']:f for f in raw['frames']};sources.append(frame_path)
        for start in (2510,2810):
            end=start+40
            past={t:f for t,f in frames.items() if start-150<=t<=start}
            current=observe(past[start],routes,exits)
            history=history_inputs(past,start,routes,exits)
            indices={t:{v[0]:v for v in past[t]['vehicles']} for t in past}
            off_arrivals=defaultdict(Counter)
            for t in range(start-149,start+1):
                for vid,v in indices[t].items():
                    if v[1]==10643 and vid not in indices[t-1]:
                        off_arrivals[(t-start-1)%150][v[2]-1]+=1.
            modes=('base','prefer_receiving') if prefer_receiving else ('base','whole_body_start_space','defer_while_forward_open')
            for mode in modes:
                name=f'{case}_{start}_{mode}'
                lanes=[CumulativeLane(port['storage_capacity_veh']/2,port['length_m'],
                    profile['travel_speed_kmh']['10643'],
                    [(v['position_m'],v['speed_kmh'],v['length_m']) for v in current['vehicles']
                     if v['link']==10643 and v['lane']==g],start,wave) for g in (1,2)]
                coupled=CoupledPort(lanes,current,history,network,program,offset,speed,
                                   2*port['length_m']/port['storage_capacity_veh'],wave,True,False,False)
                if mode=='whole_body_start_space':
                    coupled.urban.lateral_start_footprints={v['vehicle']:v['length_m']+clearance for v in current['vehicles']}
                    coupled.urban.lateral_start_footprints[None]=sum(v['length_m']+clearance for v in current['vehicles'])/len(current['vehicles'])
                elif mode=='defer_while_forward_open':
                    coupled.urban.defer_mandatory_while_forward_open=True
                elif mode=='prefer_receiving':
                    coupled.urban.prefer_more_receiving_space=True
                pending=[0.,0.];ledger=[]
                for t in range(start,end):
                    coupled.step(t)
                    for g,p in enumerate(lanes):
                        pending[g]+=off_arrivals[(t-start)%150][g]
                        n=min(pending[g],p.receiving(1));p.accept(t+1,n)
                        coupled.admit(g,n);pending[g]-=n
                    ledger.append(dict(time_s=t+1,urban_departed=[[[*lab],n] for lab,n in coupled.urban.departed.items()],
                        off_departures=[p.departed for p in lanes],outside_off_n=list(pending)))
                summary=dict(off_departures=[p.departed for p in lanes],urban_departed=sum(coupled.urban.departed.values()),
                    local_ttt_veh_h=coupled.urban.vehicle_seconds/3600,projection_m=coupled.urban.projection,
                    urban_checks=coupled.urban.checks,outside_off_n=pending,
                    outside_urban_n=sum(q.stock for q in coupled.pending.values()))
                summaries[name]=summary
                e.save(out/f'{name}.json',dict(summary=summary,trace=coupled.trace,ledger=ledger,
                    current_start=current,history=history))
                print(name,summary,flush=True)
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    e.save(out/'result.json',dict(summary=summaries,source_pins=pins,future_traffic_inputs=False,
        forecast_horizon_s=40,production_adopted=False,qualified=False,
        assumptions=['Current/past150s only; observed traffic after cutoff is never a boundary input.',
            'Whole-body space is a diagnostic cell-threshold hypothesis, not an established insertion law.',
            'Local urban cost is notOmega; surrounding mainline feedback is outside this short subsystem probe.']))


def boundary_oracle():
    """Identification ONLY: replay observed accepted arrivals as offered flows.

    An observed vehicle may wait outside this model if its predicted receiving
    space is insufficient. This is reported; it is not erased or force-inserted.
    Future routes are read only on each entry frame, never from later exits.
    """
    out = HERE/'urban_route_boundary_oracle_v1'
    out.mkdir(exist_ok=False)
    source = HERE/'route_state_native_v1'
    network = source/'none_s23/source/baseline.inpx'
    routes, exits = geometry(network)
    evidence = HERE/'urban_drain_observations_v5/s23_none_evidence.json'
    _, program, offset = dataset(evidence.with_name('s23_none.csv'), evidence)
    root = ET.parse(network).getroot()
    speed = float(next(x for x in root.findall('./links/link') if x.get('no') == '71').get('mesoSpeed'))/3.6
    # Obtain unchanged off geometry and travel speed through the canonical loader.
    _, folder, _, _ = CASES[1]
    data = e.ObservationData(folder)
    model = e.load_base_model(data.geometry, HERE/'urban_route_transport_lateral_v1/config.json')
    off = model.offramps['10643']
    profile = e.load(MODEL/'port_profile.json')
    wave = e.load(HERE/'off_spatial_supply_v1/result.json')['wave_m_s']
    sources = [Path(__file__), network, evidence, evidence.with_name('s23_none.csv'),
               HERE/'off_spatial_supply_v1/result.json', MODEL/'port_profile.json',
               HERE/'off_spatial_transport.py', HERE/'off_spatial_supply.py', HERE/'route_access_observer.py',
               source/'none_s23/analysis/frames.json', source/'vsl_s23/analysis/frames.json']
    pins = {str(p.relative_to(e.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    summary = {}
    for case in ('none_s23', 'vsl_s23'):
        raw = e.load(source/case/'analysis/frames.json')
        frames = {f['time_s']: f for f in raw['frames'] if 2250 <= f['time_s'] <= 2850}
        past = {t: f for t, f in frames.items() if t <= 2400}
        current = observe(past[2400], routes, exits)
        history = history_inputs(past, 2400, routes, exits)
        observed = {t: {v['vehicle']: v for v in observe(frames[t], routes, exits)['vehicles']}
                    for t in range(2400, 2851)}
        off_events, background = defaultdict(list), defaultdict(list)
        for t in range(2401, 2851):
            for vid, v in observed[t].items():
                if vid in observed[t-1]: continue
                if v['link'] == 10643:
                    off_events[t].append((v['lane']-1, tagged(v)))
                else:
                    if (v['link'], v['lane']) not in ((126,1), (126,2), (71,4), (71,5)):
                        raise ValueError(('Unexplained oracle local entry', t, v))
                    background[t-2401].append((v['link'], v['lane'], v['connector'], 1.))
        for mode in ('past_urban', 'actual_urban'):
            forecast = copy.deepcopy(history)
            if mode == 'actual_urban':
                forecast['background'] = dict(background)
                forecast['repeat_period_s'] = 450
            travel_speed = profile['travel_speed_kmh']['10643']
            lanes = [CumulativeLane(off['storage_capacity_veh']/2, off['length_m'], travel_speed,
                [(v['position_m'], v['speed_kmh'], v['length_m']) for v in current['vehicles']
                 if v['link'] == 10643 and v['lane'] == lane], 2400, wave) for lane in (1,2)]
            coupled = CoupledPort(lanes, current, forecast, network, program, offset, speed,
                                  2*off['length_m']/off['storage_capacity_veh'], wave, True)
            pending = [FIFO(), FIFO()]
            offered = [0, 0]
            upstream_wait = 0.
            for t in range(2400,2850):
                coupled.step(t)
                for g, label in off_events[t+1]:
                    pending[g].append(label, 1.)
                    offered[g] += 1
                for g, lane in enumerate(lanes):
                    amount = min(pending[g].stock, lane.receiving(1))
                    packets = pending[g].take(amount)
                    lane.accept(t+1, amount)
                    for label, n in packets:
                        coupled.fifo[g].append(label, n)
                        coupled.entered[g][label] += n
                    if abs(offered[g]-lane.admitted-pending[g].stock) > 1e-7:
                        raise ArithmeticError('Unaccepted native arrival vanished')
                coupled.check()
                upstream_wait += sum(q.stock for q in pending)
            initial_ids = {v['vehicle'] for v in current['vehicles'] if v['link'] == 10643}
            result = dict(normal_off_exits=[p.departed for p in lanes], admitted=[p.admitted for p in lanes],
                off_residence_veh_h=sum(p.residence_veh_h for p in lanes),
                initial10635_off_exits=sum(n for counts in coupled.left for (dest,vid), n in counts.items()
                                          if dest == 10635 and vid in initial_ids),
                off_native_arrivals_offered=offered, off_unaccepted=[q.stock for q in pending],
                off_upstream_wait_vehicle_seconds=upstream_wait,
                background_entries_actual=sum(len(v) for v in background.values()),
                background_pending=sum(q.stock for q in coupled.pending.values()),
                urban_checks=coupled.urban.checks,
                urban_n=sum(q.stock for q in coupled.urban.cells.values()))
            summary[f'{case}:{mode}'] = result
            e.save(out/f'{case}_{mode}.json', dict(summary=result, trace=coupled.trace))
            print(case, mode, result, flush=True)
    for path, pin in pins.items(): assert hashlib.sha256((e.ROOT/path).read_bytes()).hexdigest() == pin
    e.save(out/'result.json', dict(summary=summary, source_pins=pins, source_pins_verified=True,
        future_traffic_inputs=True, operational_prediction=False, qualified=False,
        caveats=['Future accepted off arrivals are offered demand for identification only, not desired upstream demand.',
                 'Future urban entry times/labels are an explicit oracle in actual_urban mode.',
                 'All unaccepted arrivals remain in outside queues with separately reported waiting.',
                 'Native lane changes within10643 and abnormal removals are not imposed on the model.',
                 'This isolates conditional downstream response; it cannot qualify any control gain.']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--lateral-access', action='store_true')
    parser.add_argument('--boundary-oracle', action='store_true')
    parser.add_argument('--history-exchange', action='store_true')
    parser.add_argument('--continuation', action='store_true')
    parser.add_argument('--nc-only', action='store_true')
    parser.add_argument('--local-recovery', action='store_true')
    parser.add_argument('--defer-mandatory', action='store_true')
    parser.add_argument('--defer-destinations', type=int, nargs='+')
    parser.add_argument('--prefer-receiving', action='store_true')
    parser.add_argument('--trace-limits', action='store_true')
    parser.add_argument('--network-exit-intent', action='store_true')
    parser.add_argument('--current-exit-intent', action='store_true')
    parser.add_argument('--branch-partition', choices=['off','on'])
    parser.add_argument('--branch-exchange', choices=['off','on'])
    parser.add_argument('--partition-context', choices=['off','on'])
    parser.add_argument('--transport-step',type=int,choices=[1,2,5,10])
    args = parser.parse_args()
    if args.local_recovery: local_recovery_probe(args.prefer_receiving)
    elif args.boundary_oracle: boundary_oracle()
    elif args.probe: run_probe(args.lateral_access, args.history_exchange, args.continuation, args.nc_only,args.defer_mandatory,args.defer_destinations,args.prefer_receiving,args.trace_limits,args.network_exit_intent,args.current_exit_intent,args.branch_partition,args.branch_exchange,args.partition_context,args.transport_step)
    else: unittest.main(argv=[sys.argv[0]])
