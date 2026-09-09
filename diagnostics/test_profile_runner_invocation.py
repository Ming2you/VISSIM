"""Real VBS command -> real adapter -> CSV contract -> writers, with fake COM.

Only observation capture and VISSIM objects/time are replaced. This test does
not establish physical authority; a subsequent live COM readback is required.
"""
from __future__ import annotations
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_real_world_stackelberg_controller.vbs"
CONFIG = ROOT / "evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs"
RAW = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry/state_000900.json"


def q(value):
    return '"' + str(value).replace('"', '""') + '"'


FAKE_COM = r'''
Class FakeAttributes
    Private values
    Private Sub Class_Initialize()
        Set values = CreateObject("Scripting.Dictionary")
        values("ContrByCOM") = False
        values("SigState") = "GREEN"
    End Sub
    Public Property Let AttValue(key, value)
        values(CStr(key)) = value
    End Property
    Public Property Get AttValue(key)
        If values.Exists(CStr(key)) Then AttValue = values(CStr(key))
    End Property
End Class
Class FakeCollection
    Private objects
    Private Sub Class_Initialize()
        Set objects = CreateObject("Scripting.Dictionary")
    End Sub
    Public Property Get Count()
        Count = 8
    End Property
    Public Function ItemByKey(key)
        If Not objects.Exists(CStr(key)) Then objects.Add CStr(key), New FakeAttributes
        Set ItemByKey = objects(CStr(key))
    End Function
End Class
Class FakeController
    Public SGs
    Private Sub Class_Initialize()
        Set SGs = New FakeCollection
    End Sub
End Class
Class FakeControllers
    Private objects
    Private Sub Class_Initialize()
        Set objects = CreateObject("Scripting.Dictionary")
    End Sub
    Public Function ItemByKey(key)
        If Not objects.Exists(CStr(key)) Then objects.Add CStr(key), New FakeController
        Set ItemByKey = objects(CStr(key))
    End Function
End Class
Class FakeNet
    Public SignalControllers, DesSpeedDecisions
    Private Sub Class_Initialize()
        Set SignalControllers = New FakeControllers
        Set DesSpeedDecisions = New FakeCollection
    End Sub
End Class
Class FakeSimulation
    Sub RunSingleStep()
    End Sub
    Sub [Stop]()
        WScript.Echo "FAKE_SIM_STOP"
    End Sub
End Class
Class FakeVissim
    Public Net, Simulation
    Private Sub Class_Initialize()
        Set Net = New FakeNet
        Set Simulation = New FakeSimulation
    End Sub
    Sub ResumeUpdateGUI(value)
    End Sub
End Class
Sub WriteStateJson(sec, destination, resetWindow)
    fso.CopyFile fixtureState, destination, True
End Sub
Sub RunContinuousTo(sec)
    WScript.Echo "FAKE_ADVANCE=" & sec
End Sub
Sub LogStateCsv(sec)
End Sub
Sub ApplyIncidentLaneClosure(sec)
End Sub
Sub ValidateDiagnosticProfileNativeSignals(sec)
    ' Native programs cannot be tested without VISSIM. Ownership is checked
    ' separately by asserting no urban entries were handed to the COM writer.
End Sub
'''


