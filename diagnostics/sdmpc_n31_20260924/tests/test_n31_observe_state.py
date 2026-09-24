"""T8 (plan C3): observe_state v2 and the RS:77-89 wiring.

obs150_observation (WP-B2) is stubbed with contract-fixture documents; the
test fixes LPR's side of the contract call order (contract section 9):
derive -> write_derived -> merge_into_state -> lane_observation, and that
configure_runtime hands the MERGED state to every later consumer.
"""
from __future__ import annotations

import copy
import shutil
import tempfile
import types
import unittest
from pathlib import Path

import n31_fixtures as fx
import contract_fixtures as cf
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers import network_provenance
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers import runtime_setup

NETWORK = 'f' * 64
MANIFEST = 'e' * 64


def merged_of(raw, derived):
    after = copy.deepcopy(raw)
    local = after['local_observation']
    local['signal_observation_window'] = copy.deepcopy(derived['head_window'])
    local['link_departures_window'] = dict(derived['link_departures_window'])
    local['far_measurement']['freeway_exit_count'] = derived['freeway_exit_count']['value']
    local['far_measurement']['freeway_exit_count_provenance'] = oc.FREEWAY_EXIT_PROVENANCE
    after[oc.MERGED_DERIVED_KEY] = derived
    return after


class ObserveStateTests(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='_tmp_', dir=fx.HERE))
        (self.dir / 'obs150').mkdir()
        self.raw = cf.state(900)
        self.raw[oc.RAW_STATE_KEY]['directory'] = str(self.dir)
        self.derived = cf.derived(900)
        self.calls = []
        self.saved_sha = network_provenance.snapshot_network_sha256
        network_provenance.snapshot_network_sha256 = lambda raw: NETWORK
        self.context = {'plant_mode': 'v2', 'manifest_sha256': MANIFEST, 'obs150': 'CTX',
                        'document': {'sources': {'network': {'path': 'n', 'sha256': NETWORK}}}}

    def tearDown(self):
        network_provenance.snapshot_network_sha256 = self.saved_sha
        shutil.rmtree(self.dir, ignore_errors=True)

    def stub(self, **override):
        derived = self.derived

        def derive(raw, context):
            self.calls.append('derive')
            self.assertEqual(context, 'CTX')
            return copy.deepcopy(derived)

        def merge_into_state(raw, d):
            self.calls.append('merge')
            self.assertTrue((self.dir / oc.derived_path(900)).is_file(), 'derived must be written before the merge')
            return merged_of(raw, d)

        def lane_observation(context, raw):
            self.calls.append('lane')
            self.assertIn(oc.MERGED_DERIVED_KEY, raw)
            observation = cf.lane_observation(900)
            d = raw[oc.MERGED_DERIVED_KEY]
            observation['source'] = {'run_id': d['run_id'], 'manifest_sha256': MANIFEST,
                                     'derived_sha256': oc.canonical_sha256(d),
                                     **{k: d['inputs'][k] for k in oc.DERIVED_INPUT_KEYS}}
            return observation
        functions = dict(derive=derive, merge_into_state=merge_into_state, lane_observation=lane_observation)
        functions.update(override)
        return fx.obs150_stub(**functions)

    def test_order_merge_and_identity(self):
        with self.stub():
            state, observation = lpr.observe_state(self.context, self.raw)
        self.assertEqual(self.calls, ['derive', 'merge', 'lane'])
        self.assertEqual(state[oc.MERGED_DERIVED_KEY], self.derived)
        self.assertEqual(state['local_observation']['far_measurement']['freeway_exit_count'], 321)
        self.assertNotIn(oc.MERGED_DERIVED_KEY, self.raw, 'the input state stays untouched')
        oc.validate_lane_observation_v2(observation)
        written = (self.dir / oc.derived_path(900)).read_bytes()
        self.assertEqual(written, oc.derived_bytes(self.derived))
        with self.stub():   # replay: identical bytes pass
            lpr.observe_state(self.context, self.raw)

    def test_identity_mismatches_fail(self):
        def wrong_derived_sha(context, raw):
            observation = cf.lane_observation(900)
            d = raw[oc.MERGED_DERIVED_KEY]
            observation['source'] = {'run_id': 'run1', 'manifest_sha256': MANIFEST, 'derived_sha256': 'a' * 64,
                                     **{k: d['inputs'][k] for k in oc.DERIVED_INPUT_KEYS}}
            return observation
        with self.stub(lane_observation=wrong_derived_sha):
            with self.assertRaisesRegex(ValueError, 'identity'):
                lpr.observe_state(self.context, self.raw)

        def wrong_manifest(context, raw):
            observation = cf.lane_observation(900)
            d = raw[oc.MERGED_DERIVED_KEY]
            observation['source'] = {'run_id': 'run1', 'manifest_sha256': 'b' * 64,
                                     'derived_sha256': oc.canonical_sha256(d),
                                     **{k: d['inputs'][k] for k in oc.DERIVED_INPUT_KEYS}}
            return observation
        with self.stub(lane_observation=wrong_manifest):
            with self.assertRaisesRegex(ValueError, 'identity'):
                lpr.observe_state(self.context, self.raw)

    def test_merge_touching_other_fields_fails(self):
        def bad_merge(raw, d):
            after = merged_of(raw, d)
            after['local_observation']['scan_ok'] = False
            return after
        with self.stub(merge_into_state=bad_merge):
            with self.assertRaises(oc.ObsContractError):
                lpr.observe_state(self.context, self.raw)

    def test_state_without_bundle_or_network_fails(self):
        raw = copy.deepcopy(self.raw)
        raw.pop(oc.RAW_STATE_KEY)
        with self.stub():
            with self.assertRaisesRegex(ValueError, 'obs150 bundle'):
                lpr.observe_state(self.context, raw)
        raw = copy.deepcopy(self.raw)
        raw[oc.RAW_STATE_KEY]['sim_sec'] = 750
        with self.stub():
            with self.assertRaisesRegex(ValueError, 'obs150 bundle'):
                lpr.observe_state(self.context, raw)
        network_provenance.snapshot_network_sha256 = lambda raw: 'c' * 64
        with self.stub():
            with self.assertRaisesRegex(ValueError, 'network differs'):
                lpr.observe_state(self.context, self.raw)

    def test_v1_meta_is_refused(self):
        raw = copy.deepcopy(self.raw)
        raw['lane_plant_observation'].pop('cadence')
        with self.stub():
            with self.assertRaises(oc.ObsContractError):
                lpr.observe_state(self.context, raw)


