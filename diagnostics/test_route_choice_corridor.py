"""Focused finite-corridor tests through actual projection and ledger APIs."""
from pathlib import Path
from copy import deepcopy
from functools import lru_cache
import json, os, pickle, sys, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers import area_runtime, projection_support, sc2001_corridor, shared_approach
from evaluation.controllers.control_area_objective import ModelAreaLedger, emit_transfer, physical_membership_from_ledger
from diagnostics.route_input_fixtures import decisions


@lru_cache(maxsize=1)
def base():
    from diagnostics.probe_model_area_integration import build_projected
    os.environ['RW_MAINLINE_SG_ONLY']='1'
    run=decisions()
    result=build_projected(ROOT/'diagnostics/fixtures/area_baseline_before_route_choice_beta0.json',run/'state_001200.json',run/'action_001050.json',fixture_inputs=False)
    return result,run


def prepared_fixture(time=1350,policy='hold_diagnostic',*,route_envelope=None):
    (cfg,_,detectors,tuning,_,_,metadata),run=deepcopy(base())
    raw=json.loads((run/f'state_{time:06d}.json').read_text(encoding='utf-8-sig'))
    if route_envelope is not None: raw['vehicle_routes']=route_envelope
    tuning['urban']['route_choice_corridor']={'evidence_path':'diagnostics/route_choice_corridor_ver2.json','unknown_policy':policy}
    detectors,meta=rc.configure(cfg,tuning,raw,detectors,per_lane_capacity_veh_h=metadata['movement_capacity_by_lanes_per_lane_veh_h'])
    detectors,raw,projection=rc.prepare_projection(cfg,detectors,raw)
    return cfg,raw,detectors,tuning,meta,projection


def fixture(time=1350,policy='hold_diagnostic',*,route_envelope=None):
    cfg,raw,detectors,tuning,meta,projection=prepared_fixture(time,policy,route_envelope=route_envelope)
    detectors,raw,support=projection_support.configure(cfg,tuning,detectors,raw)
    detectors,raw,_=sc2001_corridor.prepare_projection(cfg,detectors,raw)
    from evaluation.controllers import vissim_stackelberg_adapter as a
    from src.models.state import TrafficState,ControlAction
    calibration=a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration=a.deep_update(dict(calibration),tuning.get('calibration_override',{}))
    state=a.traffic_state_from_vissim(raw,cfg,TrafficState,detectors,calibration)
    area_runtime.configure_initial_transit(cfg,tuning,state)
    shared_approach.initialize(state,cfg,raw,detectors)
    sc2001_corridor.initialize(state,cfg,raw,detectors)
    meta.update(rc.initialize(state,cfg,raw,detectors))
    physical=physical_membership_from_ledger(json.loads((ROOT/'diagnostics/control_area_membership.json').read_text(encoding='utf-8')))
    area_runtime.seed_from_projection(state,cfg,physical)
    rc.extend_area_routes(cfg)
    _,run=base()
    action=a.control_from_json(run/f'action_{time-150:06d}.json',cfg,ControlAction)
    return cfg,state,raw,detectors,action,meta


def synthetic(cohorts):
    cfg,state,raw,detectors,action,meta=fixture()
    spec=cfg.network.route_choice_corridor; index=round(state.time_sec/cfg.simulation.T_u_sec)
    state.route_choice_corridor_state={'cohorts':deepcopy(cohorts),'last_step':index-1,'service_used_veh':{},'service_limit_veh':{},'received_veh':0.,'departed_veh':0.}
    for key,capacity in spec['capacity_veh'].items():
        state.urban_link_storage[key]=capacity-rc._tracked(state.route_choice_corridor_state,key)
    stocks=deepcopy(state._control_area_ledger.stocks)
    for key in spec['capacity_veh']:
        stocks['storage:'+key]={'inside':rc._tracked(state.route_choice_corridor_state,key),'outside':0.}
    state._control_area_ledger=ModelAreaLedger(stocks)
    return cfg,state,action,index


