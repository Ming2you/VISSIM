"""Compare the compiled transport to the preserved production loop, including AD."""
import ast
import copy
import json
from pathlib import Path
import pickle
import sys
from types import SimpleNamespace as NS
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers import sdmpc_tangent_transport as transport


def reference_loop():
    path=ROOT/'diagnostics/sdmpc_array_transport_20260922/before_sources/evaluation/controllers/physical_lane_groups.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    advance=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='advance')
    loop=next(n for n in ast.walk(advance) if isinstance(n,ast.For)
              and ast.unparse(n.iter)=='enumerate(self.matrices)')
    function=ast.parse('def reference(self,before,oldv,part_before,free,through,incoming,outgoing,incoming_moment,part_in_moment,intent_before):\n    inter=[]\n    return inter').body[0]
    function.body.insert(1,loop)
    namespace={'min':ad.minimum,'max':ad.maximum}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(path),'exec'),namespace)
    return namespace['reference']


REFERENCE=reference_loop()


def inputs(mode, seed):
    rng=np.random.default_rng(seed)
    trace=ad.Trace([1.]*12) if mode else None
    axis=0
    def number(v):
        nonlocal axis
        axis+=1
        if trace is not None and (mode==2 or axis%3==0):
            return ad.Dual(v,{axis%12:1.,(axis+5)%12:.5},trace)
        return v
    sizes=[2,3,1]
    before=[[number(float(rng.uniform(1,20))) for _ in range(n)] for n in sizes]
    if seed%3==0:before[0][0]=number(0.)
    oldv=[[number(float(rng.uniform(10,100))) for _ in range(n)] for n in sizes]
    free=[[number(float(rng.choice([0.,.1,10.]))) for _ in range(n)] for n in sizes]
    through=[[number(float(rng.choice([0.,.2,5.]))) for _ in range(n)] for n in sizes]
    incoming=[[number(.03)]*n for n in sizes]
    outgoing=[[0.]*n for n in sizes]
    moment=copy.deepcopy(incoming) if seed%2 else None
    parts={1:{'post_v':oldv[1]}}
    part_moment={1:[0.]*3,2:[0.]}
    initial={'a':[[n*.2 for n in before[0]]],
             'b':[[n*.3 for n in row] for row in before[:2]]}
    plant=NS(n=before,matrices=[[[.2,.3,.5],[0.,.75,.25]],[[1.],[1.],[1.]]],
             upstream_off=copy.deepcopy(initial),off={'a':[number(.1)]*3,'b':[number(.2)]})
    return trace,(plant,before,oldv,parts,free,through,incoming,outgoing,moment,part_moment,initial)


def outputs(args,result):
    plant=args[0]
    def flatten(x):
        if isinstance(x,dict):return [v for c in x.values() for v in flatten(c)]
        if isinstance(x,(list,tuple)):return [v for c in x for v in flatten(c)]
        return [] if x is None else [x]
    return flatten([result,*args[6:10],plant.upstream_off,plant.off])


class ArrayTransportTests(unittest.TestCase):
    def test_values_tape_branch_support_and_jacobians_match_original_loop(self):
        prior=ad.FAST_PRIMITIVES
        ad.FAST_PRIMITIVES=True
        try:
            for mode in (0,1,2):
                for seed in range(6):
                    traces=[];results=[]
                    for function in (REFERENCE,transport.longitudinal):
                        trace,args=inputs(mode,seed)
                        result=function(*args)
                        traces.append(trace);results.append(outputs(args,result))
                    np.testing.assert_array_equal(*[[ad.primal(v) for v in out] for out in results])
                    if mode:
                        for field in ('p1','p2','w1','w2','counts','exact_support','discrete_support'):
                            self.assertEqual(getattr(traces[0],field),getattr(traces[1],field),(mode,seed,field))
                        np.testing.assert_array_equal(*[t.jacobian(out,workers=1) for t,out in zip(traces,results)])
        finally:ad.FAST_PRIMITIVES=prior

    def test_compensated_plain_prefix_and_general_sum_after_dual(self):
        for row in ([1e16,1.,1.], [1.,1e100,-1e100,2.], [.1]*97, [0.,1.,1e-20,2.], []):
            packed=transport.Packed();packed.row(row);arrays=packed.arrays()
            counters=np.zeros(4,dtype=np.int64);parents=np.zeros((100,2),dtype=np.int64)
            weights=np.zeros((100,2),dtype=np.float64)
            value=transport._ordered_sum(*arrays,counters,parents,weights)
            self.assertEqual(value[0],sum(row))
        trace=ad.Trace([1.]);x=ad.Dual(2.,{0:1.},trace)
        row=[1e16,1.,1.,x,-1e16,1.]
        packed=transport.Packed();packed.row(row);arrays=packed.arrays()
        actual=transport._ordered_sum(*arrays,counters,parents,weights)
        self.assertEqual(actual[0],ad.primal(sum(row)))

    def test_nonfinite_mixed_readonly_and_frozen_inputs_fail(self):
        for value in (float('nan'),float('inf')):
            packed=transport.Packed();packed.row([value])
            with self.assertRaisesRegex(ValueError,'Nonfinite'):packed.arrays()
        a=ad.Dual(1.,{0:1.},ad.Trace([1.]));b=ad.Dual(2.,{0:1.},ad.Trace([1.]))
        packed=transport.Packed();packed.row([a,b])
        with self.assertRaisesRegex(ValueError,'mixed'):packed.arrays()
        packed=transport.Packed();packed.row([a]);a.trace.frozen=True
        with self.assertRaisesRegex(ValueError,'frozen'):packed.arrays()
        a.trace.frozen=False
        prior=ad.PRIMAL_GUARD;ad.PRIMAL_GUARD=True
        try:
            with self.assertRaisesRegex(ValueError,'read-only'):packed.arrays()
        finally:ad.PRIMAL_GUARD=prior

    def test_option_is_explicit_and_requires_reverse_scoped_prediction(self):
        from evaluation.controllers import sdmpc
        cfg=pickle.loads((ROOT/'diagnostics/sdmpc_trial_20260922/trial_h3_v1/request.pickle').read_bytes())['owned'][0].cfg
        tuning=json.loads((ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json').read_text())
        self.assertNotIn('array_transport',sdmpc.configure(tuning,copy.deepcopy(cfg)))
        tuning['adapter']['sdmpc_array_transport']=True
        self.assertTrue(sdmpc.configure(tuning,copy.deepcopy(cfg))['array_transport'])
        for change in ({'sdmpc_array_transport':1},{'sdmpc_prediction_cache':False},
                       {'sdmpc_tangent_backend':'forward'}):
            other=copy.deepcopy(tuning);other['adapter'].update(change)
            with self.assertRaises(ValueError):sdmpc.configure(other,copy.deepcopy(cfg))


if __name__=='__main__':unittest.main()
