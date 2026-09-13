"""Actual native schedule/configuration plus finite route-source dynamics."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import json,os,pickle,tempfile,unittest,xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
ROOT=Path(__file__).resolve().parents[1]
from diagnostics.probe_model_area_integration import build_projected
from diagnostics.route_input_fixtures import fixture_path
from evaluation.controllers import route_choice_corridor as rc,area_runtime,native_internal_input
from evaluation.controllers.control_area_objective import ModelAreaLedger,emit_input

@lru_cache(maxsize=1)
def base(second=900,calibrated=False):
    os.environ['RW_MAINLINE_SG_ONLY']='1';os.environ['RW_OFFSET_WRITER']='experiment'
    tuning=json.loads((ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json').read_text())
    suffix='sc15_calibrated' if calibrated else 'ver2'
    # This fixture owns its six-input contract; do not inherit newly promoted
    # route/input repairs or append duplicate source stores from active configs.
    tuning['urban']['route_choice_corridor']['evidence_paths'] = ['diagnostics/route_choice_corridor_ver2.json','diagnostics/route_choice_corridor_1128_ver2.json',
        f'diagnostics/route_choice_corridor_1099_{suffix}.json',f'diagnostics/route_choice_corridor_1100_{suffix}.json']
    tuning['urban'].pop('native_input_signal_authority',None)
    contract=json.loads((ROOT/'diagnostics/native_internal_input_1091_ver2.json').read_text())
    for no,source,decision in [('1086','343','1099'),('1087','341','1100')]:
        contract['inputs'][no]={'physical_source':source,'target_storage':'native_'+no+'_choice','target_kind':'route_choice',
            'source_decision':decision,'approach_path':[source],'physical_projection_links':[]}
    run=fixture_path(ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910/decisions_codex_area_observed_nc_s13_20260910')
    # Keep the validated input evidence available for the fixture lifetime; the
    # runtime rechecks its pinned source during projection preparation.
    directory=Path(tempfile.mkdtemp(prefix='native_choice_fixture_',dir=ROOT/'diagnostics'))
    import atexit,shutil
    def cleanup():
        target=directory.resolve()
        if not target.is_relative_to((ROOT/'diagnostics').resolve()):raise ValueError('Fixture cleanup escaped diagnostics')
        shutil.rmtree(target)
    atexit.register(cleanup)
    evidence=directory/'native.json';evidence.write_text(json.dumps(contract),encoding='utf-8')
    tuning['urban']['native_internal_inputs']=str(evidence.relative_to(ROOT));config=directory/'config.json';config.write_text(json.dumps(tuning),encoding='utf-8')
    raw_path=run/(f'state_{second:06d}.json' if second==900 else f'anchor_{second:06d}.json')
    result=build_projected(config,raw_path,run/'action_000001.json',fixture_inputs=False)
    from src.models.state import ControlAction
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    action=adapter.control_from_json(run/'action_000001.json',result[0],ControlAction)
    return result,action

def fixture(cohorts=None,index=None,second=900,calibrated=False):
    (cfg,state,detectors,tuning,raw,mapping,metadata),action=deepcopy(base(second,calibrated))
    if cohorts is not None:
        index=round(state.time_sec/cfg.simulation.T_u_sec) if index is None else index
        state.time_sec=index*cfg.simulation.T_u_sec
        local={'cohorts':deepcopy(cohorts),'last_step':index-1,'service_used_veh':{},'service_limit_veh':{},'received_veh':0.,'departed_veh':0.}
        state.route_choice_corridor_state=local;stocks=deepcopy(state._control_area_ledger.stocks)
        for spec in rc._specs(cfg):
            for storage,cap in spec['capacity_veh'].items():
                count=rc._tracked(local,storage);state.urban_link_storage[storage]=cap-count;stocks['storage:'+storage]={'inside':count,'outside':0.}
        state._control_area_ledger=ModelAreaLedger(stocks)
        state.native_internal_input_state['last_step']=index-1
    return cfg,state,action,raw,detectors

def worker(payload):
    cfg,state,control,index=pickle.loads(payload);rc.advance(state,control,None,cfg,index)
    state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
    return pickle.dumps((state.route_choice_corridor_state,state.urban_link_storage,state._control_area_ledger.stocks))


def endpoint_worker(payload):
    cfg,state,control,raw,detectors,depth=pickle.loads(payload)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,runtime_setup
    from src.models.demand import DemandStep
    runtime_setup.install_worker_runtime(adapter,cfg,raw,detectors)
    from src.controllers.rollout_endpoint import ObjectiveSpec,evaluate_price_point
    result=evaluate_price_point(state,control,adapter.demand_from_state(raw,cfg,DemandStep,depth),[],ObjectiveSpec(cfg,depth_override=depth,score_mode='raw'))
    for item in result.states:item._control_area_ledger.assert_stocks(area_runtime.model_inventory(item,cfg))
    return result.control_area,result.states[-1].route_choice_corridor_state,result.states[-1].native_internal_input_state

def cohort(route,amount=2.,passed=False,due=0):
    row=rc._cohort('native_1086_choice','prefix_tagged',route,amount,due,source='synthetic_observed_current_route',speed=30.)
    row['native_service_passed']=passed;return row

class NativeRouteChoice(unittest.TestCase):
    def test_capture_native_head_shared_budget_red_and_passed_scope(self):
        from diagnostics.test_route_choice_corridor import resource_capture_pair,assert_resource_capture_exact
        for index,passed in ((5,False),(20,False),(20,True)):
            with self.subTest(index=index,passed=passed):
                cfg,seed,action,_,_=fixture([cohort('1',passed=passed),cohort('2')],index)
                left,right=resource_capture_pair(seed,cfg,index)
                a=rc.advance(left,action,None,cfg,index);b=rc.advance(right,action,None,cfg,index)
                self.assertEqual(a,b);assert_resource_capture_exact(self,left,right)
                rows=right._control_area_ledger.response()['resource_allocations']
                heads=[r for r in rows if r['kind']=='native_fixed_head_service']
                self.assertEqual(len(heads),1 if passed else 2)
                self.assertEqual({r['resource'] for r in heads},{'SC15:SG5'})
                total=sum(r['accepted_total_veh'] for r in heads)
                if index==20:self.assertEqual(total,0.)
                else:
                    self.assertGreater(total,0.)
                    self.assertAlmostEqual(heads[1]['available_veh'],heads[0]['available_veh']-heads[0]['accepted_total_veh'])
                right._control_area_ledger.assert_stocks(area_runtime.model_inventory(right,cfg))

    def test_native_source_authority_is_explicit_not_a_blanket_head_exception(self):
        cfg,_,_,_,_=fixture();doc=json.loads((ROOT/'diagnostics/route_choice_corridor_1099_ver2.json').read_text())
        tree=ET.parse(ROOT/doc['network']['path']).getroot()
        heads={x.get('no'):x for x in tree.findall('./signalHeads/signalHead')};links={x.get('no'):x for x in tree.findall('./links/link')}
        for change in ('undeclared_input','wrong_signal_group','wrong_controller_offset'):
            bad=deepcopy(doc)
            if change=='undeclared_input':bad['generated_inputs']={}
            elif change=='wrong_signal_group':bad['native_fixed_service']['signal_group']='1'
            else:bad['native_fixed_service']['controller_offset_sec']=1
            with self.subTest(change=change),self.assertRaises(ValueError):rc._native_generation_contract(bad,tree,heads,links,cfg)

    def test_all_eight_observed_anchors_exact(self):
        for second in (900,1500,1800,2100,2700,3600,4500,5400):
            with self.subTest(second=second):
                cfg,state,_,raw,_=fixture(second=second)
                self.assertEqual(rc.diagnostics(state,cfg)['route_choice_held_unknown_route_veh'],0)
                self.assertEqual(state._control_area_ledger.event_count,0)
                state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
                physical=json.loads((ROOT/'diagnostics/control_area_membership.json').read_text())
                inside=set(physical['inside_links'])
                self.assertAlmostEqual(sum(v['inside'] for v in state._control_area_ledger.stocks.values()),sum(v for k,v in raw['vehicle_records']['full_network_link_counts'].items() if k in inside))

    def test_actual_projection_routes_no_initial_events(self):
        cfg,state,action,raw,detectors=fixture();specs={s['decision']:s for s in rc._specs(cfg)}
        assignment=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        routes={r['veh_no']:r for r in raw['vehicle_routes']['records']}
        for no,source,decision in [('1086','343','1099'),('1087','341','1100')]:
            storage='native_'+no+'_choice';records=[r for r in raw['vehicle_records']['records'] if str(r['link_no'])==source]
            self.assertEqual(assignment[source],{'storage:'+storage:float(len(records))})
            self.assertNotIn(source,detectors['native_internal_verified_physical_stock'])
            self.assertEqual(detectors['route_choice_verified_physical_stock'][source],storage)
            actual=sorted(str(routes[r['veh_no']]['route_no']) for r in records if routes[r['veh_no']]['route_decision_no']==int(decision))
            tagged=sorted(c['route'] for c in state.route_choice_corridor_state['cohorts'] if c['storage']==storage and c['route'])
            self.assertEqual(actual,tagged)
            self.assertAlmostEqual(specs[decision]['branches']['1']['share'],4/7)
            self.assertAlmostEqual(specs[decision]['branches']['2']['share'],3/7)
        self.assertEqual(sum(v['inside'] for v in state._control_area_ledger.stocks.values()),1763.)
        self.assertEqual(state._control_area_ledger.event_count,0)
        self.assertEqual(rc.diagnostics(state,cfg)['route_choice_held_unknown_route_veh'],0)

    def test_native_generation_accepted_once_no_generic_shadow(self):
        cfg,state,action,raw,detectors=fixture([])
        from src.models.demand import DemandStep
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        demand=adapter.demand_from_state(raw,cfg,DemandStep,1)[0]
        index=round(state.time_sec/cfg.simulation.T_u_sec)
        before=sum(v['inside'] for v in state._control_area_ledger.stocks.values())
        rc.advance(state,action,demand,cfg,index)
        result=native_internal_input.advance(state,action,demand,cfg,index)['native_internal_input_step']
        admitted=sum(row['generated_inside_veh'] for row in result.values())
        self.assertAlmostEqual(sum(v['inside'] for v in state._control_area_ledger.stocks.values())-before,admitted)
        for no in ('1086','1087'):
            storage='native_'+no+'_choice';amount=result[no]['generated_inside_veh'];self.assertGreater(amount,0)
            self.assertAlmostEqual(rc._tracked(state.route_choice_corridor_state,storage),amount)
            self.assertNotIn(storage,state.urban_arrival_buffer);self.assertNotIn(storage,state.urban_storage_release_buffer)
            with self.assertRaisesRegex(ValueError,'exactly once'):rc.receive_generated(state,cfg,no,amount,index)
        self.assertEqual(state._control_area_ledger.metrics.entered_veh,0.)
        self.assertEqual(state._control_area_ledger.metrics.ttd_veh,0.)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_future_choice_only_at_eligible_due_and_preserves_total(self):
        pre=rc._cohort('native_1086_choice','prechoice',None,7.,6,source='synthetic_generated',speed=30.)
        pre['native_service_passed']=False
        cfg,state,action,_,_=fixture([pre],5)
        rc.advance(state,action,None,cfg,5);self.assertEqual(state.route_choice_corridor_state['cohorts'][0]['route'],None)
        rc.advance(state,action,None,cfg,6)
        tags={c['route']:c['vehicles'] for c in state.route_choice_corridor_state['cohorts']}
        self.assertEqual(tags,{'1':4.,'2':3.});self.assertEqual(state._control_area_ledger.event_count,0)

    def test_shared_one_lane_budget_and_red_head(self):
        # t25~30 is green; two route tags share one lane's capacity, not two.
        cfg,state,action,_,_=fixture([cohort('1'),cohort('2')],5)
        spec=next(s for s in rc._specs(cfg) if s['decision']=='1099');limit=spec['per_lane_capacity_veh_h']*cfg.simulation.T_u_h
        rc.advance(state,action,None,cfg,5)
        self.assertAlmostEqual(state.route_choice_corridor_state['departed_veh'],limit)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
        cfg,state,action,_,_=fixture([cohort('1'),cohort('2')],20)
        rc.advance(state,action,None,cfg,20);self.assertEqual(state.route_choice_corridor_state['departed_veh'],0.)

    def test_past_head_observation_not_gated_twice(self):
        cfg,state,action,_,_=fixture([cohort('1',passed=True),cohort('2')],20)
        rc.advance(state,action,None,cfg,20)
        self.assertGreater(state.route_choice_corridor_state['departed_veh'],0.)
        self.assertEqual(next(c for c in state.route_choice_corridor_state['cohorts'] if c['route']=='2')['vehicles'],2.)

    def test_full_receiver_holds_then_releases_once(self):
        cfg,state,action,_,_=fixture([cohort('1')],5);target='SC1_to_SC101'
        state.urban_link_storage[target]=0.;state._control_area_ledger.stocks['storage:'+target]={'inside':cfg.network.urban_link_storage_veh[target],'outside':0.}
        rc.advance(state,action,None,cfg,5);self.assertEqual(rc._tracked(state.route_choice_corridor_state,'native_1086_choice'),2.)
        # Deliberately create one unit of receiver space in a new initial fixture
        # ledger. This is boundary-condition setup, not a hidden runtime loss.
        state.urban_link_storage[target]=1.;state._control_area_ledger.stocks['storage:'+target]['inside']-=1.
        for movement,spec in cfg.network.urban_movements.items():
            if spec['origin']==target:
                state.urban_movement_queue[movement]=0.;state._control_area_ledger.stocks['movement:'+movement]={'inside':0.,'outside':0.}
        rc.advance(state,action,None,cfg,6);self.assertLess(rc._tracked(state.route_choice_corridor_state,'native_1086_choice'),2.)
        self.assertEqual(state._control_area_ledger.event_count,1)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_copy_and_fresh_worker_same_native_program(self):
        cfg,state,action,_,_=fixture([cohort('1'),cohort('2')],5);payload=pickle.dumps((cfg,state,action,5))
        expected=worker(payload)
        with ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn')) as pool:actual=pool.submit(worker,payload).result(timeout=30)
        self.assertEqual(pickle.loads(actual),pickle.loads(expected))
        self.assertEqual(state.route_choice_corridor_state['departed_veh'],0.)

    def test_actual_450s_endpoint_and_fresh_worker(self):
        cfg,state,action,raw,detectors=fixture();before=deepcopy(state.route_choice_corridor_state)
        payload=pickle.dumps((cfg,state,action,raw,detectors,3));expected=endpoint_worker(payload)
        with ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn')) as pool:
            actual=pool.submit(endpoint_worker,payload).result(timeout=45)
        self.assertEqual(actual,expected);self.assertEqual(state.route_choice_corridor_state,before)
        self.assertGreater(expected[0]['ttt_veh_h'],0)
        self.assertEqual(sum(c['vehicles'] for c in expected[1]['cohorts'] if c['stage']=='unknown'),0)
        for no in ('1086','1087'):
            self.assertGreater(expected[2]['inputs'][no]['admitted_veh'],0)

    def test_omega_off_keeps_same_450s_physics(self):
        cfg,state,action,raw,detectors=fixture()
        from evaluation.controllers import vissim_stackelberg_adapter as adapter,area_meter_finalization
        from src.models.demand import DemandStep
        from src.simulation import coupling
        action=area_meter_finalization.finalize(action.copy(),cfg)
        forecast=adapter.demand_from_state(raw,cfg,DemandStep,3)
        states=[]
        for enabled in (True,False):
            private_cfg=deepcopy(cfg);private_cfg.network.control_area_enabled=enabled;current=state.copy()
            if not enabled:del current._control_area_ledger
            for demand in forecast:
                coupling.run_coupled_interval(current,action.copy(),demand,private_cfg)
                current.time_sec+=private_cfg.simulation.T_c_sec
            states.append((area_runtime.model_inventory(current,private_cfg),current.freeway_speed,
                current.route_choice_corridor_state,current.native_internal_input_state,current.urban_arrival_buffer,current.urban_storage_release_buffer))
        self.assertEqual(pickle.dumps(states[0]),pickle.dumps(states[1]))

if __name__=='__main__':unittest.main()
