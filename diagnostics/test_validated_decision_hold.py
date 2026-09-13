"""Current-state hold must retain actual controls and every feasibility gate."""
import copy
import hashlib
import pickle
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evaluation.controllers import area_follower_objective as joint


def digest(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


class ValidatedDecisionHoldTests(unittest.TestCase):
    def setUp(self):
        self.action = SimpleNamespace(N_P_star=100., N_UF_star=7200.,
            ramp_metering={'DW':1800., 'FW':1800., 'DE':1800., 'FE':1800.},
            green_times={'SC1_p1':30.}, offsets={'SC1':0.}, vsl={'FW_W':120., 'FW_E':120.},
            inflow_outflow_allocation={}, diagnostics={'actual':'verified'})
        self.owners = tuple('SC'+str(i) for i in range(17))+('FW_W','FW_E')
        self.follower = SimpleNamespace(_wu=SimpleNamespace(_omega_f={'FW_W':.5,'FW_E':.5}),
            cfg=SimpleNamespace(mpc=SimpleNamespace(horizon_steps=3)))
        self.state = SimpleNamespace(time_sec=1050.)
        self.options = {'np_tolerance_veh':1e-7,'nuf_tolerance_veh_h':1e-7,'shared_tolerance':1e-7}
        self.item = {'action_token':digest(self.action),'response_token':'r'*64,
            'frozen_context_token':'c'*64,'objective_veh_h':10.,
            'local_base_costs':dict.fromkeys(self.owners,1.),'quantities':{},
            'conditional_model_feasibility_witness':True,
            'model_constraint_coverage':{'complete':True,'conditional_model_feasibility_witness':True},
            'resource_summary':{'max_exceedance_veh':0.}}
        self.constraints = {'feasible':True,'np':{'actual':90.,'target':100.},
            'nuf':{'actual':7200.,'target':7200.},
            'meter_rate_veh_h_by_owner':{'FW_W':3600.,'FW_E':3600.}}
        self.commands = {'ordered_rows':({'kind':'signal'},),
            'owner_physical_sha256':dict.fromkeys(self.owners,'p'*64)}
        self.callbacks = {'ownership':SimpleNamespace(owners=self.owners),
            'command_evidence':lambda a,c:copy.deepcopy(self.commands)}

    def run_hold(self):
        with patch('evaluation.controllers.area_leader_objective.shared_quantity_constraints',
                   return_value=copy.deepcopy(self.constraints)) as check:
            result = joint.validate_actual_decision_hold(self.follower,self.state,self.action,self.item,
                callbacks=self.callbacks,context={},source_fingerprint='s'*64,options=self.options)
        self.assertEqual(check.call_args.kwargs['target_np_veh'],100.)
        self.assertEqual(check.call_args.kwargs['target_nuf_veh_h'],7200.)
        return result

    def test_current_complete_feasible_hold_has_no_game_certificate(self):
        before = digest((self.action,self.item,self.commands))
        result = self.run_hold()
        self.assertTrue(result['feasible'])
        self.assertEqual(result['schema'],'validated-decision-hold/v1')
        self.assertIsNone(result['maximum_finite_candidate_gap'])
        self.assertFalse(result['finite_neighborhood_certified'])
        self.assertNotIn('game',result)
        self.assertEqual(before,digest((self.action,self.item,self.commands)))
        result['control'].green_times['SC1_p1']=1.
        self.assertEqual(self.action.green_times['SC1_p1'],30.)

    def test_old_np_or_directional_violation_cannot_become_feasible(self):
        self.constraints['feasible']=False
        self.assertFalse(self.run_hold()['feasible'])
        self.constraints['feasible']=True
        self.constraints['meter_rate_veh_h_by_owner']={'FW_W':3700.,'FW_E':3500.}
        self.assertFalse(self.run_hold()['feasible'])

    def test_incomplete_coverage_or_resource_exceedance_is_not_feasible(self):
        self.item['model_constraint_coverage']['complete']=False
        self.assertFalse(self.run_hold()['feasible'])
        self.item['model_constraint_coverage']['complete']=True
        self.item['resource_summary']['max_exceedance_veh']=1.
        self.assertFalse(self.run_hold()['feasible'])

    def test_physical_eight_uses_total_merge_without_legacy_half_shares(self):
        self.follower.cfg.network=SimpleNamespace(physical_ramp_branches={'schema':'physical-eight-test'})
        self.constraints['meter_rate_veh_h_by_owner']={'FW_W':4700.,'FW_E':2500.}
        result=self.run_hold()
        self.assertTrue(result['feasible'])
        self.assertEqual(result['directional_constraints'],{})
        self.constraints['feasible']=False
        self.assertFalse(self.run_hold()['feasible'])

    def test_changed_action_and_missing_owner_are_errors(self):
        self.action.offsets['SC1']=1.
        with self.assertRaisesRegex(ValueError,'action'):
            self.run_hold()
        self.action.offsets['SC1']=0.
        self.item['local_base_costs'].pop(self.owners[0])
        with self.assertRaisesRegex(ValueError,'owner'):
            self.run_hold()

    def test_command_error_is_not_silently_hold_success(self):
        def fail(a,c): raise ValueError('invalid writer')
        self.callbacks['command_evidence']=fail
        with self.assertRaisesRegex(ValueError,'invalid writer'):
            self.run_hold()

    def setup_physical_initialization(self):
        self.follower.cfg.network=SimpleNamespace(
            physical_ramp_branches={'ramps':{str(i):{'to_model_link':'FW_W' if i<4 else 'FW_E'} for i in range(8)}},
            control_area_refresh_nuf_target_each_decision=True)
        self.follower.cfg.simulation=SimpleNamespace(T_c_sec=150.)
        rates={str(i):float(200+i) for i in range(8)}
        self.item['quantities']['predicted_ramp_merge']={
            'schema':'predicted-physical-ramp-merge/v1','boundary':'ramp_to_mainline',
            'start_sec':1050.,'end_sec':1500.,'omega_ttd':False,'leader_target_inherited':False,
            'rate_veh_h_by_ramp':rates,'accepted_vehicles_by_ramp':{k:v/8 for k,v in rates.items()},
            'rate_veh_h_by_owner':{'FW_W':806.,'FW_E':822.},'total_rate_veh_h':1628.}

    def test_new_step_target_changes_only_nuf_and_requires_fresh_response(self):
        self.setup_physical_initialization()
        before=digest((self.action,self.item))
        initial,proof=joint.initialize_decision_nuf(self.follower,self.state,self.action,self.item)
        self.assertEqual(initial.N_UF_star,1628.)
        expected=copy.deepcopy(self.action);expected.N_UF_star=1628.
        self.assertEqual(vars(initial),vars(expected))
        self.assertEqual(before,digest((self.action,self.item)))
        self.assertEqual(proof['previous_target_veh_h'],7200.)
        self.assertEqual(proof['reference_action_token'],digest(self.action))
        # The old response token cannot simply be reassigned to the new action.
        with self.assertRaisesRegex(ValueError,'another actual action'):
            joint.validate_actual_decision_hold(self.follower,self.state,initial,self.item,
                callbacks=self.callbacks,context={},source_fingerprint='s'*64,options=self.options)
        proof['physical_commands_unchanged']=True
        hold={'control':initial,'nuf_initialization':proof}
        joint.validate_hold_anchor(hold,self.action,self.follower.cfg,self.state)
        for field in ('N_P_star','green_times','offsets','vsl','ramp_metering','inflow_outflow_allocation'):
            bad=copy.deepcopy(hold);value=getattr(bad['control'],field)
            if isinstance(value,dict):value['tampered']=1.
            else:setattr(bad['control'],field,value+1.)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,'actual previous action'):
                joint.validate_hold_anchor(bad,self.action,self.follower.cfg,self.state)
        with self.assertRaisesRegex(ValueError,'current-decision'):
            joint.validate_hold_anchor(hold,self.action,self.follower.cfg,SimpleNamespace(time_sec=1200.))
        self.follower.cfg.network.control_area_refresh_nuf_target_each_decision=False
        with self.assertRaisesRegex(ValueError,'actual previous action'):
            joint.validate_hold_anchor(hold,self.action,self.follower.cfg,self.state)

    def test_initialization_rejects_stale_window_missing_branch_or_wrong_action(self):
        self.setup_physical_initialization()
        self.item['quantities']['predicted_ramp_merge']['end_sec']=1499.
        with self.assertRaisesRegex(ValueError,'window mismatch'):
            joint.initialize_decision_nuf(self.follower,self.state,self.action,self.item)
        self.item['quantities']['predicted_ramp_merge']['end_sec']=1500.
        self.item['quantities']['predicted_ramp_merge']['rate_veh_h_by_ramp'].pop('7')
        with self.assertRaisesRegex(ValueError,'eight branches'):
            joint.initialize_decision_nuf(self.follower,self.state,self.action,self.item)
        self.item['action_token']='wrong'
        with self.assertRaisesRegex(ValueError,'exact actual-reference'):
            joint.initialize_decision_nuf(self.follower,self.state,self.action,self.item)


if __name__=='__main__': unittest.main()
