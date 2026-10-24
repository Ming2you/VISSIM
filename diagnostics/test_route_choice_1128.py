"""Two physical route corridors using the actual paused1350 projection.

Synthetic cohorts/route labels below test dynamics, not observed destinations.
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import json, os, pickle, tempfile, unittest
from diagnostics.test_route_choice_corridor import ROOT, worker
from diagnostics.probe_model_area_integration import build_projected
from diagnostics.route_input_fixtures import decisions
from evaluation.controllers import route_choice_corridor as rc, area_runtime
from evaluation.controllers.control_area_objective import ModelAreaLedger, emit_transfer


@lru_cache(maxsize=1)
def base():
    os.environ['RW_MAINLINE_SG_ONLY']='1';os.environ['RW_OFFSET_WRITER']='experiment'
    run=decisions()
    tuning=json.loads((ROOT/'diagnostics/fixtures/area_baseline_before_route_choice_beta0.json').read_text(encoding='utf-8-sig'))
    tuning['urban']['route_choice_corridor']={'evidence_paths':[
        'diagnostics/route_choice_corridor_ver2.json','diagnostics/route_choice_corridor_1128_ver2.json'],
        'unknown_policy':'hold_diagnostic'}
    with tempfile.TemporaryDirectory(prefix='route1128_fixture_',dir=ROOT/'diagnostics') as directory:
        path=Path(directory)/'config.json';path.write_text(json.dumps(tuning),encoding='utf-8')
        result=build_projected(path,run/'state_001350.json',run/'action_001200.json',fixture_inputs=False)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.models.state import ControlAction
    action=adapter.control_from_json(run/'action_001200.json',result[0],ControlAction)
    return result,action


def fixture(cohorts=None):
    (cfg,state,detectors,tuning,raw,mapping,metadata),action=deepcopy(base())
    if cohorts is not None:
        index=round(state.time_sec/cfg.simulation.T_u_sec)
        state.route_choice_corridor_state={'cohorts':deepcopy(cohorts),'last_step':index-1,
            'service_used_veh':{},'service_limit_veh':{},'received_veh':0.,'departed_veh':0.}
        stocks=deepcopy(state._control_area_ledger.stocks)
        for storage,cap in cfg.network.route_choice_corridor['capacity_veh'].items():
            count=rc._tracked(state.route_choice_corridor_state,storage)
            state.urban_link_storage[storage]=cap-count
            stocks['storage:'+storage]={'inside':count,'outside':0.}
        state._control_area_ledger=ModelAreaLedger(stocks)
    return cfg,state,action,raw


class TwoCorridorTests(unittest.TestCase):
    def test_actual1350_initial_stock_no_entry_and_distinct_partition(self):
        cfg,state,action,raw=fixture()
        specs=rc._specs(cfg)
        self.assertEqual([x['decision'] for x in specs],['1129','1128'])
        self.assertFalse(set(rc._projection_table(specs[0]))&set(rc._projection_table(specs[1])))
        for spec in specs:
            for field,store in [('prefix_links','prefix_storage'),('local_links','local_storage')]:
                actual=sum(v for k,v in raw['vehicle_records']['full_network_link_counts'].items() if k in spec[field])
                self.assertEqual(rc._tracked(state.route_choice_corridor_state,spec[store]),actual)
        self.assertEqual(state._control_area_ledger.event_count,0)
        self.assertEqual(state._control_area_ledger.metrics.entered_veh,0.)
        self.assertEqual(state._control_area_ledger.metrics.ttd_veh,0.)
        self.assertEqual(sum(s['inside'] for s in state._control_area_ledger.stocks.values()),2669.)
        self.assertEqual(cfg.network.shared_approach['branches']['2']['target'],'SC1004_E_choice')
        self.assertEqual(cfg.network.control_area_routes['movement:SC107_S_to_W_SC1005']['inward_crossings_per_vehicle'],1)
        self.assertEqual(cfg.network.control_area_routes['movement:SC107_S_to_W_SC1005']['outward_crossings_per_vehicle'],0)
        self.assertEqual(cfg.network.control_area_routes['movement:SC107_N_SC1_to_W_SC1005']['inward_crossings_per_vehicle'],0)

    def test_distinct_native_choices_do_not_redraw_each_other(self):
        cohorts=[rc._cohort('SC1004_E_choice','prechoice',None,10.,270,speed=40.),
                 rc._cohort('SC107_W_choice','prechoice',None,10.,270,speed=40.)]
        cfg,state,action,_=fixture(cohorts)
        rc.advance(state,action,None,cfg,270)
        by={store:{c['route']:c['vehicles'] for c in state.route_choice_corridor_state['cohorts'] if c['storage']==store}
            for store in ('SC1004_E_choice','SC107_W_choice')}
        self.assertEqual(by['SC1004_E_choice'],{'1':8.,'2':1.,'3':1.})
        self.assertEqual(by['SC107_W_choice'],{'1':5.,'2':5.})
        self.assertEqual(state._control_area_ledger.event_count,0)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_free62_exit_is_finite_accepted_once_without_signal_or_ttd(self):
        cohort=rc._cohort('SC107_to_SC1005','local_tagged','1',2.,270,speed=40.)
        cfg,state,action,_=fixture([cohort])
        target='SC1005_to_SC105';cap=cfg.network.urban_link_storage_veh[target]
        for name,spec in cfg.network.urban_movements.items():
            if spec.get('origin')==target:
                state.urban_movement_queue[name]=0.
                state._control_area_ledger.stocks['movement:'+name]={'inside':0.,'outside':0.}
        state.urban_link_storage[target]=0.
        state._control_area_ledger.stocks['storage:'+target]={'inside':cap,'outside':0.}
        arrival_before=sum(state.urban_arrival_buffer.get(target,{}).values())
        release_before=sum(state.urban_storage_release_buffer.get(target,{}).values())
        before_queue=deepcopy(state.urban_movement_queue)
        action.green_times={key:0. for key in action.green_times}
        rc.advance(state,action,None,cfg,270)
        self.assertEqual(rc._tracked(state.route_choice_corridor_state,'SC107_to_SC1005'),2.)
        self.assertEqual(state._control_area_ledger.event_count,0)
        # Release physical receiving space, with its ledger inventory adjusted in
        # this isolated boundary-condition fixture, then use the real acceptance.
        state.urban_link_storage[target]=1.
        state._control_area_ledger.stocks['storage:'+target]['inside']-=1.
        before=state._control_area_ledger.event_count
        result=rc.advance(state,action,None,cfg,271)
        accepted=result['route_choice_accepted_veh']['exit:10603']
        self.assertGreater(accepted,0.);self.assertLessEqual(accepted,1.)
        self.assertEqual(state.urban_movement_queue,before_queue)
        self.assertEqual(state._control_area_ledger.event_count,before+1)
        self.assertEqual(state._control_area_ledger.metrics.ttd_veh,0.)
        self.assertAlmostEqual(sum(state.urban_arrival_buffer[target].values())-arrival_before,accepted)
        self.assertAlmostEqual(sum(state.urban_storage_release_buffer[target].values())-release_before,accepted)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_south_outside_to_inside_is_one_accepted_entry(self):
        cfg,state,action,_=fixture([])
        from src.models import urban_queue_model as uqm
        name='SC107_S_to_W_SC1005';target='SC107_W_choice'
        index=next(i for i in range(270,330) if uqm._phase_green_fraction(action,cfg,cfg.network.urban_movements[name],urban_step_index=i)>0)
        state.route_choice_corridor_state['last_step']=index-1
        rc.advance(state,action,None,cfg,index)
        amount=min(.25,rc.intended_departure(state,action,cfg,name,1.,index))
        self.assertGreater(amount,0.)
        state.urban_movement_queue[name]=1.
        state._control_area_ledger.stocks['movement:'+name]={'inside':0.,'outside':1.}
        state.urban_movement_queue[name]-=amount;state.urban_link_storage[target]-=amount
        emit_transfer(state,cfg,'movement:'+name,'storage:'+target,amount,route_key='movement:'+name)
        events=state._control_area_ledger.event_count
        self.assertTrue(rc.receive_accepted(state,cfg,name,amount,index))
        self.assertEqual(state._control_area_ledger.event_count,events)
        self.assertAlmostEqual(state._control_area_ledger.metrics.entered_veh,amount)
        self.assertEqual(state._control_area_ledger.metrics.ttd_veh,0.)
        with self.assertRaisesRegex(ValueError,'exactly once'):rc.receive_accepted(state,cfg,name,amount,index)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_two_corridor_copy_and_fresh_worker_are_private(self):
        cohorts=[rc._cohort('SC1004_E_choice','prechoice',None,10.,270,speed=40.),
                 rc._cohort('SC107_W_choice','prechoice',None,10.,270,speed=40.)]
        cfg,state,action,_=fixture(cohorts)
        frozen=pickle.dumps(state);payload=pickle.dumps((cfg,state.copy(),action,270))
        expected=worker(payload)
        import multiprocessing
        with multiprocessing.get_context('spawn').Pool(1) as pool:actual=pool.apply(worker,(payload,))
        self.assertEqual(pickle.loads(expected),pickle.loads(actual));self.assertEqual(frozen,pickle.dumps(state))


if __name__=='__main__':unittest.main()