def build_harness(tmp, controller, config_name, *, failure=None):
    source = RUNNER.read_text(encoding="utf-8")
    replacements = {"WriteStateJson", "RunContinuousTo", "LogStateCsv",
                    "ApplyIncidentLaneClosure", "ValidateDiagnosticProfileNativeSignals"}
    functions = []
    for match in re.finditer(r"(?m)^(?:Sub|Function) (\w+)[^\n]*\n.*?^End (?:Sub|Function)", source, re.S):
        if match[1] in replacements:
            continue
        body = match[0]
        if match[1] == "RunCapture3":
            # Observe, without replacing, the actual shell.Exec invocation.
            body = body.replace('    Set exec = shell.Exec(cmd)',
                                '    WScript.Echo "CAPTURE_CMD=" & cmd\n    Set exec = shell.Exec(cmd)')
        functions.append(body)
    declarations = re.findall(r"(?m)^(?:Dim|Const) [^\n]+", source)
    dictionaries = re.findall(r'(?m)^Set (\w+) = CreateObject\("Scripting.Dictionary"\)', source)
    tuning_path = ROOT / "diagnostics" / config_name
    sys.path.insert(0, str(ROOT))
    from evaluation.controllers.vissim_stackelberg_adapter import load_optional_json
    tuning = load_optional_json(str(tuning_path))
    if failure == "nonzero":
        tuning["diagnostic"]["vsl_profile"] = {"FW_E__seg0": 65}
        tuning_path = tmp / "invalid_profile.json"
        tuning_path.write_text(json.dumps(tuning), encoding="utf-8")
    adapter = ROOT / "evaluation/controllers/vissim_stackelberg_adapter.py"
    if failure in {"missing", "incomplete"}:
        # A child process returns success with missing/malformed output: the
        # runner's independent output-contract failure branches must also stop.
        adapter = tmp / "invalid_child.py"
        adapter.write_text("import pathlib, sys\n" + (
            "pathlib.Path(sys.argv[sys.argv.index('--out-action-csv')+1]).write_text('invalid\\n')\n"
            if failure == "incomplete" else ""), encoding="utf-8")
    init = ["Dim fixtureState", 'Set fso = CreateObject("Scripting.FileSystemObject")',
            'Set shell = CreateObject("WScript.Shell")']
    init += [f'Set {name} = CreateObject("Scripting.Dictionary")' for name in dictionaries]
    values = {"fixtureState": RAW, "decisionDir": tmp, "pythonExe": '"' + sys.executable + '"',
              "adapterPath": adapter, "tuningPath": tuning_path,
              "mappingPath": ROOT / tuning["mapping_json"],
              "detectorMappingPath": ROOT / tuning["detector_mapping_json"],
              "calibrationPath": ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json",
              "controllerName": controller, "warmupControllerName": "no-control",
              "lastActionJson": "", "signalTraceStage": "immediate", "RW_OFFSET_WRITER": "test_only"}
    init += [f"{key} = {q(value)}" for key, value in values.items()]
    init += ['controlStartSec = 900', 'simPeriod = 910', 'controlInterval = 150',
             'stateLogIntervalSec = 30', 'incidentEnabled = False', 'decisionsOk = 0', 'decisionsFailed = 0',
             'Set Vissim = New FakeVissim']
    for key in ("stateFile", "actionFile", "bottleneckLinkFile", "bottleneckSegmentFile", "signalTraceFile"):
        init.append(f'Set {key} = fso.CreateTextFile({q(tmp / (key + ".csv"))}, True)')
    init.append('signalTraceFile.WriteLine "sim_sec,sc,sg,requested,readback,ok,stage"')
    init += [CONFIG.read_text(encoding="utf-8-sig"),
             CONFIG.with_name(CONFIG.stem + "_sgplan.vbs").read_text(encoding="utf-8-sig"),
             'ParseSignalGroupPlanConfig']
    if failure:
        # Includes a warmup-controller failure while the selected run is a
        # diagnostic: classification must depend on controllerName.
        init += ['RunControllerDecision ' + ('1' if failure == "missing" else '900'),
                 'WScript.Echo "UNEXPECTED_CONTINUATION"']
    else:
        init += ['If UseContinuousStaticMode() Then', '    RunContinuousStaticMode',
                 'Else', '    RunEventContinuousMode', 'End If',
                 'WScript.Echo "COUNTS=" & decisionsOk & "," & decisionsFailed & "," & sigPhaseGreen.Count',
                 'WScript.Echo "LAST_ACTION=" & lastActionJson']
    init += [f'{name}.Close' for name in ("stateFile", "actionFile", "bottleneckLinkFile", "bottleneckSegmentFile", "signalTraceFile")]
    path = tmp / "invocation.vbs"
    path.write_text("\n".join(declarations + functions) + "\n" + FAKE_COM + "\n" + "\n".join(init), encoding="utf-16")
    return path


