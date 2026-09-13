"""Analytic fixed-meter intervals and sparse physical price bases, no rollout."""
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from diagnostics import test_joint_price_field as prices
from evaluation.controllers import area_meter_finalization as meters
from evaluation.controllers import joint_owner_neighbors as neighbors
from evaluation.controllers.signal_group_plan import SignalGroupPlanError
from evaluation.controllers import vissim_stackelberg_adapter as adapter


def fixed_fixture():
    f, a, edges, truth = prices.fixture(fixed_meter_rate=1800.)
    mapping = {'ramp_meters': [{'id': r+'_'+str(i), 'model_ramp_key': r, 'connector': n*2+i,
        'sc_no': 9100+n*2+i, 'sg_no': 1} for n, r in enumerate(f.cfg.network.ramps) for i in (1, 2)]}
    tuning = {'actuation': {'real_world_ramp_metering': {'allocation': 'measured_table',
        'write_back_realized': True, 'cycle_sec': 10., 'min_green_sec': 2., 'max_green_sec': 10.}}}
    raw = {'sim_sec': 1050., 'local_observation': {'far_measurement': {'link_volume_veh_h': {
        str(m['connector']): 200. for m in mapping['ramp_meters']}}}}
    meters.configure(adapter, f.cfg, tuning, mapping, raw, None, NS(local_observation_summary={}))
    a.diagnostics = {}
    meters.finalize(a, f.cfg)
    entries = []
    limits = {'green_times': 6., 'offsets': 60., 'vsl': 40., 'ramp_metering': 300.}
    for field in neighbors.LEVER_FIELDS:
        entries.extend((field, key, value, limits[field], f.cfg.network.signal_cycle_length(key) if field == 'offsets' else None)
                       for key, value in getattr(a, field).items())
    box = neighbors.FixedMoveBox(tuple(entries), neighbors._key({field: dict(getattr(a, field)) for field in neighbors.LEVER_FIELDS}))
    proof = neighbors.fixed_meter_coordinate_proofs(f.cfg, a, box)
    return f, a, edges, box, proof


