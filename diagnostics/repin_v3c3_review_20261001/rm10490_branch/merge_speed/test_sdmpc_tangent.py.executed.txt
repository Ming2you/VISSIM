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


class RampZeroTransferTests(unittest.TestCase):
    @staticmethod
    def ramp(backend, head=0.):
        source = (ROOT/'evaluation/controllers/physical_ramp_boundary.py').read_text(encoding='utf-8')
        ns = dict(namespace(), _tangent_float=backend.float_keep,
                  _tangent_min=backend.minimum, _tangent_max=backend.maximum,
                  _tangent_math=backend.MathProxy())
        exec(compile(ast.fix_missing_locations(Transform().visit(ast.parse(source))),
                     '<instrumented-ramp>', 'exec'), ns)
        return ns['PhysicalRampBoundary'](connector_id='test', length_m=100.,
            head_position_m=head, lanes=1, spacing_m=5., travel_speed_kmh=36., time_sec=0.)

    @staticmethod
    def gradient(backend, trace, value):
        if backend is ad:
            return ad.derivative(value).get(0, 0.)
        # The same reverse sweep without compilation keeps this unit test small.
        return backend._reverse_row(trace.p1, trace.p2, trace.w1, trace.w2,
            getattr(value, 'node', 0), trace.seed_nodes, trace.seed_axes, trace.seed_weights, 1)[0]

    def backends(self):
        from evaluation.controllers import sdmpc_tangent_reverse
        return (ad, sdmpc_tangent_reverse)

    def test_empty_head_preserves_transported_tangent_and_mass(self):
        for backend in self.backends():
            with self.subTest(backend=backend.__name__):
                trace = backend.Trace([.01], track_stencils=False)
                ramp = self.ramp(backend)
                ramp.admit_current(backend.Dual(.25, {0:-1.5}, trace))
                residuals = []
                for second in range(15):
                    ready = ramp.begin_interval(second, 1.)['eligible_merge_veh']
                    ramp.commit_merge(ready)
                    ramp.apply_head_service(backend.Dual(.25, {0:.5}, trace), mode='GREEN', green_sec=5.)
                    ramp.finish_interval(0.)
                    snap = ramp.snapshot()
                    residuals.append(ramp.cumulative_admitted_veh-ramp.cumulative_merge_veh-snap['connector_veh'])
                for residual in residuals:
                    self.assertEqual(backend.primal(residual), 0.)
                    self.assertAlmostEqual(self.gradient(backend, trace, residual), 0.)
                self.assertEqual(backend.primal(ramp.cumulative_merge_veh), .25)
                self.assertAlmostEqual(self.gradient(backend, trace, ramp.cumulative_merge_veh), -1.5)

    def test_zero_interval_admission_retains_tangent(self):
        for backend in self.backends():
            for head in (0., 10.):
                with self.subTest(backend=backend.__name__, head=head):
                    trace = backend.Trace([.01], track_stencils=False)
                    ramp = self.ramp(backend, head)
                    ramp.begin_interval(0., 1.); ramp.commit_merge(0.)
                    ramp.apply_head_service(0., mode='RED', green_sec=0.)
                    ramp.finish_interval(backend.Dual(0., {0:1.}, trace))
                    self.assertAlmostEqual(self.gradient(backend, trace, ramp.snapshot()['connector_veh']), 1.)

    def test_zero_coupled_admission_retains_tangent(self):
        for backend in self.backends():
            for head in (0., 10.):
                with self.subTest(backend=backend.__name__, head=head):
                    trace = backend.Trace([.01], track_stencils=False)
                    ramp = self.ramp(backend, head)
                    ramp.admit_current(backend.Dual(0., {0:1.}, trace))
                    for value in (ramp.snapshot()['connector_veh'], ramp.cumulative_admitted_veh,
                                  ramp.cumulative_requested_veh):
                        self.assertAlmostEqual(self.gradient(backend, trace, value), 1.)

    def test_plain_zero_does_not_create_cohorts(self):
        ramp = self.ramp(ad, 10.)
        ramp.admit_current(0.)
        ramp.begin_interval(0., 1.); ramp.commit_merge(0.)
        ramp.apply_head_service(0., mode='RED', green_sec=0.)
        ramp.finish_interval(0.)
        self.assertEqual((ramp._upstream, ramp._downstream), ([], []))

    def test_state_witness_accepts_only_exact_zero_ramp_cohorts(self):
        from evaluation.controllers.sdmpc_tangent_state import state_error as fast_error
        zero = ad.Dual(0., {0:-2.}, ad.Trace([.01]))
        for compare in (state_error, fast_error):
            with self.subTest(compare=compare.__module__):
                self.assertEqual(compare([(10., 1.)], [(10., 1.), (11., zero)], 'ramp._downstream'), 0.)
                with self.assertRaises(ValueError):
                    compare([], [(10., 1e-15)], 'ramp._upstream')
                self.assertEqual(compare([(10., 1.)], [(11., 1.)], 'ramp._downstream'), 1.)
                with self.assertRaises(ValueError):
                    compare([], [(math.nan, zero)], 'ramp._upstream')
                with self.assertRaises(ValueError):
                    compare([], [(10., -1.)], 'ramp._upstream')
                with self.assertRaises(ValueError):
                    compare([], [(10., zero)], 'ordinary.cohorts')


