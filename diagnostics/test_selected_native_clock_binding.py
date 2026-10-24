"""Native plan/config preparation and diagnostic commands, with no simulator."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

from diagnostics import prepare_selected_control_demand as prep
from diagnostics.test_native_vbs_clock import source_plan, ROOT
from diagnostics.test_native_runtime_reference import Action
from evaluation.controllers import diagnostic_profile, diagnostic_signal_profile, signal_group_plan as plans
from scripts.derive_signal_group_actuation_plan_mainline_20260825 import render_vbs

BASE = ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs'
SELECTED = ROOT / 'diagnostics/demand_sweep/fw070_urban030/prepared'
TUNING = ROOT / 'diagnostics/contract_candidate_configs_v4/n7_area_beta0.json'


class SelectedNativeClockBindingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.raw, self.audit = source_plan()
        self.plan = self.directory / 'native.json'
        self.plan.write_bytes(prep.json_bytes(self.raw))
        self.config = self.directory / 'native_config.vbs'
        self.config.write_bytes(BASE.read_bytes())
        self.sibling = self.directory / 'native_config_sgplan.vbs'
        self.sibling.write_text(render_vbs(self.raw, prep.sha(self.plan)), encoding='utf-8', newline='\n')
        self.tuning = {'urban': {'plan': {'actuation_plan_json': str(self.plan)}},
                       'execution': {'signal_vbs_config': str(self.config)}}

    def test_default_is_exact_base_and_selected_pair_is_fully_pinned(self):
        self.assertEqual(prep.selected_signal_config({}), (BASE, {}))
        path, pins = prep.selected_signal_config(self.tuning)
        self.assertEqual(path, self.config.resolve())
        self.assertEqual(self.config.read_bytes(), BASE.read_bytes())
        self.assertEqual(set(pins), {str(path) for path in (BASE, self.config, self.sibling, self.plan,
                         ROOT / 'scripts/derive_signal_group_actuation_plan_mainline_20260825.py')})
        for path, digest in pins.items(): self.assertEqual(digest, prep.sha(path))

    def test_missing_pair_changed_base_and_changed_sibling_are_rejected(self):
        for key in ('urban', 'execution'):
            bad = deepcopy(self.tuning)
            bad.pop(key)
            with self.assertRaisesRegex(ValueError, 'requires both JSON'):
                prep.selected_signal_config(bad)
        self.config.write_bytes(BASE.read_bytes() + b"\n' changed base\n")
        with self.assertRaisesRegex(ValueError, 'preserve the base VBS'):
            prep.selected_signal_config(self.tuning)
        self.config.write_bytes(BASE.read_bytes())
        original = self.sibling.read_bytes()
        self.sibling.write_bytes(original + b"\n' changed sibling\n")
        with self.assertRaisesRegex(ValueError, 'sibling differs'):
            prep.selected_signal_config(self.tuning)
        self.sibling.unlink()
        with self.assertRaises(FileNotFoundError): prep.selected_signal_config(self.tuning)
        self.sibling.write_bytes(original)
        bad = deepcopy(self.raw)
        bad['controllers']['16'].pop('native_clock_basis')
        self.plan.write_bytes(prep.json_bytes(bad))
        with self.assertRaisesRegex(ValueError, 'cover every controlled signal'):
            prep.selected_signal_config(self.tuning)

    def test_recording_artifacts_use_selected_config_and_sibling(self):
        network = ROOT / self.audit['network']
        report = {'network': str(network), 'network_sha256': prep.sha(network),
                  'vbs_config': str(self.config), 'source_sha256': {}, 'generated_sha256': {}}
        files = prep.recording_artifacts(report, self.directory / 'prepared')
        self.assertEqual(report['source_sha256'][str(self.config)], prep.sha(self.config))
        self.assertEqual(report['source_sha256'][str(self.sibling)], prep.sha(self.sibling))
        self.assertNotIn(str(BASE), report['source_sha256'])
        proof = json.loads(files[Path(report['network_recording_proof']['path'])])
        self.assertEqual(len(proof['groups']), 25)
        self.assertEqual(sum(map(len, proof['groups'].values())), 144)
        self.assertFalse((self.directory / 'prepared').exists(), 'Planning wrote generated files')

    def test_actual_powershell_plan_uses_proof_vbs_config_without_execute(self):
        tuning = json.loads(TUNING.read_text(encoding='utf-8'))
        tuning.setdefault('urban', {})['plan'] = self.tuning['urban']['plan']
        tuning.setdefault('execution', {}).update(self.tuning['execution'])
        path = self.directory / 'tuning.json'
        path.write_bytes(prep.json_bytes(tuning))
        name = 'native_binding_plan_' + self.directory.name.replace('-', '_')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(ROOT / 'diagnostics/run_selected_control_trial.ps1'),
            '-SelectedPrepared', str(SELECTED), '-Tuning', str(path), '-Name', name,
            '-Controller', 'no-control', '-DemandDirectory', str(self.directory / 'planned')],
            cwd=ROOT, env=dict(os.environ), capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        proof = json.loads(result.stdout)
        self.assertFalse(proof['execute'])
        self.assertEqual(proof['arguments']['VbsConfig'], str(self.config))
        self.assertEqual(proof['selected_demand']['vbs_config'], str(self.config))
        self.assertFalse((self.directory / 'planned').exists())
        self.assertFalse((ROOT / 'evaluation/runs' / name).exists())

    def build_signal(self, native=True, changes=None):
        raw = deepcopy(self.raw)
        if not native:
            for node in raw['controllers'].values(): node.pop('native_clock_basis')
        greens = {f'SC{sc}_{phase}': value for sc, node in raw['controllers'].items()
                  for phase, value in node['axis_green_sec'].items()}
        source = self.directory / 'action.json'
        source.write_bytes(prep.json_bytes({'green_times': greens}))
        profile = {'green_action_json': str(source), 'green_action_sha256': prep.sha(source),
                   'plan_content_sha256': hashlib.sha256(json.dumps(raw, ensure_ascii=False, sort_keys=True,
                        separators=(',', ':')).encode()).hexdigest(),
                   'base_writer_offsets_sec': {'SC7': 119., 'SC16': 149.},
                   'relative_offset_sec': {'SC7': 5., 'SC16': 5.},
                   'green_delta_sec': changes or {}}
        tuning = {'diagnostic': {'signal_profile': profile, 'physical_meter_green_sec': {'RM_C10639': 9}}}
        cfg = SimpleNamespace(network=SimpleNamespace(freeway_links=['FW_E', 'FW_W']))
        factory = SimpleNamespace(uncontrolled=lambda cfg: Action(green_times={}, offsets={}, vsl={},
                                      ramp_metering={}, diagnostics={}))
        action = diagnostic_signal_profile.build_control(cfg, factory, tuning, raw, ROOT)
        return raw, cfg, action, tuning

    def test_native_signal_cycles_and_g9_physical_meter_override_survive(self):
        raw, cfg, action, tuning = self.build_signal(changes={'SC7_p1': 6., 'SC16_p1': -2., 'SC16_p2': 2.})
        self.assertEqual(action.offsets['SC7'], 4.)
        self.assertEqual(action.offsets['SC16'], 4.)
        for sc, expected in (('7', 120.), ('16', 150.)):
            node = plans.node_plan_from_json(raw['controllers'][sc])
            greens = {p: action.green_times[f'SC{sc}_{p}'] for p in plans.MODEL_PHASES}
            self.assertEqual(plans.node_cycle_sec(node, greens, 3., 0.), expected)
        self.assertEqual(action.green_times['SC7_p1'], 73.)
        mapping = json.loads((ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json').read_text(encoding='utf-8'))
        cfg.network.ramps = sorted({row['model_ramp_key'] for row in mapping['ramp_meters']})
        actuation = json.loads(TUNING.read_text(encoding='utf-8'))['actuation']
        fixed = diagnostic_signal_profile.fixed_actuation(actuation, tuning)
        rows = diagnostic_profile.physical_meter_actions(action, cfg, fixed, mapping)
        self.assertEqual(rows['RM_C10639']['green_sec'], 9.)
        self.assertEqual(rows['RM_C10639']['rate_vph'], 810.)
        self.assertEqual(sum(row['green_sec'] == 10. for row in rows.values()), 7)
        self.assertEqual(fixed['real_world_signal_control']['offset_writer'], 'test_only')
        self.assertEqual(actuation['real_world_ramp_metering']['allocation'], 'measured_table')

    def test_absent_native_basis_keeps_legacy_cycles_and_default_meter_mode(self):
        raw, cfg, action, tuning = self.build_signal(native=False)
        self.assertEqual(action.offsets['SC7'], 124.)  # legacy cycle 190
        self.assertEqual(action.offsets['SC16'], 38.)  # legacy cycle 116
        for sc, expected in (('7', 190.), ('16', 116.)):
            node = plans.node_plan_from_json(raw['controllers'][sc])
            greens = {p: action.green_times[f'SC{sc}_{p}'] for p in plans.MODEL_PHASES}
            self.assertEqual(plans.node_cycle_sec(node, greens, 3., 0.), expected)
        actuation = json.loads(TUNING.read_text(encoding='utf-8'))['actuation']
        fixed = diagnostic_signal_profile.fixed_actuation(actuation)
        expected = diagnostic_profile.fixed_actuation(actuation)
        expected['real_world_signal_control'].update(enabled=True, offset_writer='test_only')
        self.assertEqual(fixed, expected)
        self.assertEqual(fixed['real_world_ramp_metering']['allocation'], 'proportional')
        self.assertIsNone(diagnostic_profile.physical_meter_actions(action, cfg, fixed, {}))


if __name__ == '__main__':
    unittest.main()
