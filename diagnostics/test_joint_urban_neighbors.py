"""Canonical neighborhood tests; no controller construction, state replay or COM.

Imports only pure signal helpers. The actual ControlAction class, projection,
phase-exchange method and writer SG functions are AST-extracted unchanged into
isolated modules, so importing a model/adapter is unnecessary. Neighborhood
definitions themselves are imported from the actual canonical module.
"""
from __future__ import annotations

import ast
import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import pickle
import sys
from types import ModuleType, SimpleNamespace, MethodType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import signal_actuation_contract as signals
from evaluation.controllers import signal_group_plan, action_csv_schema, plant_cycle
from evaluation.controllers import joint_owner_game as addresses
from evaluation.controllers import joint_owner_neighbors as proposed


def extracted(path, names, namespace, *, class_name=None):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
    nodes = tree.body if class_name is None else next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name).body
    selected = [n for n in nodes if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
    if {n.name for n in selected} != set(names):
        raise ValueError('Missing actual pure function/class')
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)] + selected, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(ROOT / path), 'exec'), namespace)


class UrbanNeighborTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {'RW_OFFSET_WRITER': 'experiment'})
        self.environment.start(); self.addCleanup(self.environment.stop)
        self.state_module = ModuleType('src.models.state')
        self.state_module.__dict__.update(dataclass=dataclass, field=field)
        self.modules = patch.dict(sys.modules, {
            'src': ModuleType('src'), 'src.models': ModuleType('src.models'),
            'src.models.state': self.state_module,
        })
        self.modules.start(); self.addCleanup(self.modules.stop)
        extracted('vendor/NumSim-mine/src/models/state.py', {'ControlAction', '_project_to_budget'}, self.state_module.__dict__)
        self.proposed = proposed
        self.plan = json.loads((ROOT / 'outputs/signal_group_actuation_plan_mainline_20260825.json').read_text(encoding='utf-8-sig'))
        self.mapping = json.loads((ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json').read_text(encoding='utf-8-sig'))
        self.tuning = json.loads((ROOT / 'diagnostics/contract_candidate_configs_v4/n7_area_beta300.json').read_text(encoding='utf-8-sig'))
        parameters = json.loads((ROOT / 'evaluation/parameters.json').read_text(encoding='utf-8-sig'))
        self.actual = {'Mapping': Mapping, 'signal_group_plan': signal_group_plan, 'action_csv_schema': action_csv_schema,
                       'RUNNER_CLEARANCE_SEC': plant_cycle.runner_clearance_sec()}
        extracted('evaluation/controllers/vissim_stackelberg_adapter.py',
                  {'plan_live_phases', 'signal_group_action_rows', '_segment_dsd_controls', '_as_float'}, self.actual)
        nodes = {r['id']: self.plan['controllers'][str(r['sc_no'])] for r in self.mapping['signals']}
        live = {s: tuple(p for p in signals.PHASES if n['phase_signal_groups'][p] and n['axis_green_sec'][p] > 0) for s, n in nodes.items()}
        # Small explicit geometry-free domain fixture, not a built traffic cfg.
        cycle = parameters['network']['cycle_length']
        low = parameters['network']['green_min']
        amber, all_red = self.actual['RUNNER_CLEARANCE_SEC']
        total = {s: cycle - len(live[s]) * (amber + all_red) for s in nodes}
        net = SimpleNamespace(signals=tuple(nodes), freeway_links=('FW_E', 'FW_W'),
            cycle_length=cycle, green_min=low,
            signal_live_phases=lambda s: live[s], signal_cycle_length=lambda s: cycle,
            signal_effective_green_total=lambda s: total[s],
            signal_green_max=lambda s: min(plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC[1], total[s] - (len(live[s]) - 1) * low),
            signal_actuation_contract={'nodes': copy.deepcopy(nodes), 'amber': amber, 'all_red': all_red, 'offset_writer': 'experiment'},
            freeway_vsl_zone_heads={d: [0, 5, 10, 15] for d in ('FW_E', 'FW_W')},
            freeway_vsl_zone_head_of_cell={d: [5 * min(i // 5, 3) for i in range(21)] for d in ('FW_E', 'FW_W')},
            freeway_vsl_zone_free=[0, 1, 2],
            ramp_to_freeway={m['model_ramp_key']: m['to_model_link'] for m in self.mapping['ramp_meters']})
        self.cfg = SimpleNamespace(network=net, mpc=SimpleNamespace(phase_price_exchange_steps_sec=tuple(self.tuning['phase_price']['exchange_steps_sec'])))
        self.ownership = addresses.build_ownership(self.cfg, self.mapping, self.plan, segment_dsd_controls=self.actual['_segment_dsd_controls'])
        values = {f: {} for f in addresses.LEVER_FIELDS}
        for a in self.ownership.addresses:
            values[a.field][a.key] = 0.0 if a.role == 'fixed_dead' or a.field == 'offsets' else (120.0 if a.field == 'vsl' else 100.0)
        self.control = self.state_module.ControlAction(**values, N_P_star=17.0, N_UF_star=400.0,
            diagnostics={'nested': {'keep': [1, 2]}}, inflow_outflow_allocation={'keep': 4.0})
        for s in nodes:
            v = signals.project_vector(net, s, {p: total[s] / len(live[s]) if p in live[s] else 0.0 for p in signals.PHASES})
            self.control.green_times.update({f'{s}_{p}': v[p] for p in signals.PHASES})
        ns = {}
        extracted('vendor/NumSim-mine/src/controllers/priced_wu_link_controller.py', {'_phase_exchange_candidates'}, ns, class_name='LinkAgentWuFollower')
        current = ns['_phase_exchange_candidates']
        tree = ast.parse((ROOT / 'evaluation/controllers/signal_actuation_contract.py').read_text(encoding='utf-8-sig'))
        outer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'install_controller')
        wrapper = next(n for n in ast.walk(outer) if isinstance(n, ast.FunctionDef) and n.name == 'exchange')
        ns = {'current': current, 'validate_vector': signals.validate_vector, 'project_vector': signals.project_vector,
              'native_clock_basis': signals.native_clock_basis, '_native_direction': signals._native_direction}
        exec(compile(ast.Module(body=[wrapper], type_ignores=[]), '<actual-installed-exchange-wrapper>', 'exec'), ns)
        ns['exchange']._physical_signal_contract = True
        # Existing fractions are read from the actual initializer's literal.
        tree = ast.parse((ROOT / 'vendor/NumSim-mine/src/controllers/wu_faithful_follower.py').read_text(encoding='utf-8-sig'))
        fractions = next(ast.literal_eval(n.value) for n in ast.walk(tree)
                         if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Attribute) and n.target.attr == 'offset_fractions')
        self.follower = SimpleNamespace(cfg=self.cfg, phase_price_in_gne=False, ramp_offset_enabled=True,
            offset_directive=None, offset_fractions=fractions,
            offset_marginal_price={'SC1': 0.0}, offset_marginal_price_ref={'SC1': 0.0},
            offset_marginal_price_trust_sec=cycle / 8.0)
        self.follower._phase_exchange_candidates = MethodType(ns['exchange'], self.follower)

    def generate(self, owner='SC1', control=None):
        return self.proposed.generate_urban_requests(self.follower, owner, control or self.control, ownership=self.ownership)

    def realize(self, bundle, control=None, **overrides):
        kwargs = dict(ownership=self.ownership, selected_plan=self.plan,
                      actuation=self.tuning['actuation'], metadata={'controller_variant': 'wu-link'},
                      signal_group_rows=self.actual['signal_group_action_rows'])
        kwargs.update(overrides)
        return self.proposed.realize_urban_requests(bundle, control or self.control, self.cfg, **kwargs)

    def test_existing_order_joint_product_and_command_dedupe(self):
        result = self.realize(self.generate())
        self.assertTrue(result['complete'])
        self.assertEqual(result['requested_count'], 52)  # 13 green points x (incumbent + 3 admitted offsets)
        self.assertEqual(len(result['candidates']), 39)  # 13 x 3 physical programs
        self.assertEqual([a[0]['kind'] for a in result['aliases'][:13]], ['incumbent'] + ['green'] * 12)
        self.assertTrue(any(a['kind'] == 'joint' for group in result['aliases'] for a in group))
        self.assertEqual(result['command_keys'], self.realize(self.generate())['command_keys'])

    def test_foreign_payload_input_and_returned_candidates_are_independent(self):
        saved = pickle.dumps(self.control)
        result = self.realize(self.generate())
        self.assertEqual(saved, pickle.dumps(self.control))
        for candidate in result['candidates']:
            addresses.assert_owner_transition(self.ownership, 'SC1', self.control, candidate)
            for key in ('N_P_star', 'N_UF_star', 'inflow_outflow_allocation', 'infeasibility', 'diagnostics'):
                self.assertEqual(getattr(candidate, key), getattr(self.control, key))
        result['candidates'][1].diagnostics['nested']['keep'].append(3)
        self.assertEqual(result['candidates'][0].diagnostics, self.control.diagnostics)
        self.assertEqual(saved, pickle.dumps(self.control))

    def test_headless_active_and_dead_recovery_preserved(self):
        result = self.realize(self.generate())
        self.assertTrue(any(c.green_times['SC1_p4'] != self.control.green_times['SC1_p4'] for c in result['candidates']))
        for owner, dead in (('SC7', 'p3'), ('SC16', 'p4'), ('SC107', 'p1'), ('SC108', 'p2'), ('SC109', 'p1')):
            for c in self.realize(self.generate(owner))['candidates']:
                self.assertEqual(c.green_times[f'{owner}_{dead}'], 0.0)
                self.assertEqual(c.vsl, self.control.vsl)
                self.assertEqual(c.ramp_metering, self.control.ramp_metering)

    def test_frozen_trust_and_source_derived_offset_lift(self):
        result = self.realize(self.generate())
        alias = next(a for group in result['aliases'] for a in group if a['kind'] == 'offset' and a['offset'] == 131.25)
        self.assertEqual(alias['offset_origin']['grid_raw_sec'], 131.25)
        self.assertEqual(alias['written_lift_sec'], -18.75)
        self.follower.offset_marginal_price = None
        result = self.realize(self.generate())
        half = next(a for group in result['aliases'] for a in group if a['kind'] == 'offset' and a['offset'] == 75.0)
        self.assertEqual(half['written_lift_sec'], -75.0)
        self.assertEqual(len(result['candidates']), 104)

    def test_rounding_wrap_aliases_and_after_rounding_trust(self):
        self.follower.offset_marginal_price = None
        self.follower.offset_fractions = (0.0, 1.0, 18.75049 / 150.0, 18.7504 / 150.0)
        result = self.realize(self.generate())
        self.assertEqual({c.offsets['SC1'] for c in result['candidates']}, {0.0, 18.75})
        self.assertEqual(len(result['candidates']), 26)
        self.follower.offset_marginal_price = {'SC1': 0.0}
        self.follower.offset_marginal_price_trust_sec = 18.7506
        self.follower.offset_fractions = (18.7506 / 150.0,)
        result = self.realize(self.generate())
        self.assertEqual(len(result['candidates']), 13)
        self.assertTrue(any(r['stage'] == 'written_offset_trust' for r in result['rejected']))

    def test_recall_rebases_without_hidden_refinement_or_new_step(self):
        first = self.realize(self.generate())
        next_control = first['candidates'][1]
        with self.assertRaisesRegex(ValueError, 'Stale'):
            self.realize(self.generate(), next_control)
        second = self.generate(control=next_control)
        self.assertEqual(second['base_green'], self.proposed._vector(next_control, 'SC1'))
        self.assertEqual(second['steps_sec'], (6.0,))
        self.assertTrue(any(abs(r['green']['p1'] - self.control.green_times['SC1_p1']) == 12 for r in second['requests']))

    def test_invalid_state_and_unsupported_domain_fail_closed(self):
        for attr, value in (('phase_price_in_gne', True), ('ramp_offset_enabled', False), ('offset_directive', {})):
            old = getattr(self.follower, attr); setattr(self.follower, attr, value)
            with self.subTest(attr=attr), self.assertRaises(ValueError): self.generate()
            setattr(self.follower, attr, old)
        for value in (float('nan'), float('inf'), True):
            bad = copy.deepcopy(self.control); bad.offsets['SC1'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): self.generate(control=bad)
        bad = copy.deepcopy(self.control); bad.offsets['SC1'] = 150.0
        with self.assertRaises(ValueError): self.generate(control=bad)
        with self.assertRaises(ValueError): self.generate('FW_E')
        self.cfg.network.signal_cycle_length = lambda _: 151.0
        with self.assertRaises(ValueError): self.generate()

    def test_plan_writer_and_physical_row_mismatches_fail_closed(self):
        bundle = self.generate()
        wrong = copy.deepcopy(self.plan); wrong['controllers']['1']['major_maps_to'] = 'p1'
        with self.assertRaises(ValueError): self.realize(bundle, selected_plan=wrong)
        with self.assertRaises(ValueError): self.realize(bundle, metadata={'suppress_signal_rows': True})
        with self.assertRaises(ValueError): self.realize(bundle, metadata={'controller_variant': 'no-control'})
        with self.assertRaises(ValueError): self.realize(bundle, signal_group_rows=lambda *a, **k: [])
        def duplicate(*a, **k):
            rows = self.actual['signal_group_action_rows'](*a, **k)
            return rows + rows[:1]
        with self.assertRaises(ValueError): self.realize(bundle, signal_group_rows=duplicate)
        self.cfg.network.signal_actuation_contract['nodes']['SC1']['major_maps_to'] = 'p1'
        with self.assertRaisesRegex(ValueError, 'Stale'): self.realize(bundle)

    def test_all_17_owner_budget_and_millisecond_grid(self):
        for owner in self.cfg.network.signals:
            result = self.realize(self.generate(owner))
            for candidate in result['candidates']:
                signals.validate_vector(self.cfg.network, owner, self.proposed._vector(candidate, owner))
            self.assertEqual(result['candidates'][0].green_times, self.control.green_times)

    def test_refinement_boundary_preserves_budget_without_scalar_reexpansion(self):
        boundary = copy.deepcopy(self.control)
        boundary.green_times.update({'SC1_p1': 20.0, 'SC1_p2': 78.0, 'SC1_p3': 20.0, 'SC1_p4': 20.0})
        bundle = self.generate(control=boundary)
        greens = [r for r in bundle['requests'] if r['kind'] == 'green']
        self.assertEqual(len(greens), 3)
        self.assertTrue(all(r['green']['p2'] == 72.0 for r in greens))
        result = self.realize(bundle, boundary)
        self.assertEqual(len(result['candidates']), 12)
        self.assertTrue(all(sum(self.proposed._vector(c, 'SC1').values()) == 138.0 for c in result['candidates']))


if __name__ == '__main__':
    unittest.main()
