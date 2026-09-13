"""Selected preparation only: real baseline bytes, temporary outputs, no simulator."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from diagnostics import prepare_selected_control_demand as preparation


ROOT = Path(__file__).resolve().parents[1]
SELECTED = ROOT / 'diagnostics/demand_sweep/fw070_urban030/prepared'
TUNING = ROOT / 'diagnostics/contract_candidate_configs_v4/n7_area_beta0.json'
LEGACY = ROOT / 'diagnostics/selected_control_demand/codex_selected_fw070_u030_beta0_r03'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


class SelectedNativeRecording(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.original = read(TUNING)
        self.output = self.directory / 'prepared'

    def tuning(self, enabled):
        document = copy.deepcopy(self.original)
        document['execution'] = {'native_signal_record': enabled}
        path = self.directory / ('tuning_' + str(enabled) + '.json')
        path.write_bytes(preparation.json_bytes(document))
        return path

    def test_default_off_six_tuple_matches_preserved_r03(self):
        # package is planning only. It may name existing evidence but must never
        # rewrite it; this is the actual pre-recording six-value result contract.
        names = ('profile.csv', 'comparison.csv', 'checks.json',
                 'native_internal_inputs.json', 'config.json', 'shared_approach.json')
        before = {name: (LEGACY / name).read_bytes() for name in names}
        profile, rows, report, declaration, config, shared = preparation.package(SELECTED, TUNING, LEGACY)
        with (LEGACY / 'comparison.csv').open(encoding='ascii', newline='') as stream:
            expected_rows = list(csv.DictReader(stream))
        expected_rows = [{key: value if key in ('input_no', 'time_int') else float(value)
                          for key, value in row.items()} for row in expected_rows]
        self.assertEqual((profile, rows, report, declaration, config, shared),
                         (before['profile.csv'].decode('ascii'), expected_rows,
                          read(LEGACY / 'checks.json'), read(LEGACY / 'native_internal_inputs.json'),
                          read(LEGACY / 'config.json'), read(LEGACY / 'shared_approach.json')))
        self.assertEqual(before, {name: (LEGACY / name).read_bytes() for name in names})
        self.assertNotIn('native_signal_record', report)

    def test_explicit_false_never_prepares_recording_or_changes_model(self):
        with patch.object(preparation, 'recording_artifacts', side_effect=AssertionError('OFF called recorder')):
            absent = preparation.package(SELECTED, TUNING, self.output)
            disabled = preparation.package(SELECTED, self.tuning(False), self.output)
        self.assertEqual(len(disabled), 6)
        for index in (0, 1, 3, 5):
            self.assertEqual(absent[index], disabled[index])
        expected = copy.deepcopy(absent[4]); expected['execution'] = {'native_signal_record': False}
        self.assertEqual(expected, disabled[4])
        self.assertNotIn('runtime_network', disabled[2])
        self.assertFalse(self.output.exists())

    def test_nonboolean_enabled_is_rejected_before_recording(self):
        with patch.object(preparation, 'recording_artifacts', side_effect=AssertionError('Invalid flag called recorder')):
            for value in (None, 0, 1, 'true', 'false', [], {}):
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'must be boolean'):
                    preparation.package(SELECTED, self.tuning(value), self.output)
        self.assertFalse(self.output.exists())

    def test_on_retains_demand_declarations_and_only_explicit_config_flag(self):
        absent = preparation.package(SELECTED, TUNING, self.output)
        enabled = preparation.package(SELECTED, self.tuning(True), self.output)
        self.assertEqual(len(enabled), 6)
        for index in (0, 1, 3, 5):
            self.assertEqual(absent[index], enabled[index])
        expected = copy.deepcopy(absent[4]); expected['execution'] = {'native_signal_record': True}
        self.assertEqual(enabled[4], expected)
        report = enabled[2]
        for key in ('network', 'network_sha256', 'profile_sha256', 'selected_demand_sha256',
                    'rows', 'inputs', 'max_abs_error_vph', 'per_input_multiplier', 'config_changed_paths'):
            self.assertEqual(report[key], absent[2][key], key)
        self.assertEqual(report['config_changed_paths'], ['urban.native_internal_inputs', 'urban.shared_approach'])
        self.assertFalse(self.output.exists(), 'Plan unexpectedly wrote recording files')

    def test_actual_cli_writes_144_groups_43_assets_and_truthful_dual_sha(self):
        from evaluation.controllers.network_provenance import validate_recording_bytes, validate_recording_proof

        tuning = self.tuning(True)
        process = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(Path(preparation.__file__).resolve()),
                                  '--selected-prepared', str(SELECTED), '--tuning', str(tuning),
                                  '--output', str(self.output)], cwd=ROOT, capture_output=True, text=True,
                                 encoding='utf-8', check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = read(self.output / 'checks.json')
        self.assertEqual(json.loads(process.stdout), report)
        proof_ref = report['network_recording_proof']
        proof_path = Path(proof_ref['path']); proof = read(proof_path)
        self.assertEqual(digest(proof_path.read_bytes()), proof_ref['sha256'])
        source_path = Path(report['network']); target_path = Path(report['runtime_network'])
        source_bytes = source_path.read_bytes(); target_bytes = target_path.read_bytes()
        self.assertEqual(source_path.name, 'baseline.inpx')
        self.assertEqual(target_path, self.output / 'native_recording' / 'baseline.inpx')
        self.assertEqual(proof['source_network'], {'path': str(source_path), 'sha256': digest(source_bytes)})
        self.assertEqual(proof['recorded_network'], {'path': str(target_path), 'sha256': digest(target_bytes)})
        self.assertEqual(report['network_sha256'], digest(source_bytes))
        self.assertEqual(report['runtime_network_sha256'], digest(target_bytes))
        self.assertNotEqual(digest(source_bytes), digest(target_bytes))
        groups = {int(sc): set(sgs) for sc, sgs in proof['groups'].items()}
        self.assertEqual(len(groups), 25)
        self.assertEqual(sum(map(len, groups.values())), 144)
        meters = set(range(9101, 9109))
        self.assertEqual({sc: groups[sc] for sc in meters}, {sc: {1} for sc in meters})
        self.assertEqual(len(set(groups) - meters), 17)
        self.assertTrue(all(sgs == set(range(1, 9)) for sc, sgs in groups.items() if sc not in meters))
        # This helper validates the full recording-only byte contract, not an
        # independently normalized geometry that could miss other XML changes.
        self.assertIsNone(validate_recording_bytes(source_bytes, target_bytes, proof['groups']))
        self.assertEqual(validate_recording_proof(proof), digest(source_bytes))
        original = ET.fromstring(source_bytes)
        sig_names = {sc.attrib['supplyFile2'][6:]
                     for sc in original.findall('./signalControllers/signalController') if sc.get('supplyFile2')}
        self.assertEqual(len(sig_names), 42)
        image_names = {value[6:] for node in original.iter('backgroundImage')
                       for value in node.attrib.values() if value.startswith('#data#')}
        self.assertEqual(image_names, {'개포동 Test-bed.jpg'})
        self.assertEqual({p.name for p in target_path.parent.iterdir()},
                         sig_names | image_names | {'baseline.inpx'})
        for name in sorted(sig_names | image_names):
            old, new = source_path.parent / name, target_path.parent / name
            self.assertEqual(old.read_bytes(), new.read_bytes(), name)
            self.assertEqual(report['source_sha256'][str(old)], digest(old.read_bytes()))
            self.assertEqual(report['generated_sha256'][str(new)], digest(new.read_bytes()))
        for name, expected in report['generated_sha256'].items():
            path = Path(name)
            self.assertTrue(path.is_relative_to(self.output))
            self.assertEqual(digest(path.read_bytes()), expected, name)
        self.assertEqual(source_path.read_bytes(), source_bytes)

    def test_asset_traversal_is_rejected_without_writing(self):
        _, _, report = preparation.convert(SELECTED)
        source = Path(report['network']).read_bytes()
        tree = ET.fromstring(source)
        node = next(sc for sc in tree.findall('./signalControllers/signalController') if sc.get('supplyFile2'))
        old = node.attrib['supplyFile2'].encode('utf-8')
        # XML replacements are confined to this synthetic local copy. The real
        # baseline and all native assets remain read-only.
        for bad in ('#data#../outside.sig', '#data#..\\outside.sig'):
            with self.subTest(reference=bad):
                altered = source.replace(old, bad.encode('ascii'), 1)
                local = self.directory / 'baseline.inpx'; local.write_bytes(altered)
                evidence = dict(report, network=str(local), network_sha256=digest(altered),
                                source_sha256={}, generated_sha256={})
                with self.assertRaisesRegex(ValueError, 'sibling basename'):
                    preparation.recording_artifacts(evidence, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
