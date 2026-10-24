"""WP-0: switch, derived schemas, context, schedule and interfaces (plan 1.1, 1.5, 1.6, 1.8, 1.9)."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c  # noqa: E402


def rejects(test, function, *args, **kwargs):
    with test.assertRaises(c.ObsContractError):
        function(*args, **kwargs)


class Switch(unittest.TestCase):
    def test_v1_manifest_stays_v1(self):
        document = json.loads((c.ROOT / 'diagnostics/lane_plant_20260921/plant.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(c.plant_mode(document), 'v1')
        rejects(self, c.validate_plant_manifest_v2, document)

    def test_manifest_v2(self):
        document = fx.manifest_v2()
        c.validate_plant_manifest_v2(document)
        self.assertEqual(c.plant_mode(document), 'v2')
        changes = [
            lambda d: d['sources'].pop('runner_config'), lambda d: d['sources'].update(lane_geometry=d['membership']),
            lambda d: d['sources']['network'].update(path='diagnostics\\x.inpx'),
            lambda d: d['sources']['network'].update(path='D:/x.inpx'),
            lambda d: d['sources']['network'].update(sha256='A' * 64),
            lambda d: d['observation'].update(expected_simres=1), lambda d: d['observation'].update(vehrec_interval_sec=1),
            lambda d: d['observation'].update(sample_interval_sec=1),
            lambda d: d['source_boundary'].update(model_step_sec=5), lambda d: d.update(lane_groups=True),
            lambda d: d.update(fw_e_terminal='open'), lambda d: d.update(vsl_command_space='cells_31'),
            lambda d: d.update(future_observations=True), lambda d: d.update(qualification=''),
            lambda d: d.pop('off_groups'), lambda d: d.update(schema='coupled-lane-plant/v3'),
        ]
        for change in changes:
            document = fx.manifest_v2()
            change(document)
            rejects(self, c.validate_plant_manifest_v2, document)

    def test_tuning_v2(self):
        document = fx.manifest_v2()
        c.validate_tuning_v2(fx.tuning_v2(document), document)
        for change in (lambda t: t['urban']['capacity']['head_observation'].update(sample_interval_sec=1),
                       lambda t: t['urban']['capacity']['head_observation'].update(enabled=False),
                       lambda t: t['execution'].update(native_signal_record=True),
                       lambda t: t['execution'].update(signal_vbs_config='diagnostics/lane_plant_20260921/scenario/lane_native.vbs'),
                       lambda t: t['freeway'].update(lane_plant='diagnostics\\sdmpc_n31_20260924\\plant_n31_v2.json')):
            tuning = fx.tuning_v2(document)
            change(tuning)
            rejects(self, c.validate_tuning_v2, tuning, document)

    def test_runner_env(self):
        env = c.expected_runner_env(fx.manifest_v2(), 'D:\\FRZ\\obs150_detectors_v2.csv')
        self.assertEqual(env['RW_OBSERVATION_CADENCE'], 'decision150')
        self.assertEqual(env['RW_SIGNAL_OBSERVATION'], '0')
        self.assertEqual(env['RW_OBS150_EXPECTED_SIMRES'], '10')
        self.assertEqual(env['RW_OBS150_VEHREC_SEC'], '5')
        self.assertEqual(env['RW_OBS150_DETECTORS_SHA256'], fx.SHA_B)
        self.assertEqual(env['RW_STATE_LOG'], 'decision')
        self.assertEqual(env['RW_QUEUE_WINDOW'], '0')
        self.assertNotIn('RW_OBS150_GT', env)

    def test_ground_truth_windows(self):
        self.assertEqual(c.parse_gt_windows('750:900,1050:1200'), [[750, 900], [1050, 1200]])
        self.assertEqual(c.parse_gt_windows(''), [])
        self.assertEqual(c.format_gt_windows([[750, 900]]), '750:900')
        for bad in ('750:800', '900:750', '750:900,800:950', '750-900', ' 750:900'):
            rejects(self, c.parse_gt_windows, bad)

    def test_provenance_block(self):
        block = {'schema': c.PROVENANCE_OBSERVATION_SCHEMA, 'cadence': 'decision150',
                 'plant_manifest': {'path': 'D:\\FRZ\\plant_n31_v2.json', 'sha256': fx.SHA_A},
                 'detectors': {'path': 'D:\\FRZ\\obs150_detectors_v2.csv', 'sha256': fx.SHA_B, 'rows': 290},
                 'expected_simres': 10, 'vehrec_interval_sec': 5, 'ground_truth_windows': [[750, 900]],
                 'freeze': None}
        c.validate_provenance_observation(block)
        rejects(self, c.validate_provenance_observation, block, require_freeze=True)
        c.validate_provenance_observation({**block, 'freeze': {'path': 'D:\\FRZ\\FREEZE.json', 'sha256': fx.SHA_C}},
                                          require_freeze=True)
        rejects(self, c.validate_provenance_observation, {**block, 'cadence': 'per_second'})


class HeadWindowAndClocks(unittest.TestCase):
    def test_head_window(self):
        c.validate_head_window_v2(fx.head_window(900), end_sec=900, detector_config_sha256=fx.SHA_B)
        changes = [
            lambda w: w.update(schema='physical-head-window/v1'), lambda w: w.update(cadence_sec=1),
            lambda w: w.update(start_sec=751), lambda w: w.update(exposure_method='actual_left_step_hold'),
            lambda w: w.update(unknown_links={}), lambda w: w.update(transition_count=150),
            lambda w: w['heads'][0].update(qualified_crossings=41), lambda w: w['heads'][0].update(green_sec=60.5),
            lambda w: w['heads'][0].update(native_sec=149), lambda w: w['heads'][0].update(green_sec=151),
            lambda w: w['heads'][0].update(native_sec=100, unverified_sec=50),
            lambda w: w['heads'].append(dict(w['heads'][0])), lambda w: w['heads'][0].pop('boundary_ambiguous'),
            lambda w: w['bypass_link_exits'].update({'403': 1.5}), lambda w: w.update(heads=[]),
        ]
        for change in changes:
            window = fx.head_window(900)
            change(window)
            rejects(self, c.validate_head_window_v2, window, end_sec=900)
        rejects(self, c.validate_head_window_v2, fx.head_window(900), end_sec=1050)
        rejects(self, c.validate_head_window_v2, fx.head_window(900), detector_config_sha256=fx.SHA_A)
        incomplete = fx.head_window(900)
        incomplete['heads'][0].update(native_sec=100, unverified_sec=50)
        incomplete['clock_complete'] = False
        c.validate_head_window_v2(incomplete)

    def test_clocks(self):
        window = {'start_s': 750, 'end_s': 900}
        good = {'1004-2': {'green': [(750, 780), (820, 850)], 'native_sec': 150, 'controlled_sec': 0,
                           'unverified_sec': 0, 'complete': True},
                '9106-1': {'green': [[812, 860]], 'native_sec': 0, 'controlled_sec': 100, 'unverified_sec': 50,
                           'complete': False}}
        c.validate_clocks(good, window)
        for key, change in (('1004-2', {'green': [(740, 780)]}), ('1004-2', {'green': [(780, 820), (750, 780)]}),
                            ('1004-2', {'green': [(750, 780), (780, 800)]}), ('1004-2', {'native_sec': 149}),
                            ('9106-1', {'complete': True}), ('9106-1', {'green': [(750, 860)]}),
                            ('1004-2', {'green': [(750.0, 780)]})):
            clocks = copy.deepcopy(good)
            clocks[key].update(change)
            rejects(self, c.validate_clocks, clocks, window)


class LaneObservationAndDerived(unittest.TestCase):
    def test_lane_observation(self):
        c.validate_lane_observation_v2(fx.lane_observation(900))
        c.validate_lane_observation_v2(fx.lane_observation(1))
        changes = [
            lambda o: o.update(lane_group_dynamics={'FW_E': {}}), lambda o: o.update(history_start_s=0),
            lambda o: o.update(future_traffic_inputs=True), lambda o: o['frames'].append(o['frames'][0]),
            lambda o: o['off_split_ratio'].update({'10481': 0.5}),
            lambda o: o['off_split_history']['10481'].update(post_branch_ramp_bypass_veh=1),
            lambda o: o['off_split_ratio'].pop('10643'), lambda o: o['ramp_arrival_shares'].update(RM_C10681=[0.5, 0.6]),
            lambda o: o.update(offramp_10643_lane_shares=[1.0]),
            lambda o: o['offramp_10643_history'].update(background={'x': 1}),
            lambda o: o['source_boundary']['FW_E'].update(backlog_veh=49.0),
            lambda o: o['source_boundary']['FW_W'].update(recent_vph=2400.5), lambda o: o.update(freeway_exit_count=-1),
            lambda o: o['source'].pop('derived_sha256'), lambda o: o.update(sample_interval_sec=5),
        ]
        for change in changes:
            observation = fx.lane_observation(900)
            change(observation)
            rejects(self, c.validate_lane_observation_v2, observation)

    def test_derived(self):
        c.validate_derived(fx.derived(900))
        c.validate_derived(fx.derived(1))
        changes = [
            lambda d: d.update(k=5), lambda d: d['lag'].update(ok=False), lambda d: d.update(boundary_ambiguous=1),
            lambda d: d['tails'].update({'960003': 1}), lambda d: d['boundaries']['source:FW_E'].update(cross=150),
            lambda d: d['freeway_exit_count'].update(value=320),
            lambda d: d['ledger_10643']['vehicles'][0].update(label_source='unidentified'),
            lambda d: d['removals']['rows'][0].update(time_sec=750.0), lambda d: d['removals'].update(window_total=2),
            lambda d: d['link_departures_window'].update({'404': 1}), lambda d: d['inputs'].pop('raw_sha256'),
            lambda d: d['head_window']['heads'][0].update(boundary_ambiguous=1),
        ]
        for change in changes:
            derived = fx.derived(900)
            change(derived)
            rejects(self, c.validate_derived, derived)
        relaxed = fx.derived(900)
        relaxed['strict'] = False
        relaxed['ledger_10643']['vehicles'][0].update(label_source='unidentified', connector=None)
        c.validate_derived(relaxed)
        first = fx.derived(1)
        first['head_window'] = fx.head_window(150)
        rejects(self, c.validate_derived, first)

    def test_merged_state(self):
        before, after = fx.merged(900)
        c.validate_merged_state(before, after)
        first_before, first_after = fx.merged(1)
        c.validate_merged_state(first_before, first_after)
        self.assertIsNone(first_after['local_observation']['signal_observation_window'])
        changes = [
            lambda s: s['local_observation'].update(link_counts={'71': 5}), lambda s: s.update(sim_sec=901),
            lambda s: s['local_observation']['far_measurement'].update(freeway_exit_count=320),
            lambda s: s['local_observation']['far_measurement'].pop('freeway_exit_count_provenance'),
            lambda s: s['local_observation']['far_measurement'].update(link_volume_veh_h={}),
            lambda s: s['local_observation'].pop('signal_observation_window'),
            lambda s: s['local_observation'].update(link_departures_window={'403': 8}),
        ]
        for change in changes:
            before, after = fx.merged(900)
            change(after)
            rejects(self, c.validate_merged_state, before, after)
        before, after = fx.merged(900)
        before['local_observation']['far_measurement']['freeway_exit_count'] = 5
        rejects(self, c.validate_merged_state, before, after)

    def test_lane_meta(self):
        state = fx.state(900)
        c.validate_lane_meta_v2(state['lane_plant_observation'], state)
        rejects(self, c.validate_lane_meta_v2, {**state['lane_plant_observation'], 'cadence': 'per_second'}, state)
        rejects(self, c.validate_lane_meta_v2, {**state['lane_plant_observation'], 'sample_interval_sec': 5}, state)


class ContextAndSchedule(unittest.TestCase):
    def test_context(self):
        context = fx.context()
        c.validate_context(context)
        self.assertEqual(len(context.rows_by_role('source')), 7)
        import dataclasses
        changes = [
            dict(offramps={k: v for k, v in context.offramps.items() if k != '10481'}),
            dict(source_refs={'FW_E': 'source:FW_E'}), dict(headfree_refs={'10565': 'headfree:10565', '10570': 'source:FW_E'}),
            dict(x10643_exit_ref='x10643_exit:10642'), dict(route_destinations_10643={1: 10636}),
            dict(chain_internal_connectors=frozenset({99999})), dict(lane_map_10643={10643: {1: 1}}),
            dict(head_groups={('71', '1004_p1'): ({'head_id': '90030883', 'link': '71', 'lane': 1,
                                                 'position_m': 78.980074, 'sc': '1004', 'sg': '2'},)}),
            dict(boundaries={}), dict(detector_csv_sha256='x'),
            dict(sig_table={'1004': c.SigProgram('1004', 'p', fx.SHA_A, 1, 75, 150, {'2': ((0, 151),)})}),
            dict(source_schedule={'FW_E': (c.ScheduleRow(0.0, None, 1.0),)}),
        ]
        for change in changes:
            with self.subTest(change=list(change)):
                rejects(self, c.validate_context, dataclasses.replace(context, **change))

    def test_schedule_matches_boundary_factory(self):
        from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1 import boundary_factory as bf
        rows = [{'road': 'FW_E', 'start_sec': 0, 'end_sec': 900, 'desired_volume_vph': 3000.0},
                {'road': 'FW_E', 'start_sec': 900, 'end_sec': 4500, 'desired_volume_vph': 3600.0},
                {'road': 'FW_E', 'start_sec': 4500, 'end_sec': None, 'desired_volume_vph': 2400.0}]
        holder = type('Holder', (), {'geometry': {'desired_source_demand': rows}})()
        schedule = c.validate_schedule([c.ScheduleRow(r['start_sec'], r['end_sec'], r['desired_volume_vph'])
                                        for r in rows])
        for cutoff in (0, 1, 150, 899, 900, 1350, 4500, 9000):
            self.assertEqual(c.schedule_integral_veh(schedule, 0, cutoff), bf.ObservationData.desired_before(holder, 'FW_E', cutoff))
        for t in (0, 899.9, 900, 4499, 4500, 8990):
            self.assertEqual(c.schedule_rate_at(schedule, t), bf.ObservationData.demand_vph(holder, 'FW_E', t))
        self.assertAlmostEqual(c.schedule_integral_veh(schedule, 850, 950), (50 * 3000 + 50 * 3600) / 3600, places=12)
        rejects(self, c.validate_schedule, [c.ScheduleRow(0.0, 900.0, 1.0), c.ScheduleRow(901.0, None, 1.0)])
        rejects(self, c.validate_schedule, [c.ScheduleRow(0.0, 900.0, 1.0)])


class Interfaces(unittest.TestCase):
    def test_signature_checker(self):
        def forecast(recent_vph, backlog_veh, schedule, start_s, block_s, n_blocks, step_s=10, *, audit=None):
            return []
        c.assert_implements('evaluation.controllers.source_boundary.forecast', forecast)

        def wrong_default(recent_vph, backlog_veh, schedule, start_s, block_s, n_blocks, step_s=5):
            return []

        def renamed(recent, backlog_veh, schedule, start_s, block_s, n_blocks, step_s=10):
            return []

        def extra_positional(raw, context, strict):
            return {}
        rejects(self, c.assert_implements, 'evaluation.controllers.source_boundary.forecast', wrong_default)
        rejects(self, c.assert_implements, 'evaluation.controllers.source_boundary.forecast', renamed)
        rejects(self, c.assert_implements, 'evaluation.controllers.obs150_observation.derive', extra_positional)
        rejects(self, c.assert_implements, 'evaluation.controllers.nope.derive', renamed)

    def test_every_interface_names_its_owner_module(self):
        owners = {name.rsplit('.', 1)[0] for name in c.INTERFACES}
        self.assertEqual(owners, {'evaluation.controllers.obs150_capture', 'evaluation.controllers.obs150_signal_clock',
                                  'evaluation.controllers.obs150_head_window', 'evaluation.controllers.obs150_lane',
                                  'evaluation.controllers.obs150_observation',
                                  'evaluation.controllers.source_boundary'})
        self.assertEqual(c.CAPTURE_CLI_ARGS, ('--eval-dir', '--err', '--out-dir', '--sim-sec', '--detectors',
                                              '--detectors-sha256'))


class GitAttributes(unittest.TestCase):
    @unittest.skipIf(shutil.which('git') is None, 'git not on PATH')
    def test_pinned_folders_are_binary_exact(self):
        paths = ['diagnostics/sdmpc_n31_20260924/obs150/obs150_detectors_v2.csv',
                 'diagnostics/obs150_20260924/tests/fixture.json']
        out = subprocess.run(['git', 'check-attr', 'text', '--', *paths], cwd=c.ROOT, capture_output=True,
                             text=True, check=True).stdout.splitlines()
        self.assertEqual(out, [p + ': text: unset' for p in paths])


if __name__ == '__main__':
    unittest.main()
