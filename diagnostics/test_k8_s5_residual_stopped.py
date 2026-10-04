"""K8-4: S5 residual stopped split (no double use) and the storage seed split diagnostic.

Declared unit tests (K8 predeclaration amendment 1 r2 §B.7 and §2 K8-4 row; DEFECTS.md §5.3 as corrected by B7;
OPT1_V2 spec amendment 1 §5.8-7 / §6.3 for the diagnostic schema the SA initializer reads):
  ResidualStoppedRuleTests  storage stopped = max(0, observed stopped - ready queue) / storage count for every
                            contiguous | stopped_instant link with a stopped observation (link 127 included);
                            ready > observed stopped is clipped at 0 and counted, never a ProjectionError;
                            constant and physical_branch links keep the K8-3 rule; queue/storage counts unchanged
  SeedSplitTests            storage_seed_split_by_link[link][storage] = {moving, stopped, due_moving_step,
                            due_stopped_step}: rows sum to what the seed scheduled per storage (±1e-9), due cells are
                            the seed's own steps, `unattributed` holds mass without a link part (0 for in_SC1001_W),
                            a kind the seed drops (due beyond the horizon) is 0 in every row, the split assertion
                            refuses a link part whose stopped exceeds its occupancy, seed off writes nothing
The real-state reproduction (+105 -> +15 shift 159.132 / 197.121 / 113.203, 61-state capture) is the K8-4 gate
(diagnostics/sdmpc_n31_20260924/k8_gates/k84_gate.py), not these tests. No VISSIM, no subprocess.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import observation_projection  # noqa: E402
from evaluation.controllers import vissim_stackelberg_adapter as adapter  # noqa: E402

GATE = 'in_SC1001_W'
SWITCHES = {'stopped_split': True, 'queue_contiguous': True, 'arrival_seed': True}


def _cfg(storage, movements, t_u=1.0):
    net = NS(urban_link_storage_veh=dict(storage), off_ramp_storage_link={}, urban_movements=dict(movements),
             ramps=[], boundary_out_links=[])
    return NS(network=net, simulation=NS(T_u_sec=t_u))


def _observation(counts, stopped, bins=None):
    local = {'link_counts': dict(counts), 'link_stopped_counts': dict(stopped)}
    if bins:
        local['queue_bins'] = dict(bins)
        local['queue_bin_m'] = 7.0
    return {'sim_sec': 2700.0, 'local_observation': local}


def _summary(cfg, state_json, mapping, switches=None):
    with mock.patch.dict(adapter._CFG_SWITCHES, switches or SWITCHES, clear=True), \
            mock.patch.object(adapter, '_LINK_GEOM_CACHE', {}):
        return adapter.build_local_observation_summary(state_json, cfg, mapping, {})


def _seed(cfg, summary, time_sec=2700.0, switches=None):
    state = NS(urban_arrival_buffer={}, time_sec=time_sec)
    with mock.patch.dict(adapter._CFG_SWITCHES, switches or SWITCHES, clear=True):
        stats = adapter.seed_urban_arrival_buffer(state, cfg, summary)
    return state, stats


# The SC1001 W example of the predeclaration (amendment 1 B7, spec amendment §5.8-7): at 2700 link 127 holds
# 110 vehicles, 62 stopped, a contiguous stop-line queue of 27; its storage share (83) feeds in_SC1001_W.
CFG_127 = _cfg({GATE: 400.0}, {'SC1001_W_to_N': {'origin': GATE, 'kind': 'boundary_in', 'beta': 1.0}})
MAP_127 = {'link_to_origins': {'127': [GATE]},
           'link_to_movements': {'127': [{'movement': 'SC1001_W_to_N', 'weight': 1.0}]}}
OBS_127 = _observation({'127': 110.0}, {'127': 62.0}, {'127|1|0': [14.0, 14.0], '127|2|0': [13.0, 13.0]})


class ResidualStoppedRuleTests(unittest.TestCase):
    def test_contiguous_link_127_uses_the_residual(self):
        s = _summary(CFG_127, OBS_127, MAP_127)
        self.assertEqual(s['urban_queue_source_by_link']['127'], 'contiguous')
        self.assertAlmostEqual(s['queue_count_by_link']['127'], 27.0, places=12)
        self.assertAlmostEqual(s['storage_count_by_link']['127'], 83.0, places=12)
        self.assertAlmostEqual(s['urban_link_storage_occupancy'][GATE], 83.0, places=12)
        # K8-4: 62 - 27 = 35 stopped in storage; the K8-3 rule would have put 83 * 62 / 110 = 46.78 there.
        self.assertAlmostEqual(s['urban_link_storage_stopped'][GATE], 35.0, places=9)
        self.assertGreater(83.0 * 62.0 / 110.0 - s['urban_link_storage_stopped'][GATE], 11.78)
        d = s['projection_diagnostics']
        self.assertEqual(d['residual_stopped_split_links'], 1.0)
        self.assertEqual(d['residual_stopped_ready_exceeds_stopped_links'], 0.0)
        self.assertEqual(d['residual_stopped_ready_exceeds_stopped_veh'], 0.0)
        self.assertEqual(s['urban_link_storage_by_link'][GATE]['127'][0], s['urban_link_storage_occupancy'][GATE])

    def test_stopped_instant_link_has_no_stopped_residual(self):
        cfg = _cfg({'S2': 100.0}, {'M2': {'origin': 'S2', 'kind': 'internal', 'beta': 1.0}})
        mapping = {'link_to_origins': {'L2': ['S2']}, 'link_to_movements': {'L2': [{'movement': 'M2'}]}}
        s = _summary(cfg, _observation({'L2': 20.0}, {'L2': 12.0}), mapping)
        self.assertEqual(s['urban_queue_source_by_link']['L2'], 'stopped_instant')
        self.assertAlmostEqual(s['queue_count_by_link']['L2'], 12.0, places=12)
        self.assertAlmostEqual(s['urban_link_storage_occupancy']['S2'], 8.0, places=12)
        # all 12 stopped vehicles are the ready queue already; the K8-3 rule put 8 * 12/20 = 4.8 stopped in storage
        self.assertLessEqual(s['urban_link_storage_stopped']['S2'], 1e-12)
        self.assertAlmostEqual(s['urban_movement_queue']['M2'], 12.0, places=12)

    def test_ready_queue_above_observed_stopped_is_clipped_and_counted(self):
        cfg = _cfg({'S3': 100.0}, {'M3': {'origin': 'S3', 'kind': 'internal', 'beta': 1.0}})
        mapping = {'link_to_origins': {'L3': ['S3']}, 'link_to_movements': {'L3': [{'movement': 'M3'}]}}
        obs = _observation({'L3': 40.0}, {'L3': 20.0}, {'L3|1|0': [30.0, 30.0]})
        s = _summary(cfg, obs, mapping)            # no ProjectionError
        self.assertEqual(s['urban_queue_source_by_link']['L3'], 'contiguous')
        self.assertAlmostEqual(s['queue_count_by_link']['L3'], 30.0, places=12)
        self.assertEqual(s['urban_link_storage_stopped']['S3'], 0.0)
        d = s['projection_diagnostics']
        self.assertEqual(d['residual_stopped_ready_exceeds_stopped_links'], 1.0)
        self.assertAlmostEqual(d['residual_stopped_ready_exceeds_stopped_veh'], 10.0, places=12)

    def test_constant_and_physical_branch_links_keep_the_k83_rule(self):
        cfg = _cfg({'S4': 100.0, 'S5': 100.0}, {'M4': {'origin': 'S4', 'kind': 'internal', 'beta': 1.0}})
        mapping = {'link_to_origins': {'L4': ['S4'], 'L5': ['S5']}, 'link_to_movements': {'L4': [{'movement': 'M4'}]},
                   'transit_storage_projection': {'L5': {}}}
        # L4: no stopped observation -> constant split (0.35 storage); L5: transit storage -> physical_branch
        s = _summary(cfg, _observation({'L4': 20.0, 'L5': 10.0}, {'L5': 3.0}), mapping)
        self.assertEqual(s['urban_queue_source_by_link']['L4'], 'constant')
        self.assertEqual(s['urban_queue_source_by_link']['L5'], 'physical_branch')
        self.assertAlmostEqual(s['urban_link_storage_occupancy']['S4'], 7.0, places=12)
        self.assertEqual(s['urban_link_storage_stopped']['S4'], 0.0)
        self.assertEqual(s['urban_link_storage_stopped']['S5'], 10.0 * min(1.0, max(0.0, 3.0 / 10.0)))
        self.assertEqual(s['projection_diagnostics']['residual_stopped_split_links'], 0.0)

    def test_link_without_movements_is_bit_identical_to_the_old_rule(self):
        cfg = _cfg({'S6': 100.0}, {})
        s = _summary(cfg, _observation({'L6': 7.0}, {'L6': 3.0}), {'link_to_origins': {'L6': ['S6']}})
        self.assertEqual(s['urban_queue_source_by_link']['L6'], 'stopped_instant')
        self.assertEqual(s['queue_count_by_link']['L6'], 0.0)
        old = 7.0 * min(1.0, max(0.0, 3.0 / 7.0))
        self.assertEqual(s['urban_link_storage_stopped']['S6'], old)

    def test_only_the_stopped_split_changes(self):
        """Queue, occupancy, speeds and every count of the projection equal the K8-3 rule's (computed here)."""
        s = _summary(CFG_127, OBS_127, MAP_127)
        self.assertAlmostEqual(sum(s['urban_movement_queue'].values()) + s['urban_link_storage_occupancy'][GATE],
                               110.0, places=12)
        self.assertEqual(s['urban_movement_queue']['SC1001_W_to_N'], s['queue_count_by_link']['127'])
        self.assertEqual(s['projection_diagnostics']['storage_assigned_veh'], s['urban_link_storage_occupancy'][GATE])
        self.assertEqual(s['projection_diagnostics']['unrepresented_vehicle_count_veh'], 0.0)


