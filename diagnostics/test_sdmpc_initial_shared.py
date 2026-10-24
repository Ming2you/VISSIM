"""Initial AD sharing must preserve the actual-merge target and cache identity."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.test_sdmpc_surrogate_reuse import action, receipt
from evaluation.controllers.sdmpc_tangent_surrogate import Query, token, validate_prediction
from evaluation.controllers.area_follower_objective import initialize_decision_nuf


def fixture(enabled=True):
    ramps={str(i):dict(to_model_link='FW_E' if i<4 else 'FW_W') for i in range(8)}
    cfg=NS(network=NS(sdmpc_options=dict(initial_shared_prediction=enabled,surrogate_reuse=True),
        physical_ramp_branches=dict(ramps=ramps)),mpc=NS(horizon_steps=3),simulation=NS(T_c_sec=150))
    follower=NS(cfg=cfg);state=NS(time_sec=900.,lane_freeway_runtime=NS())
    def run(request):
        out=receipt(request);item=out['surrogate_prediction'];item.pop('response_token')
        item['quantities']=dict(predicted_ramp_merge=dict(schema='predicted-physical-ramp-merge/v1',
            boundary='ramp_to_mainline',start_sec=900.,end_sec=1350.,omega_ttd=False,
            leader_target_inherited=False,accepted_vehicles_by_ramp={k:1. for k in ramps},
            rate_veh_h_by_ramp={k:8. for k in ramps},rate_veh_h_by_owner=dict(FW_E=32.,FW_W=32.),
            total_rate_veh_h=64.))
        item['response_token']=token(item)
        return out
    q=Query(dict(owned=(follower,state,action(),None),runtime={},bootstrap={},horizon=3,axes=[{}]),
        lambda *a:None,lambda *a,**k:None,runner=run)
    return q,follower,state


class InitialSharedTests(unittest.TestCase):
    def test_declared_lane_manifest_uses_freeway_section(self):
        import json
        from evaluation.controllers.sdmpc import configure
        tuning=json.loads((ROOT/'diagnostics/sdmpc_initial_shared_20260922/config_candidate.json').read_text())
        cfg=NS(network=NS(physical_ramp_branches={'ramps':{}},control_area_enabled=True,
            control_area_beta_seconds=0,control_area_refresh_nuf_target_each_decision=True),
            mpc=NS(horizon_steps=3),simulation=NS(T_c_sec=150))
        self.assertTrue(configure(tuning,cfg)['initial_shared_prediction'])
        tuning['freeway'].pop('lane_plant')
        with self.assertRaises(ValueError):configure(tuning,cfg)

    def prepare(self,enabled=True,derivatives=True):
        q,f,s=fixture(enabled);a=action();old=q.evaluate([a],derivatives=derivatives)[0]
        b,init=initialize_decision_nuf(f,s,a,old)
        return q,a,b,old

    def test_one_ad_supplies_hold_and_initial_derivative(self):
        q,a,b,old=self.prepare();q.bind_initial_target(a,b)
        bound=q.evaluate([b],derivatives=True)[0];ad=q.derivative(b)
        self.assertEqual(b.N_UF_star,64.)
        self.assertEqual(bound['objective_veh_h'],old['objective_veh_h'])
        self.assertEqual(q.stats()['total_rollouts'],1)
        self.assertEqual(q.stats()['unused_ad_predictions'],0)
        self.assertEqual(q.stats()['initial_scalar_rollouts_removed'],1)
        self.assertEqual(ad['candidate_prediction_reused']['source_action_token'],token(a))
        self.assertNotEqual(bound['response_token'],old['response_token'])
        self.assertEqual(bound['initial_target_binding']['initialization']['reference_response_token'],old['response_token'])
        self.assertEqual(q.evaluate([a])[0],old)

    def test_np_reuse_still_works_and_other_nuf_still_predicts(self):
        q,a,b,_=self.prepare();q.bind_initial_target(a,b)
        c=copy.deepcopy(b);c.N_P_star=25.
        self.assertIn('sdmpc_physical_response_reuse',q.evaluate([c])[0]);q.derivative(c)
        self.assertEqual(q.stats()['total_rollouts'],1)
        c.N_UF_star+=1.;q.evaluate([c]);self.assertEqual(q.stats()['total_rollouts'],2)

    def test_arbitrary_target_and_changed_actuator_rejected(self):
        for field in ('NUF','green','NP','future'):
            q,a,b,_=self.prepare()
            if field=='NUF':b.N_UF_star+=1.
            if field=='green':b.green_times['SC1_p1']+=1.
            if field=='NP':b.N_P_star+=1.
            if field=='future':b.diagnostics['sdmpc_prediction_sequence']={}
            with self.assertRaises(ValueError):q.bind_initial_target(a,b)
            self.assertIsNone(q.initial_binding)

    def test_disabled_and_scalar_only_and_repeated_binding_rejected(self):
        for enabled,derivatives in ((False,True),(True,False)):
            q,a,b,_=self.prepare(enabled,derivatives)
            with self.assertRaises(ValueError):q.bind_initial_target(a,b)
        q,a,b,_=self.prepare();q.bind_initial_target(a,b)
        with self.assertRaises(ValueError):q.bind_initial_target(a,b)

    def test_nonreference_or_later_prediction_rejected(self):
        q,a,b,_=self.prepare();a.N_P_star+=1.
        with self.assertRaises(ValueError):q.bind_initial_target(a,b)
        q,a,b,_=self.prepare();c=copy.deepcopy(a);c.N_UF_star+=1.;q.evaluate([c])
        with self.assertRaises(ValueError):q.bind_initial_target(a,b)

    def test_bound_digest_and_source_proof_are_both_checked(self):
        q,a,b,_=self.prepare();q.bind_initial_target(a,b)
        bound=q.evaluate([b])[0];bound['objective_veh_h']=-1.
        with self.assertRaises(ValueError):validate_prediction(bound,b,q.context_token)
        bound.pop('response_token');bound['response_token']=token(bound)
        with self.assertRaises(ValueError):validate_prediction(bound,b,q.context_token)
        self.assertEqual(q.evaluate([b])[0]['objective_veh_h'],20.)


if __name__=='__main__':unittest.main()
