"""C1, C7, C8, C9, C12 generators: byte-reproducible outputs and exactly the planned differences."""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import n31_fixtures as fx
import contract_fixtures as cf
import copy_b110
import make_config_n31
import make_plant_n31
import make_reference_config
from evaluation.controllers import obs150_contract as oc

sys.path.insert(0, str(fx.N31D / 'port_profile_v2'))
import extract_port_profile as epp  # noqa: E402


def pinned_paths(node):
    """Repo-relative paths of every {path, sha256} pin in a document."""
    if isinstance(node, dict):
        if isinstance(node.get('path'), str) and isinstance(node.get('sha256'), str) \
                and not os.path.isabs(node['path']):
            yield node['path'].replace('\\', '/')
        for value in node.values():
            yield from pinned_paths(value)
    elif isinstance(node, list):
        for value in node:
            yield from pinned_paths(value)


class CopyAndReferenceTests(unittest.TestCase):

    def test_c1_copies(self):
        checks = copy_b110.check()
        self.assertEqual(checks['geometry_profile'],
                         'diagnostics/demand_sweep/ramp_dsd_20260916_v2/controller_response_v1/geometry_profile.json')
        receipt = json.loads((fx.N31D / 'b110_copy_receipt.json').read_text(encoding='utf-8'))
        for row in receipt['files']:
            self.assertEqual(fx.sha256(fx.ROOT / row['path']), row['sha256'])

    @unittest.skipUnless(shutil.which('git') and (fx.ROOT / '.git').exists(), 'needs the git worktree')
    def test_pinned_inputs_are_byte_exact_in_git(self):
        """Every sha-pinned WP-C input is -text in git (core.autocrlf=true on this PC).

        The C1 copies are CRLF: with text unspecified, git add stores them LF and a
        checkout with another eol setting breaks the plant, freeze and receipt pins.
        """
        documents = [fx.N31D / 'b110_copy_receipt.json', make_reference_config.OUT, make_plant_n31.OUT]
        pinned = sorted({p for doc in documents if doc.is_file()
                         for p in pinned_paths(json.loads(doc.read_text(encoding='utf-8')))})
        self.assertTrue(set(copy_b110.FILES) <= set(pinned))
        out = subprocess.run(['git', 'check-attr', 'text', '--', *pinned], cwd=fx.ROOT, capture_output=True,
                             text=True, check=True).stdout.splitlines()
        self.assertEqual(len(out), len(pinned))
        self.assertEqual([line for line in out if not line.endswith(': text: unset')], [])

    def test_c7_reference_config(self):
        data = (json.dumps(make_reference_config.build(), indent=2, ensure_ascii=False) + '\n').encode('utf-8')
        self.assertEqual(make_reference_config.OUT.read_bytes(), data)
        reference = json.loads(data)
        boundary = fx.load_json(fx.ROOT / make_reference_config.BOUNDARY)
        freeway = reference['freeway']
        for key in make_reference_config.TRANSPORT_KEYS:
            self.assertIn(key, freeway)
        for key in make_reference_config.LANE_GROUP_KEYS:
            self.assertNotIn(key, freeway)
        self.assertEqual({k: v for k, v in freeway.items()
                          if k not in make_reference_config.TRANSPORT_KEYS + make_reference_config.VSL_KEYS},
                         boundary['freeway'])
        # Branch VSL model keys (d80faf9) with the N1F stage-2 L2 law (user decision 2026-10-01); sign cells re-derived here.
        self.assertEqual(freeway['vsl_fd_response'], {'FW_E': {'law': 'carlson', 'A': 1.33, 'E': 0.87, 'alpha': 0.0, 'speed_scale': {'form': 'cubic_lagrange', 'levels': {'80': 0.7225223093088844, '90': 0.8119772280655296, '100': 0.9006844904146349}, 'maximum': 110.0}}})
        self.assertEqual(freeway['component_vsl_transport'],
                         {'FW_E': {'sign_cells': [0, 3, 5, 8, 14, 18, 26, 28], 'initial_command': 110, 'ramp_command': 110}})
        self.assertIn('N1F stage-2 L2', freeway['_vsl_model_note'])
        self.assertIn('4091d6e140f1cf1b29ae51e7863eb1d41d0d8169756ae28987deda69b2516f6c', freeway['_vsl_model_note'])
        self.assertIn('81/91/101/110', freeway['_vsl_model_note'])
        self.assertEqual(make_reference_config.sign_cells(), make_reference_config.EXPECTED_SIGN_CELLS)
        # Outside freeway the reference is the boundary config except the action set (max 110 kept).
        expected = copy.deepcopy({k: v for k, v in boundary.items() if k != 'freeway'})
        self.assertEqual(expected['config_overrides']['freeway_follower']['vsl_set'], [60.0, 80.0, 110.0])
        expected['config_overrides']['freeway_follower']['vsl_set'] = [80.0, 90.0, 100.0, 110.0]
        self.assertEqual({k: v for k, v in reference.items() if k not in ('freeway', '_n31_note')}, expected)
        self.assertEqual(freeway['physical_ramp_capacity_vph']['RM_C10482'], 3600.0)
        self.assertEqual(freeway['component_boundary'], {'source': 'admitted_interface', 'terminal': 'open_exit'})
        self.assertEqual(reference['config_overrides']['freeway_follower']['vsl_set'], [80.0, 90.0, 100.0, 110.0])
        self.assertEqual(make_reference_config.VSL_SET, make_config_n31.VSL_SET)


