"""Compare real FIFO methods to the preserved source, including reverse tapes."""
import ast
import copy
from collections import deque
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers import sdmpc_prediction_cache as cache
from evaluation.controllers.sdmpc_tangent_runtime import Transform,namespace
from evaluation.controllers import sdmpc_tangent_runtime as runtime


def load(path):
    tree=Transform().visit(ast.parse(path.read_bytes(),filename=str(path)))
    previous=runtime.ad
    try:
        runtime.ad=ad
        ns={'__name__':'evaluation.controllers.physical_urban_transport',**namespace()}
    finally:runtime.ad=previous
    exec(compile(ast.fix_missing_locations(tree),str(path),'exec'),ns)
    return ns


OLD=load(ROOT/'diagnostics/sdmpc_persistent_plant_20260922/before_sources/evaluation/controllers/physical_urban_transport.py')
NEW=load(ROOT/'evaluation/controllers/physical_urban_transport.py')


def configuration(enabled):return NS(network=NS(sdmpc_options=dict(prediction_cache=True,persistent_urban_fifo=enabled)))


def flatten(value):
    if isinstance(value,dict):return [v for part in value.values() for v in flatten(part)]
    if isinstance(value,(list,tuple,deque)):
        return [v for part in value for v in flatten(part)]
    return [value] if isinstance(value,(float,ad.Dual)) else []


