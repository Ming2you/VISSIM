"""Regression checks for explicit freeway events; no VISSIM or source mutation."""
from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from src.models import metanet
from src.models.demand import DemandStep
from src.models.state import ControlAction, ExperimentConfig, TrafficState
from src.simulation import coupling
from evaluation.controllers import area_freeway_accounting as accounting
from evaluation.controllers import control_area_objective as area


def fixture(*, offramps=False):
    cfg = ExperimentConfig()
    cfg.simulation.control_interval = 20.0
    cfg.network.freeway_segments_per_link = 3
    cfg.network.control_area_enabled = True
    if not offramps:
        cfg.network.off_ramps = []
    state = TrafficState.initial(cfg)
    for index, link in enumerate(cfg.network.freeway_links):
        state.freeway_density[link] = [14.0, 27.0, 42.0 + index]
        state.freeway_speed[link] = [60.0, 45.0, 95.0]
        state.mainline_origin_queue[link] = 25.0
    state.refresh_freeway_flow(cfg.network)
    demand = DemandStep({link: 1500.0 for link in cfg.network.freeway_links}, {}, {})
    control = ControlAction.uncontrolled(cfg)
    return cfg, state, control, demand


def inventory(state, cfg):
    out = {f"freeway:{link}": sum(counts) for link, counts in
           accounting.continuity_vehicle_counts(state, cfg).items()}
    out.update({f"origin:{link}": value for link, value in state.mainline_origin_queue.items()})
    return out


def seed(state, cfg, **extra):
    stocks = {key: {"inside": amount if key.startswith("freeway:") else 0,
                    "outside": 0 if key.startswith("freeway:") else amount}
              for key, amount in inventory(state, cfg).items()}
    stocks.update(extra)
    state._control_area_ledger = area.ModelAreaLedger(stocks)
    return state._control_area_ledger


def physical_state(state):
    return {key: value for key, value in vars(state).items() if key != "_control_area_ledger"}


