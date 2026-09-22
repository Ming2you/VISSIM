"""Offline accounting contract tests; does not instantiate or patch VISSIM."""
from __future__ import annotations

import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.controllers.control_area_objective import (
    AreaMetrics, ControlAreaLedger, ControlAreaObjective, MembershipError,
    detector_stock_supports, model_stock_values, physical_membership_from_ledger,
    resolve_model_membership, projection_stock_cohorts, ModelAreaLedger,
)


class ControlAreaLedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger = ControlAreaLedger({"PN": True, "FW": True, "bridge": True, "outside": False})

    def test_only_inside_residence_is_ttt(self):
        self.ledger.record_residence("a", start_sec=0, end_sec=5, stocks={"PN": 10, "outside": 100})
        self.assertAlmostEqual(self.ledger.metrics.ttt_veh_h, 10 * 5 / 3600)
        self.assertEqual(self.ledger.metrics.ttd_veh, 0)

    def test_internal_freeway_transfer_and_orphan_bridge_are_not_exits(self):
        self.ledger.record_crossing("urban-ramp", source="PN", target="bridge", vehicles=5)
        self.ledger.record_crossing("ramp-freeway", source="bridge", target="FW", vehicles=5)
        self.assertEqual(self.ledger.metrics.ttd_veh, 0)
        self.assertEqual(self.ledger.mass_residual({"PN": 5, "FW": 0}, {"PN": 0, "FW": 5}), 0)

    def test_pn_to_noncontrol_counts_before_vehicle_leaves_vissim(self):
        self.ledger.record_crossing("exit", source="PN", target="outside", vehicles=3)
        self.assertEqual(self.ledger.metrics.ttd_veh, 3)
        self.assertEqual(self.ledger.mass_residual({"PN": 10, "outside": 0}, {"PN": 7, "outside": 3}), 0)

    def test_freeway_terminal_and_reentry_are_explicit_events(self):
        for event, source, target in (("exit1", "FW", "outside"), ("entry", "outside", "PN"), ("exit2", "PN", "outside")):
            self.ledger.record_crossing(event, source=source, target=target, vehicles=1)
        self.assertEqual(self.ledger.metrics.ttd_veh, 2)
        self.assertEqual(self.ledger.metrics.entered_veh, 1)

    def test_duplicate_retries_are_idempotent_but_conflicts_fail(self):
        self.assertTrue(self.ledger.record_crossing("x", source="PN", target="outside", vehicles=2))
        self.assertFalse(self.ledger.record_crossing("x", source="PN", target="outside", vehicles=2))
        with self.assertRaises(ValueError):
            self.ledger.record_crossing("x", source="PN", target="outside", vehicles=3)
        self.ledger.record_residence("r", start_sec=0, end_sec=5, stocks={"PN": 10})
        self.assertFalse(self.ledger.record_residence("r", start_sec=0, end_sec=5, stocks={"PN": 10}))
        self.assertEqual(self.ledger.metrics.ttd_veh, 2)
        self.assertAlmostEqual(self.ledger.metrics.ttt_veh_h, 50 / 3600)

    def test_overlapping_stock_integration_fails_without_partial_commit(self):
        self.ledger.record_residence("first", start_sec=0, end_sec=10, stocks={"PN": 2})
        with self.assertRaises(ValueError):
            self.ledger.record_residence("bad", start_sec=5, end_sec=15, stocks={"PN": 2, "FW": 3})
        self.ledger.record_residence("fw", start_sec=0, end_sec=10, stocks={"FW": 3})
        self.assertAlmostEqual(self.ledger.metrics.ttt_veh_h, 50 / 3600)

    def test_missing_location_does_not_become_exit_or_zero_stock(self):
        with self.assertRaises(MembershipError):
            self.ledger.record_crossing("missing", source="PN", target="unknown", vehicles=1)
        with self.assertRaises(MembershipError):
            self.ledger.record_residence("missing", start_sec=0, end_sec=5, stocks={"unknown": 0})
        self.assertEqual(self.ledger.metrics, AreaMetrics())

    def test_flux_is_not_inferred_from_stock_loss(self):
        residual = self.ledger.mass_residual({"PN": 10}, {"PN": 7})
        self.assertEqual(residual, -3)
        self.assertEqual(self.ledger.metrics.ttd_veh, 0)

    def test_invalid_counts_and_fractional_membership_fail(self):
        with self.assertRaises(MembershipError):
            ControlAreaLedger({"mixed": 0.5})
        for bad in (-1, math.nan, math.inf):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.ledger.record_crossing("bad", source="PN", target="outside", vehicles=bad)


