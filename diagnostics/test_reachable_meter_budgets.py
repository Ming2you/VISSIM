"""Actual measured meter/writer fixtures; no traffic rollout, endpoint or COM."""
import copy
import math
import pickle
import unittest
from unittest.mock import patch

from diagnostics.test_area_meter_finalization import CanonicalMeterCandidateTests
from evaluation.controllers import area_meter_finalization as module


class ReachableMeterBudgetTests(unittest.TestCase):
    def setUp(self):
        self.fixture = CanonicalMeterCandidateTests()
        self.cfg, self.control = self.fixture.fixture()
        directions = self.cfg.network.ramp_to_freeway
        self.owned = {d: tuple(r for r in self.control.ramp_metering if directions[r] == d)
                      for d in ('FW_W', 'FW_E')}
        self.requests = {d: (
            ('source_seed', {r: self.control.ramp_metering[r] for r in ramps}),
            ('existing_fraction_1', {r: 1800. for r in ramps}))
            for d, ramps in self.owned.items()}
        self.provenance = {d: {'source': 'explicit synthetic current-source values',
            'branch': 'finite seed + configured fraction fixture', 'fractions': (1.,)} for d in self.owned}

    def run_reachable(self, **overrides):
        args = dict(directional_requests=self.requests, source_provenance=self.provenance,
                    budget_tolerance_veh_h=1e-9)
        args.update(overrides)
        return module.reachable_meter_budgets(self.control, self.cfg, **args)

    def high_demand(self):
        volumes = self.cfg.network.control_area_meter_context['raw']['local_observation']['far_measurement']['link_volume_veh_h']
        volumes.update({k: 1200. for k in volumes})

    def test_all_open_alias_product_keeps_original_target_and_full_physical_rows(self):
        before = pickle.dumps((self.cfg, self.control, self.requests, self.provenance))
        original_target = self.control.N_UF_star
        self.assertEqual(original_target, 5416.227623335266)
        result = self.run_reachable()
        self.assertTrue(result['complete'])
        self.assertEqual(result['requested_count'], 4)
        self.assertEqual(result['candidate_count'], 1)
        candidate = result['candidates'][0]
        self.assertEqual(candidate['total_budget_veh_h'], 7200.)
        self.assertEqual(candidate['directional_budgets_veh_h'], {'FW_W': 3600., 'FW_E': 3600.})
        self.assertEqual(len(candidate['aliases']), 4)
        self.assertEqual([a['request_index'] for a in candidate['aliases']], list(range(4)))
        self.assertEqual({r['green_sec'] for r in candidate['physical_rows']}, {10.})
        raw_allocated = module.finalize(copy.deepcopy(self.control), self.cfg)
        self.assertEqual(self.fixture.rows(raw_allocated, self.cfg), self.fixture.rows(candidate['control'], self.cfg))
        for key, value in vars(self.control).items():
            if key not in ('ramp_metering', 'N_UF_star', 'diagnostics'):
                self.assertEqual(getattr(candidate['control'], key), value)
        self.assertEqual(candidate['control'].diagnostics['nested'], self.control.diagnostics['nested'])
        self.assertFalse(result['leader_target_selected'])
        self.assertFalse(result['omega_modified'])
        self.assertFalse(result['shared_physical_feasibility_certified'])
        self.assertEqual(before, pickle.dumps((self.cfg, self.control, self.requests, self.provenance)))
        with self.assertRaisesRegex(module.MeterCandidateInfeasible, 'total equality.*5416'):
            self.fixture.prepare(candidate['control'], self.cfg,
                total_budget={'mode': 'equality', 'veh_h': original_target}, directional_budgets={})

    def test_same_total_different_directions_and_same_budget_different_schedules_survive(self):
        self.high_demand()
        for d, ramps in self.owned.items():
            a, b = ramps
            self.requests[d] = (('pair_a', {a: 900., b: 1200.}),
                                ('pair_b', {a: 1200., b: 900.}),
                                ('lower_pair', {a: 900., b: 900.}))
        result = self.run_reachable()
        self.assertTrue(result['complete'])
        self.assertEqual(result['requested_count'], 9)
        self.assertEqual(result['candidate_count'], 9)
        candidates = result['candidates']
        same_budget_different_rows = [(a, b) for i, a in enumerate(candidates) for b in candidates[i+1:]
            if a['directional_budgets_veh_h'] == b['directional_budgets_veh_h'] and a['physical_rows'] != b['physical_rows']]
        same_total_different_directions = [(a, b) for i, a in enumerate(candidates) for b in candidates[i+1:]
            if a['total_budget_veh_h'] == b['total_budget_veh_h'] and a['directional_budgets_veh_h'] != b['directional_budgets_veh_h']]
        self.assertTrue(same_budget_different_rows)
        self.assertTrue(same_total_different_directions)
        for candidate in candidates:
            self.assertEqual(candidate['control'].N_UF_star, math.fsum(candidate['realized_rates_veh_h'][r]
                for r in sorted(candidate['realized_rates_veh_h'])))
            module.assert_writer(candidate['control'], self.cfg, require_scored=True)
            again = self.fixture.prepare(candidate['control'], self.cfg,
                total_budget={'mode': 'equality', 'veh_h': candidate['total_budget_veh_h']},
                directional_budgets={d: {'mode': 'equality', 'veh_h': v}
                                     for d, v in candidate['directional_budgets_veh_h'].items()})
            self.assertEqual(again.ramp_metering, candidate['realized_rates_veh_h'])

    def test_closed_source_and_empty_domain_are_explicit_not_fabricated(self):
        self.requests = {d: (('closed_source_seed', dict.fromkeys(keys, 0.)),) for d, keys in self.owned.items()}
        result = self.run_reachable()
        self.assertEqual(result['candidates'][0]['total_budget_veh_h'], 0.)
        self.assertEqual({r['green_sec'] for r in result['candidates'][0]['physical_rows']}, {0.})
        self.requests['FW_E'] = ()
        result = self.run_reachable()
        self.assertEqual(result['status'], 'empty_reachable_set')
        self.assertTrue(result['complete'])
        self.assertEqual(result['requested_count'], 0)
        self.assertEqual(result['candidates'], [])

    def test_infeasible_realization_is_retained_unexpected_error_is_not_gap_zero(self):
        original = module.prepare_canonical_candidate
        def fail_first(candidate, *args, **kwargs):
            if candidate.ramp_metering == self.control.ramp_metering:
                raise module.MeterCandidateInfeasible('explicit synthetic schedule-change rejection')
            return original(candidate, *args, **kwargs)
        with patch.object(module, 'prepare_canonical_candidate', fail_first):
            result = self.run_reachable()
        self.assertEqual(result['requested_count'], 4)
        self.assertEqual(len(result['rejected']), 1)
        self.assertEqual(result['rejected'][0]['stage'], 'canonical_realization')
        self.assertEqual(len(result['candidates'][0]['aliases']), 3)
        with patch.object(module, 'prepare_canonical_candidate', side_effect=RuntimeError('unexpected')):
            with self.assertRaisesRegex(RuntimeError, 'unexpected'):
                self.run_reachable()

    def test_full_cycle_ownership_nonfinite_and_provenance_contracts(self):
        for bad in (True, float('nan'), float('inf'), -1.):
            requests = copy.deepcopy(self.requests)
            label, values = requests['FW_W'][0]
            values[next(iter(values))] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.run_reachable(directional_requests=requests)
        bad = copy.deepcopy(self.requests)
        bad['FW_W'] = (('wrong_owner', dict(bad['FW_E'][0][1])),)
        with self.assertRaisesRegex(ValueError, 'ownership'):
            self.run_reachable(directional_requests=bad)
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.run_reachable(source_provenance={})
        self.cfg.network.control_area_meter_context['actuation']['real_world_ramp_metering']['max_green_sec'] = 9.
        with self.assertRaisesRegex(ValueError, 'max_green == cycle'):
            self.run_reachable()

    def test_changed_frozen_context_and_result_aliases_do_not_mutate_inputs(self):
        result = self.run_reachable()
        result['candidates'][0]['control'].diagnostics['nested']['preserved'].append(9)
        self.assertEqual(self.control.diagnostics['nested']['preserved'], [1, 2])
        original = module.prepare_canonical_candidate
        def mutate(candidate, cfg, **kwargs):
            out = original(candidate, cfg, **kwargs)
            cfg.network.control_area_meter_context['sim_sec'] += 1.
            return out
        with patch.object(module, 'prepare_canonical_candidate', mutate), self.assertRaisesRegex(ValueError, 'frozen inputs'):
            self.run_reachable()


if __name__ == '__main__':
    unittest.main()
