"""WP-B2, plan B7: obs150_observation.derive -> write_derived -> merge_into_state -> lane_observation.

The synthetic 900 s world of test_lane_derive is written as a complete disk
bundle (chunks, sha-chained index, frames, provenance) and run through the
contract call order of CONTRACT 9 (C3). t=1 runs the same path with its closure.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_lane_support as sup  # noqa: E402
from test_lane_support import c  # noqa: E402
from test_lane_derive import world_900  # noqa: E402

from evaluation.controllers import obs150_observation as ob  # noqa: E402


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.context = sup.fixture_context()

    def state(self, world, **kwargs):
        return sup.write_bundle(world, Path(self.tmp.name) / 'decisions', **kwargs)

    def test_contract_order_at_900(self):
        raw = self.state(world_900())
        derived = ob.derive(raw, self.context)
        c.validate_derived(derived)
        self.assertEqual(derived['inputs']['raw_sha256'], c.canonical_sha256(raw['obs150']))
        self.assertEqual(derived['strict'], True)
        self.assertEqual(derived['tails']['%d' % sup.key_of(sup.fixture_rows(), 'x10643_exit:10643', 1)], 1)
        self.assertEqual(derived['lag']['sum_tail'], sum(derived['tails'].values()))
        self.assertEqual(derived['boundaries']['x10643_exit:10643']['cross'], 5)
        self.assertEqual(derived['ledger_10643']['by_lane'], {'1': {'10634': 1, '10635': 1, '10642': 2},
                                                              '2': {'10635': 1}})
        self.assertEqual(derived['lag']['threshold_s'], 899.005)
        self.assertEqual(derived['removals']['window_total'], 3)
        by_vehicle = {r['vehicle_id']: r for r in derived['removals']['rows']}
        self.assertEqual(by_vehicle[302]['boundary_refs'], ['x10643_exit:10643'])
        self.assertEqual(by_vehicle[501]['on_chain'], True)
        self.assertEqual(by_vehicle[201]['on_chain'], False)
        head_window = derived['head_window']
        self.assertEqual(head_window['bypass_link_exits'], {'403': 7})
        self.assertEqual(derived['link_departures_window'], {'403': 9})
        path = c.write_derived(raw, derived)
        self.assertEqual(path.read_bytes(), c.derived_bytes(derived))
        self.assertEqual(c.write_derived(raw, derived), path)                    # replay-idempotent
        merged = ob.merge_into_state(raw, derived)
        c.validate_merged_state(raw, merged)
        self.assertEqual(merged['local_observation']['far_measurement']['freeway_exit_count'], 51)
        observation = ob.lane_observation(self.context, merged)
        c.validate_lane_observation_v2(observation)
        self.assertEqual(observation['source']['derived_sha256'], c.canonical_sha256(derived))
        self.assertEqual(observation['off_split_ratio']['10481'], 0.1)
        self.assertEqual(observation['freeway_exit_count'], 51)
        self.assertEqual(observation['frames'][0]['time_s'], 900)
        self.assertEqual(observation['offramp_10643_lane_shares'], [0.4, 0.6])
        self.assertEqual(observation['offramp_10643_history'], derived['offramp_10643_history'])

    def test_derive_is_a_pure_function_of_the_bundle(self):
        raw = self.state(world_900())
        self.assertEqual(c.canonical_json_bytes(ob.derive(raw, self.context)),
                         c.canonical_json_bytes(ob.derive(json.loads(json.dumps(raw)), self.context)))

    def test_t1(self):
        w = sup.World(1)
        w.frame_end.append((1, 74, 2, 0.3))
        raw = self.state(w)
        derived = ob.derive(raw, self.context)
        self.assertIsNone(derived['head_window'])
        self.assertEqual(derived['boundary_ambiguous'], 0)
        merged = ob.merge_into_state(raw, derived)
        self.assertIsNone(merged['local_observation']['signal_observation_window'])
        self.assertEqual(merged['local_observation']['link_departures_window'], {'403': 0})
        observation = ob.lane_observation(self.context, merged)
        self.assertEqual((observation['information_cutoff_s'], observation['history_start_s']), (1, 0))
        self.assertEqual(observation['source_boundary']['FW_E']['interval_s'], 1)

    def test_tampered_chunk_is_rejected(self):
        raw = self.state(world_900())
        chunk = Path(raw['obs150']['directory']) / Path(c.mer_chunk_path(900))
        chunk.write_bytes(chunk.read_bytes() + b'[1,960001,800.0,null,9,100,50.0,4.5,null]\n')
        with self.assertRaisesRegex(c.ObsContractError, 'differ from their pin'):
            ob.derive(raw, self.context)

    def test_lag_violation_fails_the_decision(self):
        raw = self.state(world_900())
        raw['obs150']['mer']['max_t_any'] = 898.9
        index_path = Path(raw['obs150']['directory']) / Path(c.MER_INDEX_PATH)
        document = json.loads(index_path.read_text(encoding='utf-8'))
        document['entries'][-1]['max_t_any'] = 898.9
        document['entries'][-1]['entry_sha256'] = c.mer_index_entry_sha256(document['entries'][-1])
        index_path.write_bytes(c.canonical_json_bytes(document) + b'\n')
        raw['obs150']['mer']['index_sha256'] = document['entries'][-1]['entry_sha256']
        with self.assertRaises(c.ObsLagError):
            ob.derive(raw, self.context)

    def test_fixture_sig_files_are_the_context_programs(self):
        """The fixture .sig bytes compile to exactly the context programs (sha pin included)."""
        from evaluation.controllers import obs150_signal_clock
        folder = Path(self.tmp.name) / 'sig'
        folder.mkdir()
        for sc in sup.FIXTURE_SIGS:
            with self.subTest(sc=sc):
                program = self.context.sig_table[sc]
                path = folder / f'{sc}.sig'
                path.write_bytes(sup.fixture_sig_bytes(sc))
                parsed = obs150_signal_clock.sig_program_from_file(sc, path, 1, sha256=program.sha256)
                self.assertEqual(sup.dataclasses.replace(parsed, path=program.path), program)

    def test_run_network_sig_copies_are_rechecked(self):
        """CONTRACT 6: B4 re-checks the .sig of every natively used SC in the run network folder."""
        for sc in sup.FIXTURE_SIGS:
            with self.subTest(sc=sc):
                raw = self.state(world_900())
                copy = Path(raw['network_path']).parent / f'{sc}.sig'
                copy.write_bytes(copy.read_bytes() + b'\n')
                with self.assertRaisesRegex(c.ObsContractError, 'differs from sig_manifest'):
                    ob.derive(raw, self.context)
                copy.unlink()
                with self.assertRaisesRegex(c.ObsContractError, 'lacks'):
                    ob.derive(raw, self.context)

    def test_state_without_an_absolute_network_path_is_rejected(self):
        for value in (None, '', 'relative\\net.inpx', 5):
            with self.subTest(value=value):
                raw = self.state(world_900())
                if value is None:
                    del raw['network_path']
                else:
                    raw['network_path'] = value
                with self.assertRaisesRegex(c.ObsContractError, 'network_path'):
                    ob.derive(raw, self.context)

    def test_rule_crosscheck_is_required_at_a_shared_point(self):
        """derive compares a table point with the RULE measurement at the same point (same k)."""
        from unittest import mock
        raw = self.state(world_900())                       # source:FW_E lane 1 (74, 1, 1.0) counted 150
        self.assertEqual(ob.rule_crosscheck_pairs(self.context.detectors), [])   # fixture: no shared point
        with mock.patch.dict(ob.RULE_CROSSCHECK_POINTS, {910030: (74, 1, 1.0)}, clear=True):
            with self.assertRaisesRegex(c.ObsContractError, 'differs from RULE measurement 910030 12'):
                ob.derive(raw, self.context)                # fixture raw has rule_crosscheck {'910030': 12}
            raw['obs150']['rule_crosscheck'] = {'910030': 150}
            self.assertEqual(ob.derive(raw, self.context)['sim_sec'], 900)
            raw['obs150']['rule_crosscheck'] = {}
            with self.assertRaisesRegex(c.ObsContractError, 'lacks RULE measurement 910030'):
                ob.derive(raw, self.context)

    def test_another_detector_table_is_rejected(self):
        raw = self.state(world_900())
        raw['obs150']['detector_config']['sha256'] = sup.fx.SHA_B
        with self.assertRaisesRegex(c.ObsContractError, 'another detector table'):
            ob.derive(raw, self.context)

    def test_merge_requires_the_runner_null_and_changes_nothing_else(self):
        raw = self.state(world_900())
        derived = ob.derive(raw, self.context)
        bad = sup.clone(raw)
        bad['local_observation']['far_measurement']['freeway_exit_count'] = 12
        with self.assertRaisesRegex(c.ObsContractError, 'null for the merge'):
            ob.merge_into_state(bad, derived)
        merged = ob.merge_into_state(raw, derived)
        with self.assertRaisesRegex(c.ObsContractError, 'already merged'):
            ob.merge_into_state(merged, derived)
        self.assertNotIn(c.MERGED_DERIVED_KEY, raw)

    def test_lane_observation_needs_the_merged_state(self):
        raw = self.state(world_900())
        with self.assertRaisesRegex(c.ObsContractError, 'merged state'):
            ob.lane_observation(self.context, raw)

    def test_interfaces(self):
        self.assertEqual(sorted(c.check_module('evaluation.controllers.obs150_observation')),
                         ['evaluation.controllers.obs150_observation.derive',
                          'evaluation.controllers.obs150_observation.lane_observation',
                          'evaluation.controllers.obs150_observation.load_context',
                          'evaluation.controllers.obs150_observation.merge_into_state'])


if __name__ == '__main__':
    unittest.main()