class ModelResponseTests(unittest.TestCase):
    def test_diagnostic_offramp_reader_preserves_response_and_restores_on_failure(self):
        from diagnostics.check_fixed_candidate_response import capture_offramp_supply_frames
        cfg = SimpleNamespace(simulation=SimpleNamespace(T_u_sec=5.), network=SimpleNamespace(
            off_ramp_storage_link={'OR_F_W': 'w', 'OR_F_E': 'e'},
            urban_link_storage_veh={'w': 20., 'e': 20.}))
        state = SimpleNamespace(time_sec=900., freeway_density={}, urban_movement_queue={},
            urban_link_storage={'w': 13., 'e': 19.},
            offramp_transit_buffer={'w': {180: 1., 181: 2.}})
        control = SimpleNamespace(N_P_star=0., N_UF_star=0., ramp_metering={}, vsl={},
            green_times={}, offsets={}, inflow_outflow_allocation={})
        plain = ModelAreaLedger({}, capture_response=True)
        traced = ModelAreaLedger({}, capture_response=True)
        original = ModelAreaLedger.record_freeway_operands
        plain.record_freeway_operands(state, control, initial=True)
        with self.assertRaisesRegex(RuntimeError, 'fixture interruption'):
            with capture_offramp_supply_frames(cfg, 900., 1050.) as frames:
                traced.record_freeway_operands(state, control, initial=True)
                ModelAreaLedger({}).record_freeway_operands(None, None, initial=True)
                self.assertEqual(plain.response(), traced.response())
                self.assertEqual(len(frames), 1)
                self.assertEqual(frames[0]['reservoirs']['OR_F_W']['ready_storage_at_sample_veh'], 5.)
                for ledger in (plain, traced):
                    ledger.begin_response_step('landing', 900., 910.)
                    ledger.residence((), 10/3600)
                    if ledger is plain:
                        original(ledger, state, control, {})
                    else:
                        ledger.record_freeway_operands(state, control, {})
                self.assertEqual(plain.response(), traced.response())
                self.assertEqual([row['time_sec'] for row in frames], [900., 910.])
                state.offramp_transit_buffer['w'][181] = 9.
                self.assertEqual(frames[0]['reservoirs']['OR_F_W']['pending_by_due_urban_step'][181], 2.)
                raise RuntimeError('fixture interruption')
        self.assertIs(ModelAreaLedger.record_freeway_operands, original)
        with self.assertRaises(ValueError):
            with capture_offramp_supply_frames(cfg, 900., 1050.):
                traced.record_freeway_operands(state, control, initial=True)
        self.assertIs(ModelAreaLedger.record_freeway_operands, original)

    def test_diagnostic_offramp_balance_keeps_all_branches_and_due_now_bin(self):
        from diagnostics.check_fixed_candidate_response import summarize_offramp_supply
        import copy
        net = SimpleNamespace(off_ramp_storage_link={'OR_F_W': 'w', 'OR_F_E': 'e'},
            off_ramp_from_freeway={'OR_F_W': 'FW_W', 'OR_F_E': 'FW_E'},
            off_ramp_segment_index={'OR_F_W': 1, 'OR_F_E': 2},
            off_ramp_split_ratio={'OR_F_W': .2, 'OR_F_E': .2},
            off_ramp_to_movement={'OR_F_W': ['south', 'other'], 'OR_F_E': []},
            urban_movements={'south': {'beta': .2}, 'other': {'beta': .8}},
            urban_boundary_link_length_m=468., urban_avg_speed_km_h=50.,
            offramp_direct_share_by_offramp={'OR_F_W': .5},
            offramp_direct_tail_by_offramp={'OR_F_W': 'tail'})
        cfg = SimpleNamespace(network=net, simulation=SimpleNamespace(
            T_u_sec=5., T_u_h=5/3600, T_f_sec=10., K_fu=2))
        frames = [dict(time_sec=900., urban_step_index=180, initial=True, reservoirs={
            'OR_F_W': dict(occupied_veh=7., pending_by_due_urban_step={181: 2., 182: 1.}),
            'OR_F_E': dict(occupied_veh=1., pending_by_due_urban_step={})}),
            dict(time_sec=910., urban_step_index=182, initial=False, reservoirs={
            'OR_F_W': dict(occupied_veh=7.25, pending_by_due_urban_step={182: 1., 189: .75}),
            'OR_F_E': dict(occupied_veh=1., pending_by_due_urban_step={})})]
        transfers = [dict(stage='landing', start_sec=900., end_sec=910., source='freeway:FW_W',
            target='storage:w', route_key='offramp_signal:OR_F_W', vehicles=.75),
            dict(stage='landing', start_sec=900., end_sec=910., source='freeway:FW_W',
            target='storage:tail', route_key='offramp_direct:OR_F_W', vehicles=1.25)]
        transfers += [dict(stage='urban', start_sec=900., end_sec=905., source='storage:w',
            target='storage:' + name, route_key='movement:' + name, vehicles=value)
            for name, value in (('south', .3), ('other', .2))]
        before = copy.deepcopy((frames, transfers))
        result = summarize_offramp_supply(cfg, frames, transfers, [], 7)
        row = result['offramps']['OR_F_W']
        self.assertEqual(row['signal_landings_with_verified_due'][0]['due_sec'], 945.)
        self.assertEqual(row['direct_landings_bypassing_storage'][0]['vehicles'], 1.25)
        self.assertEqual(len(row['all_storage_outgoing']), 2)
        self.assertEqual(row['interval_checks'][0]['last_drained_urban_step'], 181)
        self.assertEqual(row['interval_checks'][0]['pending_bin_max_error_veh'], 0.)
        self.assertAlmostEqual(row['interval_checks'][0]['stock_balance_residual_veh'], 0.)
        self.assertEqual((frames, transfers), before)
        # A due-now entry was not drained at the last urban step; dropping it
        # or assigning a new landing the wrong due must fail, not hide transit.
        for changed in ({189: .75}, {182: 1., 190: .75}):
            bad = copy.deepcopy(frames)
            bad[1]['reservoirs']['OR_F_W']['pending_by_due_urban_step'] = changed
            with self.assertRaisesRegex(ValueError, 'due bins'):
                summarize_offramp_supply(cfg, bad, transfers, [], 7)
        with self.assertRaisesRegex(ValueError, 'stock balance'):
            summarize_offramp_supply(cfg, frames, transfers[:-1], [], 7)

    def test_whole_constraint_schedule_missing_visit_and_frames_fail_closed(self):
        ledger = ModelAreaLedger({}, capture_response=True)
        ledger.plan_constraint_interval(900., 5., 10., 2, 1, ['urban_allocator', 'shared_approach'])
        self.assertEqual(ledger.response()['model_constraint_coverage']['expected_visits'], 7)
        visits = list(ledger.response()['constraint_coverage'])
        for row in visits[:-1]:
            ledger.begin_response_step(row['stage'], row['start_sec'], row['end_sec'])
            ledger.complete_constraint_coverage(row['scope'])
        self.assertFalse(ledger.response()['model_constraint_coverage']['allocator_visits_complete'])
        last = visits[-1]
        ledger.begin_response_step(last['stage'], last['start_sec'], last['end_sec'])
        ledger.complete_constraint_coverage(last['scope'])
        coverage = ledger.response()['model_constraint_coverage']
        self.assertTrue(coverage['allocator_visits_complete'])
        self.assertFalse(coverage['captured_frames_complete'])
        self.assertFalse(coverage['conditional_model_feasibility_witness'])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            ledger.complete_constraint_coverage(last['scope'])

    def test_constraint_omission_and_unplanned_visit_cannot_be_full_witness(self):
        ledger = ModelAreaLedger({}, capture_response=True)
        ledger.begin_response_step('urban', 0, 5)
        ledger.complete_constraint_coverage('isolated', missing_constraints=['unobserved_actual_gate'])
        coverage = ledger.response()['model_constraint_coverage']
        self.assertFalse(coverage['conditional_model_feasibility_witness'])
        self.assertEqual(coverage['missing_constraints'], ['unobserved_actual_gate'])
        cloned = ledger.clone()
        cloned._response['constraint_coverage'][0]['missing_constraints'].append('clone_only')
        self.assertNotIn('clone_only', ledger.response()['model_constraint_coverage']['missing_constraints'])
        self.assertFalse(ledger.response()['physical_native_fidelity_certificate'])
        ModelAreaLedger({}).plan_constraint_interval(None, None, None, None, None, None)

    def test_complete_planned_model_witness_stays_separate_from_plant_certificate(self):
        ledger = ModelAreaLedger({'freeway:F': {'inside': 1.}}, capture_response=True)
        state = SimpleNamespace(time_sec=0., freeway_density={'F': [1.]},
                                urban_movement_queue={}, shared_approach_state=None)
        control = SimpleNamespace(N_P_star=0., N_UF_star=0., ramp_metering={}, vsl={},
                                   green_times={}, offsets={}, inflow_outflow_allocation={})
        ledger.record_freeway_operands(state, control, initial=True)
        ledger.plan_constraint_interval(0., 5., 10., 2, 1, ['urban_allocator'], off_ramps=['OR'])
        rows = ledger.response()['constraint_coverage']
        for row in rows:
            ledger.begin_response_step(row['stage'], row['start_sec'], row['end_sec'])
            ledger.complete_constraint_coverage(row['scope'])
        ledger.begin_response_step('landing', 0., 10.)
        ledger.residence(['freeway:F'], 10/3600)
        ledger.record_freeway_operands(state, control, {})
        response = ledger.response()
        self.assertTrue(response['model_constraint_coverage']['complete'])
        self.assertTrue(response['conditional_model_feasibility_witness'])
        self.assertFalse(response['shared_capacity_certificate'])
        self.assertFalse(response['physical_native_fidelity_certificate'])
        # A missing per-off-ramp visit cannot be masked by the overall landing.
        ledger._response['constraint_coverage'][3]['completed'] = False
        self.assertFalse(ledger.response()['model_constraint_coverage']['complete'])
        ledger._response['constraint_coverage'][3]['completed'] = True
        ledger._response['constraint_coverage'][0]['missing_constraints'] = ['query_operand_missing']
        self.assertFalse(ledger.response()['conditional_model_feasibility_witness'])

    def test_existing_state_projection_bound_is_not_accepted_flow(self):
        ledger = ModelAreaLedger({}, capture_response=True)
        ledger.begin_response_step('urban', 0, 5)
        ledger.record_state_upper_bound('queue_projection', 'm', 3., 3.)
        self.assertEqual(ledger.response()['resource_allocations'], [])
        self.assertEqual(ledger.response()['state_bounds'][0]['value_veh'], 3.)
        with self.assertRaisesRegex(ValueError, 'upper bound exceeded'):
            ledger.record_state_upper_bound('queue_projection', 'm', 4., 3.)

    def test_resource_allocations_use_accepted_counts_and_reject_oversubscription(self):
        ledger = ModelAreaLedger({}, capture_response=True)
        ledger.begin_response_step('urban', 900, 902)
        ledger.record_resource_allocation('receiving', 'shared_link', 5., {'owner_A': 2., 'owner_B': 3.})
        row = ledger.response()['resource_allocations'][0]
        self.assertEqual(row['accepted_total_veh'], 5.)
        self.assertEqual(row['exceedance_veh'], 0.)
        with self.assertRaisesRegex(ValueError, 'exceeds shared'):
            ledger.record_resource_allocation('receiving', 'shared_link', 5., {'owner_A': 5., 'owner_B': 1.})
        self.assertEqual(len(ledger.response()['resource_allocations']), 1)
        self.assertFalse(ledger.response()['shared_capacity_certificate'])
        ModelAreaLedger({}).record_resource_allocation(None, None, None, None)

    def test_freeway_operands_preserve_raw_cohorts_and_actual_control(self):
        ledger = ModelAreaLedger({'freeway:F': {'inside': 4}, 'storage:shared': {'outside': 3}},
                                capture_response=True)
        state = SimpleNamespace(time_sec=900., freeway_density={'F': [4.]},
            urban_movement_queue={'to_ramp': 2.},
            shared_approach_state={'bins': {'ramp_branch': {452: 3.}}, 'unadmitted_demand_veh': 7.})
        control = SimpleNamespace(N_P_star=1., N_UF_star=900., ramp_metering={'R': 900.},
            vsl={'F': 100.}, green_times={'S_p1': 40.}, offsets={'S': 2.}, inflow_outflow_allocation={})
        ledger.record_freeway_operands(state, control, initial=True)
        with self.assertRaises(ValueError):
            ledger.record_freeway_operands(state, control, initial=True)
        ledger.begin_response_step('landing', 900, 910)
        ledger.residence(('freeway:F',), 10/3600)
        ledger.record_freeway_operands(state, control, {'R': 600.})
        state.shared_approach_state['bins']['ramp_branch'][452] = 99.
        control.ramp_metering['R'] = 1.
        response = ledger.response()
        frame = response['freeway_frames'][0]
        self.assertEqual(frame['shared_approach_state']['bins']['ramp_branch'], {452: 3.})
        self.assertEqual(frame['actual_ramp_release_veh_h'], {'R': 600.})
        self.assertEqual(frame['applied_control']['ramp_metering'], {'R': 900.})
        self.assertEqual(response['initial_freeway_operands']['start_sec'], 900.)
        frame['freeway_density']['F'][0] = 99.
        self.assertEqual(ledger.response()['freeway_frames'][0]['freeway_density']['F'], [4.])
        ledger.begin_response_step('urban', 910, 912)
        with self.assertRaisesRegex(ValueError, 'post-landing'):
            ledger.record_freeway_operands(state, control, {'R': 600.})
        # OFF must return without touching any model object.
        ModelAreaLedger({}).record_freeway_operands(None, None, initial=True)

    def test_capture_preserves_metrics_and_exposes_only_accepted_transfers(self):
        stocks = {"storage:a": {"inside": 8, "outside": 2}}
        plain = ModelAreaLedger(stocks)
        traced = ModelAreaLedger(stocks, capture_response=True)
        traced.begin_response_step("urban", 900, 902)
        for ledger in (plain, traced):
            ledger.transfer("storage:a", "storage:b", 5, inside_to_inside=0,
                            outside_to_inside=0, route_key="a_to_b", event_id="move")
            ledger.transfer("storage:a", "storage:b", 5, inside_to_inside=0,
                            outside_to_inside=0, route_key="a_to_b", event_id="move")
            ledger.residence(("storage:a", "storage:b"), 2 / 3600, event_id="time")
            ledger.residence(("storage:a", "storage:b"), 2 / 3600, event_id="time")
        self.assertEqual(plain.stocks, traced.stocks)
        self.assertEqual(plain.metrics, traced.metrics)
        self.assertEqual(plain.flow_counts, traced.flow_counts)
        response = traced.response()
        self.assertEqual(len(response["transfers"]), 1)
        self.assertEqual(response["transfers"][0]["vehicles"], 5)
        self.assertEqual(response["transfers"][0]["ttd_veh"], 4)
        self.assertEqual(response["transfers"][0]["start_sec"], 900)
        self.assertEqual(response["residence"][0]["inside_veh"], {"storage:a": 4, "storage:b": 0})
        self.assertFalse(response["shared_capacity_certificate"])
        with self.assertRaisesRegex(ValueError, "not enabled"):
            plain.response()

    def test_query_copy_and_returned_response_do_not_share_mutable_records(self):
        ledger = ModelAreaLedger({"a": {"inside": 3}}, capture_response=True)
        ledger.begin_response_step("urban", 0, 2)
        clone = ledger.clone()
        clone.transfer("a", None, 1, inside_to_inside=0, outside_to_inside=0)
        self.assertEqual(ledger.response()["transfers"], [])
        exported = clone.response()
        exported["transfers"][0]["vehicles"] = 999
        self.assertEqual(clone.response()["transfers"][0]["vehicles"], 1)

    def test_missing_clock_or_invalid_window_fails_before_stock_change(self):
        ledger = ModelAreaLedger({"a": {"inside": 3}}, capture_response=True)
        with self.assertRaisesRegex(ValueError, "clock"):
            ledger.transfer("a", None, 1, inside_to_inside=0, outside_to_inside=0)
        self.assertEqual(ledger.stocks["a"]["inside"], 3)
        for start, end in ((2, 1), (0, math.nan), (math.inf, 2)):
            with self.assertRaises(ValueError):
                ledger.begin_response_step("urban", start, end)

    def test_physical_reentry_counts_match_existing_metrics(self):
        ledger = ModelAreaLedger({"a": {"inside": 2, "outside": 2}}, capture_response=True)
        ledger.begin_response_step("landing", 10, 20)
        ledger.transfer("a", "b", 4, inside_to_inside=1, outside_to_inside=1,
                        physical_source_inside=True, outward_crossings=1, inward_crossings=1)
        row = ledger.response()["transfers"][0]
        self.assertEqual(row["ttd_veh"], ledger.metrics.ttd_veh)
        self.assertEqual(row["entered_veh"], ledger.metrics.entered_veh)


