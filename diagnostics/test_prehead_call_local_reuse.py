"""Prepared synthetic exact-function regressions; no model or full cfg setup.

Run only in the parent-authorized test window. No tests run on module import.
"""
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import subprocess
import sys
from types import SimpleNamespace as NS, ModuleType
import unittest

from diagnostics.prepare_prehead_call_local_reuse import ROOT,SOURCE,BEFORE_SHA256,FIXTURE,functions,proposed_source


def load_pair():
    manifest=json.loads((ROOT/'diagnostics/prehead_call_local_reuse_manifest.json').read_text(encoding='utf-8'))
    raw=FIXTURE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['fixture_sha256']:
        raise AssertionError('Frozen original functions changed')
    original=ModuleType('prehead_call_local_original')
    exec(compile(raw,str(FIXTURE),'exec'),original.__dict__)
    current=(ROOT/SOURCE).read_bytes(); current_sha=hashlib.sha256(current).hexdigest()
    if current_sha==BEFORE_SHA256:
        source=proposed_source()
    elif current_sha==manifest['after_lf_sha256']:
        source=current.decode('utf-8')
    else:
        raise AssertionError('Unknown before/after production source')
    candidate=ModuleType('prehead_call_local_candidate')
    candidate.__dict__.update(defaultdict=defaultdict,math=math,EPS=1e-8)
    exec(compile('\n\n'.join(functions(source).values()),'<prehead-call-local-four-functions>','exec'),candidate.__dict__)
    return original,candidate


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


def outcome(module,state,cfg,movement='other',vehicles=0.,step=180):
    try:
        value=module.receive_accepted(state,cfg,movement,vehicles,step)
        return ('return',value,pickle.dumps(state))
    except Exception as exc:
        return ('raise',type(exc).__name__,str(exc),pickle.dumps(state))


