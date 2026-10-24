"""Frozen-input matching, overlap ownership and failed-query cleanup."""
from pathlib import Path
import sys
import copy
import json
import pickle
from threading import Event
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_prefetch import InitialDerivative


def request():
    cfg=NS(network=NS(sdmpc_options={'derivative_workers':8}))
    return dict(owned=[NS(cfg=cfg)],action={'green':[20.,30.]},runtime={'bound':1},bootstrap={'source':'abc'})


class InitialOverlapTests(unittest.TestCase):
    def test_frozen_request_and_reduced_worker_limit(self):
        original=request();started=Event();release=Event();seen=[]
        def compute(frozen):
            started.set();release.wait(3.);seen.append(frozen)
            return {'reverse_sweeps':{'workers':7},'costs':[1.]}
        with InitialDerivative(original,compute) as task:
            self.assertTrue(started.wait(3.))
            original['action']['green'][0]=21.
            release.set()
            with self.assertRaisesRegex(ValueError,'full request changed'):task.consume(original)
            original['action']['green'][0]=20.
            value=task.consume(original)
            self.assertEqual(value['costs'],[1.])
            self.assertEqual(seen[0]['action']['green'],[20.,30.])
            self.assertEqual(seen[0]['reverse_worker_limit'],7)
            self.assertNotIn('reverse_worker_limit',original)
            with self.assertRaises(ValueError):task.consume(original)
        self.assertTrue(task.future.done())

    def test_prediction_exception_propagates_and_joins(self):
        def fail(_):raise ValueError('actual derivative failure')
        with self.assertRaisesRegex(ValueError,'actual derivative failure'):
            with InitialDerivative(request(),fail) as task:task.consume(request())
        self.assertTrue(task.future.done())

    def test_hold_failure_is_preserved_and_owned_task_is_joined(self):
        def compute(_):return {}
        with self.assertRaisesRegex(ValueError,'hold failure'):
            with InitialDerivative(request(),compute) as task:raise ValueError('hold failure')
        self.assertTrue(task.future.done())

    def test_unused_or_wrong_resource_configuration_fails(self):
        with self.assertRaisesRegex(ValueError,'not consumed'):
            with InitialDerivative(request(),lambda _:{}):pass
        for workers in (1,2,9,True):
            r=request();r['owned'][0].cfg.network.sdmpc_options['derivative_workers']=workers
            with self.assertRaises(ValueError):InitialDerivative(r,lambda _:None)

    def test_configuration_is_explicit_and_requires_reverse_concurrency(self):
        from evaluation.controllers import sdmpc
        model=pickle.loads((ROOT/'diagnostics/sdmpc_audit_20260922/compact_h3_v4/request.pickle').read_bytes())['owned'][0].cfg
        tuning=json.loads((ROOT/'diagnostics/sdmpc_audit_20260922/config_candidate.json').read_text())
        self.assertNotIn('initial_derivative_overlap',sdmpc.configure(tuning,copy.deepcopy(model)))
        tuning['adapter']['sdmpc_initial_derivative_overlap']=True
        self.assertTrue(sdmpc.configure(tuning,copy.deepcopy(model))['initial_derivative_overlap'])
        for change in ({'sdmpc_initial_derivative_overlap':1},{'sdmpc_derivative_workers':2},
                       {'sdmpc_tangent_concurrent_primal':False}):
            other=copy.deepcopy(tuning);other['adapter'].update(change)
            with self.assertRaises(ValueError):sdmpc.configure(other,copy.deepcopy(model))


if __name__=='__main__':unittest.main()
