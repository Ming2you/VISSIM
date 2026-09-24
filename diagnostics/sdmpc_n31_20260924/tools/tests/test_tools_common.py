"""WP-D shared helpers (n31_common.py)."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import n31_common as nc  # noqa: E402


class Common(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='n31_common_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_effective_tuning_follows_extends_like_the_adapter(self):
        (self.tmp / 'base.json').write_text(json.dumps(
            {'a': {'x': 1, 'y': 2}, 'config_overrides': {'freeway_follower': {'vsl_set': [80, 100, 120]}}}), encoding='utf-8')
        (self.tmp / 'sub').mkdir()
        (self.tmp / 'sub' / 'child.json').write_text(json.dumps(
            {'extends': '../base.json', 'a': {'y': 3}, 'config_overrides': {'freeway_follower': {'vsl_set': [60, 80, 110]}}}),
            encoding='utf-8')
        tuning, chain = nc.load_effective_tuning(self.tmp / 'sub' / 'child.json')
        self.assertEqual(tuning['a'], {'x': 1, 'y': 3})
        self.assertNotIn('extends', tuning)
        self.assertEqual([Path(c['path']).name for c in chain], ['child.json', 'base.json'])
        self.assertEqual(nc.effective_vsl_max(tuning), 110.0)
        (self.tmp / 'loop.json').write_text(json.dumps({'extends': 'loop.json'}), encoding='utf-8')
        with self.assertRaises(nc.ToolError):
            nc.load_effective_tuning(self.tmp / 'loop.json')
        with self.assertRaises(nc.ToolError):
            nc.effective_vsl_max({})

    def test_repo_paths_are_relative_forward_slash_only(self):
        self.assertEqual(nc.repo_path(self.tmp, 'a/b.json'), self.tmp / 'a' / 'b.json')
        for bad in ('a\\b.json', 'C:/x.json', '/x.json', 'a/../b.json', ''):
            with self.assertRaises(nc.ToolError, msg=bad):
                nc.repo_path(self.tmp, bad)

    def test_vbs_constants_and_clock(self):
        path = self.tmp / 'cfg.vbs'
        path.write_text('RW_FW_E_CHAIN_LINKS = "74,10699," & _\r\n    "2"\r\nRW_N = 12\r\n\' comment\r\n', encoding='utf-8')
        self.assertEqual(nc.vbs_constants(path), {'RW_FW_E_CHAIN_LINKS': '74,10699,2', 'RW_N': '12'})
        self.assertEqual([nc.previous_decision_sec(t) for t in (150, 300, 9000)], [1, 150, 8850])
        for bad in (1, 151, 0):
            with self.assertRaises(nc.ToolError):
                nc.previous_decision_sec(bad)

    def test_link_or_copy_and_folders(self):
        src = self.tmp / 'a.txt'
        src.write_text('x', encoding='utf-8')
        self.assertEqual(nc.link_or_copy(src, self.tmp / 'd' / 'b.txt'), 'hardlink')
        self.assertEqual(os.stat(src).st_nlink, 2)
        with self.assertRaises(nc.ToolError):
            nc.link_or_copy(src, self.tmp / 'd' / 'b.txt')
        run = self.tmp / 'run'
        (run / 'decisions_n1').mkdir(parents=True)
        self.assertEqual(nc.find_decisions_dir(run), run / 'decisions_n1')
        self.assertEqual(nc.run_dir_of(run / 'decisions_n1'), (run, 'n1'))
        (run / 'decisions_n2').mkdir()
        with self.assertRaises(nc.ToolError):
            nc.find_decisions_dir(run)
        frz = self.tmp / 'frz'
        (frz / 'x' / 'y').mkdir(parents=True)
        (frz / 'FREEZE.json').write_text('{}', encoding='utf-8')
        self.assertEqual(nc.find_freeze_root(frz / 'x' / 'y'), frz)
        self.assertIsNone(nc.find_freeze_root(self.tmp / 'run'))


if __name__ == '__main__':
    unittest.main()
