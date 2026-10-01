"""K5 (REPIN_V3C2 plan 3.5, V-5/V-9, review N5/N7): command -> written distribution map and VSL family check.

No VISSIM, no adapter run, no plant rollout. The writer is exercised through iter_action_csv_rows on the real
ver2n21 mapping (66 VSL rows) with signal rows switched off.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor/NumSim-mine'))
from evaluation.controllers import vsl_command_distribution as vcd  # noqa: E402
from evaluation.controllers import obs150_contract as oc  # noqa: E402
from evaluation.controllers import vissim_stackelberg_adapter as adapter  # noqa: E402

N31D = ROOT / 'diagnostics/sdmpc_n31_20260924'
MAPPING = ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
COMMANDS = [80.0, 90.0, 100.0, 110.0]
SINGLE = {'model': 'single_value', 'distribution_by_command': {'80': 81, '90': 91, '100': 101, '110': 110}}
L1 = {'law': 'carlson', 'A': 0.94, 'E': 1.44, 'alpha': 0.0}
L2 = {'law': 'carlson', 'A': 1.33, 'E': 0.87, 'alpha': 0.0,
      'speed_scale': {'form': 'cubic_lagrange', 'maximum': 110.0,
                      'levels': {'80': 0.7225223093088844, '90': 0.8119772280655296, '100': 0.9006844904146349}}}
RUNNER_DISTRIBUTION = 'RW_X = "1"\r\nRW_ALLOWED_VSL_SPEEDS = "80,90,100,110"\r\n'
RUNNER_SINGLE = 'RW_X = "1"\r\nRW_ALLOWED_VSL_SPEEDS = "81,91,101,110"\r\n'


def tuning(single=False, vsl_set=COMMANDS):
    doc = {'config_overrides': {'freeway_follower': {'vsl_set': list(vsl_set)}}, 'actuation': {'x': 1}}
    if single:
        doc['actuation']['vsl_command_distribution'] = copy.deepcopy(SINGLE)
    return doc


def reference(law, vsl_set=COMMANDS):
    return {'config_overrides': {'freeway_follower': {'vsl_set': list(vsl_set)}},
            'freeway': {'vsl_fd_response': {'FW_E': copy.deepcopy(law)}}}


class MapTests(unittest.TestCase):
    def test_absent_is_identity(self):
        self.assertIsNone(vcd.parse({}, COMMANDS))
        self.assertIsNone(vcd.validate_tuning(tuning()))
        self.assertEqual(vcd.written_set(tuning()), COMMANDS)

    def test_single_value_map(self):
        self.assertEqual(vcd.parse(tuning(True)['actuation'], COMMANDS), {80.0: 81, 90.0: 91, 100.0: 101, 110.0: 110})
        self.assertEqual(vcd.written_set(tuning(True)), [81.0, 91.0, 101.0, 110.0])

    def test_written_value_is_strict(self):
        mapping = vcd.parse(tuning(True)['actuation'], COMMANDS)
        self.assertEqual([vcd.written_value(mapping, c) for c in COMMANDS], [81.0, 91.0, 101.0, 110.0])
        self.assertEqual(vcd.written_value(mapping, 90.0 + 1e-12), 91.0)
        for raw in (95.0, 120.0, 89.9, float('nan'), True, '90'):
            with self.assertRaises(ValueError, msg=raw):
                vcd.written_value(mapping, raw)

    def test_runner_constant(self):
        self.assertEqual(vcd.runner_allowed_speeds(RUNNER_SINGLE), [81.0, 91.0, 101.0, 110.0])
        for text in ('RW_X = "1"\n', 'RW_ALLOWED_VSL_SPEEDS = "80"\nRW_ALLOWED_VSL_SPEEDS = "90"\n',
                     'RW_ALLOWED_VSL_SPEEDS = "fast"\n'):
            with self.assertRaises(ValueError):
                vcd.runner_allowed_speeds(text)


class WriterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping = json.loads(MAPPING.read_text(encoding='utf-8-sig'))
        cls.ramps = {str(m['id']): {'sc_no': m.get('sc_no', 0), 'rate_vph': 900.0, 'green_sec': 10.0}
                     for m in cls.mapping['ramp_meters']}

    def rows(self, values, single):
        cfg = SimpleNamespace(network=SimpleNamespace(), freeway_follower=SimpleNamespace(vsl_set=list(COMMANDS)))
        actuation = {'real_world_signal_control': {'enabled': False}}
        if single:
            actuation['vsl_command_distribution'] = copy.deepcopy(SINGLE)
        rows = list(adapter.iter_action_csv_rows(SimpleNamespace(), cfg, self.mapping, values, self.ramps,
                                                 {'controller_status': 'ok'}, actuation))
        return [r for r in rows if r['kind'] == 'vsl']

    def test_key_absent_keeps_nearest_with_the_120_extension(self):
        n = len(self.mapping['segments'])
        for value, written in ((110.0, 110.0), (80.0, 80.0), (95.0, 90.0), (117.0, 120.0), (100.4, 100.0)):
            rows = self.rows([value] * n, single=False)
            self.assertEqual(len(rows), 66)
            self.assertEqual({repr(r['speed_kph']) for r in rows}, {repr(written)})
            self.assertEqual({repr(r['speed_kph']) for r in rows},
                             {repr(adapter.nearest(value, [80.0, 90.0, 100.0, 110.0, 120.0]))})

    def test_single_value_writes_the_distribution_number(self):
        n = len(self.mapping['segments'])
        values = [COMMANDS[i % 4] for i in range(n)]
        absent, single = self.rows(values, False), self.rows(values, True)
        self.assertEqual(len(single), 66)
        target = {80.0: 81.0, 90.0: 91.0, 100.0: 101.0, 110.0: 110.0}
        for a, s in zip(absent, single):
            self.assertEqual({k: v for k, v in a.items() if k != 'speed_kph'}, {k: v for k, v in s.items() if k != 'speed_kph'})
            self.assertEqual(s['speed_kph'], target[a['speed_kph']])
            self.assertIs(type(s['speed_kph']), float)
        self.assertEqual(repr(self.rows([110.0] * n, True)[0]['speed_kph']), '110.0')
        for bad in (95.0, 120.0):
            with self.assertRaises(ValueError):
                self.rows([bad] * n, True)


class FamilyTests(unittest.TestCase):
    def test_consistent_families_pass(self):
        got = vcd.check_family(tuning(), reference(L1), RUNNER_DISTRIBUTION)
        self.assertEqual((got['family'], got['written']), ('distribution', COMMANDS))
        got = vcd.check_family(tuning(True), reference(L2), RUNNER_SINGLE)
        self.assertEqual((got['family'], got['written']), ('single_value', [81.0, 91.0, 101.0, 110.0]))

    def test_mixed_families_refuse(self):
        for t, r, runner in ((tuning(), reference(L2), RUNNER_DISTRIBUTION),          # L2 + identity map
                             (tuning(True), reference(L1), RUNNER_SINGLE),            # L1 + single-value map
                             (tuning(True), reference(L2), RUNNER_DISTRIBUTION),      # runner 80..110 + single-value map
                             (tuning(), reference(L1), RUNNER_SINGLE),                # runner 81.. + identity map
                             (tuning(), reference(L1, [80.0, 100.0, 110.0]), RUNNER_DISTRIBUTION)):
            with self.assertRaises(ValueError):
                vcd.check_family(t, r, runner)
        bad = copy.deepcopy(L2)
        bad['speed_scale']['levels'] = {'70': .6, '90': .81, '100': .9}
        with self.assertRaises(ValueError):
            vcd.check_family(tuning(True), reference(bad), RUNNER_SINGLE)

    def test_this_tree_passes_and_validate_tuning_v2_refuses_a_bad_map(self):
        config = json.loads((N31D / 'config_n31_v2.json').read_text(encoding='utf-8'))
        plant = json.loads((N31D / 'plant_n31_v2.json').read_text(encoding='utf-8-sig'))
        got = vcd.check_family_files(config, ROOT / plant['sources']['reference_config']['path'],
                                     ROOT / plant['sources']['runner_config']['path'])
        self.assertEqual(got['family'], 'distribution')
        oc.validate_tuning_v2(config, plant)
        broken = copy.deepcopy(config)
        broken['actuation']['vsl_command_distribution'] = {'model': 'single_value',
                                                           'distribution_by_command': {'80': 81, '90': 91, '100': 101}}
        with self.assertRaises(oc.ObsContractError):
            oc.validate_tuning_v2(broken, plant)


if __name__ == '__main__':
    unittest.main()
