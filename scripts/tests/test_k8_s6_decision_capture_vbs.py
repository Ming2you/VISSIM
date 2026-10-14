"""K8-1 (S6): the runner's decision call captures the adapter output to files - cscript mock, no VISSIM.

Declared by the K8 pre-declaration (K8_PREDECLARATION.md section 2 K8-1, AMENDMENT_1 r2 section 2
K8-1 (N3), AMENDMENT_2 section 1, which replaces item (v)). The procedures under test, and the
statements of RunControllerDecision that build the command, call the adapter and write the log
lines, are cut from the real runner text and loaded with ExecuteGlobal (no hand copies). The inline
command assembly and the call line it replaced come from the parent commit BASE_COMMIT (git).
The "python" child is a stdlib mock adapter run with PYTHONUTF8=1, as run_sdmpc_n31.ps1:208 does.

  (i)   64 KB stdout + 64 KB stderr: the new call ends within 60 s, exit codes 0 and 3 stay, and the
        CONTROLLER_DECISION line is OneLine(capture file contents)
  (ii)  683 B normal output (277 B stdout + 406 B stderr, Korean warning lines): the log lines of the
        old RunCapture3 (pipe) and of the new call are byte-identical
  (iii) spaces and Korean in the adapter and decision folder paths, python in the quoted
        PythonCommandPrefix form; the child gets the same argv through both calls
  (iv)  the capture files stay in the decision folder; an empty stderr raises nothing
  (v)   a missing quoted python path: (v-0) premise, (v-1) result, (v-2) the two log lines, (v-3) no files
  BuildDecisionCommand: the runner's new statements give the old inline assembly's string (case grid)
Report only (the outcome is not asserted): (v') the unquoted launcher form; with K8_S6_REPORT_OLD64K=1,
whether the old RunCapture3 finishes the 64 KB mock within 60 s (only the owned PID tree is killed).
K8_S6_KEEP_DIR=<dir outside the repo> keeps the work tree and writes k81_mock_report.json there.
Never VISSIM: the harness creates only FileSystemObject/WScript.Shell and runs no runner top-level code.
"""
from __future__ import annotations

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
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from test_b1a_vbs_verified_capture_static import VBS_PATH, procedure  # noqa: E402

CSCRIPT = shutil.which("cscript.exe") or shutil.which("cscript")
VBS_REL = "scripts/run_real_world_stackelberg_controller.vbs"
BASE_COMMIT = "acf057591f70219c8135fe0014170d5315f27a81"  # K8-0, the parent of K8-1
SIM_SEC = 2700
WALL_SEC = "12.34"  # one fixed wall_sec, so whole log lines compare byte for byte
NEW_PROCEDURES = ("BuildDecisionCommand", "DecisionCapturePath", "ReadDecisionCaptureText", "RunDecisionCapture")
LOADED_PROCEDURES = ("Q", "OneLine", "Pad6", "EnvText", "IsPythonPathCandidate", "PythonCommandPrefix",
                     "RunCapture3") + NEW_PROCEDURES + ("RunControllerDecision",)
# The adapter's three warning lines of a normal SDMPC-31 decision (K8 scratch full_hook 2700 adapter
# log): 406 B with CRLF, the stderr size DEFECTS.md section 6 measured on GB-9.
WARN_LINES = (
    "[경고] leader_hinge 성분은 merge {7,9,13,14} 기하에서 캘리브레이션됨 - 현재 {8,10,12,18,21,22,23}, 재검증 필요",
    "[경고] np_deadband 성분은 merge {7,9,13,14} 기하에서 캘리브레이션됨 - 현재 {8,10,12,18,21,22,23}, 재검증 필요",
    "[경고] leader_mfd_far 성분은 merge {7,9,13,14} 기하에서 캘리브레이션됨 - 현재 {8,10,12,18,21,22,23}, 재검증 필요",
)
REPORT: dict = {}


def _stdout_277_line() -> str:
    """The adapter's status line in its real form, padded so that line + CRLF is exactly 277 B."""
    for wall in (569.014124, 569.01412):
        for pad in range(0, 120):
            run = "decisions_k8s6_" + "x" * pad
            line = json.dumps({"status": "ok",
                               "out_action_json": f"D:\\VISSIM_runs\\{run}\\action_002700.json",
                               "out_action_csv": f"D:\\VISSIM_runs\\{run}\\action_002700.csv",
                               "decision_wall_sec": wall})
            if len(line.encode("utf-8")) + 2 == 277:
                return line
    raise AssertionError("no 277 B status line")


STDOUT_LINE = _stdout_277_line()

MOCK_SOURCE = r'''import json, os, sys
from pathlib import Path
STDOUT_LINE = @@STDOUT@@
WARN_LINES = @@WARN@@
args = sys.argv[1:]
ctrl = args[args.index("--controller") + 1]
_, kind, code = ctrl.split("-")
record = {"ctrl": ctrl, "argv0": sys.argv[0], "args": args, "utf8_mode": sys.flags.utf8_mode,
          "cwd": os.getcwd(), "env_keys": sorted(os.environ)}
with open(Path(__file__).with_name("argv_log.jsonl"), "a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def payload(tag, fill):
    return b"".join(b"K8S6-%s-%04d-" % (tag, i) + fill * 48 + b"\r\n" for i in range(1024))


if kind == "64k":
    sys.stdout.buffer.write(payload(b"OUT", b"o"))
    sys.stdout.flush()
    sys.stderr.buffer.write(payload(b"ERR", b"e"))
    sys.stderr.flush()
elif kind in ("683", "emptyerr"):
    sys.stdout.write(STDOUT_LINE + "\n")
    if kind == "683":
        for line in WARN_LINES:
            sys.stderr.write(line + "\n")
sys.stdout.flush()
sys.stderr.flush()
sys.exit(int(code))
'''


