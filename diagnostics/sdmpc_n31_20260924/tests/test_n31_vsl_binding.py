"""T2 (plan C11, C4(a,c,d,g), C10): parent-space VSL binding of the refined plant kernels.

The controller keeps its 21-cell namespace (FW_x__seg{0,5,10,15}); every one of
the 62 refined cells must read its PARENT zone's command, never the link-level
fallback. The component's own 31-index heads (canonical_harness:315-317) would
misread silently; the test shows that too.
"""
from __future__ import annotations

import copy
import types
import unittest

import n31_fixtures as fx
from evaluation.controllers import lane_plant_runtime as lpr

ZONE_VALUES = {0: 101.0, 5: 102.0, 10: 103.0, 15: 104.0}
SENTINEL = 33.0


def control_for(conf, road):
    from src.models.state import ControlAction
    control = ControlAction.uncontrolled(conf)
    control.vsl = {road: SENTINEL, **{f'{road}__seg{h}': v for h, v in ZONE_VALUES.items()}}
    return control


class BindingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sandbox = fx.V2Sandbox().__enter__()
        with fx.obs150_stub():
            cls.context = lpr.load_sources(cls.sandbox.manifest)
        cls.component = cls.context['component']
        params = cls.context['parameters']['by_direction']
        cls.unbound = {road: cls.component._config(road, params[road]) for road in cls.component.roads}

    @classmethod
    def tearDownClass(cls):
        cls.sandbox.__exit__(None, None, None)

    def bind(self, *, shares=(0.3, 0.7), heads=None, lanes='lane_km', origin=None):
        roads = self.component.roads
        cells = {r: [c for c in self.context['geometry']['cells'] if c['road'] == r] for r in roads}
        profile = {'lane_km': lambda c: c['lane_km'] / c['length_km'],       # LPR initialize (v2)
                   'effective_lanes': lambda c: c['effective_lanes']}[lanes]
        state = types.SimpleNamespace(
            time_sec=900,
            freeway_density={r: [10.0 + i for i in range(31)] for r in roads},
            freeway_speed={r: [None if i % 7 == 3 else 70.0 + i for i in range(31)] for r in roads},
            freeway_effective_lanes={r: [profile(c) for c in cells[r]] for r in roads},
            freeway_flow={r: [0.0] * 21 for r in roads})
        if origin is not None:
            state.mainline_origin_queue = dict(origin)
        net = types.SimpleNamespace(freeway_variable_cell_lengths=True,
                                    freeway_vsl_zone_heads=heads or {'FW_E': [0, 5, 10, 15], 'FW_W': [0, 5, 10, 15]},
                                    freeway_vsl_zone_free=[0, 1, 2], freeway_segment_length_profile_km={})
        cfg = types.SimpleNamespace(network=net)
        freeway = types.SimpleNamespace(configs=copy.deepcopy(self.unbound))
        binding = lpr._bind_refined(self.context, {'offramp_10643_lane_shares': list(shares)}, cfg, state, freeway)
        return binding, cfg, state, freeway, cells

    def test_parent_tables(self):
        binding, cfg, _, freeway, _ = self.bind()
        self.assertEqual(binding['vsl_zone_head_of_cell'], fx.EXPECTED_HEAD_OF_CELL)
        self.assertEqual(binding['vsl_command_space'], 'parent_21')
        for road, conf in freeway.configs.items():
            net = conf.network
            self.assertEqual(net.freeway_vsl_zone_heads[road], [0, 5, 10, 15])
            self.assertEqual(net.freeway_vsl_zone_head_of_cell[road], fx.EXPECTED_HEAD_OF_CELL[road])
            self.assertEqual(net.freeway_vsl_zone_of_cell[road],
                             [[0, 5, 10, 15].index(h) for h in fx.EXPECTED_HEAD_OF_CELL[road]])
            self.assertEqual(net.freeway_vsl_zone_free, [0, 1, 2])

    def test_every_refined_cell_reads_its_parent_zone(self):
        from src.models import state as st
        _, _, _, freeway, _ = self.bind()
        for road, conf in freeway.configs.items():
            control = control_for(conf, road)
            reads = [st.segment_vsl(control, road, c, conf) for c in range(31)]
            self.assertEqual(reads, [ZONE_VALUES[h] for h in fx.EXPECTED_HEAD_OF_CELL[road]], road)
            self.assertNotIn(SENTINEL, reads)

    def test_component_heads_would_misread(self):
        """Without the binding, 31-index heads read keys the controller never writes."""
        from src.models import state as st
        conf = self.unbound['FW_E']
        control = control_for(conf, 'FW_E')
        reads = [st.segment_vsl(control, 'FW_E', c, conf) for c in range(31)]
        self.assertIn(SENTINEL, reads)

    def test_zone_axis_reaches_parent_cells(self):
        from src.models import state as st
        _, _, _, freeway, _ = self.bind()
        conf = freeway.configs['FW_W']
        control = control_for(conf, 'FW_W')
        before = [st.segment_vsl(control, 'FW_W', c, conf) for c in range(31)]
        control.vsl['FW_W__seg10'] = 60.0
        after = [st.segment_vsl(control, 'FW_W', c, conf) for c in range(31)]
        changed = [c for c in range(31) if before[c] != after[c]]
        self.assertEqual(changed, list(range(15, 25)))

    def test_empty_cells_speed_flow_and_lengths(self):
        binding, cfg, state, freeway, cells = self.bind()
        for road, conf in freeway.configs.items():
            rows = conf.network.freeway_segment_params[road]
            empty = [i for i in range(31) if i % 7 == 3]
            self.assertEqual(binding['empty_cells_v_free'][road], empty)
            for i in empty:
                self.assertEqual(state.freeway_speed[road][i], rows[i]['v_free'])
            self.assertTrue(all(v is not None for v in state.freeway_speed[road]))
            self.assertEqual(len(state.freeway_flow[road]), 31)
            for d, v, lanes, q in zip(state.freeway_density[road], state.freeway_speed[road],
                                      state.freeway_effective_lanes[road], state.freeway_flow[road]):
                self.assertEqual(q, d * v * lanes)
            self.assertEqual(cfg.network.freeway_segment_length_profile_km[road], [c['length_km'] for c in cells[road]])

    def test_state_lanes_are_the_kernel_profile(self):
        """canonical_harness:314/:713-715: lane_km/length_km, which the geometry's effective_lanes misses by 1 ulp."""
        _, _, state, freeway, cells = self.bind()
        for road, conf in freeway.configs.items():
            self.assertEqual(state.freeway_effective_lanes[road], list(conf.network.freeway_segment_lanes[road]))
        self.assertTrue(any(c['effective_lanes'] != c['lane_km'] / c['length_km'] for r in cells for c in cells[r]))
        with self.assertRaisesRegex(ValueError, 'lane profiles differ'):
            self.bind(lanes='effective_lanes')

    def test_empty_speed_uses_calibrated_multiplier(self):
        """canonical_harness:716-717: the per-road row v_free after the direction multiplier."""
        _, _, state, freeway, _ = self.bind()
        params = self.context['parameters']['by_direction']['FW_W']
        base_rows = self.component.base.network.freeway_segment_params['FW_W']
        base_v = base_rows[3].get('v_free', self.component.base.network.v_free)
        self.assertAlmostEqual(state.freeway_speed['FW_W'][3], base_v * params.get('v_free_multiplier', 1.0), places=12)

    def test_offramp_split_record(self):
        binding, cfg, _, _, _ = self.bind(shares=(0.25, 0.75))
        self.assertEqual(cfg.network.lane_plant_10643_lane_split,
                         {'mode': 'observed_lane_shares_held', 'shares': [0.25, 0.75], 'information_cutoff_s': 900})
        self.assertEqual(binding['offramp_10643_lane_shares'], [0.25, 0.75])
        for bad in ((0.5,), (0.6, 0.6), (-0.1, 1.1), (float('nan'), 1.0)):
            with self.assertRaises(ValueError):
                self.bind(shares=bad)

    def test_origin_queue_must_start_empty(self):
        """C6: A1's admitted-rate forecast already carries the source backlog (BF:163 initial queue 0)."""
        self.bind(origin={'FW_E': 0.0, 'FW_W': 0.0})
        for origin in ({'FW_E': 2.5, 'FW_W': 0.0}, {'FW_E': 0.0, 'FW_W': 1e-9}):
            with self.assertRaisesRegex(ValueError, 'origin queue must start empty'):
                self.bind(origin=origin)

    def test_binding_requires_controller_zones(self):
        with self.assertRaises(ValueError):
            self.bind(heads={'FW_E': [0, 5, 10, 15]})
        with self.assertRaises(ValueError):
            self.bind(heads={'FW_E': [0, 5, 10, 15], 'FW_W': [0, 5, 10, 25]})


if __name__ == '__main__':
    unittest.main()
