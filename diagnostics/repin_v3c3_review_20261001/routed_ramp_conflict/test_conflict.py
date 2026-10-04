"""Exercise the existing runtime at an exit-before-merge boundary."""
import math
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from evaluation.controllers.lane_ramp_runtime import LaneRampRuntime
from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph as gap


class Buffer:
    lanes = 1
    def snapshot(self):
        return dict(connector_veh=10., outside_component_backlog_veh=0.)
    def advance_local_interval(self, **kwargs):
        self.arguments = kwargs
        return dict(accepted_merge_veh=0.)


class ConflictTests(unittest.TestCase):
    def run_runtime(self, through, exit_stock, *, enabled=True, past_ratio=.25):
        runtime = LaneRampRuntime.__new__(LaneRampRuntime)
        runtime.cycle_sec = 10.
        runtime.receiving_nodes = {'r': dict(critical_gap_sec=3.5, followup_sec=1.5)}
        runtime.lane_coupling = {}
        runtime.buffers = {'r': Buffer()}
        runtime.predebited = None
        net = NS(ramps=['r'], ramp_capacity_veh_h={'r': 3600.}, ramp_merge_segment_index={'r': 1},
                 off_ramps=['o'], off_ramp_segment_index={'o': 0}, off_ramp_split_ratio={'o': past_ratio},
                 offramp_route_inventory={'branches': {'o': dict(freeway='FW', source_cell=0)}} if enabled else None)
        cfg = NS(network=net, simulation=NS(T_f_sec=1., T_f_h=1/3600.))
        freeway = NS(time_sec=0., configs={'FW': cfg}, lanes={})
        state = NS(ramp_queue={'r': 10.}, freeway_density={'FW': [20., 10.]},
                   freeway_speed={'FW': [60., 60.]}, freeway_effective_lanes={'FW': [4., 4.]},
                   offramp_route_inventory_state={'cells': {'FW': [
                       {'observed|terminal': through, 'observed|o': exit_stock}, {'observed|terminal': 10.}]}})
        control = NS(ramp_metering={'r': 3600.})
        with patch('evaluation.controllers.area_freeway_accounting._mn.compute_ramp_release_flows',
                   return_value=({'r': 3600.}, {})), \
             patch('evaluation.controllers.control_area_objective.get_ledger', return_value=None), \
             patch('evaluation.controllers.control_area_objective.emit_transfer'), \
             patch('evaluation.controllers.sdmpc_prediction_cache.ramp_query_control', return_value=control):
            runtime.advance(state, control, NS(), freeway, service={'r': dict(
                mode='GREEN', green_sec=9., service_veh=4.2)})
        self.assertEqual(state.ramp_queue['r'], 10.)
        return runtime.buffers['r'].arguments['receiving_budget_veh']

    def test_current_routes_override_stale_split(self):
        for through, off in ((10., 0.), (0., 10.), (5., 5.)):
            with self.subTest(through=through):
                expected = gap(1200.*through/(through+off), 3.5, 1.5)/3600.
                self.assertAlmostEqual(self.run_runtime(through, off), expected, places=13)

    def test_stale_ratio_cannot_change_routed_receiving(self):
        values = [self.run_runtime(7., 3., past_ratio=r) for r in (0., .25, .9)]
        self.assertTrue(all(x == values[0] for x in values))

    def test_disabled_path_keeps_original_formula(self):
        for ratio in (0., .25, .9):
            self.assertEqual(self.run_runtime(7., 3., enabled=False, past_ratio=ratio),
                             gap(1200.*(1-ratio), 3.5, 1.5)/3600.)

    def test_matching_route_fraction_reproduces_static_case(self):
        self.assertEqual(self.run_runtime(7.5, 2.5), self.run_runtime(7.5, 2.5, enabled=False))

    def test_empty_current_stock_does_not_invent_conflicting_traffic(self):
        self.assertEqual(self.run_runtime(0., 0.), gap(0., 3.5, 1.5)/3600.)


if __name__ == '__main__':
    unittest.main(verbosity=2)