def _payload(tag: bytes, fill: bytes) -> bytes:
    return b"".join(b"K8S6-%s-%04d-" % (tag, i) + fill * 48 + b"\r\n" for i in range(1024))


def _oneline(text: str) -> str:
    return text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip(" ")


def vq(value) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _git_base_source() -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_COMMIT}:{VBS_REL}"],
                              capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.decode("utf-8") if done.returncode == 0 else None


def _lines_from(proc: str, first: str, last: str) -> str:
    """The physical lines of proc from the one starting with `first` through the one containing `last`."""
    lines = proc.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith(first)]
    ends = [i for i, line in enumerate(lines) if last in line]
    if len(starts) != 1 or len(ends) != 1 or starts[0] > ends[0]:
        raise AssertionError(f"slice {first!r}..{last!r}: starts={starts} ends={ends}")
    return "".join(lines[starts[0]: ends[0] + 1])


def _one_line(proc: str, start: str) -> str:
    found = [line for line in proc.splitlines(keepends=True) if line.lstrip(" ").startswith(start)]
    if len(found) != 1:
        raise AssertionError(f"expected one line starting {start!r}, found {len(found)}")
    return found[0]


def _echo_expression(line: str) -> str:
    text = line.strip()
    if not text.startswith("WScript.Echo "):
        raise AssertionError(line)
    return text[len("WScript.Echo "):]


def build_procs(new_text: str, old_text: str) -> tuple[str, dict]:
    """ExecuteGlobal text: real procedures + wrappers around real RunControllerDecision statements."""
    new_bytes = new_text.encode("utf-8")
    old_bytes = old_text.encode("utf-8")
    real = [procedure(new_text, name) for name in LOADED_PROCEDURES]
    for piece in real:
        assert piece.encode("utf-8") in new_bytes  # byte-exact cut
    new_decision = procedure(new_text, "RunControllerDecision")
    old_decision = procedure(old_text, "RunControllerDecision")
    old_assembly = _lines_from(old_decision, '    cmd = pythonExe & " " & Q(adapterPath)',
                               'If adapterMode <> "" Then cmd = cmd & " --mode " & Q(adapterMode)')
    old_call = _one_line(old_decision, "exitCode = RunCapture3(cmd, outText, errText)")
    new_prep = _lines_from(new_decision, '    adapterMode = EnvText("RW_ADAPTER_MODE")',
                           'captureErrPath = DecisionCapturePath(')
    new_call = _one_line(new_decision, "exitCode = RunDecisionCapture(")
    result_line = _one_line(new_decision, 'result = "exit=" & exitCode')
    decision_echo = _echo_expression(_one_line(new_decision, 'WScript.Echo "CONTROLLER_DECISION sim_sec="'))
    error_echo = _echo_expression(_one_line(new_decision, 'WScript.Echo "ERROR=DECISION_EXIT_NONZERO sim_sec="'))
    for piece in (old_assembly, old_call):
        assert piece.encode("utf-8") in old_bytes
    for piece in (new_prep, new_call, result_line):
        assert piece.encode("utf-8") in new_bytes
    wrappers = f'''
Function OldDecisionCommand()
    Dim cmd
{old_assembly.rstrip()}
    OldDecisionCommand = cmd
End Function

Function OldDecisionCall(cmd, ByRef outText, ByRef errText)
    Dim exitCode
{old_call.rstrip()}
    OldDecisionCall = exitCode
End Function

Sub RunnerDecisionPrep(simSec, ByRef cmdOut, ByRef outP, ByRef errP)
    Dim cmd, captureOutPath, captureErrPath
{new_prep.rstrip()}
    cmdOut = cmd
    outP = captureOutPath
    errP = captureErrPath
End Sub

Function RunnerDecisionCall(cmd, captureOutPath, captureErrPath, ByRef outText, ByRef errText)
    Dim exitCode
{new_call.rstrip()}
    RunnerDecisionCall = exitCode
End Function

Sub EmitDecisionLog(simSec, wallSec, exitCode, outText, errText)
    Dim result
{result_line.rstrip()}
    lastResult = result
    lastDecisionLine = {decision_echo}
    WScript.Echo lastDecisionLine
    lastErrorLine = ""
    If exitCode <> 0 Then
        lastErrorLine = {error_echo}
        WScript.Echo lastErrorLine
    End If
End Sub
'''
    parts = {"old_assembly": old_assembly, "old_call": old_call, "new_prep": new_prep, "new_call": new_call,
             "result_line": result_line, "decision_echo": decision_echo, "error_echo": error_echo}
    return "\n".join(real) + wrappers, parts


