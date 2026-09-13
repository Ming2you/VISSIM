"""Validate forced offset arms and byte-preserving native network preparation."""
from __future__ import annotations
import copy
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from evaluation.controllers import diagnostic_signal_profile, offset_promotion
from diagnostics.prepare_native_offset_network import prepare, shift_sig_bytes
from diagnostics import test_diagnostic_profile as profile_tests


class SignalProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profile_tests.ProfileTests.setUpClass()
        cls.adapter, cls.cfg = profile_tests.ProfileTests.adapter, profile_tests.ProfileTests.cfg
        cls.mapping, cls.ControlAction = profile_tests.ProfileTests.mapping, profile_tests.ProfileTests.ControlAction
        cls.plan = cls.adapter.load_signal_group_actuation_plan()

    def test_forced_tables_change_only_relative_offset_csv_columns(self):
        base_rows = None
        for name, delta in (("zero", 0), ("plus10", 10), ("minus10", -10), ("plus20", 20), ("minus20", -20)):
            tuning = self.adapter.load_optional_json(str(ROOT / f"diagnostics/signal_profile_config_{name}.json"))
            action = diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)
            actuation = diagnostic_signal_profile.fixed_actuation(tuning["actuation"])
            locked = offset_promotion.evaluate({key: None for key in offset_promotion.LOCK_NAMES})
            writer = offset_promotion.resolve_writer(actuation, verdict=locked)
            self.assertEqual(writer, "test_only")
            self.assertFalse(locked["promoted"])
            self.assertEqual(set(action.vsl.values()), {120})
            self.assertEqual(action.offsets["SC1001"], delta % 150)
            self.assertEqual(action.offsets["SC1004"], (-delta) % 150)
            self.assertTrue(all(v == 0 for k, v in action.offsets.items() if k not in {"SC1001", "SC1004"}))
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "action.csv"
                self.adapter.write_action_csv(path, action, self.cfg, self.mapping,
                    profile_tests.ProfileTests.plain_segment_vsl, {}, actuation,
                    signal_group_plan_table=self.plan, offset_writer=writer)
                with path.open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
            self.assertEqual(len([r for r in rows if r["kind"] == "signal"]), 17)
            self.assertTrue(all(float(r["green_sec"]) == 10 for r in rows if r["kind"] == "ramp_meter"))
            for row in rows:
                if row["kind"] in ("signal", "signal_sg"):
                    self.assertEqual(float(row["offset"]), action.offsets[f"SC{row['sc_no']}"])
                row.pop("offset", None)
            if base_rows is None:
                base_rows = rows
            else:
                self.assertEqual(rows, base_rows)

    def test_source_or_plan_drift_is_rejected(self):
        tuning = self.adapter.load_optional_json(str(ROOT / "diagnostics/signal_profile_config_zero.json"))
        altered = copy.deepcopy(tuning)
        altered["diagnostic"]["signal_profile"]["green_action_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "action SHA"):
            diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, altered, self.plan, ROOT)
        altered_plan = copy.deepcopy(self.plan)
        altered_plan["amber_sec"] = 2
        with self.assertRaisesRegex(ValueError, "SG plan"):
            diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, altered_plan, ROOT)
        tuning["diagnostic"]["signal_profile"]["relative_offset_sec"] = {"SC99999": 10}
        with self.assertRaisesRegex(ValueError, "unknown signal"):
            diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)

    def test_recorded_vsl_replay_preserves_complete_nonconstant_profile(self):
        tuning = self.adapter.load_optional_json(str(ROOT / "diagnostics/signal_profile_config_zero.json"))
        recorded = json.loads((ROOT / tuning["diagnostic"]["signal_profile"]["green_action_json"]).read_text())
        expected = profile_tests.profile.build_control(self.cfg, self.ControlAction,
            {"diagnostic": {"vsl_profile": {"FW_E__seg0": 80}}}, self.mapping,
            profile_tests.ProfileTests.allowed).vsl
        recorded["vsl"] = expected
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "action.json"
            source.write_text(json.dumps(recorded), encoding="utf-8")
            spec = tuning["diagnostic"]["signal_profile"]
            spec.update(green_action_json=str(source),
                        green_action_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                        replay_recorded_vsl=True)
            action = diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)
            self.assertEqual(action.vsl, expected)
            spec["replay_recorded_vsl"] = False
            baseline = diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)
            self.assertEqual(set(baseline.vsl.values()), {120.0})

    def test_recorded_vsl_replay_rejects_incomplete_or_inconsistent_zones(self):
        tuning = self.adapter.load_optional_json(str(ROOT / "diagnostics/signal_profile_config_zero.json"))
        recorded = json.loads((ROOT / tuning["diagnostic"]["signal_profile"]["green_action_json"]).read_text())
        profile = profile_tests.profile.build_control(self.cfg, self.ControlAction,
            {"diagnostic": {"vsl_profile": {"FW_E__seg0": 80}}}, self.mapping,
            profile_tests.ProfileTests.allowed).vsl
        variants = []
        missing = dict(profile)
        missing.pop("FW_E__seg2")
        variants.append(missing)
        for key, value in (("FW_X", 120), ("FW_E__seg2", 120), ("FW_E__seg0", 90),
                           ("FW_E__seg0", True), ("FW_E__seg0", "80")):
            altered = dict(profile)
            altered[key] = value
            variants.append(altered)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "action.json"
            spec = tuning["diagnostic"]["signal_profile"]
            spec.update(green_action_json=str(source), replay_recorded_vsl=True)
            for values in variants:
                with self.subTest(values=values):
                    recorded["vsl"] = values
                    source.write_text(json.dumps(recorded), encoding="utf-8")
                    spec["green_action_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
                    with self.assertRaisesRegex(ValueError, "VSL"):
                        diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)

    def test_recorded_targets_replay_preserves_targets_without_changing_commands(self):
        tuning = self.adapter.load_optional_json(str(ROOT / "diagnostics/signal_profile_config_zero.json"))
        spec = tuning["diagnostic"]["signal_profile"]
        recorded = json.loads((ROOT / spec["green_action_json"]).read_text())
        recorded.update(N_P_star=-250.0, N_UF_star=1887.525930614418)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "action.json"
            source.write_text(json.dumps(recorded), encoding="utf-8")
            spec.update(green_action_json=str(source),
                        green_action_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
            baseline = diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)
            spec["replay_recorded_targets"] = False
            disabled = diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)
            self.assertEqual(vars(baseline), vars(disabled))
            spec["replay_recorded_targets"] = True
            replayed = diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)
            self.assertEqual((replayed.N_P_star, replayed.N_UF_star),
                             (recorded["N_P_star"], recorded["N_UF_star"]))
            for field in ("green_times", "offsets", "vsl", "ramp_metering"):
                self.assertEqual(getattr(baseline, field), getattr(replayed, field))

    def test_recorded_targets_replay_rejects_missing_nonfinite_or_boolean_values(self):
        tuning = self.adapter.load_optional_json(str(ROOT / "diagnostics/signal_profile_config_zero.json"))
        spec = tuning["diagnostic"]["signal_profile"]
        recorded = json.loads((ROOT / spec["green_action_json"]).read_text())
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "action.json"
            spec.update(green_action_json=str(source), replay_recorded_targets=True)
            for key, value in (("N_P_star", None), ("N_UF_star", None),
                               ("N_P_star", float("nan")), ("N_UF_star", float("inf")),
                               ("N_P_star", True), ("N_UF_star", "1887"), ("N_UF_star", -1.0)):
                with self.subTest(key=key, value=value):
                    payload = dict(recorded, N_P_star=-250.0, N_UF_star=1887.525930614418)
                    if value is None:
                        payload.pop(key)
                    else:
                        payload[key] = value
                    source.write_text(json.dumps(payload), encoding="utf-8")
                    spec["green_action_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
                    with self.assertRaisesRegex(ValueError, "recorded leader target"):
                        diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)
            spec["replay_recorded_targets"] = "true"
            with self.assertRaisesRegex(ValueError, "boolean"):
                diagnostic_signal_profile.build_control(self.cfg, self.ControlAction, tuning, self.plan, ROOT)