class CallLocalTests(unittest.TestCase):
    def setUp(self):
        self.original,self.candidate=load_pair()

    def pair(self,cfg,state,movement='other',vehicles=0.,step=180):
        before=pickle.dumps(cfg)
        a=outcome(self.original,deepcopy(state),cfg,movement,vehicles,step)
        b=outcome(self.candidate,deepcopy(state),cfg,movement,vehicles,step)
        self.assertEqual(a,b)
        self.assertEqual(pickle.dumps(cfg),before)
        return a

    def test_same_check_and_blocked_calls_one_fewer_input_scan(self):
        cfg,state=fixture(); traces=[]
        for module in (self.original,self.candidate):
            events=[]
            for name in ('_inputs','_blocked','_check'):
                fn=getattr(module,name)
                def observed(*args,_fn=fn,_name=name,**kwargs):
                    events.append(_name);return _fn(*args,**kwargs)
                setattr(module,name,observed)
            outcome(module,deepcopy(state),cfg)
            traces.append(events)
        self.assertEqual(traces[0],['_inputs','_blocked','_check','_inputs'])
        self.assertEqual(traces[1],['_inputs','_blocked','_check'])

    def test_relevant_proportional_departure_exact(self):
        cfg,state=fixture();state.urban_movement_queue['A']-=2.
        result=self.pair(cfg,state,'A',2.)
        after=pickle.loads(result[-1]).native_input_prehead_state
        self.assertEqual(after['departed_scope_veh'],.6)
        self.assertEqual(after['wn_actual'],{'A':2.})

    def test_invalid_state_errors_and_partial_mutation_exact(self):
        for kind in ('negative','nan','missing_input','missing_route','subset','storage','balance','wrong_step'):
            with self.subTest(kind=kind):
                cfg,state=fixture();local=state.native_input_prehead_state;step=180
                if kind=='negative':local['cohorts'][0]['vehicles']=-1.
                elif kind=='nan':local['cohorts'][0]['vehicles']=float('nan')
                elif kind=='missing_input':local['cohorts'][0]['input']='missing'
                elif kind=='missing_route':local['cohorts'][0]['route']='missing'
                elif kind=='subset':state.urban_movement_queue['A']=0.
                elif kind=='storage':state.urban_link_storage['origin']=100.
                elif kind=='balance':local['initial_veh']=90.
                else:step=181
                self.assertEqual(self.pair(cfg,state,step=step)[0],'raise')

    def test_zero_and_irrelevant_notifications_do_not_skip_validation_or_pruning(self):
        cfg,state=fixture();state.native_input_prehead_state['cohorts'].append(
            dict(state.native_input_prehead_state['cohorts'][0],vehicles=0.))
        result=self.pair(cfg,state)
        self.assertEqual(len(pickle.loads(result[-1]).native_input_prehead_state['cohorts']),3)
        state.native_input_prehead_state['initial_veh']=99.
        self.assertEqual(self.pair(cfg,state)[0],'raise')

    def test_blocked_and_future_ready_discharge_errors_exact(self):
        for movement in ('B','A'):
            cfg,state=fixture()
            if movement=='A':state.native_input_prehead_state['cohorts'][0]['ready']=181
            state.urban_movement_queue[movement]=0.
            result=self.pair(cfg,state,movement,4.)
            self.assertEqual(result[:3],('raise','ValueError','Native blocked first-head cohort was discharged early'))

    def test_same_cardinality_nested_changes_between_calls_are_fresh(self):
        for kind in ('branch','origin','wn','kind','replace_row','replace_source'):
            with self.subTest(kind=kind):
                cfg,state=fixture(); source=cfg.network.native_internal_inputs['inputs']; count=len(source)
                # Warm the same module and cfg objects; no result survives this call.
                self.pair(cfg,state)
                row=source['1093'];spec=row['prehead_spec']
                if kind=='branch':spec['branches']['1']['movement']='C'
                elif kind=='origin':
                    spec['origin']='empty';cfg.network.urban_link_storage_veh['empty']=100.;state.urban_link_storage['empty']=100.
                elif kind=='wn':spec['wn_movements']=['B','C']
                elif kind=='kind':row['kind']='irrelevant'
                elif kind=='replace_row':source['1093']=dict(row,kind='irrelevant')
                else:cfg.network.native_internal_inputs={'inputs':{**source,'1093':dict(row,kind='irrelevant')}}
                self.assertEqual(len(cfg.network.native_internal_inputs['inputs']),count)
                state.urban_movement_queue['A']-=2.
                result=self.pair(cfg,state,'A',2.)
                if kind in ('branch','origin'):self.assertEqual(result[0],'raise')
                elif kind=='wn':self.assertEqual(pickle.loads(result[-1]).native_input_prehead_state['wn_actual'],{})
                else:self.assertEqual(pickle.loads(result[-1]).native_input_prehead_state['departed_scope_veh'],0.)

    def test_direct_check_still_scans_current_cfg_every_time(self):
        cfg,state=fixture()
        for module in (self.original,self.candidate):
            module._check(deepcopy(state),cfg)
        cfg.network.native_internal_inputs['inputs']['1093']['prehead_spec']['branches']['1']['movement']='C'
        for module in (self.original,self.candidate):
            with self.assertRaisesRegex(ValueError,'subset exceeds actual queue: C'):
                module._check(deepcopy(state),cfg)

    def test_absent_feature_returns_without_requiring_prehead_state(self):
        cfg,state=fixture();cfg.network.native_internal_inputs['inputs'].pop('1093')
        del state.native_input_prehead_state
        self.assertEqual(self.pair(cfg,state)[0],'return')

    def test_cohort_order_and_candidate_clones_preserved(self):
        cfg,state=fixture();state.native_input_prehead_state['cohorts'].reverse()
        for copied_cfg in (deepcopy(cfg),pickle.loads(pickle.dumps(cfg))):
            self.pair(copied_cfg,state)
            self.assertFalse(hasattr(copied_cfg.network,'native_prehead_dispatch_index'))

    def test_nested_value_change_during_same_call_is_visible_through_row_reference(self):
        # Synthetic read-hook changes a nested value; no field value is copied/cached.
        outcomes=[]
        for module in (self.original,self.candidate):
            cfg,state=fixture();blocked=module._blocked
            def changing(*args,_original=blocked,**kwargs):
                result=_original(*args,**kwargs)
                cfg.network.native_internal_inputs['inputs']['1093']['prehead_spec']['origin']='empty'
                cfg.network.urban_link_storage_veh['empty']=100.;state.urban_link_storage['empty']=100.
                return result
            module._blocked=changing
            outcomes.append(outcome(module,state,cfg))
        self.assertEqual(*outcomes)
        self.assertEqual(outcomes[0][0],'raise')

    def test_fresh_process_synthetic_pickle_has_no_inter_call_cache(self):
        result=subprocess.run([sys.executable,'-X','utf8','-m',__name__ if __name__!='__main__' else 'diagnostics.test_prehead_call_local_reuse','--worker'],
            cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'exact':True,'new_model_evaluations':0})


def worker():
    original,candidate=load_pair();cfg,state=fixture()
    cfg,state=pickle.loads(pickle.dumps((cfg,state)))
    assert outcome(original,deepcopy(state),cfg)==outcome(candidate,deepcopy(state),cfg)
    cfg.network.native_internal_inputs['inputs']['1093']['kind']='irrelevant'
    assert outcome(original,deepcopy(state),cfg)==outcome(candidate,deepcopy(state),cfg)
    print(json.dumps({'exact':True,'new_model_evaluations':0}))


if __name__=='__main__':
    if '--worker' in sys.argv:worker()
    else:unittest.main()
