"""Pinned physical replay must preserve service coordinates and writer encoding."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from evaluation.controllers import diagnostic_signal_profile as profile


class RecordedPhysicalMeterReplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'action.json'
        self.plan = {'controllers': {}}
        self.ramps = {f'RM_C{i}': {'sc_no': 9100+i, 'capacity_vph': 900., 'cycle_sec': 10.,
            'service_by_green_veh_h': {'0': 0., '8': 1166.4, '10': 1512.}} for i in range(1, 9)}
        self.cfg = NS(network=NS(freeway_links=['FW_E', 'FW_W'], physical_ramp_branches={
            'ramps': self.ramps, 'legacy_groups': ['A', 'B', 'C', 'D'], 'minimum_green_sec': 1}))
        self.factory = NS(uncontrolled=lambda cfg: NS(N_P_star=0., N_UF_star=0., green_times={},
            offsets={}, vsl={}, ramp_metering={mid: 1512. for mid in self.ramps}, diagnostics={}))
        self.spec = {'green_action_json': str(self.source),
            'plan_content_sha256': hashlib.sha256(json.dumps(self.plan, sort_keys=True,
                separators=(',', ':')).encode()).hexdigest(), 'source_action_csv': str(self.source.with_suffix('.csv'))}
        self.tuning = {'diagnostic': {'signal_profile': self.spec}}

    def write(self, green=8, services=None):
        greens = {mid: (green if mid == 'RM_C1' else 10) for mid in self.ramps}
        rates = {mid: self.ramps[mid]['service_by_green_veh_h'][str(g)] for mid, g in greens.items()}
        self.source.write_text(json.dumps({'green_times': {}, 'ramp_metering': rates if services is None else services}), encoding='utf-8')
        with self.source.with_suffix('.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=('kind', 'id', 'sc_no', 'rate_vph', 'green_sec', 'metadata'))
            writer.writeheader()
            for mid, g in greens.items():
                writer.writerow(dict(kind='ramp_meter', id=mid, sc_no=self.ramps[mid]['sc_no'],
                    rate_vph=g*90., green_sec=g, metadata='ok'))
        self.spec['green_action_sha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.spec['source_action_csv_sha256'] = hashlib.sha256(self.source.with_suffix('.csv').read_bytes()).hexdigest()
        return rates

    def build(self):
        return profile.build_control(self.cfg, self.factory, self.tuning, self.plan, self.root)

    def test_opt_in_g8_keeps_service_table_separate_from_csv_rate(self):
        expected = self.write()
        before = copy.deepcopy(self.tuning)
        with self.assertRaisesRegex(ValueError, 'service rates differ'):
            self.build()
        self.assertEqual(before, self.tuning)
        self.spec['replay_recorded_metering'] = True
        action = self.build()
        self.assertEqual(action.ramp_metering, expected)
        self.assertEqual(action.diagnostics['rw_meter_green_RM_C1'], 8.)
        self.assertEqual(action.ramp_metering['RM_C1'], 1166.4)
        self.assertNotEqual(action.ramp_metering['RM_C1'], 720.)
        self.assertEqual(set(action.vsl.values()), {120.})

    def test_absent_and_false_preserve_g10_replay(self):
        self.write(green=10)
        original = vars(self.build())
        self.spec['replay_recorded_metering'] = False
        self.assertEqual(original, vars(self.build()))

    def test_inconsistent_json_services_cannot_override_pinned_csv(self):
        self.write(services={mid: 1512. for mid in self.ramps})
        self.spec['replay_recorded_metering'] = True
        with self.assertRaisesRegex(ValueError, 'service rates differ'):
            self.build()

    def test_incomplete_nonfinite_boolean_services_and_flags_fail_closed(self):
        self.spec['replay_recorded_metering'] = True
        valid = self.write()
        for bad in ({}, {**valid, 'RM_C1': float('nan')}, {**valid, 'RM_C1': True}, {**valid, 'RM_C1': -1}):
            self.write(services=bad)
            with self.subTest(services=bad), self.assertRaises(ValueError):
                self.build()
        self.write()
        for bad in (1, 'true', None):
            self.spec['replay_recorded_metering'] = bad
            with self.subTest(flag=bad), self.assertRaisesRegex(ValueError, 'boolean'):
                self.build()


if __name__ == '__main__':
    unittest.main()
