"""Mutation, branch and derivative preservation for exact traffic caches."""
import copy
import math
from pathlib import Path
import pickle
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_prediction_cache as cache
from evaluation.controllers import sdmpc_continuous as continuous
from evaluation.controllers import physical_urban_transport as transport
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary


def cfg(enabled=True):
    return NS(network=NS(sdmpc_options={'prediction_cache':enabled}))


class PredictionCacheTests(unittest.TestCase):
    def test_direct_sums_retain_every_tape_edge_and_derivative(self):
        import numpy as np
        from evaluation.controllers import sdmpc_tangent_reverse as ad
        results=[]
        for enabled in (False,True):
            with patch.object(ad,'DIRECT_SUM_NODES',enabled):
                trace=ad.Trace([.1,.1])
                a,b=ad.Dual(1.,{0:1.},trace),ad.Dual(3.,{1:2.},trace)
                out=[ad.MathProxy.fsum(v) for v in
                     ([],[a],[1.,2.],[a,a,b,2.],[a*1e16,a,a*-1e16],(a*.1 for _ in range(600)))]
                graph=tuple(list(v) for v in (trace.p1,trace.p2,trace.w1,trace.w2))
                results.append(([ad.primal(v) for v in out],graph,trace.jacobian(out,1)))
                with self.assertRaises(ValueError):ad.MathProxy.fsum([a,b])
                foreign=ad.Dual(1.,{0:1.},ad.Trace([.1]))
                with self.assertRaises(ValueError):ad.MathProxy.fsum([a,foreign])
                with self.assertRaises(ValueError):ad.MathProxy.fsum([math.inf,-math.inf])
        self.assertEqual(results[0][:2],results[1][:2])
        np.testing.assert_array_equal(results[0][2],results[1][2])

    def test_fifo_every_mutator_copy_and_scope(self):
        q=transport.FIFO([(i%3,.1+i/1000) for i in range(90)])
        def check():
            self.assertEqual(q.stock,math.fsum(n for _,n in q.q))
            self.assertEqual(q.stock,math.fsum(n for _,n in q.q))
        with cache.scope(cfg()) as local:
            check();self.assertIn(q,local.stocks)
            q.append(2,.125);check()
            q.append(8,.075);check()
            q.take(.123);check()
            q.take_label(1,.05);check()
            q.compact_runs(lambda label:label%2);check()
            lateral=transport.IndexedLateralDepartures(q)
            lateral.take_label(2,.03);lateral.commit();check()
            other=copy.deepcopy(q);self.assertNotIn(other,local.stocks)
            other.append(0,1.);self.assertAlmostEqual(other.stock-q.stock,1.)
            self.assertNotIn('stocks',vars(q))
            with cache.scope(cfg()):
                q.append(0,.25)
                self.assertEqual(q.stock,math.fsum(n for _,n in q.q))
            check()
            with cache.scope(cfg(False)):
                self.assertIsNone(cache.active())
                q.append(0,.25)
            check()
        self.assertIsNone(cache.active())
        check()

    def test_fifo_guards_and_no_incremental_sum(self):
        q=transport.FIFO([(0,1e16),(1,1.),(2,1.)])
        with cache.scope(cfg()):
            self.assertEqual(q.stock,1e16+2.)
            with self.assertRaises(ArithmeticError):q.take(q.stock+10.)
            with self.assertRaises(ValueError):q.append(0,float('nan'))
            self.assertEqual(q.stock,1e16+2.)
        with cache.scope(cfg(False)) as local:
            self.assertIsNone(local)

    def test_fifo_tangent_values_and_complete_axis_sum(self):
        from diagnostics.test_sdmpc_fifo_batch import classes
        from evaluation.controllers import sdmpc_dual as ad
        FIFO,Indexed=classes()
        results=[]
        for enabled in (False,True):
            trace=ad.Trace([.1]*3,track_stencils=False)
            q=FIFO([(i%3,ad.Dual(.4+i/100,{i%3:1.},trace)) for i in range(30)])
            with cache.scope(cfg(enabled)):
                out=[q.stock,q.stock]
                q.take(ad.Dual(.1,{1:.2},trace));out.append(q.stock)
                d=Indexed(q);d.take_label(2,ad.Dual(.05,{0:.4},trace));d.commit()
                out.extend([q.stock,q.stock]);q.append(1,.2);out.append(q.stock)
                results.append([(ad.primal(v),ad.derivative(v)) for v in out])
        self.assertEqual(*results)

    def test_continuous_signal_dynamic_changes_and_equal_primals(self):
        from evaluation.controllers import sdmpc_dual as ad
        basis=dict(kind='serial',cycle_sec=60.,amber_sec=2.,all_red_sec=1.,
                   phase_order=['p1','p2','p3','p4'],idle_after_phase_sec=dict.fromkeys(['p1','p2','p3','p4'],0.))
        c=cfg();c.simulation=NS(T_u_sec=1.)
        c.network.sdmpc_options['signal_transition_width_sec']=2.
        c.network.signal_actuation_contract={'nodes':{'SC1':{'native_clock_basis':basis}}}
        control=NS(green_times={'SC1_p'+str(i):10. for i in range(1,5)},offsets={'SC1':0.})
        spec={'phase':'SC1_p1'}
        original=continuous.periodic_fraction
        with patch.object(continuous,'periodic_fraction',wraps=original) as calculation,cache.scope(c):
            a=continuous.phase_fraction(control,c,spec,9)
            self.assertEqual(a,continuous.phase_fraction(control,c,spec,9))
            self.assertEqual(calculation.call_count,1)
            control.green_times['SC1_p1']=8.
            self.assertNotEqual(a,continuous.phase_fraction(control,c,spec,9))
            control.offsets['SC1']=2.
            continuous.phase_fraction(control,c,spec,9)
            basis['cycle_sec']=61.
            continuous.phase_fraction(control,c,spec,9)
            self.assertEqual(calculation.call_count,4)
            # Distinct seeds with the same primal cannot return one another.
            trace=ad.Trace([.1,.1],track_stencils=False)
            for axis in (0,1):
                control.green_times['SC1_p1']=ad.Dual(10.,{axis:1.},trace)
                continuous.phase_fraction(control,c,spec,9)
            self.assertEqual(calculation.call_count,6)

    def test_ramp_snapshot_all_checks_and_identical_stocks(self):
        ramp=PhysicalRampBoundary(connector_id='x',length_m=100.,head_position_m=40.,lanes=1,
            spacing_m=7.,travel_speed_kmh=36.,time_sec=0.,initial_cohorts=[(10.,36.,1),(60.,36.,1)])
        baseline=ramp.snapshot()
        with cache.scope(cfg()),patch.object(ramp,'_stocks',wraps=ramp._stocks) as stocks:
            self.assertEqual(ramp.snapshot(),baseline)
            self.assertEqual(stocks.call_count,1)
            ramp.cumulative_requested_veh+=1.
            with self.assertRaises(ValueError):ramp.snapshot()

    def test_options_absent_invalid_and_catalog_isolation(self):
        from evaluation.controllers import sdmpc,native_input_prehead as pre
        model=pickle.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').read_bytes())['owned'][0].cfg
        self.assertNotIn('prediction_cache',sdmpc.configure({'adapter':{'sdmpc':'proxlinear-v1'}},copy.deepcopy(model)))
        with self.assertRaises(ValueError):sdmpc.configure({'adapter':{'sdmpc':'proxlinear-v1','sdmpc_prediction_cache':1}},model)
        c=cfg();c.network.native_internal_inputs={'inputs':{'a':{'kind':'native_choice_prehead'},'b':{'kind':'other'}}}
        expected=pre._inputs(c)
        with cache.scope(c):
            self.assertEqual(pre._inputs(c),expected)
            self.assertIs(pre._inputs(c),pre._inputs(c))
        c.network.native_internal_inputs['inputs']['c']={'kind':'native_choice_prehead'}
        with cache.scope(c):self.assertEqual(set(pre._inputs(c)),{'a','c'})


if __name__=='__main__':unittest.main()