class PersistentFIFOTests(unittest.TestCase):
    def setUp(self):
        self.flags=ad.DIRECT_SUM_NODES,ad.FAST_PRIMITIVES
        ad.DIRECT_SUM_NODES=True;ad.FAST_PRIMITIVES=True

    def tearDown(self):
        ad.DIRECT_SUM_NODES,ad.FAST_PRIMITIVES=self.flags

    def case(self,enabled,mode,seed):
        ns=NEW if enabled else OLD
        trace=ad.Trace([1.]*4)
        def value(v,j):return ad.Dual(v,{j%4:1.},trace) if mode else v
        with cache.scope(configuration(enabled)):
            q=ns['FIFO']([(0,value(.7,0)),(1,value(.4,1)),(0,value(.5,2)),(2,value(.9,3))])
            before=q.stock
            q.append(2,value(.13,0));q.append(3,value(.27,1))
            receipts=q.take(value((.31,.7,1.0)[seed%3],2))
            phase=ns['IndexedLateralDepartures'](q)
            phase.take_label(2,value(.2,1));phase.take_label(0,value(.15,0));phase.commit()
            q.compact_runs(lambda label:label%2)
            counts=q.counts();stock=q.stock
            snapshots=copy.deepcopy(list(q.q))
            # Direct materialization gives a state snapshot without retaining an arena.
            array_buffer=q._array(create=False) if enabled else None
            if enabled:
                self.assertIs(array_buffer,q._array())
                self.assertIs(array_buffer.v,q._array().v)
            q.take(value(.05,3))
            outputs=flatten([before,receipts,counts,stock,snapshots,list(q.q)])
        self.assertIsInstance(q.__dict__['q'],deque)
        return trace,outputs

    def test_transport_chain_values_graph_and_jacobian(self):
        for mode in (0,1):
            for seed in range(3):
                with self.subTest(mode=mode,seed=seed):
                    old,a=self.case(False,mode,seed);new,b=self.case(True,mode,seed)
                    np.testing.assert_array_equal([ad.primal(v) for v in a],[ad.primal(v) for v in b])
                    if mode:
                        for field in ('p1','p2','w1','w2','counts','exact_support','discrete_support'):
                            self.assertEqual(getattr(old,field),getattr(new,field),field)
                        np.testing.assert_array_equal(old.jacobian(a,workers=1),new.jacobian(b,workers=1))

    def test_unindexed_zero_and_invalid_requests(self):
        for ns,enabled in ((OLD,False),(NEW,True)):
            with cache.scope(configuration(enabled)):
                q=ns['FIFO']([(0,.5),(1,.6),(0,.7)])
                self.assertEqual(q.take(0.),[])
                q.take_label(0,.6)
                self.assertEqual(q.counts(),{0:.6,1:.6})
                with self.assertRaises(ArithmeticError):q.take(3.)
                with self.assertRaises(ArithmeticError):q.take_label(1,3.)

    def test_persistent_snapshots_guarded_reads_and_scope_cleanup(self):
        from evaluation.controllers.sdmpc_tangent_fifo import get
        trace=ad.Trace([1.])
        q=NEW['FIFO']([(0,ad.Dual(2.,{0:1.},trace)),(1,1.)])
        with cache.scope(configuration(True)):
            q.take(.25);buffer=get(q);address=buffer.v.ctypes.data
            saved=copy.deepcopy(q)
            saved_values=[ad.primal(n) for _,n in saved.q]
            q.take(.5);q.append(1,.2)
            self.assertIs(buffer,get(q));self.assertEqual(address,buffer.v.ctypes.data)
            self.assertEqual(saved_values,[ad.primal(n) for _,n in saved.q])
            before=q.stock;nodes=len(trace.p1)
            try:
                ad.PRIMAL_GUARD=True
                q.stock;q.counts()
            finally:ad.PRIMAL_GUARD=False
            self.assertEqual(len(trace.p1),nodes)
            self.assertIs(q.stock,before)
        self.assertIsNone(cache.active())
        self.assertEqual(set(vars(q)),{'q'})
        self.assertEqual([ad.primal(n) for _,n in q.q],[1.25,1.2])
        with self.assertRaisesRegex(RuntimeError,'injected failure'):
            with cache.scope(configuration(True)):
                q.take(.1)
                raise RuntimeError('injected failure')
        self.assertIsNone(cache.active())

    def test_fractional_chain_over_many_steps(self):
        for mode in (0,1):
            trials=[]
            for enabled in (False,True):
                ns=NEW if enabled else OLD;trace=ad.Trace([1.]*3)
                def value(v,j):return ad.Dual(v,{j%3:1.},trace) if mode else v
                with cache.scope(configuration(enabled)):
                    q=ns['FIFO']([(0,value(10.,0)),(1,value(4.,1)),(0,value(2.,2))])
                    outputs=[]
                    for i in range(30):
                        q.append(i%3,value(.3,(i//10)%3))
                        q.take(value(.1,(i//10)%3))
                        phase=ns['IndexedLateralDepartures'](q)
                        phase.take_label(1,.03);phase.commit()
                        q.compact_runs(lambda label:label%2)
                        outputs.extend(flatten([q.counts(),q.stock]))
                    outputs.extend(flatten(list(q.q)))
                trials.append((trace,outputs))
            (ta,a),(tb,b)=trials
            np.testing.assert_array_equal([ad.primal(v) for v in a],[ad.primal(v) for v in b])
            if mode:
                for field in ('p1','p2','w1','w2','counts','exact_support','discrete_support'):
                    self.assertEqual(getattr(ta,field),getattr(tb,field),field)
                np.testing.assert_array_equal(ta.jacobian(a,workers=1),tb.jacobian(b,workers=1))

    def test_default_and_option_prerequisites(self):
        from evaluation.controllers import sdmpc
        import json
        base=json.loads((ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json').read_text(encoding='utf-8'))
        import pickle
        request=pickle.loads((ROOT/'diagnostics/sdmpc_trial_20260922/trial_h3_v1/request.pickle').read_bytes())
        cfg=copy.deepcopy(request['owned'][0].cfg)
        self.assertFalse(sdmpc.configure(base,cfg).get('persistent_urban_fifo',False))
        candidate=copy.deepcopy(base);candidate['adapter']['sdmpc_persistent_urban_fifo']=True
        self.assertTrue(sdmpc.configure(candidate,cfg)['persistent_urban_fifo'])
        candidate['adapter']['sdmpc_prediction_cache']=False
        with self.assertRaises(ValueError):sdmpc.configure(candidate,cfg)


if __name__=='__main__':unittest.main()