class PlantManifestTests(unittest.TestCase):

    def test_missing_owner_inputs_are_listed(self):
        pending = [rel for rel in (make_plant_n31.SOURCES['network'], make_plant_n31.SOURCES['runner_config'],
                                   make_plant_n31.SOURCES['sig_manifest'], make_plant_n31.DETECTORS,
                                   make_plant_n31.BASE_CONFIG) if not (fx.ROOT / rel).is_file()]
        if not pending:
            self.skipTest('all owner inputs exist; see test_real_manifest')
        with self.assertRaises(FileNotFoundError) as caught:
            make_plant_n31.build()
        for rel in pending:
            self.assertIn(rel, str(caught.exception))

    def test_sandbox_manifest(self):
        with fx.V2Sandbox() as sandbox:
            document = sandbox.document
            oc.validate_plant_manifest_v2(document)
            self.assertEqual(document['sources']['network']['sha256'], make_plant_n31.NETWORK_SHA256)
            self.assertEqual(document['source_boundary'], oc.SOURCE_BOUNDARY_BLOCK)
            self.assertEqual((document['fw_e_terminal'], document['lane_groups'], document['vsl_command_space']),
                             ('component', False, 'parent_21'))
            self.assertIn('NOT_QUALIFIED', document['qualification'])
            for key in ('geometry', 'refined_partition', 'reference_config', 'parameters', 'port_profile',
                        'reference_protocol'):
                self.assertEqual(document['sources'][key]['path'], make_plant_n31.SOURCES[key])

    def test_wrong_network_is_refused(self):
        with fx.V2Sandbox() as sandbox:
            sources = {k: v['path'] for k, v in sandbox.document['sources'].items()}
            sources['network'] = 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/source_dsd/baseline.inpx'
            with self.assertRaises(ValueError):
                make_plant_n31.build(fx.ROOT, sources=sources, detectors=sandbox.document['observation']['detectors']['path'],
                                     base_config=fx.rel(sandbox.dir / 'config_n31_v2.base.json'),
                                     membership_prefix=fx.rel(sandbox.dir) + '/')

    @unittest.skipUnless((make_plant_n31.OUT).is_file(), 'plant_n31_v2.json not generated yet (needs WP-E/B2 inputs)')
    def test_real_manifest(self):
        self.assertEqual(make_plant_n31.OUT.read_bytes(), make_plant_n31.dumps(make_plant_n31.build()))