class MembershipTests(unittest.TestCase):
    def test_projection_cohorts_use_assigned_counts_not_number_of_links(self):
        cohorts = projection_stock_cohorts(
            {"in": {"storage:mixed": 92}, "out": {"storage:mixed": 1}},
            {"in": True, "out": False},
        )
        self.assertEqual(cohorts["storage:mixed"], {"inside": 92, "outside": 1})
        with self.assertRaises(MembershipError):
            projection_stock_cohorts({"unknown": {"storage:mixed": 1}}, {"in": True})

    def test_installed_physical_branches_do_not_remerge_raw_offramp_group(self):
        supports = detector_stock_supports({
            "link_to_origins": {"in": ["OR_storage"], "out": ["tail"]},
            "off_ramp_connectors": {"OR": [{"connector": "in"}, {"connector": "out"}]},
            "physical_storage_projection": {"link_to_storage": {"in": "OR_storage", "out": "tail"}},
        }, off_ramp_storage_links={"OR": "OR_storage"}, freeway_chains={})
        self.assertEqual(supports["storage:OR_storage"], {"in"})
        self.assertEqual(supports["storage:tail"], {"out"})

    def test_ledger_unresolved_and_overlap_fail(self):
        doc = {"schema": "control-area-membership/v1", "inside_links": [1], "outside_links": [2], "unresolved": []}
        self.assertEqual(physical_membership_from_ledger(doc), {"1": True, "2": False})
        with self.assertRaises(MembershipError):
            physical_membership_from_ledger({**doc, "unresolved": ["bridge"]})
        with self.assertRaises(MembershipError):
            physical_membership_from_ledger({**doc, "outside_links": [1]})

    def test_detector_join_does_not_guess_mixed_or_missing_model_fraction(self):
        supports = detector_stock_supports({
            "link_to_origins": {"in": ["L"], "out": ["L"]},
            "link_to_movements": {"in": [{"movement": "m", "weight": 1}]},
            "ramp_link_to_queues": {"in": ["R"]},
            "off_ramp_connectors": {"OR": [{"connector": "in"}]},
        }, off_ramp_storage_links={"OR": "OR_storage"}, freeway_chains={"F": ["in"]})
        physical = {"in": True, "out": False}
        keys = ["movement:m", "ramp:R", "freeway:F", "storage:OR_storage"]
        self.assertEqual(resolve_model_membership(physical, supports, keys), dict.fromkeys(keys, True))
        with self.assertRaisesRegex(MembershipError, "mixed"):
            resolve_model_membership(physical, supports, ["storage:L"])
        with self.assertRaisesRegex(MembershipError, "no support"):
            resolve_model_membership(physical, supports, ["transit:gate:L"])

    def test_model_inventory_includes_real_transit_not_schedule_aliases(self):
        state = SimpleNamespace(
            urban_movement_queue={"m": 2}, ramp_queue={"R": 3}, mainline_origin_queue={"F": 4},
            urban_link_storage={"L": 7}, urban_inflow_transit_buffer={"gate:L": {5: 6}},
            urban_arrival_buffer={"L": {5: 100}}, urban_storage_release_buffer={"L": {5: 100}},
        )
        net = SimpleNamespace(freeway_links=["F"], urban_link_storage_veh={"L": 12}, urban_movements={"m": {}}, ramps=["R"])
        counts = model_stock_values(state, net, freeway_vehicle_counts={"F": [7, 8]})
        self.assertEqual(counts, {"movement:m": 2, "ramp:R": 3, "origin:F": 4, "storage:L": 5, "freeway:F": 15, "transit:gate:L": 6})
        state.freeway_buffer_up_density = {"F": [1]}
        with self.assertRaises(MembershipError):
            model_stock_values(state, net, freeway_vehicle_counts={"F": [7, 8]})

    def test_missing_model_queue_cannot_silently_reduce_objective(self):
        state = SimpleNamespace(urban_movement_queue={}, ramp_queue={}, mainline_origin_queue={})
        net = SimpleNamespace(freeway_links=[], urban_movements={"missing": {}}, ramps=[])
        with self.assertRaisesRegex(MembershipError, "inventory"):
            model_stock_values(state, net, freeway_vehicle_counts={})