class FreewayAccountingTests(unittest.TestCase):
    def test_extracted_equations_remain_pinned(self):
        for module, name, expected in (
            (metanet, "freeway_substep", accounting.VENDOR_FREEWAY_METHOD_SHA256),
            (coupling, "run_coupled_interval", accounting.VENDOR_COUPLING_METHOD_SHA256),
        ):
            source = Path(module.__file__).read_text(encoding="utf-8")
            node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
            self.assertEqual(hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest(), expected,
                             "vendor method changed; review the extracted event implementation")

    def test_actual_terminal_entry_and_merge_preserve_every_state_field(self):
        for incident, zero_gradient in ((False, False), (True, False), (False, True)):
            with self.subTest(incident=incident, zero_gradient=zero_gradient):
                cfg, state, control, demand = fixture()
                cfg.network.terminal_zero_gradient = zero_gradient
                if incident:
                    demand.freeway_lane_loss = {"FW_E": {1: 0.5}}
                ramp = cfg.network.ramps[0]
                release = {r: 240.0 if r == ramp else 0.0 for r in cfg.network.ramps}
                merged = release[ramp] * cfg.simulation.T_f_h
                ledger = seed(state, cfg, **{f"merge_pending:{ramp}": {"inside": merged}})
                original = state.copy()
                result = accounting._freeway_substep_events(
                    state, control, demand, cfg, ramp_release_veh_h=release, update_ramp_queues=False)
                reference = metanet.freeway_substep(
                    original, control, demand, cfg, ramp_release_veh_h=release, update_ramp_queues=False)
                self.assertEqual(result, reference)
                self.assertEqual(physical_state(state), physical_state(original))
                ledger.assert_stocks(inventory(state, cfg))
                self.assertAlmostEqual(ledger.ttd_veh, result[1]["mainline_exit_flow_total"] * cfg.simulation.T_f_h)
                requested = sum(demand.freeway_mainline.values()) * cfg.simulation.T_f_h
                accepted = requested + 50.0 - sum(state.mainline_origin_queue.values())
                self.assertAlmostEqual(ledger.entered_veh, accepted)
                self.assertAlmostEqual(ledger.flow_counts[f"merge_pending:{ramp}->freeway:{cfg.network.ramp_to_freeway[ramp]}"], merged)
                # The stored rho_new*v_new*lanes is demand, not accepted terminal outflow.
                if not zero_gradient:
                    demand_exit = sum(row[-1] for row in state.freeway_flow.values()) * cfg.simulation.T_f_h
                    self.assertNotAlmostEqual(ledger.ttd_veh, demand_exit)
                area.integrate_residence(state, cfg, list(inventory(state, cfg)), cfg.simulation.T_f_h)
                expected_ttt = sum(sum(v) for v in state.freeway_vehicle_count_by_link(cfg.network).values()) * cfg.simulation.T_f_h
                self.assertAlmostEqual(ledger.ttt_veh_h, expected_ttt)
                self.assertEqual(original._control_area_ledger.event_count, 0)

    def test_offramp_is_emitted_once_by_schedule_before_residence(self):
        cfg, state, control, demand = fixture(offramps=True)
        cfg.network.ramps = []
        cfg.network.ramp_to_freeway = {}
        state.ramp_queue = {}
        seed(state, cfg)
        # Captured Tf frames now verify the complete physical inventory. Keep
        # the isolated urban state stationary but seed its existing stocks too.
        from evaluation.controllers.area_runtime import model_inventory
        for key, amount in model_inventory(state, cfg).items():
            state._control_area_ledger.stocks.setdefault(key, {'inside': amount, 'outside': 0.})
        state._control_area_ledger = area.ModelAreaLedger(state._control_area_ledger.stocks, capture_response=True)
        schedule_count = 0
        residence_count = 0

        def schedule(s, c, off, amount, next_step):
            nonlocal schedule_count
            schedule_count += 1
            storage = c.network.off_ramp_storage_link[off]
            s.urban_link_storage[storage] -= amount
            area.emit_transfer(s, c, f"freeway:{c.network.off_ramp_from_freeway[off]}",
                               f"storage:{storage}", amount, preserve_area=True)
            return amount, 0.0

        def residence(s, c, keys, dt_h):
            nonlocal residence_count
            residence_count += 1
            self.assertEqual(schedule_count, residence_count * len(cfg.network.off_ramps))
            tracked = s._control_area_ledger.stocks
            for key, amount in inventory(s, c).items():
                self.assertAlmostEqual(sum(tracked[key].values()), amount)
            area.integrate_residence(s, c, keys, dt_h)

        # Hold urban transitions fixed to isolate the exact Tf integration order.
        from evaluation.controllers import area_meter_finalization
        # This fixture has no meters; meter realization is tested separately.
        with mock.patch.object(area_meter_finalization, 'finalize', lambda control, cfg: control), \
                mock.patch.multiple(coupling,
                sync_onramp_queues_from_freeway=lambda *a: None,
                sync_onramp_queues_to_freeway=lambda *a: None,
                urban_substep=lambda *a, **kw: (0.0, {}),
                aggregate_urban_diagnostics=lambda *a, **kw: {},
                off_ramp_capacity_by_freeway_link=lambda *a, **kw: {},
                schedule_offramp_arrivals=schedule,
                freeway_substep=accounting._freeway_substep_events), \
                mock.patch.object(accounting, "_area", SimpleNamespace(
                    emit_transfer=area.emit_transfer, integrate_residence=residence,
                    get_ledger=area.get_ledger)):
            result = accounting._run_coupled_interval_events(state, control, demand, cfg)
        self.assertEqual(residence_count, cfg.simulation.K_cf)
        off_count = sum(sum(v.values()) for k, v in state._control_area_ledger.stocks.items() if k.startswith("storage:"))
        self.assertAlmostEqual(off_count, result.diagnostics["coupling_offramp_arrivals_accepted_veh"])
        self.assertGreater(off_count, 0)
        response = state._control_area_ledger.response()
        landing = [row for row in response['transfers'] if str(row['target']).startswith('storage:')]
        self.assertTrue(landing)
        self.assertEqual({row['stage'] for row in landing}, {'landing'})
        self.assertEqual([row['start_sec'] for row in response['residence']], [0.0, 10.0])
        # An inside storage transfer is not an Omega departure.
        self.assertEqual(sum(v for k, v in state._control_area_ledger.flow_counts.items() if "->storage:" in k), off_count)

    def test_install_disabled_delegation_idempotence_and_clone_isolation(self):
        cfg, state, control, demand = fixture()
        baseline_fw, baseline_cp = metanet.freeway_substep, coupling.run_coupled_interval
        calls = []

        def rebind(name, old, new):
            calls.append(name)
            if getattr(coupling, name, None) is old:
                setattr(coupling, name, new)

        adapter = SimpleNamespace(_fw_rebind=rebind)
        cfg.network.control_area_enabled = False
        self.assertEqual(accounting.install(adapter, cfg)["area_freeway_accounting_enabled"], 0)
        self.assertIs(metanet.freeway_substep, baseline_fw)
        cfg.network.control_area_enabled = True
        seed(state, cfg)
        original = state.copy()
        with mock.patch.object(metanet, "freeway_substep", baseline_fw), \
                mock.patch.object(coupling, "freeway_substep", coupling.freeway_substep), \
                mock.patch.object(coupling, "run_coupled_interval", baseline_cp):
            self.assertEqual(accounting.install(adapter, cfg)["area_freeway_accounting_installed"], 1)
            installed = metanet.freeway_substep
            self.assertEqual(accounting.install(adapter, cfg)["area_freeway_accounting_installed"], 0)
            self.assertIs(installed, metanet.freeway_substep)
            self.assertEqual(calls, ["freeway_substep", "run_coupled_interval"])
            args = {"ramp_release_veh_h": {}, "update_ramp_queues": False}
            missing = state.copy()
            del missing._control_area_ledger
            with self.assertRaisesRegex(ValueError, "candidate-owned ledger"):
                metanet.freeway_substep(missing, control, demand, cfg, **args)
            metanet.freeway_substep(state, control, demand, cfg, **args)
            self.assertEqual(original._control_area_ledger.event_count, 0)
            self.assertGreater(state._control_area_ledger.event_count, 0)
            cfg.network.control_area_enabled = False
            reference, actual = original.copy(), original.copy()
            self.assertEqual(baseline_fw(reference, control, demand, cfg, **args),
                             metanet.freeway_substep(actual, control, demand, cfg, **args))
            self.assertEqual(physical_state(reference), physical_state(actual))
            self.assertEqual(actual._control_area_ledger.event_count, 0)

    def test_inventory_uses_conservation_geometry_even_if_display_getter_is_patched(self):
        cfg, state, _, _ = fixture()
        cfg.network.freeway_segment_length_profile_km = {link: [0.1, 0.8, 1.1] for link in cfg.network.freeway_links}
        state.freeway_effective_lanes["FW_E"] = [0.5, 1.0, 3.0]
        with mock.patch.object(state, "freeway_vehicle_count_by_link", return_value={"FW_E": [9999.0]}):
            actual = accounting.continuity_vehicle_counts(state, cfg)
        self.assertEqual(actual["FW_E"], [14 * 0.5 * 0.5, 27 * 0.5 * 1, 43 * 0.5 * 3])

    def test_unsupported_provenance_fails_before_mutation(self):
        cfg, state, control, demand = fixture()
        seed(state, cfg)
        before = copy.deepcopy(physical_state(state))
        with self.assertRaisesRegex(ValueError, "standalone"):
            accounting._freeway_substep_events(state, control, demand, cfg)
        self.assertEqual(before, physical_state(state))
        cfg.network.freeway_buffer_segments = 1
        with self.assertRaisesRegex(ValueError, "buffer-chain"):
            accounting._freeway_substep_events(state, control, demand, cfg, update_ramp_queues=False)
        self.assertEqual(before, physical_state(state))