C9_PATHS = {'freeway.lane_plant', 'freeway.segment_params', 'urban.capacity.head_observation.sample_interval_sec',
            'config_overrides.freeway_follower.vsl_set', 'config_overrides.network.v_free',
            '_canonical.fd_fit_20260828.values.v_free', 'execution.native_signal_record',
            'execution.signal_vbs_config', 'observation.physical_branch_projection.source.network', '_n31_note',
            'calibration_override.prediction.local_ramp_arrival_forecast.queue_drain_horizon_sec_by_ramp',
            'calibration_override.prediction.local_ramp_arrival_forecast.max_vph_by_ramp',
            'calibration_override.prediction.local_ramp_arrival_forecast.strict_ramp_keys',
            'urban.beta.source', 'urban.ramp.offramp_direct_share', 'actuation.vsl_command_distribution'}
# Differences replaced as a whole subtree: collapse their leaves onto the root.
C9_SUBTREES = ('observation.physical_branch_projection.source.network',
               'calibration_override.prediction.local_ramp_arrival_forecast.queue_drain_horizon_sec_by_ramp',
               'calibration_override.prediction.local_ramp_arrival_forecast.max_vph_by_ramp',
               'urban.ramp.offramp_direct_share', 'actuation.vsl_command_distribution')
METERS = {'RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644', 'RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484'}


def flatten(node, trail=''):
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(flatten(v, trail + '.' + k if trail else k))
        if not node:
            out[trail] = {}
    else:
        out[trail] = node
    return out


class TuningTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.base = fx.load_json(fx.OBS1)
        cls.tuning = make_config_n31.apply(cls.base, require_repinned=False)

    def test_exactly_the_c9_differences(self):
        before, after = flatten(self.base), flatten(self.tuning)
        changed = {k for k in set(before) | set(after) if before.get(k, '<absent>') != after.get(k, '<absent>')}
        roots = {next((root for root in C9_SUBTREES if k.startswith(root + '.') or k == root), k) for k in changed}
        self.assertEqual(roots, C9_PATHS)

    def test_ramp_forecast_is_keyed_by_meter(self):
        """Runtime ramps are the mapping's RM_C meters; the legacy group keys must not survive."""
        forecast = self.tuning['calibration_override']['prediction']['local_ramp_arrival_forecast']
        mapping = fx.load_json(fx.ROOT / self.tuning['mapping_json'])
        self.assertEqual({m['id'] for m in mapping['ramp_meters']}, METERS)
        for key in ('queue_drain_horizon_sec_by_ramp', 'max_vph_by_ramp'):
            self.assertEqual(set(forecast[key]), METERS, key)
            self.assertEqual(forecast[key], make_config_n31.RAMP_FORECAST[key])
        self.assertIs(forecast['strict_ramp_keys'], True)
        stale = copy.deepcopy(self.base)
        stale['calibration_override']['prediction']['local_ramp_arrival_forecast']['max_vph_by_ramp'] = {'RM_C10480': 1.0}
        with self.assertRaisesRegex(ValueError, 'legacy group table'):
            make_config_n31.apply(stale, require_repinned=False)

    def test_beta_source_is_the_pinned_network_routing_table(self):
        """Network v3c3 re-pin (2026-10-01; v3c1 2026-09-28, v3b 2026-09-25): the tuning names the pinned network's
        routing beta, not the 0824 e14 table."""
        self.assertEqual(self.tuning['urban']['beta'], {'measured': True, 'floor': 0.0, 'source': 'routing_v3c3'})
        make_config_n31.check_beta(fx.ROOT)
        document = fx.load_json(fx.ROOT / make_config_n31.BETA_FILE)
        self.assertEqual(document['source'].replace('\\', '/'), make_config_n31.NETWORK)
        self.assertEqual(len(document['beta']), 373)   # v3b 370 (345 before the explicit assignment) + SC104 S_SC106
        with_source = copy.deepcopy(self.base)
        with_source['urban']['beta']['source'] = 'knr'
        with self.assertRaisesRegex(ValueError, 'default source'):
            make_config_n31.apply(with_source, require_repinned=False)

    def test_values(self):
        t = self.tuning
        self.assertEqual(t['freeway']['lane_plant'], make_config_n31.PLANT)
        self.assertEqual(t['freeway']['segment_params'], make_config_n31.SEGMENT_PARAMS)
        self.assertTrue((fx.ROOT / t['freeway']['segment_params']).is_file())
        self.assertNotIn('sample_interval_sec', t['urban']['capacity']['head_observation'])
        self.assertEqual(t['config_overrides']['freeway_follower']['vsl_set'], [80.0, 90.0, 100.0, 110.0])
        self.assertEqual(t['config_overrides']['network']['v_free'], 110.0)
        self.assertIs(t['execution']['native_signal_record'], False)
        self.assertEqual(t['execution']['signal_vbs_config'], make_config_n31.RUNNER_CONFIG)
        self.assertEqual(t['observation']['physical_branch_projection']['source']['network'],
                         {'path': make_config_n31.NETWORK, 'sha256': make_plant_n31.NETWORK_SHA256})
        self.assertEqual(t['freeway']['vsl_zone_heads'], {'FW_E': [0, 5, 10, 15], 'FW_W': [0, 5, 10, 15]})
        self.assertEqual(t['config_overrides']['freeway_follower']['max_vsl_step'], 40.0)
        # the single-value family (user decision 2026-10-01): commands stay 80..110, the CSV writes 81/91/101/110
        self.assertEqual(t['actuation']['vsl_command_distribution'],
                         {'model': 'single_value', 'distribution_by_command': {'80': 81, '90': 91, '100': 101, '110': 110}})
        self.assertNotIn('vsl_command_distribution', make_config_n31.apply(self.base, require_repinned=False,
                                                                           family='distribution')['actuation'])
        with self.assertRaisesRegex(ValueError, 'Unknown VSL family'):
            make_config_n31.apply(self.base, require_repinned=False, family='spread')

    def test_validates_against_a_v2_manifest(self):
        document = cf.manifest_v2()
        document['sources']['runner_config']['path'] = make_config_n31.RUNNER_CONFIG
        oc.validate_tuning_v2(self.tuning, document)
        with self.assertRaises(oc.ObsContractError):
            oc.validate_tuning_v2(self.base, document)

    def test_unrepinned_base_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'fcb349d3 pack'):
            make_config_n31.apply(self.base)
        with self.assertRaises(ValueError):
            make_config_n31.apply({**self.base, 'extends': 'x.json'}, require_repinned=False)

    @unittest.skipUnless((fx.ROOT / make_config_n31.BASE).is_file(), 'WP-E base config not written yet')
    def test_real_config(self):
        if make_config_n31.OUT.is_file():
            self.assertEqual(make_config_n31.OUT.read_bytes(), make_config_n31.dumps(make_config_n31.build()))
        else:
            make_config_n31.build()


