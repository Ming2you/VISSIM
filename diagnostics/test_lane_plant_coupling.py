"""Mass, timing and receiver contracts for the opt-in coupled lane runtime."""
import copy
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
