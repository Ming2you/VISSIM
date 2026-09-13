"""Small synthetic horizon checks; no FZP scan or figure rendering."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


SOURCE = Path(__file__).resolve().parents[1] / 'reports/20260911_fd_mfd_fw070_urban050/build_figures.py'
SPEC = importlib.util.spec_from_file_location('fd_figure_horizon', SOURCE)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class FigureHorizon(unittest.TestCase):
    def test_trapezoids_cover_all_windows_with_unchanged_5400_values(self):
        for end in (5400, 7200, 9000):
            for width in (30, 60, 150):
                with self.subTest(end=end, width=width):
                    t = np.arange(end + 1, dtype=float)
                    values = np.column_stack([t, t * 2])
                    actual = m.mean_windows(values, width)
                    expected = (np.arange(end // width) + .5) * width
                    np.testing.assert_array_equal(actual[:, 0], expected)
                    np.testing.assert_array_equal(actual[:, 1], expected * 2)
                    if end == 5400:
                        legacy = ((values[:-1] + values[1:]) * .5).reshape(5400 // width, width, 2).mean(axis=1)
                        np.testing.assert_array_equal(actual, legacy)

    def test_incomplete_or_invalid_windows_fail(self):
        for count, width in ((9000, 150), (1, 150), (9001, 0), (9001, -1), (9001, 30.0), (9001, True)):
            with self.subTest(count=count, width=width), self.assertRaises(ValueError):
                m.mean_windows(np.zeros((count, 2)), width)

    def test_receipt_horizon_requires_completed_closed_native_run(self):
        base = dict(completed=True, exit_code=0, owned_native_alive=False, seed=13, terminal_sec=5400)
        for end in (5400, 7200, 9000, 9000.0):
            with self.subTest(end=end):
                self.assertEqual(m.run_horizon({**base, 'terminal_sec': end}), int(end))
        for key, value in (('terminal_sec', 6000), ('terminal_sec', '9000'), ('terminal_sec', float('nan')),
                           ('completed', False), ('exit_code', False), ('exit_code', 1),
                           ('owned_native_alive', True), ('seed', 14)):
            with self.subTest(key=key, value=value), self.assertRaises(AssertionError):
                m.run_horizon({**base, key: value})


if __name__ == '__main__':
    unittest.main()
