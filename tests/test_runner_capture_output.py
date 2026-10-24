"""Exercise the real VBS capture functions without opening VISSIM.

The child exits itself after three seconds if its output blocks, so a failing
regression test cannot leave a hung helper process behind.
"""
import os
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts/run_real_world_stackelberg_controller.vbs'


@unittest.skipUnless(os.name == 'nt', 'Windows Script Host required')
class RunnerCaptureTests(unittest.TestCase):
    def test_fixed_replay_uses_all_decision_times(self):
        source = RUNNER.read_text(encoding='utf-8-sig')
        function = re.search(r'(?ms)^Function UseSingleDecisionEventMode\(.*?^End Function\s*$', source).group(0)
        cases = [('diagnostic-ramp-profile', 900, '', True),
                 ('diagnostic-ramp-profile', 900, 'commands', False),
                 ('diagnostic-vsl-profile', 900, 'commands', False),
                 ('diagnostic-rule-profile', 900, '', False),
                 ('wu-link', 900, '', False), ('no-control', 900, '', False),
                 ('diagnostic-ramp-profile', -1, '', False)]
        with tempfile.TemporaryDirectory(prefix='replay cadence ') as directory:
            script = Path(directory)/'probe.vbs'
            lines = ['Option Explicit', 'Dim controllerName, controlStartSec, RW_COMMAND_REPLAY_DIR']
            for controller, start, replay, expected in cases:
                lines += [f'controllerName="{controller}"', f'controlStartSec={start}',
                          f'RW_COMMAND_REPLAY_DIR="{replay}"',
                          'WScript.Echo CStr(UseSingleDecisionEventMode())']
            script.write_text('\n'.join(lines)+'\n'+function, encoding='utf-16')
            result = subprocess.run(['cscript.exe','//Nologo',str(script)], capture_output=True,
                                    text=True, encoding='mbcs', timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [str(row[3]) for row in cases])

    def test_recorded_commands_copy_exactly_without_pending_price_receipt(self):
        source = RUNNER.read_text(encoding='utf-8-sig')
        function = re.search(r'(?ms)^Function CopyRecordedAction\(.*?^End Function\s*$', source).group(0)
        with tempfile.TemporaryDirectory(prefix='replay 한글 ') as directory:
            folder=Path(directory); original=folder/'source'; original.mkdir()
            (original/'action_000150.json').write_bytes(b'{"saved":true}\n')
            (original/'action_000150.csv').write_bytes(b'kind,id\r\nvsl,1\r\n')
            (original/'action_000150.json.sdmpc_pending').write_text('old context')
            script=folder/'test.vbs'
            def quoted(p):return '"'+str(p).replace('"','""')+'"'
            script.write_text('Option Explicit\nDim fso,rc,e\nSet fso=CreateObject("Scripting.FileSystemObject")\n'
                +f'rc=CopyRecordedAction({quoted(original)},"action_000150",{quoted(folder/"out.json")},{quoted(folder/"out.csv")},e)\n'
                +'WScript.Echo CStr(rc) & ":" & e\n'+function,encoding='utf-16')
            for expected in (0,1):
                result=subprocess.run(['cscript.exe','//Nologo',str(script)],capture_output=True,
                                      text=True,encoding='mbcs',timeout=5)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertTrue(result.stdout.startswith(str(expected)+':'),result.stdout)
            for suffix in ('json','csv'):
                self.assertEqual((folder/f'out.{suffix}').read_bytes(),(original/f'action_000150.{suffix}').read_bytes())
            self.assertFalse((folder/'out.json.sdmpc_pending').exists())
            (folder/'out.json').unlink();(folder/'out.csv').unlink()
            (original/'action_000150.csv').unlink()
            result=subprocess.run(['cscript.exe','//Nologo',str(script)],capture_output=True,
                                  text=True,encoding='mbcs',timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(result.stdout.startswith('1:'),result.stdout)
            self.assertFalse((folder/'out.json').exists())

    def capture(self, timed, *, size=65536, code=0, delay=0, limit=5):
        source = RUNNER.read_text(encoding='utf-8-sig')
        names = ('RunCapture3', 'RunCapture3Timeout', 'StartFileCapture',
                 'FinishFileCapture', 'TerminateExecTree', 'Q')
        blocks = []
        for name in names:
            match = re.search(r'(?ms)^(Function|Sub) ' + name + r'\(.*?^End \1\s*$', source)
            if match:
                blocks.append(match.group(0))
        with tempfile.TemporaryDirectory(prefix='capture test 한글 &() ') as directory:
            folder = Path(directory)
            child = folder/'child.py'
            child.write_text(
                'import os,sys,threading,time\n'
                f'time.sleep({delay!r})\n'
                'def emit():\n'
                f' os.write(1,b"O"*{size})\n'
                f' os.write(2,b"E"*{size})\n'
                't=threading.Thread(target=emit,daemon=True)\n'
                't.start();t.join(3)\n'
                f'os._exit(97 if t.is_alive() else {code})\n', encoding='utf-8')
            command = subprocess.list2cmdline([sys.executable,str(child)])
            call = f'RunCapture3Timeout(cmd, {limit}, o, e)' if timed else 'RunCapture3(cmd, o, e)'
            script = folder/'probe.vbs'
            script.write_text(
                'Option Explicit\nDim shell,fso,cmd,o,e,rc\n'
                'Set shell=CreateObject("WScript.Shell")\n'
                'Set fso=CreateObject("Scripting.FileSystemObject")\n'
                'cmd="'+command.replace('"','""')+'"\n'
                f'rc={call}\n'
                'WScript.Echo CStr(rc) & "," & CStr(Len(o)) & "," & CStr(Len(e))\n'
                'WScript.Quit 0\n'+'\n'.join(blocks), encoding='utf-16')
            result = subprocess.run(['cscript.exe','//Nologo',str(script)],
                                    capture_output=True,text=True,encoding='mbcs',timeout=12)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertTrue(result.stdout.strip(),result.stderr)
            return tuple(map(int,result.stdout.strip().split(',')))

    def test_both_large_streams_complete(self):
        self.assertEqual(self.capture(False),(0,65536,65536))

    def test_timed_both_large_streams_preserve_failure_code(self):
        self.assertEqual(self.capture(True,code=7),(7,65536,65536))

    def test_small_output_is_unchanged(self):
        self.assertEqual(self.capture(False,size=3),(0,3,3))

    def test_empty_output_is_unchanged(self):
        self.assertEqual(self.capture(False,size=0),(0,0,0))

    def test_owned_child_timeout(self):
        result = self.capture(True,size=0,delay=4,limit=0.2)
        self.assertEqual(result[0],-2)
        self.assertGreaterEqual(result[2],len('EXEC_TIMEOUT'))


@unittest.skipUnless(os.name == 'nt', 'Windows Script Host required')
class NativeNetworkPerformanceTests(unittest.TestCase):
    def capture(self, *, delay='50.0', covered='True', sim_time='150.0', existing=False):
        source = RUNNER.read_text(encoding='utf-8-sig')
        names = ('WriteNativeNetworkPerformance', 'NativeNetworkPerformanceFatal', 'TryB1aFiniteDouble', 'ComBoolean', 'Num')
        blocks = [re.search(r'(?ms)^(Function|Sub) ' + name + r'\(.*?^End \1\s*$', source).group(0)
                  for name in names]
        with tempfile.TemporaryDirectory(prefix='native performance ') as directory:
            folder = Path(directory)
            output = folder/'result.json'
            if existing:
                output.write_text('preserved', encoding='ascii')
            fixture = '''Option Explicit
Dim Vissim, fso, simPeriod, target
Class FakeLinks
 Public Property Get Count
  Count = 2
 End Property
 Public Function GetMultiAttValues(key)
  Dim values(1,1)
  values(0,0) = 1: values(0,1) = True
  values(1,0) = 2: values(1,1) = COVERED
  GetMultiAttValues = values
 End Function
End Class
Class FakeMetrics
 Public Function AttValue(key)
  Select Case key
   Case "TravTmTot(Current,1,All)": AttValue = 100.0
   Case "DelayLatent(Current,1)": AttValue = DELAY
   Case "DemandLatent(Current,1)": AttValue = 1
   Case "VehAct(Current,1,All)": AttValue = 2
   Case "VehArr(Current,1,All)": AttValue = 4
   Case Else: Err.Raise 5, , "Unexpected query: " & key
  End Select
 End Function
End Class
Class FakeSimulation
 Public Function AttValue(key)
  AttValue = SIMTIME
 End Function
End Class
Class FakeNet
 Public Links, VehicleNetworkPerformanceMeasurement
End Class
Class FakeVissim
 Public Net, Simulation
End Class
Set Vissim = New FakeVissim
Set Vissim.Net = New FakeNet
Set Vissim.Net.Links = New FakeLinks
Set Vissim.Net.VehicleNetworkPerformanceMeasurement = New FakeMetrics
Set Vissim.Simulation = New FakeSimulation
Set fso = CreateObject("Scripting.FileSystemObject")
simPeriod = 150
target = "OUTPUT"
WriteNativeNetworkPerformance target
'''.replace('COVERED', covered).replace('DELAY', delay).replace('SIMTIME', sim_time)
            fixture = fixture.replace('OUTPUT', str(output).replace('"', '""'))
            script = folder/'probe.vbs'
            script.write_text(fixture+'\n'.join(blocks), encoding='utf-16')
            result = subprocess.run(['cscript.exe','//Nologo',str(script)], capture_output=True,
                                    text=True, encoding='mbcs', timeout=5)
            return result, output.read_text(encoding='ascii') if output.exists() else None

    def test_native_seconds_and_counts_are_separate(self):
        result, text = self.capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(text)
        self.assertEqual(data['native'], dict(TravTmTot=100, DelayLatent=50, DemandLatent=1, VehAct=2, VehArr=4))
        self.assertEqual(data['evaluated_links'], 2)
        self.assertEqual(data['to_sec'], 150)

    def test_missing_or_invalid_values_are_not_zero(self):
        for delay in ('Null', 'Empty', '-1.0', '""'):
            with self.subTest(delay=delay):
                result, text = self.capture(delay=delay)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(text)

    def test_partial_scope_and_incomplete_run_fail(self):
        for change in ({'covered':'False'}, {'sim_time':'149.9'}):
            with self.subTest(change=change):
                result, text = self.capture(**change)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(text)

    def test_existing_result_is_preserved(self):
        result, text = self.capture(existing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(text, 'preserved')


if __name__ == '__main__':
    unittest.main()
