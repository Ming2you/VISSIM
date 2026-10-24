"""WP-B1 B7: signal_head_observation (SHO) consuming physical-head-window/v2.

The v1 consumer is covered by diagnostics/test_signal_observation_window_patch.py
and friends (unchanged). Here: the v2 branch of settings (SHO:32-53), of
validate_provenance (SHO:56-86 + validate_provenance_v2) and of install
(SHO:157-163), end to end with a real provenance manifest, plant manifest and
detector table on disk.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c as oc  # noqa: E402
from evaluation.controllers import signal_head_observation as sho  # noqa: E402

OPTIONS = {'enabled': True, 'min_green_sec': 30.0, 'min_crossings': 5.0}
PLAN = {'controllers': {'1004': {'phase_signal_groups': {'p1': ['8']}}}}


def evidence(path):
    return {'path': str(path), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def distribute(cfg, groups, estimates, caps):
    if ('66', 'p1') in estimates:
        caps['through'] = estimates['66', 'p1']
        return 1
    return 0


class Fixture:
    """A v2 run on disk: network, tuning, detector table, plant manifest, provenance and the state."""

    def __init__(self, directory, *, name='sdmpc31_v2_s31', gt=()):
        d = Path(directory)
        self.network = d / 'network.inpx'
        self.network.write_text('<network><signalHeads><signalHead no="1" lane="66 1" pos="100" sg="1004 8" '
                                'allVehTypes="true"/></signalHeads></network>', encoding='utf-8')
        self.tuning = d / 'tuning.json'
        self.tuning.write_text(json.dumps({'urban': {'capacity': {'head_observation': OPTIONS}}}))
        self.detectors = d / 'obs150_detectors_v2.csv'
        rows = fx.detector_rows()
        self.detectors.write_bytes(oc.format_detector_csv(rows))
        detectors = {**evidence(self.detectors), 'rows': len(rows)}
        document = fx.manifest_v2()
        document['observation']['detectors']['sha256'] = detectors['sha256']
        self.plant = d / 'plant_n31_v2.json'
        self.plant.write_text(json.dumps(document))
        self.freeze = d / 'FREEZE.json'           # a launch runs from a frozen tree (CONTRACT 1.4)
        self.freeze.write_text(json.dumps({'tree': 'frozen'}))
        env = {**oc.expected_runner_env(document, str(self.detectors)), 'RW_PYTHON': 'python'}
        gt = [list(w) for w in gt]
        if gt:
            env['RW_OBS150_GT'] = oc.format_gt_windows(gt)
        self.manifest = {
            'run_id': 'test-run', 'name': name, 'files': {'tuning': evidence(self.tuning), 'network': evidence(self.network)},
            'env': env,
            'signal_observation': {'config_key': 'urban.capacity.head_observation', 'options': OPTIONS,
                                   'config_chain': [evidence(self.tuning)], 'lane_plant': evidence(self.plant)},
            'observation': {'schema': oc.PROVENANCE_OBSERVATION_SCHEMA, 'cadence': oc.OBSERVATION_CADENCE,
                            'plant_manifest': evidence(self.plant), 'detectors': detectors,
                            'expected_simres': 10, 'vehrec_interval_sec': 5, 'ground_truth_windows': gt,
                            'freeze': evidence(self.freeze)}}
        self.provenance = d / 'manifest.json'
        self.write_manifest()
        obs = fx.raw_obs(900)
        obs.update(run_id='test-run', ground_truth_windows=gt,
                   detector_config={'path': str(self.detectors), 'sha256': detectors['sha256'], 'rows': len(rows)})
        self.raw = {'network_path': str(self.network), 'sim_sec': 900,
                    'run_provenance': {'run_id': 'test-run', 'manifest_path': str(self.provenance)},
                    'local_observation': {'scan_ok': True, 'signal_observation_window': self.window(750, 900, 10),
                                          'link_departures_window': {'403': 0},
                                          'far_measurement': {'interval_sec': 150, 'freeway_exit_count': 5,
                                                              'freeway_exit_count_provenance': 'conservation_v2'}},
                    oc.RAW_STATE_KEY: obs}
        self.cfg = types.SimpleNamespace(network=types.SimpleNamespace(
            movement_capacity_veh_h=200, movement_capacity_by_movement_veh_h={'through': 200.0}))

    def write_manifest(self):
        self.provenance.write_text(json.dumps(self.manifest))

    def window(self, start, end, count, *, complete=True, green=45):
        head = {'head_id': '1', 'link': '66', 'lane': 1, 'position_m': 100.0, 'sc': '1004', 'sg': '8',
                'crossings': count, 'qualified_crossings': count, 'green_sec': green, 'native_sec': 150,
                'controlled_sec': 0, 'unverified_sec': 0, 'boundary_ambiguous': 0}
        return {'schema': oc.HEAD_WINDOW_SCHEMA_V2, 'config_sha256': self.manifest['files']['tuning']['sha256'],
                'detector_config_sha256': self.manifest['observation']['detectors']['sha256'],
                'start_sec': start, 'end_sec': end, 'cadence_sec': 150, 'exposure_method': oc.HEAD_EXPOSURE_METHOD_V2,
                'clock_complete': complete, 'heads': [head], 'bypass_link_exits': {'403': 0}}

    def at(self, end, count, **keywords):
        self.raw['sim_sec'] = end
        self.raw[oc.RAW_STATE_KEY]['sim_sec'] = end
        self.raw['local_observation']['signal_observation_window'] = self.window(end - 150, end, count, **keywords)

    def install(self, previous=None, options=OPTIONS):
        return sho.install(self.cfg, self.raw, previous, {'through': 200.0}, PLAN, distribute, options)


def save_previous(path, metadata):
    path.write_text(json.dumps({'metadata': {**metadata, 'sim_sec': metadata['head_observation_snapshot_sec']},
                                'run_provenance': {'run_id': 'test-run'}}))


class ShoV2(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='obs150_sho_v2_')
        self.addCleanup(self.directory.cleanup)
        self.fx = Fixture(self.directory.name)

    def test_two_adjacent_v2_windows_update_the_capacity(self):
        untouched = copy.deepcopy(self.fx.raw)
        first = self.fx.install()
        self.assertEqual(self.fx.raw, untouched)
        self.assertEqual((first['head_observation_window_v2'], first['head_observation_waiting_second_window'],
                          first['head_observation_invalid_window']), (1.0, 1.0, 0.0))
        self.assertEqual(self.fx.cfg.network.movement_capacity_by_movement_veh_h['through'], 200.0)
        previous = Path(self.directory.name) / 'previous.json'
        save_previous(previous, first)
        self.fx.at(1050, 20)
        second = self.fx.install(previous)
        self.assertEqual(second['head_observation_groups_updated'], 1.0)
        # min(3600*20/45, 3600*10/45) = 800 veh/h, an achieved lower bound
        self.assertEqual(self.fx.cfg.network.movement_capacity_by_movement_veh_h['through'], 800.0)

    def test_incomplete_clock_is_an_invalid_window(self):
        self.fx.raw['local_observation']['signal_observation_window'] = self.fx.window(750, 900, 10, complete=False)
        result = self.fx.install()
        self.assertEqual((result['head_observation_invalid_window'], result['head_observation_waiting_second_window']),
                         (1.0, 0.0))

    def test_t1_carries_no_window(self):
        self.fx.raw['sim_sec'] = 1
        self.fx.raw[oc.RAW_STATE_KEY]['sim_sec'] = 1
        self.fx.raw['local_observation']['signal_observation_window'] = None
        self.assertEqual(self.fx.install()['head_observation_missing_window'], 1.0)

    def test_ground_truth_windows_need_a_dev_run(self):
        for name, allowed in (('sdmpc31_g1', True), ('sdmpc31_v2_s31', False)):
            with self.subTest(name=name):
                fixture = Fixture(self.directory.name, name=name, gt=[[750, 900]])
                if allowed:
                    fixture.install()
                else:
                    with self.assertRaises(ValueError):
                        fixture.install()

    def test_every_mismatch_is_refused(self):
        def options_with_interval(f):
            return {**OPTIONS, 'sample_interval_sec': 1}

        cases = {
            'sample_interval_sec': lambda f: None,
            'cadence env missing': lambda f: (f.manifest['env'].pop('RW_OBSERVATION_CADENCE'), f.write_manifest()),
            'RW_OBS150_GT without windows': lambda f: (f.manifest['env'].update(RW_OBS150_GT='750:900'),
                                                      f.write_manifest()),
            'detector table changed': lambda f: f.detectors.write_bytes(f.detectors.read_bytes() + b'\n'),
            'plant manifest changed': lambda f: f.plant.write_text(f.plant.read_text() + ' '),
            'lane_plant pin differs': lambda f: (f.manifest['signal_observation']['lane_plant'].update(sha256='0' * 64),
                                                 f.write_manifest()),
            'v1 provenance for a v2 state': lambda f: (f.manifest.pop('observation'), f.write_manifest()),
            'v2 provenance for a v1 state': lambda f: f.raw.pop(oc.RAW_STATE_KEY),
            'bundle table differs': lambda f: f.raw[oc.RAW_STATE_KEY]['detector_config'].update(rows=3),
            'bundle time differs': lambda f: f.raw[oc.RAW_STATE_KEY].update(sim_sec=750),
            'unmerged state': lambda f: f.raw['local_observation'].pop('signal_observation_window'),
            'missing window': lambda f: f.raw['local_observation'].update(signal_observation_window=None),
            'impossible counts': lambda f: f.raw['local_observation']['signal_observation_window']['heads'][0].update(
                qualified_crossings=11),
            'unverified but complete': lambda f: f.raw['local_observation']['signal_observation_window']['heads'][0].update(
                native_sec=140, unverified_sec=10),
            'not one 150 s window': lambda f: f.raw['local_observation']['signal_observation_window'].update(start_sec=780),
            'launch without a freeze pin': lambda f: (f.manifest['observation'].update(freeze=None), f.write_manifest()),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                fixture = Fixture(self.directory.name)
                change(fixture)
                options = options_with_interval(fixture) if name == 'sample_interval_sec' else OPTIONS
                with self.assertRaises(ValueError):
                    fixture.install(options=options)

    def test_head_sets_must_agree(self):
        """B7: a head the window lacks (or has in excess) against the INPX groups stops the decision.

        Without the check a missing head was only 'short exposure' and its group was dropped silently.
        """
        def extra_network_head(f):
            text = f.network.read_text(encoding='utf-8').replace(
                '</signalHeads>', '<signalHead no="2" lane="67 1" pos="50" sg="1004 8" allVehTypes="true"/></signalHeads>')
            f.network.write_text(text, encoding='utf-8')
            f.manifest['files']['network'] = evidence(f.network)
            f.write_manifest()

        def extra_window_head(f):
            heads = f.raw['local_observation']['signal_observation_window']['heads']
            heads.append({**heads[0], 'head_id': '2', 'link': '67'})

        for name, change in (('window lacks a head', extra_network_head), ('window has an extra head', extra_window_head)):
            for complete in (True, False):
                with self.subTest(case=name, clock_complete=complete):
                    fixture = Fixture(self.directory.name)
                    fixture.raw['local_observation']['signal_observation_window']['clock_complete'] = complete
                    change(fixture)
                    with self.assertRaisesRegex(ValueError, 'differ from the INPX physical groups'):
                        fixture.install()
        both = Fixture(self.directory.name)
        extra_network_head(both)
        extra_window_head(both)
        both.install()          # the same two heads on both sides

    def test_mode_detection(self):
        self.assertEqual(sho.observation_mode(self.fx.raw), 'v2')
        self.assertEqual(sho.observation_mode({'sim_sec': 900}), 'v1')
        with self.assertRaises(ValueError):
            sho.observation_mode({'sim_sec': 900}, {'observation': {}})
        with self.assertRaises(ValueError):
            sho.settings({**OPTIONS, 'sample_interval_sec': 1}, v2=True)
        self.assertEqual(sho.settings({**OPTIONS, 'sample_interval_sec': 1})['sample_interval_sec'], 1)


if __name__ == '__main__':
    unittest.main()
