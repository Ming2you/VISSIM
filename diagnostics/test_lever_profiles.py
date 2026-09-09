"""Exercise pending four-lever integration only in memory; no live COM changes."""
from __future__ import annotations
import ast
import copy
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from diagnostics import test_diagnostic_profile as base_tests
from evaluation.controllers import diagnostic_signal_profile


def pending_source(relative):
    source = (ROOT / relative).read_text(encoding="utf-8")
    patch = (ROOT / "diagnostics/diagnostic_lever_profiles.patch").read_text(encoding="utf-8")
    portion = patch.split("--- a/" + relative + "\n", 1)[1].split("--- a/", 1)[0]
    for hunk in re.split(r"^@@[^\n]*\n", portion, flags=re.M)[1:]:
        old = "".join(s[1:] for s in hunk.splitlines(True) if s.startswith((" ", "-")))
        new = "".join(s[1:] for s in hunk.splitlines(True) if s.startswith((" ", "+")))
        if old in source:
            source = source.replace(old, new, 1)
        elif new not in source:
            raise AssertionError(f"pending lever patch drifted: {relative}")
    return source


def pending_profile():
    module = types.ModuleType("pending_diagnostic_profile")
    exec(compile(pending_source("evaluation/controllers/diagnostic_profile.py"), "pending_profile", "exec"), module.__dict__)
    return module


def probe(name, output):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    profile = pending_profile()
    adapter.diagnostic_profile = profile
    adapter.diagnostic_signal_profile = diagnostic_signal_profile
    diagnostic_signal_profile.diagnostic_profile = profile
    source = pending_source("evaluation/controllers/vissim_stackelberg_adapter.py")
    body = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
            and node.name in {"main", "real_world_ramp_meter_actions"}]
    exec(compile(ast.Module(body=body, type_ignores=[]), adapter.__file__, "exec"), adapter.__dict__)

    def forbidden(*a, **kw):
        raise AssertionError("fixed authority arm entered policy, optimizer, measured cache or write-back")

    for function in ("apply_vissim_policy_guards", "apply_actuation_guards_to_control", "apply_post_guard_safety_evaluation",
                     "real_world_ramp_meter_write_back", "apply_ramp_spillback_guard", "build_priced_wu_link_controller"):
        setattr(adapter, function, forbidden)
    # Normal VSL/signal all-open allocation may call the helper, which returns
    # None for proportional mode. Explicit physical overrides must bypass it.
    if name.startswith("ramp_"):
        adapter._measured_meter_allocation = forbidden
    cases = {
        "vsl80": ("vsl_profile_config_80.json", profile.CONTROLLER),
        "ramp_open": ("ramp_profile_config_open.json", profile.RAMP_CONTROLLER),
        "ramp_g5": ("ramp_profile_config_c10639_g5.json", profile.RAMP_CONTROLLER),
        "signal_zero": ("signal_profile_config_zero.json", diagnostic_signal_profile.CONTROLLER),
        "signal_green10": ("signal_profile_config_sc1004_green10.json", diagnostic_signal_profile.CONTROLLER),
        "signal_offset10": ("signal_profile_config_plus10.json", diagnostic_signal_profile.CONTROLLER),
    }
    config_name, controller = cases[name]
    config = ROOT / "diagnostics" / config_name
    tuning = adapter.load_optional_json(str(config))
    sys.argv = [adapter.__file__, "--state-json", str(base_tests.RAW_STATE),
                "--out-action-json", str(Path(output) / "action.json"), "--out-action-csv", str(Path(output) / "action.csv"),
                "--mapping-json", str(ROOT / tuning["mapping_json"]),
                "--detector-mapping-json", str(ROOT / tuning["detector_mapping_json"]),
                "--calibration-json", str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"),
                "--controller", controller, "--tuning-json", str(config),
                "--diagnostic-allowed-vsl-speeds", "50,60,70,80,90,100,115,120"]
    adapter.main()


class LeverProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_tests.ProfileTests.setUpClass()
        cls.base = base_tests.ProfileTests
        cls.profile = pending_profile()

    def test_physical_override_contract_and_static_mode_validation(self):
        tuning = {"diagnostic": {"vsl_profile": {}, "physical_meter_green_sec": {"RM_C10639": 5}}}
        action = self.profile.build_control(self.base.cfg, self.base.ControlAction, tuning, self.base.mapping, self.base.allowed)
        settings = self.profile.fixed_actuation(self.base.tuning["actuation"], tuning)
        rows = self.profile.physical_meter_actions(action, self.base.cfg, settings, self.base.mapping)
        self.assertEqual(rows["RM_C10639"]["green_sec"], 5)
        self.assertEqual(rows["RM_C10639"]["rate_vph"], 450)
        self.assertEqual([rows[mid]["green_sec"] for mid in ("RM_C10644", "RM_C10646")], [10, 10])
        self.assertEqual(sum(r["green_sec"] == 10 for r in rows.values()), 7)
        self.assertIn("not measured throughput", action.diagnostics["diagnostic_meter_rate_semantics"])
        with self.assertRaisesRegex(ValueError, "nonconstant physical meters"):
            self.profile.validate_controller(self.profile.CONTROLLER, tuning)
        self.profile.validate_controller(self.profile.RAMP_CONTROLLER, tuning)
        for changes in ({"R_F_E": 5}, {"RM_C10639": 5.5}, {"RM_C10639": True}, {"RM_C10639": -1}, {"RM_C10639": float("nan")}):
            bad = copy.deepcopy(tuning)
            bad["diagnostic"]["physical_meter_green_sec"] = changes
            with self.assertRaises(ValueError):
                self.profile.build_control(self.base.cfg, self.base.ControlAction, bad, self.base.mapping, self.base.allowed)

    def test_green_changes_reject_cycle_drift_dead_phase_or_clamping(self):
        tuning = self.base.adapter.load_optional_json(str(ROOT / "diagnostics/signal_profile_config_zero.json"))
        plan = self.base.adapter.load_signal_group_actuation_plan()
        for delta in ({"SC1004_p3": 10}, {"SC1004_p1": -20, "SC1004_p3": 20}, {"SC109_p1": 10, "SC109_p2": -10}):
            bad = copy.deepcopy(tuning)
            bad["diagnostic"]["signal_profile"]["green_delta_sec"] = delta
            with self.assertRaises(ValueError):
                diagnostic_signal_profile.build_control(self.base.cfg, self.base.ControlAction, bad, plan, ROOT)

    def test_actual_main_pipeline_isolates_all_four_levers(self):
        cases = {}
        for name in ("vsl80", "ramp_open", "ramp_g5", "signal_zero", "signal_green10", "signal_offset10"):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                result = subprocess.run([sys.executable, __file__, "--probe", name, tmp], cwd=ROOT,
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=55)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                action = json.loads((Path(tmp) / "action.json").read_text(encoding="utf-8"))
                self.assertEqual(action["metadata"]["controller_status"], "ok")
                with (Path(tmp) / "action.csv").open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
                for row in rows:
                    row.pop("metadata")  # Runtime timing/audit metadata is not a plant command.
                cases[name] = (action, rows)
        open_rows, metered_rows = cases["ramp_open"][1], cases["ramp_g5"][1]
        self.assertEqual({r["kind"] for r in open_rows}, {"vsl", "ramp_meter"})
        differences = [(a, b) for a, b in zip(open_rows, metered_rows) if a != b]
        self.assertEqual(len(differences), 1)
        a, b = differences[0]
        self.assertEqual(b["id"], "RM_C10639")
        self.assertEqual({k for k in a if a[k] != b[k]}, {"rate_vph", "green_sec"})
        self.assertEqual(float(b["green_sec"]), 5)
        self.assertEqual(float(b["rate_vph"]), 450)
        for row in metered_rows:
            if row["kind"] == "ramp_meter" and row["id"] != "RM_C10639":
                self.assertEqual(float(row["green_sec"]), 10)
        zero, green, shifted = (cases[name][1] for name in ("signal_zero", "signal_green10", "signal_offset10"))
        self.assertEqual(len(zero), len(green))
        changed = 0
        for a, b in zip(zero, green):
            if a != b:
                changed += 1
                self.assertEqual(a["sc_no"], "1004")
                allowed = {"p1_green", "p3_green"} if a["kind"] == "signal" else {"p1_green", "p2_green"}
                self.assertTrue({k for k in a if a[k] != b[k]} <= allowed)
        self.assertGreater(changed, 1)
        action = cases["signal_green10"][0]
        self.assertEqual(action["green_times"]["SC1004_p1"], 10)
        self.assertAlmostEqual(action["green_times"]["SC1004_p3"], 78.06376811594205)
        for a, b in zip(zero, shifted):
            self.assertTrue({k for k in a if a[k] != b[k]} <= {"offset"})
        vsl_rows = cases["vsl80"][1]
        self.assertEqual(len(vsl_rows), len(open_rows))
        self.assertTrue(all({k for k in a if a[k] != b[k]} <= {"speed_kph"} for a, b in zip(open_rows, vsl_rows)))

    @unittest.skipUnless(sys.platform == "win32", "requires Windows cscript for the offline scheduler mock")
    def test_ramp_event_scheduler_writes_every_transition_and_checks_held_state(self):
        source = pending_source("scripts/run_real_world_stackelberg_controller.vbs")
        names = ("UseContinuousStaticMode", "UseEventContinuousMode", "UseSingleDecisionEventMode",
                 "RunEventContinuousMode", "MinEventTarget", "NextControlAfter", "NextLogAfter",
                 "NextRampTransitionAfter", "RampCompositeStateAt", "RampStateAt",
                 "ApplyRuntimeRampMeters", "ApplyRampMeterSignal", "SignalRowsSuppressedForController")
        extracted = [re.search(rf"(?m)^(?:Sub|Function) {name}\([^\n]*\).*?^End (?:Sub|Function)",
                               source, re.S | re.M).group(0) for name in names]
        native = re.search(r"(?m)^Sub ValidateDiagnosticProfileNativeSignals\(.*?^End Sub", source, re.S | re.M).group(0)
        self.assertIn('"diagnostic-ramp-profile"', native)
        mock = '''
Const RAMP_CYCLE_SEC = 10
Const RAMP_AMBER_SEC = 1
Dim controllerName, controlStartSec, simPeriod, stateLogIntervalSec, controlInterval
Dim Vissim, rampGreen, held, RW_RAMP_METER_SCS, signalTraceSimSec, sigPhaseGreen
controllerName = "diagnostic-ramp-profile"
controlStartSec = 900
simPeriod = 920
stateLogIntervalSec = 30
controlInterval = 150
RW_RAMP_METER_SCS = "9101,9102,9103,9104,9105,9106,9107,9108"
Set rampGreen = CreateObject("Scripting.Dictionary")
Set held = CreateObject("Scripting.Dictionary")
Set sigPhaseGreen = CreateObject("Scripting.Dictionary")
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
    Dim sc
    For Each sc In Split(RW_RAMP_METER_SCS, ",")
        rampGreen(sc) = 10
    Next
End Sub
Sub RunControllerDecision(sec)
    WScript.Echo "DECISION=" & sec
    If sec >= controlStartSec Then rampGreen("9105") = 5
End Sub
Sub ApplyRuntimeSignals(sec)
    If sigPhaseGreen.Count <> 0 Then WScript.Quit 8
End Sub
Sub ApplyIncidentLaneClosure(sec)
End Sub
Sub LogStateCsv(sec)
End Sub
Function NextSignalTransitionAfter(sec)
    NextSignalTransitionAfter = simPeriod
End Function
Function NextIncidentTransitionAfter(sec)
    NextIncidentTransitionAfter = simPeriod
End Function
Sub RunContinuousTo(sec)
End Sub
Function DictValue(d, key, fallback)
    If d.Exists(key) Then
        DictValue = d(key)
    Else
        DictValue = fallback
    End If
End Function
Function FMod(value, divisor)
    FMod = value - Int(value / divisor) * divisor
End Function
Function PerfNow()
    PerfNow = 0
End Function
Sub PerfAdd(name, elapsed)
End Sub
Function SetSignalGroupState(sc, sg, state)
    held(CStr(sc)) = state
    If signalTraceSimSec >= 900 Then WScript.Echo "WRITE=" & signalTraceSimSec & "," & sc & "," & state
    SetSignalGroupState = True
End Function
Sub ValidateRuntimeSignalPersistence(sec)
    If sec >= 900 Then WScript.Echo "POST=" & sec & ",9105," & held("9105")
End Sub
Sub ValidateDiagnosticProfileNativeSignals(sec)
    WScript.Echo "NATIVE=" & sec
End Sub
If UseContinuousStaticMode() Then WScript.Quit 2
If Not UseEventContinuousMode() Then WScript.Quit 3
If Not SignalRowsSuppressedForController(controllerName) Then WScript.Quit 4
RunEventContinuousMode
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ramp_event_mock.vbs"
            path.write_text("\n".join(extracted) + "\n" + mock, encoding="utf-16")
            result = subprocess.run(["cscript.exe", "//nologo", str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual([line for line in lines if line.startswith("DECISION=")], ["DECISION=1", "DECISION=900"])
        self.assertEqual([line for line in lines if line.startswith("NATIVE=")], ["NATIVE=1", "NATIVE=900", "NATIVE=920"])
        writes = [line for line in lines if line.startswith("WRITE=") and ",9105," in line]
        self.assertEqual(writes, [f"WRITE={sec},9105,{state}" for sec, state in
                                 ((900, "GREEN"), (905, "AMBER"), (906, "RED"), (910, "GREEN"),
                                  (915, "AMBER"), (916, "RED"), (920, "GREEN"))])
        for line in lines:
            if line.startswith("WRITE=") and ",9105," not in line:
                self.assertTrue(line.endswith(",GREEN"))
        for sec, state in ((905, "GREEN"), (906, "AMBER"), (910, "RED")):
            self.assertIn(f"POST={sec},9105,{state}", lines)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--probe":
        probe(sys.argv[2], sys.argv[3])
    else:
        unittest.main()
