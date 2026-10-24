"""Mass, timing and receiver contracts for the opt-in coupled lane runtime."""
import copy
import math
import unittest
from collections import Counter
from evaluation.controllers.physical_urban_transport import FIFO, UrbanTransport

from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary, LaneResolvedRampBoundary


class LocalUrbanRoundoffTests(unittest.TestCase):
    def test_real_candidate_shared_queue_receipts_are_debited_together(self):
        from evaluation.controllers.lane_urban_runtime import _debit_stock,_debit_movement_transfers
        # Actual state900 candidate132, step927: three lanes share one queue.
        stock=.07671221302989878
        receipts=(.035884276453469935,.035884276453469935,.004943660122958958)
        remaining=stock
        with self.assertRaises(ArithmeticError):
            for n in receipts:remaining=_debit_stock(remaining,n)
        keys={str(i):'movement:m' for i in range(3)}
        transfers=[(('external',str(i)),(71,1,0),(((10634,None),n),)) for i,n in enumerate(receipts)]
        for rows in (transfers,list(reversed(transfers))):
            queues={'m':stock,'untouched':2.}
            _debit_movement_transfers(queues,rows,keys)
            self.assertEqual(queues,{'m':0.,'untouched':2.})

    def test_grouped_real_overdraw_is_rejected_without_partial_debit(self):
        from evaluation.controllers.lane_urban_runtime import _debit_movement_transfers
        queues={'a':1.,'b':.1}
        keys={'a':'movement:a','b1':'movement:b','b2':'movement:b'}
        transfers=[(('external',name),(71,1,0),(((10634,None),n),))
                   for name,n in (('a',.5),('b1',.05),('b2',.050001))]
        with self.assertRaises(ArithmeticError):_debit_movement_transfers(queues,transfers,keys)
        self.assertEqual(queues,{'a':1.,'b':.1})

    def test_subtraction_roundoff_is_not_negative_stock(self):
        from evaluation.controllers.lane_urban_runtime import _debit_stock
        self.assertEqual(_debit_stock(.1, .10000000000000002),0.)
        self.assertAlmostEqual(_debit_stock(.4,.1),.3)

    def test_real_overdraw_stays_an_error(self):
        from evaluation.controllers.lane_urban_runtime import _debit_stock
        for stock,amount in ((.1,.100001),(0.,.000001),(-.1,0.),(1.,float('nan'))):
            with self.subTest(stock=stock,amount=amount),self.assertRaises(ArithmeticError):
                _debit_stock(stock,amount)