def worker(payload):
    cfg,state,action,index=pickle.loads(payload)
    rc.advance(state,action,None,cfg,index)
    state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
    return pickle.dumps((state.route_choice_corridor_state,state.urban_link_storage,state.urban_movement_queue,state._control_area_ledger.stocks))


def resource_capture_pair(state, cfg, step):
    """Same existing stock/counters, only the optional response differs."""
    pair = [state.copy(), state.copy()]
    for candidate, capture in zip(pair, (False, True)):
        old = candidate._control_area_ledger
        ledger = ModelAreaLedger(old.stocks, capture_response=capture)
        for key, value in vars(old).items():
            if not key.startswith('_response'):
                setattr(ledger, key, deepcopy(value))
        ledger.begin_response_step('urban', step*cfg.simulation.T_u_sec, (step+1)*cfg.simulation.T_u_sec)
        candidate._control_area_ledger = ledger
    return pair


def assert_resource_capture_exact(test, left, right):
    for item in (left, right):
        test.assertIsNotNone(item._control_area_ledger)
    test.assertEqual(pickle.dumps({k:v for k,v in vars(left).items() if k != '_control_area_ledger'}),
                     pickle.dumps({k:v for k,v in vars(right).items() if k != '_control_area_ledger'}))
    test.assertEqual({k:v for k,v in vars(left._control_area_ledger).items() if not k.startswith('_response')},
                     {k:v for k,v in vars(right._control_area_ledger).items() if not k.startswith('_response')})


def current_routes(raw,assignments):
    from evaluation.controllers.vehicle_routes import ATTRIBUTES
    records=[]
    for row in raw['vehicle_records']['records']:
        route=assignments.get(row['veh_no'])
        records.append({'veh_no':row['veh_no'],'route_decision_no':1129 if route is not None else None,
                        'route_no':route,'route_decision_type':'STATIC' if route is not None else None})
    return {'schema_version':'vissim-vehicle-routes-v1','complete':True,'sim_sec_before':raw['sim_sec'],
            'sim_sec_after':raw['sim_sec'],'record_count':len(records),'collection_count_before':len(records),
            'collection_count_after':len(records),'source_attributes':ATTRIBUTES,'records':records}


