"""Spatial receiver values, ordered gradients, shared inputs and branch ties."""
from pathlib import Path
import copy
import json
import pickle
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers import sdmpc_tangent_spatial as spatial


def reference(storage, stopline, queues, intended, rule):
    space=ad.maximum(0.,storage)
    if stopline is not None:space=ad.minimum(space,ad.maximum(0.,stopline))
    point=0.
    for value in queues:point+=ad.maximum(0.,value)
    space=ad.maximum(0.,space-point)
    total=sum(ad.maximum(v,0.) for v in intended.values())
    if total<=space or total<=1.e-9:
        out={k:ad.maximum(v,0.) for k,v in intended.items()}
    elif rule=='equal_split':
        share=space/max(len(intended),1)
        out={k:ad.minimum(ad.maximum(v,0.),share) for k,v in intended.items()}
    elif rule=='main_priority':
        out={};remaining=space
        for key in sorted(intended,key=lambda k:0 if k.startswith('in_') else 1):
            out[key]=ad.minimum(ad.maximum(intended[key],0.),remaining)
            remaining-=out[key]
    else:
        out={k:ad.maximum(v,0.)*space/total for k,v in intended.items()}
    return space,out


def values(result):
    space,out=result
    return [ad.primal(space),*[ad.primal(x) for x in out.values()]]


def graph(trace, outputs):
    seeds={node:axis for node,axis in zip(trace.seed_nodes,trace.seed_axes)}
    memo={0:None}
    def visit(node):
        if node not in memo:
            if node in seeds:memo[node]=('seed',seeds[node])
            else:memo[node]=(visit(trace.p1[node]),visit(trace.p2[node]),trace.w1[node],trace.w2[node])
        return memo[node]
    return [visit(x.node) if isinstance(x,ad.Dual) else None for x in outputs]


class SpatialReceiverTests(unittest.TestCase):
    def test_scalar_cases_and_cpython_compensated_prefix(self):
        cases=[(10.,None,[2.,1.],{'a':6.,'in_b':8.,'c':-1.}),
               (5.,3.,[3.],{'a':0.,'b':1.}),
               (2.,None,[],{'a':1.e16,'b':1.,'c':1.}),
               (4.,None,[],{}),(-1.,0.,[-2.],{'in_a':1.e-11,'b':1.e-11})]
        for rule in ('proportional','equal_split','main_priority'):
            expected=[reference(*case,rule) for case in cases]
            for workers in (1,2):
                actual=spatial.execute([spatial.prepare(*case) for case in cases],rule,kernel_workers=workers)
                self.assertEqual(actual,expected)
                self.assertEqual([list(x[1]) for x in actual],[list(x[1]) for x in expected])

    def test_values_graphs_and_jacobians_preserve_all_input_dependencies(self):
        for rule in ('proportional','equal_split','main_priority'):
            for workers in (1,2):
                traces=[];outputs=[];results=[]
                for compiled in (False,True):
                    trace=ad.Trace([1.]*6)
                    seeds=[ad.Dual(v,{i:1.},trace) for i,v in enumerate([8.,2.,3.,6.,1.,0.])]
                    cases=[(seeds[0],None,[seeds[1]],{'a':seeds[2],'in_b':seeds[3]}),
                           (seeds[0],5.,[seeds[4],seeds[5]],{'in_a':seeds[3],'b':seeds[2]}),
                           (seeds[5],None,[seeds[5]],{'a':seeds[5],'b':seeds[4]}),
                           (10.,None,[],{'prefix_a':1.e16,'prefix_b':1.,'c':seeds[2]})]
                    if compiled:
                        rows=[]
                        for case in cases:
                            rows.append(spatial.prepare(*case))
                            # Model the original shared-head operations between receivers.
                            _=seeds[0]*seeds[1]
                        result=spatial.execute(rows,rule,kernel_workers=workers)
                    else:
                        result=[]
                        for case in cases:
                            result.append(reference(*case,rule))
                            _=seeds[0]*seeds[1]
                    flattened=[v for space,out in result for v in (space,*out.values())]
                    traces.append(trace);outputs.append(flattened);results.append(result)
                self.assertEqual([values(r) for r in results[0]],[values(r) for r in results[1]])
                self.assertEqual([list(r[1]) for r in results[0]],[list(r[1]) for r in results[1]])
                self.assertEqual(graph(traces[0],outputs[0]),graph(traces[1],outputs[1]))
                self.assertEqual(traces[0].exact_support,traces[1].exact_support)
                self.assertEqual(traces[0].counts,traces[1].counts)
                matrices=[t.jacobian(out,workers=1) for t,out in zip(traces,outputs)]
                np.testing.assert_array_equal(*matrices)

    def test_mixed_tapes_and_nonfinite_values_fail(self):
        a=ad.Dual(1.,{0:1.},ad.Trace([1.]))
        b=ad.Dual(2.,{0:1.},ad.Trace([1.]))
        with self.assertRaisesRegex(ValueError,'mixed reverse tapes'):
            spatial.prepare(a,None,[],{'b':b})
        for invalid in (float('inf'),float('nan')):
            with self.assertRaisesRegex(ValueError,'Nonfinite'):
                spatial.prepare(invalid,None,[],{})

    def test_readonly_guard_and_frozen_tape_are_not_physics(self):
        trace=ad.Trace([1.]);a=ad.Dual(1.,{0:1.},trace)
        prior=ad.PRIMAL_GUARD
        try:
            ad.PRIMAL_GUARD=True
            with self.assertRaisesRegex(ValueError,'read-only'):
                spatial.prepare(a,None,[],{})
        finally:ad.PRIMAL_GUARD=prior
        trace.frozen=True
        with self.assertRaisesRegex(ValueError,'frozen tape'):
            spatial.prepare(a,None,[],{})

    def test_freeze_and_order_of_head_operations(self):
        trace=ad.Trace([1.]);a=ad.Dual(7.,{0:1.},trace)
        intended={'a':a*2.}
        row=spatial.prepare(a,None,[],intended)
        later=a*3.
        intended['a']=999.
        result=spatial.execute([row],'proportional',kernel_workers=1)[0]
        self.assertEqual(values(result),[7.,7.])
        self.assertLess(row['start']+row['capacity']-1,later.node)
        np.testing.assert_array_equal(trace.jacobian([result[1]['a'],later],workers=1),[[1.],[3.]])

    def test_config_is_opt_in_and_keeps_eight_worker_schedule(self):
        from evaluation.controllers import sdmpc
        cfg=pickle.loads((ROOT/'diagnostics/sdmpc_trial_20260922/trial_h3_v1/request.pickle').read_bytes())['owned'][0].cfg
        tuning=json.loads((ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json').read_text())
        self.assertNotIn('spatial_receiving',sdmpc.configure(tuning,copy.deepcopy(cfg)))
        tuning['adapter']['sdmpc_spatial_receiving']=True
        self.assertTrue(sdmpc.configure(tuning,copy.deepcopy(cfg))['spatial_receiving'])
        for change in ({'sdmpc_spatial_receiving':1},{'sdmpc_derivative_workers':7},
                       {'sdmpc_tangent_concurrent_primal':False}):
            other=copy.deepcopy(tuning);other['adapter'].update(change)
            with self.assertRaises(ValueError):sdmpc.configure(other,copy.deepcopy(cfg))


if __name__=='__main__':unittest.main()
