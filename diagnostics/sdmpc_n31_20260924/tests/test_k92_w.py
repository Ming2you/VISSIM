"""K9-2-1 W tests (K8_PREDECLARATION_AMENDMENT_24 section 2.1 / 4.3 U; synthetic cfg objects only, no capture, rollout,
adapter run or VISSIM): runtime_setup.install_sc109w_through_saturation.

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k92_w.py -v
Key absent = {} and nothing touched; exactly one key changes (A7) to the evidence value whose repr is '5209.8' (A11 /
RG-8); A1 (capacity / lane <= 2000), A2 (group 173|p3 sum <= lanes x 2000), A5 (value before = lanes x per_lane), A6
(spec) refuse with ValueError; a sha / schema / shape mismatch of the pin and a missing target refuse with ValueError.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', HERE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from evaluation.controllers import runtime_setup as RS  # noqa: E402

EVIDENCE = 'diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json'
EVIDENCE_SHA256 = 'b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712'      # K92_VALUES.json (P0-1)
OTHER_EVIDENCE = 'diagnostics/sdmpc_n31_20260924/k9/sc1001wout_saturation_v3c3_20261009.json'
W = 'SC109_W_SC108_to_E'
L = 'SC109_W_SC108_to_N_SC16'
PER_LANE = 206.53061224489795
SPEC = {'signal': 'SC109', 'kind': 'boundary_out', 'phase': 'SC109_p3', 'origin': 'SC108_to_SC109',
        'destination': 'out_SC109_E', 'receiving_link': 'SC109_E_out', 'beta': 0.826}


def pin(rel=EVIDENCE):
    return {'evidence': rel, 'evidence_sha256': hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}


def cfg(spec=None, caps=None):
    movements = {W: dict(SPEC if spec is None else spec),
                 L: {'signal': 'SC109', 'kind': 'internal', 'phase': 'SC109_p4', 'origin': 'SC108_to_SC109'},
                 'OTHER': {'signal': 'SC5', 'kind': 'internal', 'phase': 'SC5_p1', 'origin': 'x'}}
    caps = caps if caps is not None else {W: 3 * PER_LANE, L: 2 * PER_LANE, 'OTHER': 1234.5}
    return types.SimpleNamespace(network=types.SimpleNamespace(urban_movements=movements,
                                                               movement_capacity_by_movement_veh_h=caps))


def tuning(value):
    return {'urban': {'sc109w_through_saturation': value}}


class WTests(unittest.TestCase):
    def test_evidence_is_the_p0_file(self):
        self.assertEqual(pin()['evidence_sha256'], EVIDENCE_SHA256)
        doc = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))
        v = doc['values']
        self.assertEqual(doc['schema'], 'k92-sc109w-through-saturation/v1')
        self.assertEqual((v['movement'], v['lanes'], v['statistic'], v['s_veh_h_lane']),
                         (W, 3, 's_from_green_start_incl_startup', 1736.6))
        self.assertEqual(repr(v['capacity_veh_h']), '5209.8')
        self.assertEqual(v['capacity_repr'], '5209.8')
        self.assertEqual(v['capacity_veh_h'], round(v['s_veh_h_lane'] * v['lanes'], 1))
        self.assertNotEqual(v['capacity_veh_h'], v['s_veh_h_lane'] * v['lanes'])      # 5209.799999999999 never used

    def test_key_absent_is_empty_and_touches_nothing(self):
        c = cfg()
        before = copy.deepcopy(c.network.movement_capacity_by_movement_veh_h)
        ident = id(c.network.movement_capacity_by_movement_veh_h)
        self.assertEqual(RS.install_sc109w_through_saturation(c, {'urban': {}}, PER_LANE), {})
        self.assertEqual(RS.install_sc109w_through_saturation(c, None, PER_LANE), {})
        self.assertEqual(c.network.movement_capacity_by_movement_veh_h, before)
        self.assertEqual(id(c.network.movement_capacity_by_movement_veh_h), ident)

    def test_exactly_one_key_and_repr(self):
        c = cfg()
        before = dict(c.network.movement_capacity_by_movement_veh_h)
        meta = RS.install_sc109w_through_saturation(c, tuning(pin()), PER_LANE)
        after = c.network.movement_capacity_by_movement_veh_h
        self.assertEqual([k for k in after if after[k] != before[k]], [W])
        self.assertEqual(list(after), list(before))                                   # key order kept
        self.assertEqual(repr(after[W]), '5209.8')
        m = meta['k92_w']
        self.assertEqual((m['before'], m['after'], m['lanes'], m['u4_key']), (3 * PER_LANE, 5209.8, 3, '173|p3'))
        self.assertEqual(m['evidence_sha256'], EVIDENCE_SHA256)
        self.assertEqual(m['u4_sha256'], '22384c00313a0104a9febf5344914acd15f20058a0a62fe91d2bc085dcbb292b')
        self.assertTrue(all(k.startswith('k92_') for k in meta))

    def test_a5_value_before(self):
        c = cfg(caps={W: 5700.6, L: 2 * PER_LANE, 'OTHER': 1.0})
        with self.assertRaisesRegex(ValueError, 'A5'):
            RS.install_sc109w_through_saturation(c, tuning(pin()), PER_LANE)
        with self.assertRaisesRegex(ValueError, 'A5'):
            RS.install_sc109w_through_saturation(cfg(), tuning(pin()), None)

    def test_a6_spec(self):
        for field, value in (('kind', 'internal'), ('phase', 'SC109_p2'), ('origin', 'x'), ('destination', 'y'),
                             ('receiving_link', 'z')):
            spec = dict(SPEC, **{field: value})
            with self.assertRaisesRegex(ValueError, 'A6'):
                RS.install_sc109w_through_saturation(cfg(spec=spec), tuning(pin()), PER_LANE)

    def _doc(self, **values):
        doc = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))
        doc['values'].update(values)
        return doc, 'f' * 64

    def test_a1_a2(self):
        with mock.patch.object(RS, 'load_k8b_evidence', return_value=self._doc(capacity_veh_h=6300.0)):
            with self.assertRaisesRegex(ValueError, 'A1'):
                RS.install_sc109w_through_saturation(cfg(), tuning(pin()), PER_LANE)
        c = cfg()
        c.network.urban_movements['EXTRA'] = {'signal': 'SC109', 'kind': 'internal', 'phase': 'SC109_p3',
                                              'origin': 'SC108_to_SC109'}
        c.network.movement_capacity_by_movement_veh_h['EXTRA'] = 900.0
        with self.assertRaisesRegex(ValueError, 'A2'):
            RS.install_sc109w_through_saturation(c, tuning(pin()), PER_LANE)

    def test_pin_errors_and_missing_target(self):
        with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
            RS.install_sc109w_through_saturation(cfg(), tuning({'evidence': EVIDENCE, 'evidence_sha256': '0' * 64}),
                                                 PER_LANE)
        with self.assertRaisesRegex(ValueError, 'schema'):
            RS.install_sc109w_through_saturation(cfg(), tuning(pin(OTHER_EVIDENCE)), PER_LANE)
        with self.assertRaisesRegex(ValueError, 'must be'):
            RS.install_sc109w_through_saturation(cfg(), tuning({'evidence': EVIDENCE}), PER_LANE)
        c = cfg()
        del c.network.urban_movements[W]
        with self.assertRaisesRegex(ValueError, 'target movement'):
            RS.install_sc109w_through_saturation(c, tuning(pin()), PER_LANE)
        with mock.patch.object(RS, 'load_k8b_evidence', return_value=self._doc(movement='SC109_E_to_W_SC108')):
            with self.assertRaisesRegex(ValueError, 'target movement'):
                RS.install_sc109w_through_saturation(cfg(), tuning(pin()), PER_LANE)


if __name__ == '__main__':
    unittest.main()