@unittest.skipUnless(sys.platform == "win32", "Windows cscript required; no live VISSIM is used")
class ProfileRunnerInvocationTests(unittest.TestCase):
    def invoke(self, tmp, controller, config, failure=None):
        path = build_harness(tmp, controller, config, failure=failure)
        env = dict(os.environ, RW_MAINLINE_SG_ONLY="1", RW_SIGNAL_READBACK_SEC="1",
                   RW_SIGNAL_WRITE_ON_CHANGE="0", RW_FORCE_STEPWISE="0")
        return subprocess.run(["cscript.exe", "//nologo", str(path)], cwd=ROOT, env=env,
                              capture_output=True, text=True, errors="replace", timeout=90)

    def test_real_command_adapter_csv_and_first_events(self):
        cases = [("diagnostic-vsl-profile", "vsl_profile_config_80.json", 0),
                 ("diagnostic-ramp-profile", "ramp_profile_config_c10639_g5.json", 0),
                 ("diagnostic-signal-profile", "signal_profile_config_sc1004_green10.json", 17)]
        for controller, config, signals in cases:
            with self.subTest(controller=controller), tempfile.TemporaryDirectory() as directory:
                tmp = Path(directory)
                result = self.invoke(tmp, controller, config)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"COUNTS=2,0,{signals}", result.stdout)
                self.assertNotIn("ERROR=", result.stdout)
                commands = [x for x in result.stdout.splitlines() if x.startswith("CAPTURE_CMD=")]
                self.assertEqual(len(commands), 2)
                self.assertNotIn("--diagnostic-allowed-vsl-speeds", commands[0])
                self.assertIn('--diagnostic-allowed-vsl-speeds "50,60,70,80,90,100,115,120"', commands[1])
                action = json.loads((tmp / "action_000900.json").read_text(encoding="utf-8"))
                self.assertEqual(action["metadata"]["controller_status"], "ok")
                with (tmp / "signalTraceFile.csv").open(newline="") as stream:
                    trace = list(csv.DictReader(stream))
                self.assertTrue(all(x["ok"] == "1" and x["requested"] == x["readback"] for x in trace))
                if not signals:
                    self.assertTrue(all(int(x["sc"]) >= 9101 for x in trace))
                else:
                    self.assertTrue(any(x["sc"] == "1004" and x["stage"] == "immediate" for x in trace))
                    self.assertEqual(action["green_times"]["SC1004_p1"], 10)
                if controller == "diagnostic-ramp-profile":
                    for sec, requested in ((900, "GREEN"), (905, "AMBER"), (906, "RED"), (910, "GREEN")):
                        self.assertTrue(any(x["sim_sec"] == str(sec) and x["sc"] == "9105"
                                            and x["stage"] == "immediate" and x["requested"] == requested for x in trace))
                    for sec, requested in ((905, "GREEN"), (906, "AMBER"), (910, "RED")):
                        self.assertTrue(any(x["sim_sec"] == str(sec) and x["sc"] == "9105"
                                            and x["stage"] == "post_step" and x["requested"] == requested for x in trace))

    def test_diagnostic_decision_failures_stop_before_continuation(self):
        for failure in ("nonzero", "missing", "incomplete"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                result = self.invoke(Path(directory), "diagnostic-ramp-profile",
                                     "ramp_profile_config_c10639_g5.json", failure)
                self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
                self.assertIn("ERROR=DIAGNOSTIC_DECISION_FAILED", result.stdout)
                self.assertIn("FAKE_SIM_STOP", result.stdout)
                self.assertNotIn("UNEXPECTED_CONTINUATION", result.stdout)

    def test_non_diagnostic_failure_keeps_existing_final_integrity_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.invoke(Path(directory), "no-control",
                                 "ramp_profile_config_c10639_g5.json", "missing")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ERROR=ACTION_CSV_MISSING", result.stdout)
            self.assertIn("UNEXPECTED_CONTINUATION", result.stdout)
            self.assertNotIn("FAKE_SIM_STOP", result.stdout)


if __name__ == "__main__":
    unittest.main()