class LaneRampMirrorRoundoffTests(unittest.TestCase):
    """LaneRampRuntime.advance's mirror debit (decision 7650 of sdmpc31_v3b_s31d)."""
    # RM_C10681 at t=7678: the mirror held 1 ULP less than the buffer's fsum and
    # the merge emptied the buffer exactly.
    STOCK, MERGED = 0.0978995213945203, 0.09789952139452118

    @staticmethod
    def instrumented(backend):
        """_debit_mirror compiled exactly as the tangent worker's Finder does."""
        import ast, inspect
        from evaluation.controllers import lane_ramp_runtime, sdmpc_tangent_runtime as rt
        from evaluation.controllers import sdmpc_dual, sdmpc_tangent_reverse
        ad = sdmpc_tangent_reverse if backend == 'reverse' else sdmpc_dual
        ns = dict(_tangent_float=ad.float_keep, _tangent_min=ad.minimum, _tangent_max=ad.maximum,
                  _tangent_math=ad.MathProxy(), _tangent_numpy=ad.NumpyProxy(),
                  _tangent_isinstance=rt.numeric_isinstance, _tangent_type=rt.numeric_type,
                  __name__='lane_ramp_runtime_instrumented')
        tree = rt.Transform().visit(ast.parse(inspect.getsource(lane_ramp_runtime)))
        exec(compile(ast.fix_missing_locations(tree), lane_ramp_runtime.__file__, 'exec'), ns)
        trace = (lambda: ad.Trace([.01, .01])) if backend == 'reverse' else (
            lambda: ad.Trace([.01, .01], track_stencils=False))
        return ad, trace, ns['_debit_mirror']

    def test_real_7650_roundoff_is_exact_zero(self):
        from evaluation.controllers.lane_ramp_runtime import _debit_mirror
        self.assertEqual(self.STOCK-self.MERGED, -8.881784197001252e-16)  # the former mirror value
        result = _debit_mirror(self.STOCK, self.MERGED)
        self.assertIs(type(result), float)
        self.assertEqual(result.hex(), (0.).hex())

    def test_nonnegative_or_nan_difference_is_the_former_subtraction(self):
        from evaluation.controllers.lane_ramp_runtime import _debit_mirror
        for stock, merged in ((self.STOCK, self.STOCK), (.3, .1), (7.695754694296717, .29650668141107556),
                              (4.440892098500626e-16, 0.), (0., 0.), (8., 1e-300), (5e-324, 0.), (.1, .1)):
            with self.subTest(stock=stock, merged=merged):
                self.assertEqual(_debit_mirror(stock, merged).hex(), (stock-merged).hex())
        self.assertTrue(math.isnan(_debit_mirror(float('nan'), 0.)))

    def test_only_drift_within_the_mirror_tolerance_is_zeroed(self):
        from evaluation.controllers import lane_ramp_runtime as runtime
        self.assertEqual(runtime.MIRROR_TOLERANCE_VEH, 1e-7)
        for stock, merged in ((0., 1e-7), (.3, .3+5e-8), (.25, .25+1e-9), (self.STOCK, self.MERGED)):
            with self.subTest(stock=stock, merged=merged):
                self.assertLess(stock-merged, 0.)
                self.assertEqual(runtime._debit_mirror(stock, merged).hex(), (0.).hex())
        # Beyond the tolerance the former negative mirror is kept for assert_mirror.
        for stock, merged in ((0., 1.5e-7), (.1, .100001), (0., 1e-6), (-1e-3, 0.)):
            with self.subTest(stock=stock, merged=merged):
                self.assertEqual(runtime._debit_mirror(stock, merged).hex(), (stock-merged).hex())

    def test_closing_assert_mirror_accepts_every_zeroed_and_rejects_every_kept_negative(self):
        from types import SimpleNamespace
        from evaluation.controllers.lane_ramp_runtime import LaneRampRuntime, _debit_mirror
        def passes(mirror, connector):
            buffer = SimpleNamespace(snapshot=lambda: {'connector_veh': connector,
                                                       'outside_component_backlog_veh': 0.})
            try:
                LaneRampRuntime.assert_mirror(SimpleNamespace(buffers={'R': buffer}),
                                              SimpleNamespace(ramp_queue={'R': mirror}))
            except ArithmeticError:
                return False
            return True
        # The buffer is a nonnegative fsum of cohorts; the mirror drifts from it.
        for drift in (0., 8.9e-16, 1e-9, 5e-8, 1e-7, 1.0000001e-7, 1.5e-7, 1e-6, 1e-3):
            stock, merged = .25, .25+drift
            former, new = stock-merged, _debit_mirror(stock, merged)
            for connector in (0., 1e-12, 3e-8, 1e-7, 2e-7):
                with self.subTest(drift=drift, connector=connector):
                    if passes(former, connector):
                        self.assertTrue(passes(new, connector))
                    if new < 0.:
                        self.assertFalse(passes(new, connector))

    def test_taped_debit_outside_the_window_leaves_the_tape_unchanged(self):
        for backend in ('forward', 'reverse'):
            ad, new_trace, debit = self.instrumented(backend)
            for stock, merged in ((.5, .2), (.3, .3), (self.STOCK, self.STOCK), (.1, .100001)):
                with self.subTest(backend=backend, stock=stock, merged=merged):
                    old_t = new_trace()
                    old = ad.Dual(stock, {0: 1.}, old_t)-ad.Dual(merged, {1: 1.}, old_t)
                    t = new_trace()
                    new = debit(ad.Dual(stock, {0: 1.}, t), ad.Dual(merged, {1: 1.}, t))
                    self.assertIs(type(new), type(old))  # an exact 0 keeps its Dual
                    self.assertEqual(ad.primal(new), ad.primal(old))
                    self.assertEqual(dict(t.counts), dict(old_t.counts))  # no comparison event
                    if backend == 'reverse':
                        self.assertEqual((new.node, list(t.p1), list(t.p2), list(t.w1), list(t.w2)),
                                         (old.node, list(old_t.p1), list(old_t.p2), list(old_t.w1), list(old_t.w2)))
                    else:
                        self.assertEqual((new.tangent, t.operations), (old.tangent, old_t.operations))
            probe = new_trace()
            _ = ad.Dual(.5, {0: 1.}, probe) < 0.  # the counter does see a Dual comparison
            self.assertEqual(probe.counts['primal_comparisons'], 1)

    def test_taped_negative_roundoff_is_exact_zero(self):
        for backend in ('forward', 'reverse'):
            ad, new_trace, debit = self.instrumented(backend)
            with self.subTest(backend=backend):
                t = new_trace()
                stock, merged = ad.Dual(self.STOCK, {0: 1.}, t), ad.Dual(self.MERGED, {0: 1., 1: .5}, t)
                self.assertEqual(ad.primal(stock-merged), -8.881784197001252e-16)
                result = debit(stock, merged)
                self.assertIs(type(result), float)
                self.assertEqual(result.hex(), (0.).hex())


