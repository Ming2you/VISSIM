"""T8 with the real WP-B2 observer (plan C3, C4(h,i), C5, C6).

test_n31_observe_state.py fixes LPR's side of the call order with a stubbed
obs150_observation. Here the real obs150_observation runs on WP-B2's synthetic
900 s disk bundle (test_lane_derive.world_900 written by
test_lane_support.write_bundle: sha-chained .mer index, .err chunk, frames,
provenance) through lane_plant_runtime.observe_state, and every LPR v2
consumer then reads its lane observation. The bundle is observed both strict
(ground-truth windows, as G1) and operational (none, as V5); obs150_lane's
strict-only refusals (D11, removals within the .err 0.1 m rounding of an inner
segment end, obs150_lane.py:492-505) belong to WP-B2's own tests:

  C4(h)  _offramp_history_v2 (the exact 10643 ledger, not the 1 s replay)
  C5     the held 10643 lane shares split an aggregate admission exactly
  C4(i)  source_boundary.observed_block on the native timetable of the same
         schedule: the observer's schedule integral must be the forecast's
  C6     demand_blocks == forecast(recent, backlog) of the observed record;
         None at t=1 (cutoff < history_sec)

Nothing outside a temporary folder under this tests directory is written.
"""
from __future__ import annotations

import copy
import shutil
import tempfile
import types
import unittest
from pathlib import Path

import n31_fixtures as fx
import test_lane_support as sup
from test_lane_derive import world_900
from evaluation.controllers import lane_coupling
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers import network_provenance
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers import obs150_observation
from evaluation.controllers import source_boundary as sb

INPUTS = {'1098': 'FW_E', '1099': 'FW_W'}


def native_timetable(schedules):
    """native_input_schedule of the context schedule (the shape LPR:371-381 declares)."""
    return {'schema': 'native-input-schedule/v1', 'freeway_link_by_input': dict(INPUTS),
            'inputs': {no: {'schedule': [{'start_sec': r.start_sec, 'rate_veh_h': r.vph} for r in schedules[road]]}
                       for no, road in INPUTS.items()}}


