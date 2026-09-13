"""Installed production: declarations -> shared clock/CSV -> actual VBS parser."""
from __future__ import annotations
import copy
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from diagnostics.probe_signal_feasibility import setup
from evaluation.controllers import vissim_stackelberg_adapter as adapter, offset_promotion, signal_actuation_contract
RUNNER = "scripts/run_real_world_stackelberg_controller.vbs"


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {RUNNER: (ROOT / RUNNER).read_text(encoding="utf-8")}
        cls.promotion = offset_promotion
        cls.contract = signal_actuation_contract
        cls.cfg, cls.state, cls.dm, cls.tuning, cls.raw, cls.mapping, _ = setup()
        cls.tuning = copy.deepcopy(cls.tuning)
        cls.tuning.setdefault("urban", {})["physical_signal_contract"] = True
        cls.tuning["actuation"]["real_world_signal_control"]["offset_writer"] = "experiment"
        cls.plan = adapter.load_signal_group_actuation_plan()
        with mock.patch.dict(os.environ, RW_OFFSET_WRITER="experiment"):
            cls.contract.configure(cls.cfg, cls.tuning, cls.plan)
        from src.models.state import ControlAction, segment_vsl
        cls.ControlAction, cls.segment_vsl = ControlAction, staticmethod(segment_vsl)
        cls.writer = staticmethod(adapter.write_action_csv)
        cls.meta_writer = staticmethod(adapter._action_csv_metadata)

    def control(self):
        action = self.ControlAction.uncontrolled(self.cfg)
        raw = json.loads((ROOT / "diagnostics/frozen_n7_2100_green_action.json").read_text(encoding="utf-8"))
        action.green_times.update(raw["green_times"])
        action = self.contract.prepare_control(action, self.cfg)
        action.offsets.update({s: (-10.0 if i % 2 else 20.0) for i, s in enumerate(self.cfg.network.signals)})
        return action

    def metadata(self, action):
        return {"controller_status": "ok", "physical_signal_contract_enabled": 1.0,
                **self.promotion.action_metadata(action, "experiment", self.promotion.evaluate(evidence={}))}

    def write(self, path, action):
        self.writer(path, action, self.cfg, self.mapping, self.segment_vsl, self.metadata(action),
                    self.tuning["actuation"], self.plan, "experiment")

    def test_dual_declaration_contract_and_production_gates(self):
        p = self.promotion
        verdict = p.evaluate(evidence={})
        self.assertFalse(verdict["promoted"])
        self.assertTrue(all(row["status"] == "NOT_EVALUATED" for row in verdict["locks"]))
        for mode, env, flag in (("experiment", "", True), ("", "experiment", True),
                                ("test_only", "experiment", True), ("experiment", "experiment", False)):
            with self.subTest(mode=mode, env=env, flag=flag), mock.patch.dict(os.environ, RW_OFFSET_WRITER=env):
                with self.assertRaises(p.OffsetPromotionError):
                    p.resolve_writer({"real_world_signal_control": {"offset_writer": mode}}, verdict=verdict, physical_signal_contract=flag)
        with mock.patch.dict(os.environ, RW_OFFSET_WRITER="experiment"):
            self.assertEqual(p.resolve_writer(self.tuning["actuation"], verdict=verdict, physical_signal_contract=True), "experiment")
            # An explicit experiment must never relabel itself production.
            self.assertEqual(p.resolve_writer(self.tuning["actuation"], verdict={"promoted": True}, physical_signal_contract=True), "experiment")
        with mock.patch.dict(os.environ, RW_OFFSET_WRITER=""):
            self.assertEqual(p.resolve_writer({}, verdict=verdict), "intent_only")
            self.assertEqual(p.resolve_writer({"real_world_signal_control": {"offset_writer": "test_only"}}, verdict=verdict), "test_only")
            with self.assertRaises(p.OffsetPromotionError):
                p.resolve_writer({"real_world_signal_control": {"offset_writer": "production"}}, verdict={"promoted": True})
        self.assertEqual(p.matrix_lever_status(verdict), "BLOCKED")
        evidence = {key: {"status": "PASS", "signal_profile_id": "fixture", "topology_sha256": "same"} for key in p.LOCK_NAMES}
        self.assertTrue(p.evaluate(evidence=evidence)["promoted"])
        evidence["n8_4_runtime"]["topology_sha256"] = "different"
        self.assertFalse(p.evaluate(evidence=evidence)["promoted"])
        self.assertEqual(p.matrix_lever_status(p.evaluate(evidence=evidence)), "BLOCKED")

    def test_shared_modulo_csv_precision_and_nonfinite(self):
        action = self.control()
        before = dict(action.offsets)
        for signal in self.cfg.network.signals:
            cycle = self.cfg.network.signal_cycle_length(signal)
            for value, expected in ((-10., cycle - 10.), (cycle, 0.), (cycle - .0001, 0.), (-.0001, 0.), (2 * cycle + 10.0004, 10.)):
                action.offsets[signal] = value
                self.assertAlmostEqual(self.contract.written_offset_sec(action, self.cfg, signal), expected)
            for value in (float("nan"), float("inf"), -float("inf")):
                action.offsets[signal] = value
                with self.assertRaises(self.promotion.OffsetPromotionError):
                    self.contract.written_offset_sec(action, self.cfg, signal)
            action.offsets[signal] = before[signal]
        self.assertEqual(action.offsets, before)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "action.csv"
            self.write(path, action)
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
        values = {str(s): self.contract.written_offset_sec(action, self.cfg, s) for s in self.cfg.network.signals}
        for row in rows:
            if row["kind"] in ("signal", "signal_sg"):
                self.assertEqual(float(row["offset"]), values["SC" + row["sc_no"]])
                self.assertIn("offset_writer=experiment", row["metadata"])
        changed = 0
        zero = action.copy()
        zero.offsets = {s: 0. for s in self.cfg.network.signals}
        for s in self.cfg.network.signals:
            for phase in self.cfg.network.signal_live_phases(s):
                spec = {"phase": s + "_" + phase}
                changed += sum(self.contract.phase_fraction(action, self.cfg, spec, step) != self.contract.phase_fraction(zero, self.cfg, spec, step) for step in range(180, 210))
        self.assertGreater(changed, 0)

    def test_metadata_and_forced_test_only_preserved(self):
        action = self.control()
        metadata = self.metadata(action)
        self.assertEqual(metadata["offset_production_writes"], 0.)
        self.assertEqual(metadata["offset_promotion_status"], "NOT_EVALUATED")
        metadata["physical_projection_provenance"] = {"route": [1, 2], "source": "fixture"}
        encoded = self.meta_writer(metadata)
        self.assertNotIn(",", encoded)
        self.assertIn("physical_projection_provenance_sha256=", encoded)
        self.assertEqual(metadata["physical_projection_provenance"]["route"], [1, 2])
        with self.assertRaises(ValueError):
            self.meta_writer({**metadata, "physical_signal_contract_enabled": 0.})
        action.diagnostics[self.promotion.FORCED_ARM_TABLE_KEY] = json.dumps({"SC1004": 10.})
        self.assertEqual(self.promotion.written_offset_sec("SC1004", action, "test_only"), 10.)
        self.assertEqual(self.promotion.written_offset_sec("SC1004", action, "intent_only"), 0.)

    @unittest.skipUnless(sys.platform == "win32", "requires cscript; no live VISSIM")
    def test_actual_vbs_csv_contract_before_first_event(self):
        from diagnostics import test_profile_runner_invocation as harness
        for mutation in (None, "sg_offset", "metadata", "sg_window"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                tmp = Path(directory)
                runner = tmp / "proposed_runner.vbs"
                runner.write_text(self.sources[RUNNER], encoding="utf-8")
                action_path = tmp / "trial.csv"
                self.write(action_path, self.control())
                if mutation:
                    with action_path.open(newline="", encoding="utf-8") as stream:
                        rows = list(csv.DictReader(stream))
                        fields = list(rows[0])
                    for row in rows:
                        if mutation == "sg_offset" and row["kind"] == "signal_sg" and row["sc_no"] == "1004":
                            row["offset"] = str((float(row["offset"]) + 1) % 150)
                        if mutation == "metadata":
                            row["metadata"] = "ok"
                        if mutation == "sg_window" and row["kind"] == "signal_sg" and row["sc_no"] == "1004":
                            row["p2_green"] = row["p1_green"]
                    with action_path.open("w", newline="", encoding="utf-8") as stream:
                        writer = csv.DictWriter(stream, fields)
                        writer.writeheader(); writer.writerows(rows)
                with mock.patch.object(harness, "RUNNER", runner):
                    script_path = harness.build_harness(tmp, "wu-link", "signal_profile_config_sc1004_green10.json")
                script = script_path.read_text(encoding="utf-16")
                script = script.replace('RW_OFFSET_WRITER = "test_only"', 'RW_OFFSET_WRITER = "experiment"')
                begin = script.rindex('If UseContinuousStaticMode() Then')
                end = script.index('WScript.Echo "LAST_ACTION=" & lastActionJson', begin) + len('WScript.Echo "LAST_ACTION=" & lastActionJson')
                script = script[:begin] + ('If ApplyActionCsv(900, ' + harness.q(action_path) + ', "wu-link") Then\n'
                          'WScript.Echo "EXPERIMENT_ACCEPTED"\nApplyRuntimeSignals 900\nElse\n'
                          'WScript.Echo "EXPERIMENT_REJECTED"\nEnd If\n') + script[end:]
                script_path.write_text(script, encoding="utf-16")
                result = subprocess.run(["cscript.exe", "//nologo", str(script_path)], capture_output=True, text=True, timeout=30,
                                        env=dict(os.environ, RW_MAINLINE_SG_ONLY="1", RW_SIGNAL_WRITE_ON_CHANGE="0"))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("EXPERIMENT_" + ("ACCEPTED" if mutation is None else "REJECTED"), result.stdout)
                if mutation == "sg_offset":
                    self.assertIn("EXPERIMENT_SG_OFFSET_MISMATCH", result.stdout)
                if mutation is None:
                    with (tmp / "signalTraceFile.csv").open(newline="") as stream:
                        trace = list(csv.DictReader(stream))
                    self.assertTrue(any(row["sc"] == "1004" for row in trace))
                    self.assertTrue(all(row["ok"] == "1" for row in trace))

    @unittest.skipUnless(sys.platform == "win32", "requires cscript; no live VISSIM")
    def test_experiment_decision_failure_stops_real_runner_branch(self):
        from diagnostics import test_profile_runner_invocation as harness
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            runner = tmp / "proposed_runner.vbs"
            runner.write_text(self.sources[RUNNER], encoding="utf-8")
            with mock.patch.object(harness, "RUNNER", runner):
                script_path = harness.build_harness(tmp, "wu-link", "signal_profile_config_sc1004_green10.json", failure="missing")
            script = script_path.read_text(encoding="utf-16")
            script = script.replace('RW_OFFSET_WRITER = "test_only"', 'RW_OFFSET_WRITER = "experiment"')
            script_path.write_text(script, encoding="utf-16")
            result = subprocess.run(["cscript.exe", "//nologo", str(script_path)], capture_output=True, text=True, timeout=30,
                                    env=dict(os.environ, RW_MAINLINE_SG_ONLY="1"))
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("ERROR=ACTION_CSV_MISSING", result.stdout)
            self.assertIn("FAKE_SIM_STOP", result.stdout)
            self.assertNotIn("UNEXPECTED_CONTINUATION", result.stdout)


if __name__ == "__main__":
    unittest.main()
