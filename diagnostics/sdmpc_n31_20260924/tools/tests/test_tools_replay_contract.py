"""K2 (REPIN_V3C2 plan section 3.2, P-1/P-2): the replay action contract is membership in the written set.

Runs no replay, no adapter, no PowerShell (test_tools_replay.py stays untouched and is not run here).
"""
from __future__ import annotations

import csv
import inspect
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import make_replay_state_v2 as mr  # noqa: E402
import n31_common as nc  # noqa: E402

COMMANDS = [80.0, 90.0, 100.0, 110.0]
SINGLE = {'model': 'single_value', 'distribution_by_command': {'80': 81, '90': 91, '100': 101, '110': 110}}
FIELDS = ['kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane', 'speed_kph', 'p1_green', 'p2_green', 'p3_green',
          'p4_green', 'offset', 'rate_vph', 'green_sec', 'metadata']


def tuning(actuation=None, vsl_set=COMMANDS, runner='diagnostics/n31/scenario/runner.vbs'):
    doc = {'config_overrides': {'freeway_follower': {'vsl_set': list(vsl_set)}},
           'execution': {'signal_vbs_config': runner}}
    if actuation is not None:
        doc['actuation'] = {'vsl_command_distribution': actuation}
    return doc


class ReplayContract(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='n31_replay_contract_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def action_csv(self, speeds, vsl_rows=mr.VSL_ROWS, meter_rows=mr.METER_ROWS):
        path = self.tmp / ('action_%d.csv' % len(list(self.tmp.iterdir())))   # never overwrite an earlier file
        with open(path, 'w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for i in range(vsl_rows):
                writer.writerow({'kind': 'vsl', 'id': f'S{i}', 'speed_kph': speeds[i % len(speeds)], 'metadata': 'ok'})
            for i in range(meter_rows):
                writer.writerow({'kind': 'ramp_meter', 'id': f'RM{i}', 'green_sec': 10.0, 'metadata': 'ok'})
        return path

    def contract(self, written, runner=None):
        return {'written_set': list(written), 'runner_allowed': list(written if runner is None else runner),
                'runner_config': 'x'}

    def test_membership_in_the_written_set(self):
        distribution = self.contract([80.0, 90.0, 100.0, 110.0])
        single = self.contract([81.0, 91.0, 101.0, 110.0])
        for speeds, family, ok in (([110.0], distribution, True), ([110.0], single, True),
                                   ([91.0, 110.0], single, True), ([80.0, 90.0, 110.0], distribution, True),
                                   ([90.0], single, False), ([120.0], single, False), ([120.0], distribution, False),
                                   ([91.0], distribution, False)):
            got = mr.action_contract(self.action_csv(speeds), None, vsl_contract=family)
            self.assertIs(got['ok'], ok, (speeds, family['written_set']))
            self.assertEqual(got['vsl_speeds'], sorted(set(speeds)))
            self.assertEqual(got['vsl_written_set'], family['written_set'])

    def test_row_counts_still_bind(self):
        written = self.contract([81.0, 91.0, 101.0, 110.0])
        self.assertFalse(mr.action_contract(self.action_csv([110.0], vsl_rows=65), None, vsl_contract=written)['ok'])
        self.assertFalse(mr.action_contract(self.action_csv([110.0], meter_rows=7), None, vsl_contract=written)['ok'])

    def test_runner_must_equal_the_written_set(self):
        got = mr.action_contract(self.action_csv([110.0]), None,
                                 vsl_contract=self.contract([81.0, 91.0, 101.0, 110.0], runner=[80.0, 90.0, 100.0, 110.0]))
        self.assertFalse(got['ok'])
        self.assertFalse(got['vsl_written_set_equals_runner'])

    def test_positional_vsl_expected_keeps_its_meaning(self):
        # N14: compare(out_dir, vsl_expected) and action_contract(csv, vsl_expected) are unchanged positionally.
        params = list(inspect.signature(mr.compare).parameters.values())
        self.assertEqual([p.name for p in params[:2]], ['out_dir', 'vsl_expected'])
        self.assertEqual(params[2].name, 'vsl_contract')
        self.assertIs(params[2].kind, inspect.Parameter.KEYWORD_ONLY)
        path = self.action_csv([110.0])
        self.assertEqual(mr.action_contract(path, 110.0),
                         {'ok': True, 'vsl_rows': 66, 'vsl_speeds': [110.0], 'vsl_expected': 110.0, 'meter_rows': 8})
        self.assertFalse(mr.action_contract(self.action_csv([100.0, 110.0]), 110.0)['ok'])
        self.assertFalse(mr.action_contract(path, 120.0)['ok'])
        self.assertTrue(mr.action_contract(self.action_csv([91.0]), None)['ok'])   # no contract: counts only
        # both: the single-value assertion and membership
        single = self.contract([81.0, 91.0, 101.0, 110.0])
        self.assertTrue(mr.action_contract(path, 110.0, vsl_contract=single)['ok'])
        self.assertFalse(mr.action_contract(self.action_csv([91.0, 110.0]), 110.0, vsl_contract=single)['ok'])


class WrittenSet(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='n31_written_set_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_identity_and_single_value_images(self):
        self.assertEqual(nc.effective_vsl_written_set(tuning()), [80.0, 90.0, 100.0, 110.0])
        self.assertEqual(nc.effective_vsl_written_set(tuning(SINGLE)), [81.0, 91.0, 101.0, 110.0])

    def test_malformed_maps_refuse(self):
        bad = [
            {'model': 'identity', 'distribution_by_command': SINGLE['distribution_by_command']},
            {'model': 'single_value'},
            {'model': 'single_value', 'distribution_by_command': {'80': 81, '90': 91, '100': 101}},
            {'model': 'single_value', 'distribution_by_command': {'80': 81, '90': 91, '100': 101, '110': 111}},
            {'model': 'single_value', 'distribution_by_command': {'80': 81, '90': 81, '100': 101, '110': 110}},
            {'model': 'single_value', 'distribution_by_command': {'80': 81, '90': 91, '100': 101, '110': 110, '120': 121}},
            {'model': 'single_value', 'distribution_by_command': {'80.0': 81, '90': 91, '100': 101, '110': 110}},
            {'model': 'single_value', 'distribution_by_command': {'80': 81.0, '90': 91, '100': 101, '110': 110}},
            {'model': 'single_value', 'distribution_by_command': {'80': True, '90': 91, '100': 101, '110': 110}},
        ]
        for spec in bad:
            with self.assertRaises(nc.ToolError, msg=spec):
                nc.effective_vsl_written_set(tuning(spec))
        with self.assertRaises(nc.ToolError):
            nc.effective_vsl_written_set({'config_overrides': {}})

    def test_tuning_tree_runner_is_found_and_read(self):
        root = self.tmp / 'tree'
        (root / 'diagnostics/n31/scenario').mkdir(parents=True)
        (root / 'diagnostics/n31/scenario/runner.vbs').write_text(
            "' runner\r\nRW_A = \"1\"\r\nRW_ALLOWED_VSL_SPEEDS = \"81,91,101,110\"\r\n", encoding='utf-8')
        path = root / 'diagnostics/n31/config.json'
        path.write_text(json.dumps(tuning(SINGLE)), encoding='utf-8')
        doc, _ = nc.load_effective_tuning(path)
        got = nc.tuning_vsl_contract(path, doc)
        self.assertEqual(got['written_set'], [81.0, 91.0, 101.0, 110.0])
        self.assertEqual(got['runner_allowed'], [81.0, 91.0, 101.0, 110.0])
        self.assertEqual(Path(got['runner_config']), root / 'diagnostics/n31/scenario/runner.vbs')
        path.write_text(json.dumps(tuning(SINGLE, runner='diagnostics/n31/scenario/missing.vbs')), encoding='utf-8')
        with self.assertRaises(nc.ToolError):
            nc.tuning_vsl_contract(path, nc.load_effective_tuning(path)[0])

    def test_the_deployed_tuning_of_this_tree(self):
        path = nc.ROOT / nc.N31D_REL / 'config_n31_v2.json'
        doc, _ = nc.load_effective_tuning(path)
        got = nc.tuning_vsl_contract(path, doc)
        self.assertEqual(got['written_set'], got['runner_allowed'])
        self.assertEqual(Path(got['runner_config']).resolve(),
                         (nc.ROOT / doc['execution']['signal_vbs_config']).resolve())


if __name__ == '__main__':
    unittest.main()