class AcceptedMergeLedgerTests(unittest.TestCase):
    gradient = staticmethod(RampZeroTransferTests.gradient)
    backends = RampZeroTransferTests.backends
    @staticmethod
    def ledger(backend, stocks):
        from collections import Counter
        source = (ROOT/'evaluation/controllers/control_area_objective.py').read_text(encoding='utf-8')
        nodes = [n for n in ast.parse(source).body
                 if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in ('_nonnegative','ModelAreaLedger','MembershipError')]
        tree = ast.Module(body=[ast.ImportFrom(module='__future__',
            names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
        ns = dict(namespace(), _tangent_float=backend.float_keep, _tangent_min=backend.minimum,
                  _tangent_max=backend.maximum, math=backend.MathProxy(), Counter=Counter)
        exec(compile(ast.fix_missing_locations(Transform().visit(tree)), '<accepted-merge-ledger>', 'exec'), ns)
        ledger = ns['ModelAreaLedger'](stocks, capture_response=True)
        ledger.begin_response_step('freeway', 0., 1.)
        return ledger

    def test_zero_accepted_packet_reaches_freeway_with_both_area_cohorts(self):
        for backend in self.backends():
            with self.subTest(backend=backend.__name__):
                trace = backend.Trace([.01], track_stencils=False)
                flow = backend.Dual(0., {0:2.}, trace)
                ledger = self.ledger(backend, {'ramp:R':{'inside':.4, 'outside':.6},
                                             'freeway:F':{'inside':5.}})
                ledger.transfer('ramp:R', 'merge_pending:R', flow,
                                inside_to_inside=1., outside_to_inside=0.)
                pending = ledger.stocks.get('merge_pending:R', {'inside':0., 'outside':0.})
                self.assertAlmostEqual(self.gradient(backend, trace, pending['inside']), .8)
                self.assertAlmostEqual(self.gradient(backend, trace, pending['outside']), 1.2)
                ledger.transfer('merge_pending:R', 'freeway:F', flow,
                                inside_to_inside=1., outside_to_inside=1., complete_source=True)
                self.assertAlmostEqual(self.gradient(backend, trace, ledger.stocks['freeway:F']['inside']), 2.)
                self.assertAlmostEqual(self.gradient(backend, trace, ledger.entered_veh), 1.2)
                self.assertAlmostEqual(self.gradient(backend, trace, ledger.ttd_veh), 0.)
                for amount in ledger.stocks['merge_pending:R'].values():
                    self.assertAlmostEqual(self.gradient(backend, trace, amount), 0.)
                total = sum(sum(row.values()) for row in ledger.stocks.values())
                self.assertEqual(backend.primal(total), 6.)
                self.assertAlmostEqual(self.gradient(backend, trace, total), 0.)

    def test_complete_packet_rejects_partial_draw(self):
        ledger = self.ledger(ad, {'merge_pending:R':{'inside':1.}})
        with self.assertRaises(ValueError):
            ledger.transfer('merge_pending:R', 'freeway:F', .5,
                            inside_to_inside=1., outside_to_inside=1., complete_source=True)

    def test_plain_zero_keeps_no_event(self):
        ledger = self.ledger(ad, {})
        ledger.transfer('merge_pending:R', 'freeway:F', 0.,
                        inside_to_inside=1., outside_to_inside=1., complete_source=True)
        self.assertEqual(ledger.stocks, {})
        self.assertEqual(ledger.event_count, 0)


if __name__ == '__main__':
    unittest.main()


class AcceptedMergeReceivingTests(unittest.TestCase):
    gradient = staticmethod(RampZeroTransferTests.gradient)
    backends = RampZeroTransferTests.backends

    @staticmethod
    def receiving(backend):
        source = (ROOT/'evaluation/controllers/area_freeway_accounting.py').read_text(encoding='utf-8')
        fn = next(n for n in ast.parse(source).body
                  if isinstance(n, ast.FunctionDef) and n.name == '_freeway_substep_events')
        assignments = [n for n in ast.walk(fn) if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'receiving_for_mainline' for t in n.targets)]
        if len(assignments) != 1:
            raise AssertionError('Expected the unique canonical receiving allocation')
        module = ast.parse('def receive(receiving, ramp_in_by_link, link, rho_for_flow):\n    pass')
        module.body[0].body = [assignments[0], ast.Return(value=ast.Name(id='receiving_for_mainline',ctx=ast.Load()))]
        ns = dict(namespace(), _tangent_float=backend.float_keep,
                  _tangent_min=backend.minimum, _tangent_max=backend.maximum,
                  _tangent_math=backend.MathProxy())
        exec(compile(ast.fix_missing_locations(Transform().visit(module)), '<canonical-receiving>', 'exec'), ns)
        return ns['receive']

    def test_accepted_merge_and_remaining_supply_share_one_budget(self):
        for backend in self.backends():
            for accepted in (0., 1.):
                with self.subTest(backend=backend.__name__,accepted=accepted):
                    trace = backend.Trace([.01],track_stencils=False)
                    supply = backend.Dual(10.,{0:1.},trace)
                    merge = backend.Dual(accepted,{0:3.},trace)
                    mainline = self.receiving(backend)([supply],{'road':[merge]},'road',[0.])[0]
                    self.assertEqual(backend.primal(mainline+merge),10.)
                    self.assertAlmostEqual(self.gradient(backend,trace,mainline),-2.)
                    self.assertAlmostEqual(self.gradient(backend,trace,mainline+merge),1.)

    def test_exhausted_receiving_budget_keeps_nonnegative_mainline_supply(self):
        for backend in self.backends():
            trace = backend.Trace([.01],track_stencils=False)
            merge = backend.Dual(2.,{0:3.},trace)
            mainline = self.receiving(backend)([1.],{'road':[merge]},'road',[0.])[0]
            self.assertEqual(backend.primal(mainline),0.)
            self.assertEqual(self.gradient(backend,trace,mainline),0.)


class ZeroMergeSpeedTests(unittest.TestCase):
    gradient = staticmethod(RampZeroTransferTests.gradient)
    backends = RampZeroTransferTests.backends

    @staticmethod
    def speed(backend):
        from types import SimpleNamespace
        from evaluation.controllers.physical_ramp_boundary import _has_transfer
        source = (ROOT/'evaluation/controllers/area_freeway_accounting.py').read_text(encoding='utf-8')
        fn = next(n for n in ast.parse(source).body
                  if isinstance(n, ast.FunctionDef) and n.name == '_freeway_substep_events')
        blocks = [n for n in ast.walk(fn) if isinstance(n, ast.If)
                  and ast.unparse(n.test).startswith('delta_i > 0.0')]
        if len(blocks) != 1:
            raise AssertionError('Expected the canonical linear merge deceleration')
        module = ast.parse('def apply(flow, delta_i):\n    pass')
        setup = ast.parse("v_new=70.; i=0; link='road'; dt_h=1./3600.; speeds=[60.]; lengths=[.5]; lanes_now=[3.]; rho=40.; direction_params={}; ramp_in_by_link={'road':[flow]}").body
        module.body[0].body = setup+[blocks[0],ast.Return(value=ast.Name(id='v_new',ctx=ast.Load()))]
        ns = dict(namespace(), _tangent_float=backend.float_keep,
                  _tangent_min=backend.minimum, _tangent_max=backend.maximum,
                  _tangent_math=backend.MathProxy(), _has_transfer=_has_transfer,
                  net=SimpleNamespace(v_min=1.,metanet_kappa_veh_km_lane=20.))
        exec(compile(ast.fix_missing_locations(Transform().visit(module)), '<canonical-merge-speed>', 'exec'), ns)
        return ns['apply']

    def test_zero_merge_keeps_linear_deceleration_sensitivity(self):
        for backend in self.backends():
            for flow in (0.,500.):
                with self.subTest(backend=backend.__name__,flow=flow):
                    trace=backend.Trace([.01],track_stencils=False)
                    x=backend.Dual(flow,{0:1.},trace)
                    expected=-2.*(1./3600.)*60./(.5*3.*60.)
                    got=self.speed(backend)(x,2.)
                    self.assertAlmostEqual(backend.primal(got),70.+expected*flow)
                    self.assertAlmostEqual(self.gradient(backend,trace,got),expected)
                    self.assertEqual(self.speed(backend)(0.,2.),70.)
                    self.assertEqual(self.speed(backend)(x,0.),70.)
