"""Post-run recorded transfer grouping, without a model or COM invocation."""
import math
import pickle
import unittest

from diagnostics.control_improvement.decision_common_anchor_20260911.ramp8_physical_v1.invoke import ttd_by_windows


class RecordedTtdWindowsTests(unittest.TestCase):
    def test_boundary_ownership_and_legacy_first_window_are_exact(self):
        rows = [dict(start_sec=start, end_sec=end, route_key=key, ttd_veh=count)
                for start, end, key, count in (
                    (900., 910., 'exit:a', .1), (1040., 1050., 'exit:b', 2.),
                    (1050., 1050., 'exit:a', .2), (1050., 1060., 'exit:a', 3.),
                    (1190., 1200., 'exit:b', 4.), (1200., 1210., 'exit:c', 5.),
                    (1340., 1350., 'exit:c', 6.), (1340., 1350., 'internal', 0.))]
        before = pickle.dumps(rows, protocol=5)
        legacy = {}
        for row in rows:
            if row['end_sec'] <= 1050. and row['ttd_veh']:
                key = str(row['route_key'])
                legacy[key] = legacy.get(key, 0.) + row['ttd_veh']
        total, windows = ttd_by_windows(rows)
        self.assertEqual(pickle.dumps(windows[0]['by_route']), pickle.dumps(legacy))
        self.assertEqual(windows[1]['by_route'], {'exit:a': 3., 'exit:b': 4.})
        self.assertEqual(windows[2]['by_route'], {'exit:c': 11.})
        self.assertEqual(list(total), ['exit:a', 'exit:b', 'exit:c'])
        self.assertAlmostEqual(math.fsum(total.values()), math.fsum(r['ttd_veh'] for r in rows))
        self.assertEqual(before, pickle.dumps(rows, protocol=5))

    def test_invalid_or_ambiguous_event_is_rejected(self):
        for start, end, count in ((899., 910., 1.), (1045., 1055., 1.),
                                  (1345., 1355., 1.), (910., 900., 1.),
                                  (900., float('nan'), 1.), (float('inf'), 910., 1.),
                                  (900., 910., -1.), (900., 910., float('inf')),
                                  (900., 910., True)):
            with self.subTest(start=start, end=end, count=count):
                with self.assertRaises(ValueError):
                    ttd_by_windows([dict(start_sec=start, end_sec=end, route_key='exit', ttd_veh=count)])

    def test_no_exits_is_an_empty_three_window_summary(self):
        total, windows = ttd_by_windows([])
        self.assertEqual(total, {})
        self.assertEqual([w['by_route'] for w in windows], [{}, {}, {}])


if __name__ == '__main__':
    unittest.main()
