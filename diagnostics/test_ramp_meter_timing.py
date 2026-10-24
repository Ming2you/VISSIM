"""Execute canonical meter clocks with WSH and config transport with PowerShell; no VISSIM."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from scripts.tests.test_b1a_vbs_verified_capture_static import procedure

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts/run_real_world_stackelberg_controller.vbs'
WATCHDOG = ROOT / 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
CSCRIPT = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/cscript.exe'
POWERSHELL = CSCRIPT.parent / 'WindowsPowerShell/v1.0/powershell.exe'


@unittest.skipUnless(CSCRIPT.is_file(), 'Windows Script Host required')
class RampClockTests(unittest.TestCase):
    def run_clock(self, amber, source=None):
        source = RUNNER.read_text(encoding='utf-8') if source is None else source
        names = ('EnvText', 'FMod', 'DictValue',
                 'RampStateAt', 'ApplyRampMeterSignal', 'RampCompositeStateAt', 'NextRampTransitionAfter')
        has_runtime = 'Function ReadRuntimeRampAmberSec()' in source
        if has_runtime:
            names = ('ReadRuntimeRampAmberSec',)+names
        helpers = '\n\n'.join(procedure(source, name) for name in names)
        constants = '\n'.join(re.search(r'^Const '+name+r' = .+$', source, re.M).group(0)
                              for name in ('RAMP_CYCLE_SEC', 'RAMP_AMBER_SEC'))
        script = '''Option Explicit
Dim runtimeRampAmberSec, signalTraceSimSec, rampGreen, RW_RAMP_METER_SCS, simPeriod, g, t
Set rampGreen = CreateObject("Scripting.Dictionary")
RW_RAMP_METER_SCS = "9101"
simPeriod = 100
runtimeRampAmberSec = ReadRuntimeRampAmberSec()
Function SetSignalGroupState(sc, sg, state)
    SetSignalGroupState = state
End Function
For g = 0 To 10
    rampGreen("9101") = g
    For t = 0 To 30
        WScript.Echo g & "," & t & "," & RampStateAt(g,t) & "," & ApplyRampMeterSignal(9101,g,t) & "," & NextRampTransitionAfter(t)
    Next
Next
'''
        if not has_runtime:
            script = script.replace('runtimeRampAmberSec = ReadRuntimeRampAmberSec()',
                                    'runtimeRampAmberSec = RAMP_AMBER_SEC')
        env = dict(os.environ)
        env.pop('RW_RAMP_AMBER_SEC', None)
        if amber is not None:
            env['RW_RAMP_AMBER_SEC'] = amber
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'clock.vbs'
            path.write_text('Option Explicit\n'+constants+'\n'+script.removeprefix('Option Explicit\n')+'\n'+helpers, encoding='utf-16')
            return subprocess.run([str(CSCRIPT), '//nologo', str(path)], env=env,
                                  capture_output=True, text=True, encoding='mbcs', errors='replace', timeout=15)

    def test_all_greens_states_and_event_transitions_match_one_clock(self):
        results = {}
        for amber in (None, '1', '0'):
            result = self.run_clock(amber)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            results[amber] = result.stdout
            rows = [row.split(',') for row in result.stdout.splitlines()]
            self.assertEqual(len(rows), 11*31)
            clearance = 1 if amber is None else int(amber)
            def expected(g, t):
                position = t % 10
                return ('RED' if g <= 0 else 'GREEN' if position < g else
                        'AMBER' if position < g+clearance else 'RED')
            for green, time, state, applied, event in rows:
                g, t = int(green), int(time)
                self.assertEqual((state, applied), (expected(g,t), expected(g,t)))
                change = next((i for i in range(t+1,t+12) if expected(g,i) != state), 100)
                self.assertEqual(int(event), change)
                if amber == '0':
                    self.assertIn(state, ('RED', 'GREEN'))
        self.assertEqual(results[None], results['1'])

    def test_legacy_output_matches_archived_actual_runner_functions_byte_for_byte(self):
        path = ROOT/'diagnostics/control_improvement/decision_common_anchor_20260911/native_clock_replay_v1/source_v1/run_real_world_stackelberg_controller.vbs'
        source = path.read_text(encoding='utf-8')
        self.assertNotIn('Function ReadRuntimeRampAmberSec()', source)
        legacy = self.run_clock(None, source)
        self.assertEqual(legacy.returncode, 0, legacy.stdout+legacy.stderr)
        for amber in (None, '1'):
            current = self.run_clock(amber)
            self.assertEqual(current.returncode, 0, current.stdout+current.stderr)
            self.assertEqual(current.stdout, legacy.stdout)

    def test_bad_transport_fails_instead_of_falling_back(self):
        for value in ('2', '-1', '0.5', 'true', 'garbage'):
            result = self.run_clock(value)
            self.assertEqual(result.returncode, 2, result.stdout+result.stderr)
            self.assertIn('ERROR=INVALID_RAMP_AMBER_SEC', result.stdout)

    def test_startup_validation_precedes_vissim_and_urban_clock_is_unchanged(self):
        source = RUNNER.read_text(encoding='utf-8')
        self.assertLess(source.index('runtimeRampAmberSec = ReadRuntimeRampAmberSec()'),
                        source.index('Set Vissim = CreateObject("Vissim.Vissim")'))
        self.assertIn('Const AMBER_SEC = 3', source)
        self.assertIn('Const ALL_RED_SEC = 0', source)
        self.assertIn('state = RampStateAt(greenSec, simSec)', procedure(source, 'ApplyRampMeterSignal'))


@unittest.skipUnless(POWERSHELL.is_file(), 'Windows PowerShell required')
class RampTransportTests(unittest.TestCase):
    def test_canonical_config_and_transport(self):
        result = subprocess.run([str(POWERSHELL), '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(ROOT/'diagnostics/test_ramp_meter_timing.ps1')],
                                env=dict(os.environ), capture_output=True, text=True, encoding='mbcs', errors='replace', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
