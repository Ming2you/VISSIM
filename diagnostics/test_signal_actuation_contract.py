"""Actual n7 actions -> installed contract -> installed CSV/SG/VBS oracle."""
from __future__ import annotations

import copy
import ast
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from evaluation.controllers import signal_actuation_contract as proposed
from diagnostics.probe_signal_feasibility import setup
from evaluation.controllers import vissim_stackelberg_adapter as adapter, offset_promotion


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.state, cls.dm, cls.tuning, cls.raw, cls.mapping, _ = setup()
        from src.models.state import ControlAction, segment_vsl
        from src.models import urban_queue_model
        from src.controllers import wu_faithful_follower
        cls.ControlAction, cls.segment_vsl = ControlAction, staticmethod(segment_vsl)
        cls.original_clock = staticmethod(urban_queue_model._phase_green_fraction)
        cls.original_local_fractions = staticmethod(wu_faithful_follower.WuFaithfulFollower._offset_green_fractions_vec)
        cls.old_cfg = copy.deepcopy(cls.cfg)
        cls.plan = adapter.load_signal_group_actuation_plan()
        tun = copy.deepcopy(cls.tuning)
        tun.setdefault("urban", {})["physical_signal_contract"] = True
        tun["actuation"]["real_world_signal_control"]["offset_writer"] = "test_only"
        proposed.configure(cls.cfg, tun, cls.plan)
        cls.clock = staticmethod(proposed.wrap_clock(cls.original_clock))
        cls.run_dir = ROOT / "evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910"
        cls.actions = sorted(cls.run_dir.glob("action_*.json"))

    def action(self, path=None, offset=0):
        path = path or ROOT / "diagnostics/frozen_n7_2100_green_action.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        ctrl = self.ControlAction.uncontrolled(self.cfg)
        ctrl.green_times.update(payload["green_times"])
        ctrl = proposed.prepare_control(ctrl, self.cfg)
        offsets = {s: offset % self.cfg.network.signal_cycle_length(s) for s in self.cfg.network.signals}
        ctrl.offsets.update(offsets)
        ctrl.diagnostics[offset_promotion.FORCED_ARM_TABLE_KEY] = json.dumps(offsets)
        return ctrl

    def rows(self, action, cfg=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "action.csv"
            adapter.write_action_csv(path, action, cfg or self.cfg, self.mapping, self.segment_vsl, {},
                                     self.tuning["actuation"], self.plan, "test_only")
            with path.open(newline="") as handle:
                return list(csv.DictReader(handle))

    def test_off_preserves_original_values_and_objects(self):
        ctrl = self.ControlAction.uncontrolled(self.old_cfg)
        self.assertIs(proposed.prepare_control(ctrl, self.old_cfg), ctrl)
        vec = {"p1": 0., "p2": 20., "p3": 96.5, "p4": 24.5}
        self.assertIs(proposed.project_vector(self.old_cfg.network, "SC109", vec), vec)
        self.assertEqual(self.old_cfg.network.signal_green_max("SC109"), 101.)
        for signal in self.old_cfg.network.signals:
            for offset in (-20., 0., 10., 140.):
                ctrl.offsets[signal] = offset
                for phase in proposed.PHASES:
                    spec = {"intersection": signal, "phase": signal + "_" + phase}
                    for step in (0, 1, 29, 30, 31, 179, 180, 181):
                        self.assertEqual(self.clock(ctrl, self.old_cfg, spec, step), self.original_clock(ctrl, self.old_cfg, spec, step))

    def test_seed_projection_cap_cycle_precision_and_isolation(self):
        original = self.ControlAction.uncontrolled(self.cfg)
        original.green_times.update({"SC109_p1": 0., "SC109_p2": 20., "SC109_p3": 96.5, "SC109_p4": 24.5})
        saved = dict(original.green_times)
        ctrl = proposed.prepare_control(original, self.cfg)
        self.assertEqual(original.green_times, saved)
        self.assertIsNot(ctrl, original)
        vals = {p: ctrl.green_times["SC109_" + p] for p in proposed.PHASES}
        self.assertEqual(vals, {"p1": 0., "p2": 23.25, "p3": 90., "p4": 27.75})
        self.assertEqual(sum(vals.values()) + 9, 150.)
        self.assertEqual(self.cfg.network.signal_green_max("SC109"), 90.)
        with self.assertRaises(ValueError):
            proposed.validate_vector(self.cfg.network, "SC109", {"p1": 0., "p2": 20., "p3": 96.5, "p4": 24.5})
        with self.assertRaises(ValueError):
            proposed.project_vector(self.cfg.network, "SC109", {"p2": float("nan")})
        proposed.validate_control(ctrl, self.cfg)

    def test_distribution_and_real_candidate_exchange_and_price_direction(self):
        from src.models import state
        controller = adapter.build_priced_wu_link_controller(self.cfg, self.tuning)
        proposed.install_controller(controller)
        follower = controller.nash_solver
        for signal in self.cfg.network.signals:
            low, high, _ = proposed.bounds(self.cfg.network, signal)
            scalars = follower._urban_green_candidates(signal, self.state, {}, self.action(offset=0))
            self.assertTrue(all(low <= v <= high and v == round(v, 3) for v in scalars))
            for primary in (low - 100, low, 47.123456, high, high + 100):
                vec = state.distribute_phase_green(self.cfg.network, primary, signal=signal)
                proposed.validate_vector(self.cfg.network, signal, vec)
                for candidate in follower._phase_exchange_candidates(signal, vec, 6.):
                    proposed.validate_vector(self.cfg.network, signal, candidate)
                for phase in self.cfg.network.signal_live_phases(signal):
                    direction = controller._phase_direction(signal, vec, phase, 6.)
                    if direction is not None:
                        proposed.validate_vector(self.cfg.network, signal, direction)
        before = state.distribute_phase_green
        proposed.install_candidates(self.cfg)
        self.assertIs(state.distribute_phase_green, before)

    def test_reject_partial_plan_and_infeasible_cycle(self):
        cfg = copy.deepcopy(self.old_cfg)
        tun = copy.deepcopy(self.tuning)
        tun["urban"]["physical_signal_contract"] = True
        bad = copy.deepcopy(self.plan)
        bad["controllers"]["1"]["phase_segments"]["p1"][0]["end_fraction"] = .5
        with self.assertRaisesRegex(ValueError, "partial SG"):
            proposed.configure(cfg, tun, bad)
        cfg.network.effective_green_total_by_signal["SC109"] = 300.
        with self.assertRaisesRegex(ValueError, "cannot contain budget"):
            proposed.configure(cfg, tun, self.plan)

    def test_all_n7_actions_17_signals_signed_offsets_dead_phases_and_boundaries(self):
        checks, max_error, mutated, large_mutations, largest = 0, 0.0, 0, 0, 0.0
        for path in self.actions:
            raw_action = json.loads(path.read_text(encoding="utf-8"))
            for offset in (-20, -10, 0, 10, 20):
                control = self.action(path, offset)
                rows = self.rows(control)
                axis = {"SC" + row["sc_no"]: row for row in rows if row["kind"] == "signal"}
                groups = {(int(row["sc_no"]), str(row["dsd_no"])): row for row in rows if row["kind"] == "signal_sg"}
                for signal in self.cfg.network.signals:
                    for phase in proposed.PHASES:
                        emitted = float(axis[signal][phase + "_green"])
                        self.assertEqual(emitted, control.green_times[signal + "_" + phase])
                        if offset == 0 and abs(float(raw_action["green_times"].get(signal + "_" + phase, 0)) - emitted) > 1e-8:
                            mutated += 1
                            change = abs(float(raw_action["green_times"].get(signal + "_" + phase, 0)) - emitted)
                            large_mutations += change > .002
                            largest = max(change, largest)
                        segs = self.plan["controllers"][signal[2:]]["phase_segments"][phase]
                        row = groups.get((int(signal[2:]), str(segs[0]["sg_no"]))) if segs else None
                        spec = {"intersection": signal, "phase": signal + "_" + phase}
                        # A complete cycle plus both sides of absolute cycle boundaries.
                        for step in (*range(180, 210), 0, 29, 30, 31, 359, 360, 361):
                            expected = 0.0 if row is None else sum(
                                float(row["p1_green"]) <= (sec + float(row["offset"])) % float(row["green_sec"]) < float(row["p2_green"])
                                for sec in range(step * 5, step * 5 + 5)) / 5
                            actual = self.clock(control, self.cfg, spec, step)
                            error = abs(expected - actual)
                            max_error = max(error, max_error)
                            self.assertLessEqual(error, 1e-12, (path.name, signal, phase, offset, step, expected, actual))
                            checks += 1
        report = {"n7_actions": len(self.actions), "signals": len(self.cfg.network.signals),
                  "relative_offsets_sec": [-20, -10, 0, 10, 20], "substep_checks": checks,
                  "max_fraction_error": max_error, "seed_changed_phase_values": mutated,
                  "seed_changed_above_2ms": large_mutations, "seed_max_change_sec": largest,
                  "oracle": "existing write_action_csv SG windows, integer-second hold as actual VBS event scheduler",
                  "production_applied": True}
        (ROOT / "diagnostics/signal_contract_regression.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    def test_locked_offset_remains_physically_zero(self):
        cfg = copy.deepcopy(self.cfg)
        cfg.network.signal_actuation_contract["offset_writer"] = "intent_only"
        control = self.action(offset=20)
        zero = self.action(offset=0)
        spec = {"intersection": "SC1001", "phase": "SC1001_p3"}
        for step in range(30):
            self.assertEqual(self.clock(control, cfg, spec, step), self.clock(zero, cfg, spec, step))

    def test_actual_follower_local_green_fractions_match_each_model_movement(self):
        from src.controllers import wu_faithful_follower
        controller = adapter.build_priced_wu_link_controller(self.cfg, self.tuning)
        control = self.action(offset=0)
        follower = controller.nash_solver
        with mock.patch.object(wu_faithful_follower, "_phase_green_fraction", proposed.wrap_clock(self.original_clock)):
            for signal in self.cfg.network.signals:
                values = {p: control.green_times[signal + "_" + p] for p in proposed.PHASES}
                fractions = follower._offset_green_fractions_vec(signal, values, 0., 30, 180)
                model = follower._local_models[signal]
                for movement in model.movements:
                    for sub in range(30):
                        expected = self.clock(control, self.cfg, model.specs[movement], 180 + sub)
                        self.assertEqual(fractions[movement][sub], expected, (signal, movement, sub))
        old = adapter.build_priced_wu_link_controller(self.old_cfg, self.tuning).nash_solver
        with mock.patch.object(wu_faithful_follower, "_phase_green_fraction", self.original_clock):
            for signal in self.old_cfg.network.signals:
                values = {p: control.green_times[signal + "_" + p] for p in proposed.PHASES}
                self.assertEqual(old._offset_green_fractions_vec(signal, values, 10., 30, 180),
                                 self.original_local_fractions(old, signal, values, 10., 30, 180))

    def test_native_selector_uses_actual_mainline_selection(self):
        control = adapter.native_fixed_control(self.old_cfg, self.ControlAction)
        for signal in self.old_cfg.network.signals:
            axes = self.plan["controllers"][signal[2:]]["axis_green_sec"]
            self.assertEqual({p: control.green_times[signal + "_" + p] for p in proposed.PHASES}, axes)
        self.assertEqual(control.diagnostics["native_fixed_native_program_replay"], 0.)
        self.assertIn("mainline_20260825", control.diagnostics["native_fixed_plan_path"])

    def test_shared_setup_and_worker_install_actual_model_aliases(self):
        from diagnostics.probe_model_area_integration import build_projected
        from evaluation.controllers import runtime_setup
        from src.models import urban_queue_model
        tun = copy.deepcopy(self.tuning)
        tun["urban"]["physical_signal_contract"] = True
        tun["actuation"]["real_world_signal_control"]["offset_writer"] = "test_only"
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps(tun), encoding="utf-8")
            fixture = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"
            cfg, state, dm, _, raw, _, metadata = build_projected(config, fixture / "state_000900.json", fixture / "action_000001.json")
            self.assertEqual(metadata["physical_signal_contract_nodes"], 17)
            control = adapter.control_from_json(ROOT / "diagnostics/frozen_n7_2100_green_action.json", cfg, self.ControlAction)
            proposed.validate_control(control, cfg)
            # Spawn semantics: only cfg is deep-copied; hooks are freshly installed.
            restored = copy.deepcopy(cfg)
            for _ in range(2):
                runtime_setup.install_worker_runtime(adapter, restored, raw, dm)
                self.assertEqual(restored.network.signal_green_max("SC109"), 90.)
                for signal in restored.network.signals:
                    for phase in proposed.PHASES:
                        spec = {"intersection": signal, "phase": signal + "_" + phase}
                        for step in (180, 181, 184, 209, 210):
                            self.assertEqual(urban_queue_model._phase_green_fraction(control, restored, spec, step), proposed.phase_fraction(control, restored, spec, step))
            with self.assertRaisesRegex(ValueError, "authority differ"):
                proposed.validate_writer(control, restored, self.plan, "intent_only")


    def test_actual_vbs_state_function(self):
        source = (ROOT / "scripts/run_real_world_stackelberg_controller.vbs").read_text(encoding="utf-8")
        names = ("SignalGroupPlanKey", "SignalGroupPlanWindows", "SignalGroupStateFromPlan", "AnySignalGroupGreenAt", "FMod")
        functions = [re.search(r"(?ms)^Function " + name + r"\([^\n]*\).*?^End Function", source)[0] for name in names]
        script = ['Option Explicit', 'Const AMBER_SEC = 3', 'Dim sgPlanWindows, i, sec, fraction',
                  'Set sgPlanWindows = CreateObject("Scripting.Dictionary")', *functions]
        expected = []
        cases = []
        for cycle in (150., 150.001, 149.999):
            cfg = copy.deepcopy(self.cfg)
            for signal in cfg.network.signals:
                cfg.network.cycle_length_by_signal[signal] = cycle
                cfg.network.effective_green_total_by_signal[signal] = round(cycle - 3 * len(cfg.network.signal_live_phases(signal)), 3)
            for offset in (-20, -10, 0, 10, 20):
                control = proposed.prepare_control(self.action(offset=0), cfg)
                offsets = {s: round(offset % cycle, 3) for s in cfg.network.signals}
                control.offsets.update(offsets)
                control.diagnostics[offset_promotion.FORCED_ARM_TABLE_KEY] = json.dumps(offsets)
                cases.append((cfg, control))
        for cfg, control in cases:
            rows = self.rows(control, cfg)
            script.append('sgPlanWindows.RemoveAll')
            for row in rows:
                if row["kind"] == "signal_sg":
                    script.append(f'sgPlanWindows("{row["sc_no"]}-{row["dsd_no"]}") = "{row["p1_green"]}|{row["p2_green"]};"')
            for signal in cfg.network.signals:
                cycle = cfg.network.signal_cycle_length(signal)
                off = control.offsets[signal]
                node = self.plan["controllers"][signal[2:]]
                for phase in proposed.PHASES:
                    if not node["phase_segments"][phase]:
                        continue
                    group = node["phase_segments"][phase][0]["sg_no"]
                    spec = {"intersection": signal, "phase": signal + "_" + phase}
                    for step in (179, 180, 181, 184, 195, 209, 210, 211, 29999, 30000, 30001):
                        script += ['fraction = 0', f'For sec = {step * 5} To {step * 5 + 4}',
                                   f'If SignalGroupStateFromPlan({signal[2:]}, {group}, FMod(sec + {off}, {cycle}), {cycle}) = "GREEN" Then fraction = fraction + 1',
                                   'Next', 'WScript.Echo CStr(fraction)']
                        expected.append(round(self.clock(control, cfg, spec, step) * 5))
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "oracle.vbs"
            file.write_text("\n".join(script), encoding="utf-8")
            result = subprocess.run(["cscript.exe", "//nologo", str(file)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([int(v) for v in result.stdout.splitlines()], expected)
        (ROOT / "diagnostics/signal_contract_vbs_oracle.json").write_text(json.dumps({
            "function": "actual SignalGroupStateFromPlan + actual FMod, extracted unchanged from frozen VBS",
            "cycles": [150., 150.001, 149.999], "checks": len(expected),
            "relative_offsets": [-20, -10, 0, 10, 20], "status": "PASS",
            "scope": "VBS function semantics with actual CSV rows; no live COM claim"}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