class ObjectiveTests(unittest.TestCase):
    def test_requested_zero_sixty_one_fifty_three_hundred_second_sensitivity(self):
        candidates = {"A": AreaMetrics(ttt_veh_h=10, ttd_veh=0),
                      "B": AreaMetrics(ttt_veh_h=12, ttd_veh=60)}
        winners, scores_b = [], []
        for seconds in (0, 60, 150, 300):
            objective = ControlAreaObjective(beta_hours=seconds / 3600)
            scores = {key: objective.score(metrics) for key, metrics in candidates.items()}
            winners.append(min(scores, key=scores.get))
            scores_b.append(scores["B"])
        self.assertEqual(winners, ["A", "A", "B", "B"])
        self.assertEqual(scores_b, [12, 11, 9.5, 7])

    def test_reward_weight_has_no_default_and_is_in_hours(self):
        with self.assertRaises(TypeError):
            ControlAreaObjective()
        objective = ControlAreaObjective(beta_hours=60 / 3600)
        self.assertAlmostEqual(objective.score(AreaMetrics(ttt_veh_h=1, ttd_veh=3)), 0.95)
        with self.assertRaises(ValueError):
            ControlAreaObjective(beta_hours=-1)

    def test_naive_ttt_prune_would_reject_possible_winner(self):
        objective = ControlAreaObjective(beta_hours=1)
        partial = AreaMetrics(ttt_veh_h=5)
        # TTT 5 already exceeds incumbent 4, but 10 later exits can make J=-5.
        self.assertFalse(objective.can_prune(partial, incumbent_veh_h=4, max_future_exits_veh=10))
        self.assertEqual(objective.lower_bound(partial, max_future_exits_veh=10), -5)
        self.assertTrue(objective.can_prune(partial, incumbent_veh_h=4, max_future_exits_veh=0))
        self.assertFalse(objective.can_prune(partial, incumbent_veh_h=4, max_future_exits_veh=None))

    def test_bound_is_admissible_over_possible_remaining_exits_and_ttt(self):
        objective = ControlAreaObjective(beta_hours=0.25)
        partial = AreaMetrics(ttt_veh_h=3, ttd_veh=2)
        lower = objective.lower_bound(partial, max_future_exits_veh=5)
        for future_exits in range(6):
            for future_ttt in (0, 0.1, 10):
                final = objective.score(AreaMetrics(3 + future_ttt, 2 + future_exits))
                self.assertLessEqual(lower, final)
        self.assertFalse(objective.can_prune(partial, incumbent_veh_h=lower, max_future_exits_veh=5))

    def test_zero_weight_preserves_nonnegative_ttt_pruning(self):
        objective = ControlAreaObjective(beta_hours=0)
        self.assertTrue(objective.can_prune(AreaMetrics(5), incumbent_veh_h=4, max_future_exits_veh=None))


