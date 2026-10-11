"""K9-1-0b Z1 tests (K8_PREDECLARATION_AMENDMENT_19 r2 sections 2.4 and 4.1 K9-1-0b): the latent key touch of the
LOR direct row (Z1-a, no key).  Synthetic direct-row toy only (no capture, rollout, adapter run or VISSIM), run in a
fresh tangent-instrumented subprocess (tests/k9_latent_parity_probe.py), forward and reverse-v1:

  - 1-ulp parity: the scalar witness with the W_out room at its structural 0.0 (n = 0.0) against the tangent run with
    a Dual room +-2**-51: the release-buffer keys after the drain equal, no key divergence anywhere in the whole
    state (sdmpc_tangent_worker.state_error raises on a key mismatch) and the state error <= 1e-9; with and without
    the W_out exit law (without it the target is routed, so the arrival buffer is touched too);
  - the F-2 form: the keys the touch books at room 0.0 are the keys the n > 0 branch books (due = step + the
    direct-class residence, or uqm._link_delay_steps without the law), with value 0.0 (the +0.0 is omitted).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k9_latent.py -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROBE = HERE / 'k9_latent_parity_probe.py'
NUMBA_DEPS = Path(os.environ.get('K8G_DEPS', r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'))


def probe(backend, scenario):
    env = dict(os.environ, PYTHONHASHSEED='0', NUMBA_NUM_THREADS='1', OMP_NUM_THREADS='1')
    if backend == 'reverse-v1':
        env['PYTHONPATH'] = os.pathsep.join([str(NUMBA_DEPS / 'sdmpc'), str(NUMBA_DEPS / 'sdmpc-numba'),
                                             env.get('PYTHONPATH', '')])
    done = subprocess.run([sys.executable, '-B', str(PROBE), backend, scenario], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=900)
    if done.returncode != 0:
        raise AssertionError(done.stdout[-4000:] + done.stderr[-4000:])
    return json.loads(done.stdout.strip().splitlines()[-1])


class LatentTouchParityTests(unittest.TestCase):
    def check(self, backend, scenario, touched_scalar=1):
        out = probe(backend, scenario)
        self.assertIsNone(out['after_drain']['exception'], out)
        self.assertIsNone(out['full_state']['exception'], out)
        self.assertTrue(out['key_divergence_0'], out)
        self.assertTrue(out['parity'], out)
        self.assertEqual(out['keys_after_drain'][0], out['keys_after_drain'][1])
        self.assertEqual(out['touch_events'][0], touched_scalar)          # the scalar witness took the touch
        rel = out['keys_after_drain'][0]['release'].get('SC1001_W_out')
        self.assertTrue(rel, out)                                         # the release key exists (Z1)
        if 'nolaw' in scenario:
            self.assertEqual(out['keys_after_drain'][0]['arrival'].get('SC1001_W_out'), rel)
        return out

    def test_law_plus_forward(self):
        self.check('forward', 'law_plus')

    def test_law_minus_forward(self):
        self.check('forward', 'law_minus')

    def test_law_plus_reverse_v1(self):
        self.check('reverse-v1', 'law_plus')

    def test_law_minus_reverse_v1(self):
        self.check('reverse-v1', 'law_minus')

    def test_nolaw_plus_forward(self):
        self.check('forward', 'nolaw_plus')

    def test_nolaw_minus_reverse_v1(self):
        self.check('reverse-v1', 'nolaw_minus')


class LatentTouchFormTests(unittest.TestCase):
    def check(self, scenario):
        out = probe('forward', scenario)
        self.assertEqual(out['touch_events'], [1, 0], out)                # touch at 0.0; the branch at n > 0
        self.assertTrue(out['same_keys'], out)
        self.assertTrue(out['touch_values_zero'], out)
        return out

    def test_due_with_exit_law(self):
        self.check('due_law')

    def test_due_without_exit_law(self):
        out = self.check('due_nolaw')
        self.assertTrue(out['keys_touch']['arrival'].get('SC1001_W_out'))


if __name__ == '__main__':
    unittest.main()