HEADER = r'''Option Explicit
Dim fso, shell, procStream, procText, sideStream
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
Dim pythonExe, adapterPath, stateJsonPath, outJsonPath, outCsvPath, mappingPath, effController
Dim detectorMappingPath, calibrationPath, tuningPath, RW_ALLOWED_VSL_SPEEDS, lastActionJson, adapterMode
Dim decisionDir, lastResult, lastDecisionLine, lastErrorLine
Dim cmd, outP, errP, code1, code2, o1, o2, e1, e2, r1, l1, x1, t0, el, oldCmd, newCmd
Set sideStream = fso.CreateTextFile(@@SIDE@@, True, True)
' ANSI read of the runner bytes: the decoding cscript applies to the runner file itself.
Set procStream = fso.OpenTextFile(@@PROCS@@, 1, False, 0)
procText = procStream.ReadAll
procStream.Close
ExecuteGlobal procText
WScript.Echo "@@LOADED"

Function B(x)
    If x Then
        B = "1"
    Else
        B = "0"
    End If
End Function

Sub Side(key, value)
    sideStream.WriteLine key & "=" & Replace(Replace(CStr(value), vbCr, "\r"), vbLf, "\n")
End Sub

Sub SetMode(value)
    Dim env
    Set env = shell.Environment("PROCESS")
    If value = "" Then
        On Error Resume Next
        env.Remove "RW_ADAPTER_MODE"
        Err.Clear
        On Error GoTo 0
    Else
        env("RW_ADAPTER_MODE") = value
    End If
End Sub

Sub SetCase(py, adapter, folder, ctrl)
    pythonExe = PythonCommandPrefix(py)
    adapterPath = adapter
    decisionDir = folder
    stateJsonPath = fso.BuildPath(folder, "state_002700.json")
    outJsonPath = fso.BuildPath(folder, "action_002700.json")
    outCsvPath = fso.BuildPath(folder, "action_002700.csv")
    mappingPath = fso.BuildPath(@@CONFIG@@, "mapping 한글.json")
    detectorMappingPath = fso.BuildPath(@@CONFIG@@, "detector mapping 검지.json")
    calibrationPath = fso.BuildPath(@@CONFIG@@, "calibration 보정.json")
    tuningPath = fso.BuildPath(@@CONFIG@@, "config_n31_v2 튜닝.json")
    RW_ALLOWED_VSL_SPEEDS = ""
    lastActionJson = fso.BuildPath(folder, "action_002550.json")
    effController = ctrl
    SetMode ""
End Sub
'''


class Work:
    root: Path | None = None
    keep: Path | None = None
    parts: dict | None = None


def _expected_args(folder: Path, ctrl: str) -> list[str]:
    config = Work.root / "설정 폴더 k8"
    return ["--state-json", str(folder / "state_002700.json"),
            "--out-action-json", str(folder / "action_002700.json"),
            "--out-action-csv", str(folder / "action_002700.csv"),
            "--mapping-json", str(config / "mapping 한글.json"),
            "--controller", ctrl,
            "--detector-mapping-json", str(config / "detector mapping 검지.json"),
            "--calibration-json", str(config / "calibration 보정.json"),
            "--tuning-json", str(config / "config_n31_v2 튜닝.json"),
            "--previous-action-json", str(folder / "action_002550.json")]


def _adapter() -> Path:
    return Work.root / "어댑터 폴더 k8" / "mock adapter k8.py"


def _folder(item: str) -> Path:
    folder = Work.root / f"결정 폴더 {item}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _kill_owned_tree(pid: int) -> str:
    # Only the cscript process this test started and its descendants; never by image name.
    done = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=60)
    return (done.stdout + done.stderr).decode("mbcs", errors="replace").strip()


class Run:
    def __init__(self, name, out, err, code, wall, timed_out, killed, side):
        self.name, self.out, self.err, self.code = name, out, err, code
        self.wall, self.timed_out, self.killed, self.side = wall, timed_out, killed, side

    def lines(self) -> list[bytes]:
        return self.out.split(b"\r\n")

    def block(self, name: str) -> list[bytes]:
        lines = self.lines()
        begin, end = lines.index(b"@@B " + name.encode()), lines.index(b"@@E " + name.encode())
        return lines[begin + 1:end]

    def info(self, tag: str) -> dict[str, str]:
        found = [line for line in self.lines() if line.startswith(b"@@" + tag.encode() + b" ")]
        if len(found) != 1:
            raise AssertionError(f"{self.name}: @@{tag} lines {len(found)}\n{self.text()}")
        pairs = found[0].decode("ascii").split(" ")[1:]
        return dict(pair.split("=", 1) for pair in pairs)

    def text(self) -> str:
        return (self.out + b"\n" + self.err).decode("mbcs", errors="replace")[-4000:]

    def complete(self) -> bool:
        return (not self.timed_out and self.code == 0 and self.err == b"" and b"@@LOADED" in self.lines()
                and b"@@DONE" in self.lines())


