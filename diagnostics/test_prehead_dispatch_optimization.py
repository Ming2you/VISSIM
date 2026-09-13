"""Every old validation call and invalid-state exception is preserved."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pickle
import statistics
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from diagnostics.prepare_prehead_dispatch_optimization import ROOT,PINS,candidate_module,candidate_native_module
from evaluation.controllers import native_input_prehead as original

CANDIDATE=candidate_module()


def fixture():
    spec={'origin':'origin','branches':{'1':{'movement':'A'},'2':{'movement':'B'},'3':{'movement':'C'}},
          'wn_movements':['A','C']}
    inputs={str(i):{'kind':'irrelevant'} for i in range(9)}
    inputs['1093']={'kind':'native_choice_prehead','prehead_spec':spec}
    cfg=NS(network=NS(native_internal_inputs={'inputs':inputs},urban_link_storage_veh={'origin':100.}))
    cohorts=[{'input':'1093','route':'1','stage':'queue','passed_first':True,'ready':180,'vehicles':3.},
             {'input':'1093','route':'2','stage':'queue','passed_first':False,'ready':180,'vehicles':2.},
             {'input':'1093','route':None,'stage':'decision','due':182,'vehicles':1.}]
    state=NS(urban_link_storage={'origin':94.},urban_movement_queue={'A':10.,'B':4.,'C':0.,'other':3.},
             native_input_prehead_state={'last_step':180,'finished_step':179,'cohorts':cohorts,'initial_veh':6.,
               'generated_veh':0.,'departed_scope_veh':0.,'wn_actual':{},'first_head_service_veh':0.,
               'existing_wn_budget_overdraw_veh':0.})
    return cfg,state


def outcome(module,state,cfg,movement,vehicles,step):
    try:
        result=module.receive_accepted(state,cfg,movement,vehicles,step)
        return ('return',result,pickle.dumps(state))
    except Exception as exc:
        return ('raise',type(exc).__name__,str(exc),pickle.dumps(state))


class DispatchIndexTests(unittest.TestCase):
    def pair(self,state,cfg,movement='other',vehicles=1.,step=180):
        newcfg=deepcopy(cfg);CANDIDATE.prepare_dispatch_index(newcfg)
        oldstate,newstate=deepcopy(state),deepcopy(state)
        expected=outcome(original,oldstate,cfg,movement,vehicles,step)
        actual=outcome(CANDIDATE,newstate,newcfg,movement,vehicles,step)
        self.assertEqual(actual,expected)
        return expected,newstate

    def test_irrelevant_movement_still_runs_full_validation_at_same_call(self):
        cfg,state=fixture()
        cfg2=deepcopy(cfg);CANDIDATE.prepare_dispatch_index(cfg2)
        with patch.object(original,'_check',wraps=original._check) as oldcheck,patch.object(CANDIDATE,'_check',wraps=CANDIDATE._check) as newcheck:
            a=outcome(original,deepcopy(state),cfg,'other',1.,180)
            b=outcome(CANDIDATE,deepcopy(state),cfg2,'other',1.,180)
        self.assertEqual(a,b);self.assertEqual(oldcheck.call_count,1);self.assertEqual(newcheck.call_count,1)

    def test_unrelated_notify_retains_invalid_state_exceptions_and_timing(self):
        for kind in ('negative','nan','missing_input','missing_route','subset','storage','balance','wrong_step'):
            cfg,state=fixture();local=state.native_input_prehead_state;step=180
            if kind=='negative':local['cohorts'][0]['vehicles']=-1.
            elif kind=='nan':local['cohorts'][0]['vehicles']=float('nan')
            elif kind=='missing_input':local['cohorts'][0]['input']='missing'
            elif kind=='missing_route':local['cohorts'][0]['route']='missing'
            elif kind=='subset':state.urban_movement_queue['A']=0.
            elif kind=='storage':state.urban_link_storage['origin']=100.
            elif kind=='balance':local['initial_veh']=90.
            else:step=181
            with self.subTest(kind=kind):
                result,_=self.pair(state,cfg,step=step)
                self.assertEqual(result[0],'raise')

    def test_relevant_tagged_and_ordinary_proportional_departure_is_byte_exact(self):
        cfg,state=fixture();state.urban_movement_queue['A']-=2.
        _,result=self.pair(state,cfg,'A',2.)
        self.assertEqual(result.native_input_prehead_state['departed_scope_veh'],.6)
        self.assertEqual(result.native_input_prehead_state['wn_actual'],{'A':2.})

    def test_blocked_left_and_delayed_ready_predicates_are_identical(self):
        cfg,state=fixture();cfg2=deepcopy(cfg);CANDIDATE.prepare_dispatch_index(cfg2)
        for movement in ('A','B','C','other'):
            for step in (179,180,181):
                with self.subTest(movement=movement,step=step):
                    self.assertEqual(original.limit_intended(state,cfg,movement,4.,8.,step),CANDIDATE.limit_intended(state,cfg2,movement,4.,8.,step))
        state.urban_movement_queue['B']=0.
        result,_=self.pair(state,cfg,'B',4.)
        self.assertEqual(result[0:3],('raise','ValueError','Native blocked first-head cohort was discharged early'))

    def test_zero_acceptance_does_not_skip_pruning_or_check(self):
        cfg,state=fixture();state.native_input_prehead_state['cohorts'].append(dict(state.native_input_prehead_state['cohorts'][0],vehicles=0.))
        _,after=self.pair(state,cfg,vehicles=0.)
        self.assertEqual(len(after.native_input_prehead_state['cohorts']),3)

    def test_absent_index_and_absent_feature_preserve_fallback(self):
        cfg,state=fixture()
        self.assertEqual(original._inputs(cfg),CANDIDATE._inputs(cfg))
        cfg.network.native_internal_inputs['inputs'].pop('1093')
        CANDIDATE.prepare_dispatch_index(cfg)
        self.assertFalse(hasattr(cfg.network,'native_prehead_dispatch_index'))
        self.assertEqual(outcome(original,deepcopy(state),cfg,'other',1.,180),outcome(CANDIDATE,deepcopy(state),cfg,'other',1.,180))

    def test_candidate_copy_and_fresh_pickle_keep_config_aliases_and_no_cohort_cache(self):
        cfg,state=fixture();CANDIDATE.prepare_dispatch_index(cfg)
        for copied in (deepcopy(cfg),pickle.loads(pickle.dumps(cfg))):
            index=CANDIDATE._dispatch_index(copied)
            self.assertIs(index['source_inputs'],copied.network.native_internal_inputs['inputs'])
            self.assertIs(index['inputs']['1093'],copied.network.native_internal_inputs['inputs']['1093'])
            self.assertEqual(set(index),{'source_inputs','source_count','inputs','origins','movements','wn_movements'})
            self.assertEqual(outcome(original,deepcopy(state),copied,'other',1.,180),outcome(CANDIDATE,deepcopy(state),copied,'other',1.,180))

    def test_explicit_reconfigure_or_source_replacement_cannot_use_old_index(self):
        cfg,state=fixture();CANDIDATE.prepare_dispatch_index(cfg)
        cfg.network.native_internal_inputs={'inputs':{}}
        self.assertIsNone(CANDIDATE._dispatch_index(cfg));self.assertEqual(CANDIDATE._inputs(cfg),{})
        CANDIDATE.prepare_dispatch_index(cfg)
        self.assertFalse(hasattr(cfg.network,'native_prehead_dispatch_index'))

    def test_check_permutation_and_same_float_summation_order(self):
        cfg,state=fixture();state.native_input_prehead_state['cohorts'].reverse()
        self.pair(state,cfg)


def main():
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(DispatchIndexTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    # Reuse eight actual raw900/geometry/clock/receiving regressions against the
    # proposed module in memory. Other runtime modules remain actual production.
    import diagnostics.test_native_input_prehead as actual
    from evaluation.controllers import native_internal_input as native
    native_candidate=candidate_native_module()
    class ActualIndexed(actual.NativePreheadTests):
        @classmethod
        def setUpClass(cls):
            # Install only the two in-memory proposal functions at real runtime
            # construction. No fake flag/index or transformed input is supplied.
            with patch.object(native,'configure',native_candidate.configure),patch.object(original,'prepare_dispatch_index',CANDIDATE.prepare_dispatch_index,create=True):
                super().setUpClass()
            assert CANDIDATE._dispatch_index(cls.built[0]) is not None

        def test_actual_config_worker_pickle_and_metadata_scope(self):
            cfg=self.built[0];before=pickle.dumps(cfg);restored=pickle.loads(before)
            self.assertIs(CANDIDATE._dispatch_index(restored)['source_inputs'],restored.network.native_internal_inputs['inputs'])
            self.assertEqual(restored.network.native_internal_inputs,cfg.network.native_internal_inputs)
            self.assertNotIn('native_prehead_dispatch_index',restored.network.native_internal_inputs)
            self.assertEqual(pickle.dumps(cfg),before)
    with patch.object(actual,'prehead',CANDIDATE):
        live=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ActualIndexed))
    cfg,state=fixture();indexed=deepcopy(cfg);CANDIDATE.prepare_dispatch_index(indexed)
    count=4000;measurements=[]
    for module,c in ((original,cfg),(CANDIDATE,indexed)):
        s=deepcopy(state);start=time.perf_counter()
        with patch.object(module,'_check',wraps=module._check) as check:
            for _ in range(count):
                module.limit_intended(s,c,'other',3.,1.,180)
                module.receive_accepted(s,c,'other',1.,180)
        measurements.append({'module':'original' if module is original else 'indexed','calls_per_function':count,
                             'check_calls':check.call_count,'wall_sec':time.perf_counter()-start,
                             'state_sha256':hashlib.sha256(pickle.dumps(s)).hexdigest()})
    assert measurements[0]['state_sha256']==measurements[1]['state_sha256']
    assert all(x['check_calls']==count for x in measurements)
    timings=[]
    # No validation mocking here: alternate module order and report every tiny
    # timing. These synthetic cohort lengths are not a claim about a real run.
    for multiplier in (1,10,100):
        cfg,state=fixture();state.native_input_prehead_state['cohorts']=[deepcopy(c) for _ in range(multiplier) for c in state.native_input_prehead_state['cohorts']]
        state.native_input_prehead_state['initial_veh']*=multiplier
        state.urban_movement_queue['A']*=multiplier;state.urban_movement_queue['B']*=multiplier
        cfg.network.urban_link_storage_veh['origin']=100.*multiplier
        state.urban_link_storage['origin']=94.*multiplier
        indexed=deepcopy(cfg);CANDIDATE.prepare_dispatch_index(indexed)
        row={'cohorts':3*multiplier,'calls_each':1000,'original_sec':[],'indexed_sec':[],'identical_final_state':True}
        for repeat in range(4):
            outputs={}
            pairs=((original,cfg),(CANDIDATE,indexed))
            if repeat%2:pairs=tuple(reversed(pairs))
            for module,c in pairs:
                s=deepcopy(state);start=time.perf_counter()
                for _ in range(1000):
                    module.limit_intended(s,c,'other',3.,1.,180)
                    module.receive_accepted(s,c,'other',1.,180)
                name='original' if module is original else 'indexed'
                row[name+'_sec'].append(time.perf_counter()-start)
                outputs[name]=pickle.dumps(s)
            assert outputs['original']==outputs['indexed']
        row['median_indexed_over_original']=statistics.median(row['indexed_sec'])/statistics.median(row['original_sec'])
        timings.append(row)
    changes=[p for p,h in PINS.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    report={'schema':'prehead-index-regression/v1','production_applied':False,'focused_tests':result.testsRun,
            'focused_passed':result.wasSuccessful(),'actual_contract_tests':live.testsRun,'actual_contract_passed':live.wasSuccessful(),
            'microbench':measurements,'microbench_scope':'Single-process tiny fixture with mock call counting; not worker/fullmain speedup. All _check calls retained.',
            'synthetic_unmocked_benchmarks':timings,
            'timing_limit':'Concurrent parent profile may affect all wall measurements. Synthetic 3/30/300-cohort fixtures are not an observed rollout distribution or a full-main speed claim.',
            'source_changes':changes}
    (ROOT/'diagnostics/prehead_dispatch_optimization_validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if not result.wasSuccessful() or not live.wasSuccessful() or changes:raise SystemExit(1)


if __name__=='__main__':main()
