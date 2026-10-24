"""The branch VSL model (d80faf9 A0.5_E4) in the v2 plant kernels (2026-09-24 port).

- The reference config carries the two model keys and the component installs them.
- 110 hold: both roads, 450 s, two synthetic states, stepping the aggregate
  kernels as LaneFreewayRuntime does. Every step's cost, diagnostics and cell
  state is bit-identical to the same component built without the VSL keys (the
  pre-port plant; the pre-port code was separately compared, see the port
  report). The FW_E transport state exists and conserves the physical stock.
- Below 110 the model is active and changes the rollout.
- The full-follower guard: a controller tuning with vsl_fd_response or
  component_vsl_transport is refused unless the caller is the lane-plant component.
- Cohort initialization (user decision 2026-09-24): each cell starts tagged with
  its governing upstream sign's command in the last applied action (110 before
  any); all-110 tags are bit-identical to the untagged cohorts.
AD (one-sided at 110, central below) is in test_n31_ad_smoke.py.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
import types
import unittest
from pathlib import Path

import n31_fixtures as fx
import make_reference_config

T0 = 900.0
CASES = {'moderate': (lambda i: 15.0 + (3 * i) % 20, lambda i: 95.0, 5200.0),
         'congested': (lambda i: 0.0 if i == 4 else 20.0 + (11 * i) % 60, lambda i: 40.0 + (13 * i) % 70, 7600.0)}


def bound_confs(reference_path):
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_refined_geometry import parents
    geometry = fx.load_json(fx.GEOMETRY)
    component = CanonicalFreewayModel(geometry, reference_path)
    params = fx.parameters()['by_direction']
    confs = {road: component._config(road, params[road]) for road in component.roads}
    cells = {r: [c for c in geometry['cells'] if c['road'] == r] for r in component.roads}
    state = types.SimpleNamespace(time_sec=int(T0), freeway_density={r: [20.0] * 31 for r in cells},
                                  freeway_speed={r: [80.0] * 31 for r in cells},
                                  freeway_effective_lanes={r: [c['lane_km'] / c['length_km'] for c in cells[r]] for r in cells},
                                  freeway_flow={})
    cfg = types.SimpleNamespace(network=types.SimpleNamespace(
        freeway_variable_cell_lengths=True, freeway_vsl_zone_heads={'FW_E': [0, 5, 10, 15], 'FW_W': [0, 5, 10, 15]},
        freeway_vsl_zone_free=[0, 1, 2], freeway_segment_length_profile_km={}))
    context = {'parents': parents(geometry), 'geometry': geometry, 'component': component,
               'document': {'vsl_command_space': 'parent_21'}}
    lpr._bind_refined(context, {'offramp_10643_lane_shares': [0.5, 0.5]}, cfg, state,
                      types.SimpleNamespace(configs=confs))
    return component, confs


def rollout(conf, road, rho, v, source, vsl, steps=450):
    from evaluation.controllers import area_freeway_accounting as acc
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    cfg = copy.deepcopy(conf)
    net = cfg.network
    lanes = net.freeway_segment_lanes[road]
    state = TrafficState.initial(cfg)
    state.time_sec = T0
    state.freeway_effective_lanes[road] = list(lanes)
    state.freeway_density[road] = [rho(i) for i in range(len(lanes))]
    state.freeway_speed[road] = [v(i) for i in range(len(lanes))]
    state.mainline_origin_queue[road] = 0.0
    state.urban_link_storage = dict(net.urban_link_storage_veh)
    control = ControlAction.uncontrolled(cfg)
    for owner in ('FW_E', 'FW_W'):
        control.vsl.update({f'{owner}__seg{i}': 110.0 for i in range(21)})
    control.vsl.update(vsl)
    rows = []
    for k in range(steps):
        net.off_ramp_split_ratio = {o: 0.12 for o in net.off_ramps}
        cost, diag = acc._freeway_substep_events(
            state, control, DemandStep({road: source}, {}, {}), cfg,
            offramp_capacity_veh_h={o: 900.0 + 30.0 * (k % 5) for o in net.off_ramps},
            ramp_release_veh_h={r: 500.0 + 40.0 * (k % 7) for r in net.ramps},
            ramp_release_diagnostics={'total_no_meter_flow': 0.0, 'mean_ramp_receiving_factor': 1.0},
            update_ramp_queues=False, include_ramp_queue_ttt=False, complete_allocator_scope=False)
        rows.append((cost, dict(diag), list(state.freeway_density[road]), list(state.freeway_speed[road]),
                     list(state.freeway_flow[road]), list(state.freeway_effective_lanes[road]),
                     state.mainline_origin_queue[road]))
        state.time_sec += cfg.simulation.T_f_sec
    return rows, getattr(state, '_component_vsl_exposure', {}).get(road)


class VSLModelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.component, cls.confs = bound_confs(fx.REFERENCE)
        reference = fx.load_json(fx.REFERENCE)
        for key in make_reference_config.VSL_KEYS:
            reference['freeway'].pop(key)
        handle, name = tempfile.mkstemp(prefix='_tmp_vsl_', suffix='.json', dir=fx.HERE)
        os.close(handle)
        try:
            Path(name).write_text(json.dumps(reference), encoding='utf-8')
            _, cls.legacy = bound_confs(name)
        finally:
            Path(name).unlink(missing_ok=True)

    def test_component_installs_the_branch_keys(self):
        for road, conf in self.confs.items():
            net = conf.network
            self.assertEqual(net.freeway_vsl_fd_response, {'FW_E': {'law': 'carlson', 'A': 0.5, 'E': 4.0, 'alpha': 0.0}})
            self.assertEqual(net.component_vsl_transport['FW_E']['sign_cells'], [0, 3, 5, 8, 14, 18, 26, 28])
            self.assertEqual(max(conf.freeway_follower.vsl_set), 110.0)
        for conf in self.legacy.values():
            self.assertFalse(hasattr(conf.network, 'freeway_vsl_fd_response'))
            self.assertFalse(hasattr(conf.network, 'component_vsl_transport'))

    def test_110_hold_is_bit_identical(self):
        for road in ('FW_E', 'FW_W'):
            for name, (rho, v, source) in CASES.items():
                with self.subTest(road=road, case=name):
                    new, exposure = rollout(self.confs[road], road, rho, v, source, {})
                    old, none = rollout(self.legacy[road], road, rho, v, source, {})
                    self.assertIsNone(none)
                    self.assertEqual(new, old)       # exact float equality of every step
                    if road == 'FW_E':
                        self.assertEqual({k for row in exposure.cohorts for k in row}, {110.0})
                        self.assertLess(exposure.max_residual, 1e-9)
                        stocks = [sum(row.values()) for row in exposure.cohorts]
                        self.assertEqual(len(stocks), 31)
                    else:
                        self.assertIsNone(exposure)

    def test_below_110_is_active_and_conserved(self):
        rho, v, source = CASES['congested']
        new, exposure = rollout(self.confs['FW_E'], 'FW_E', rho, v, source, {'FW_E__seg10': 80.0})
        old, _ = rollout(self.legacy['FW_E'], 'FW_E', rho, v, source, {'FW_E__seg10': 80.0})
        self.assertNotEqual([r[3] for r in new], [r[3] for r in old])
        self.assertLess(exposure.max_residual, 1e-9)
        tagged = {k for row in exposure.cohorts[14:26] for k in row}
        self.assertIn(80.0, tagged)
        # Upstream of the zone's first sign (cell 14) nobody has seen 80.
        self.assertEqual({k for row in exposure.cohorts[:14] for k in row}, {110.0})

    def test_full_follower_guard(self):
        from evaluation.controllers import runtime_setup
        tuning = {'freeway': {'vsl_fd_response': {'FW_E': {'law': 'carlson', 'A': 0.5, 'E': 4.0, 'alpha': 0.0}}}}
        with self.assertRaisesRegex(ValueError, 'component-only'):
            runtime_setup.configure_freeway_runtime(None, None, tuning, None)
        # The transport key alone is also refused outside the component (it would be dead there).
        tuning = {'freeway': {'component_vsl_transport': {'FW_E': {'sign_cells': [0], 'initial_command': 110,
                                                                   'ramp_command': 110}}}}
        with self.assertRaisesRegex(ValueError, 'component_vsl_transport is component-only'):
            runtime_setup.configure_freeway_runtime(None, None, tuning, None)
        tuning = fx.build_full_tuning()
        self.assertNotIn('vsl_fd_response', tuning['freeway'])
        self.assertNotIn('component_vsl_transport', tuning['freeway'])

    def test_sign_cells_follow_the_network(self):
        self.assertEqual(make_reference_config.sign_cells(), [0, 3, 5, 8, 14, 18, 26, 28])
        self.assertNotEqual(make_reference_config.EXPECTED_SIGN_CELLS, make_reference_config.HANDOFF_SIGN_CELLS)

    # ------------------------------------------------ cohort initialization (user decision 2026-09-24)
    @staticmethod
    def applied(changes):
        """A last applied action: every FW_E/FW_W cell key at 110, then `changes`, link keys = min."""
        vsl = {f'{owner}__seg{i}': 110.0 for owner in ('FW_E', 'FW_W') for i in range(21)}
        vsl.update(changes)
        for owner in ('FW_E', 'FW_W'):
            vsl[owner] = min(vsl[f'{owner}__seg{i}'] for i in range(21))
        return vsl

    def test_cohort_init_seg10_at_90(self):
        """seg10 = 90: cells after sign 14/18 (to sign 26) tagged 90, ramps downstream enter at 110."""
        from evaluation.controllers import freeway_fd as fd
        net = self.confs['FW_E'].network
        spec, head_of = net.component_vsl_transport['FW_E'], net.freeway_vsl_zone_head_of_cell['FW_E']
        zone10 = {f'FW_E__seg{i}': 90.0 for i in range(10, 15)}
        commands = fd.applied_cohort_commands(spec, 'FW_E', head_of, self.applied(zone10), 110.0)
        self.assertEqual(commands, [110.0] * 14 + [90.0] * 12 + [110.0] * 5)
        # Cell 25 already reads zone 15 (110) but its vehicles last passed sign 18 (90).
        self.assertEqual((head_of[14], head_of[25], head_of[26]), (10, 15, 15))
        # First decision / nothing applied: every cell at the entry command.
        self.assertEqual(fd.applied_cohort_commands(spec, 'FW_E', head_of, None, 110.0), [110.0] * 31)
        # The display read equals the plant's own segment_vsl at every sign cell.
        from src.models import metanet as mn
        from src.models.state import ControlAction
        control = ControlAction(vsl=self.applied(zone10))
        for sign in spec['sign_cells']:
            self.assertEqual(commands[sign], mn.segment_vsl(control, 'FW_E', sign, self.confs['FW_E']))
        # Held 90: one step later the initial tags are kept in 14..25 and on-ramp
        # vehicles (RM_C10490 -> cell 21, RM_C10484 -> cell 23) enter at ramp_command 110.
        conf = copy.deepcopy(self.confs['FW_E'])
        conf.network.component_vsl_initial_commands = {'FW_E': tuple(commands)}
        rho, v, source = CASES['congested']
        _, exposure = rollout(conf, 'FW_E', rho, v, source, zone10, steps=1)
        for cell in range(14, 26):
            self.assertIn(90.0, exposure.cohorts[cell], cell)
        ramp_cells = sorted(r['to_cell'] for r in self.component.ramps.values() if r['road'] == 'FW_E')
        self.assertEqual(ramp_cells, [10, 12, 21, 23])
        for cell in (21, 23):
            self.assertEqual(set(exposure.cohorts[cell]), {90.0, 110.0}, cell)
        for cell in (10, 12):
            self.assertEqual(set(exposure.cohorts[cell]), {110.0}, cell)
        self.assertEqual({k for row in exposure.cohorts[:14] for k in row}, {110.0})
        self.assertLess(exposure.max_residual, 1e-9)

    def test_cohort_init_all_110_is_bit_identical(self):
        from evaluation.controllers import freeway_fd as fd
        net = self.confs['FW_E'].network
        tags = fd.applied_cohort_commands(net.component_vsl_transport['FW_E'], 'FW_E',
                                          net.freeway_vsl_zone_head_of_cell['FW_E'], self.applied({}), 110.0)
        self.assertEqual(tags, [110.0] * 31)
        conf = copy.deepcopy(self.confs['FW_E'])
        conf.network.component_vsl_initial_commands = {'FW_E': tuple(tags)}
        for name, (rho, v, source) in CASES.items():
            with self.subTest(case=name):
                tagged, a = rollout(conf, 'FW_E', rho, v, source, {})
                plain, b = rollout(self.confs['FW_E'], 'FW_E', rho, v, source, {})
                self.assertEqual(tagged, plain)
                self.assertEqual((a.cohorts, a.tangents), (b.cohorts, b.tangents))

    def test_cohort_init_changes_a_held_below_110_rollout(self):
        """Holding 90 after 90 was applied: the vehicles already inside the zone respond now."""
        from evaluation.controllers import freeway_fd as fd
        net = self.confs['FW_E'].network
        zone10 = {f'FW_E__seg{i}': 90.0 for i in range(10, 15)}
        tags = fd.applied_cohort_commands(net.component_vsl_transport['FW_E'], 'FW_E',
                                          net.freeway_vsl_zone_head_of_cell['FW_E'], self.applied(zone10), 110.0)
        conf = copy.deepcopy(self.confs['FW_E'])
        conf.network.component_vsl_initial_commands = {'FW_E': tuple(tags)}
        rho, v, source = CASES['congested']
        tagged, _ = rollout(conf, 'FW_E', rho, v, source, zone10, steps=30)
        reset, _ = rollout(self.confs['FW_E'], 'FW_E', rho, v, source, zone10, steps=30)
        self.assertNotEqual([r[3] for r in tagged], [r[3] for r in reset])
        # Speeds upstream of the zone's first sign are untouched in the first step.
        self.assertEqual(tagged[0][3][:14], reset[0][3][:14])

    def test_cohort_init_rejects_bad_tags(self):
        from evaluation.controllers import freeway_fd as fd
        spec = dict(sign_cells=[0], initial_command=110.0, ramp_command=110.0)
        with self.assertRaisesRegex(ValueError, 'cover every cell'):
            fd.VSLExposure([1.0, 2.0], spec, 110.0, [110.0])
        for bad in (120.0, 0.0, float('nan'), True):
            with self.assertRaisesRegex(ValueError, 'Invalid initial VSL cohort command'):
                fd.VSLExposure([1.0, 2.0], spec, 110.0, [110.0, bad])
        with self.assertRaisesRegex(ValueError, 'Invalid applied VSL command'):
            fd.applied_cohort_commands(spec, 'FW_E', [0, 0], {'FW_E__seg0': 120.0}, 110.0)
        x = fd.VSLExposure([1.0, 2.0], spec, 110.0, [90.0, 70.0])
        self.assertEqual((x.cohorts, x.tangents), ([{90.0: 1.0}, {70.0: 2.0}], [{90.0: 0.0}, {70.0: 0.0}]))

    def test_last_applied_action_source(self):
        """lane_plant_runtime reads the runner's previous (= last applied) action; none -> 110."""
        from evaluation.controllers import lane_plant_runtime as lpr
        self.assertEqual(lpr.applied_vsl_from_previous(None), (None, {'source': 'no_previous_action'}))
        self.assertEqual(lpr.applied_vsl_from_previous(''), (None, {'source': 'no_previous_action'}))
        with tempfile.TemporaryDirectory(dir=fx.HERE) as tmp:
            missing = Path(tmp) / 'action_000750.json'
            with self.assertRaisesRegex(ValueError, 'missing'):
                lpr.applied_vsl_from_previous(str(missing))
            # An SDMPC three-block plan: only block zero (top-level vsl) was written.
            zone10 = {f'FW_E__seg{i}': 90.0 for i in range(10, 15)}
            future = self.applied({f'FW_E__seg{i}': 50.0 for i in range(10, 15)})
            document = {'vsl': self.applied(zone10), 'metadata': {'sim_sec': 2850.0},
                        'diagnostics': {'sdmpc_prediction_sequence': {'schema': 'sdmpc-sequence/v1',
                                                                      'future': [{'vsl': future}] * 2}}}
            path = Path(tmp) / 'action_002850.json'
            path.write_text(json.dumps(document), encoding='utf-8')
            vsl, source = lpr.applied_vsl_from_previous(str(path))
            self.assertEqual(vsl, self.applied(zone10))
            self.assertEqual((source['sim_sec'], source['sdmpc_applied_receipt']), (2850.0, False))
            Path(str(path) + '.applied').write_text('2850\n', encoding='utf-16')
            self.assertTrue(lpr.applied_vsl_from_previous(str(path))[1]['sdmpc_applied_receipt'])
            # The canonical v2 hook tags the per-road plant configs.
            confs = copy.deepcopy(self.confs)
            record = lpr._initialize_vsl_cohorts(types.SimpleNamespace(configs=confs), str(path))
            self.assertTrue(record['enabled'])
            self.assertEqual(record['commands']['FW_E'], [110.0] * 14 + [90.0] * 12 + [110.0] * 5)
            self.assertEqual(confs['FW_E'].network.component_vsl_initial_commands['FW_E'],
                             tuple(record['commands']['FW_E']))
            self.assertFalse(hasattr(confs['FW_W'].network, 'component_vsl_initial_commands'))
            first = lpr._initialize_vsl_cohorts(types.SimpleNamespace(configs=copy.deepcopy(self.confs)), None)
            self.assertEqual((first['source'], first['commands']['FW_E']), ('no_previous_action', [110.0] * 31))
            path.write_text(json.dumps({'metadata': {}}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'lacks its VSL command map'):
                lpr.applied_vsl_from_previous(str(path))


if __name__ == '__main__':
    unittest.main()
