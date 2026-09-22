"""Shared continuous prediction identity, explicit approximation, and accounting."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from src.models.state import ControlAction
from evaluation.controllers.sdmpc_tangent_surrogate import Query, MODEL, token, plain
from evaluation.controllers.sdmpc_tangent import checked_matrices


def action():
    return ControlAction(N_P_star=30., N_UF_star=100., green_times={'SC1_p1':20.})


def receipt(request):
    a=request['action']; ad=request['surrogate_evaluation']=='ad'
    item=dict(action_token=token(a), frozen_context_token=request['surrogate_context_sha256'],
        prediction_model=MODEL, execution_model_evaluated=False, price_or_quantity_terms_included=False,
        objective_veh_h=a.green_times['SC1_p1'])
    item['response_token']=token(item)
    return dict(surrogate_prediction=item, primal_audit_performed=False,
        surrogate_evaluation=request['surrogate_evaluation'], complete_primal_state_match=False,
        max_primal_state_error=None, scalar_rollouts=int(not ad), tangent_rollouts=int(ad),
        ad_axes=[0] if ad else [], fallback_reasons={}, wall_sec_including_spawn=0.,
        costs=[20.], resources=[10.,100.], cost_jacobian=[[1.]],resource_jacobian=[[2.],[3.]])


def query(runner=receipt):
    return Query(dict(owned=(),runtime={},bootstrap={},horizon=3,axes=[{}]),
                 lambda *a:None,lambda *a,**k:None,runner=runner)


class SurrogateReuseTests(unittest.TestCase):
    def test_ad_candidate_and_next_derivative_share_one_trajectory(self):
        q=query();a=action();q.evaluate([a],derivatives=True);q.derivative(a)
        self.assertEqual(q.stats()['total_rollouts'],1)
        self.assertEqual(q.stats()['scalar_rollouts'],0)
        self.assertEqual(q.stats()['unused_ad_predictions'],0)

    def test_np_can_reuse_but_nuf_and_actuators_cannot(self):
        q=query();a=action();q.evaluate([a],derivatives=True)
        b=copy.deepcopy(a);b.N_P_star=25.;row=q.evaluate([b])[0]
        self.assertIn('sdmpc_physical_response_reuse',row)
        q.derivative(b);self.assertEqual(q.stats()['total_rollouts'],1)
        b.N_UF_star+=1.;q.evaluate([b]);self.assertEqual(q.stats()['total_rollouts'],2)
        b.green_times['SC1_p1']+=1.;q.evaluate([b]);self.assertEqual(q.stats()['total_rollouts'],3)

    def test_returned_response_cannot_mutate_cached_values(self):
        q=query();a=action();r=q.evaluate([a])[0];r['objective_veh_h']=-999.
        self.assertEqual(q.evaluate([a])[0]['objective_veh_h'],20.)

    def test_scalar_cache_is_not_a_derivative(self):
        q=query();a=action();q.evaluate([a]);q.derivative(a)
        self.assertEqual((q.stats()['scalar_rollouts'],q.stats()['tangent_rollouts']),(1,1))

    def test_nonselected_prefetch_counted_and_bounded(self):
        seen=[]
        def run(r):seen.append(r['reverse_worker_limit']);return receipt(r)
        q=query(run);a=action();b=copy.deepcopy(a);b.green_times['SC1_p1']=21.
        q.evaluate([a,b],derivatives=True);q.derivative(a)
        self.assertEqual(seen,[4,4]);self.assertEqual(q.stats()['unused_ad_predictions'],1)

    def test_failure_does_not_publish_partial_batch(self):
        def fail(r):
            if r['action'].green_times['SC1_p1']>20.:raise RuntimeError('test')
            return receipt(r)
        q=query(fail);a=action();b=copy.deepcopy(a);b.green_times['SC1_p1']=21.
        with self.assertRaises(RuntimeError):q.evaluate([a,b],derivatives=True)
        self.assertEqual(q.entries,{})
        self.assertEqual(q.stats()['failed_predictions_with_unknown_rollout_count'],2)

    def test_forged_or_audited_receipt_rejected(self):
        for field,value in (('action_token','bad'),('prediction_model','exact'),('objective_veh_h',-1.)):
            def changed(r):
                out=receipt(r);out['surrogate_prediction'][field]=value;return out
            with self.assertRaises(ValueError):query(changed).evaluate([action()])
        def false_audit(r):
            out=receipt(r);out['primal_audit_performed']=True;return out
        with self.assertRaises(ValueError):query(false_audit).evaluate([action()])

    def test_unaudited_jacobian_requires_explicit_same_model_anchor(self):
        r=receipt(dict(action=action(),surrogate_evaluation='ad',surrogate_context_sha256='x'))
        with self.assertRaises(ValueError):checked_matrices(r,[20.],[10.,100.],[{}],1e-8)
        checked_matrices(r,[20.],[10.,100.],[{}],1e-8,allow_surrogate=True)
        with self.assertRaises(ValueError):checked_matrices(r,[21.],[10.,100.],[{}],1e-8,allow_surrogate=True)
        self.assertFalse(r['complete_primal_state_match']);self.assertIsNone(r['max_primal_state_error'])

    def test_closed_query_and_nonfinite_summary_rejected(self):
        q=query();q.close()
        with self.assertRaises(ValueError):q.evaluate([action()])
        with self.assertRaises(ValueError):plain({'cost':float('nan')})


if __name__=='__main__':unittest.main()
