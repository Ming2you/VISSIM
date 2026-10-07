"""K8b-1 P-1 tests (K8_PREDECLARATION_AMENDMENT_16 r2 section 2.1; synthetic cfg objects only, no capture, rollout,
adapter run or VISSIM): runtime_setup.install_sc1002w_saturation and make_config_n31.apply_k8b (p1 part).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k8b_p1.py -v
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', HERE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from evaluation.controllers import runtime_setup as RS  # noqa: E402

EVIDENCE = 'diagnostics/sdmpc_n31_20260924/k8b/sc1002w_saturation_v3c3_20261007.json'
E, S, N = 'SC1002_W_SC1001_to_E_SC101', 'SC1002_W_SC1001_to_S_SC105', 'SC1002_W_SC1001_to_N_SC2004'


def make_config():
    path = ROOT / 'diagnostics/sdmpc_n31_20260924/make_config_n31.py'
    spec = importlib.util.spec_from_file_location('k8b_test_make_config_n31', path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


def pin():
    import hashlib
    return {'evidence': EVIDENCE, 'evidence_sha256': hashlib.sha256((ROOT / EVIDENCE).read_bytes()).hexdigest()}


def cfg(beta_e=0.1624, beta_s=0.6957, beta_n=0.142):
    movements = {E: {'beta': beta_e}, S: {'beta': beta_s}, N: {'beta': beta_n}, 'OTHER': {'beta': 0.3}}
    caps = {E: 206.53, S: 206.53, N: 413.06, 'OTHER': 1234.5}
    net = types.SimpleNamespace(urban_movements=movements, movement_capacity_by_movement_veh_h=caps)
    return types.SimpleNamespace(network=net)


def tuning(value):
    return {'urban': {'sc1002w_saturation': value}}


class P1Tests(unittest.TestCase):
    def test_key_absent_touches_nothing(self):
        c = cfg()
        caps = c.network.movement_capacity_by_movement_veh_h
        before = dict(caps)
        self.assertEqual(RS.install_sc1002w_saturation(c, {'urban': {}}), {})
        self.assertEqual(RS.install_sc1002w_saturation(c, None), {})
        self.assertIs(c.network.movement_capacity_by_movement_veh_h, caps)
        self.assertEqual(caps, before)

    def test_formula_and_other_movements(self):
        ev = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))['values']
        s3, s4 = float(ev['s_p3_veh_h_lane']), float(ev['s_p4_veh_h_lane'])
        self.assertEqual((s3, s4), (1674.9, 1706.7))                       # PROBE_VALUES.json P1 (section 2.1)
        c = cfg()
        meta = RS.install_sc1002w_saturation(c, tuning(pin()))['k8b_p1']
        caps = c.network.movement_capacity_by_movement_veh_h
        self.assertEqual(caps[E], 2.0 * s3 * 0.1624 / (0.1624 + 0.6957))
        self.assertEqual(caps[S], 2.0 * s3 * 0.6957 / (0.1624 + 0.6957))
        self.assertEqual(caps[N], 1.0 * s4)
        self.assertEqual(caps['OTHER'], 1234.5)
        # section 2.1 example (betas shown rounded to 4 places there): 634.04 / 2715.76 / 1706.7
        self.assertAlmostEqual(caps[E], 634.04, delta=0.15)
        self.assertAlmostEqual(caps[S], 2715.76, delta=0.15)
        self.assertEqual(meta['before'], {E: 206.53, S: 206.53, N: 413.06})
        self.assertEqual(meta['beta'], {'E': 0.1624, 'S': 0.6957, 'N': 0.142})
        self.assertEqual(meta['evidence_sha256'], pin()['evidence_sha256'])

    def test_config_errors(self):
        bad_sha = dict(pin(), evidence_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
            RS.install_sc1002w_saturation(cfg(), tuning(bad_sha))
        with self.assertRaisesRegex(ValueError, 'must be'):
            RS.install_sc1002w_saturation(cfg(), tuning({'path': EVIDENCE}))
        with self.assertRaisesRegex(ValueError, 'repository-relative'):
            RS.install_sc1002w_saturation(cfg(), tuning(dict(pin(), evidence=str(ROOT / EVIDENCE))))
        with self.assertRaisesRegex(ValueError, 'beta_E \\+ beta_S <= 0'):
            RS.install_sc1002w_saturation(cfg(beta_e=0.0, beta_s=0.0), tuning(pin()))

    def test_make_config_apply_k8b_p1(self):
        mc = make_config()
        doc = {'urban': {'stopline_approach': {'storage': 'observed_full'}, 'queue': {'contiguous': True}}}
        out = mc.apply_k8b(doc, ROOT, parts=('p1',))
        self.assertEqual(out['urban']['sc1002w_saturation'], pin())
        self.assertNotIn('sc1002w_saturation', doc['urban'])                 # pure on doc
        with self.assertRaises(ValueError):
            mc.apply_k8b(out, ROOT, parts=('p1',))
        with self.assertRaises(ValueError):
            mc.apply_k8b({'urban': {}}, ROOT, parts=('p1',))


if __name__ == '__main__':
    unittest.main()
