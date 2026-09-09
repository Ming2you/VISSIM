"""Offline profile/CSV tests and a mocked execution of the real VBS scheduler.

The scheduler and main pipeline come from the installed canonical sources.
No VISSIM instance is created and no existing production file is written.
"""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RAW_STATE = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry/state_000900.json"
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from evaluation.controllers import diagnostic_profile as profile


def integration_source(relative):
    """Read the source under test without applying a proposal fallback."""
    return (ROOT / relative).read_text(encoding="utf-8-sig")


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        cls.adapter = adapter
        cls.tuning = adapter.load_optional_json(str(ROOT / "evaluation/configs/n21_n7_20260908.json"))
        adapter.install_config_switches(cls.tuning)
        cls.mapping = json.loads((ROOT / cls.tuning["mapping_json"]).read_text(encoding="utf-8"))
        adapter.repo_imports(ROOT / "vendor/NumSim-mine")
        from src.models.state import ControlAction, segment_vsl
        cls.ControlAction = ControlAction
        cls.plain_segment_vsl = staticmethod(segment_vsl)
        cls.cfg = adapter.build_config(ROOT / "vendor/NumSim-mine", 150, 1800,
                                       "fast-smoke", {}, cls.tuning,
                                       local_observation=True, flagship=False)
        adapter.install_freeway_segment_lanes(cls.cfg, cls.tuning, cls.mapping)
        adapter.install_freeway_vsl_zones(cls.cfg, cls.tuning)
        config = ROOT / "evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs"
        cls.allowed = re.search(r'RW_ALLOWED_VSL_SPEEDS = "([^"]+)"',
                                config.read_text(encoding="utf-8-sig")).group(1)

    def control(self, values, **kwargs):
        return profile.build_control(kwargs.get("cfg", self.cfg), self.ControlAction,
                                     {"diagnostic": {"vsl_profile": values}},
                                     kwargs.get("mapping", self.mapping),
                                     kwargs.get("allowed", self.allowed))

    def test_real_zone_profile_and_baseline(self):
        from src.models.state import segment_vsl
        for cap in (80, 100, 120):
            action = self.control({"FW_E__seg0": cap, "FW_E__seg5": cap})
            for link in self.cfg.network.freeway_links:
                for cell in range(21):
                    expected = cap if link == "FW_E" and cell < 10 else 120
                    self.assertEqual(self.plain_segment_vsl(action, link, cell, self.cfg), expected)
                    self.assertEqual(segment_vsl(action, link, cell, self.cfg), expected)
        self.assertEqual(set(self.control({}).vsl.values()), {120.0})

    def test_reject_nonhead_missing_dsd_and_bad_speeds(self):
        for key in ("FW_E__seg2", "FW_E__seg9", "FW_E", "FW_X__seg0"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.control({key: 80})
        bad_mapping = copy.deepcopy(self.mapping)
        for seg in bad_mapping["segments"]:
            if seg["model_link"] == "FW_E" and seg["model_segment_index"] == 5:
                seg["dsds"] = []
        with self.assertRaisesRegex(ValueError, "no physical DSD"):
            self.control({"FW_E__seg5": 80}, mapping=bad_mapping)
        for speed in (65, 90, float("nan"), float("inf"), -80, True, "80"):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                self.control({"FW_E__seg0": speed})
        cfg = copy.deepcopy(self.cfg)
        cfg.freeway_follower.vsl_set.append(65)
        with self.assertRaisesRegex(ValueError, "unsupported VSL"):
            self.control({"FW_E__seg0": 65}, cfg=cfg)
        with self.assertRaises(ValueError):
            self.control({}, allowed="")
        with self.assertRaises(ValueError):
            self.control({}, allowed="80,100")

    def test_csv_has_only_physical_vsl_and_eight_fully_open_meters(self):
        action = self.control({"FW_E__seg0": 80, "FW_E__seg5": 80})
        actuation = profile.fixed_actuation(self.tuning["actuation"])
        self.assertEqual(self.tuning["actuation"]["real_world_ramp_metering"]["allocation"], "measured_table")
        # Even low requested group rates must not close a physical meter.
        action.ramp_metering = {key: 1 for key in action.ramp_metering}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "action.csv"
            self.adapter.write_action_csv(path, action, self.cfg, self.mapping,
                                          self.plain_segment_vsl,
                                          {"suppress_signal_rows": 1}, actuation)
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
        self.assertEqual({row["kind"] for row in rows}, {"vsl", "ramp_meter"})
        meters = [row for row in rows if row["kind"] == "ramp_meter"]
        self.assertEqual(len(meters), 8)
        for row in meters:
            self.assertEqual(float(row["green_sec"]), 10.0)
            physical = next(m for m in self.mapping["ramp_meters"] if m["id"] == row["id"])
            self.assertEqual(float(row["rate_vph"]), physical["capacity_vph"])
        segments = {seg["segment_id"]: seg for seg in self.mapping["segments"]}
        vsl_rows = [row for row in rows if row["kind"] == "vsl"]
        expected_dsds = {str(d["dsd_no"]) for s in self.mapping["segments"] for d in s["dsds"]}
        self.assertEqual({row["dsd_no"] for row in vsl_rows}, expected_dsds)
        self.assertEqual(len(vsl_rows), len(expected_dsds))
        for row in vsl_rows:
            seg = segments[row["id"]]
            expected = 80 if seg["model_link"] == "FW_E" and seg["model_segment_index"] < 10 else 120
            self.assertEqual(float(row["speed_kph"]), expected)

    def test_installed_adapter_compiles_with_diagnostic_branch(self):
        source = integration_source("evaluation/controllers/vissim_stackelberg_adapter.py")
        compile(source, "installed_canonical_adapter", "exec")
        self.assertTrue("diagnostic_profile.CONTROLLERS" in source)
        self.assertTrue("diagnostic_fixed_profile_guards_bypassed" in source)

    @unittest.skipUnless(RAW_STATE.exists(), "requires local no-control raw snapshot")
    def test_main_does_not_publish_fixed_control_after_profile_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, __file__, "--probe-reject", "80", tmp],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("injected diagnostic profile failure", result.stderr)
            self.assertFalse((Path(tmp)/"action.json").exists())
            self.assertFalse((Path(tmp)/"action.csv").exists())

    @unittest.skipUnless(RAW_STATE.exists(), "requires local no-control raw snapshot")
    def test_real_main_pipeline_has_no_policy_optimizer_or_closed_meter(self):
        for cap in (80, 100, 120):
            with self.subTest(cap=cap), tempfile.TemporaryDirectory() as tmp:
                result = subprocess.run([sys.executable, __file__, "--probe", str(cap), tmp],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                action = json.loads((Path(tmp) / "action.json").read_text(encoding="utf-8"))
                self.assertEqual(action["metadata"]["controller_status"], "ok")
                self.assertEqual(action["metadata"]["suppress_signal_rows"], 1)
                self.assertEqual(action["vsl"]["FW_E__seg0"], cap)
                self.assertEqual(action["vsl"]["FW_E__seg5"], cap)
                self.assertEqual(action["vsl"]["FW_E__seg10"], 120)
                with (Path(tmp) / "action.csv").open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual({r["kind"] for r in rows}, {"vsl", "ramp_meter"})
                self.assertTrue(all(float(r["green_sec"]) == 10 for r in rows if r["kind"] == "ramp_meter"))

    @unittest.skipUnless(sys.platform == "win32", "VBScript scheduler mock uses Windows cscript")
    def test_real_static_scheduler_applies_at_900_and_logs_without_urban_control(self):
        source = integration_source("scripts/run_real_world_stackelberg_controller.vbs")
        names = ("UseContinuousStaticMode", "SignalRowsSuppressedForController", "RunContinuousStaticMode")
        extracted = []
        for name in names:
            extracted.append(re.search(rf"(?m)^(?:Function|Sub) {name}\([^\n]*\).*?^End (?:Function|Sub)",
                                       source, flags=re.S | re.M).group(0))
        # Use the actual static scheduler with stubs, never VISSIM COM.
        mock = '''
Dim controllerName, controlStartSec, simPeriod, stateLogIntervalSec, Vissim
controllerName = "diagnostic-vsl-profile"
controlStartSec = 900
simPeriod = 1800
stateLogIntervalSec = 30
Class FakeSimulation
    Sub RunSingleStep()
    End Sub
End Class
Class FakeVissim
    Public Simulation
    Private Sub Class_Initialize()
        Set Simulation = New FakeSimulation
    End Sub
End Class
Set Vissim = New FakeVissim
Function ForceStepwiseMode()
    ForceStepwiseMode = False
End Function
Sub InitializeComRampMeterControl()
    WScript.Echo "RAMPS_OPEN"
End Sub
Sub RunControllerDecision(sec)
    WScript.Echo "DECISION=" & sec
End Sub
Sub ApplyIncidentLaneClosure(sec)
End Sub
Sub LogStateCsv(sec)
    WScript.Echo "LOG=" & sec
End Sub
Function NextLogAfter(sec)
    NextLogAfter = (Int(sec / 30) + 1) * 30
End Function
Function NextIncidentTransitionAfter(sec)
    NextIncidentTransitionAfter = 999999
End Function
Sub RunContinuousTo(sec)
    WScript.Echo "CONTINUOUS=" & sec
End Sub
Sub ValidateRuntimeSignalPersistence(sec)
End Sub
Sub ValidateDiagnosticProfileNativeSignals(sec)
    WScript.Echo "NATIVE_READBACK=" & sec
End Sub
If Not UseContinuousStaticMode() Then WScript.Quit 2
If Not SignalRowsSuppressedForController(controllerName) Then WScript.Quit 3
RunContinuousStaticMode
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scheduler_mock.vbs"
            path.write_text("\n".join(extracted) + "\n" + mock, encoding="utf-16")
            result = subprocess.run(["cscript.exe", "//nologo", str(path)],
                                    text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual([line for line in lines if line.startswith("DECISION=")],
                         ["DECISION=1", "DECISION=900"])
        self.assertLess(lines.index("LOG=900"), lines.index("DECISION=900"))
        self.assertIn("CONTINUOUS=1800", lines)
        self.assertIn("LOG=1800", lines)
        self.assertEqual(lines.count("RAMPS_OPEN"), 1)
        self.assertEqual([line for line in lines if line.startswith("NATIVE_READBACK=")],
                         ["NATIVE_READBACK=1", "NATIVE_READBACK=900", "NATIVE_READBACK=1800"])
        decision = re.search(r"(?m)^Sub RunControllerDecision\(.*?^End Sub", source, re.S | re.M).group(0)
        self.assertIn("simSec < controlStartSec", decision)
        self.assertIn("effController = warmupControllerName", decision)
        self.assertIn('Q(RW_ALLOWED_VSL_SPEEDS)', decision)
        static = extracted[-1]
        self.assertNotIn("ApplyRuntimeSignals", static)
        # Urban COM handover is confined to signal rows, which this alias forbids.
        self.assertIn('ElseIf kind = "signal" Then', source)

    @unittest.skipUnless(sys.platform == "win32", "VBScript readback mock uses Windows cscript")
    def test_native_ownership_readback_rejects_com_handover(self):
        source = integration_source("scripts/run_real_world_stackelberg_controller.vbs")
        native = re.search(r"(?m)^Sub ValidateDiagnosticProfileNativeSignals\(.*?^End Sub",
                           source, re.S | re.M).group(0)
        mock = '''
Dim controllerName, RW_SIGNAL_SCS, signalFailures, bad, fake
controllerName = "diagnostic-vsl-profile"
RW_SIGNAL_SCS = "1"
signalFailures = 0
bad = False
Class FakeSG
    Public owned
    Public Property Get AttValue(name)
        AttValue = owned
    End Property
End Class
Class FakeSC
    Public SGs
    Private Sub Class_Initialize()
        Dim a, b
        Set a = New FakeSG
        Set b = New FakeSG
        a.owned = False
        b.owned = bad
        SGs = Array(a, b)
    End Sub
End Class
Function CachedSignalController(scNo)
    Set CachedSignalController = New FakeSC
End Function
Function CachedSignalGroupCount(scNo, sc)
    CachedSignalGroupCount = 2
End Function
Function ComBoolean(value)
    ComBoolean = CBool(value)
End Function
ValidateDiagnosticProfileNativeSignals 1
If signalFailures <> 0 Then WScript.Quit 2
bad = True
ValidateDiagnosticProfileNativeSignals 900
If signalFailures <> 1 Then WScript.Quit 3
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "native_ownership_mock.vbs"
            path.write_text(native + "\n" + mock, encoding="utf-16")
            result = subprocess.run(["cscript.exe", "//nologo", str(path)],
                                    text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("sim_sec=1 checked=2 non_native=0 missing=0", result.stdout)
        self.assertIn("sim_sec=900 checked=2 non_native=1 missing=0", result.stdout)


def main_probe(cap, output, *, reject=False):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter

    def forbidden(*args, **kwargs):
        raise AssertionError("fixed profile entered a policy/optimization/write-back path")

    if reject:
        def invalid_profile(*args, **kwargs):
            raise ValueError("injected diagnostic profile failure")
        profile.build_control = invalid_profile

    for name in ("apply_vissim_policy_guards", "apply_actuation_guards_to_control",
                 "apply_post_guard_safety_evaluation", "real_world_ramp_meter_write_back",
                 "apply_ramp_spillback_guard", "build_priced_wu_link_controller"):
        setattr(adapter, name, forbidden)
    config = ROOT / f"diagnostics/vsl_profile_config_{cap}.json"
    tuning = adapter.load_optional_json(str(config))
    sys.argv = [adapter.__file__, "--state-json", str(RAW_STATE),
                "--out-action-json", str(Path(output) / "action.json"),
                "--out-action-csv", str(Path(output) / "action.csv"),
                "--mapping-json", str(ROOT / tuning["mapping_json"]),
                "--detector-mapping-json", str(ROOT / tuning["detector_mapping_json"]),
                "--calibration-json", str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"),
                "--controller", profile.CONTROLLER, "--tuning-json", str(config),
                "--diagnostic-allowed-vsl-speeds", "50,60,70,80,90,100,115,120"]
    adapter.main()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--probe", "--probe-reject"):
        main_probe(sys.argv[2], sys.argv[3], reject=sys.argv[1] == "--probe-reject")
    else:
        unittest.main()
