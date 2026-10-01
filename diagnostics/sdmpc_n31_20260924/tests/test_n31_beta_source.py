"""urban.beta.source routing_v3c3 (SDMPC-31 re-pin to network v3c3, 2026-10-01; routing_v3c1 on v3c1 2026-09-28..10-01,
routing_v3b on v3b 2026-09-25..28).

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

TUNING = {'urban': {'beta': {'measured': True, 'floor': 0.0, 'source': 'routing_v3c3'}}}


def cfg_for(movements):
    return types.SimpleNamespace(network=types.SimpleNamespace(
        urban_movements={name: {'beta': 0.25} for name in movements}))


class BetaSourceTests(unittest.TestCase):

    def test_routing_v3c3_is_the_n31d_table(self):
        self.assertEqual(ad.BETA_EVIDENCE_JSON['routing_v3c3'].resolve(), (fx.ROOT / make_config_n31.BETA_FILE).resolve())
        document = json.loads(ad.BETA_EVIDENCE_JSON['routing_v3c3'].read_text(encoding='utf-8'))
        self.assertEqual(document['source'].replace('\\', '/'), make_config_n31.NETWORK)
        self.assertEqual(fx.sha256(fx.ROOT / make_config_n31.NETWORK), make_config_n31.NETWORK_SHA256)

    def test_routing_v3c3_installs_every_movement(self):
        document = json.loads(ad.BETA_EVIDENCE_JSON['routing_v3c3'].read_text(encoding='utf-8'))
        cfg = cfg_for(document['beta'])
        meta = ad.install_measured_turn_beta(cfg, TUNING)
        self.assertEqual(meta['measured_beta_movements'], 373.0)       # v3b 370 + SC104 S_SC106 (v3c1 decision 1168, kept in v3c3)
        self.assertEqual(meta['measured_beta_source_routing'], 1.0)
        self.assertEqual({name: spec['beta'] for name, spec in cfg.network.urban_movements.items()}, document['beta'])

    def test_v3b_moves_the_link_40_left_turn(self):
        """RD 1119 (link 40) 1:1:1 since v3b (kept on v3c1 and v3c3): SC1001 S_SC1003 left share 0.8333 (v2) -> 0.3333."""
        document = json.loads(ad.BETA_EVIDENCE_JSON['routing_v3c3'].read_text(encoding='utf-8'))
        for turn in ('W', 'N_SC2002', 'E_SC1002'):
            self.assertEqual(document['beta']['SC1001_S_SC1003_to_' + turn], 0.3333)

    def test_explicit_approach_places_the_interchange_decisions(self):
        """RD 1117 (link 127, 707:2065:7104) reaches SC1001 W/offW/offE; RD 1124/1126/1138/1140 leave SC1004 E_SC107;
        v3c1 RD 1165 (V5b, kept in v3c3) sits on SC1 N_SC101 with RD 13 and 1164, not on SC1005 W_SC1004."""
        document = json.loads(ad.BETA_EVIDENCE_JSON['routing_v3c3'].read_text(encoding='utf-8'))
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
        sc1 = {(r['signal'], r['approach']): sorted(d['no'] for d in r['decisions']) for r in document['approaches']}
        self.assertEqual(sc1[('SC1', 'N_SC101')], ['1164', '1165', '13'])
        self.assertEqual(sc1[('SC1005', 'W_SC1004')], ['1129'])
        self.assertEqual(document['explicit_approach']['decisions']['1165'], [['SC1', 'N_SC101']])
        self.assertEqual(document['explicit_approach']['sha256'], make_config_n31.BETA_EXPLICIT_SHA256)

    def test_derivation_reproduces_the_pinned_tables(self):
        """scripts/derive_routing_turn_beta.py rebuilds the pinned v3c3 table byte for byte, and without
        --explicit-approach still rebuilds the 0824 table from the e14 network."""
        script = fx.ROOT / 'scripts/derive_routing_turn_beta.py'
        with tempfile.TemporaryDirectory() as tmp:
            v3c3, e14 = Path(tmp) / 'v3c3.json', Path(tmp) / 'e14.json'
            for argv in ([sys.executable, '-B', str(script), '--network', make_config_n31.NETWORK,
                          '--movements-config', make_config_n31.BETA_MOVEMENTS, '--out', str(v3c3),
                          '--generated', '2026-10-01', '--explicit-approach', make_config_n31.BETA_EXPLICIT],
                         [sys.executable, '-B', str(script), '--movements-config', make_config_n31.BETA_MOVEMENTS,
                          '--out', str(e14)]):
                done = subprocess.run(argv, cwd=fx.ROOT, capture_output=True, text=True, encoding='utf-8',
                                      errors='replace', env=dict(os.environ, PYTHONUTF8='1'))
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(fx.sha256(v3c3), make_config_n31.BETA_SHA256)
            self.assertEqual(fx.sha256(e14), fx.sha256(fx.ROOT / 'outputs/movement_beta_routing_20260824.json'))

    def test_missing_network_specific_file_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / 'absent.json'
            with mock.patch.dict(ad.BETA_EVIDENCE_JSON, {'routing_v3c3': absent}):
                with self.assertRaises(FileNotFoundError):
                    ad.install_measured_turn_beta(cfg_for([]), TUNING)
            with mock.patch.dict(ad.BETA_EVIDENCE_JSON, {'routing': absent}):
                meta = ad.install_measured_turn_beta(cfg_for([]), {'urban': {'beta': {'measured': True}}})
            self.assertEqual(meta, {'measured_beta_enabled': 0.0, 'measured_beta_source_missing': 1.0})

    def test_the_v3c1_sources_left_this_tree(self):
        """Network v3c3 re-pin (U8-a, 2026-10-01; as decision D1 of v3c1): the v3c1 keys and files are gone (and the v3b
        ones before them), not kept behind a flag; v3c1 replays run from a frozen tree."""
        from evaluation.controllers.beta_source import COMPLETE_BETA_SOURCES
        self.assertEqual(sorted(ad.BETA_EVIDENCE_JSON), ['knr', 'routing', 'routing_v3c3', 'routing_v3c3_2'])
        self.assertEqual(COMPLETE_BETA_SOURCES, frozenset({'routing_v3c3_2'}))
        for old in ('routing_v3c1', 'routing_v3c1_2', 'routing_v3b'):
            with self.assertRaisesRegex(ValueError, old):
                ad.install_measured_turn_beta(cfg_for([]), {'urban': {'beta': {'measured': True, 'source': old}}})
        beta = fx.ROOT / 'diagnostics/sdmpc_n31_20260924/beta'
        self.assertEqual(sorted(p.name for p in beta.glob('*v3c1*')), [])
        self.assertEqual(sorted(p.name for p in beta.glob('movement_beta_routing_*.json')),
                         ['movement_beta_routing_v3c3_20261001.json', 'movement_beta_routing_v3c3_2_20261001.json'])

    def test_the_v3c3_tables_carry_the_v3c1_values(self):
        """DA-1: v3c3 edits no routing decision, so both tables equal their v3c1 predecessors except the network pin and
        the generation date (the predecessors are git objects of K6 54d821c, read only when the repository has them)."""
        def old(rel):
            done = subprocess.run(['git', '-C', str(fx.ROOT), 'show', '54d821c:' + rel], capture_output=True)
            if done.returncode:
                self.skipTest('K6 commit 54d821c not in this repository')
            return json.loads(done.stdout.decode('utf-8'))
        n31d = 'diagnostics/sdmpc_n31_20260924/beta/'
        for key, predecessor in (('routing_v3c3', 'movement_beta_routing_v3c1_20260928.json'),
                                 ('routing_v3c3_2', 'movement_beta_routing_v3c1_2_20260928.json')):
            new = json.loads(ad.BETA_EVIDENCE_JSON[key].read_text(encoding='utf-8'))
            self.assertEqual(new['beta'], old(n31d + predecessor)['beta'], key)


if __name__ == '__main__':
    unittest.main()