class RouteChoiceTests(unittest.TestCase):
    def test_capture_shared10634_actual_receipts_and_queries_no_debit(self):
        from src.models import urban_queue_model as uqm
        cfg,seed,action,index=synthetic([])
        names=['SC1004_W_to_E_SC1005','SC1004_offE_to_E_SC1005','SC1004_offW_to_E_SC1005']
        index=next(i for i in range(index,index+60) if uqm._phase_green_fraction(action,cfg,cfg.network.urban_movements[names[0]],urban_step_index=i)>0)
        seed.route_choice_corridor_state['last_step']=index-1
        left,right=resource_capture_pair(seed,cfg,index)
        results=[]
        for state in (left,right):
            rc.advance(state,action,None,cfg,index)
            total=rc.intended_departure(state,action,cfg,names[0],100.,index)
            for _ in range(2):
                self.assertEqual(rc.intended_departure(state,action,cfg,names[0],100.,index),total)
            if state is right:self.assertEqual(state._control_area_ledger.response()['resource_allocations'],[])
            accepted=[]
            for name,fraction in [(names[1],.4),(names[2],.6)]:
                limit=rc.intended_departure(state,action,cfg,name,100.,index)
                amount=min(total*fraction,limit);accepted.append(amount)
                source=cfg.network.off_ramp_storage_link[cfg.network.urban_movements[name]['off_ramp']]
                target=cfg.network.route_choice_corridor['prefix_storage']
                state.urban_link_storage[source]+=amount;state.urban_link_storage[target]-=amount
                emit_transfer(state,cfg,'storage:'+source,'storage:'+target,amount,preserve_area=True)
                rc.receive_accepted(state,cfg,name,amount,index)
            results.append((total,accepted,rc.intended_departure(state,action,cfg,names[0],100.,index)))
        self.assertEqual(results[0],results[1]);assert_resource_capture_exact(self,left,right)
        rows=right._control_area_ledger.response()['resource_allocations']
        self.assertEqual([r['resource'] for r in rows],['10634','10634'])
        self.assertEqual(rows[0]['available_veh'],results[0][0])
        self.assertEqual(rows[1]['available_veh'],results[0][0]-results[0][1][0])
        self.assertAlmostEqual(sum(r['accepted_total_veh'] for r in rows),results[0][0])
        self.assertEqual(set().union(*(r['accepted_by_source_veh'] for r in rows)),{'movement:'+m for m in names[1:]})
        self.assertFalse(right._control_area_ledger.response()['shared_capacity_certificate'])
        right._control_area_ledger.assert_stocks(area_runtime.model_inventory(right,cfg))

    def test_capture_branch_budget_and_blocked_receiving_are_separate(self):
        cohorts=[rc._cohort('SC1004_E_choice','prefix_tagged',key,amount,270,speed=40.)
                 for key,amount in [('1',8.),('2',1.),('3',1.)]]
        cfg,seed,action,index=synthetic(cohorts)
        target=cfg.network.route_choice_corridor['bypass_storage']
        seed.urban_link_storage[target]=0.
        seed._control_area_ledger.stocks['storage:'+target]={'inside':cfg.network.urban_link_storage_veh[target],'outside':0.}
        left,right=resource_capture_pair(seed,cfg,index)
        self.assertEqual(rc.advance(left,action,None,cfg,index),rc.advance(right,action,None,cfg,index))
        assert_resource_capture_exact(self,left,right)
        rows=right._control_area_ledger.response()['resource_allocations']
        blocked=next(r for r in rows if r['kind']=='route_choice_receiving' and r['resource']=='storage:'+target)
        self.assertEqual((blocked['available_veh'],blocked['accepted_total_veh']),(0.,0.))
        branch=[r for r in rows if r['kind']=='route_choice_branch_service' and r['resource']=='1129:branch:local']
        self.assertEqual(len(branch),2)
        self.assertAlmostEqual(branch[1]['available_veh'],branch[0]['available_veh']-branch[0]['accepted_total_veh'])
        self.assertGreater(sum(r['accepted_total_veh'] for r in branch),0.)
        right._control_area_ledger.assert_stocks(area_runtime.model_inventory(right,cfg))

    def test_actual_1350_initial_count_and_no_entry_reward(self):
        cfg,state,raw,detectors,_,meta=fixture()
        spec=cfg.network.route_choice_corridor
        self.assertEqual(meta['route_choice_stock_veh'][spec['prefix_storage']],4.)
        self.assertEqual(meta['route_choice_stock_veh'][spec['local_storage']],1.)
        self.assertEqual(meta['route_choice_held_unknown_route_veh'],1.)
        self.assertEqual(state._control_area_ledger.metrics.ttd_veh,0.)
        self.assertEqual(state._control_area_ledger.metrics.entered_veh,0.)
        physical=physical_membership_from_ledger(json.loads((ROOT/'diagnostics/control_area_membership.json').read_text(encoding='utf-8')))
        raw_n=sum(v for k,v in raw['vehicle_records']['full_network_link_counts'].items() if physical[k])
        self.assertAlmostEqual(sum(row['inside'] for row in state._control_area_ledger.stocks.values()),raw_n)
        assignment=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(assignment['10634'],{'storage:'+spec['prefix_storage']:3.})
        self.assertEqual(assignment['56'],{'storage:'+spec['prefix_storage']:1.})
        for key in spec['capacity_veh']:
            self.assertNotIn(key,state.urban_arrival_buffer)
            self.assertNotIn(key,state.urban_storage_release_buffer)

    def test_error_policy_rejects_unknown_past_route(self):
        with self.assertRaisesRegex(ValueError,'Current1129 route required'):
            fixture(policy='error')

    def test_observed_current_route_is_preserved_and_never_redrawn(self):
        (_,run)=base()
        raw=json.loads((run/'state_001350.json').read_text(encoding='utf-8-sig'))
        routes=current_routes(raw,{4834:3})
        cfg,state,_,_,action,meta=fixture(policy='error',route_envelope=routes)
        local=[c for c in state.route_choice_corridor_state['cohorts'] if c['storage']=='SC1004_to_SC1005']
        self.assertEqual(len(local),1); self.assertEqual(local[0]['route'],'3')
        self.assertEqual(meta['route_choice_held_unknown_route_veh'],0.)
        self.assertEqual(meta['route_choice_prediction_route_complete'],1.)

    def test_shared69_continuation_uses_one_accepted_transfer_no_new_gate(self):
        cfg,state,action,index=synthetic([])
        rc.advance(state,action,None,cfg,index)
        spec=cfg.network.route_choice_corridor; source=spec['shared_continuation']['source_storage']; target=spec['prefix_storage']
        self.assertEqual(cfg.network.shared_approach['branches']['2']['target'],target)
        self.assertGreater(rc._prefix_distance(spec,'10636',0.),300.)
        amount=.25
        state.urban_link_storage[source]+=amount; state.urban_link_storage[target]-=amount
        emit_transfer(state,cfg,'storage:'+source,'storage:'+target,amount,preserve_area=True)
        events=state._control_area_ledger.event_count
        self.assertTrue(rc.receive_shared_accepted(state,cfg,source,'2',amount,index))
        self.assertEqual(state._control_area_ledger.event_count,events)
        self.assertEqual(rc._tracked(state.route_choice_corridor_state,target),amount)
        self.assertNotIn(target,state.urban_arrival_buffer)
        with self.assertRaisesRegex(ValueError,'exactly once'):
            rc.receive_shared_accepted(state,cfg,source,'2',amount,index)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_physical_service_budget_shared_across_W_offE_and_offW(self):
        cfg,state,action,index=synthetic([])
        from src.models import urban_queue_model as uqm
        spec=cfg.network.route_choice_corridor
        names=['SC1004_W_to_E_SC1005','SC1004_offE_to_E_SC1005','SC1004_offW_to_E_SC1005']
        # Use a genuine positive interval from the actual action's physical clock.
        index=next(i for i in range(index,index+60) if uqm._phase_green_fraction(action,cfg,cfg.network.urban_movements[names[0]],urban_step_index=i)>0)
        state.route_choice_corridor_state['last_step']=index-1
        rc.advance(state,action,None,cfg,index)
        total=rc.intended_departure(state,action,cfg,names[0],100.,index)
        self.assertGreater(total,0.)
        accepted=[]
        for name,fraction in [(names[1],.4),(names[2],.6)]:
            limit=rc.intended_departure(state,action,cfg,name,100.,index)
            amount=min(total*fraction,limit); accepted.append(amount)
            source=cfg.network.off_ramp_storage_link[cfg.network.urban_movements[name]['off_ramp']]
            target=spec['prefix_storage']
            state.urban_link_storage[source]+=amount; state.urban_link_storage[target]-=amount
            emit_transfer(state,cfg,'storage:'+source,'storage:'+target,amount,preserve_area=True)
            events=state._control_area_ledger.event_count
            self.assertTrue(rc.receive_accepted(state,cfg,name,amount,index))
            self.assertEqual(state._control_area_ledger.event_count,events)
        self.assertAlmostEqual(sum(accepted),total)
        self.assertAlmostEqual(rc.intended_departure(state,action,cfg,names[0],100.,index),0.)
        with self.assertRaisesRegex(ValueError,'exactly once'):
            rc.receive_accepted(state,cfg,names[1],.1,index)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_former_shared_receiver_cannot_create_unproven_external_demand(self):
        from src.models.demand import DemandStep
        cfg,state,action,index=synthetic([])
        demand=DemandStep(freeway_mainline={},urban_boundary={'in_SC1005_W':1.},ramp_arrival={})
        with self.assertRaisesRegex(ValueError,'unsupported independent external demand'):
            rc.advance(state,action,demand,cfg,index)

    def test_two_simultaneous_regular_requests_share_one_budget(self):
        cfg,state,action,index=synthetic([])
        from src.models import urban_queue_model as uqm
        names=['SC1004_W_to_E_SC1005','SC1004_offE_to_E_SC1005']
        index=next(i for i in range(index,index+60) if uqm._phase_green_fraction(action,cfg,cfg.network.urban_movements[names[0]],urban_step_index=i)>0)
        state.route_choice_corridor_state['last_step']=index-1
        rc.advance(state,action,None,cfg,index)
        intended={name:rc.intended_departure(state,action,cfg,name,100.,index) for name in names}
        self.assertGreater(sum(intended.values()),max(intended.values()))
        frozen=deepcopy(intended)
        limited=rc.limit_intended_batch(state,cfg,intended,index)
        self.assertEqual(intended,frozen)
        self.assertLessEqual(sum(limited.values()),max(intended.values())+1e-12)
        self.assertTrue(all(value>0 for value in limited.values()))
        self.assertEqual(state.route_choice_corridor_state['service_used_veh'],{})

    def test_eligible_choice_splits_once_without_stock_events(self):
        cohort=rc._cohort('SC1004_E_choice','prechoice',None,10.,270,speed=40.)
        cfg,state,action,index=synthetic([cohort])
        rc.advance(state,action,None,cfg,index)
        result={c['route']:c['vehicles'] for c in state.route_choice_corridor_state['cohorts']}
        self.assertEqual(result,{'1':8.,'2':1.,'3':1.})
        self.assertEqual(state._control_area_ledger.event_count,0)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_full_bypass_retains_its_tag_and_local_branches_proceed(self):
        cohorts=[rc._cohort('SC1004_E_choice','prefix_tagged',key,amount,270,speed=40.) for key,amount in [('1',8.),('2',1.),('3',1.)]]
        cfg,state,action,index=synthetic(cohorts)
        target=cfg.network.route_choice_corridor['bypass_storage']
        cap=cfg.network.urban_link_storage_veh[target]
        state.urban_link_storage[target]=0.
        state._control_area_ledger.stocks['storage:'+target]={'inside':cap,'outside':0.}
        result=rc.advance(state,action,None,cfg,index)
        self.assertEqual(result['route_choice_accepted_veh'].get('branch:bypass',0.),0.)
        left=[c for c in state.route_choice_corridor_state['cohorts'] if c['storage']=='SC1004_E_choice' and c['route']=='1']
        self.assertEqual(sum(c['vehicles'] for c in left),8.)
        self.assertGreater(result['route_choice_accepted_veh']['branch:local'],0.)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_typed_local_arrival_never_resplits_ninety_ten(self):
        cohorts=[rc._cohort('SC1004_to_SC1005','local_tagged',key,1.,270,speed=40.) for key in ('2','3')]
        cfg,state,action,index=synthetic(cohorts)
        before=dict(state.urban_movement_queue)
        rc.advance(state,action,None,cfg,index)
        for key,movement in cfg.network.route_choice_corridor['local_movements'].items():
            self.assertEqual(state.urban_movement_queue[movement]-before[movement],1.)
        self.assertNotIn('SC1004_to_SC1005',state.urban_arrival_buffer)
        self.assertEqual(state._control_area_ledger.metrics.ttd_veh,0.)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_absent_flag_preserves_objects_and_config(self):
        from types import SimpleNamespace
        cfg=SimpleNamespace(network=SimpleNamespace()); detectors={}; raw={}
        before=pickle.dumps(cfg)
        result,meta=rc.configure(cfg,{},raw,detectors)
        self.assertIs(result,detectors); self.assertEqual(meta,{})
        self.assertEqual(before,pickle.dumps(cfg))
        self.assertEqual(rc.prepare_projection(cfg,detectors,raw),(detectors,raw,{}))

    def test_candidate_copy_and_fresh_worker_are_isolated(self):
        cohort=rc._cohort('SC1004_E_choice','prechoice',None,10.,270,speed=40.)
        cfg,state,action,index=synthetic([cohort]); frozen=pickle.dumps(state)
        copy_state=state.copy()
        payload=pickle.dumps((cfg,copy_state,action,index))
        expected=worker(payload)
        import multiprocessing
        with multiprocessing.get_context('spawn').Pool(1) as pool:
            observed=pool.apply(worker,(payload,))
        self.assertEqual(pickle.loads(expected),pickle.loads(observed))
        self.assertEqual(frozen,pickle.dumps(state))


if __name__=='__main__': unittest.main()
