"""K9-1-1 W1 tests (K8_PREDECLARATION_AMENDMENT_19 r2 section 2.1; synthetic cfg objects only, no capture, rollout,
adapter run or VISSIM): runtime_setup.install_sc1001wout_saturation and make_config_n31.apply_k91 (w1 part).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k9_w1.py -v
"""
from __future__ import annotations

import hashlib
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

EVIDENCE = 'diagnostics/sdmpc_n31_20260924/k9/sc1001wout_saturation_v3c3_20261009.json'
EVIDENCE_SHA256 = 'b64eadc4ca0361667b66605529f63f821ab77e524a5b18dbd0de46df2ac17a4b'     # K91_VALUES.json w1
E, N, S = 'SC1001_E_SC1002_to_W_RAMP', 'SC1001_N_SC2002_to_W_RAMP', 'SC1001_S_SC1003_to_W_RAMP'
T = 'SC1001_N_SC2002_to_S_SC1003'                    # shares lane 37|1 with N (section 2.1)


def make_config():
    path = ROOT / 'diagnostics/sdmpc_n31_20260924/make_config_n31.py'
    spec = importlib.util.spec_from_file_location('k9_test_make_config_n31', path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


def pin():
    return {'evidence': EVIDENCE, 'evidence_sha256': hashlib.sha256((ROOT / EVIDENCE).read_bytes()).hexdigest()}


def cfg(b_e=0.4, b_n=0.48571, b_t=0.42857, b_s=0.42858):
    movements = {E: {'beta': b_e}, N: {'beta': b_n}, T: {'beta': b_t}, S: {'beta': b_s}, 'OTHER': {'beta': 0.3}}
    caps = {E: 413.06, N: 206.53, S: 206.53, T: 782.61, 'OTHER': 1234.5}
    return types.SimpleNamespace(network=types.SimpleNamespace(urban_movements=movements,
                                                               movement_capacity_by_movement_veh_h=caps))


def tuning(value):
    return {'urban': {'sc1001_wout_saturation': value}}


class W1Tests(unittest.TestCase):
    def test_evidence_is_the_p0_file(self):
        self.assertEqual(pin()['evidence_sha256'], EVIDENCE_SHA256)
        v = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))['values']
        self.assertEqual(v['s_veh_h_lane'], {'29|p3': 1727.1, '37|p1': 1726.1262230995364, '40|p2': 1732.4})
        self.assertEqual(v['lane_members'], {'29|2': [E], '29|3': [E], '37|1': [T, N], '40|4': [S]})

    def test_key_absent_touches_nothing(self):
        c = cfg()
        caps = c.network.movement_capacity_by_movement_veh_h
        before = dict(caps)
        self.assertEqual(RS.install_sc1001wout_saturation(c, {'urban': {}}), {})
        self.assertEqual(RS.install_sc1001wout_saturation(c, None), {})
        self.assertIs(c.network.movement_capacity_by_movement_veh_h, caps)
        self.assertEqual(caps, before)

    def test_formula_and_other_movements(self):
        c = cfg()
        meta = RS.install_sc1001wout_saturation(c, tuning(pin()))['k9_w1']
        caps = c.network.movement_capacity_by_movement_veh_h
        s29, s37, s40 = 1727.1, 1726.1262230995364, 1732.4
        self.assertEqual(caps[E], s29 * (0.4 / 0.4 + 0.4 / 0.4))                        # two lanes, E alone
        self.assertEqual(caps[N], s37 * (0.48571 / (0.42857 + 0.48571)))               # lane 37|1 shared with T
        self.assertEqual(caps[S], s40 * (0.42858 / 0.42858))
        self.assertAlmostEqual(caps[N], 917.0045560216288, delta=0.01)                  # probe s31 1650 (MINI_K91 3)
        self.assertEqual(caps[T], 782.61)                                               # T keeps its bytes
        self.assertEqual(caps['OTHER'], 1234.5)
        self.assertEqual(meta['before'], {E: 413.06, N: 206.53, S: 206.53})
        self.assertEqual(meta['after'], {E: caps[E], N: caps[N], S: caps[S]})
        self.assertEqual(meta['beta'], {E: 0.4, T: 0.42857, N: 0.48571, S: 0.42858})
        self.assertEqual(meta['lanes'], {E: ['29|2', '29|3'], N: ['37|1'], S: ['40|4']})
        self.assertEqual(meta['evidence_sha256'], EVIDENCE_SHA256)

    def test_config_errors(self):
        with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
            RS.install_sc1001wout_saturation(cfg(), tuning(dict(pin(), evidence_sha256='0' * 64)))
        with self.assertRaisesRegex(ValueError, 'beta sum of lane 37\\|1 <= 0'):
            RS.install_sc1001wout_saturation(cfg(b_n=0.0, b_t=0.0), tuning(pin()))
        c = cfg()
        del c.network.urban_movements[T]
        with self.assertRaisesRegex(ValueError, 'lane 37\\|1 members'):
            RS.install_sc1001wout_saturation(c, tuning(pin()))
        c = cfg()
        del c.network.urban_movements[S]
        with self.assertRaisesRegex(ValueError, 'three SC1001 -> W_RAMP'):
            RS.install_sc1001wout_saturation(c, tuning(pin()))

    def test_make_config_apply_k91_w1(self):
        mc = make_config()
        k8b = {'urban': {'stopline_approach': {'storage': 'observed_full', 'city_arrival': {}},
                         'sc1002w_saturation': {}, 'wout_exit_law': {}}}
        out = mc.apply_k91(k8b, ROOT, parts=('w1',))
        self.assertEqual(out['urban']['sc1001_wout_saturation'], pin())
        self.assertNotIn('sc1001_wout_saturation', k8b['urban'])                        # pure on doc
        self.assertNotIn('latent_reservation_touch', out['urban'])                      # Z1-a: no key
        with self.assertRaises(ValueError):
            mc.apply_k91(out, ROOT, parts=('w1',))
        with self.assertRaises(ValueError):
            mc.apply_k91({'urban': {'stopline_approach': {}}}, ROOT, parts=('w1',))     # not a K8b arm
        with self.assertRaises(ValueError):
            mc.apply_k91(k8b, ROOT, parts=('w9',))


if __name__ == '__main__':
    unittest.main()
