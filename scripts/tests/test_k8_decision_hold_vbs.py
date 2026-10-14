"""K8-8 runner band test (amendment 21 section 7.2, G-H4): the hold-on-exception path of the runner - cscript, no VISSIM.

The runner procedures are cut from the real runner text and loaded with ExecuteGlobal (no hand copies), as the S6
test does: RunControllerDecision in full, the capture/command helpers it calls, the four new K8-8 procedures, and the
summary lines.  Only the procedures that would touch VISSIM or the state writer are test doubles (WriteStateJson,
InitializeComRampMeterControl, ApplyActionCsv, PerfNow/PerfAdd, ElapsedSec = a fixed 1.25 s so whole log lines
compare byte for byte).  The adapter is a stdlib mock; the helper is a stdlib mock in (c)-(k), and the real
scripts/decision_hold.py (byte-identical copy beside the harness, as beside the runner) in (v).

  (a) off (env unset / strict), [success, success, exception]: output byte-identical to the 74cd495f procedures,
      Quit 3, no hold file or line                    (b) on + successes only: same bytes + the one start line
  (c) on + exception + .error.txt + helper success    (d) on + exit 1 without .error.txt -> strict, no helper
  (e) on + exit 2 / -1 (missing python) / exit 0 without CSV -> strict, no helper
  (f) helper exit 3 -> DECISION_HOLD_FAILED, DECISION_EXIT_NONZERO, EXPERIMENT_DECISION_FAILED, Quit 3
  (g) helper exit 0 without receipt -> as (f)          (h) lastActionJson "" (i) T = ControlStartSec (j) diagnostic-*
  (k) held CSV apply failure -> ACTION_CSV_INCOMPLETE  (l) ValidateDecisionErrorPolicy  (m) summary line
  (n) BuildHoldCommand vector  (s) failed hold keeps the decision's stderr; gate 5' (ControlStartSec = -1)
  (t) on + success with decisionsHeld undeclared under Option Explicit
  (p) WD Read-DecisionErrorPolicy cut out and run alone in PowerShell; (q) launch_plan.decision_error_policy;
      WD, LP and the helper agree on every tuning case
  (v) the real helper through BuildHoldCommand/RunDecisionCapture: HOLD_OK, held files, then (c)'s runner facts.
Never VISSIM: the harness creates only FileSystemObject/WScript.Shell and runs no runner top-level code.
Only the cscript/powershell processes this test starts (and their descendants) are ever stopped.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (HERE, ROOT, ROOT / 'scripts', ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from test_b1a_vbs_verified_capture_static import VBS_PATH, procedure  # noqa: E402

CSCRIPT = shutil.which('cscript.exe') or shutil.which('cscript')
POWERSHELL = shutil.which('powershell') or r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
VBS_REL = 'scripts/run_real_world_stackelberg_controller.vbs'
WD_PATH = ROOT / 'scripts' / 'run_real_world_single_watchdog_distributed_core17legs4b.ps1'
HELPER = ROOT / 'scripts' / 'decision_hold.py'
BASE_COMMIT = '74cd495f3b08312eb11384f4fcf06109a26c0cba'   # the parent of K8-8
SHARED = ('Q', 'OneLine', 'Pad6', 'EnvText', 'IsPythonPathCandidate', 'PythonCommandPrefix', 'RunCapture3',
          'BuildDecisionCommand', 'DecisionCapturePath', 'ReadDecisionCaptureText', 'RunDecisionCapture',
          'RunControllerDecision')
NEW = ('ValidateDecisionErrorPolicy', 'DecisionHoldOnException', 'BuildHoldCommand', 'RunDecisionHold')
SUMMARY_STARTS = ('WScript.Echo "DECISIONS_OK="', 'WScript.Echo "DECISIONS_FAILED="',
                  'If EnvText("RW_DECISION_ERROR_POLICY") = "hold_previous_on_exception" Then '
                  'WScript.Echo "DECISIONS_HELD_ON_EXCEPTION="')
RUN_ID = 'run-k88-vbs'
OBS_RUN_ID = 'obs-k88-vbs'
ON = 'hold_previous_on_exception'
WARN = '[경고] leader_hinge 성분은 merge {7,9,13,14} 기하에서 캘리브레이션됨 - 재검증 필요'
REPORT: dict = {}

MOCKS = r'''
Function ElapsedSec(t0)
    ElapsedSec = 1.25
End Function
Function PerfNow()
    PerfNow = 0
End Function
Sub PerfAdd(name, t0)
End Sub
Sub WriteStateJson(simSec, path, publish)
End Sub
Sub InitializeComRampMeterControl()
End Sub
Function ApplyActionCsv(simSec, csvPath, effectiveController)
    WScript.Echo "@@APPLY sim_sec=" & simSec & " csv=" & csvPath & " ctrl=" & effectiveController
    If applyFail.Exists(CStr(simSec)) Then
        ApplyActionCsv = False
    Else
        ApplyActionCsv = True
    End If
End Function
'''

HEADER = r'''Option Explicit
Dim fso, shell, procStream, procText
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
Dim decisionDir, obs150Mode, controllerName, controlStartSec, warmupControllerName, adapterMode
Dim pythonExe, adapterPath, mappingPath, detectorMappingPath, calibrationPath, tuningPath, RW_ALLOWED_VSL_SPEEDS
Dim lastActionJson, decisionsFailed, decisionsOk, controlInterval, RW_OFFSET_WRITER, Vissim
Dim stateFile, actionFile, bottleneckLinkFile, bottleneckSegmentFile, signalTraceFile, vslTraceFile, applyFail
@@HELD_DIM@@
Set applyFail = CreateObject("Scripting.Dictionary")
' ANSI read of the runner bytes: the decoding cscript applies to the runner file itself.
Set procStream = fso.OpenTextFile(@@PROCS@@, 1, False, 0)
procText = procStream.ReadAll
procStream.Close
ExecuteGlobal procText
WScript.Echo "@@LOADED"
decisionDir = @@DIR@@
obs150Mode = False
controllerName = @@CTRL@@
controlStartSec = @@CS@@
warmupControllerName = "no-control"
pythonExe = PythonCommandPrefix(@@PY@@)
adapterPath = @@ADAPTER@@
mappingPath = @@MAPPING@@
detectorMappingPath = ""
calibrationPath = ""
tuningPath = @@TUNING@@
RW_ALLOWED_VSL_SPEEDS = "60,80,100"
lastActionJson = @@LAST@@
decisionsFailed = 0
decisionsOk = 0
controlInterval = 150
RW_OFFSET_WRITER = "experiment"
@@HELD_INIT@@
Sub Report()
    WScript.Echo "@@STATE ok=" & decisionsOk & " failed=" & decisionsFailed & " last=" & lastActionJson
End Sub
'''

MOCK_ADAPTER = r'''import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
FIELDS = @@FIELDS@@
RUN_ID, OBS_RUN_ID, WARN = @@IDS@@
args = sys.argv[1:]
get = lambda k: args[args.index(k) + 1]
out_json = Path(get("--out-action-json"))
out_csv = Path(get("--out-action-csv"))
T = int(out_json.stem.split("_")[1])
mode = json.loads((HERE / "mock_plan.json").read_text(encoding="utf-8"))[str(T)]
with open(HERE / "argv_log.jsonl", "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"T": T, "mode": mode, "args": args}, ensure_ascii=False) + "\n")
obs = out_json.parent / "obs150"
obs.mkdir(exist_ok=True)
(obs / ("derived_%06d.json" % T)).write_text(json.dumps({"schema": "obs150-derived/v1", "sim_sec": T,
    "run_id": OBS_RUN_ID, "window": {"start_s": T - 150, "end_s": T}}), encoding="utf-8")
err = sys.stderr.buffer
err.write((WARN + "\n").encode("utf-8"))


def action(active):
    return {"N_P_star": 600.0 + T, "N_UF_star": 12.5, "ramp_metering": {"RM_C10480": 1512.0},
            "vsl": {"FW_W__seg0": 110.0}, "green_times": {"SC5": {"SC5_p1": 30.0}}, "offsets": {"SC5": 0.0},
            "inflow_outflow_allocation": {}, "diagnostics": {"sdmpc_prediction_sequence": [1, 2], "keep": 1},
            "metadata": {"sim_sec": float(T), "controller": get("--controller"), "controller_status": "ok",
                         "sdmpc_active": active, "run_provenance": {"run_id": RUN_ID}, "far_rate_est_10491": 900.0,
                         "sdmpc_state": {"schema": "x"}},
            "prediction": {"wall_sec": 1.0}, "run_provenance": {"run_id": RUN_ID}}


def write_ok(active, csv=True):
    out_json.write_text(json.dumps(action(active), indent=2), encoding="utf-8")
    if csv:
        rows = [",".join(FIELDS), "vsl,RW_FW_W_S0,1,,26,1,110.0,,,,,,,,ok",
                "ramp_meter,RM_C10480,,,,,,,,,,,%d,4,ok" % (1000 + T)]
        out_csv.write_bytes(("\r\n".join(rows) + "\r\n").encode("utf-8"))
    if active:
        Path(str(out_json) + ".sdmpc_pending").write_text("Native application required\n", encoding="utf-8")


def fail(with_report=True):
    error = out_json.with_suffix(".error.txt")
    root = "evaluation.controllers.control_area_objective.MembershipError: unresolved destination (None, None)"
    if with_report:
        error.write_text("Traceback (most recent call last):\n  File \"x.py\", line 1, in solve\n"
                         "RuntimeError: Tangent prediction failed:\n" + root + "\n", encoding="utf-8")
    err.write(("DECISION_FAILED type=RuntimeError message=Tangent prediction failed: root_error=%s traceback=%s\n"
               % (root, error)).encode("utf-8"))
    err.flush()
    sys.exit(1)


if mode in ("ok", "warm"):
    write_ok(mode == "ok")
    sys.stdout.write(json.dumps({"status": "ok", "decision_wall_sec": 1.0}) + "\n")
elif mode == "nocsv":
    write_ok(True, csv=False)
elif mode == "exc":
    fail()
elif mode == "exc_partial":
    write_ok(True)
    fail()
elif mode == "exc_noerr":
    fail(with_report=False)
elif mode == "exit2":
    err.write(b"usage error\n")
    sys.exit(2)
sys.stdout.flush()
err.flush()
sys.exit(0)
'''

MOCK_HELPER = r'''import json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
args = sys.argv[1:]
get = lambda k: args[args.index(k) + 1]
failed_json, failed_csv, prev = Path(get("--failed-action-json")), Path(get("--failed-action-csv")), Path(get("--previous-action-json"))
T = int(failed_json.stem.split("_")[1])
mode = json.loads((HERE / "mock_helper_plan.json").read_text(encoding="utf-8"))[str(T)]
with open(HERE / "helper_argv.jsonl", "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"T": T, "mode": mode, "args": args}, ensure_ascii=False) + "\n")
if mode == "refuse":
    sys.stderr.write("DECISION_HOLD_REFUSED reason=E9 detail=mock\n")
    sys.exit(3)
for name in (".json", ".csv", ".json.sdmpc_pending"):
    p = failed_json.with_name(failed_json.stem + name)
    if p.exists():
        p.rename(p.with_name(p.name + ".failed_decision"))
shutil.copyfile(prev, failed_json)
shutil.copyfile(prev.with_suffix(".csv"), failed_csv)
if mode == "ok":
    failed_json.with_name(failed_json.stem + ".hold.json").write_text("{}", encoding="utf-8")
sys.stdout.write("HOLD_OK sim_sec=%d mock=1\n" % T)
sys.exit(0)
'''


def vq(value) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_show(rel: str) -> str | None:
    try:
        done = subprocess.run(['git', '-C', str(ROOT), 'show', f'{BASE_COMMIT}:{rel}'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.decode('utf-8') if done.returncode == 0 else None


def summary_sub(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.startswith(SUMMARY_STARTS)]
    return 'Sub EmitSummary()\n' + '\n'.join('    ' + line for line in lines) + '\nEnd Sub\n'


def build_procs(text: str, new: bool) -> str:
    names = SHARED + (NEW if new else ())
    real = [procedure(text, name) for name in names]
    for piece in real:
        assert piece.encode('utf-8') in text.encode('utf-8')        # byte-exact cut
    return '\n'.join(real) + '\n' + summary_sub(text) + MOCKS


def kill_owned_tree(pid: int) -> str:
    done = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, timeout=60)
    return (done.stdout + done.stderr).decode('mbcs', errors='replace').strip()


class Run:
    def __init__(self, out, err, code, timed_out):
        self.out, self.err, self.code, self.timed_out = out, err, code, timed_out

    @property
    def lines(self) -> list[str]:
        return self.out.decode('mbcs', errors='replace').split('\r\n')

    def body(self) -> list[str]:
        lines = self.lines
        return lines[lines.index('@@LOADED') + 1:]

    def starting(self, prefix: str) -> list[str]:
        return [line for line in self.lines if line.startswith(prefix)]

    def text(self) -> str:
        return (self.out + b'\n' + self.err).decode('mbcs', errors='replace')[-4000:]


class Case:
    """One decision folder + runner folder with the mock adapter, the helper (mock or real) and the harness."""

    def __init__(self, base: Path, name: str, plan: dict, helper_plan: dict | None = None, real_helper=False,
                 policy_in_tuning=ON):
        self.root = base / f'k88 대역 {name}'
        if self.root.exists():
            shutil.rmtree(self.root)
        self.dir = self.root / '결정 폴더 k88'
        self.runner = self.root / '러너 폴더 k88'
        self.adapter_dir = self.root / '어댑터 폴더 k88'
        for d in (self.dir, self.runner, self.adapter_dir):
            d.mkdir(parents=True)
        self.adapter = self.adapter_dir / 'mock adapter k88.py'
        from evaluation.controllers import action_csv_schema
        self.adapter.write_text(MOCK_ADAPTER.replace('@@FIELDS@@', repr(tuple(action_csv_schema.ACTION_CSV_FIELDS)))
                                .replace('@@IDS@@', repr((RUN_ID, OBS_RUN_ID, WARN))), encoding='utf-8')
        (self.adapter_dir / 'mock_plan.json').write_text(json.dumps({str(k): v for k, v in plan.items()}),
                                                         encoding='utf-8')
        if real_helper:
            shutil.copyfile(HELPER, self.runner / 'decision_hold.py')
            assert sha((self.runner / 'decision_hold.py').read_bytes()) == sha(HELPER.read_bytes())
        else:
            (self.runner / 'decision_hold.py').write_text(MOCK_HELPER, encoding='utf-8')
            (self.runner / 'mock_helper_plan.json').write_text(
                json.dumps({str(k): v for k, v in (helper_plan or {}).items()}), encoding='utf-8')
        self.tuning = self.root / '튜닝 k88.json'
        tun = {'config_overrides': {}}
        if policy_in_tuning:
            tun['runtime'] = {'decision_error_policy': policy_in_tuning}
        self.tuning.write_text(json.dumps(tun), encoding='utf-8')
        for T in plan:
            state = {'sim_sec': float(T), 'control_interval_sec': 150.0, 'run_provenance': {'run_id': RUN_ID},
                     'obs150': {'directory': str(self.dir), 'run_id': OBS_RUN_ID}}
            (self.dir / f'state_{T:06d}.json').write_text(json.dumps(state), encoding='utf-8')

    def p(self, T, suffix):
        return self.dir / f'action_{T:06d}{suffix}'

    def run(self, procs: str, body: str, policy=None, held_declared=True, ctrl='wu-link', cs=900, last='',
            py=None, timeout=240.0) -> Run:
        procs_path = self.runner / ('procs_%s.vbs' % sha(procs.encode('utf-8'))[:12])
        procs_path.write_bytes(procs.encode('utf-8'))
        text = (HEADER.replace('@@PROCS@@', vq(procs_path)).replace('@@DIR@@', vq(self.dir))
                .replace('@@CTRL@@', vq(ctrl)).replace('@@CS@@', str(cs)).replace('@@PY@@', vq(py or sys.executable))
                .replace('@@ADAPTER@@', vq(self.adapter)).replace('@@MAPPING@@', vq(self.root / 'mapping.json'))
                .replace('@@TUNING@@', vq(self.tuning)).replace('@@LAST@@', vq(last))
                .replace('@@HELD_DIM@@', 'Dim decisionsHeld' if held_declared else '')
                .replace('@@HELD_INIT@@', 'decisionsHeld = 0' if held_declared else ''))
        harness = self.runner / 'harness.vbs'
        harness.write_text(text + body + '\nWScript.Echo "@@DONE"\n', encoding='utf-16')
        env = {k: v for k, v in os.environ.items() if not k.startswith('RW_')}
        env['PYTHONUTF8'] = '1'
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        if policy is not None:
            env['RW_DECISION_ERROR_POLICY'] = policy
        child = subprocess.Popen([CSCRIPT, '//nologo', str(harness)], cwd=str(self.root), env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            out, err = child.communicate(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            kill_owned_tree(child.pid)
            out, err = child.communicate()
            timed_out = True
        return Run(out, err, child.returncode, timed_out)

    def helper_calls(self) -> list[dict]:
        path = self.runner / 'helper_argv.jsonl'
        return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []

    def adapter_calls(self) -> list[dict]:
        path = self.adapter_dir / 'argv_log.jsonl'
        return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def decisions(*secs, report=True, summary=False, validate=False) -> str:
    lines = ['ValidateDecisionErrorPolicy'] if validate else []
    lines += [f'RunControllerDecision {T}' for T in secs]
    if report:
        lines.append('Report')
    if summary:
        lines.append('EmitSummary')
    return '\n'.join(lines) + '\n'


class Work:
    base: Path | None = None
    new_procs: str | None = None
    old_procs: str | None = None


def setUpModule():
    Work.base = Path(tempfile.mkdtemp(prefix='k88vbs_'))
    new_text = VBS_PATH.read_bytes().decode('utf-8')
    Work.new_procs = build_procs(new_text, new=True)
    old_text = git_show(VBS_REL)
    Work.old_procs = build_procs(old_text, new=False) if old_text is not None else None


def tearDownModule():
    if Work.base is not None:
        shutil.rmtree(Work.base, ignore_errors=True)


@unittest.skipUnless(CSCRIPT, 'Windows Script Host is required')
class RunnerBand(unittest.TestCase):
    def assertComplete(self, run: Run, code=0):
        self.assertFalse(run.timed_out, run.text())
        self.assertEqual(run.err, b'', run.text())
        self.assertEqual(run.code, code, run.text())
        if code == 0:
            self.assertIn('@@DONE', run.lines, run.text())

    def assertStrictStop(self, run: Run, case: Case, T: int, lead: str):
        self.assertComplete(run, 3)
        body = run.body()
        self.assertNotIn('@@DONE', run.lines)
        self.assertEqual([l for l in body if l.startswith('DECISION_HOLD') or l.startswith('DECISION_HELD')], [])
        self.assertTrue(any(l.startswith(lead + f' sim_sec={T}') for l in body), run.text())
        self.assertEqual(case.helper_calls(), [])
        self.assertEqual(sorted(p.name for p in case.dir.glob('*.hold*')), [])

    # ---------------------------------------------------------------- (a) (b) byte identity when nothing is held
    def test_a_off_output_byte_identical_to_parent(self):
        if Work.old_procs is None:
            self.skipTest('git history of 74cd495f is not available')
        plan = {3600: 'ok', 3750: 'ok', 3900: 'exc'}
        for policy in (None, 'strict'):
            with self.subTest(policy=policy):
                runs = {}
                for side, procs, validate in (('new', Work.new_procs, True), ('old', Work.old_procs, False)):
                    case = Case(Work.base, 'a', plan, helper_plan={3900: 'ok'})
                    runs[side] = case.run(procs, decisions(3600, 3750, 3900, validate=validate), policy=policy)
                    self.assertStrictStop(runs[side], case, 3900, 'ERROR=EXPERIMENT_DECISION_FAILED')
                    self.assertEqual(sorted(p.name for p in case.runner.glob('helper_argv.jsonl')), [])
                self.assertEqual(runs['new'].body(), runs['old'].body())
                self.assertEqual(runs['new'].out, runs['old'].out)
                REPORT[f'a_{policy}'] = {'lines': len(runs['new'].body())}

    def test_b_on_successes_only_add_the_start_line(self):
        if Work.old_procs is None:
            self.skipTest('git history of 74cd495f is not available')
        plan = {3600: 'ok', 3750: 'ok'}
        new_case = Case(Work.base, 'b', plan)
        new = new_case.run(Work.new_procs, decisions(3600, 3750, validate=True), policy=ON)
        self.assertComplete(new)
        old_case = Case(Work.base, 'b', plan)
        old = old_case.run(Work.old_procs, decisions(3600, 3750), policy=None)
        self.assertComplete(old)
        self.assertEqual(new.body()[0], 'DECISION_ERROR_POLICY=hold_previous_on_exception')
        self.assertEqual(new.body()[1:], old.body())
        self.assertIn('@@STATE ok=2 failed=0 last=' + str(new_case.p(3750, '.json')), new.lines)

    # ---------------------------------------------------------------- (c) hold with a mock helper
    def test_c_on_exception_held_and_next_decision_reads_the_held_command(self):
        case = Case(Work.base, 'c', {3600: 'ok', 3750: 'ok', 3900: 'exc', 4050: 'ok'}, helper_plan={3900: 'ok'})
        run = case.run(Work.new_procs, decisions(3600, 3750, 3900, 4050) + 'WScript.Echo "@@HELD n=" & decisionsHeld\n',
                       policy=ON)
        self.assertComplete(run)
        body = run.body()
        held_json, held_csv = case.p(3900, '.json'), case.p(3900, '.csv')
        self.assertEqual([l for l in body if l.startswith('ERROR=')], [])
        attempt = [l for l in body if l.startswith('DECISION_HOLD_ATTEMPT')]
        self.assertEqual(attempt, [f'DECISION_HOLD_ATTEMPT sim_sec=3900 source={case.p(3750, ".json")}'])
        self.assertEqual([l for l in body if l.startswith('DECISION_HELD_ON_EXCEPTION')],
                         ['DECISION_HELD_ON_EXCEPTION sim_sec=3900 HOLD_OK sim_sec=3900 mock=1'])
        order = [i for i, l in enumerate(body) if l.startswith(('CONTROLLER_DECISION sim_sec=3900', 'DECISION_HOLD_ATTEMPT',
                                                                 'DECISION_HELD_ON_EXCEPTION', '@@APPLY sim_sec=3900'))]
        self.assertEqual(order, sorted(order))
        self.assertEqual(len(order), 4)
        self.assertIn(f'@@APPLY sim_sec=3900 csv={held_csv} ctrl=wu-link', body)
        self.assertIn('@@STATE ok=3 failed=0 last=' + str(case.p(4050, '.json')), body)
        self.assertIn('@@HELD n=1', body)
        calls = case.adapter_calls()
        after = [c for c in calls if c['T'] == 4050][0]['args']
        self.assertEqual(after[after.index('--previous-action-json') + 1], str(held_json))
        helper = case.helper_calls()
        self.assertEqual(len(helper), 1)
        hargs = helper[0]['args']
        self.assertEqual(hargs[hargs.index('--previous-action-json') + 1], str(case.p(3750, '.json')))
        for name in ('action_003900.hold.stdout.txt', 'action_003900.hold.stderr.txt'):
            self.assertTrue((case.dir / name).is_file(), name)
        error = case.p(3900, '.error.txt')
        root = 'evaluation.controllers.control_area_objective.MembershipError: unresolved destination (None, None)'
        expected_err = (WARN + '\n').encode('utf-8') + (
            f'DECISION_FAILED type=RuntimeError message=Tangent prediction failed: root_error={root} traceback={error}\n'
        ).encode('utf-8')
        self.assertEqual(case.p(3900, '.stderr.txt').read_bytes(), expected_err)     # S6 capture untouched
        self.assertEqual(case.p(3900, '.stdout.txt').read_bytes(), b'')
        self.assertTrue(Path(str(case.p(3750, '.json')) + '.applied').is_file())
        self.assertFalse(Path(str(held_json) + '.applied').exists())
        self.assertTrue(Path(str(case.p(4050, '.json')) + '.applied').is_file())

    # ---------------------------------------------------------------- (d) (e) (h) (i) (j) (s-5') strict, no helper
    def test_d_exit1_without_error_report_is_strict(self):
        case = Case(Work.base, 'd', {3600: 'ok', 3750: 'ok', 3900: 'exc_noerr'}, helper_plan={3900: 'ok'})
        run = case.run(Work.new_procs, decisions(3600, 3750, 3900), policy=ON)
        self.assertStrictStop(run, case, 3900, 'ERROR=EXPERIMENT_DECISION_FAILED')
        self.assertTrue(run.starting('ERROR=DECISION_EXIT_NONZERO sim_sec=3900 exit=1 '))

    def test_e_other_failures_are_strict(self):
        for name, mode, lead, py in (('e2', 'exit2', 'ERROR=DECISION_EXIT_NONZERO', None),
                                     ('e0', 'nocsv', 'ERROR=ACTION_CSV_MISSING', None),
                                     ('em1', 'exc', 'ERROR=DECISION_EXIT_NONZERO', 'missing')):
            with self.subTest(name=name):
                case = Case(Work.base, name, {3600: 'ok', 3750: 'ok', 3900: mode}, helper_plan={3900: 'ok'})
                body = decisions(3600, 3750, report=False)
                if py == 'missing':
                    missing = case.root / '없는 파이썬' / 'python.exe'
                    body += f'pythonExe = PythonCommandPrefix({vq(missing)})\n'
                body += decisions(3900)
                run = case.run(Work.new_procs, body, policy=ON)
                self.assertStrictStop(run, case, 3900, lead)
                self.assertTrue(run.starting('ERROR=EXPERIMENT_DECISION_FAILED sim_sec=3900'))
                if py == 'missing':
                    self.assertTrue(run.starting('ERROR=DECISION_EXIT_NONZERO sim_sec=3900 exit=-1 stderr=EXEC_FAILED '))

    def test_h_i_j_gates_and_5prime(self):
        cases = (('h', {1050: 'exc'}, dict(last=''), 1050, 'ERROR=EXPERIMENT_DECISION_FAILED'),
                 ('i', {750: 'warm', 900: 'exc'}, dict(), 900, 'ERROR=EXPERIMENT_DECISION_FAILED'),
                 ('j', {3750: 'ok', 3900: 'exc'}, dict(ctrl='diagnostic-vsl-profile'), 3900,
                  'ERROR=DIAGNOSTIC_DECISION_FAILED'),
                 ('s5p', {3750: 'ok', 3900: 'exc'}, dict(cs=-1), 3900, 'ERROR=EXPERIMENT_DECISION_FAILED'))
        for name, plan, kwargs, T, lead in cases:
            with self.subTest(name=name):
                case = Case(Work.base, name, plan, helper_plan={T: 'ok'})
                run = case.run(Work.new_procs, decisions(*plan), policy=ON, **kwargs)
                self.assertStrictStop(run, case, T, lead)
                self.assertTrue(run.starting(f'ERROR=DECISION_EXIT_NONZERO sim_sec={T} exit=1 '))
                self.assertTrue(case.p(T, '.error.txt').is_file())

    # ---------------------------------------------------------------- (f) (g) (k) (s) failed holds
    def test_f_g_failed_hold_falls_into_the_strict_lines_with_the_decision_stderr(self):
        for name, helper_mode, hold_exit in (('f', 'refuse', 3), ('g', 'noreceipt', 0)):
            with self.subTest(name=name):
                case = Case(Work.base, name, {3600: 'ok', 3750: 'ok', 3900: 'exc'}, helper_plan={3900: helper_mode})
                run = case.run(Work.new_procs, decisions(3600, 3750, 3900), policy=ON)
                self.assertComplete(run, 3)
                body = run.body()
                tail = [l for l in body[[i for i, l in enumerate(body) if l.startswith('DECISION_HOLD_ATTEMPT')][0]:] if l]
                self.assertTrue(tail[1].startswith(f'ERROR=DECISION_HOLD_FAILED sim_sec=3900 hold_exit={hold_exit} stderr='),
                                tail)
                if helper_mode == 'refuse':
                    self.assertEqual(tail[1], 'ERROR=DECISION_HOLD_FAILED sim_sec=3900 hold_exit=3 stderr='
                                              'DECISION_HOLD_REFUSED reason=E9 detail=mock')
                # the decision's S6 stderr, last line = its DECISION_FAILED summary (the runner reads the UTF-8
                # capture as ANSI, so only the ASCII end of the folder path is compared)
                self.assertTrue(tail[2].endswith('\\action_003900.error.txt'), tail[2][-200:])
                self.assertIn(' traceback=', tail[2])
                self.assertTrue(tail[2].startswith('ERROR=DECISION_EXIT_NONZERO sim_sec=3900 exit=1 stderr='), tail)
                self.assertNotIn('DECISION_HOLD_REFUSED', tail[2])                     # (s) the decision's stderr
                self.assertIn('DECISION_FAILED type=RuntimeError', tail[2])
                self.assertTrue(tail[3].startswith('ERROR=EXPERIMENT_DECISION_FAILED sim_sec=3900'), tail)
                self.assertEqual(len(tail), 4)
                self.assertEqual(len(case.helper_calls()), 1)
                self.assertNotIn('DECISION_HELD_ON_EXCEPTION', '\n'.join(body))

    def test_k_held_csv_apply_failure_stops(self):
        case = Case(Work.base, 'k', {3600: 'ok', 3750: 'ok', 3900: 'exc'}, helper_plan={3900: 'ok'})
        run = case.run(Work.new_procs, 'applyFail.Add "3900", True\n' + decisions(3600, 3750, 3900), policy=ON)
        self.assertComplete(run, 3)
        body = run.body()
        self.assertTrue(run.starting('DECISION_HELD_ON_EXCEPTION sim_sec=3900 '))
        self.assertTrue(run.starting('ERROR=ACTION_CSV_INCOMPLETE sim_sec=3900 '))
        self.assertTrue(run.starting('ERROR=EXPERIMENT_DECISION_FAILED sim_sec=3900'))
        self.assertEqual(run.starting('ERROR=DECISION_EXIT_NONZERO'), [])
        self.assertLess(body.index([l for l in body if l.startswith('DECISION_HELD_ON_EXCEPTION')][0]),
                        body.index([l for l in body if l.startswith('ERROR=ACTION_CSV_INCOMPLETE')][0]))

    # ---------------------------------------------------------------- (l) (m) (n) (t)
    def test_l_validate_decision_error_policy(self):
        case = Case(Work.base, 'l', {3600: 'ok'})
        for policy, code, lines in ((None, 0, []), ('strict', 0, []), (ON, 0, ['DECISION_ERROR_POLICY=hold_previous_on_exception']),
                                    ('hold_previous', 2, ['ERROR=DECISION_ERROR_POLICY_INVALID value=hold_previous']),
                                    ('bogus', 2, ['ERROR=DECISION_ERROR_POLICY_INVALID value=bogus'])):
            with self.subTest(policy=policy):
                run = case.run(Work.new_procs, 'ValidateDecisionErrorPolicy\nWScript.Echo "@@AFTER"\n', policy=policy)
                self.assertFalse(run.timed_out)
                self.assertEqual(run.code, code, run.text())
                body = run.body()
                if code == 0:
                    self.assertEqual(body[:len(lines) + 1], lines + ['@@AFTER'])
                else:
                    self.assertEqual(body[:1], lines)
                    self.assertNotIn('@@AFTER', body)

    def test_m_summary_line_only_when_on(self):
        case = Case(Work.base, 'm', {3600: 'ok'})
        for policy, extra in ((None, []), ('strict', []), (ON, ['DECISIONS_HELD_ON_EXCEPTION=0'])):
            with self.subTest(policy=policy):
                run = case.run(Work.new_procs, 'EmitSummary\n', policy=policy)
                self.assertComplete(run)
                self.assertEqual(run.body()[:2 + len(extra)], ['DECISIONS_OK=0', 'DECISIONS_FAILED=0'] + extra)
                self.assertEqual(run.body()[2 + len(extra)], '@@DONE')

    def test_n_build_hold_command_vector(self):
        case = Case(Work.base, 'n', {3600: 'ok'})
        body = ('WScript.Echo "@@CMD " & BuildHoldCommand(PythonCommandPrefix("C:\\py 3\\python.exe"), '
                '"D:\\runner dir\\decision_hold.py", "D:\\d d\\state_003900.json", "D:\\d d\\action_003900.json", '
                '"D:\\d d\\action_003900.csv", "D:\\d d\\action_003750.json", '
                '"diagnostics\\sdmpc_n31_20260924\\config_n31_v2.json", 900)\n')
        run = case.run(Work.new_procs, body, policy=ON)
        self.assertComplete(run)
        expected = ('@@CMD "C:\\py 3\\python.exe" "D:\\runner dir\\decision_hold.py" --state-json "D:\\d d\\state_003900.json" '
                    '--failed-action-json "D:\\d d\\action_003900.json" --failed-action-csv "D:\\d d\\action_003900.csv" '
                    '--previous-action-json "D:\\d d\\action_003750.json" '
                    '--tuning-json "diagnostics\\sdmpc_n31_20260924\\config_n31_v2.json" --control-start-sec 900 '
                    '--decision-exit 1')
        self.assertEqual(run.body()[0], expected)
        REPORT['n'] = expected

    def test_t_success_without_global_decisions_held(self):
        case = Case(Work.base, 't', {3600: 'ok', 3750: 'ok'})
        run = case.run(Work.new_procs, decisions(3600, 3750), policy=ON, held_declared=False)
        self.assertComplete(run)
        self.assertIn('@@STATE ok=2 failed=0 last=' + str(case.p(3750, '.json')), run.body())

    # ---------------------------------------------------------------- (v) the real helper
    def test_v_real_helper_through_the_runner(self):
        case = Case(Work.base, 'v', {3600: 'ok', 3750: 'ok', 3900: 'exc', 4050: 'ok'}, real_helper=True)
        run = case.run(Work.new_procs, decisions(3600, 3750, 3900, 4050, validate=True) +
                       'WScript.Echo "@@HELD n=" & decisionsHeld\n', policy=ON, timeout=300)
        self.assertComplete(run)
        body = run.body()
        self.assertEqual(body[0], 'DECISION_ERROR_POLICY=hold_previous_on_exception')
        self.assertEqual([l for l in body if l.startswith('ERROR=')], [], run.text())
        held = [l for l in body if l.startswith('DECISION_HELD_ON_EXCEPTION')]
        self.assertEqual(len(held), 1)
        held_json, held_csv, receipt = case.p(3900, '.json'), case.p(3900, '.csv'), case.p(3900, '.hold.json')
        self.assertTrue(held[0].startswith('DECISION_HELD_ON_EXCEPTION sim_sec=3900 HOLD_OK sim_sec=3900 '
                                           'source_sim_sec=3750 origin_sim_sec=3750 chain=1 '), held[0])
        self.assertIn(f'csv_sha256={sha(held_csv.read_bytes())}', held[0])
        self.assertIn(f'json_sha256={sha(held_json.read_bytes())}', held[0])
        self.assertIn('type=RuntimeError root_type=MembershipError', held[0])
        self.assertEqual(held_csv.read_bytes(), case.p(3750, '.csv').read_bytes())
        doc = json.loads(held_json.read_text(encoding='utf-8'))
        self.assertEqual(doc['metadata']['controller_status'], ON)
        self.assertEqual(doc['metadata']['sim_sec'], 3900.0)
        self.assertTrue(receipt.is_file())
        self.assertEqual(json.loads(receipt.read_text(encoding='utf-8'))['source']['kind'], 'sdmpc')
        self.assertEqual((case.dir / 'action_003900.hold.stderr.txt').read_bytes(), b'')
        self.assertIn(b'HOLD_OK sim_sec=3900 ', (case.dir / 'action_003900.hold.stdout.txt').read_bytes())
        self.assertNotIn(b'DECISION_FAILED', (case.dir / 'action_003900.hold.stdout.txt').read_bytes())
        self.assertIn(f'@@APPLY sim_sec=3900 csv={held_csv} ctrl=wu-link', body)
        self.assertIn('@@STATE ok=3 failed=0 last=' + str(case.p(4050, '.json')), body)
        self.assertIn('@@HELD n=1', body)
        after = [c for c in case.adapter_calls() if c['T'] == 4050][0]['args']
        self.assertEqual(after[after.index('--previous-action-json') + 1], str(held_json))
        self.assertFalse(Path(str(held_json) + '.applied').exists())
        self.assertFalse((case.dir / 'action_003900.hold_error.txt').exists())
        self.assertEqual(sha((case.runner / 'decision_hold.py').read_bytes()), sha(HELPER.read_bytes()))
        REPORT['v'] = {'held_line': held[0][:200]}


# ---------------------------------------------------------------- (p) (q): WD, LP and the helper agree
POLICY_CASES = (
    ('none', [{}], 'strict'),
    ('strict', [{'runtime': {'decision_error_policy': 'strict'}}], 'strict'),
    ('on', [{'runtime': {'decision_error_policy': ON}}], ON),
    ('empty_runtime', [{'runtime': {}}], 'strict'),
    ('old_355_value', [{'runtime': {'decision_error_policy': 'hold_previous'}}], None),
    ('not_string', [{'runtime': {'decision_error_policy': 1}}], None),
    ('deadline_key', [{'runtime': {'decision_error_policy': ON, 'decision_timeout_sec': 1800}}], None),
    ('runtime_not_object', [{'runtime': ON}], None),
    ('extends_parent_on', [{'extends': 'p1.json'}, {'runtime': {'decision_error_policy': ON}}], ON),
    ('child_strict_over_parent_on', [{'extends': 'p1.json', 'runtime': {'decision_error_policy': 'strict'}},
                                     {'runtime': {'decision_error_policy': ON}}], 'strict'),
    ('parent_deadline_key', [{'extends': 'p1.json', 'runtime': {'decision_error_policy': ON}},
                             {'runtime': {'decision_timeout_sec': 30}}], None),
    ('parent_bad_value', [{'extends': 'p1.json', 'runtime': {'decision_error_policy': ON}},
                          {'runtime': {'decision_error_policy': 'hold_previous'}}], None),
    ('cycle', [{'extends': 'p1.json'}, {'extends': 'tuning.json'}], None),
    ('missing_parent', [{'extends': 'no_such.json'}], None),
)


def write_policy_case(folder: Path, docs: list) -> Path:
    folder.mkdir(parents=True)
    for i, doc in enumerate(docs):
        (folder / ('tuning.json' if i == 0 else f'p{i}.json')).write_text(json.dumps(doc), encoding='utf-8')
    return folder / 'tuning.json'


def wd_function_text() -> str:
    lines = WD_PATH.read_bytes().decode('utf-8-sig').splitlines()
    start = [i for i, l in enumerate(lines) if l.startswith('function Read-DecisionErrorPolicy(')]
    assert len(start) == 1, start
    end = next(i for i in range(start[0] + 1, len(lines)) if lines[i] == '}')
    return '\n'.join(lines[start[0]:end + 1]) + '\n'


class PolicyReaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='k88pol_'))
        cls.paths = {name: write_policy_case(cls.tmp / f'정책 {name}', docs) for name, docs, _ in POLICY_CASES}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_p_watchdog_function_alone(self):
        script = self.tmp / 'wd_policy_test.ps1'
        calls = '\n'.join(
            f"try {{ $r['{name}'] = 'value:' + (Read-DecisionErrorPolicy '{str(path)}') }} "
            f"catch {{ $r['{name}'] = 'throw' }}" for name, path in self.paths.items())
        script.write_text("$ErrorActionPreference = 'Stop'\n" + wd_function_text() + "$r = [ordered]@{}\n" + calls +
                          "\n$r | ConvertTo-Json -Compress\n", encoding='utf-8-sig')
        done = subprocess.run([POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                              capture_output=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr.decode('mbcs', 'replace'))
        got = json.loads(done.stdout.decode('utf-8', 'replace').strip().splitlines()[-1])
        for name, _, want in POLICY_CASES:
            self.assertEqual(got[name], 'throw' if want is None else 'value:' + want, name)
        REPORT['p'] = got

    def test_q_launch_plan_function(self):
        import launch_plan as lp
        from n31_common import ToolError
        for name, _, want in POLICY_CASES:
            with self.subTest(name=name):
                if want is None:
                    with self.assertRaises((ToolError, ValueError, OSError)):
                        lp.decision_error_policy(self.paths[name])
                else:
                    self.assertEqual(lp.decision_error_policy(self.paths[name]), want)
        source = (ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'tools' / 'launch_plan.py').read_text(encoding='utf-8')
        self.assertEqual(source.count("env['RW_DECISION_ERROR_POLICY'] = decision_error_policy(tuning_path)"), 1)

    def test_helper_reads_the_same_way(self):
        import decision_hold as dh
        for name, _, want in POLICY_CASES:
            with self.subTest(name=name):
                if want is None:
                    with self.assertRaises((ValueError, OSError)):
                        dh.read_policy_chain(self.paths[name])
                else:
                    self.assertEqual(dh.read_policy_chain(self.paths[name])[0], want)


if __name__ == '__main__':
    unittest.main()