class NativeNetworkTests(unittest.TestCase):
    def test_native_sources_unchanged_and_shared_program_clones_shift_independently(self):
        audit = json.loads((ROOT / "diagnostics/native_signal_replay_audit.json").read_text(encoding="utf-8"))
        source_sig = Path(next(row["program"] for row in audit["controllers"] if row["sc"] == 1001)).read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "native.sig").write_bytes(source_sig)
            source = tmp / "source.inpx"
            network = b'<network><signalControllers><signalController no="1001" active="true" supplyFile2="#data#native.sig" progNo="1"></signalController><signalController no="1004" active="true" supplyFile2="#data#native.sig" progNo="1"></signalController></signalControllers></network>'
            source.write_bytes(network)
            recipe = {"name": "opposed", "relative_native_offset_sec": {"SC1001": 10, "SC1004": -10}}
            report = prepare(source, tmp / "opposed.inpx", recipe)
            self.assertEqual(source.read_bytes(), network)
            self.assertEqual((tmp / "native.sig").read_bytes(), source_sig)
            self.assertEqual(report["treatment_start_sec"], 0)
            self.assertEqual([r["programs"][0]["after_offset_sec"] for r in report["controllers"]], [85, 65])
            self.assertTrue(all(r["native_clock_state_checks"] > 0 for r in report["controllers"]))
            self.assertEqual(prepare(source, tmp / "opposed.inpx", recipe), report)
            with self.assertRaises(ValueError):
                prepare(source, source, recipe)
            zero, _ = shift_sig_bytes(source_sig, 0, zero=True)
            self.assertNotEqual(zero, source_sig)
            native, _ = shift_sig_bytes(source_sig, 0)
            self.assertEqual(native, source_sig)
            with self.assertRaises(ValueError):
                shift_sig_bytes(source_sig, float("nan"))


if __name__ == "__main__":
    unittest.main()
