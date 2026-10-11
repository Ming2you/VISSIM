"""K9-1-3 F17b tests (K8_PREDECLARATION_AMENDMENT_19 r2 section 2.3; synthetic observation bundles only -- no
capture, rollout, adapter run or VISSIM): evaluation/controllers/offramp_split_forecast.py (windows, the candidate
rule, the window documents of the decision bundle, install / apply, key absent), the deployed / harness path
equivalence on byte-equal window documents, and the FH 'FD3 kept' wrapper of the gate harness (sa_fh.neutralize_f17b).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k9_f17b.py -v
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', HERE, ROOT / 'diagnostics/sdmpc_n31_20260924/k8_gates/sa'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from evaluation.controllers import offramp_split_forecast as F  # noqa: E402
from evaluation.controllers import obs150_contract as oc  # noqa: E402

EVIDENCE = 'diagnostics/sdmpc_n31_20260924/k9/offramp_split_forecast_v3c3_20261009.json'
EVIDENCE_SHA256 = '48f7bfca705eb811607dd400fcbcf48a26d32a1e540d773c7e74adcf72dc4758'     # K91_VALUES.json f17b
EW = ['10479', '10491', '10638', '10645']


def pin():
    return {'evidence': EVIDENCE, 'evidence_sha256': hashlib.sha256((ROOT / EVIDENCE).read_bytes()).hexdigest()}


def derived(directory, Tp, run_id, counts):
    doc = {'schema': oc.DERIVED_SCHEMA, 'sim_sec': Tp, 'run_id': run_id, 'window': {'start_s': Tp - 150, 'end_s': Tp},
           'off_split': {o: {'off_veh': a, 'eligible_exits_veh': b} for o, (a, b) in counts.items()}}
    p = Path(directory) / oc.derived_path(Tp)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc), encoding='utf-8')


def counts_of(Tp):
    return {o: (Tp // 150 + i, 3 * (Tp // 150) + 2 * i + 1) for i, o in enumerate(EW)}


class ForecastRuleTests(unittest.TestCase):
    def test_evidence_is_the_p0_file(self):
        self.assertEqual(pin()['evidence_sha256'], EVIDENCE_SHA256)
        v = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))['values']
        self.assertEqual(v, {'candidate': 'C4', 'exits': EW, 'window_sec': 150, 'decision_interval_sec': 150,
                             'definition': 'all windows ending in (0, T]'})

    def test_windows(self):
        self.assertEqual({c: F.windows_of(c, 900) for c in F.CANDIDATES},
                         {'C0': [900], 'C1': [900, 750, 600], 'C2': [900, 750, 600, 450, 300, 150],
                          'C4': [900, 750, 600, 450, 300, 150], 'C3': [900]})
        self.assertEqual(F.windows_of('C4', 150), [150])
        self.assertEqual(F.windows_of('C4', 1), [])                                  # the first decision: no window
        self.assertEqual(F.windows_of('C1', 300), [300, 150])

    def test_c4_pools_all_windows(self):
        vals = {'candidate': 'C4', 'exits': ['10479', '10491']}
        cur = {'10479': (3, 10), '10491': (1, 4)}
        hist = {1350: {'10479': (2, 10), '10491': (0, 0)}, 1200: {'10479': (5, 20), '10491': (3, 6)}}
        for T in range(150, 1200, 150):
            hist[T] = {'10479': (0, 0), '10491': (0, 0)}
        fc, per, ws = F.forecast_values(vals, 1500, cur, hist)
        self.assertEqual(fc['10479'], (3 + 2 + 5) / (10 + 10 + 20))
        self.assertEqual(fc['10491'], (1 + 0 + 3) / (4 + 0 + 6))
        self.assertEqual((ws[0], ws[-1], len(ws)), (1500, 150, 10))
        self.assertEqual(per['10479']['n_windows'], 10)
        fc0, _p, _w = F.forecast_values({'candidate': 'C4', 'exits': ['10479']}, 1, {'10479': (0, 0)}, {})
        self.assertEqual(fc0, {'10479': 0.0})                                       # empty sum elig -> 0.0 (O150)


class BundleTests(unittest.TestCase):
    def test_window_documents(self):
        with tempfile.TemporaryDirectory() as d:
            derived(d, 750, 'R', {'10479': (4, 9)})
            self.assertEqual(F.window_counts({'directory': d, 'run_id': 'R'}, 750, ['10479']), {'10479': (4, 9)})
            with self.assertRaisesRegex(ValueError, 'another run'):
                F.window_counts({'directory': d, 'run_id': 'X'}, 750, ['10479'])
            with self.assertRaisesRegex(ValueError, 'missing'):
                F.window_counts({'directory': d, 'run_id': 'R'}, 600, ['10479'])
            with self.assertRaisesRegex(ValueError, 'absent'):
                F.window_counts({'directory': d, 'run_id': 'R'}, 750, ['10491'])

    def run_install(self, d, T):
        for Tp in range(150, T, 150):
            derived(d, Tp, 'R', counts_of(Tp))
        cur = counts_of(T)
        observation = {'information_cutoff_s': T,
                       'off_split_history': {o: {'off_veh': a, 'eligible_exits_veh': b} for o, (a, b) in cur.items()},
                       'off_split_ratio': {o: a / b for o, (a, b) in cur.items()}}
        cfg = types.SimpleNamespace(network=types.SimpleNamespace())
        meta = F.install(cfg, {'freeway': {'offramp_split_forecast': pin()}},
                         {oc.RAW_STATE_KEY: {'directory': d, 'run_id': 'R'}}, observation)
        return cfg, observation, meta, cur

    def test_install_apply_and_path_equivalence(self):
        T = 1650
        with tempfile.TemporaryDirectory() as deploy, tempfile.TemporaryDirectory() as replay:
            cfg, observation, meta, cur = self.run_install(deploy, T)
            for Tp in range(150, T, 150):                                         # the harness copies (bytes)
                src, dst = Path(deploy) / oc.derived_path(Tp), Path(replay) / oc.derived_path(Tp)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            cfg2, _obs2, meta2, _ = self.run_install(replay, T)
            fc = cfg.network.k9_offramp_split_forecast
            self.assertEqual(fc, cfg2.network.k9_offramp_split_forecast)          # deployed = harness path
            for o in EW:
                off = sum(counts_of(Tp)[o][0] for Tp in range(150, T + 1, 150))
                elig = sum(counts_of(Tp)[o][1] for Tp in range(150, T + 1, 150))
                self.assertEqual(fc[o], off / elig)
                pe = meta['k9_f17b']['per_exit'][o]
                self.assertEqual((pe['c0'], pe['n'], pe['current_window']), (cur[o][0] / cur[o][1], cur[o][1],
                                                                            list(cur[o])))
            self.assertEqual(meta['k9_f17b']['windows_end_s'], [150, T])
            self.assertEqual(meta['k9_f17b']['evidence_sha256'], EVIDENCE_SHA256)
            F.apply(observation, fc)
            self.assertEqual(observation['off_split_ratio'], fc)
            with self.assertRaises(ValueError):
                F.apply({'off_split_ratio': {}}, fc)

    def test_missing_window_is_an_error_and_key_absent_is_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            derived(d, 150, 'R', counts_of(150))
            observation = {'information_cutoff_s': 450, 'off_split_history': {o: {'off_veh': 1, 'eligible_exits_veh': 2}
                                                                                for o in EW},
                           'off_split_ratio': {o: 0.5 for o in EW}}
            cfg = types.SimpleNamespace(network=types.SimpleNamespace())
            with self.assertRaisesRegex(ValueError, 'missing'):                     # 300 absent: no truncated variant
                F.install(cfg, {'freeway': {'offramp_split_forecast': pin()}},
                          {oc.RAW_STATE_KEY: {'directory': d, 'run_id': 'R'}}, observation)
            self.assertEqual(F.install(cfg, {'freeway': {}}, {}, observation), {})
            self.assertFalse(hasattr(cfg.network, 'k9_offramp_split_forecast'))


class FhWrapperTests(unittest.TestCase):
    def test_fh_keeps_the_pre_f17b_shares(self):
        import sa_fh
        module = types.SimpleNamespace(apply=F.apply)
        transplant = types.SimpleNamespace(record={})
        sa_fh.neutralize_f17b(module, transplant)
        observation = {'off_split_ratio': {'10479': 0.21, '10491': 0.24, '10638': 0.17, '10645': 0.26}}
        module.apply(observation, {'10479': 0.1, '10491': 0.2, '10638': 0.3, '10645': 0.4})
        self.assertEqual(observation['off_split_ratio'], {'10479': 0.21, '10491': 0.24, '10638': 0.17, '10645': 0.26})
        self.assertTrue(transplant.record['f17b']['neutralized'])
        self.assertEqual(transplant.record['f17b']['kept'], observation['off_split_ratio'])
        with self.assertRaises(ValueError):
            module.apply({'off_split_ratio': {}}, {'10479': 0.1})


if __name__ == '__main__':
    unittest.main()
