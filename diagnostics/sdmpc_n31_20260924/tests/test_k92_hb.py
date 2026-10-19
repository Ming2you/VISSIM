"""K9-2-2 H-b tests (K8_PREDECLARATION_AMENDMENT_24 sections 2.2 / 2.3 / 4.3 U; synthetic inputs only, no capture,
rollout, adapter run or VISSIM): signal_head_observation.configure_head_floor_seed and the seed lines of install().

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k92_hb.py -v
The section 2.2 formula (lower end max(rule value, s) at the carried point even without a valid window, and
max(base, carried, supported, s) at the supported point; learning kept), key absent = the old formula bytes and
results, the seed after an invalid window and after a discarded prior, the binding meta (strict), meta names k92_*,
B1-B6 refusals and the coupling (seed without the W key -> ValueError, D-K9-31)."""
from __future__ import annotations

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

from evaluation.controllers import signal_head_observation as SHO  # noqa: E402

EVIDENCE = 'diagnostics/sdmpc_n31_20260924/k92/head_floor_seed_v3c3_robs_20261016.json'
EVIDENCE_SHA256 = 'b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee'       # K92_VALUES.json (P0-2)
W_PIN = {'evidence': 'diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json',
         'evidence_sha256': 'b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712'}
S = 1045.1612903225805
BASE = 413.0612244897959
L = 'SC109_W_SC108_to_N_SC16'
W = 'SC109_W_SC108_to_E'
OPTIONS = {'enabled': True, 'min_green_sec': 30, 'min_crossings': 5}
HEADS_P4 = [{'head_id': '1090501', 'link': '173', 'lane': 5, 'position_m': 26.07073929399942, 'sc': '109', 'sg': '5'},
            {'head_id': '1090502', 'link': '173', 'lane': 4, 'position_m': 26.02638042297696, 'sc': '109', 'sg': '5'}]
HEADS_P3 = [{'head_id': '1090201', 'link': '173', 'lane': 3, 'position_m': 25.927629118318755, 'sc': '109', 'sg': '2'}]
PLAN = {'controllers': {'109': {'phase_signal_groups': {'p3': [2], 'p4': [5]}}}}


def pin():
    return {'evidence': EVIDENCE, 'evidence_sha256': hashlib.sha256((ROOT / EVIDENCE).read_bytes()).hexdigest()}


def tuning(seed=True, w=True, options=None):
    cap = {'head_observation': dict(OPTIONS if options is None else options)}
    if seed:
        cap['head_floor_seed'] = pin()
    urban = {'capacity': cap}
    if w:
        urban['sc109w_through_saturation'] = dict(W_PIN)
    return {'urban': urban}


def cfg():
    net = types.SimpleNamespace(
        urban_movements={W: {'origin': 'SC108_to_SC109', 'kind': 'boundary_out'},
                         L: {'origin': 'SC108_to_SC109', 'kind': 'internal'}},
        movement_capacity_by_movement_veh_h={W: 619.5918367346939, L: BASE, 'OTHER': 1.0},
        movement_capacity_veh_h=0.0)
    return types.SimpleNamespace(network=net)


def distribute(cfg_, groups, est, caps):
    for (link, phase), total in est.items():
        if (link, phase) == ('173', 'p4'):
            caps[L] = float(total) * 1.0
    return len(est)


def window(start, end, green=31, q=(5, 4), valid=True):
    rows = []
    for h, qq in zip(HEADS_P4 + HEADS_P3, list(q) + [0]):
        rows.append({'head_id': h['head_id'], 'link': h['link'], 'lane': h['lane'],
                     'position_m': SHO.serialized_head_position(h['position_m']), 'sc': h['sc'], 'sg': h['sg'],
                     'green_sec': green, 'qualified_crossings': qq, 'crossings': qq, 'native_sec': end - start,
                     'controlled_sec': 0})
    return {'start_sec': start, 'end_sec': end, 'clock_complete': valid, 'heads': rows}


def run(tmp, c, now, win, prior_md=None, prior_time=None, run_id='r'):
    prev = Path(tmp) / 'prev.json'
    if prior_md is None:
        prev.write_text('{}', encoding='utf-8')
    else:
        md = dict(prior_md, sim_sec=prior_time)
        md.setdefault('head_provenance_ctx', 1.0)
        md.setdefault('head_observation_snapshot_sec', prior_time)
        prev.write_text(json.dumps({'metadata': md, 'run_provenance': {'run_id': run_id}}), encoding='utf-8')
    state = {'sim_sec': now, 'network_path': 'n.inpx', 'run_provenance': {'run_id': 'r'},
             'local_observation': {'signal_observation_window': win}}
    c.network.movement_capacity_by_movement_veh_h = {W: 619.5918367346939, L: BASE, 'OTHER': 1.0}   # each decision
    caps = dict(c.network.movement_capacity_by_movement_veh_h)
    with mock.patch.object(SHO, 'observation_mode', return_value='v2'), \
            mock.patch.object(SHO, 'validate_provenance', return_value='ctx'), \
            mock.patch.object(SHO, 'physical_groups', return_value={('173', 'p4'): HEADS_P4, ('173', 'p3'): HEADS_P3}):
        meta = SHO.install(c, state, str(prev), caps, PLAN, distribute, dict(OPTIONS))
    return meta


