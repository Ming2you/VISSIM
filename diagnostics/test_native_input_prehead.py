"""Real contracts plus accepted-transfer fixtures for the1093 head subset."""
from copy import deepcopy
import json
import hashlib
from pathlib import Path
import pickle
import unittest
import tempfile
import xml.etree.ElementTree as ET
from types import SimpleNamespace

from diagnostics.probe_model_area_integration import ROOT,adapter,build_projected
from diagnostics.route_input_fixtures import fixture_path
from evaluation.controllers import native_input_prehead as prehead,area_runtime
from evaluation.controllers.control_area_objective import emit_input,emit_transfer
from src.models.state import ControlAction


class NativePreheadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910/decisions_codex_area_observed_nc_s13_20260910'
        cls.built=build_projected(ROOT/'diagnostics/native_internal_extended_integration_config.json',
            fixture_path(folder/'state_000900.json'),fixture_path(folder/'action_000001.json'),fixture_inputs=False)
        cls.action=adapter.control_from_json(fixture_path(folder/'action_000001.json'),cls.built[0],ControlAction)

    def ready_left(self):
        """Generate ten real subset vehicles; advance their physical travel."""
        from src.models import urban_queue_model as uqm
        cfg,original,*_=self.built;state=original.copy();action=self.action.copy()
        spec=cfg.network.native_internal_inputs['inputs']['1093']['prehead_spec'];origin=spec['origin']
        prehead.advance(state,cfg,180)
        self.assertGreaterEqual(state.urban_link_storage[origin],10.)
        state.urban_link_storage[origin]-=10.
        emit_input(state,cfg,'storage:'+origin,10.,route_key='input:internal:1093')
        self.assertTrue(prehead.receive_generated(state,cfg,'1093',10.,180))
        prehead.finish_step(state,action,cfg,180)
        first=dict(cfg.network.urban_movements[spec['capacity_reference_movement']],phase=spec['first_phase'])
        for step in range(181,240):
            prehead.advance(state,cfg,step)
            blocked=[c for c in state.native_input_prehead_state['cohorts'] if c['stage']=='queue' and not c['passed_first']]
            fraction=uqm._phase_green_fraction(action,cfg,first,urban_step_index=step)
            if blocked and fraction>0:
                budget=fraction*cfg.simulation.T_u_h*spec['physical_head_lanes']*uqm._movement_capacity_flow(
                    action,cfg,spec['capacity_reference_movement'],cfg.network.urban_movements[spec['capacity_reference_movement']])
                return cfg,state,action,spec,step,budget
            prehead.finish_step(state,action,cfg,step)
        self.fail('The valid clock never reached p3 with an admitted left cohort')

    def accept_wn(self,cfg,state,spec,step,amount):
        movement=spec['wn_movements'][0];target=cfg.network.urban_movements[movement]['receiving_link']
        self.assertGreaterEqual(state.urban_movement_queue[movement],amount)
        self.assertGreaterEqual(state.urban_link_storage[target],amount)
        state.urban_movement_queue[movement]-=amount;state.urban_link_storage[target]-=amount
        emit_transfer(state,cfg,'movement:'+movement,'storage:'+target,amount,route_key='movement:'+movement)
        prehead.receive_accepted(state,cfg,movement,amount,step)

    def test_actual_source_contract_and_native_weights_initial_events_zero(self):
        cfg,state,*_=self.built;row=cfg.network.native_internal_inputs['inputs']['1093'];spec=row['prehead_spec']
        self.assertEqual(row['physical_projection_links'],['225','10359'])
        self.assertEqual([b['weight'] for b in spec['branches'].values()],[35.,242.,84.])
        self.assertEqual(spec['first_phase'],'SC11_p3')
        self.assertEqual(cfg.network.urban_movements[spec['left_movement']]['phase'],'SC11_p4')
        self.assertEqual(spec['physical_head_lanes'],2)
        self.assertAlmostEqual(spec['interhead_distance_m'],19.676165226566283)
        self.assertEqual((state._control_area_ledger.entered_veh,state._control_area_ledger.ttd_veh,state._control_area_ledger.event_count),(0,0,0))

    def test_wn_actual_has_priority_and_overdraw_cannot_create_service(self):
        cfg,state,action,spec,step,budget=self.ready_left();before=pickle.dumps(self.built[1])
        blocked=sum(c['vehicles'] for c in state.native_input_prehead_state['cohorts'] if c['stage']=='queue' and not c['passed_first'])
        self.accept_wn(cfg,state,spec,step,2*budget)
        result=prehead.finish_step(state,action,cfg,step)
        self.assertEqual(result['native_prehead_first_service_veh'],0.)
        self.assertAlmostEqual(result['native_prehead_existing_wn_budget_overdraw_veh'],budget)
        self.assertAlmostEqual(sum(c['vehicles'] for c in state.native_input_prehead_state['cohorts'] if c['stage']=='queue' and not c['passed_first']),blocked)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
        self.assertEqual(pickle.dumps(self.built[1]),before)

    def test_remaining_budget_is_partial_left_service_with_delay_and_no_stock_event(self):
        cfg,state,action,spec,step,budget=self.ready_left()
        self.accept_wn(cfg,state,spec,step,budget/2)
        inventory=area_runtime.model_inventory(state,cfg);events=state._control_area_ledger.event_count
        result=prehead.finish_step(state,action,cfg,step)
        self.assertAlmostEqual(result['native_prehead_first_service_veh'],budget/2)
        passed=[c for c in state.native_input_prehead_state['cohorts'] if c['stage']=='queue' and c['passed_first']
                and spec['branches'][c['route']]['movement']==spec['left_movement']]
        self.assertTrue(passed);self.assertTrue(all(c['ready']>=step+1 for c in passed))
        self.assertEqual(area_runtime.model_inventory(state,cfg),inventory)
        self.assertEqual(state._control_area_ledger.event_count,events)
        available=state.urban_movement_queue[spec['left_movement']]
        blocked=prehead._blocked(state.native_input_prehead_state,{'1093':cfg.network.native_internal_inputs['inputs']['1093']},spec['left_movement'],step)
        self.assertAlmostEqual(prehead.limit_intended(state,cfg,spec['left_movement'],available,available,step),available-blocked)
        with self.assertRaisesRegex(ValueError,'one finish'):prehead.finish_step(state,action,cfg,step)
        state._control_area_ledger.assert_stocks(inventory)

    def test_absent_kind_is_exact_noop_and_unfinished_steps_fail(self):
        cfg,state,*_=self.built;cfg=deepcopy(cfg);state=state.copy()
        cfg.network.native_internal_inputs['inputs'].pop('1093');before=pickle.dumps(state)
        self.assertEqual(prehead.initialize(state,cfg,{}),{})
        self.assertEqual(prehead.advance(state,cfg,180),{})
        self.assertEqual(prehead.finish_step(state,self.action,cfg,180),{})
        self.assertFalse(prehead.receive_generated(state,cfg,'1093',1.,180))
        self.assertEqual(prehead.limit_intended(state,cfg,'anything',10.,3.,180),3.)
        prehead.receive_accepted(state,cfg,'anything',1.,180)
        self.assertEqual(pickle.dumps(state),before)
        cfg,state,*_=self.built;copy=state.copy();prehead.advance(copy,cfg,180)
        with self.assertRaisesRegex(ValueError,'completed candidate'):prehead.advance(copy,cfg,181)

    def test_native_weight_head_phase_and_path_tampering_fail_closed(self):
        cfg,_,_,_,raw,*_=self.built;cfg=deepcopy(cfg)
        row=deepcopy(cfg.network.native_internal_inputs['inputs']['1093'])
        del cfg.network.native_internal_inputs
        document=json.loads((ROOT/row['route_evidence']['path']).read_text())
        tree=ET.parse(ROOT/document['network']['path']).getroot()
        links={x.get('no'):x for x in tree.findall('./links/link')}
        from evaluation.controllers.control_area_objective import physical_membership_from_ledger
        physical=physical_membership_from_ledger(json.loads((ROOT/document['membership']['path']).read_text()))
        contract=json.loads((ROOT/'diagnostics/control_area_route_contract_physical_routes.json').read_text())
        for kind in ('weight','phase','lane','path'):
            changed=deepcopy(document)
            if kind=='weight':changed['branches']['1']['rel_flow']='2 0:36'
            elif kind=='phase':changed['first_phase']='SC11_p4'
            elif kind=='lane':changed['first_head_lanes']=3
            else:changed['branches']['2']['native_path'][1]='10359'
            with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics') as directory:
                path=Path(directory)/'evidence.json';path.write_text(json.dumps(changed))
                altered=dict(row,route_evidence={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
                with self.subTest(kind=kind),self.assertRaises(ValueError):
                    prehead.configure_input(cfg,altered,tree,links,physical,contract,raw)

    def test_early_p4_acceptance_of_blocked_tag_is_rejected(self):
        cfg,state,action,spec,step,budget=self.ready_left()
        movement=spec['left_movement'];queue=state.urban_movement_queue[movement]
        inputs={'1093':cfg.network.native_internal_inputs['inputs']['1093']}
        blocked=prehead._blocked(state.native_input_prehead_state,inputs,movement,step)
        attempted=queue-blocked+blocked/2
        state.urban_movement_queue[movement]-=attempted
        with self.assertRaisesRegex(ValueError,'discharged early'):
            prehead.receive_accepted(state,cfg,movement,attempted,step)

    def test_initial_reservation_roundoff_never_creates_negative_buffer(self):
        cfg=self.built[0];origin=cfg.network.native_internal_inputs['inputs']['1093']['target_storage']
        occupied=1.-5e-9
        state=SimpleNamespace(time_sec=900.,urban_link_storage={origin:cfg.network.urban_link_storage_veh[origin]-occupied},
            urban_link_speed_kph={origin:20.},urban_arrival_buffer={origin:{181:occupied}},
            urban_storage_release_buffer={origin:{181:occupied}},urban_movement_queue={})
        row={'veh_no':999999,'link_no':225,'lane_no':1,'position_m':1.,'speed_kph':20.,'stopped':False}
        raw={'sim_sec':900.,'vehicle_records':{'complete':True,'records':[row],'record_count':1,
            'collection_count_before':1,'collection_count_after':1,'capture_sim_sec_before':900.,
            'capture_sim_sec_after':900.,'full_network_link_counts':{'225':1}}}
        prehead.initialize(state,cfg,raw)
        self.assertTrue(all(n>=0 for n in state.urban_arrival_buffer[origin].values()))
        self.assertTrue(all(n>=0 for n in state.urban_storage_release_buffer[origin].values()))

    def test_duplicate_prehead_sources_are_rejected_before_configuration(self):
        from evaluation.controllers import native_internal_input as native
        document=json.loads((ROOT/'diagnostics/native_internal_inputs_extended_ver2.json').read_text())
        document['inputs']['1092']['kind']='native_choice_prehead'
        cfg=deepcopy(self.built[0]);del cfg.network.native_internal_inputs
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics') as directory:
            path=Path(directory)/'evidence.json';path.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError,'only one declared source subset'):
                native.configure(cfg,{'urban':{'native_internal_inputs':str(path)}},self.built[4],self.built[2])


if __name__=='__main__':unittest.main()
