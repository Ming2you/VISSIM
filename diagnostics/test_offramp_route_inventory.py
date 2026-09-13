"""Bounded route/stock tests; no VISSIM, trajectory reads or solver rollout."""
from pathlib import Path
import copy
import hashlib
import json
import math
import pickle
import sys
import subprocess
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import offramp_routing as routing
from evaluation.controllers import area_freeway_accounting as accounting
from src.models.state import ExperimentConfig, TrafficState, ControlAction
from src.models.demand import DemandStep

CONTRACT = 'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/offramp_route_inventory_v1.json'
RAW = 'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2/state_000900.json'
MISSED_EXIT_RAW = ('evaluation/runs/codex_phys8_fidelity_fw080_u050_cl9000_s13_v1/'
    'decisions_codex_phys8_fidelity_fw080_u050_cl9000_s13_v1/state_003150.json')


def observed_fixture(runtime, raw_path=RAW):
    raw = json.loads((ROOT/raw_path).read_text(encoding='utf-8-sig'))
    cfg = ExperimentConfig()
    cfg.network.freeway_segments_per_link = 21
    cfg.network.offramp_route_inventory = copy.deepcopy(runtime)
    cfg.network.off_ramps = sorted({r['group'] for r in runtime['branches'].values()})
    cfg.network.off_ramp_from_freeway = {r['group']:r['freeway'] for r in runtime['branches'].values()}
    cfg.network.ramps = []
    cfg.network.ramp_to_freeway = {}
    state = TrafficState.initial(cfg)
    state.time_sec = raw['sim_sec']
    state.ramp_queue = {}
    for fw, rows in raw['freeway_segments'].items():
        state.freeway_effective_lanes[fw] = [row['lanes'] for row in rows]
        state.freeway_density[fw] = [row['count']/(cfg.network.freeway_segment_length_km*row['lanes']) for row in rows]
        state.freeway_speed[fw] = [60. for _ in rows]
    routing.initialize_inventory(state,cfg,raw)
    return cfg,state,raw


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT/CONTRACT).read_text())
        cls.mapping = json.loads((ROOT/cls.document['mapping']['path']).read_text(encoding='utf-8-sig'))
        cls.runtime = routing.compile_inventory(cls.document,cls.mapping)

    def test_absent_option_is_exact_noop(self):
        cfg,state = NS(network=NS()), NS(ordinary={'a':[1,2]})
        before = pickle.dumps((cfg,state))
        self.assertEqual(routing.configure_inventory(cfg,{},None,None),{})
        self.assertEqual(routing.initialize_inventory(state,cfg,None),{})
        self.assertEqual(pickle.dumps((cfg,state)),before)

    def test_eight_physical_cells_and_origins(self):
        self.assertEqual({k:v['source_cell'] for k,v in self.runtime['branches'].items()},
            {'10479':6,'10491':7,'10645':11,'10638':12,'10643':8,'10682':9,'10481':13,'10483':14})
        self.assertEqual({fw:v['input'] for fw,v in self.runtime['inputs'].items()}, {'FW_E':'1098','FW_W':'1099'})
        for row in self.runtime['inputs'].values():
            self.assertAlmostEqual(sum(row['weights'].values()),1.)
        self.assertAlmostEqual(self.runtime['inputs']['FW_W']['weights']['10479'],3/16)
        self.assertAlmostEqual(self.runtime['inputs']['FW_W']['weights']['10645'],10/16*3/12)
        self.assertAlmostEqual(self.runtime['inputs']['FW_E']['weights']['10481'],8/13.6*4/15)

    def test_known_route_kept_and_through_reaches_only_next_decision(self):
        self.assertEqual(routing._route_distribution(self.runtime,self.runtime['routes']['1132:1'],'FW_W',0),{'10479':1.})
        expected = {'10638':1/12,'10645':3/12,'terminal':8/12}
        self.assertEqual(routing._route_distribution(self.runtime,self.runtime['routes']['1132:3'],'FW_W',0),expected)
        east = routing._route_distribution(self.runtime,self.runtime['routes']['1130:2'],'FW_E',0)
        self.assertEqual(east,{'10481':4/15,'10483':3/15,'terminal':8/15})

    def test_null_after_decision_never_redraws_and_postdecision_merges_skip(self):
        fw,position,_ = routing._position(self.runtime,'120',2279.0266)
        self.assertEqual(routing._future_distribution(self.runtime,fw,position),{'terminal':1.})
        fw,position,_ = routing._position(self.runtime,'120',250.)
        self.assertIn('10638',routing._future_distribution(self.runtime,fw,position))
        for ramp in ('RM_C10490','RM_C10646','RM_C10644','RM_C10484'):
            self.assertEqual(self.runtime['merges'][ramp]['weights'],{'terminal':1.})
        self.assertNotIn('10682',self.runtime['merges']['RM_C10639']['weights'])
        self.assertNotIn('10479',self.runtime['merges']['RM_C10480']['weights'])

    def test_real_complete_900_snapshot_partitions_existing_cells(self):
        cfg,state,raw = observed_fixture(self.runtime)
        inv = state.offramp_route_inventory_state
        for fw,rows in raw['freeway_segments'].items():
            self.assertEqual([round(sum(row.values()),8) for row in inv['cells'][fw]],
                             [float(row['count']) for row in rows])
        clone = pickle.loads(pickle.dumps(state,protocol=5))
        self.assertEqual(inv,clone.offramp_route_inventory_state)
        other = state.copy()
        other.offramp_route_inventory_state['cells']['FW_E'][0]['mutation|terminal']=1
        self.assertNotEqual(inv,other.offramp_route_inventory_state)

    def test_recorded_missed_exit_keeps_current_stock_and_original_route(self):
        cfg,state,raw = observed_fixture(self.runtime, MISSED_EXIT_RAW)
        meta = routing.initialize_inventory(state,cfg,raw)
        inv = state.offramp_route_inventory_state
        self.assertEqual(meta['offramp_route_inventory_initial_known_veh'],1441)
        self.assertEqual(meta['offramp_route_inventory_initial_null_veh'],210)
        self.assertEqual(meta['offramp_route_inventory_initial_missed_target_veh'],1)
        self.assertEqual(inv['missed_target_diagnostics']['observed_missed_target_veh'],1)
        self.assertEqual(inv['missed_target_diagnostics']['current_missed_target_veh'],1.)
        self.assertEqual(inv['missed_target_diagnostics']['terminal_censored_veh'],0.)
        missed = meta['offramp_route_inventory_initial_missed_targets']
        self.assertEqual(len(missed),1)
        self.assertEqual((missed[0]['veh_no'],missed[0]['route'],missed[0]['target'],
                          missed[0]['cell']), (12602,'1130:3','10682',11))
        key = 'observed_route:1130:3|missed_target:10682'
        self.assertEqual(inv['cells']['FW_E'][11][key],1.)
        self.assertNotIn(key,inv['cells']['FW_E'][9])
        for fw,rows in raw['freeway_segments'].items():
            self.assertEqual([round(sum(row.values()),8) for row in inv['cells'][fw]],
                             [float(row['count']) for row in rows])
        self.assertEqual(inv,pickle.loads(pickle.dumps(state,protocol=5)).offramp_route_inventory_state)
        routing.assert_inventory(state,cfg,accounting.continuity_vehicle_counts(state,cfg))

    def test_missed_target_before_future_decision_is_not_redrawn(self):
        cfg,state,raw = observed_fixture(self.runtime, MISSED_EXIT_RAW)
        physical=next(r for r in raw['vehicle_records']['records'] if r['veh_no']==12602)
        branch=self.runtime['branches']['10682']
        physical['position_m']=branch['source_chain_m']-self.runtime['physical']['2'][1]+.1
        self.assertLess(branch['source_chain_m']+.1,self.runtime['decisions']['1131']['chain_m'])
        raw['freeway_segments']['FW_E'][11]['count']-=1
        raw['freeway_segments']['FW_E'][9]['count']+=1
        for i,row in enumerate(raw['freeway_segments']['FW_E']):
            state.freeway_density['FW_E'][i]=row['count']/(cfg.network.freeway_segment_length_km*row['lanes'])
        metadata=routing.initialize_inventory(state,cfg,raw)
        self.assertEqual(metadata['offramp_route_inventory_initial_missed_target_veh'],1)
        self.assertEqual(state.offramp_route_inventory_state['cells']['FW_E'][9]
                         ['observed_route:1130:3|missed_target:10682'],1.)
        self.assertEqual(state.offramp_route_inventory_state['missed_target_diagnostics']
                         ['current_missed_target_veh'],1.)

    def test_new_observed_normal_route_replaces_previous_missed_class(self):
        cfg,state,raw = observed_fixture(self.runtime, MISSED_EXIT_RAW)
        route=next(r for r in raw['vehicle_routes']['records'] if r['veh_no']==12602)
        route['route_no']=2  # Synthetic next observation of a compiled through route.
        metadata=routing.initialize_inventory(state,cfg,raw)
        self.assertNotIn('offramp_route_inventory_initial_missed_target_veh',metadata)
        inv=state.offramp_route_inventory_state
        self.assertNotIn('missed_target_diagnostics',inv)
        self.assertFalse(any('missed_target:' in k for rows in inv['cells'].values() for row in rows for k in row))
        self.assertAlmostEqual(sum(sum(row.values()) for rows in inv['cells'].values() for row in rows),1651.)

    def test_missed_static_identity_can_remain_on_downstream_mainline_link(self):
        cfg,state,raw = observed_fixture(self.runtime, MISSED_EXIT_RAW)
        physical=next(r for r in raw['vehicle_records']['records'] if r['veh_no']==12602)
        self.assertNotIn('119',self.runtime['routes']['1130:3']['path'])
        physical.update(link_no=119,position_m=1.)
        counts=raw['vehicle_records']['full_network_link_counts']
        counts['2']-=1
        counts['119']=counts.get('119',0)+1
        fw,position,cell=routing._position(self.runtime,119,1.)
        raw['freeway_segments'][fw][11]['count']-=1
        raw['freeway_segments'][fw][cell]['count']+=1
        for i,row in enumerate(raw['freeway_segments'][fw]):
            state.freeway_density[fw][i]=row['count']/(cfg.network.freeway_segment_length_km*row['lanes'])
        metadata=routing.initialize_inventory(state,cfg,raw)
        missed=metadata['offramp_route_inventory_initial_missed_targets'][0]
        self.assertFalse(missed['physical_link_on_selected_route'])
        self.assertEqual((missed['veh_no'],missed['route'],missed['target']),(12602,'1130:3','10682'))
        self.assertEqual(state.offramp_route_inventory_state['cells'][fw][cell]
                         ['observed_route:1130:3|missed_target:10682'],1.)
        # A different direction or an unknown route is still not a continuation.
        route=next(r for r in raw['vehicle_routes']['records'] if r['veh_no']==12602)
        route.update(route_decision_no=1132,route_no=1)
        with self.assertRaisesRegex(ValueError,'compiled native paths'):
            routing.initialize_inventory(state,cfg,raw)
        route.update(route_decision_no=1130,route_no=999)
        with self.assertRaisesRegex(ValueError,'compiled native paths'):
            routing.initialize_inventory(state,cfg,raw)

    def test_unaffected_recorded_900_and_3000_initialization_is_byte_exact(self):
        receipt=json.loads((ROOT/'diagnostics/control_improvement/decision_common_anchor_20260911/'
            'ramp8_physical_v1/route3150_prepatch_initialization_v1.json').read_text())
        for row in receipt['rows']:
            with self.subTest(path=row['path']):
                self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['raw_sha256'])
                cfg,state,raw=observed_fixture(self.runtime,row['path'])
                metadata=routing.initialize_inventory(state,cfg,raw)
                payload=json.dumps({'inventory':state.offramp_route_inventory_state,'metadata':metadata},
                    sort_keys=True,separators=(',',':')).encode()
                self.assertEqual(hashlib.sha256(payload).hexdigest(),row['inventory_metadata_sha256'])
                self.assertEqual(len(payload),row['serialized_bytes'])

    def test_missed_target_advects_but_does_not_become_normal_terminal_exit(self):
        runtime = {'branches':{'d':{'freeway':'FW','source_cell':0}},
            'inputs':{'FW':{'input':'1','weights':{'terminal':1.}}}, 'merges':{}}
        cfg=NS(network=NS(offramp_route_inventory=runtime))
        key='observed_route:1:1|missed_target:d'
        state=NS(mainline_origin_queue={'FW':0.},offramp_route_inventory_state={
            'schema':'offramp-route-stock/v1','cells':{'FW':[{key:4.,'known|terminal':6.},{}]},
            'origins':{'FW':{}},'missed_target_diagnostics':{'observed_missed_target_veh':4}})
        sending,branches=routing.sending_requests(state,cfg,'FW',[10.,0.],1.)
        self.assertEqual((sending,branches),([10.,0.],{'d':0.}))
        routing.advance_inventory(state,cfg,'FW',mainline=[10.],terminal=0.,offramps={},
            entry=0.,generated=0.,merges={},duration_h=1.)
        self.assertEqual(state.offramp_route_inventory_state['cells']['FW'][1][key],4.)
        for offered in (2.,10.):  # Physical sending and external terminal capacity limits.
            with self.subTest(offered=offered):
                limited=copy.deepcopy(state)
                available,_=routing.sending_requests(limited,cfg,'FW',[0.,offered],1.)
                accepted=min(available[-1],2.)
                self.assertEqual(accepted,2.)
                routing.advance_inventory(limited,cfg,'FW',mainline=[0.],terminal=accepted,offramps={},
                    entry=0.,generated=0.,merges={},duration_h=1.)
                self.assertEqual(limited.offramp_route_inventory_state['cells']['FW'][1],
                    {key:4.,'known|terminal':4.})
                routing.assert_inventory(limited,cfg,{'FW':[0.,8.]})
        sending,branches=routing.sending_requests(state,cfg,'FW',[0.,10.],1.)
        self.assertEqual((sending,branches),([0.,6.],{'d':0.}))
        routing.advance_inventory(state,cfg,'FW',mainline=[0.],terminal=6.,offramps={},
            entry=0.,generated=0.,merges={},duration_h=1.)
        self.assertEqual(state.offramp_route_inventory_state['cells']['FW'],[{}, {key:4.}])
        self.assertEqual(state.offramp_route_inventory_state['missed_target_diagnostics'],
            {'observed_missed_target_veh':4,'current_missed_target_veh':4.,'terminal_censored_veh':4.})
        self.assertEqual(routing.sending_requests(state,cfg,'FW',[0.,4.],1.),([0.,0.],{'d':0.}))
        routing.assert_inventory(state,cfg,{'FW':[0.,4.]})

    def test_route_capture_incomplete_or_stock_mismatch_fails(self):
        cfg,state,raw = observed_fixture(self.runtime)
        raw['vehicle_routes']['complete']=False
        with self.assertRaisesRegex(ValueError,'incomplete'):
            routing.initialize_inventory(state,cfg,raw)
        state.offramp_route_inventory_state['cells']['FW_E'][0]['bad|terminal']=2
        with self.assertRaisesRegex(ValueError,'partition'):
            routing.assert_inventory(state,cfg,accounting.continuity_vehicle_counts(state,cfg))

    def test_rejected_target_retained_and_other_flow_advection_is_exact(self):
        runtime = {'branches':{'d':{'freeway':'FW','source_cell':0},'s':{'freeway':'FW','source_cell':1}},
            'inputs':{'FW':{'input':'1','weights':{'s':.25,'terminal':.75}}},
            'merges':{'r':{'freeway':'FW','cell':1,'weights':{'terminal':1.}}}}
        cfg=NS(network=NS(offramp_route_inventory=runtime))
        state=NS(mainline_origin_queue={'FW':2.},offramp_route_inventory_state={
            'schema':'offramp-route-stock/v1','cells':{'FW':[{'known|d':4.,'known|s':2.,'known|terminal':4.},{}]},
            'origins':{'FW':{'expected_input:1|terminal':2.}}})
        sending,branches = routing.sending_requests(state,cfg,'FW',[10.,0.],1.)
        self.assertEqual(sending,[6.,0.])
        self.assertEqual(branches,{'d':4.,'s':0.})
        routing.advance_inventory(state,cfg,'FW',mainline=[3.],terminal=0.,offramps={'d':1.,'s':0.},
            entry=1.,generated=2.,merges={'r':2.},duration_h=1.)
        rows=state.offramp_route_inventory_state['cells']['FW']
        self.assertEqual(rows[0]['known|d'],3.)
        self.assertEqual(rows[1]['known|s'],1.)
        self.assertEqual(rows[1]['expected_merge:r|terminal'],2.)
        self.assertAlmostEqual(sum(map(lambda row:sum(row.values()),rows)),12.)
        self.assertAlmostEqual(sum(state.offramp_route_inventory_state['origins']['FW'].values()),3.)
        state.mainline_origin_queue['FW']=3.
        routing.assert_inventory(state,cfg,{'FW':[7.,5.]})

    def test_unit_freeway_step_conserves_physical_and_route_stocks(self):
        from diagnostics.test_area_freeway_accounting import seed
        cfg,state,_ = observed_fixture(self.runtime)
        ledger = seed(state,cfg)
        control=ControlAction.uncontrolled(cfg)
        demand=DemandStep({fw:500. for fw in cfg.network.freeway_links},{},{})
        before=sum(map(sum,accounting.continuity_vehicle_counts(state,cfg).values()))
        capacities={key:0. if key=='10479' else 10000. for key in self.runtime['branches']}
        _,diag=accounting._freeway_substep_events(state,control,demand,cfg,
            offramp_capacity_veh_h=capacities,ramp_release_veh_h={},update_ramp_queues=False)
        after=sum(map(sum,accounting.continuity_vehicle_counts(state,cfg).values()))
        expected=before+cfg.simulation.T_f_h*(1000.-diag['mainline_exit_flow_total']-diag['offramp_flow_total'])
        self.assertAlmostEqual(after+sum(state.mainline_origin_queue.values()),expected)
        self.assertEqual(diag['offramp_flow_branch_10479'],0.)
        self.assertAlmostEqual(diag['offramp_flow_total'],sum(diag['offramp_flow_branch_'+k] for k in self.runtime['branches']))
        routing.assert_inventory(state,cfg,accounting.continuity_vehicle_counts(state,cfg))

    def test_branch_receiving_is_separate_and_explicit_landing_never_resplits(self):
        from src.models import urban_queue_model as uqm
        from evaluation.controllers import urban_flow_accounting as urban
        cfg=ExperimentConfig();state=TrafficState.initial(cfg)
        uqm.ensure_urban_state(state,cfg)
        off=cfg.network.off_ramps[0]
        signal=cfg.network.off_ramp_storage_link[off]
        direct=next(key for key in cfg.network.urban_link_storage_veh if key!=signal)
        cfg.network.offramp_direct_share_by_offramp={off:.99}
        cfg.network.offramp_direct_tail_by_offramp={off:direct}
        cfg.network.offramp_route_inventory={'branches':{'d':{'receiver':direct},'s':{'receiver':signal}}}
        state.urban_link_storage[direct]=1.
        state.urban_link_storage[signal]=4.
        with mock.patch.object(uqm,'_effective_available_space',side_effect=lambda s,c,k:s.urban_link_storage[k]):
            self.assertEqual(routing.branch_capacities(state,cfg,.5),{'d':2.,'s':8.})
        events=[]
        def schedule(s,c,o,amount,step):
            accepted=min(s.urban_link_storage[signal],amount)
            s.urban_link_storage[signal]-=accepted
            return accepted,amount-accepted
        with mock.patch.object(urban,'_adapter',NS(_LEGSPLIT_LAST={})), \
             mock.patch.object(urban,'_original_schedule',schedule,create=True), \
             mock.patch.object(uqm,'_offramp_landing_orig_schedule',None,create=True), \
             mock.patch.object(urban,'emit_transfer',side_effect=lambda s,c,source,target,amount,**kw:events.append((target,amount))), \
             mock.patch('evaluation.controllers.route_choice_corridor.known_legsplit_receive'):
            self.assertEqual(urban.schedule_offramp_arrivals_accounted(state,cfg,off,5.,10,
                branch_vehicles={'direct':1.,'signal':4.}),(5.,0.))
        self.assertEqual(events,[('storage:'+direct,1.),('storage:'+signal,4.)])
        self.assertEqual(state.urban_link_storage[direct],0.)
        self.assertEqual(state.urban_link_storage[signal],0.)

    def test_branch_diagnostic_rate_aggregates_as_rate_not_sum(self):
        from src.simulation.coupling import _aggregate_freeway_diagnostics
        rows=[{'offramp_flow_branch_10479':3.,'offramp_blocked_flow_branch_10479':1.},
              {'offramp_flow_branch_10479':5.,'offramp_blocked_flow_branch_10479':3.}]
        result=_aggregate_freeway_diagnostics(rows)
        self.assertEqual(result,{'offramp_flow_branch_10479':4.,'offramp_blocked_flow_branch_10479':2.})

    def test_native_origin_source_forecast_totals_must_match(self):
        cfg=NS(network=NS(offramp_route_inventory={'inputs':{'FW':{'input':'1099'}}},
            native_input_schedule={'inputs':{'1099':{'schedule':[
                {'start_sec':0.,'rate_veh_h':100.},{'start_sec':950.,'rate_veh_h':400.}]}}}),
            simulation=NS(control_interval=150.))
        state=NS(time_sec=900.)
        routing.validate_origin_demand(state,cfg,NS(freeway_mainline={'FW':300.}))
        with self.assertRaisesRegex(ValueError,'native input source'):
            routing.validate_origin_demand(state,cfg,NS(freeway_mainline={'FW':100.}))

    def test_canonical_setup_preserves_raw_routes_and_native_forecast_sources(self):
        if '--setup-only' not in sys.argv:
            # Runtime installation deliberately patches canonical modules. Its
            # integration fixture must not replace later toy-test baselines.
            result=subprocess.run([sys.executable,__file__,'--setup-only'],cwd=ROOT,
                text=True,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            return
        from diagnostics.probe_model_area_integration import build_projected
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        base=ROOT/'diagnostics/selected_control_demand/codex_physical8_fw080_u050_fastnp_closedloop1350_v3/config.json'
        tuning=json.loads(base.read_text(encoding='utf-8-sig'))
        tuning['freeway']['offramp_route_inventory']=CONTRACT
        record=(ROOT/RAW).parent
        with tempfile.TemporaryDirectory(prefix='offramp_setup_') as folder:
            path=Path(folder)/'config.json';path.write_text(json.dumps(tuning),encoding='utf-8')
            cfg,state,detectors,tuning,raw,mapping,meta=build_projected(path,ROOT/RAW,
                record/'action_000750.json',fixture_inputs=False)
        self.assertEqual(meta['offramp_route_inventory_initial_known_veh'],424)
        self.assertEqual(meta['offramp_route_inventory_initial_null_veh'],144)
        self.assertEqual(len({b['receiver'] for b in cfg.network.offramp_route_inventory['branches'].values()}),8)
        calibration=adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
        calibration=adapter.deep_update(dict(calibration),tuning.get('calibration_override',{}))
        forecast=adapter.demand_from_state(raw,cfg,DemandStep,3,calibration,detectors)
        for i,demand in enumerate(forecast):
            clock=NS(time_sec=state.time_sec+i*cfg.simulation.control_interval)
            routing.validate_origin_demand(clock,cfg,demand)

    def test_constant_weights_required_and_changed_mapping_rejected(self):
        import xml.etree.ElementTree as ET
        with self.assertRaisesRegex(ValueError,'constant'):
            routing._weight(ET.fromstring('<route relFlow="2 0:2 900:3"/>'))
        mapping=copy.deepcopy(self.mapping)
        mapping['freeway_model_links']['FW_E']['segment_bounds_m'][1]+=1
        with self.assertRaisesRegex(ValueError,'geometry'):
            routing.compile_inventory(self.document,mapping)


if __name__=='__main__':
    if sys.argv[1:]==['--setup-only']:
        RoutingTests.setUpClass()
        RoutingTests('test_canonical_setup_preserves_raw_routes_and_native_forecast_sources').test_canonical_setup_preserves_raw_routes_and_native_forecast_sources()
    else:
        unittest.main()
