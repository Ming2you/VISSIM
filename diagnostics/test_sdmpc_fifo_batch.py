"""Exact FIFO/active-branch derivative checks for indexed lateral departures."""
from pathlib import Path
import ast
import copy
import inspect
import math
import random
import sys
import unittest
from collections import deque, defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import physical_urban_transport as transport
from evaluation.controllers import sdmpc_dual as ad
from evaluation.controllers.sdmpc_tangent_runtime import Transform, namespace


def classes():
    source = '\n'.join(inspect.getsource(c) for c in
                       (transport.FIFO, transport.IndexedLateralDepartures))
    ns = dict(namespace(), deque=deque, defaultdict=defaultdict, EPS=transport.EPS, math=ad.MathProxy(),
              prediction_cache=transport.prediction_cache)
    exec(compile(ast.fix_missing_locations(Transform().visit(ast.parse(source))),
                 '<indexed-fifo-test>', 'exec'), ns)
    return ns['FIFO'], ns['IndexedLateralDepartures']


class IndexedFIFOTests(unittest.TestCase):
    def compare(self, packets, requests):
        FIFO, Indexed = classes()
        old, new = FIFO(), FIFO()
        old.q = deque([label,n] for label,n in packets)
        new.q = deque([label,n] for label,n in packets)
        indexed = Indexed(new)
        for label, amount in requests:
            self.assertEqual(old.take_label(label, amount), indexed.take_label(label, amount))
            indexed.commit()
            self.assertEqual([x[0] for x in old.q], [x[0] for x in new.q])
            for (_, x), (_, y) in zip(old.q, new.q):
                self.assertEqual(ad.primal(x), ad.primal(y))
                self.assertEqual(ad.derivative(x), ad.derivative(y))

    def test_interleaved_destinations_repeated_departures(self):
        rng = random.Random(17)
        for dual in (False, True):
            trace = ad.Trace([.1]*4, track_stencils=False)
            packets = [(i%4, ad.Dual(.5+rng.random(), {i%4:1.}, trace) if dual
                        else .5+rng.random()) for i in range(200)]
            requests = [(i%4, ad.Dual(.13, {(i+1)%4:.3}, trace) if dual else .13)
                        for i in range(300)]
            self.compare(packets, requests)

    def test_exact_exhaustion_retains_derivative_on_next_fragment(self):
        trace = ad.Trace([.1]*2, track_stencils=False)
        self.compare([(0, ad.Dual(1., {0:1.}, trace)), (1,2.), (0,3.)],
                     [(0,ad.Dual(1., {1:1.}, trace)), (0,.2)])

    def test_guard_uses_same_order_and_rejects_next_ulp(self):
        FIFO, Indexed = classes()
        q=FIFO([(i%2,.1) for i in range(20)])
        amount=0.
        for label,n in q.q:
            if label==0: amount+=n
        with self.assertRaises(ArithmeticError):
            Indexed(q).take_label(0,math.nextafter(amount+1e-7,math.inf))

    def test_sub_epsilon_tail_and_multiple_targets(self):
        self.compare([(0,1.),(1,1.),(0,2.),(2,.5),(0,4.)],
                     [(0,1.-transport.EPS/2),(1,.4),(0,2.2),(1,.6),(0,.2)])


if __name__ == '__main__':
    unittest.main()