class Stop(Exception):
    def __init__(self, state_json):
        super().__init__('stop')
        self.state_json = state_json


class ConfigureRuntimeWiringTests(unittest.TestCase):
    """RS:77-89: v2 validates the tuning, then every consumer sees the merged state."""

    def setUp(self):
        self.saved = {k: getattr(lpr, k) for k in ('load_sources', 'observe_state', 'bind_current_routes')}
        self.document = cf.manifest_v2()
        self.merged = {'merged': True}
        self.seen = []
        lpr.load_sources = lambda manifest: {'plant_mode': 'v2', 'document': self.document}
        lpr.observe_state = lambda context, raw: (self.seen.append(raw) or self.merged, 'OBS')
        lpr.bind_current_routes = lambda state, observation: dict(state, routes_bound=observation)

    def tearDown(self):
        for key, value in self.saved.items():
            setattr(lpr, key, value)

    def run_configure(self, tuning):
        def stop(state_json):
            raise Stop(state_json)
        adapter = types.SimpleNamespace(_link_counts_from_local_observation=stop)
        cfg = types.SimpleNamespace(network=types.SimpleNamespace())
        with self.assertRaises(Stop) as caught:
            runtime_setup.configure_runtime(adapter, cfg, tuning, {}, {'raw': True}, None, {}, {}, None)
        return caught.exception.state_json

    def test_merged_state_reaches_consumers(self):
        state = self.run_configure(cf.tuning_v2(self.document))
        self.assertEqual(state, {'merged': True, 'routes_bound': 'OBS'})
        self.assertEqual(self.seen, [{'raw': True}])

    def test_invalid_v2_tuning_stops_before_observation(self):
        tuning = cf.tuning_v2(self.document)
        tuning['urban']['capacity']['head_observation']['sample_interval_sec'] = 1
        with self.assertRaises(oc.ObsContractError):
            self.run_configure(tuning)
        self.assertEqual(self.seen, [])
        tuning = cf.tuning_v2(self.document)
        tuning['execution']['native_signal_record'] = True
        with self.assertRaises(oc.ObsContractError):
            self.run_configure(tuning)


if __name__ == '__main__':
    unittest.main()