def floor_key():
    ident = hashlib.sha256(json.dumps({'heads': HEADS_P4, 'context': 'ctx'}, sort_keys=True).encode()).hexdigest()[:16]
    return 'head_discharge_floor_173_p4_' + ident, 'head_candidate_rate_173_p4_' + ident, \
        'head_candidate_end_173_p4_' + ident


class HbTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix='k92hb_')

    def seeded(self):
        c = cfg()
        meta = SHO.configure_head_floor_seed(c, tuning(), {}, PLAN)
        self.assertEqual(c.network.head_floor_seed, {('173', 'p4'): S})
        return c, meta

    def test_evidence_is_the_p0_file(self):
        self.assertEqual(pin()['evidence_sha256'], EVIDENCE_SHA256)
        v = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))['values']
        self.assertEqual((repr(v['seed']), v['seed_repr'], v['learning']), ('1045.1612903225805', '1045.1612903225805',
                                                                            'kept (D-K9-36)'))

    def test_old_formula_lines_kept(self):
        src = (ROOT / 'evaluation/controllers/signal_head_observation.py').read_bytes()
        self.assertEqual(src.count(b'            estimates[link, phase] = max(base, carried)\r\n'), 1)
        self.assertEqual(src.count(b'        estimates[link, phase] = max(base, carried, supported)\r\n'), 1)

    def test_key_absent_old_results(self):
        c = cfg()
        c.network.head_floor_seed = {('173', 'p4'): S}
        self.assertEqual(SHO.configure_head_floor_seed(c, tuning(seed=False), {}, PLAN), {})
        self.assertFalse(hasattr(c.network, 'head_floor_seed'))
        fk, ck, ek = floor_key()
        meta = run(self.tmp, c, 1050.0, window(900.0, 1050.0))
        self.assertNotIn(fk, meta)
        self.assertNotIn('k92_hb_seed_binding', meta)
        self.assertEqual(meta[ck], 3600 * 5 / 31 + 3600 * 4 / 31)
        self.assertEqual(c.network.movement_capacity_by_movement_veh_h[L], BASE)
        meta2 = run(self.tmp, c, 1200.0, window(1050.0, 1200.0), prior_md={fk: 900.0, ck: 1200.0, ek: 1050.0},
                    prior_time=1050.0)
        rate = 3600 * 5 / 31 + 3600 * 4 / 31
        self.assertEqual(meta2[fk], max(BASE, 900.0, min(1200.0, rate)))
        self.assertEqual(meta2['head_observation_groups_updated'], 1.0)

    def test_seed_without_valid_window_and_binding(self):
        c, cmeta = self.seeded()
        self.assertTrue(all(k.startswith('k92_') for k in cmeta))
        fk, _ck, _ek = floor_key()
        meta = run(self.tmp, c, 150.0, window(0.0, 150.0, valid=False))
        self.assertEqual(meta[fk], S)
        self.assertEqual(meta['k92_hb_seed_binding'], 1.0)
        self.assertEqual(meta['head_observation_groups_carried'], 0.0)            # counters unchanged (H5)
        self.assertEqual(meta['head_observation_groups_updated'], 0.0)
        self.assertEqual(c.network.movement_capacity_by_movement_veh_h[L], S)
        self.assertEqual([k for k in meta if k.startswith('head_') and 'floor' in k], [fk])

    def test_seed_after_discarded_prior(self):
        c, _ = self.seeded()
        fk, ck, ek = floor_key()
        meta = run(self.tmp, c, 150.0, window(0.0, 150.0), prior_md={fk: S}, prior_time=1.0)
        self.assertEqual(meta['head_observation_prior_discarded'], 1.0)
        self.assertEqual(meta[fk], S)
        self.assertEqual(meta['k92_hb_seed_binding'], 1.0)

    def test_supported_and_learning_kept(self):
        c, _ = self.seeded()
        fk, ck, ek = floor_key()
        high = 3600 * 9 / 31 + 3600 * 8 / 31
        meta = run(self.tmp, c, 1200.0, window(1050.0, 1200.0, q=(9, 8)),
                   prior_md={fk: S, ck: high, ek: 1050.0}, prior_time=1050.0)
        self.assertEqual(meta[fk], max(BASE, S, min(high, high), S))
        self.assertEqual(meta['k92_hb_seed_binding'], 0.0)
        self.assertEqual(meta['head_observation_groups_updated'], 1.0)
        low = 3600 * 5 / 31 + 3600 * 0 / 31
        meta2 = run(self.tmp, c, 1350.0, window(1200.0, 1350.0, q=(5, 0)),
                    prior_md={fk: S, ck: low, ek: 1200.0}, prior_time=1200.0)
        self.assertEqual(meta2[fk], S)
        self.assertEqual(meta2['k92_hb_seed_binding'], 0.0)                       # carried = s: not strictly above
        meta3 = run(self.tmp, c, 1350.0, window(1200.0, 1350.0, q=(5, 0)),
                    prior_md={ck: low, ek: 1200.0}, prior_time=1200.0)
        self.assertEqual(meta3[fk], S)
        self.assertEqual(meta3['k92_hb_seed_binding'], 1.0)                       # supported 580.6 < s

    def test_seed_below_carried_is_not_binding(self):
        c, _ = self.seeded()
        fk, ck, ek = floor_key()
        meta = run(self.tmp, c, 3900.0, window(3750.0, 3900.0, green=20), prior_md={fk: 1509.6774193548385},
                   prior_time=3750.0)
        self.assertEqual(meta[fk], 1509.6774193548385)
        self.assertEqual(meta['k92_hb_seed_binding'], 0.0)

    def test_b3_b4_runtime(self):
        c, _ = self.seeded()
        prev = Path(self.tmp) / 'prev.json'
        prev.write_text('{}', encoding='utf-8')
        state = {'sim_sec': 150.0, 'network_path': 'n.inpx', 'run_provenance': {'run_id': 'r'},
                 'local_observation': {'signal_observation_window': None}}
        other = [dict(HEADS_P4[0], head_id='9999999'), HEADS_P4[1]]
        with mock.patch.object(SHO, 'observation_mode', return_value='v2'), \
                mock.patch.object(SHO, 'validate_provenance', return_value='ctx'), \
                mock.patch.object(SHO, 'physical_groups', return_value={('173', 'p4'): other}):
            with self.assertRaisesRegex(ValueError, 'B3 / B4'):
                SHO.install(c, state, str(prev), dict(c.network.movement_capacity_by_movement_veh_h), PLAN, distribute,
                            dict(OPTIONS))

        def two(cfg_, groups, est, caps):
            caps[L] = 1.0
            caps['EXTRA'] = 1.0
        with mock.patch.object(SHO, 'observation_mode', return_value='v2'), \
                mock.patch.object(SHO, 'validate_provenance', return_value='ctx'), \
                mock.patch.object(SHO, 'physical_groups', return_value={('173', 'p4'): HEADS_P4}):
            with self.assertRaisesRegex(ValueError, 'B3 / B4'):
                SHO.install(c, state, str(prev), dict(c.network.movement_capacity_by_movement_veh_h), PLAN, two,
                            dict(OPTIONS))

    def test_configure_refusals(self):
        with self.assertRaisesRegex(ValueError, 'requires urban.sc109w_through_saturation'):
            SHO.configure_head_floor_seed(cfg(), tuning(w=False), {}, PLAN)               # D-K9-31 coupling
        with self.assertRaisesRegex(ValueError, 'B6'):
            SHO.configure_head_floor_seed(cfg(), tuning(options={'enabled': True, 'min_green_sec': 20,
                                                                 'min_crossings': 5}), {}, PLAN)
        bad = tuning()
        bad['urban']['capacity']['head_floor_seed'] = {'evidence': EVIDENCE, 'evidence_sha256': '0' * 64}
        with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
            SHO.configure_head_floor_seed(cfg(), bad, {}, PLAN)
        with self.assertRaisesRegex(ValueError, 'B3'):
            SHO.configure_head_floor_seed(cfg(), tuning(), {}, {'controllers': {'109': {'phase_signal_groups':
                                                                                         {'p3': [5], 'p4': [2]}}}})
        c = cfg()
        c.network.movement_capacity_by_movement_veh_h[L] = 2000.0
        with self.assertRaisesRegex(ValueError, 'B2'):
            SHO.configure_head_floor_seed(c, tuning(), {}, PLAN)
        c = cfg()
        c.network.urban_movements[L]['origin'] = 'elsewhere'
        with self.assertRaisesRegex(ValueError, 'coupling'):
            SHO.configure_head_floor_seed(c, tuning(), {}, PLAN)
        from evaluation.controllers import runtime_setup as RS
        doc = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))
        for change, msg in (({'seed': 4100.0, 'seed_repr': '4100.0'}, 'B1'),
                            ({'members': ['X']}, 'B3 / B4'), ({'seed_repr': '1045.1612903225807'}, 'repr')):
            d = json.loads(json.dumps(doc))
            d['values'].update(change)
            with mock.patch.object(RS, 'load_k8b_evidence', return_value=(d, 'f' * 64)):
                with self.assertRaisesRegex(ValueError, msg):
                    SHO.configure_head_floor_seed(cfg(), tuning(), {}, PLAN)


if __name__ == '__main__':
    unittest.main()