class RealObserverPipelineTests(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='_tmp_', dir=fx.HERE))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.obs = sup.fixture_context()
        saved = network_provenance.snapshot_network_sha256
        network_provenance.snapshot_network_sha256 = lambda raw: self.obs.network_sha256
        self.addCleanup(setattr, network_provenance, 'snapshot_network_sha256', saved)
        self.context = {'plant_mode': 'v2', 'manifest_sha256': self.obs.manifest_sha256, 'obs150': self.obs,
                        'document': {'sources': {'network': {'path': 'n', 'sha256': self.obs.network_sha256}}}}

    def observe(self, world, name, *, ground_truth=True):
        raw = sup.write_bundle(world, self.dir / name, ground_truth=ground_truth)
        before = copy.deepcopy(raw)
        merged, observation = lpr.observe_state(self.context, raw)
        self.assertEqual(raw, before, 'observe_state must not touch its input state')
        return raw, merged, observation

    def test_observe_state_with_the_real_observer(self):
        # strict: a verification run with ground-truth windows (G1, RW_OBS150_GT);
        # operational: V5 (no GT windows), where obs150_lane counts by the rounded .err position
        for ground_truth in (True, False):
            with self.subTest(strict=ground_truth):
                raw, merged, observation = self.observe(world_900(), 'd900_%d' % ground_truth,
                                                        ground_truth=ground_truth)
                derived = obs150_observation.derive(raw, self.obs)
                self.assertIs(derived['strict'], ground_truth)
                self.assertEqual(merged[oc.MERGED_DERIVED_KEY], derived)
                written = Path(raw[oc.RAW_STATE_KEY]['directory']) / oc.derived_path(900)
                self.assertEqual(written.read_bytes(), oc.derived_bytes(derived))
                oc.validate_merged_state(raw, merged)
                oc.validate_lane_observation_v2(observation)
                self.assertEqual(merged['local_observation']['far_measurement']['freeway_exit_count'],
                                 derived['freeway_exit_count']['value'])
                self.assertEqual(observation['source']['derived_sha256'], oc.canonical_sha256(derived))
                self.assertEqual(observation['source']['manifest_sha256'], self.obs.manifest_sha256)
                self.assertEqual([f['time_s'] for f in observation['frames']], [900])
                # replay: the same bytes pass write_derived again
                lpr.observe_state(self.context, raw)

    def test_identity_is_checked_against_the_real_observer(self):
        raw = sup.write_bundle(world_900(), self.dir / 'd900')
        context = dict(self.context, manifest_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'identity'):
            lpr.observe_state(context, raw)

    def test_consumers_read_the_observation(self):
        for ground_truth in (True, False):
            with self.subTest(strict=ground_truth):
                self.check_consumers(ground_truth)

    def check_consumers(self, ground_truth):
        _, merged, observation = self.observe(world_900(), 'c900_%d' % ground_truth, ground_truth=ground_truth)
        derived = merged[oc.MERGED_DERIVED_KEY]
        # C4(h): the ledger history, tuples as local_history returns them
        history = lpr._offramp_history_v2(observation, 900)
        self.assertEqual(history['off_composition'],
                         [[tuple(pair) for pair in lane] for lane in derived['offramp_10643_history']['off_composition']])
        self.assertEqual((history['information_cutoff_s'], history['history_start_s']), (900, 750))
        with self.assertRaisesRegex(ValueError, 'causal window'):
            lpr._offramp_history_v2(observation, 1050)
        # C4(h): every receiving ramp of the context has one share per connector lane
        for name, ref in self.obs.ramp_arrivals.items():
            if ref.receiving:
                shares = observation['ramp_arrival_shares'][name]
                self.assertEqual(len(shares), len(ref.lanes), name)
                self.assertAlmostEqual(sum(shares), 1.0, places=12)
        # C5: the held lane shares split an aggregate admission exactly
        shares = observation['offramp_10643_lane_shares']
        self.assertEqual(shares, derived['offramp_10643_lane_shares'])
        split = {'mode': 'observed_lane_shares_held', 'shares': list(shares), 'information_cutoff_s': 900}
        lanes = lane_coupling.split_10643(0.8, [1800.0, 1800.0, 0.0], split)
        self.assertEqual(lanes[0], 0.8 * shares[0])
        self.assertEqual(sum(lanes), 0.8)
        # C4(i): the observer and the forecast use one schedule
        native = native_timetable(self.obs.source_schedule)
        schedules = sb.road_schedules(native)
        for road in oc.ROADS:
            self.assertTrue(sb.same_schedule(schedules[road], tuple(self.obs.source_schedule[road])))
        record = sb.observed_block(observation, schedules)
        self.assertEqual(record['by_road'], {road: dict(observation['source_boundary'][road]) for road in oc.ROADS})
        self.assertEqual(record['information_cutoff_s'], 900)
        # C6: the A1 blocks of that record
        cfg = types.SimpleNamespace(
            simulation=types.SimpleNamespace(control_interval=150.0),
            network=types.SimpleNamespace(lane_plant_enabled=True, native_input_schedule=native,
                                          lane_plant_sources={'source_boundary': dict(oc.SOURCE_BOUNDARY_BLOCK)},
                                          freeway_source_boundary_observed=record))
        blocks = sb.demand_blocks(cfg, 900.0, 5)
        for road in oc.ROADS:
            row = observation['source_boundary'][road]
            self.assertEqual(blocks[road], sb.forecast(row['recent_vph'], row['backlog_veh'], schedules[road],
                                                       900.0, 150, 5, step_s=10))
            self.assertTrue(all(q >= 0.0 for q in blocks[road]))
        # a timetable the observer did not integrate is refused
        shifted = {road: tuple(oc.ScheduleRow(r.start_sec, r.end_sec, r.vph + 1.0) for r in rows)
                   for road, rows in schedules.items()}
        with self.assertRaisesRegex(ValueError, 'schedule integral'):
            sb.observed_block(observation, shifted)

    def test_t1_decision(self):
        world = sup.World(1)
        world.frame_end.append((1, 74, 2, 0.3))
        _, merged, observation = self.observe(world, 'd1')
        self.assertIsNone(merged['local_observation']['signal_observation_window'])
        self.assertEqual((observation['information_cutoff_s'], observation['history_start_s']), (1, 0))
        history = lpr._offramp_history_v2(observation, 1)
        self.assertEqual(history['history_start_s'], 0)
        schedules = sb.road_schedules(native_timetable(self.obs.source_schedule))
        record = sb.observed_block(observation, schedules)
        self.assertEqual({row['interval_s'] for row in record['by_road'].values()}, {1})
        cfg = types.SimpleNamespace(
            simulation=types.SimpleNamespace(control_interval=150.0),
            network=types.SimpleNamespace(lane_plant_enabled=True, native_input_schedule=None,
                                          lane_plant_sources={'source_boundary': dict(oc.SOURCE_BOUNDARY_BLOCK)},
                                          freeway_source_boundary_observed=record))
        self.assertIsNone(sb.demand_blocks(cfg, 1.0, 5))    # BF:91 needs a complete 150 s history


if __name__ == '__main__':
    unittest.main()
