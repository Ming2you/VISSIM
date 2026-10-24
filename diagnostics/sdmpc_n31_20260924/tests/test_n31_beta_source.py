"""urban.beta.source routing_v3b (SDMPC-31 re-pin to network v3b, 2026-09-25).

config_n31_v2.json selects the routing beta derived on the pinned network (N31D/beta/, scripts/
derive_routing_turn_beta.py with the 474-movement core17legs4b config) instead of the default 0824 table,
which was derived on modi_eval_userfix_20260814e. A network-specific source must never switch the measured
beta off silently when its file is missing; the default sources keep their old fallback (bit-identical).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import n31_fixtures as fx
import make_config_n31
from evaluation.controllers import vissim_stackelberg_adapter as ad

TUNING = {'urban': {'beta': {'measured': True, 'floor': 0.0, 'source': 'routing_v3b'}}}


def cfg_for(movements):
    return types.SimpleNamespace(network=types.SimpleNamespace(
        urban_movements={name: {'beta': 0.25} for name in movements}))


class BetaSourceTests(unittest.TestCase):

    def test_routing_v3b_is_the_n31d_table(self):
        self.assertEqual(ad.BETA_EVIDENCE_JSON['routing_v3b'].resolve(), (fx.ROOT / make_config_n31.BETA_FILE).resolve())
        document = json.loads(ad.BETA_EVIDENCE_JSON['routing_v3b'].read_text(encoding='utf-8'))
        self.assertEqual(document['source'].replace('\\', '/'), make_config_n31.NETWORK)
        self.assertEqual(fx.sha256(fx.ROOT / make_config_n31.NETWORK), make_config_n31.NETWORK_SHA256)

    def test_routing_v3b_installs_every_movement(self):
        document = json.loads(ad.BETA_EVIDENCE_JSON['routing_v3b'].read_text(encoding='utf-8'))
        cfg = cfg_for(document['beta'])
        meta = ad.install_measured_turn_beta(cfg, TUNING)
        self.assertEqual(meta['measured_beta_movements'], 370.0)
        self.assertEqual(meta['measured_beta_source_routing'], 1.0)
        self.assertEqual({name: spec['beta'] for name, spec in cfg.network.urban_movements.items()}, document['beta'])

    def test_v3b_moves_the_link_40_left_turn(self):
        """RD 1119 (link 40) 1:1:1 in v3b: SC1001 S_SC1003 left share 0.8333 (v2) -> 0.3333."""
        document = json.loads(ad.BETA_EVIDENCE_JSON['routing_v3b'].read_text(encoding='utf-8'))
        for turn in ('W', 'N_SC2002', 'E_SC1002'):
            self.assertEqual(document['beta']['SC1001_S_SC1003_to_' + turn], 0.3333)

    def test_explicit_approach_places_the_interchange_decisions(self):
        """RD 1117 (link 127, 707:2065:7104) reaches SC1001 W/offW/offE; RD 1124/1126/1138/1140 leave SC1004 E_SC107."""
        document = json.loads(ad.BETA_EVIDENCE_JSON['routing_v3b'].read_text(encoding='utf-8'))
        beta = document['beta']
        self.assertEqual([beta['SC1001_W_to_' + t] for t in ('E_SC1002', 'N_SC2002', 'S_SC1003')], [0.7193, 0.2091, 0.0716])
        for app in ('offW', 'offE'):   # to_W has no route evidence and keeps its 1/6 (the derivation's held-share rule)
            self.assertEqual(beta['SC1001_%s_to_W' % app], 0.1667)
            self.assertEqual(beta['SC1001_%s_to_E_SC1002' % app], 0.5994)
        self.assertFalse([k for k in beta if k.startswith('SC1004_E_SC107_')])
        placed = {(r['signal'], r['approach']): sorted((d['no'], d['how']) for d in r['decisions'])
                  for r in document['approaches'] if r['signal'] == 'SC1004'}
        self.assertEqual(placed[('SC1004', 'W')], [('1138', '명시 배정'), ('1140', '명시 배정')])
        self.assertEqual(placed[('SC1004', 'offW')], [('1140', '명시 배정')])
        self.assertEqual(placed[('SC1004', 'offE')], [('1126', '명시 배정')])
        self.assertEqual(placed[('SC1004', 'S')], [('1124', '명시 배정')])
        self.assertEqual(document['explicit_approach']['sha256'], make_config_n31.BETA_EXPLICIT_SHA256)

    def test_derivation_reproduces_the_pinned_tables(self):
        """scripts/derive_routing_turn_beta.py rebuilds the pinned v3b table byte for byte, and without
        --explicit-approach still rebuilds the 0824 table from the e14 network."""
        script = fx.ROOT / 'scripts/derive_routing_turn_beta.py'
        with tempfile.TemporaryDirectory() as tmp:
            v3b, e14 = Path(tmp) / 'v3b.json', Path(tmp) / 'e14.json'
            for argv in ([sys.executable, '-B', str(script), '--network', make_config_n31.NETWORK,
                          '--movements-config', make_config_n31.BETA_MOVEMENTS, '--out', str(v3b),
                          '--generated', '2026-09-25', '--explicit-approach', make_config_n31.BETA_EXPLICIT],
                         [sys.executable, '-B', str(script), '--movements-config', make_config_n31.BETA_MOVEMENTS,
                          '--out', str(e14)]):
                done = subprocess.run(argv, cwd=fx.ROOT, capture_output=True, text=True, encoding='utf-8',
                                      errors='replace', env=dict(os.environ, PYTHONUTF8='1'))
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(fx.sha256(v3b), make_config_n31.BETA_SHA256)
            self.assertEqual(fx.sha256(e14), fx.sha256(fx.ROOT / 'outputs/movement_beta_routing_20260824.json'))

    def test_missing_network_specific_file_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / 'absent.json'
            with mock.patch.dict(ad.BETA_EVIDENCE_JSON, {'routing_v3b': absent}):
                with self.assertRaises(FileNotFoundError):
                    ad.install_measured_turn_beta(cfg_for([]), TUNING)
            with mock.patch.dict(ad.BETA_EVIDENCE_JSON, {'routing': absent}):
                meta = ad.install_measured_turn_beta(cfg_for([]), {'urban': {'beta': {'measured': True}}})
            self.assertEqual(meta, {'measured_beta_enabled': 0.0, 'measured_beta_source_missing': 1.0})


if __name__ == '__main__':
    unittest.main()