class FixedMeterPriceProofTests(unittest.TestCase):
    def historical_fixture(self):
        f, a, edges, box, _ = fixed_fixture()
        context = f.cfg.network.control_area_meter_context
        physical = adapter.real_world_ramp_meter_actions(deepcopy(a), f.cfg,
            context['actuation'], context['mapping'])
        historical = meters.prepare_historical_meter_reference(a, f.cfg,
            written_meter_rows=[{'kind': 'ramp_meter', 'id': mid, 'sc_no': int(row['sc_no']),
                'rate_vph': round(row['rate_vph'], 3), 'green_sec': round(row['green_sec'], 3)}
                for mid, row in physical.items()],
            source_provenance={'fixture': 'verified earlier eight writer rows'})['previous']
        context['sim_sec'] += 150.
        context['raw']['local_observation']['far_measurement']['link_volume_veh_h'] = {
            key: 500. for key in context['raw']['local_observation']['far_measurement']['link_volume_veh_h']}
        return f, historical, box

    def test_historical_box_uses_current_hints_but_preserves_actual_commands(self):
        f, historical, box = self.historical_fixture()
        before = deepcopy((vars(historical), f.cfg.network.control_area_meter_context, box))
        with self.assertRaisesRegex(ValueError, 'changed or unfinalized'):
            meters.assert_writer(historical, f.cfg, require_scored=True)
        held = meters.prepare_held_actual_reference(historical, f.cfg)
        expected = neighbors.fixed_meter_coordinate_proofs(f.cfg, held, box)
        proof = neighbors.fixed_meter_coordinate_proofs(f.cfg, historical, box)
        self.assertEqual(proof, expected)
        self.assertEqual(proof['anchor_token'], box.anchor_token)
        self.assertEqual(proof['context_sha256'], meters._context(f.cfg)[1])
        self.assertEqual({row['open_total_veh_h'] for row in proof['meters'].values()}, {1000.})
        self.assertEqual({tuple(row['request_interval_veh_h']) for row in proof['meters'].values()}, {(1500., 1800.)})
        self.assertEqual(before, (vars(historical), f.cfg.network.control_area_meter_context, box))
        self.assertEqual(neighbors.validate_fixed_meter_coordinate_proofs(f.cfg, historical,
            proof, move_box=box), historical.ramp_metering)

    def test_historical_proof_and_physical_definition_are_not_bypassed(self):
        for kind in ('history', 'physical_command', 'mapping', 'unproven_old_marker'):
            f, historical, box = self.historical_fixture()
            if kind == 'history':
                historical.diagnostics[meters.HISTORICAL_REFERENCE]['proof_sha256'] = 'changed'
            elif kind == 'physical_command':
                mid = next(iter(historical.diagnostics[meters.HISTORICAL_REFERENCE]['commands']))
                historical.diagnostics[mid] = -1.
            elif kind == 'mapping':
                f.cfg.network.control_area_meter_context['mapping']['ramp_meters'][0]['sc_no'] += 1
            else:
                historical.diagnostics.pop(meters.HISTORICAL_REFERENCE)
            before = deepcopy((vars(historical), f.cfg.network.control_area_meter_context, box))
            with self.subTest(kind=kind), patch.object(meters, 'finalize',
                    side_effect=AssertionError('Invalid history must fail before allocation')):
                with self.assertRaises(ValueError):
                    neighbors.fixed_meter_coordinate_proofs(f.cfg, historical, box)
            self.assertEqual(before, (vars(historical), f.cfg.network.control_area_meter_context, box))

    def test_all_requests_above_demand_are_fixed_not_unknown_zero_gradients(self):
        f, a, edges, box, proof = fixed_fixture()
        self.assertEqual(set(proof['meters']), set(f.cfg.network.ramps))
        for row in proof['meters'].values():
            self.assertEqual(row['request_interval_veh_h'], [1500., 1800.])
            self.assertEqual(row['open_total_veh_h'], 400.)
        field = prices.api.fit_joint_price_field(f, a, edges,
            fixed_meter_proofs=proof, fixed_move_box=box)
        self.assertEqual(field['holder_values']['metering_marginal_price'], dict.fromkeys(f.cfg.network.ramps, 0.))
        self.assertEqual(field['fixed_meter_proofs'], proof)
        for owner in f.cfg.network.freeway_links:
            self.assertEqual(field['owner_fits'][owner]['dimension'], 3)
            self.assertIn('not identified derivatives', field['owner_fits'][owner]['fixed_meter_price_convention'])
        report = prices.api.install_joint_price_field(f, a, field,
            expected_owners=tuple(f.cfg.network.signals)+tuple(f.cfg.network.freeway_links),
            expected_context=field['context'], nuf_mode='dual')
        self.assertEqual(f._joint_fixed_meter_proofs, proof)
        self.assertEqual(report['fixed_meter_proofs'], proof)
        with self.assertRaisesRegex(ValueError, 'unidentified active'):
            prices.api.fit_joint_price_field(f, a, edges)

    def test_forged_changed_context_and_different_active_box_fail(self):
        f, a, edges, box, proof = fixed_fixture()
        bad = deepcopy(proof)
        bad['meters']['R1']['open_total_veh_h'] = 399.
        with self.assertRaisesRegex(ValueError, 'source/context/anchor'):
            neighbors.validate_fixed_meter_coordinate_proofs(f.cfg, a, bad, move_box=box)
        altered = neighbors.FixedMoveBox(tuple((field, key, ref, limit+1 if field == 'ramp_metering' else limit, cycle)
            for field, key, ref, limit, cycle in box.entries), box.anchor_token)
        with self.assertRaisesRegex(ValueError, 'active decision box'):
            prices.api.fit_joint_price_field(f, a, edges, fixed_meter_proofs=proof, fixed_move_box=altered)
        f.cfg.network.control_area_meter_context['raw']['local_observation']['far_measurement']['link_volume_veh_h']['1'] = 1100.
        with self.assertRaises(ValueError):
            neighbors.validate_fixed_meter_coordinate_proofs(f.cfg, a, proof, move_box=box)

    def test_high_demand_leaves_meter_coordinates_unidentified_until_probed(self):
        f, a, edges, box, proof = fixed_fixture()
        context = f.cfg.network.control_area_meter_context
        physical = adapter.real_world_ramp_meter_actions(deepcopy(a), f.cfg, context['actuation'], context['mapping'])
        historical = meters.prepare_historical_meter_reference(a, f.cfg,
            written_meter_rows=[{'kind': 'ramp_meter', 'id': mid, 'sc_no': int(row['sc_no']),
                'rate_vph': round(row['rate_vph'], 3), 'green_sec': round(row['green_sec'], 3)} for mid, row in physical.items()],
            source_provenance={'fixture': 'actual eight canonical rows'})['previous']
        context['sim_sec'] += 150.
        context['raw']['local_observation']['far_measurement']['link_volume_veh_h'] = {
            key: 1200. for key in context['raw']['local_observation']['far_measurement']['link_volume_veh_h']}
        a = meters.prepare_held_actual_reference(historical, f.cfg)
        movable = neighbors.fixed_meter_coordinate_proofs(f.cfg, a, box)
        self.assertEqual(movable['meters'], {})
        with self.assertRaisesRegex(ValueError, 'unidentified active'):
            prices.api.fit_joint_price_field(f, a, edges, fixed_meter_proofs=movable, fixed_move_box=box)


