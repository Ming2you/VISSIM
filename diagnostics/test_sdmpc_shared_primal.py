from pathlib import Path
import copy
import hashlib
import math
import pickle
import sys
import tempfile
import unittest
from collections import deque
from fractions import Fraction
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_state import state_error as fast
from evaluation.controllers.sdmpc_tangent_worker import state_error as legacy, expand_shared_request
from evaluation.controllers.sdmpc_dual import Dual, Trace


class SharedPrimalTests(unittest.TestCase):
    def test_nested_stock_and_aliases_keep_maximum_error(self):
        x = {'q': [Dual(3., {0: 1.}, Trace([.01]))], 'clock': np.arange(12).reshape(3, 4)}
        y = {'q': [3.001], 'clock': np.arange(12).reshape(3, 4)}
        a, b = [x, x, {'cohort': deque([Fraction(1, 3)])}], [y, y, {'cohort': deque([Fraction(1, 3)])}]
        self.assertEqual(fast(a, b), legacy(a, b))
        self.assertEqual(fast(Fraction(1, 2), Fraction(1, 3)), legacy(Fraction(1, 2), Fraction(1, 3)))
        with self.assertRaises(ValueError):
            fast(a, b+[{}])
        b[0]['clock'][2, 2] = 77
        self.assertEqual(fast(a, b), 67.)
        with self.assertRaises(ValueError):
            fast({'stock': 1.}, {'other': 1.})

    def test_numeric_arrays_and_nonfinite_failures(self):
        a = np.array([0., 2., math.inf, -math.inf])
        b = np.array([0., 2.5, math.inf, -math.inf])
        self.assertEqual(fast(a, b), legacy(a, b))
        for x, y in [(math.nan, math.nan), (math.inf, 1.),
                     (np.array([math.nan]), np.array([math.nan])),
                     (np.array([math.inf]), np.array([-math.inf]))]:
            with self.subTest(x=x), self.assertRaises(ValueError):
                fast(x, y)
        with self.assertRaises(ValueError):
            fast(np.zeros((2, 3)), np.zeros((3, 2)))

    def test_ledger_modes_and_packed_history_keep_all_transfers(self):
        row = dict(stage='urban', start_sec=1., end_sec=2., source='q', target=None,
                   route_key='sink:q', vehicles=.2, ttd_veh=.2, entered_veh=0.)
        rows = [row, dict(row)]
        combined = [dict(row, vehicles=.4, ttd_veh=.4)]
        a = {'transfers': rows, '_packed_response_records': [pickle.dumps({'transfers': rows})]}
        b = {'transfers': combined, '_packed_response_records': [pickle.dumps({'transfers': combined})]}
        self.assertEqual(fast(a, b), legacy(a, b))
        combined[0]['vehicles'] += .1
        self.assertEqual(fast(a, b), legacy(a, b))
        with self.assertRaises(ValueError):
            fast({'transfers': rows, 'ordinary': rows}, {'transfers': combined, 'ordinary': combined})
        with self.assertRaises(ValueError):
            fast([dict(row, unknown=3)], [], 'ledger.transfers')
        self.assertEqual(fast([row], [], 'ledger.transfers'), .2)

    def test_runtime_objects_code_identity_and_slots(self):
        class Slot:
            __slots__ = ('q',)
        a, b = Slot(), Slot()
        a.q, b.q = 1., 2.
        self.assertEqual(fast(a, b), legacy(a, b))
        self.assertEqual(fast({'code': math}, {'code': math}), 0.)
        with self.assertRaises(ValueError):
            fast({'code': math}, {'code': sys})
        Ledger = type('ModelAreaLedger', (), {})
        a, b = Ledger(), Ledger()
        a._response = b._response = {'transfers': []}
        a.event_count, b.event_count = 1, 2
        with self.assertRaises(ValueError):
            fast(a, b)

    def test_shared_request_binding_and_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'request.pickle'
            data = pickle.dumps({'owned': ['anchor'], 'action': {'green': 3}}, protocol=5)
            path.write_bytes(data)
            desc = dict(path=str(path), sha256=hashlib.sha256(data).hexdigest())
            envelope = dict(shared_request=desc, scalar_output=str(Path(tmp)/'scalar.pickle'))
            got = expand_shared_request(envelope)
            self.assertEqual(got['action'], {'green': 3})
            self.assertEqual(got['shared_anchor_sha256'], desc['sha256'])
            with self.assertRaises(ValueError):
                expand_shared_request(dict(envelope, action={'green': 8}))
            with self.assertRaises(ValueError):
                expand_shared_request(dict(envelope, shared_primal={}))
            path.write_bytes(data+b'changed')
            with self.assertRaises(ValueError):
                expand_shared_request(envelope)

    def test_option_requires_explicit_tangent_mode(self):
        from evaluation.controllers import sdmpc
        cfg = pickle.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').read_bytes())['owned'][0].cfg
        base = {'adapter': {'sdmpc': 'proxlinear-v1', 'sdmpc_derivatives': 'tangent-v1'}}
        self.assertNotIn('tangent_shared_primal', sdmpc.configure(base, copy.deepcopy(cfg)))
        self.assertNotIn('indexed_coverage', sdmpc.configure(base, copy.deepcopy(cfg)))
        for value in (True, False):
            tuning = copy.deepcopy(base)
            tuning['adapter']['sdmpc_indexed_coverage'] = value
            self.assertIs(sdmpc.configure(tuning, copy.deepcopy(cfg))['indexed_coverage'], value)
        with self.assertRaises(ValueError):
            sdmpc.configure({'adapter': dict(base['adapter'], sdmpc_indexed_coverage=1)}, copy.deepcopy(cfg))
        for value in (True, False):
            tuning = copy.deepcopy(base)
            tuning['adapter']['sdmpc_tangent_shared_primal'] = value
            self.assertIs(sdmpc.configure(tuning, copy.deepcopy(cfg))['tangent_shared_primal'], value)
        for value in (1, 'yes'):
            tuning['adapter']['sdmpc_tangent_shared_primal'] = value
            with self.assertRaises(ValueError):
                sdmpc.configure(tuning, copy.deepcopy(cfg))
        with self.assertRaises(ValueError):
            sdmpc.configure({'adapter': {'sdmpc': 'proxlinear-v1', 'sdmpc_tangent_shared_primal': True}}, cfg)


if __name__ == '__main__':
    unittest.main()