class DistanceObjectiveTests(unittest.TestCase):
    def test_units_and_exits_are_independent_of_distance(self):
        obj = ControlAreaObjective(beta_hours=150/3600, distance_hours_per_km=60/3600)
        self.assertAlmostEqual(obj.score(AreaMetrics(10, 24), tvd_veh_km=120), 7.)
        self.assertAlmostEqual(obj.score(AreaMetrics(10, 0), tvd_veh_km=120), 8.)

    def test_zero_weight_preserves_exact_old_score(self):
        for beta in (0, 60/3600, 150/3600, 300/3600):
            obj = ControlAreaObjective(beta)
            metrics = AreaMetrics(1.23456, 17.89)
            expected = metrics.ttt_veh_h - beta * metrics.ttd_veh + 0.123
            self.assertEqual(obj.score(metrics, nonnegative_cost_veh_h=.123), expected)
            self.assertEqual(obj.score(metrics, nonnegative_cost_veh_h=.123, tvd_veh_km=321), expected)

    def test_positive_reward_requires_accounted_distance(self):
        obj = ControlAreaObjective(0, 1/60)
        with self.assertRaisesRegex(ValueError, 'explicitly accounted'):
            obj.score(AreaMetrics(1))
        for invalid in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError): obj.score(AreaMetrics(1), tvd_veh_km=invalid)
            with self.assertRaises(ValueError): ControlAreaObjective(0, invalid)

    def test_missing_future_distance_bound_disables_pruning(self):
        obj = ControlAreaObjective(0, .1)
        self.assertFalse(obj.can_prune(AreaMetrics(10), incumbent_veh_h=1,
            max_future_exits_veh=0, tvd_veh_km=0))
        self.assertTrue(obj.can_prune(AreaMetrics(10), incumbent_veh_h=1,
            max_future_exits_veh=0, tvd_veh_km=0, max_future_tvd_veh_km=1))

    def test_combined_bound_is_admissible(self):
        obj = ControlAreaObjective(.25, .1)
        bound = obj.lower_bound(AreaMetrics(3, 2), tvd_veh_km=10,
            max_future_exits_veh=5, max_future_tvd_veh_km=30)
        for exits in range(6):
            for distance in (0, 10, 30):
                for ttt in (0, .1, 10):
                    self.assertLessEqual(bound, obj.score(AreaMetrics(3+ttt, 2+exits), tvd_veh_km=10+distance))

    def test_stopped_queue_cost_is_retained_and_more_distance_is_rewarded(self):
        obj = ControlAreaObjective(0, 60/3600)
        self.assertEqual(obj.score(AreaMetrics(2), tvd_veh_km=0), 2)
        self.assertLess(obj.score(AreaMetrics(2), tvd_veh_km=60), obj.score(AreaMetrics(2), tvd_veh_km=30))


if __name__ == "__main__":
    unittest.main()