class ConstraintEvidenceTests(unittest.TestCase):
    def test_exact_query_limits_and_bad_return_and_unpinned_query_rejected(self):
        cfg, state, control, demand = fixture()
        ledger = seed(state, cfg)
        state._control_area_ledger = area.ModelAreaLedger(ledger.stocks, capture_response=True)
        ledger = state._control_area_ledger
        ledger.begin_response_step('freeway', 0., cfg.simulation.T_f_sec)
        state.ramp_queue = {r: 2. + i for i, r in enumerate(cfg.network.ramps)}
        before = copy.deepcopy(physical_state(state))
        release, diag = metanet.compute_ramp_release_flows(state, control, demand, cfg, include_current_arrivals=False)
        accounting._record_ramp_release_query(state, control, demand, cfg, release, metanet.compute_ramp_release_flows)
        self.assertEqual(before, physical_state(state))
        self.assertEqual(len(ledger.response()['resource_allocations']), 4*len(cfg.network.ramps))
        self.assertTrue(all(row['accepted_total_veh'] <= row['available_veh'] + 1e-9
                            for row in ledger.response()['resource_allocations']))
        bad = dict(release); bad[cfg.network.ramps[0]] += 1.
        with self.assertRaisesRegex(ValueError, 'differs from pinned min'):
            accounting._record_ramp_release_query(state, control, demand, cfg, bad, metanet.compute_ramp_release_flows)
        def foreign(state, control, demand, cfg, include_current_arrivals=True):
            return release, diag
        with self.assertRaises(ValueError):
            accounting._record_ramp_release_query(state, control, demand, cfg, release, foreign)

    def test_freeway_capture_limits_preserve_entire_legacy_return_and_state(self):
        cfg, state, control, demand = fixture(offramps=True)
        seed(state, cfg)
        left, right = state.copy(), state.copy()
        ledger = right._control_area_ledger = area.ModelAreaLedger(right._control_area_ledger.stocks, capture_response=True)
        ledger.begin_response_step('freeway', 0., cfg.simulation.T_f_sec)
        caps = {off: 60. for off in cfg.network.off_ramps}
        kwargs = dict(offramp_capacity_veh_h=caps, ramp_release_veh_h={}, update_ramp_queues=False)
        expected = accounting._freeway_substep_events(left, control, demand, cfg, **kwargs)
        actual = accounting._freeway_substep_events(right, control, demand, cfg, **kwargs)
        self.assertEqual(actual, expected)
        self.assertEqual(physical_state(left), physical_state(right))
        rows = ledger.response()['resource_allocations']
        kinds = {r['kind'] for r in rows}
        self.assertTrue({'freeway_mainline_sending', 'freeway_mainline_receiving_after_ramps',
                        'freeway_entry_capacity', 'freeway_terminal_capacity',
                        'freeway_offramp_receiving'} <= kinds)
        self.assertFalse(ledger.response()['model_constraint_coverage']['complete'])
        self.assertFalse(ledger.response()['shared_capacity_certificate'])


if __name__ == "__main__":
    unittest.main()
