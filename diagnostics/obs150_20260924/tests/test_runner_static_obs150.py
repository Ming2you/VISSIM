"""WP-A runner (plan V1 + A1-A9 wiring): compile check and the order of the obs150 calls.

tools/vbs_compile_check.ps1 compiles the whole runner without running a statement (plan V1).
The ordering tests pin the call sites the harness tests cannot reach: the top-level startup
sequence, the event loop and the state writer. The kill-policy tests pin that the obs150 (v2)
watchdog path can never reach the name-based Kill-Vissim. No VISSIM is started, and the
watchdog is only parsed here, never run.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import runner_harness as rh  # noqa: E402
from scripts.tests.test_b1a_vbs_verified_capture_static import _without_vbs_comment, procedure  # noqa: E402

COMPILE_CHECK = rh.ROOT / 'tools' / 'vbs_compile_check.ps1'


def code_lines(text):
    return [_without_vbs_comment(line) for line in text.splitlines()]


def ordered(test, text, tokens):
    positions = [text.index(token) for token in tokens]
    test.assertEqual(positions, sorted(positions), tokens)


class CompileCheckTests(unittest.TestCase):
    def compile(self, *paths):
        args = [rh.POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(COMPILE_CHECK)]
        if paths:
            args += ['-Path', ','.join(str(p) for p in paths)]
        return subprocess.run(args, cwd=str(rh.ROOT), capture_output=True, text=True, errors='replace', timeout=300)

    def setUp(self):
        if not (rh.POWERSHELL and rh.CSCRIPT):
            self.skipTest('Windows PowerShell and Windows Script Host are required')

    def test_runner_compiles(self):
        result = self.compile()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('VBS_COMPILE_OK path=' + str(rh.VBS_PATH), result.stdout)

    def test_a_syntax_error_is_reported(self):
        text = rh.VBS_PATH.read_bytes()
        mutant = text.replace(b'Sub Obs150StartupFatal(reason, detail)\n',
                              b'Sub Obs150StartupFatal(reason, detail)\n    If reason Then\n', 1)
        self.assertNotEqual(mutant, text)
        with tempfile.TemporaryDirectory(prefix='wpa_compile_') as temp:
            path = Path(temp) / 'mutant.vbs'
            path.write_bytes(mutant)
            result = self.compile(path)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('VBS_COMPILE_FAIL path=' + str(path), result.stdout)

    def test_the_check_does_not_run_the_runner(self):
        text = rh.VBS_PATH.read_bytes()
        # A runner whose first statement would echo: the inserted Quit 0 must stop it first.
        mutant = text.replace(b'Option Explicit\n', b'Option Explicit\nWScript.Echo "RAN"\n', 1)
        with tempfile.TemporaryDirectory(prefix='wpa_compile_') as temp:
            path = Path(temp) / 'echo.vbs'
            path.write_bytes(mutant)
            result = self.compile(path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('RAN', result.stdout)

    def test_watchdog_parses(self):
        command = ("$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
                   f"'{rh.PS1_PATH}',[ref]$t,[ref]$e);$e.Count")
        result = subprocess.run([rh.POWERSHELL, '-NoProfile', '-Command', command], capture_output=True, text=True,
                                errors='replace', timeout=120)
        self.assertEqual(result.stdout.strip(), '0', result.stdout + result.stderr)


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.text = rh.source()
        self.top = self.text[:self.text.index('Sub InitializeDefaultActionState()')]

    def test_startup_order(self):
        ordered(self, self.top, [
            'ValidateObs150Startup\n', 'ResolvePythonInterpreter\n', 'If obs150Mode Then Obs150VerifyDetectorTable\n',
            'Set Vissim = CreateObject("Vissim.Vissim")', 'If obs150Mode Then ReadObs150SimRes\n',
            'LoadFarMeasurementLinks\n', 'If obs150Mode Then Obs150InstallDetectors\n',
            'ConfigureEvaluationOutput fso.BuildPath', 'If obs150Mode Then Obs150WriteInstallRecord\n',
            'If Not obs150Mode Then Vissim.Simulation.AttValue("SimRes") = 1\n', 'ElseIf UseEventContinuousMode() Then'])
        self.assertNotIn('\nVissim.Simulation.AttValue("SimRes") = 1\n', self.top)

    def test_mode_selection(self):
        self.assertIn('UseContinuousStaticMode = (Not obs150Mode) And', procedure(self.text, 'UseContinuousStaticMode'))
        event = procedure(self.text, 'UseEventContinuousMode')
        ordered(self, event, ['If obs150Mode Then', 'UseEventContinuousMode = True',
                              '"RUN_MODE=CONTINUOUS_EVENT_OBS150 controller="', 'Exit Function'])

    def test_event_loop(self):
        loop = procedure(self.text, 'RunEventContinuousMode')
        ordered(self, loop, ['If obs150Mode Then', 'Obs150FirstStep', 'RunControllerDecision 1', 'Do While',
                             'Obs150AdvanceTo CLng(currentSec), CLng(targetSec)', 'RunControllerDecision CLng(currentSec)'])
        first = procedure(self.text, 'Obs150FirstStep')
        ordered(self, first, ['WriteLanePlantObservation 0, 0', 'RunContinuousTo 1', 'RecordStartupSimulationProgress'])
        self.assertIn('If obs150Mode Then Obs150AssertStop CLng(targetSec)', procedure(self.text, 'RunContinuousTo'))

    def test_meters_go_under_com_after_the_first_bundle(self):
        decision = procedure(self.text, 'RunControllerDecision')
        ordered(self, decision, ['WriteStateJson simSec, stateJsonPath, True',
                                 'If obs150Mode And CLng(simSec) = 1 Then InitializeComRampMeterControl',
                                 'exitCode = RunCapture3(cmd, outText, errText)', 'ApplyActionCsv(simSec'])

    def test_state_writer(self):
        writer = procedure(self.text, 'WriteStateJson')
        ordered(self, writer, ['If obs150Mode Then Obs150BeginBundle simSec', 'ScanVehicleState simSec',
                               'If Not scanOk Then', 'obs150Json = Obs150Bundle(simSec, collectionCountBefore',
                               'ts.TargetPath = tempPath', 'If obs150Mode Then ts.WriteLine "  ""obs150"": " & obs150Json',
                               '""cadence"": ""decision_150s""'])

    def test_evaluation_settings(self):
        evaluation = procedure(self.text, 'ConfigureEvaluationOutput')
        ordered(self, evaluation, [
            'Obs150RejectStaleEvaluation obs150EvalOutDir',
            'Obs150SetEvaluation "DataCollCollectData", True', 'Obs150SetEvaluation "DataCollFromTime", 0',
            'Obs150SetEvaluation "DataCollToTime", CLng(simPeriod)',
            'Obs150SetEvaluation "DataCollInterval", OBS150_DECISION_SEC',
            'Obs150SetEvaluation "DataCollRawWriteFile", True', 'Obs150SetEvaluation "DataCollRawFromTime", 0',
            'Obs150SetEvaluation "DataCollRawToTime", CLng(simPeriod)'])

    def test_signal_hooks_run_outside_resume_next(self):
        for name, hook in (('InitializeComRampMeterControl', 'Obs150SignalOwn CLng(scNo), 1, sg'),
                           ('EnableSignalControllerForRuntime', 'Obs150SignalOwn CLng(scNo), CLng(sgNo), sg')):
            body = procedure(self.text, name)
            at = body.index(hook)
            # the last error-mode switch before the hook turns Resume Next off again
            self.assertGreater(body.rindex('On Error GoTo 0', 0, at), body.rindex('On Error Resume Next', 0, at), name)
        self.assertIn('If obs150Mode Then Obs150SignalReadback scNo, sgNo, requestedState, readbackState, ok',
                      procedure(self.text, 'RecordSignalReadback'))

    def test_native_frame_advance_is_one_named_constant(self):
        self.assertEqual(re.findall(r'(?m)^Const OBS150_FRAME_ADVANCE = .*$', self.text),
                         [f'Const OBS150_FRAME_ADVANCE = {rh.D10_FRAME_ADVANCE}'])
        clock = procedure(self.text, 'SignalClockPosition')
        self.assertIn('frameAdvance = 1', clock)
        self.assertIn('If UBound(clockSpec) = 4 Then frameAdvance = CLng(clockSpec(4))', clock)

    def test_d10_is_documented_as_open(self):
        """While D10 is 0 it is open until G1: the runner must not present 0 as decided by V0-4."""
        if rh.D10_FRAME_ADVANCE != 0:
            self.skipTest('D10 decided: its record is the integrator\'s D10 patch')
        at = self.text.index('Const OBS150_FRAME_ADVANCE = 0')
        comment = self.text[self.text.rindex("' D10 (plan A4", 0, at):at]
        for phrase in ('is OPEN until G1', 'PROVISIONAL', 'READ-BACK only', 'moved\n\' at 851.1', 'The user decides D10'):
            self.assertIn(phrase, comment)
        self.assertNotIn('needs no frame advance', comment)
        apply_ = procedure(self.text, 'Obs150ApplyNativeFrameAdvance')
        self.assertIn('source=probe_readback d10=open_pending_G1', apply_)
        self.assertNotIn('source=V0-4', self.text)
        self.assertIn('If CLng(simResSteps) <> 10 Then', apply_)
        # The ground-truth writer does not claim a COM read-back is the state the vehicles feel.
        self.assertIn("For a COM SG it is the read-back state\n' only", self.text)

    def test_no_network_save(self):
        offenders = [line for line in code_lines(self.text) if re.search(r'(?i)\bSaveNet\b', line)]
        self.assertEqual(offenders, [])

    def test_obs150_code_is_ascii(self):
        block = rh.obs150_block(self.text) + rh.obs150_globals(self.text)
        self.assertTrue(block.isascii())


# Parse-only (Parser::ParseFile never runs a statement of the watchdog): every command and
# assignment the kill policy depends on, with its enclosing function and if-conditions.
AST_DUMP = r'''
param([string]$Path)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw "parse errors: $($errors.Count)" }
function Get-Enclosing($node) {
  $conditions = @(); $function = $null; $p = $node.Parent
  while ($null -ne $p) {
    if ($p -is [System.Management.Automation.Language.IfStatementAst]) {
      $inClause = $false
      foreach ($clause in $p.Clauses) {
        if ($clause.Item2.Extent.StartOffset -le $node.Extent.StartOffset -and
            $node.Extent.EndOffset -le $clause.Item2.Extent.EndOffset) {
          $conditions += $clause.Item1.Extent.Text; $inClause = $true
        }
      }
      if (-not $inClause -and $null -ne $p.ElseClause) { $conditions += 'else' }
    }
    if ($null -eq $function -and $p -is [System.Management.Automation.Language.FunctionDefinitionAst]) { $function = $p.Name }
    $p = $p.Parent
  }
  return @{conditions = @($conditions); function = $function}
}
$out = [ordered]@{commands = @(); assignments = @(); loops = @(); functions = @()}
foreach ($c in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] }, $true)) {
  $e = Get-Enclosing $c
  $out.commands += [ordered]@{name = [string]$c.GetCommandName(); text = $c.Extent.Text; offset = $c.Extent.StartOffset;
    function = $e.function; conditions = $e.conditions; pipeline = $c.Parent.Extent.Text}
}
foreach ($a in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] }, $true)) {
  $e = Get-Enclosing $a
  $out.assignments += [ordered]@{left = $a.Left.Extent.Text; text = $a.Extent.Text; offset = $a.Extent.StartOffset;
    function = $e.function; conditions = $e.conditions}
}
foreach ($f in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.ForStatementAst] }, $true)) {
  $out.loops += [ordered]@{initializer = $f.Initializer.Extent.Text; condition = $f.Condition.Extent.Text; offset = $f.Extent.StartOffset}
}
foreach ($f in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)) {
  $out.functions += [ordered]@{name = $f.Name; first = $f.Body.EndBlock.Statements[0].Extent.Text; text = $f.Extent.Text}
}
[Console]::Out.Write(($out | ConvertTo-Json -Depth 6 -Compress))
'''

NAME_KILL = 'Get-Process -Name "VISSIM200","VISSIM200CL","cscript"'


class KillPolicyTests(unittest.TestCase):
    """The v2 (obs150) watchdog stops only what it launched, by PID and start time.

    Kill-Vissim stops every VISSIM and cscript on the machine by NAME (it killed three live runs
    on 2026-09-24 03:15). These tests only read and parse the watchdog; they never run it.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = rh.PS1_PATH.read_bytes().decode('utf-8-sig')
        cls.ast = None
        if rh.POWERSHELL:
            with tempfile.TemporaryDirectory(prefix='wpa_ast_') as temp:
                dump = Path(temp) / 'ast_dump.ps1'
                dump.write_text(AST_DUMP, encoding='utf-8-sig')
                result = subprocess.run([rh.POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(dump),
                                         '-Path', str(rh.PS1_PATH)], capture_output=True, timeout=180)
            if result.returncode != 0:
                raise AssertionError(result.stdout.decode('utf-8', 'replace') + result.stderr.decode('utf-8', 'replace'))
            cls.ast = json.loads(result.stdout.decode('utf-8'))

    def need_ast(self):
        if self.ast is None:
            self.skipTest('Windows PowerShell is required for the AST checks')
        return self.ast

    def commands(self, name):
        return [c for c in self.need_ast()['commands'] if c['name'] == name]

    def assignments(self, left):
        return [a for a in self.need_ast()['assignments'] if a['left'] == left]

    def attempt_loop_offset(self):
        loops = [loop for loop in self.need_ast()['loops'] if loop['initializer'] == '$attempt = 1']
        self.assertEqual(len(loops), 1, loops)
        self.assertEqual(loops[0]['condition'], '$attempt -le $MaxAttempts')
        return loops[0]['offset']

    def function(self, name):
        found = [f for f in self.need_ast()['functions'] if f['name'] == name]
        self.assertEqual(len(found), 1, name)
        return found[0]

    def test_kill_vissim_is_called_only_behind_no_global_kill(self):
        calls = self.commands('Kill-Vissim')
        self.assertEqual(len(calls), 1, calls)
        call = calls[0]
        self.assertIsNone(call['function'])
        self.assertEqual(call['conditions'], ['-not $NoGlobalKill'])
        self.assertGreater(call['offset'], self.attempt_loop_offset())

    def test_v2_forces_no_global_kill_before_the_attempt_loop(self):
        writes = self.assignments('$NoGlobalKill')
        # One write only, so nothing can clear it again before the loop.
        self.assertEqual(len(writes), 1, writes)
        write = writes[0]
        self.assertEqual(write['text'], '$NoGlobalKill = $true')
        self.assertIsNone(write['function'])
        self.assertEqual(write['conditions'], ['$headObservation.obs150'])
        self.assertLess(write['offset'], self.attempt_loop_offset())

    def test_kill_vissim_refuses_on_the_v2_path(self):
        flags = self.assignments('$script:Obs150Run')
        self.assertEqual([f['text'] for f in flags], ['$script:Obs150Run = [bool]$headObservation.obs150'])
        self.assertIsNone(flags[0]['function'])
        self.assertEqual(flags[0]['conditions'], [])
        self.assertLess(flags[0]['offset'], self.assignments('$NoGlobalKill')[0]['offset'])
        kill = self.function('Kill-Vissim')
        # The guard is the first statement: nothing runs before it, the name-based stop runs after it.
        self.assertEqual(kill['first'], "if ($script:Obs150Run) { throw 'obs150 (v2) never stops processes by name (Kill-Vissim)' }")
        self.assertLess(kill['text'].index('throw'), kill['text'].index(NAME_KILL))

    def test_name_based_stops_exist_only_inside_kill_vissim(self):
        stops = self.commands('Stop-Process')
        self.assertEqual(len(stops), 2, stops)
        by_name = [s for s in stops if s['function'] == 'Kill-Vissim']
        by_pid = [s for s in stops if s['function'] == 'Stop-RunProcesses']
        self.assertEqual(len(by_name), 1)
        self.assertIn(NAME_KILL, by_name[0]['pipeline'])
        self.assertEqual(len(by_pid), 1)
        self.assertRegex(by_pid[0]['text'], r'^Stop-Process -Id \$current\.Id\b')
        self.assertEqual(by_pid[0]['conditions'], ['$current -and $current.StartTime -eq $identity.StartTime'])
        for name in ('taskkill', 'taskkill.exe', 'Stop-Computer', 'wmic'):
            self.assertEqual(self.commands(name), [], name)
        # Get-Process by name only identifies (no stop) outside Kill-Vissim.
        for get in self.commands('Get-Process'):
            if get['function'] != 'Kill-Vissim':
                self.assertNotIn('Stop-Process', get['pipeline'], get)

    def test_stops_use_the_identity_recorded_at_launch(self):
        identities = self.assignments('$runnerIdentity')
        self.assertEqual([i['text'] for i in identities],
                         ['$runnerIdentity = [pscustomobject]@{ Id = $proc.Id; StartTime = $proc.StartTime }'])
        calls = self.commands('Stop-RunProcesses')
        # STARTUP_TIMEOUT and WATCHDOG_KILL (with the v2 descendants), EXIT_NO_DONE (v2 only).
        self.assertEqual(sorted(c['text'] for c in calls),
                         ['Stop-RunProcesses $runnerIdentity $runVissimIdentity']
                         + ['Stop-RunProcesses $runnerIdentity $runVissimIdentity $runDescendants'] * 2)
        for call in calls:
            self.assertIsNone(call['function'])
            self.assertGreater(call['offset'], identities[0]['offset'])
        after_exit = [c for c in calls if not c['text'].endswith('$runDescendants')][0]
        self.assertEqual(after_exit['conditions'], ['$script:Obs150Run', '$proc.HasExited'])
        descendants = self.assignments('$runDescendants')
        self.assertEqual(
            [d['text'] for d in descendants],
            ['$runDescendants = $(if ($script:Obs150Run) { Get-RunDescendantIdentities $runnerIdentity } else { @() })'] * 2)
        stop = self.function('Stop-RunProcesses')['text']
        self.assertIn('Get-Process -Id $identity.Id', stop)
        for name in ('Stop-RunProcesses', 'Get-RunDescendantIdentities', 'Test-RunVissimTitle'):
            self.assertNotIn('-Name', self.function(name)['text'], name)
        walk = self.function('Get-RunDescendantIdentities')['text']
        self.assertNotIn('Stop-Process', walk)
        # Only children created after their parent, from a root whose start time still matches.
        self.assertIn('if (-not $root -or $root.StartTime -ne $RootIdentity.StartTime) { return ,$found }', walk)
        self.assertIn('$child.CreationDate -lt $parent.StartTime', walk)

    def test_vissim_identification_matches_a_whole_file_name(self):
        find = self.function('Find-RunVissimIdentity')['text']
        self.assertIn('(Test-RunVissimTitle $_.MainWindowTitle $NetworkFileName)', find)
        self.assertNotIn('IndexOf', find)

    def test_grep_kill_vissim_call_sites(self):
        """The same pin without the parser: plain text, comments stripped."""
        code = [line.split('#', 1)[0].rstrip() for line in self.text.splitlines()]
        sites = [line.strip() for line in code if 'Kill-Vissim' in line]
        self.assertEqual(sites, ['function Kill-Vissim {',
                                 "if ($script:Obs150Run) { throw 'obs150 (v2) never stops processes by name (Kill-Vissim)' }",
                                 'if (-not $NoGlobalKill) { Kill-Vissim } else { Log "NoGlobalKill: 전역 VISSIM/cscript kill 생략" }'])
        self.assertEqual(len(re.findall(r'(?m)^\s*\$NoGlobalKill\s*=', self.text)), 1)
        # The first top-level v2 block (the argument checks) holds it; it ends at the next column-0 '}'.
        start = re.search(r'(?m)^if \(\$headObservation\.obs150\) \{\r?$', self.text).start()
        block = self.text[start:self.text.index('\n}', start)]
        self.assertIn('$NoGlobalKill = $true', block)
        self.assertLess(self.text.index('$NoGlobalKill = $true'), self.text.index('for ($attempt = 1;'))
        self.assertEqual([line.strip() for line in code if 'Stop-Process' in line],
                         ['Stop-Process -Force -ErrorAction SilentlyContinue',
                          'Stop-Process -Id $current.Id -Force -ErrorAction SilentlyContinue'])

    def test_preflight_only_exits_before_any_stop_or_attempt(self):
        """-PreflightOnly (run by the launcher before G1) leaves at its own top-level block, before the
        attempt loop and before every call site of Kill-Vissim and Stop-RunProcesses. Plain text, no parser."""
        code = [line.split('#', 1)[0].rstrip() for line in self.text.splitlines()]
        starts = [i for i, line in enumerate(code) if line == 'if ($PreflightOnly) {']
        self.assertEqual(len(starts), 1, starts)
        end = next(i for i in range(starts[0] + 1, len(code)) if code[i] == '}')
        block = [line.strip() for line in code[starts[0] + 1:end] if line.strip()]
        self.assertEqual(block[-1], 'exit 0', block)
        self.assertFalse([line for line in block if re.search(r'Kill-Vissim|Stop-RunProcesses|Stop-Process', line)], block)
        loop = [i for i, line in enumerate(code) if line.startswith('for ($attempt = 1;')]
        self.assertEqual(len(loop), 1, loop)
        self.assertLess(end, loop[0])
        calls = [i for i, line in enumerate(code)
                 if re.search(r'\b(Kill-Vissim|Stop-RunProcesses)\b', line) and not line.lstrip().startswith('function ')
                 and "throw 'obs150 (v2) never stops" not in line]
        self.assertEqual(len(calls), 4, [code[i].strip() for i in calls])   # 1 Kill-Vissim + 3 Stop-RunProcesses
        self.assertTrue(all(i > end for i in calls), [(i + 1, code[i].strip()) for i in calls])


if __name__ == '__main__':
    unittest.main()
