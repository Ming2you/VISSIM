"""Physical eight-ramp source, command and accepted-merge regression checks."""
import copy
import json
from pathlib import Path
import pickle
import sys
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'vendor/NumSim-mine'))
from evaluation.controllers import physical_ramp_branches as ramps
from diagnostics.probe_model_area_integration import build_projected
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from src.models.state import ControlAction


class PhysicalRampTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'
        cls.record=ROOT/'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2'
        cls.cfg,cls.state,cls.det,cls.tuning,cls.raw,cls.mapping,cls.metadata=build_projected(
            cls.folder/'config.json',cls.record/'state_000900.json',cls.record/'action_000750.json',fixture_inputs=False)
        cls.anchor=adapter.control_from_json(cls.record/'action_000900.json',cls.cfg,ControlAction)

    def greens(self, **values):
        return {**{mid:10. for mid in self.cfg.network.ramps},**values}

    def test_complete_sweep_prefetch_configuration_requires_explicit_boolean(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix='physical-prefetch-config-') as directory:
            path=Path(directory)/'tuning.json'
            for enabled in (False,True,'true',1,None):
                tuning=copy.deepcopy(self.tuning)
                tuning['control_area_objective']['prefetch_complete_sweep_responses']=enabled
                path.write_text(json.dumps(tuning),encoding='utf-8')
                if type(enabled) is bool:
                    cfg,*_=build_projected(path,self.record/'state_000900.json',
                        self.record/'action_000750.json',fixture_inputs=False)
                    self.assertIs(getattr(cfg.network,'control_area_prefetch_complete_sweep_responses',False),enabled)
                else:
                    with self.assertRaisesRegex(ValueError,'prefetch_complete_sweep_responses must be boolean'):
                        build_projected(path,self.record/'state_000900.json',
                            self.record/'action_000750.json',fixture_inputs=False)

    def test_eight_region_observations_distinguish_mixed_approach_destinations(self):
        regions=self.metadata['physical_ramp_observed_regions']
        self.assertEqual(set(regions),set(self.cfg.network.ramps))
        self.assertEqual(len({link for row in regions.values() for link in row['physical_links']}),16)
        west=regions['RM_C10646']
        self.assertEqual((west['approach_veh'],west['current_route_without_ramp_veh']),(2,2))
        self.assertEqual(west['this_ramp_veh'],west['connector_veh'])
        source=regions['RM_C10482']
        self.assertEqual(source['approach_veh'],9)
        self.assertEqual(source['this_ramp_veh']-source['connector_veh'],6)
        self.assertEqual(source['other_ramp_veh'],{'RM_C10490':2})
        self.assertEqual(source['current_route_without_ramp_veh'],1)
        shared=regions['RM_C10644']
        self.assertEqual(shared['this_ramp_veh']-shared['connector_veh'],20)
        self.assertEqual(shared['other_ramp_veh'],{'RM_C10639':1})
        self.assertEqual(shared['unresolved_veh'],1)

    def test_held_actual_eight_commands_keep_target_and_reject_changed_proof(self):
        from evaluation.controllers import area_meter_finalization as meters
        before=pickle.dumps(self.anchor,protocol=5)
        held=meters.prepare_held_actual_reference(self.anchor,self.cfg)
        self.assertEqual(held.N_UF_star,self.anchor.N_UF_star)
        self.assertEqual(ramps.physical_commands(held,self.cfg),ramps.physical_commands(self.anchor,self.cfg))
        self.assertEqual(pickle.dumps(self.anchor,protocol=5),before)
        bad=self.anchor.copy();bad.diagnostics['physical_ramp_recorded_csv']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'CSV changed'):meters.prepare_held_actual_reference(bad,self.cfg)

    def test_no_control_explicitly_opens_all_eight_physical_meters(self):
        control=adapter._make_no_control(ControlAction,self.cfg)
        rows=ramps.physical_commands(control,self.cfg)
        self.assertEqual(set(rows),set(self.cfg.network.ramps))
        self.assertEqual({r['green_sec'] for r in rows.values()},{10.})
        self.assertEqual({r['rate_vph'] for r in rows.values()},{900.})

    def test_known_city_routes_use_physical_receivers_without_new_stock(self):
        cfg,state,*_=build_projected(self.folder/'config_routes_v3.json',self.record/'state_000900.json',self.record/'action_000750.json',fixture_inputs=False)
        local=state.known_legsplit_route_state
        # Two on121 plus one on its incoming connector10682, all1130:3.
        self.assertEqual(sum(c['vehicles'] for c in local['cohorts']),3.)
        self.assertEqual({c['target'] for c in local['cohorts']},{'free'})
        routes=cfg.network.known_legsplit_routes['routes']
        self.assertEqual(routes['1135:2']['target'],'RM_C10646')
        self.assertEqual(routes['1135:4']['target'],'RM_C10681')
        self.assertEqual(cfg.network.urban_link_storage_veh['SC1004_W_out']-state.urban_link_storage['SC1004_W_out'],3.)

    def test_eight_green_domain_reaches_each_meter_without_service_sum_budget(self):
        from evaluation.controllers import joint_owner_neighbors as neighbors
        from evaluation.controllers import joint_owner_game as game
        plan=json.loads(Path(self.tuning['urban']['plan']['actuation_plan_json']).read_text(encoding='utf-8-sig'))
        catalog=game.build_ownership(self.cfg,self.mapping,plan,segment_dsd_controls=adapter._segment_dsd_controls)
        anchor=self.anchor.copy()
        for owner in ('FW_E','FW_W'):
            for i in range(21):anchor.vsl[f'{owner}__seg{i}']=anchor.vsl[owner]
        frozen=pickle.dumps(anchor,protocol=5)
        def rows(control):
            commands=ramps.physical_commands(control,self.cfg)
            return {(kind,identity): (commands[key] if key in commands else
                {'vsl':control.vsl[key]} if kind=='dsd' else {'unchanged':identity})
                for kind,identity,owner,key in catalog.writes}
        for owner in ('FW_E','FW_W'):
            points,mode,budget,proof=neighbors._physical_meter_points(
                SimpleNamespace(cfg=self.cfg),owner,anchor,anchor)
            self.assertEqual((mode,budget),('none',None))
            self.assertEqual(len(points),9)  # incumbent + (9s,8s) for each of four SGs
            domain=neighbors.Domain({0:(),5:(),10:()},points,(),450.,mode,budget,1e-7,proof,'fixed_target')
            result=neighbors.generate(catalog,self.cfg,owner,anchor,domain,
                requested_admissible=lambda c:{'feasible':True},realize=lambda c:ramps.prepare_control(c,self.cfg),
                realized_admissible=lambda c:{'feasible':True},physical_rows=rows,meter_actual_reference=anchor)
            self.assertEqual(len(result['candidates']),9)
            deferred=neighbors.generate(catalog,self.cfg,owner,anchor,domain,
                requested_admissible=lambda c:{'feasible':True},realize=lambda c:ramps.prepare_control(c,self.cfg),
                realized_admissible=lambda c:{'feasible':True},physical_rows=rows,
                meter_actual_reference=anchor,defer_physical_commands=True)
            self.assertEqual([pickle.dumps(r['control']) for r in result['candidates']],
                             [pickle.dumps(r['control']) for r in deferred['candidates']])
            self.assertTrue(all(r['physical_rows'] is None and r['physical_sha256'] is None
                                for r in deferred['candidates'][1:]))
            changed=set()
            for row in result['candidates']:
                candidate=row['control']
                self.assertEqual(candidate.N_UF_star,anchor.N_UF_star)
                difference=game.assert_owner_transition(catalog,owner,anchor,candidate)
                self.assertLessEqual(len(difference),1)
                changed.update(key for field,key in difference)
                self.assertTrue(all(abs(candidate.diagnostics['rw_meter_green_'+mid]-10)<=2 for mid in self.cfg.network.ramps))
            self.assertEqual(changed,{r for r,d in self.cfg.network.ramp_to_freeway.items() if d==owner})
            with self.assertRaisesRegex(ValueError,'actual'):
                neighbors.generate(catalog,self.cfg,owner,anchor,domain,
                    requested_admissible=lambda c:{'feasible':True},realize=lambda c:c,
                    realized_admissible=lambda c:{'feasible':True},physical_rows=rows)
        self.assertEqual(pickle.dumps(anchor,protocol=5),frozen)

    def test_physical_domain_keeps_actual_anchor_after_an_update(self):
        from evaluation.controllers import joint_owner_neighbors as neighbors
        incumbent=ramps.candidate_from_greens(self.anchor,self.anchor,self.cfg,self.greens(RM_C10644=8.))
        points,_,_,_=neighbors._physical_meter_points(SimpleNamespace(cfg=self.cfg),'FW_W',incumbent,self.anchor)
        table=self.cfg.network.physical_ramp_branches['ramps']['RM_C10644']['service_by_green_veh_h']
        values={p['RM_C10644'] for _,p in points}
        self.assertEqual(values,{table[str(g)] for g in (8,9,10)})
        self.assertNotIn(table['6'],values)

    def test_full_fixed_move_box_uses_green_seconds_for_physical_meters(self):
        from evaluation.controllers import joint_owner_neighbors as neighbors,joint_owner_game as game
        plan=json.loads(Path(self.tuning['urban']['plan']['actuation_plan_json']).read_text(encoding='utf-8-sig'))
        catalog=game.build_ownership(self.cfg,self.mapping,plan,segment_dsd_controls=adapter._segment_dsd_controls)
        anchor=self.anchor.copy()
        for owner in ('FW_E','FW_W'):
            for i in range(21):anchor.vsl[f'{owner}__seg{i}']=anchor.vsl[owner]
        limits=dict(green_sec=6.,offset_sec=75.,vsl_kmh=20.,meter_green_sec=2.)
        box=neighbors.build_fixed_move_box(catalog,anchor,self.cfg,limits)
        candidate=ramps.candidate_from_greens(anchor,anchor,self.cfg,self.greens(RM_C10482=8.))
        self.assertGreater(abs(candidate.ramp_metering['RM_C10482']-anchor.ramp_metering['RM_C10482']),300.)
        box.validate(candidate)  # the old rate box must not silently remove g8
        candidate.diagnostics['rw_meter_green_RM_C10482']=7.
        with self.assertRaises(ValueError):box.validate(candidate)
        self.assertEqual(sum(field=='diagnostics' for field,*_ in box.entries),8)

    def test_final_transport_uses_merge_quantity_and_retains_frozen_target(self):
        from diagnostics.test_joint_leader_result import fixture,digest
        from evaluation.controllers import area_leader_objective as leader
        value=fixture();control=value['game']['control']
        control.ramp_metering=dict(self.anchor.ramp_metering)
        control.diagnostics=copy.deepcopy(self.anchor.diagnostics)
        control.N_UF_star=1200.
        q=ramps.predicted_merge_quantity({'freeway_frames':[{'start_sec':900.,'end_sec':1350.,
            'actual_ramp_release_veh_h':{r:(1200. if r=='RM_C10644' else 0.) for r in self.cfg.network.ramps}}]},
            self.cfg,start_sec=900.,end_sec=1350.)
        constraints=value['final_score']['quantity_constraints']
        constraints.update(nuf_definition='predicted_accepted_mainline_merge',physical_ramp_merge=copy.deepcopy(q),
            meter_rate_veh_h_by_owner=q['rate_veh_h_by_owner'],window={'start_sec':900.,'end_sec':1350.})
        constraints['nuf'].update(actual=1200.,target=1200.)
        value['final_score']['control_area']['predicted_ramp_merge']=copy.deepcopy(q)
        value['final_action_token']=value['final_score']['action_token']=digest(control)
        before=pickle.dumps(value,protocol=5)
        kwargs=dict(target_np_veh=340.,target_nuf_veh_h=1200.,cfg=self.cfg)
        result=leader.validate_joint_leader_result(value,**kwargs)
        self.assertEqual(result['control'].N_UF_star,1200.)
        self.assertNotEqual(sum(result['control'].ramp_metering.values()),1200.)
        self.assertEqual(before,pickle.dumps(value,protocol=5))
        for mutate in (
            lambda x:x['final_score']['control_area'].pop('predicted_ramp_merge'),
            lambda x:x['final_score']['quantity_constraints']['physical_ramp_merge']['rate_veh_h_by_ramp'].update(RM_C10644=1512.),
            lambda x:x['final_score']['quantity_constraints'].update(nuf_definition='service_sum'),
        ):
            wrong=copy.deepcopy(value);mutate(wrong)
            with self.assertRaises(ValueError):leader.validate_joint_leader_result(wrong,**kwargs)
        with self.assertRaises(ValueError):
            leader.validate_joint_leader_result(value,target_np_veh=340.,target_nuf_veh_h=1200.)
        # A permitted prediction residual must not overwrite the frozen target.
        target_nuf=1200.+5e-8
        control.N_UF_star=target_nuf
        constraints['nuf'].update(target=target_nuf,residual=1200.-target_nuf,violation=abs(1200.-target_nuf))
        value['final_action_token']=value['final_score']['action_token']=digest(control)
        result=leader.validate_joint_leader_result(value,target_np_veh=340.,target_nuf_veh_h=target_nuf,cfg=self.cfg)
        self.assertEqual(result['control'].N_UF_star,target_nuf)

    def physical_infeasible_restoration(self):
        from diagnostics.test_joint_leader_result import fixture, digest
        value=fixture();control=value['game']['control']
        control.ramp_metering=dict(self.anchor.ramp_metering)
        control.diagnostics=copy.deepcopy(self.anchor.diagnostics)
        control.N_UF_star=1120.
        q=ramps.predicted_merge_quantity({'freeway_frames':[{'start_sec':900.,'end_sec':1350.,
            'actual_ramp_release_veh_h':{r:(1200. if r=='RM_C10644' else 0.) for r in self.cfg.network.ramps}}]},
            self.cfg,start_sec=900.,end_sec=1350.)
        quantity=value['final_score']['quantity_constraints']
        quantity.update(feasible=False,nuf_definition='predicted_accepted_mainline_merge',
            physical_ramp_merge=copy.deepcopy(q),meter_rate_veh_h_by_owner=q['rate_veh_h_by_owner'],
            window={'start_sec':900.,'end_sec':1350.})
        quantity['nuf'].update(actual=1200.,target=1120.,residual=80.,violation=80.,
            tolerance=40.,satisfied=False)
        quantity['np'].update(actual=400.,residual=60.,violation=60.,satisfied=False)
        quantity['net_inflow_veh_by_owner']=dict.fromkeys(quantity['net_inflow_veh_by_owner'],0.)
        quantity['net_inflow_veh_by_owner']['SC1']=400.
        value['final_score']['control_area']['predicted_ramp_merge']=copy.deepcopy(q)
        value['final_action_token']=value['final_score']['action_token']=digest(control)
        value['game']['error']={'kind':'evaluation_budget','phase':'search'}
        value['initializer_restoration']={'status':'evaluation_budget','error':{'kind':'evaluation_budget'},
            'feasible':False,'control':None,'domain_infeasible':False,'best_infeasible':control.copy(),
            'final_violation':(60.-quantity['np']['tolerance'])/340.+40./1120.}
        return value

    def test_physical_infeasible_budget_uses_merges_and_keeps_feasibility_unknown(self):
        from evaluation.controllers import area_follower_objective as objective
        value=self.physical_infeasible_restoration()
        before=pickle.dumps(value,protocol=5)
        status,validated,evidence=objective._runtime_joint_candidate_validation(value,
            target_np=340.,target_nuf=1120.,initial=value['game']['control'],
            expected_owners=value['game']['owners'],cfg=self.cfg)
        self.assertEqual(status,'restoration_budget_stop')
        self.assertIsNone(validated)
        self.assertFalse(evidence['candidate_feasibility_known'])
        self.assertFalse(evidence['leader_domain_infeasible'])
        self.assertEqual(before,pickle.dumps(value,protocol=5))

    def test_physical_infeasible_budget_rejects_inconsistent_merge_evidence(self):
        from evaluation.controllers import area_follower_objective as objective
        for mutate in (
            lambda x:x['final_score']['control_area'].pop('predicted_ramp_merge'),
            lambda x:x['final_score']['quantity_constraints'].update(nuf_definition='service_sum'),
            lambda x:x['final_score']['quantity_constraints']['window'].update(end_sec=1349.),
            lambda x:x['final_score']['quantity_constraints']['meter_rate_veh_h_by_owner'].update(FW_W=1120.),
            lambda x:x['final_score']['quantity_constraints']['physical_ramp_merge']['rate_veh_h_by_ramp'].update(RM_C10644=1512.),
            lambda x:x['initializer_restoration'].update(final_violation=0.),
        ):
            value=self.physical_infeasible_restoration();mutate(value)
            with self.assertRaises(ValueError):
                objective._runtime_joint_candidate_validation(value,target_np=340.,target_nuf=1120.,
                    initial=value['game']['control'],expected_owners=value['game']['owners'],cfg=self.cfg)

    def test_exact_connector_counts_and_correct_independent_merge_cells(self):
        counts=self.raw['local_observation']['link_counts']
        expected={mid:float(counts.get(str(r['connector']),0)) for mid,r in self.cfg.network.physical_ramp_branches['ramps'].items()}
        self.assertEqual(self.state.ramp_queue,expected)
        self.assertEqual(sum(expected.values()),22.)
        self.assertEqual(self.cfg.network.ramp_merge_segment_index['RM_C10646'],11)
        self.assertEqual(self.cfg.network.ramp_merge_segment_index['RM_C10644'],13)
        assignment=self.state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        for mid,row in self.cfg.network.physical_ramp_branches['ramps'].items():
            positive={k:v for k,v in assignment.get(str(row['connector']),{}).items() if v}
            self.assertEqual(positive,{'ramp:'+mid:expected[mid]} if expected[mid] else {})

    def test_existing_approach_sources_are_retargeted_without_group_split(self):
        n=self.cfg.network
        self.assertEqual(n.urban_movements['SC1001_W_to_onW']['ramp'],'RM_C10482')
        self.assertEqual(n.urban_movements['SC1001_W_to_onE']['ramp'],'RM_C10490')
        self.assertEqual(n.shared_approach['branches']['1']['target'],'RM_C10644')
        self.assertEqual(n.shared_approach['branches']['3']['target'],'RM_C10639')
        self.assertEqual(n.boundary_out_ramp_split['SC1004_W_out']['ramps'],{'RM_C10681':.1667,'RM_C10646':.5})
        self.assertIn('RM_C10482',n.gate_onramp_queue_ramps)
        self.assertNotIn('R_D_W',n.gate_onramp_queue_ramps)

    def test_single_green_does_not_change_its_former_group_partner(self):
        before=pickle.dumps(self.anchor,protocol=5)
        candidate=ramps.candidate_from_greens(self.anchor,self.anchor,self.cfg,self.greens(RM_C10644=8.))
        commands=ramps.physical_commands(candidate,self.cfg)
        self.assertEqual(commands['RM_C10644']['green_sec'],8.)
        self.assertEqual(commands['RM_C10644']['rate_vph'],720.)
        self.assertEqual(candidate.ramp_metering['RM_C10644'],1166.4)
        self.assertEqual(commands['RM_C10646'],ramps.physical_commands(self.anchor,self.cfg)['RM_C10646'])
        self.assertEqual(candidate.N_UF_star,self.anchor.N_UF_star)
        self.assertEqual(pickle.dumps(self.anchor,protocol=5),before)
        self.assertEqual(ramps.physical_commands(candidate.copy(),self.cfg),commands)

    def test_box_never_recenters_and_unrealizable_green_fails(self):
        candidate=ramps.candidate_from_greens(self.anchor,self.anchor,self.cfg,self.greens(RM_C10644=8.))
        for value in (6.,8.5,float('nan'),True):
            with self.assertRaises(ValueError):
                ramps.candidate_from_greens(candidate,self.anchor,self.cfg,self.greens(RM_C10644=value))

    def test_mismatched_service_cannot_reallocate_other_meter(self):
        candidate=self.anchor.copy();candidate.ramp_metering['RM_C10644']=1.
        with self.assertRaisesRegex(ValueError,'differ'):
            ramps.physical_commands(candidate,self.cfg)

    def test_writer_preserves_eight_rates_and_rejects_late_override(self):
        candidate=ramps.candidate_from_greens(self.anchor,self.anchor,self.cfg,self.greens(RM_C10644=8.))
        settings=self.tuning['actuation']
        before=pickle.dumps(candidate,protocol=5)
        rows=adapter.real_world_ramp_meter_actions(candidate,self.cfg,settings,self.mapping)
        self.assertEqual(rows['RM_C10644']['green_sec'],8.)
        self.assertEqual(adapter.real_world_ramp_meter_write_back(candidate,self.cfg,settings,self.mapping),candidate.ramp_metering)
        self.assertEqual(pickle.dumps(candidate,protocol=5),before)
        wrong=copy.deepcopy(settings);wrong['real_world_ramp_metering']['diagnostic_green_sec']={}
        with self.assertRaisesRegex(ValueError,'override'):
            adapter.real_world_ramp_meter_actions(candidate,self.cfg,wrong,self.mapping)
        mapping=copy.deepcopy(self.mapping);mapping['ramp_meters'][0]['sc_no']+=1
        with self.assertRaisesRegex(ValueError,'mapping'):
            adapter.real_world_ramp_meter_actions(candidate,self.cfg,settings,mapping)

    def test_merge_quantity_counts_flow_over_time_not_service_sum(self):
        def frame(start,end,flow):
            return {'start_sec':start,'end_sec':end,'actual_ramp_release_veh_h':{mid:(flow if mid=='RM_C10644' else 0.) for mid in self.cfg.network.ramps}}
        response={'freeway_frames':[frame(900.,910.,1200.),frame(910.,920.,2400.)]}
        q=ramps.predicted_merge_quantity(response,self.cfg,start_sec=900.,end_sec=920.)
        self.assertEqual(q['total_rate_veh_h'],1800.)
        self.assertEqual(q['accepted_vehicles_by_ramp']['RM_C10644'],10.)
        self.assertEqual(q['rate_veh_h_by_owner'],{'FW_E':0.,'FW_W':1800.})
        self.assertFalse(q['omega_ttd'])
        for mutate in (
            lambda x:x['freeway_frames'].pop(),
            lambda x:x['freeway_frames'][1].update(start_sec=900.),
            lambda x:x['freeway_frames'][0]['actual_ramp_release_veh_h'].pop('RM_C10644'),
            lambda x:x['freeway_frames'][0]['actual_ramp_release_veh_h'].update(RM_C10644=-1.),
        ):
            broken=copy.deepcopy(response);mutate(broken)
            with self.assertRaises(ValueError):ramps.predicted_merge_quantity(broken,self.cfg,start_sec=900.,end_sec=920.)

    def test_absent_feature_does_not_read_csv_or_touch_action(self):
        cfg=copy.deepcopy(self.cfg);del cfg.network.physical_ramp_branches
        before=pickle.dumps(self.anchor,protocol=5)
        self.assertIs(ramps.read_recorded_control(self.anchor,cfg,'missing-action.json'),self.anchor)
        self.assertEqual(pickle.dumps(self.anchor,protocol=5),before)

    def test_shared_city_arrival_does_not_reselect_an_onramp(self):
        from evaluation.controllers import shared_approach
        from src.models import urban_queue_model as uqm
        cfg,state,*_=build_projected(self.folder/'config_routes_v2.json',self.record/'state_000900.json',self.record/'action_000750.json',fixture_inputs=False)
        spec=cfg.network.shared_approach
        cfg.network.shared_approach['schedule']=[]
        index=int(state.time_sec/cfg.simulation.T_u_sec)
        state.shared_approach_state['bins']={key:({index:12.} if key=='4' else {}) for key in spec['branches']}
        state.urban_link_storage[spec['storage']]=spec['capacity_veh']-12.
        result=shared_approach.advance(state,self.anchor,None,cfg,index)
        accepted=result['shared_accepted_by_branch']['4'];self.assertGreater(accepted,0.)
        source=spec['branches']['4']['target']
        due=index+uqm._link_delay_steps(state,cfg,source)
        routing=uqm.approach_routing(cfg)[source]
        # Mix an ordinary vehicle cohort with route-locked city arrivals. Only
        # the former may retain the pre-existing generic onE prior.
        arrived=accepted+12.
        distribution=ramps.split_tagged_arrival(state,cfg,source,due,arrived,routing)
        amounts=dict(distribution)
        self.assertAlmostEqual(sum(amounts.values()),arrived)
        self.assertAlmostEqual(amounts['SC1004_W_to_onE'],1.)
        for mid in ('SC1004_W_to_E_SC1005','SC1004_W_to_N_SC1003','SC1004_W_to_S'):
            self.assertGreater(amounts[mid],dict(routing)[mid]*12.)
        self.assertNotEqual(dict(routing)['SC1004_W_to_onE']*arrived,amounts['SC1004_W_to_onE'])
        self.assertIsNone(ramps.split_tagged_arrival(state,cfg,source,due,0.,routing))

    def test_tagged_arrival_missing_parent_count_fails_without_consuming_tag(self):
        cfg,state,*_=build_projected(self.folder/'config_routes_v2.json',self.record/'state_000900.json',self.record/'action_000750.json',fixture_inputs=False)
        ramps.tag_shared_city_arrival(state,cfg,'4',200,3.)
        before=pickle.dumps(state,protocol=5)
        with self.assertRaisesRegex(ValueError,'parent'):
            ramps.split_tagged_arrival(state,cfg,'in_SC1004_W',200,2.,[])
        self.assertEqual(pickle.dumps(state,protocol=5),before)


if __name__=='__main__':unittest.main()