class SeedSplitTests(unittest.TestCase):
    def test_rows_sum_to_the_scheduled_seed_with_due_cells(self):
        cfg = _cfg({GATE: 400.0}, {'SC1001_W_to_N': {'origin': GATE, 'kind': 'boundary_in', 'beta': 1.0}})
        mapping = {'link_to_origins': {'127': [GATE], '10777': [GATE], '32': [GATE]},
                   'link_to_movements': {'127': [{'movement': 'SC1001_W_to_N'}]}}
        obs = _observation({'127': 110.0, '10777': 9.0, '32': 155.0}, {'127': 62.0, '10777': 4.0, '32': 0.0},
                           {'127|1|0': [27.0, 27.0]})
        s = _summary(cfg, obs, mapping)
        state, stats = _seed(cfg, s)
        split = s['projection_diagnostics']['storage_seed_split_by_link']
        self.assertEqual(split['unattributed'], {})
        rows = {link: split[link][GATE] for link in ('127', '10777', '32')}
        t0 = 2700
        for row in rows.values():
            self.assertEqual((row['due_moving_step'], row['due_stopped_step']), (t0 + 15, t0 + 105))
            self.assertIs(type(row['due_moving_step']), int)
        buf = state.urban_arrival_buffer[GATE]
        self.assertEqual(set(buf), {t0 + 15, t0 + 105})
        self.assertAlmostEqual(math.fsum(r['moving'] for r in rows.values()), buf[t0 + 15], delta=1e-9)
        self.assertAlmostEqual(math.fsum(r['stopped'] for r in rows.values()), buf[t0 + 105], delta=1e-9)
        self.assertAlmostEqual(rows['127']['stopped'], 35.0, places=9)
        self.assertAlmostEqual(rows['127']['moving'], 48.0, places=9)
        self.assertAlmostEqual(rows['10777']['stopped'], 4.0, places=12)   # stopped_instant without a queue entry
        self.assertEqual(rows['32']['stopped'], 0.0)
        self.assertEqual(rows['32']['moving'], 155.0)
        self.assertAlmostEqual(stats['moving_veh'] + stats['stopped_veh'], 110.0 - 27.0 + 9.0 + 155.0, places=9)
        self.assertEqual(s['projection_diagnostics']['storage_seed_split_rows'], 3.0)
        self.assertEqual(s['projection_diagnostics']['storage_seed_split_unattributed_veh'], 0.0)

    def test_two_storages_and_a_step_length(self):
        cfg = _cfg({'A': 50.0, 'B': 50.0}, {'MA': {'origin': 'A', 'kind': 'internal', 'beta': 1.0},
                                             'MB': {'origin': 'B', 'kind': 'internal', 'beta': 1.0}}, t_u=5.0)
        mapping = {'link_to_origins': {'L': ['A', 'B']}}
        s = _summary(cfg, _observation({'L': 10.0}, {'L': 4.0}), mapping)
        state, _ = _seed(cfg, s, time_sec=900.0)
        split = s['projection_diagnostics']['storage_seed_split_by_link']
        for storage in ('A', 'B'):
            row = split['L'][storage]
            self.assertEqual((row['due_moving_step'], row['due_stopped_step']), (180 + 3, 180 + 21))
            self.assertAlmostEqual(row['moving'] + row['stopped'], 5.0, places=12)
            self.assertAlmostEqual(row['stopped'], 2.0, places=12)
            self.assertAlmostEqual(state.urban_arrival_buffer[storage][183], row['moving'], delta=1e-12)
            self.assertAlmostEqual(state.urban_arrival_buffer[storage][201], row['stopped'], delta=1e-12)

    def test_mass_without_a_link_part_is_unattributed(self):
        cfg = _cfg({'S': 50.0, GATE: 50.0}, {'M': {'origin': 'S', 'kind': 'internal', 'beta': 1.0},
                                              'G': {'origin': GATE, 'kind': 'boundary_in', 'beta': 1.0}})
        summary = {'urban_link_storage_occupancy': {'S': 10.0, GATE: 6.0},
                   'urban_link_storage_stopped': {'S': 4.0, GATE: 2.0},
                   'urban_link_storage_by_link': {'S': {'L1': [7.0, 3.0]}, GATE: {'127': [6.0, 2.0]}},
                   'projection_diagnostics': {}}
        state, _ = _seed(cfg, summary)
        split = summary['projection_diagnostics']['storage_seed_split_by_link']
        self.assertEqual(split['unattributed'], {'S': {'moving': 2.0, 'stopped': 1.0}})
        self.assertNotIn(GATE, split['unattributed'])
        self.assertEqual(split['L1']['S']['moving'] + split['unattributed']['S']['moving'],
                         state.urban_arrival_buffer['S'][2715])
        self.assertEqual(split['L1']['S']['stopped'] + split['unattributed']['S']['stopped'],
                         state.urban_arrival_buffer['S'][2805])
        self.assertEqual(summary['projection_diagnostics']['storage_seed_split_unattributed_veh'], 3.0)

    def test_split_assertion_refuses_a_part_with_stopped_above_occupancy(self):
        cfg = _cfg({'S': 50.0}, {'M': {'origin': 'S', 'kind': 'internal', 'beta': 1.0}})
        summary = {'urban_link_storage_occupancy': {'S': 10.0}, 'urban_link_storage_stopped': {'S': 4.0},
                   'urban_link_storage_by_link': {'S': {'L1': [2.0, 3.0], 'L2': [8.0, 1.0]}},
                   'projection_diagnostics': {}}
        with self.assertRaises(RuntimeError):
            _seed(cfg, summary)

    def test_storage_outside_routing_and_seed_off_write_nothing(self):
        cfg = _cfg({'S': 50.0, 'X': 50.0}, {'M': {'origin': 'S', 'kind': 'internal', 'beta': 1.0}})
        summary = {'urban_link_storage_occupancy': {'S': 3.0, 'X': 5.0}, 'urban_link_storage_stopped': {'S': 1.0},
                   'urban_link_storage_by_link': {'S': {'L1': [3.0, 1.0]}, 'X': {'L2': [5.0, 0.0]}},
                   'projection_diagnostics': {}}
        state, _ = _seed(cfg, summary)
        split = summary['projection_diagnostics']['storage_seed_split_by_link']
        self.assertEqual(set(split), {'L1', 'unattributed'})
        self.assertNotIn('X', state.urban_arrival_buffer)
        off = {'urban_link_storage_occupancy': {'S': 3.0}, 'urban_link_storage_stopped': {'S': 1.0},
               'urban_link_storage_by_link': {'S': {'L1': [3.0, 1.0]}}, 'projection_diagnostics': {}}
        state, stats = _seed(cfg, off, switches={'arrival_seed': False})
        self.assertEqual(state.urban_arrival_buffer, {})
        self.assertEqual(off['projection_diagnostics'], {})
        self.assertEqual(stats, {'links': 0.0, 'moving_veh': 0.0, 'stopped_veh': 0.0, 'dropped_veh': 0.0})

    def test_kind_the_seed_does_not_schedule_is_zero_in_every_row(self):
        """A due beyond the 450 s horizon is dropped by the seed; its rows carry 0 for that kind."""
        cfg = _cfg({'S': 50.0}, {'M': {'origin': 'S', 'kind': 'internal', 'beta': 1.0}})
        summary = {'urban_link_storage_occupancy': {'S': 10.0}, 'urban_link_storage_stopped': {'S': 4.0},
                   'urban_link_storage_by_link': {'S': {'L1': [6.0, 3.0], 'L2': [4.0, 1.0]}},
                   'projection_diagnostics': {}}
        with mock.patch.object(adapter, '_ARRIVAL_TAU_STOPPED_SEC', 500.0):
            state, stats = _seed(cfg, summary)
        split = summary['projection_diagnostics']['storage_seed_split_by_link']
        self.assertEqual(stats['dropped_veh'], 4.0)
        self.assertEqual(state.urban_arrival_buffer['S'], {2715: 6.0})
        self.assertEqual([split[k]['S']['stopped'] for k in ('L1', 'L2')], [0.0, 0.0])
        self.assertEqual([split[k]['S']['moving'] for k in ('L1', 'L2')], [3.0, 3.0])
        self.assertEqual(split['unattributed'], {})

    def test_projection_error_is_not_raised_by_the_rule(self):
        """85e raises ProjectionError when ready > observed stopped; K8-4 clips and counts (DEFECTS §5.3)."""
        cfg = _cfg({'S': 100.0}, {'M': {'origin': 'S', 'kind': 'internal', 'beta': 1.0}})
        mapping = {'link_to_origins': {'L': ['S']}, 'link_to_movements': {'L': [{'movement': 'M'}]}}
        obs = _observation({'L': 10.0}, {'L': 0.0}, {'L|1|0': [6.0, 6.0]})
        try:
            s = _summary(cfg, obs, mapping)
        except observation_projection.ProjectionError as exc:  # pragma: no cover - the defect this test pins
            self.fail(f'ProjectionError raised: {exc}')
        self.assertEqual(s['projection_diagnostics']['residual_stopped_ready_exceeds_stopped_links'], 1.0)
        self.assertEqual(s['urban_link_storage_stopped']['S'], 0.0)
        _, stats = _seed(cfg, s)
        self.assertAlmostEqual(stats['moving_veh'], 4.0, places=12)


if __name__ == '__main__':
    unittest.main()
