"""Speculative work must keep input identity, worker bounds and cleanup."""
from pathlib import Path
import copy
import json
import pickle
import sys
from threading import Event
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.test_sdmpc_initial_overlap import request
from evaluation.controllers.sdmpc_tangent_prefetch import TrialDerivatives


def requests(count=2):
    result=[]
    for index in range(count):
        item=request()
        item['owned'][0].cfg.network.sdmpc_options['trial_derivative_overlap']=True
        item['action']['green'][0]+=index
        result.append(item)
    return result


def qualified(item):
    return dict(reverse_sweeps={'workers':item['reverse_worker_limit']},
        complete_primal_state_match=True, fallback_reasons={}, wall_sec_including_spawn=1.)


class TrialOverlapTests(unittest.TestCase):
    def test_both_start_before_selection_and_second_can_win(self):
        jobs=requests();started=[Event(),Event()];release=Event()
        def compute(item):
            index=int(item['action']['green'][0]-20)
            started[index].set();release.wait(3.)
            return qualified(item)
        with TrialDerivatives(jobs,compute) as batch:
            try:
                self.assertTrue(all(event.wait(3.) for event in started))
            finally:
                release.set()
            result=batch.consume(jobs[1])
            self.assertTrue(result['trial_prediction_overlap']['full_request_exact'])
            self.assertEqual(result['trial_prediction_overlap']['reverse_workers'],3)
        self.assertTrue(batch.closed)
        self.assertTrue(batch.receipt['all_joined'])
        self.assertTrue(batch.receipt['unused_qualified'])
        self.assertEqual(batch.receipt['max_numerical_workers'],8)
        self.assertEqual(batch.receipt['unused_derivatives'],1)
        self.assertEqual([row['consumed'] for row in batch.receipt['tasks']],[False,True])

    def test_full_request_mismatch_and_duplicate_use_rejected(self):
        jobs=requests(1)
        with TrialDerivatives(jobs,qualified) as batch:
            changed=copy.deepcopy(jobs[0]);changed['runtime']['bound']=2
            self.assertTrue(batch.contains_action(changed['action']))
            with self.assertRaisesRegex(ValueError,'full request changed'):batch.consume(changed)
            batch.consume(jobs[0])
            with self.assertRaisesRegex(ValueError,'already consumed'):batch.consume(jobs[0])
        self.assertEqual(batch.receipt['reverse_workers_per_derivative'],7)
        self.assertEqual(batch.receipt['max_numerical_workers'],8)

    def test_new_restoration_action_does_not_match_and_unused_work_joins(self):
        jobs=requests()
        with TrialDerivatives(jobs,qualified) as batch:
            restored=copy.deepcopy(jobs[0]['action']);restored['green'][0]=99.
            self.assertFalse(batch.contains_action(restored))
            batch.close()
            self.assertTrue(all(future.done() for future in batch.futures))
        self.assertEqual(batch.receipt['unused_derivatives'],2)
        self.assertTrue(batch.receipt['unused_qualified'])

    def test_failure_of_discarded_prediction_is_not_hidden(self):
        jobs=requests()
        def compute(item):
            if item['action']['green'][0]==21.:raise ValueError('discarded prediction failed')
            return qualified(item)
        with self.assertRaisesRegex(ValueError,'discarded prediction failed'):
            with TrialDerivatives(jobs,compute) as batch:
                batch.consume(jobs[0])
                batch.close()
        self.assertTrue(all(future.done() for future in batch.futures))
        self.assertFalse(batch.receipt['unused_qualified'])

    def test_primary_native_failure_preserved_and_children_joined(self):
        def fail(_):raise ValueError('secondary worker failure')
        with self.assertRaisesRegex(ValueError,'original native failure'):
            with TrialDerivatives(requests(),fail) as batch:
                raise ValueError('original native failure')
        self.assertTrue(batch.receipt['all_joined'])
        self.assertFalse(batch.receipt['unused_qualified'])

    def test_unqualified_unused_prediction_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unqualified'):
            with TrialDerivatives(requests(),lambda _:{}):pass

    def test_config_and_batch_enforce_explicit_mode_and_resource_limit(self):
        for count in (0,3):
            with self.assertRaises(ValueError):TrialDerivatives(requests(count),qualified)
        job=requests(1)[0]
        with self.assertRaises(ValueError):TrialDerivatives([job,job],qualified)
        job['owned'][0].cfg.network.sdmpc_options['derivative_workers']=7
        with self.assertRaises(ValueError):TrialDerivatives([job],qualified)
        from evaluation.controllers import sdmpc
        model=pickle.loads((ROOT/'diagnostics/sdmpc_flow_20260922/flow_h3_v2/request.pickle').read_bytes())['owned'][0].cfg
        tuning=json.loads((ROOT/'diagnostics/sdmpc_flow_20260922/config_candidate.json').read_text())
        self.assertNotIn('trial_derivative_overlap',sdmpc.configure(tuning,copy.deepcopy(model)))
        tuning['adapter']['sdmpc_trial_derivative_overlap']=True
        self.assertTrue(sdmpc.configure(tuning,copy.deepcopy(model))['trial_derivative_overlap'])
        for change in ({'sdmpc_trial_derivative_overlap':1},{'sdmpc_derivative_workers':7},
                       {'sdmpc_initial_derivative_overlap':False},{'sdmpc_response_np_cache':False}):
            other=copy.deepcopy(tuning);other['adapter'].update(change)
            with self.assertRaises(ValueError):sdmpc.configure(other,copy.deepcopy(model))


if __name__=='__main__':unittest.main()