class VslFamilyTests(unittest.TestCase):
    """V-11 / U5-a (repin plan 2026-10-01): both VSL families are complete, consistent generator outputs. The tree holds
    single_value; the distribution family is built as an overlay outside the tree by the generators' --vsl-family /
    --out-root options, twice (byte-identical), and passes the V-9 family check of the runtime."""

    FAMILY = (('diagnostics/sdmpc_n31_20260924/repin_scenario_v2.py', 'runner-family', '--vsl-family', 'distribution'),
              ('scripts/build_obs150_detectors.py',),
              ('diagnostics/sdmpc_n31_20260924/make_reference_config.py', '--vsl-family', 'distribution'),
              ('diagnostics/sdmpc_n31_20260924/make_plant_n31.py', '--vsl-family', 'distribution'),
              ('diagnostics/sdmpc_n31_20260924/make_config_n31.py', '--vsl-family', 'distribution'))

    @classmethod
    def build_family(cls, folder):
        for argv in cls.FAMILY:
            done = subprocess.run([sys.executable, '-B', *argv, '--out-root', str(folder)], cwd=fx.ROOT, capture_output=True,
                                  text=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONUTF8='1'))
            if done.returncode:
                raise AssertionError(' '.join(argv) + ' failed:\n' + done.stdout[-2000:] + done.stderr[-4000:])
        return {p.relative_to(folder).as_posix(): fx.sha256(p) for p in sorted(Path(folder).rglob('*')) if p.is_file()}

    def test_live_tree_is_the_single_value_family(self):
        from evaluation.controllers import vsl_command_distribution as vcd
        plant = fx.load_json(make_plant_n31.OUT)
        family = vcd.check_family_files(fx.load_json(make_config_n31.OUT),
                                        fx.ROOT / plant['sources']['reference_config']['path'],
                                        fx.ROOT / plant['sources']['runner_config']['path'])
        self.assertEqual(family, {'family': 'single_value', 'commands': [80.0, 90.0, 100.0, 110.0],
                                  'written': [81.0, 91.0, 101.0, 110.0], 'speed_scale_roads': ['FW_E']})
        self.assertEqual((make_reference_config.VSL_FAMILY, make_plant_n31.VSL_FAMILY, make_config_n31.VSL_FAMILY),
                         ('single_value',) * 3)

    def test_distribution_family_overlay(self):
        import tempfile
        from evaluation.controllers import vsl_command_distribution as vcd
        with tempfile.TemporaryDirectory(prefix='n31_family_a_') as a, tempfile.TemporaryDirectory(prefix='n31_family_b_') as b:
            first, second = self.build_family(Path(a)), self.build_family(Path(b))
            self.assertEqual(first, second)                      # deterministic
            n31d = 'diagnostics/sdmpc_n31_20260924/'
            self.assertEqual(sorted(first), sorted(n31d + rel for rel in (
                'config_n31_v2.json', 'obs150/obs150_detectors_v2.csv', 'obs150/obs150_detectors_v2.manifest.json',
                'plant_n31_v2.json', 'reference_config_n31_v2.json', 'scenario/lane_native_b110.vbs')))
            self.assertEqual(first[n31d + 'obs150/obs150_detectors_v2.csv'], fx.sha256(fx.ROOT / make_plant_n31.DETECTORS))
            folder = Path(a)
            tuning = fx.load_json(folder / n31d / 'config_n31_v2.json')
            plant = fx.load_json(folder / n31d / 'plant_n31_v2.json')
            reference = fx.load_json(folder / n31d / 'reference_config_n31_v2.json')
            self.assertEqual(reference['freeway']['vsl_fd_response'],
                             {'FW_E': {'law': 'carlson', 'A': 0.94, 'E': 1.44, 'alpha': 0.0}})
            self.assertNotIn('vsl_command_distribution', tuning['actuation'])
            for key in ('reference_config', 'runner_config'):            # the plant pins the overlay files, repo-relative
                pin = plant['sources'][key]
                self.assertEqual(pin['sha256'], fx.sha256(folder / pin['path']))
                self.assertNotEqual(pin['sha256'], fx.sha256(fx.ROOT / pin['path']))
            sidecar = fx.load_json(folder / n31d / 'obs150/obs150_detectors_v2.manifest.json')
            self.assertEqual(sidecar['sources']['runner_config'], plant['sources']['runner_config'])
            family = vcd.check_family_files(tuning, folder / plant['sources']['reference_config']['path'],
                                            folder / plant['sources']['runner_config']['path'])
            self.assertEqual(family, {'family': 'distribution', 'commands': [80.0, 90.0, 100.0, 110.0],
                                      'written': [80.0, 90.0, 100.0, 110.0], 'speed_scale_roads': []})
            # mixing the families refuses (V-9): the live map with the L1 overlay, the overlay tuning with the live plant
            mixed = copy.deepcopy(tuning)
            mixed['actuation']['vsl_command_distribution'] = copy.deepcopy(make_config_n31.VSL_COMMAND_DISTRIBUTION)
            with self.assertRaises(ValueError):
                vcd.check_family_files(mixed, folder / plant['sources']['reference_config']['path'],
                                       folder / plant['sources']['runner_config']['path'])
            live = fx.load_json(make_plant_n31.OUT)
            with self.assertRaises(ValueError):
                vcd.check_family_files(tuning, fx.ROOT / live['sources']['reference_config']['path'],
                                       fx.ROOT / live['sources']['runner_config']['path'])

    def test_a_non_live_family_never_writes_into_the_tree(self):
        for argv in self.FAMILY[2:]:
            done = subprocess.run([sys.executable, '-B', *argv], cwd=fx.ROOT, capture_output=True, text=True,
                                  encoding='utf-8', errors='replace')
            self.assertNotEqual(done.returncode, 0, argv)
            self.assertIn('--out-root', done.stdout + done.stderr)
        done = subprocess.run([sys.executable, '-B', *self.FAMILY[0], '--out-root', str(fx.ROOT / 'outputs')], cwd=fx.ROOT,
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
        self.assertIn('REPIN_ERROR runner-family --out-root must lie outside the tree', done.stdout)


class PortProfileTests(unittest.TestCase):

    def test_bracket_resolved_residence(self):
        lengths = {'1': 300.0}
        events = [{'time_s': 100.1, 'vehicle': 7, 'connector': 1, 'kind': 'arrival', 'position_m': 36.0,
                   'speed_kmh': 108.0, 'residence_s': None},
                  {'time_s': 110.1, 'vehicle': 7, 'connector': 1, 'kind': 'departure', 'position_m': 264.0,
                   'speed_kmh': 108.0, 'residence_s': 10.0}]
        row = epp.travel(events, lengths, 5)['1']
        # entry 1.2 s before the first row, exit 1.2 s after the last: 5 + 1.2 + 1.2 = 7.4 s
        self.assertAlmostEqual(row['travel_speed_kmh_interp'], 300.0 * 3.6 / 7.4, places=12)
        self.assertAlmostEqual(row['travel_speed_kmh_quantized'], 300.0 * 3.6 / 10.0, places=12)
        stopped = copy.deepcopy(events)
        stopped[1]['speed_kmh'] = 0.0
        self.assertAlmostEqual(epp.travel(stopped, lengths, 5)['1']['travel_speed_kmh_interp'],
                               300.0 * 3.6 / (5.0 + 1.2 + 5.0), places=12)

    def test_training_window_and_missing_samples(self):
        lengths = {'1': 300.0, '2': 100.0}
        events = [{'time_s': 905.1, 'vehicle': 1, 'connector': 1, 'kind': 'departure', 'position_m': 290.0,
                   'speed_kmh': 90.0, 'residence_s': 10.0}]
        with self.assertRaises(ValueError):
            epp.travel(events, lengths, 5)

    def test_pinned_profile(self):
        document = fx.load_json(epp.OUT_PROFILE)
        travel = fx.load_json(epp.OUT_TRAVEL)
        self.assertEqual(document['provenance']['selection'], 'interp')
        self.assertEqual(document['travel_speed_kmh'],
                         {c: r['travel_speed_kmh_interp'] for c, r in travel['connectors'].items()})
        component = fx.component()
        ports = {str(r['connector']) for r in (*component.ramps.values(), *component.offramps.values())}
        self.assertEqual(set(document['travel_speed_kmh']), ports)
        self.assertIs(document['occupancy_lane_loss'], False)
        self.assertEqual(travel['source']['fzp']['sha256'], epp.FZP_SHA256)

    @unittest.skipUnless(epp.RUN.is_dir() and os.environ.get('N31_SLOW') == '1',
                         'set N31_SLOW=1 to re-derive C12 from the 1.16 GB FZP')
    def test_regenerates_bytes(self):
        events, travel_doc, document = epp.build('interp')
        travel_doc['source'].pop('elapsed_sec_not_benchmark', None)
        self.assertEqual(epp.OUT_PROFILE.read_bytes(), epp.dumps(document))
        self.assertEqual(epp.OUT_TRAVEL.read_bytes(), epp.dumps(travel_doc))
        self.assertEqual(epp.OUT_EVENTS.read_bytes(), epp.events_bytes(events))


if __name__ == '__main__':
    unittest.main()
