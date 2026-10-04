"""Derivative checks at smooth points, and actuator/conservation contracts."""
from pathlib import Path
import ast
import math
import sys
import unittest
from collections import deque
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_dual as ad
from evaluation.controllers import sdmpc_continuous as relaxed
from evaluation.controllers.sdmpc_tangent_runtime import Transform, namespace
from evaluation.controllers.sdmpc_tangent_worker import state_error
from evaluation.controllers.sdmpc_tangent import checked_matrices


class TangentTests(unittest.TestCase):
    def test_lean_trace_keeps_jacobian_without_fd_risk_propagation(self):
        def predict(full):
            trace = ad.Trace([.01,.01],track_stencils=full)
            u = ad.Dual(3.2,{0:1.},trace)
            q = ad.Dual(.4,{1:1.},trace)
            cost = 0.
            for step in range(30):
                served = ad.minimum(q, ad.maximum(0.,u-step/5.))
                q = q+.13-served
                cost += (q-0.)*1./1.+served*0.
            return cost,trace
        full,_ = predict(True)
        lean,trace = predict(False)
        self.assertEqual(ad.primal(full),ad.primal(lean))
        self.assertEqual(ad.derivative(full),ad.derivative(lean))
        self.assertFalse(trace.result([lean])['stencil_crossings_assessed'])
        x=ad.Dual(2.,{0:1.},trace)
        zero=ad.Dual(0.,{1:1.},trace)
        one=ad.Dual(1.,{1:1.},trace)
        self.assertEqual(ad.derivative(x*zero),{1:2.})
        self.assertEqual(ad.derivative(x/one),{0:1.,1:-2.})

    def test_lateral_overdraw_guard_keeps_original_float_addition_order(self):
        from evaluation.controllers.physical_urban_transport import FIFO
        queue = FIFO([(label, .1) for _ in range(10) for label in (1,2)])
        # Python 3.12 sum(float) can use a different summation algorithm than
        # Counter's repeated +=. The original guard's last-ULP rejection is
        # part of the contract, even though the large overdraw tolerance stays.
        original_limit = queue.counts()[1]+1e-7
        with self.assertRaises(ArithmeticError):
            queue.take_label(1, math.nextafter(original_limit, math.inf))

    def test_lateral_label_fast_path_preserves_primal_and_jacobian(self):
        from evaluation.controllers import physical_urban_transport as transport
        from collections import Counter
        # Instrument both implementations exactly as the worker does. Repeated
        # labels, nonadjacent fragments and exhausted prefixes exercise FIFO.
        source = '''
def reference(queue, label, amount):
    counts = Counter()
    for old_label, n in queue:
        counts[old_label] += n
    if amount < -EPS or amount > counts[label]+1e-7:
        raise ArithmeticError('Lateral label overdraw')
    remaining = amount
    result = deque()
    for old_label, n in queue:
        moved = min(n, remaining) if old_label == label else 0.
        remaining -= moved
        if n-moved > EPS:
            result.append([old_label, n-moved])
    return result
'''
        import inspect, textwrap
        fast = textwrap.dedent(inspect.getsource(transport.FIFO.take_label))
        ns = dict(namespace(), Counter=Counter, deque=deque, EPS=transport.EPS,
                  prediction_cache=transport.prediction_cache)
        exec(compile(ast.fix_missing_locations(Transform().visit(ast.parse(source+'\n'+fast))), '<fifo-test>', 'exec'), ns)
        trace = ad.Trace([.01]*4)
        packets = deque([[i%4, ad.Dual(.5+i/30.,{i%4:1.},trace)] for i in range(30)])
        for label, amount in [(2, .2),(0,1.6),(3,.5),(1,3.)]:
            dual_amount = ad.Dual(amount, {label:.3},trace)
            expected = ns['reference'](packets,label,dual_amount)
            queue = type('Queue',(),{})()
            # This extracted-method fixture exercises the unchanged object path.
            # The real FIFO's array path is tested separately against this path.
            queue._array = lambda: None
            queue.q = packets
            ns['take_label'](queue,label,dual_amount)
            self.assertEqual([x[0] for x in queue.q],[x[0] for x in expected])
            for (_, got),(_, want) in zip(queue.q,expected):
                self.assertEqual(ad.primal(got),ad.primal(want))
                self.assertEqual(ad.derivative(got),ad.derivative(want))
            packets = queue.q
        for fn in (lambda: ns['reference'](packets,0,100.),
                   lambda: ns['take_label'](queue,0,100.)):
            with self.assertRaises(ArithmeticError): fn()

    def test_fractional_native_exit_budget_is_spent_once(self):
        from diagnostics.test_lane_plant_coupling import UrbanReceivingTests
        p = UrbanReceivingTests.toy({1:[((10634,1),.01),((10634,2),2.)]})
        p.program.service_fraction_at = lambda *args, **kw: .4
        p.step({}, exit_receiving={10634:100.,10635:100.,10642:100.})
        self.assertAlmostEqual(sum(p.departed.values()), .4*p.capacity_rate)
        self.assertAlmostEqual(sum(p.counts().values())+sum(p.departed.values()), 2.01)

    def test_zero_fraction_retains_queue(self):
        from diagnostics.test_lane_plant_coupling import UrbanReceivingTests
        p = UrbanReceivingTests.toy({1:[((10634,1),2.)]})
        p.program.service_fraction_at = lambda *args, **kw: 0.
        p.step({}, exit_receiving={10634:100.,10635:100.,10642:100.})
        self.assertEqual(sum(p.departed.values()),0.)
        self.assertEqual(sum(p.counts().values()),2.)

    def test_no_implicit_derivative_loss(self):
        x = ad.Dual(2., {0:1.}, ad.Trace([.1]))
        with self.assertRaises(TypeError):
            float(x)
        with self.assertRaises(TypeError):
            np.asarray([x], dtype=float)

    def test_chain_rule_across_prediction(self):
        def rollout(u):
            n, v, cost = 8., 35., 0.
            for _ in range(30):
                v += .07*(100.*ad.MathProxy.exp(-n/24.)-v)+.02*u
                n = n+.12-.001*n*v
                cost += n/3600.
            return cost
        trace = ad.Trace([.001])
        result = rollout(ad.Dual(20., {0:1.}, trace))
        h = 1e-4
        finite = (rollout(20.+h)-rollout(20.-h))/(2*h)
        self.assertAlmostEqual(ad.derivative(result)[0], finite, delta=1e-10)
        self.assertGreater(trace.operations, 30)

    def test_fsum_retains_primal_accuracy_and_tangents(self):
        trace = ad.Trace([.1])
        values = [ad.Dual(1e16, {0:3.}, trace), ad.Dual(1., {0:2.}, trace), -1e16]
        total = ad.MathProxy.fsum(values)
        self.assertEqual(ad.primal(total), 1.)
        self.assertEqual(ad.derivative(total), {0:5.})

    def test_signal_cycle_conserves_green_and_offset(self):
        for offset in (0., .4, 11.3, 39.7):
            trace = ad.Trace([.001, .001])
            green, shift = ad.Dual(13.4, {0:1.}, trace), ad.Dual(offset, {1:1.}, trace)
            fractions = [relaxed.periodic_fraction(t, 1., 40., shift, 0., green, 2.) for t in range(40)]
            total = ad.MathProxy.fsum(fractions)
            self.assertAlmostEqual(ad.primal(total), 13.4, places=10)
            self.assertAlmostEqual(ad.derivative(total).get(0, 0.), 1., places=10)
            self.assertAlmostEqual(ad.derivative(total).get(1, 0.), 0., places=10)
            self.assertTrue(all(-1e-10 <= ad.primal(v) <= 1.+1e-10 for v in fractions))

    def test_green_and_offset_match_numeric_directional_check(self):
        def f(g, offset):
            return sum((t+1)*relaxed.periodic_fraction(t,1.,40.,offset,0.,g,2.) for t in range(17))
        trace = ad.Trace([.001, .001])
        y = f(ad.Dual(13.4,{0:1.},trace), ad.Dual(.3,{1:1.},trace))
        h = 1e-5
        self.assertAlmostEqual(ad.derivative(y)[0], (f(13.4+h,.3)-f(13.4-h,.3))/(2*h), delta=1e-6)
        self.assertAlmostEqual(ad.derivative(y)[1], (f(13.4,.3+h)-f(13.4,.3-h))/(2*h), delta=1e-6)

    def test_meter_interpolation_not_ceiling(self):
        row = {'service_by_green_veh_h':{'0':0.,'3':400.,'4':700.,'5':800.}}
        g = ad.Dual(3.4,{0:10.},ad.Trace([.01]))
        rate = relaxed.meter_rate(g,row)
        self.assertAlmostEqual(ad.primal(rate), 520.)
        self.assertEqual(ad.derivative(rate), {0:3000.})
        self.assertEqual(relaxed.meter_rate(4.,row),700.)

    def test_instrumentation_keeps_scalar_and_gradient(self):
        source = '''import math
def f(x):
    assert isinstance(x, (int, float))
    return math.fsum([float(x)*x, math.exp(x)])
'''
        ns = namespace()
        exec(compile(ast.fix_missing_locations(Transform().visit(ast.parse(source))), '<test>', 'exec'),ns)
        x = ad.Dual(.3,{0:1.},ad.Trace([.001]))
        y = ns['f'](x)
        self.assertEqual(ad.primal(y), ns['f'](.3))
        self.assertAlmostEqual(ad.derivative(y)[0], .6+math.exp(.3))

    def test_state_validation_does_not_skip_nested_stock(self):
        x = ad.Dual(3.,{0:1.},ad.Trace([.01]))
        self.assertEqual(state_error({'cohorts':[x]}, {'cohorts':[3.]}),0.)
        self.assertEqual(state_error({'cohorts':[x]}, {'cohorts':[4.]}),1.)
        with self.assertRaises(ValueError):
            state_error({'cohorts':[x]}, {'other':[3.]})
        self.assertEqual(state_error(deque([('ramp',x)]),deque([('ramp',3.)])),0.)
        self.assertEqual(state_error({'kernel':math}, {'kernel':math}), 0.)

    def test_sparse_ledger_comparison_preserves_missing_transfer_amount(self):
        row = dict(stage='urban',start_sec=1.,end_sec=2.,source='q',target=None,
                   route_key='sink:q',vehicles=1e-15,ttd_veh=1e-15,entered_veh=0.)
        self.assertEqual(state_error([row],[],'ledger.transfers'),1e-15)
        row['vehicles']=row['ttd_veh']=.1
        self.assertEqual(state_error([row],[],'ledger.transfers'),.1)
        other=dict(row,route_key='other')
        self.assertEqual(state_error([row],[other],'ledger.transfers'),.1)

    def test_relaxed_primal_difference_is_reported_not_hidden(self):
        receipt = dict(costs=[3.], resources=[2.,8.], cost_jacobian=[[4.]],
            resource_jacobian=[[5.],[6.]], fallback_reasons={},
            complete_primal_state_match=True, max_primal_state_error=0.)
        grad,matrix,fb = checked_matrices(receipt,np.array([3.2]),np.array([2.1,8.4]),[{}],1e-8)
        self.assertEqual(fb,{})
        np.testing.assert_allclose(receipt['anchor_correction_costs'],[.2])
        np.testing.assert_allclose(receipt['anchor_correction_resources'],[.1,.4])


if __name__ == '__main__':
    unittest.main()