def run_harness(name: str, body: str, timeout: float = 120.0) -> Run:
    harness = Work.root / f"harness_{name}.vbs"
    side = Work.root / f"side_{name}.txt"
    text = (HEADER.replace("@@SIDE@@", vq(side)).replace("@@PROCS@@", vq(Work.root / "procs_runner.vbs"))
            .replace("@@CONFIG@@", vq(Work.root / "설정 폴더 k8")))
    harness.write_text(text + body + '\nsideStream.Close\nWScript.Echo "@@DONE"\n', encoding="utf-16")
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env.pop("RW_ADAPTER_MODE", None)
    started = time.perf_counter()
    child = subprocess.Popen([CSCRIPT, "//nologo", str(harness)], cwd=str(Work.root), env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    killed = ""
    try:
        out, err = child.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        killed = _kill_owned_tree(child.pid)
        out, err = child.communicate()
        timed_out = True
    wall = time.perf_counter() - started
    values = {}
    if side.exists():
        for line in side.read_text(encoding="utf-16").splitlines():
            key, _, value = line.partition("=")
            values[key] = value
    return Run(name, out, err, child.returncode, wall, timed_out, killed, values)


def _argv_records(ctrl: str) -> list[dict]:
    path = _adapter().with_name("argv_log.jsonl")
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [row for row in rows if row["ctrl"] == ctrl]


def _call_body(folder: Path, ctrl: str, py: str | None = None, old: bool = False, new: bool = True,
               pre: tuple[str, ...] = ()) -> str:
    lines = [f"SetCase {vq(py or sys.executable)}, {vq(_adapter())}, {vq(folder)}, {vq(ctrl)}",
             f"RunnerDecisionPrep {SIM_SEC}, cmd, outP, errP",
             'Side "cmd", cmd', 'Side "outP", outP', 'Side "errP", errP', 'Side "pythonExe", pythonExe', *pre]
    if old:
        lines += ["t0 = Timer", "code1 = OldDecisionCall(cmd, o1, e1)", "el = Timer - t0",
                  "If el < 0 Then el = el + 86400",
                  'WScript.Echo "@@OLD code=" & code1 & " elapsed_ms=" & CLng(el * 1000) & " outlen=" & Len(o1) & '
                  '" errlen=" & Len(e1) & " out_exists=" & B(fso.FileExists(outP)) & " err_exists=" & B(fso.FileExists(errP))',
                  'WScript.Echo "@@B old"', f"EmitDecisionLog {SIM_SEC}, {WALL_SEC}, code1, o1, e1", 'WScript.Echo "@@E old"',
                  "r1 = lastResult", "l1 = lastDecisionLine", "x1 = lastErrorLine", 'Side "e1", e1']
    if new:
        lines += ["t0 = Timer", "code2 = RunnerDecisionCall(cmd, outP, errP, o2, e2)", "el = Timer - t0",
                  "If el < 0 Then el = el + 86400",
                  'WScript.Echo "@@NEW code=" & code2 & " elapsed_ms=" & CLng(el * 1000) & " outlen=" & Len(o2) & '
                  '" errlen=" & Len(e2) & " out_exists=" & B(fso.FileExists(outP)) & " err_exists=" & B(fso.FileExists(errP))',
                  'WScript.Echo "@@B new"', f"EmitDecisionLog {SIM_SEC}, {WALL_SEC}, code2, o2, e2", 'WScript.Echo "@@E new"',
                  'Side "e2", e2']
    if old and new:
        lines += ['WScript.Echo "@@CMP code=" & B(code1 = code2) & " out=" & B(o1 = o2) & " err=" & B(e1 = e2) & '
                  '" result=" & B(r1 = lastResult) & " line=" & B(l1 = lastDecisionLine) & " errline=" & B(x1 = lastErrorLine)']
    return "\n".join(lines) + "\n"


def setUpModule():
    keep = os.environ.get("K8_S6_KEEP_DIR", "").strip()
    if keep:
        base = Path(keep).resolve()
        if base == ROOT or ROOT in base.parents:
            raise AssertionError("K8_S6_KEEP_DIR must be outside the repository")
        run_dir = base / time.strftime("run_%Y%m%dT%H%M%S")
        Work.keep = run_dir
    else:
        run_dir = Path(tempfile.mkdtemp(prefix="k8s6_"))
    Work.root = run_dir / "k8 s6 모의 루트"
    (Work.root / "설정 폴더 k8").mkdir(parents=True)
    _adapter().parent.mkdir(parents=True)
    _adapter().write_text(MOCK_SOURCE.replace("@@STDOUT@@", repr(STDOUT_LINE)).replace("@@WARN@@", repr(WARN_LINES)),
                          encoding="utf-8")
    new_text = VBS_PATH.read_bytes().decode("utf-8")
    old_text = _git_base_source()
    Work.parts = None
    if old_text is not None:
        procs, Work.parts = build_procs(new_text, old_text)
        (Work.root / "procs_runner.vbs").write_bytes(procs.encode("utf-8"))
    REPORT.update({"root": str(Work.root), "python": sys.executable, "vbs_sha256": _sha(VBS_PATH.read_bytes()),
                   "base_commit": BASE_COMMIT, "stdout_277_line": STDOUT_LINE})


def tearDownModule():
    if Work.keep is not None:
        (Work.keep / "k81_mock_report.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=1),
                                                        encoding="utf-8")
    elif Work.root is not None:
        shutil.rmtree(Work.root.parent, ignore_errors=True)


def _sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


class StaticDecisionCallTests(unittest.TestCase):
    """Text-only checks (no cscript): scope of the change in the runner."""

    def setUp(self):
        self.source = VBS_PATH.read_bytes().decode("utf-8")
        self.base = _git_base_source()

    def test_old_pipe_functions_are_byte_identical_to_the_parent(self):
        if self.base is None:
            self.skipTest("git history of the parent commit is not available")
        for name in ("RunCapture3", "RunCapture3Timeout", "Q", "OneLine", "PythonCommandPrefix", "IsPythonPathCandidate"):
            self.assertEqual(procedure(self.source, name), procedure(self.base, name), name)
        REPORT["static_old_functions_identical"] = True

    def test_only_the_decision_call_moves_to_the_file_capture(self):
        decision = procedure(self.source, "RunControllerDecision")
        self.assertEqual(decision.count("RunDecisionCapture("), 1)
        self.assertNotIn("RunCapture3(", decision)
        self.assertEqual(decision.count("BuildDecisionCommand("), 1)
        callers = {}
        for name in ("AddPythonWhereCandidates", "AdapterImportProbe", "ResolvePythonInterpreter",
                     "RunDecisionCapture", "RunControllerDecision"):
            callers[name] = procedure(self.source, name).count("RunCapture3(")
        self.assertEqual(callers, {"AddPythonWhereCandidates": 1, "AdapterImportProbe": 1,
                                   "ResolvePythonInterpreter": 1, "RunDecisionCapture": 1,
                                   "RunControllerDecision": 0})
        code = [line for line in self.source.splitlines() if not line.lstrip().startswith("'")]
        self.assertEqual(sum(line.count("RunCapture3(") for line in code), 5)  # 4 calls + declaration
        self.assertEqual(sum(line.count("RunDecisionCapture(") for line in code), 3)  # 2 calls + declaration (K8-8 hold)
        for name in NEW_PROCEDURES:
            procedure(self.source, name)  # exactly one declaration
        REPORT["static_call_sites"] = callers

    def test_capture_has_no_timeout_and_reads_ansi(self):
        body = procedure(self.source, "RunDecisionCapture")
        code = "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("'"))
        for word in ("Timer", "Terminate", "timeout", "TerminateExecTree"):
            self.assertNotIn(word.lower(), code.lower(), word)
        self.assertIn('"cmd /d /s /c """ & cmd & " 1> " & Q(outPath) & " 2> " & Q(errPath) & """"', code)
        self.assertIn("Do While exec.Status = 0", code)
        reader = procedure(self.source, "ReadDecisionCaptureText")
        self.assertIn("fso.OpenTextFile(path, 1, False, 0)", reader)
        self.assertIn("size > 0", reader)


@unittest.skipUnless(CSCRIPT, "Windows Script Host is required")
class MockAdapterDecisionCaptureTests(unittest.TestCase):
    """cscript + mock adapter. The declared items (i)-(v) and the BuildDecisionCommand identity."""

    def setUp(self):
        if Work.parts is None:
            self.skipTest("git history of the parent commit is not available")

    def test_0_runner_procedures_load_with_execute_global(self):
        run = run_harness("load", "")
        self.assertTrue(run.complete(), run.text())
        REPORT["load"] = {"complete": True, "procedures": list(LOADED_PROCEDURES)}

    def test_1_build_decision_command_equals_inline_assembly(self):
        folder = _folder("bdc")
        cases = [
            ("deploy", r"C:\Users\TRLAB\anaconda3\python.exe", r"D:\VISSIM-merge\FRZ\x\vissim_stackelberg_adapter.py",
             r"D:\VISSIM_runs\x\decisions_sdmpc31", "sdmpc-n31", []),
            ("optional_blank", sys.executable, str(_adapter()), str(folder), "sdmpc-n31",
             ['detectorMappingPath = ""', 'calibrationPath = ""', 'tuningPath = ""', 'lastActionJson = ""']),
            ("optional_empty", sys.executable, str(_adapter()), str(folder), "sdmpc-n31",
             ["detectorMappingPath = Empty", "calibrationPath = Empty", "tuningPath = Empty",
              "lastActionJson = Empty", "RW_ALLOWED_VSL_SPEEDS = Empty"]),
            ("diag_vsl", sys.executable, str(_adapter()), str(folder), "diagnostic-vsl-profile",
             ['RW_ALLOWED_VSL_SPEEDS = "60,80,100"']),
            ("diag_ramp_mixed_case", sys.executable, str(_adapter()), str(folder), "Diagnostic-Ramp-Profile",
             ['RW_ALLOWED_VSL_SPEEDS = "60,80,100"']),
            ("diag_rule", sys.executable, str(_adapter()), str(folder), "diagnostic-rule-profile",
             ['RW_ALLOWED_VSL_SPEEDS = "80"']),
            ("diag_signal_blank_speeds", sys.executable, str(_adapter()), str(folder), "diagnostic-signal-profile", []),
            ("diag_other_not_listed", sys.executable, str(_adapter()), str(folder), "diagnostic-other-profile",
             ['RW_ALLOWED_VSL_SPEEDS = "60"']),
            ("mode", sys.executable, str(_adapter()), str(folder), "sdmpc-n31", ['SetMode "fuller-smoke"']),
            ("mode_padded", sys.executable, str(_adapter()), str(folder), "sdmpc-n31", ['SetMode "  fast-smoke  "']),
            ("launcher_unquoted", "py -3", str(_adapter()), str(folder), "sdmpc-n31", []),
            ("korean_space_paths", sys.executable, str(_adapter()), str(folder), "k8mock-683-0", []),
        ]
        body = []
        for name, py, adapter, case_folder, ctrl, extra in cases:
            body += [f"SetCase {vq(py)}, {vq(adapter)}, {vq(case_folder)}, {vq(ctrl)}", *extra,
                     "oldCmd = OldDecisionCommand()", f"RunnerDecisionPrep {SIM_SEC}, newCmd, outP, errP",
                     f'Side "{name}.old", oldCmd', f'Side "{name}.new", newCmd',
                     f'WScript.Echo "@@BDC_{name} eq=" & B(oldCmd = newCmd) & " len=" & Len(newCmd)']
        run = run_harness("bdc", "\n".join(body) + "\n")
        self.assertTrue(run.complete(), run.text())
        result = {}
        for name, *_ in cases:
            info = run.info(f"BDC_{name}")
            old, new = run.side[f"{name}.old"], run.side[f"{name}.new"]
            result[name] = {"eq_vbs": info["eq"], "eq_py": old == new, "len": int(info["len"])}
            self.assertEqual(info["eq"], "1", name)
            self.assertEqual(old, new, name)
        side = run.side
        self.assertIn(" --previous-action-json ", side["deploy.new"])
        self.assertNotIn(" --previous-action-json ", side["optional_blank.new"])
        self.assertNotIn(" --detector-mapping-json ", side["optional_empty.new"])
        for name in ("diag_vsl", "diag_ramp_mixed_case", "diag_rule", "diag_signal_blank_speeds"):
            self.assertIn(" --diagnostic-allowed-vsl-speeds ", side[f"{name}.new"], name)
        self.assertNotIn(" --diagnostic-allowed-vsl-speeds ", side["diag_other_not_listed.new"])
        self.assertTrue(side["mode.new"].endswith(' --mode "fuller-smoke"'))
        self.assertTrue(side["mode_padded.new"].endswith(' --mode "fast-smoke"'))
        self.assertTrue(side["launcher_unquoted.new"].startswith('py -3 "'))
        self.assertTrue(side["deploy.new"].startswith('"C:\\Users\\TRLAB\\anaconda3\\python.exe" "'))
        REPORT["bdc"] = result

    def _item_i(self, code: int):
        folder = _folder(f"i 64k exit{code}")
        ctrl = f"k8mock-64k-{code}"
        run = run_harness(f"i_{code}", _call_body(folder, ctrl), timeout=120)
        record = {"cscript_wall_sec": round(run.wall, 3), "timed_out": run.timed_out}
        REPORT[f"i_exit{code}"] = record
        self.assertTrue(run.complete(), run.text())
        info = run.info("NEW")
        out_path, err_path = folder / "action_002700.stdout.txt", folder / "action_002700.stderr.txt"
        out_b, err_b = out_path.read_bytes(), err_path.read_bytes()
        expected_line = (f"CONTROLLER_DECISION sim_sec={SIM_SEC} wall_sec={WALL_SEC} result=exit={code} "
                         f"stdout={_oneline(out_b.decode('ascii'))} stderr={_oneline(err_b.decode('ascii'))}").encode("ascii")
        block = run.block("new")
        record.update({"exit": int(info["code"]), "elapsed_ms": int(info["elapsed_ms"]), "stdout_B": len(out_b),
                       "stderr_B": len(err_b), "payload_match": out_b == _payload(b"OUT", b"o") and err_b == _payload(b"ERR", b"e"),
                       "line_B": len(block[0]), "line_equals_oneline_files": block[0] == expected_line,
                       "error_line": block[1].decode("ascii")[:80] if len(block) > 1 else ""})
        self.assertEqual(len(out_b), 65536)
        self.assertEqual(len(err_b), 65536)
        self.assertTrue(record["payload_match"])
        self.assertEqual(int(info["code"]), code)
        self.assertLess(int(info["elapsed_ms"]), 60000)
        self.assertLess(run.wall, 60.0)
        self.assertEqual(block[0], expected_line)
        if code:
            self.assertEqual(block[1], f"ERROR=DECISION_EXIT_NONZERO sim_sec={SIM_SEC} exit={code} stderr="
                                       f"{_oneline(err_b.decode('ascii'))}".encode("ascii"))
            self.assertEqual(len(block), 2)
        else:
            self.assertEqual(len(block), 1)
        self.assertEqual(Path(run.side["outP"]), out_path)
        self.assertEqual(Path(run.side["errP"]), err_path)

    def test_2_item_i_64kb_exit0(self):
        self._item_i(0)

    def test_3_item_i_64kb_exit3(self):
        self._item_i(3)

    def test_4_items_ii_iii_683b_log_line_byte_identical(self):
        folder = _folder("ii 683B 정상")
        ctrl = "k8mock-683-0"
        before = len(_argv_records(ctrl))
        run = run_harness("ii", _call_body(folder, ctrl, old=True), timeout=120)
        record = {"cscript_wall_sec": round(run.wall, 3)}
        REPORT["ii_iii"] = record
        self.assertTrue(run.complete(), run.text())
        old_info, new_info, cmp_info = run.info("OLD"), run.info("NEW"), run.info("CMP")
        out_path, err_path = folder / "action_002700.stdout.txt", folder / "action_002700.stderr.txt"
        out_b, err_b = out_path.read_bytes(), err_path.read_bytes()
        old_block, new_block = run.block("old"), run.block("new")
        records = _argv_records(ctrl)[before:]
        expected_args = _expected_args(folder, ctrl)
        env_only_new = sorted(set(records[-1]["env_keys"]) - set(records[0]["env_keys"])) if len(records) == 2 else None
        env_only_old = sorted(set(records[0]["env_keys"]) - set(records[-1]["env_keys"])) if len(records) == 2 else None
        record.update({"old": old_info, "new": new_info, "cmp_vbs": cmp_info,
                       "stdout_B": len(out_b), "stderr_B": len(err_b), "total_B": len(out_b) + len(err_b),
                       "stderr_has_korean": "경고".encode("utf-8") in err_b,
                       "old_line_B": len(old_block[0]), "lines_byte_identical": old_block == new_block,
                       "old_made_no_capture_file": old_info["out_exists"] == "0" and old_info["err_exists"] == "0",
                       "python_prefix": run.side["pythonExe"], "argv_calls": len(records),
                       "argv_same_old_new": len(records) == 2 and records[0]["args"] == records[1]["args"]
                       and records[0]["argv0"] == records[1]["argv0"],
                       "argv_expected": bool(records) and all(r["args"] == expected_args for r in records),
                       "argv0_is_adapter": bool(records) and all(Path(r["argv0"]) == _adapter() for r in records),
                       "utf8_mode": [r["utf8_mode"] for r in records],
                       "cwd_same": len(records) == 2 and records[0]["cwd"] == records[1]["cwd"],
                       "env_only_new": env_only_new, "env_only_old": env_only_old,
                       "capture_files": [str(out_path), str(err_path)]})
        # (ii)
        self.assertEqual(len(out_b), 277)
        self.assertEqual(len(err_b), 406)
        self.assertEqual(out_b, STDOUT_LINE.encode("utf-8") + b"\r\n")
        self.assertEqual(err_b, b"".join(line.encode("utf-8") + b"\r\n" for line in WARN_LINES))
        self.assertTrue(record["stderr_has_korean"])
        self.assertEqual(old_info["code"], "0")
        self.assertEqual(new_info["code"], "0")
        self.assertEqual(cmp_info, {"code": "1", "out": "1", "err": "1", "result": "1", "line": "1", "errline": "1"})
        self.assertEqual(len(old_block), 1)
        self.assertEqual(old_block, new_block)
        self.assertTrue(record["old_made_no_capture_file"])
        # (iii)
        self.assertTrue(run.side["pythonExe"].startswith('"') and run.side["pythonExe"].endswith('"'))
        self.assertIn(" ", str(folder))
        self.assertIn(" ", str(_adapter()))
        self.assertEqual(new_info["out_exists"], "1")
        self.assertEqual(new_info["err_exists"], "1")
        self.assertEqual(len(records), 2)
        self.assertTrue(record["argv_same_old_new"])
        self.assertTrue(record["argv_expected"])
        self.assertTrue(record["argv0_is_adapter"])
        self.assertEqual(record["utf8_mode"], [1, 1])
        self.assertTrue(record["cwd_same"])

    def test_5_item_iv_capture_files_stay_and_empty_stderr(self):
        folder = _folder("iv 빈 stderr")
        run = run_harness("iv", _call_body(folder, "k8mock-emptyerr-0"), timeout=120)
        record = {"cscript_wall_sec": round(run.wall, 3), "complete": run.complete()}
        REPORT["iv"] = record
        self.assertTrue(run.complete(), run.text())
        new_info = run.info("NEW")
        out_path, err_path = folder / "action_002700.stdout.txt", folder / "action_002700.stderr.txt"
        record.update({"new": new_info, "new_lines": [b.decode("mbcs", "replace") for b in run.block("new")],
                       "stdout_B": out_path.stat().st_size,
                       "stderr_B": err_path.stat().st_size, "e2": run.side.get("e2"),
                       "files_in_decision_folder": sorted(p.name for p in folder.iterdir())})
        self.assertEqual(new_info["code"], "0")
        self.assertEqual(new_info["errlen"], "0")
        self.assertEqual(run.side["e2"], "")
        self.assertEqual(new_info["out_exists"], "1")
        self.assertEqual(new_info["err_exists"], "1")
        self.assertEqual(err_path.stat().st_size, 0)
        self.assertEqual(out_path.stat().st_size, 277)
        self.assertEqual(len(run.block("new")), 1)
        # report only: the old pipe function on the same empty-stderr mock (another decision folder)
        old_run = run_harness("iv_old", _call_body(_folder("iv old report"), "k8mock-emptyerr-0", old=True, new=False),
                              timeout=120)
        record["old_report_only"] = {
            "complete": old_run.complete(),
            "old_lines": [b.decode("mbcs", "replace") for b in old_run.block("old")] if old_run.complete()
            else old_run.text()[-500:],
            "same_line_as_new": old_run.complete() and old_run.block("old") == run.block("new")}

    def test_6_item_v_missing_quoted_python_path(self):
        folder = _folder("v 없는 경로")
        missing = _adapter().parent / "없음_k8" / "python.exe"
        self.assertFalse(missing.exists())
        before = len(_argv_records("k8mock-683-0"))
        body = _call_body(folder, "k8mock-683-0", py=str(missing), old=True,
                          pre=(f'WScript.Echo "@@V0PRE file_exists=" & B(fso.FileExists({vq(missing)}))',))
        body += 'WScript.Echo "@@V0 e1_prefix=" & B(Left(e1, 12) = "EXEC_FAILED ") & " o1_empty=" & B(o1 = "")\n'
        body += 'WScript.Echo "@@V1 o2_empty=" & B(o2 = "") & " o_eq=" & B(o1 = o2) & " e_eq=" & B(e1 = e2)\n'
        body += 'WScript.Echo "@@V3 out_exists=" & B(fso.FileExists(outP)) & " err_exists=" & B(fso.FileExists(errP))\n'
        run = run_harness("v", body, timeout=120)
        record = {"cscript_wall_sec": round(run.wall, 3)}
        REPORT["v"] = record
        self.assertTrue(run.complete(), run.text())
        v0, v1, v3, cmp_info = run.info("V0"), run.info("V1"), run.info("V3"), run.info("CMP")
        v0.update(run.info("V0PRE"))
        old_info, new_info = run.info("OLD"), run.info("NEW")
        old_block, new_block = run.block("old"), run.block("new")
        record.update({"pythonExe": run.side["pythonExe"], "v0": v0, "code1": old_info["code"], "v1": v1,
                       "code2": new_info["code"], "cmp_vbs": cmp_info, "v3": v3, "e1": run.side["e1"],
                       "e2": run.side["e2"], "old_lines": [b.decode("mbcs", "replace") for b in old_block],
                       "lines_byte_identical": old_block == new_block,
                       "mock_starts": len(_argv_records("k8mock-683-0")) - before})
        # (v-0) premise: otherwise the item is "premise not met", not a verdict on the implementation
        premise = (v0["file_exists"] == "0" and old_info["code"] == "-1" and v0["e1_prefix"] == "1"
                   and run.side["pythonExe"].startswith('"'))
        record["premise_met"] = premise
        if not premise:
            self.fail(f"(v-0) premise not met (not an implementation verdict): {record}")
        # (v-1)
        self.assertEqual(new_info["code"], "-1")
        self.assertEqual(v1, {"o2_empty": "1", "o_eq": "1", "e_eq": "1"})
        self.assertEqual(run.side["e1"], run.side["e2"])
        # (v-2): VBS:1239 result and VBS:1245 ERROR line; wall_sec is one fixed value in both
        self.assertEqual(cmp_info["result"], "1")
        self.assertEqual(cmp_info["errline"], "1")
        self.assertEqual(len(old_block), 2)
        self.assertEqual(old_block, new_block)
        self.assertTrue(old_block[1].startswith(f"ERROR=DECISION_EXIT_NONZERO sim_sec={SIM_SEC} exit=-1 stderr=EXEC_FAILED ".encode("ascii")))
        # (v-3)
        self.assertEqual(v3, {"out_exists": "0", "err_exists": "0"})
        self.assertEqual(record["mock_starts"], 0)  # neither call started a child

    def test_7_report_only_unquoted_launcher(self):
        folder = _folder("v prime launcher")
        run = run_harness("vprime", _call_body(folder, "k8mock-683-0", py="k8_no_such_launcher -3", old=True),
                          timeout=120)
        record = {"complete": run.complete(), "cscript_wall_sec": round(run.wall, 3)}
        REPORT["v_prime_report_only"] = record
        self.assertTrue(run.complete(), run.text())  # the harness ran; the outcome itself is only reported
        old_info, new_info = run.info("OLD"), run.info("NEW")
        record.update({"pythonExe": run.side["pythonExe"], "old_code": int(old_info["code"]),
                       "new_code": int(new_info["code"]), "old_nonzero_branch": int(old_info["code"]) != 0,
                       "new_nonzero_branch": int(new_info["code"]) != 0, "e1": run.side["e1"], "e2": run.side["e2"],
                       "new_capture_files": [new_info["out_exists"], new_info["err_exists"]],
                       "old_lines": [b.decode("mbcs", "replace") for b in run.block("old")],
                       "new_lines": [b.decode("mbcs", "replace") for b in run.block("new")]})

    @unittest.skipUnless(os.environ.get("K8_S6_REPORT_OLD64K") == "1", "report only; K8_S6_REPORT_OLD64K=1 runs it (60 s)")
    def test_8_report_only_old_function_with_64kb(self):
        folder = _folder("old 64k report")
        run = run_harness("old64k", _call_body(folder, "k8mock-64k-0", old=True, new=False), timeout=60)
        REPORT["old64k_report_only"] = {"finished_within_60s": not run.timed_out, "cscript_wall_sec": round(run.wall, 3),
                                        "killed_owned_tree": run.killed,
                                        "argv_calls": len(_argv_records("k8mock-64k-0"))}


if __name__ == "__main__":
    unittest.main()