class SparsePriceBasisTests(unittest.TestCase):
    def test_urban_basis_uses_fallback_when_first_requested_basis_is_outside_box(self):
        from diagnostics.test_joint_neighbor_callbacks import JointNeighborCallbackTests
        f = JointNeighborCallbackTests(); f.setUp(); self.addCleanup(f.doCleanups)
        f.cfg.mpc.phase_price_exchange_steps_sec = (6., 3.)
        limits = {'green_sec': 3., 'offset_sec': 75., 'vsl_kmh': 40., 'meter_veh_h': 300.}
        cb = f.make(decision_anchor=f.initial, move_limits=limits, price_probe=True)
        result = cb['neighbor_evidence']('SC1', f.initial, f.context)
        self.assertEqual(len(result['candidates']), 5)
        self.assertLess(len(result['candidates']), result['source_bundle']['requested_count'])
        self.assertTrue(any(row['stage'] == 'written_fixed_decision_box' for row in result['source_bundle']['rejected']))
        self.assertTrue(all(not cb['move_box'].violations(u) for u in result['candidates']))
        normal = f.make(decision_anchor=f.initial, move_limits=limits)
        full = normal['neighbors']('SC1', f.initial, f.context)
        self.assertGreater(len(full.candidates), len(result['candidates']))
        self.assertTrue(all(any(u.green_times == v.green_times and u.offsets == v.offsets for v in full.candidates)
                            for u in result['candidates']))


class NativeConcurrentPriceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json
        from dataclasses import replace
        from pathlib import Path
        import sys
        from evaluation.controllers import signal_group_plan as plans
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / 'plant' / 'src'))
        from vissim_strict.signal_program import parse_sig
        raw = json.loads((root / 'outputs/signal_group_actuation_plan_mainline_20260825.json').read_text(encoding='utf-8'))
        audit = json.loads((root / 'reports/20260911_decision_runtime/current_native_anchor_source_audit.json').read_text(encoding='utf-8'))
        row = next(row for row in audit['controllers'] if row['sc'] == '7')
        plan = plans.node_plan_from_json(raw['controllers']['7'])
        basis = plans.build_native_clock_basis(plan, parse_sig(root / row['program'], 1),
            amber_sec=3., all_red_sec=0.)
        cls.native_node = plans.node_plan_to_json(replace(plan, native_clock_basis=basis))

    def fixture(self, *, changes=None, bind_context=True, coordinate_cycle=120.):
        f, a, edges, truth = prices.fixture()
        old_live, old_cycle = f.cfg.network.signal_live_phases, f.cfg.network.signal_cycle_length
        f.cfg.network.signal_live_phases = lambda s: ('p1', 'p2', 'p4') if s == 'SC7' else old_live(s)
        f.cfg.network.signal_cycle_length = lambda s: 120. if s == 'SC7' else old_cycle(s)
        f.cfg.network.signal_actuation_contract = {'nodes': {'SC7': deepcopy(self.native_node)}}
        a.green_times.update(SC7_p1=67., SC7_p2=90., SC7_p3=0., SC7_p4=24.)
        a.offsets['SC7'] = 119.
        native = {k: v for k, v in a.green_times.items() if k.startswith('SC7_')}
        native['SC7'] = 119.
        for rows in edges.values():
            for edge in rows:
                if bind_context:
                    edge['context']['native_clock_nodes'] = {'SC7': deepcopy(self.native_node)}
                for side in ('base', 'probe'):
                    edge['model_owner_values'][side]['SC7'] = dict(native)
        sample = edges['SC1'][0]
        owners = tuple(edges)
        base = {'objective_veh_h': 100., 'local_base_costs': dict.fromkeys(owners, 10.),
            'context': deepcopy(sample['context']), 'response_token': 'same-base', 'local_cost_response_token': 'same-base',
            'physical_owner_tokens': {o: o+'-base' for o in owners},
            'model_owner_values': deepcopy(sample['model_owner_values']['base']),
            'price_or_quantity_terms_included': False, 'local_cost_contains_omega_beta': False}
        rows = []
        truth = {'SC7_p1': 2., 'SC7_p2': 3., 'SC7_p3': 0., 'SC7_p4': -3., 'SC7': .25}
        if changes is None:
            changes = ({'SC7_p1': -6.}, {'SC7_p2': -6., 'SC7_p4': 6.}, {'SC7': -2.})
        for i, change in enumerate(changes):
            direction = {k: change.get(k, 0.) for k in native}
            after = {k: value+direction[k] for k, value in native.items()}
            probe = deepcopy(base)
            probe['model_owner_values']['SC7'] = after
            probe['response_token'] = probe['local_cost_response_token'] = 'native-probe-'+str(i)
            probe['physical_owner_tokens']['SC7'] = 'native-physical-'+str(i)
            probe['objective_veh_h'] += sum(truth[k]*v for k, v in direction.items())
            coordinate = {'owner': 'SC7', 'kind': 'joint_direction', 'parameter_unit': '1', 'displacement': 1.,
                'base_values': native, 'probe_values': after, 'direction': direction,
                'address_kinds': {k: 'offset' if k == 'SC7' else 'green' for k in native},
                'address_owners': dict.fromkeys(native, 'SC7'), 'offset_cycles': {'SC7': coordinate_cycle}}
            rows.append(prices.api.matched_external_secant(base, probe, owners=owners, owner='SC7', coordinate=coordinate))
        edges['SC7'] = rows
        return f, a, edges

    def test_p1_is_independent_and_p2_p4_use_their_own_zero_sum_gauge(self):
        f, a, edges = self.fixture()
        field = prices.api.fit_joint_price_field(f, a, edges)
        observed = field['holder_values']['signal_phase_price']['SC7']
        for key, expected in {'p1': 2., 'p2': 3., 'p3': 0., 'p4': -3.}.items():
            self.assertAlmostEqual(observed[key], expected)
        self.assertAlmostEqual(sum(observed.values()), 2.)
        prices.api.install_joint_price_field(f, a, field, expected_owners=tuple(edges),
            expected_context=field['context'], nuf_mode='dual')
        self.assertEqual(f.signal_phase_price['SC7'], observed)
        # Without the opt-in clock, these same p1-only edges must fail the old
        # serial fixed-total contract, rather than silently changing its gauge.
        del f.cfg.network.signal_actuation_contract
        with self.assertRaisesRegex(ValueError, 'native clock nodes differ'):
            prices.api.fit_joint_price_field(f, a, edges)

    def test_missing_opt_in_retains_legacy_full_green_sum(self):
        with self.assertRaisesRegex(ValueError, 'fixed green budget'):
            self.fixture(bind_context=False)

    def test_wrong_pair_budget_dead_phase_amber_and_offset_cycle_fail(self):
        for change in ({'SC7_p2': -6.}, {'SC7_p3': 1.}, {'SC7_p1': 22.}):
            with self.subTest(change=change), self.assertRaises(SignalGroupPlanError):
                self.fixture(changes=(change,))
        with self.assertRaisesRegex(ValueError, 'offset cycle'):
            self.fixture(coordinate_cycle=150.)

    def test_fitter_rechecks_native_manifold_and_installation_binds_clock(self):
        f, a, edges = self.fixture()
        forged = deepcopy(edges)
        edge = forged['SC7'][0]
        edge['model_owner_values']['probe']['SC7']['SC7_p1'] = 90.
        edge['coordinate']['probe_values']['SC7_p1'] = 90.
        edge['coordinate']['direction']['SC7_p1'] = edge['realized_deltas']['SC7_p1'] = 23.
        with self.assertRaisesRegex(SignalGroupPlanError, 'p1 amber'):
            prices.api.fit_joint_price_field(f, a, forged)
        field = prices.api.fit_joint_price_field(f, a, edges)
        original = deepcopy(vars(f))
        field['context']['native_clock_nodes']['SC7']['native_clock_basis']['source_path'] = 'foreign-source.sig'
        with self.assertRaisesRegex(ValueError, 'native clock nodes differ'):
            prices.api.install_joint_price_field(f, a, field, expected_owners=tuple(edges),
                expected_context=field['context'], nuf_mode='dual')
        self.assertEqual(vars(f), original)


if __name__ == '__main__': unittest.main()