def ramp(lanes=1):
    args = dict(connector_id='test', length_m=120., head_position_m=90.,
                lanes=lanes, spacing_m=6., travel_speed_kmh=36., time_sec=0.,
                initial_cohorts=[[120., 20., 1], [90., 0., 1]])
    if lanes == 1:
        return PhysicalRampBoundary(**args)
    return LaneResolvedRampBoundary(**args, lane_arrival_shares=[.25, .75])


def advance(model, arrivals):
    return model.advance_local_interval(start_sec=model.time_sec, duration_sec=1.,
        cycle_sec=10., receiving_budget_veh=.4, service_veh=4., mode='GREEN',
        green_sec=8., request_arrivals_veh=arrivals, allow_partial_cycle=True)


class CoupledAdmissionTests(unittest.TestCase):
    def test_delayed_commit_matches_existing_one_second_dynamics(self):
        for lanes in (1, 2):
            a, b = ramp(lanes), ramp(lanes)
            for second in range(50):
                n = min(.2, a.current_admission_space(), b.current_admission_space())
                expected, actual = advance(a, n), advance(b, 0.)
                b.admit_current(n)
                self.assertEqual(expected['accepted_merge_veh'], actual['accepted_merge_veh'])
                for key, value in a.snapshot().items():
                    if isinstance(value, (float, int)):
                        self.assertAlmostEqual(value, b.snapshot()[key], places=10)
                    else:
                        self.assertEqual(value, b.snapshot()[key])
            self.assertEqual(a.time_sec, 50.)

    def test_rejected_arrival_does_not_create_backlog_or_mutate(self):
        for lanes in (1, 2):
            model = ramp(lanes)
            before = copy.deepcopy(model.snapshot())
            with self.assertRaisesRegex(ValueError, 'exceed'):
                model.admit_current(model.current_admission_space()+1.)
            self.assertEqual(before, model.snapshot())


class UrbanReceivingTests(unittest.TestCase):
    @staticmethod
    def toy(queues, green=True):
        class Signal:
            def state_at(self, *args, **kwargs):
                return 'GREEN' if green else 'RED'
        p = UrbanTransport.__new__(UrbanTransport)
        p.program, p.offset, p.time = Signal(), 0, 0
        p.speed, p.spacing, p.wave = 10., 6., 3.
        p.lateral_access = True
        p.continuation, p.exchange_rates = False, {}
        p.compact_equal_behavior = True
        p.unrouted_labels, p.fallback_exits = set(), {10634,10635,10642}
        p.capacity_rate = 10*3/(6*13)
        p.exits = {10634: {'lanes': [1,2,3], 'position_m': 96},
                   10635: {'lanes': [4,5], 'position_m': 95},
                   10642: {'lanes': [1], 'position_m': 48}}
        p.edges = {71: [0., 24.]}
        p.cells = {(71,lane,0): FIFO(rows) for lane, rows in queues.items()}
        p.cap = {key: 4. for key in p.cells}
        p.dx = {key: 24. for key in p.cells}
        p.initial = p.counts()
        p.admitted, p.departed = Counter(), Counter()
        p.movements, p.blocked_seconds = Counter(), Counter()
        p.vehicle_seconds, p.checks = 0., 0
        return p

    @staticmethod
    def urban():
        return UrbanReceivingTests.toy({1: [((10634, 1), 2.)], 2: [((None, 2), 2.)]})

    def test_closed_receiver_retains_all_stock_and_waiting_cost(self):
        p = self.urban()
        for _ in range(20):
            p.step({}, exit_receiving={10634:0.,10635:0.,10642:0.})
        self.assertAlmostEqual(sum(p.counts().values()), 4.)
        self.assertEqual(sum(p.departed.values()), 0.)
        self.assertAlmostEqual(p.vehicle_seconds, 80.)

    def test_shared_exit_budget_is_spent_once_with_unknown_identity_retained(self):
        p = self.urban()
        p.step({}, exit_receiving={10634:.1,10635:0.,10642:0.})
        self.assertAlmostEqual(sum(p.departed.values()), .1)
        self.assertGreater(p.departed[None, 2], 0.)
        self.assertTrue(all(target == ('exit',10634) for source,target,rows in p.last_transfers))
        self.assertAlmostEqual(sum(p.counts().values()) + sum(p.departed.values()), 4.)

    def test_explicit_unbounded_receiver_matches_original_transition(self):
        a, b = self.urban(), self.urban()
        for _ in range(20):
            a.step({})
            b.step({}, exit_receiving={10634:100.,10635:100.,10642:100.})
            self.assertEqual(a.counts(), b.counts())
            self.assertEqual(a.departed, b.departed)
            self.assertEqual(a.vehicle_seconds, b.vehicle_seconds)


if __name__ == '__main__':
    unittest.main()
