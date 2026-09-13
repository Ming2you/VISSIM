"""Actual VBS demand routines with in-script fake objects; no VISSIM COM.

The original source is read from the parent's exact ZIP; production is read
once and never edited. Generated harnesses and outputs are retained for audit.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts/run_real_world_stackelberg_controller.vbs'
ARCHIVE = ROOT / 'diagnostics/fixtures/startup_gui_original_vbs_v1.zip'
ORIGINAL_SHA = '71ec5f8d8a36a93f21f8e66da80730e91dae64de1a3eb2321f0361df636b9a81'
CURRENT_SHA = '30a279cbcc111a7374af023decf65456ccf6c46e005dc7ab6639bc8b5f69cdb0'

FAKES = r'''
Class FakeWindow
    Public Property Let AttValue(key, value)
        WScript.Echo "TRACE=QUICK key=" & key & " value=" & CStr(value)
    End Property
End Class
Class FakeGraphics
    Public CurrentNetworkWindow
    Private Sub Class_Initialize()
        Set CurrentNetworkWindow = New FakeWindow
    End Sub
End Class
Class FakeVissim
    Public Graphics
    Private Sub Class_Initialize()
        Set Graphics = New FakeGraphics
    End Sub
    Sub LoadNet(path, add)
        WScript.Echo "TRACE=LOAD"
    End Sub
    Sub SuspendUpdateGUI()
        guiSuspended = True
        WScript.Echo "TRACE=SUSPEND"
    End Sub
End Class
Class FakeInterval
    Public Idx, Volume, Written
    Public Property Get AttValue(key)
        WScript.Echo "TRACE=GET idx=" & CStr(Idx) & " key=" & key
        If key = "TimeInt" Then
            AttValue = "1-" & CStr(Idx)
        ElseIf key = "Volume" Then
            If Idx = 5 Then
                If (mode = "before_fail" Or mode = "both_fail") And Written = 0 Then
                    Err.Raise 513, "Fake.Volume", "BEFORE_SENTINEL"
                    Exit Property
                End If
                If mode = "after_fail" And Written > 0 Then
                    Err.Raise 515, "Fake.Volume", "AFTER_SENTINEL"
                    Exit Property
                End If
                If mode = "empty" Then
                    AttValue = Empty
                    Exit Property
                End If
                If mode = "text" Then
                    AttValue = "not-a-number"
                    Exit Property
                End If
            End If
            AttValue = Volume
        ElseIf key = "Cont" Then
            AttValue = False
        End If
    End Property
    Public Property Let AttValue(key, value)
        WScript.Echo "TRACE=SET idx=" & CStr(Idx) & " key=" & key & " value=" & Num(value) & " suspended=" & CStr(guiSuspended)
        If Idx = 5 And (mode = "write_fail" Or mode = "both_fail") Then
            Err.Raise 514, "Fake.Volume", "WRITE_SENTINEL"
            Exit Property
        End If
        Volume = value
        Written = Written + 1
    End Property
End Class
Class FakeIntervals
    Public Rows
    Function GetAll()
        GetAll = Rows
    End Function
End Class
Class FakeInput
    Public TimeIntVehVols
    Public Property Get AttValue(key)
        If key = "No" Then AttValue = "1097"
    End Property
End Class
'''


def routines(source):
    names = {'ScaleInputAllIntervals', 'StrictDemandAttribute', 'StrictDemandVolume',
             'SafeAtt', 'ToDbl', 'Num', 'TimeIntIndex', 'FatalDemandError'}
    return '\n'.join(m[0] for m in re.finditer(r'(?ms)^(?:Sub|Function) (\w+)[^\n]*\n.*?^End (?:Sub|Function)', source) if m[1] in names)


def gui_block(source):
    return re.search(r'(?ms)^On Error Resume Next\nVissim\.Graphics\.CurrentNetworkWindow\.AttValue\("QuickMode"\) = 1\nVissim\.SuspendUpdateGUI\nErr\.Clear\nOn Error GoTo 0', source)[0]


@unittest.skipUnless(sys.platform == 'win32', 'Requires Windows cscript; never creates VISSIM')
class StartupDemandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        current_raw = RUNNER.read_bytes()
        if hashlib.sha256(current_raw).hexdigest() != CURRENT_SHA:
            raise ValueError('Current VBS differs from the reviewed parent patch')
        with zipfile.ZipFile(ARCHIVE) as archive:
            original_raw = archive.read('scripts/run_real_world_stackelberg_controller.vbs')
        if hashlib.sha256(original_raw).hexdigest() != ORIGINAL_SHA:
            raise ValueError('Original VBS recovery bytes differ')
        cls.current = current_raw.decode('utf-8-sig').replace('\r\n', '\n')
        cls.original = original_raw.decode('utf-8-sig').replace('\r\n', '\n')
        cls.dest = ROOT / 'diagnostics' / ('startup_demand_gui_validation_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        cls.dest.mkdir(exist_ok=False)
        cls.evidence = []

    def invoke(self, source, *, mode='ok', factor=1.0, label):
        before_gui = source.index('Vissim.SuspendUpdateGUI') < source.index('    ApplyVehicleInputDemandProfile CDbl(demandScale)')
        init = ['Option Explicit', 'Dim Vissim, mode, guiSuspended, netPath, vi, col, rows(5), i, values, beforeText, afterText, nIntervals, totalsBefore, totalsAfter',
                'mode = "' + mode + '"', 'guiSuspended = False', 'netPath = "FAKE_ONLY_NO_LOADNET"',
                'Set Vissim = New FakeVissim', 'Vissim.LoadNet netPath, False']
        if before_gui:
            init.append(gui_block(source))
        init += ['values = Array(112, 160, 168, 144, 112, 80)',
                 'For i = 0 To 5', '    Set rows(i) = New FakeInterval',
                 '    rows(i).Idx = i + 1', '    rows(i).Volume = CDbl(values(i))',
                 '    rows(i).Written = 0', 'Next',
                 'Set col = New FakeIntervals', 'col.Rows = rows', 'Set vi = New FakeInput',
                 'Set vi.TimeIntVehVols = col',
                 'Set totalsBefore = CreateObject("Scripting.Dictionary")',
                 'Set totalsAfter = CreateObject("Scripting.Dictionary")',
                 'ScaleInputAllIntervals vi, ' + str(factor) + ', totalsBefore, totalsAfter, beforeText, afterText, nIntervals']
        if not before_gui:
            init.append(gui_block(source))
        init += ['WScript.Echo "RESULT=" & beforeText & "|" & afterText & "|" & CStr(nIntervals)', 'WScript.Quit 0']
        body = '\n'.join(init) + '\n' + FAKES + '\n' + routines(source)
        self.assertNotIn('CreateObject("Vissim.', body)
        self.assertNotIn('RunSingleStep', body)
        path = self.dest / (label + '.vbs')
        path.write_bytes(body.encode('utf-16'))
        executable = Path(os.environ['SystemRoot']) / 'System32/cscript.exe'
        result = subprocess.run([str(executable), '//nologo', str(path)], capture_output=True, timeout=10)
        (self.dest / (label + '.stdout')).write_bytes(result.stdout)
        (self.dest / (label + '.stderr')).write_bytes(result.stderr)
        text = result.stdout.decode('utf-8', errors='replace')
        self.evidence.append({'label': label, 'source_sha256': CURRENT_SHA if source == self.current else ORIGINAL_SHA,
                              'mode': mode, 'factor': factor, 'exit_code': result.returncode,
                              'harness_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                              'stdout_sha256': hashlib.sha256(result.stdout).hexdigest()})
        return result.returncode, text

    def test_gui_before_demand_and_native_settings_order_preserved(self):
        self.assertLess(self.current.index('Vissim.SuspendUpdateGUI'), self.current.index('    ApplyVehicleInputDemandProfile CDbl(demandScale)'))
        self.assertEqual(gui_block(self.original), gui_block(self.current))
        for factor in (1.0, 0.8333):
            a, old = self.invoke(self.original, factor=factor, label='normal_old_' + str(factor))
            b, new = self.invoke(self.current, factor=factor, label='normal_current_' + str(factor))
            self.assertEqual((a, b), (0, 0))
            old_writes = re.findall(r'TRACE=SET (.*?) suspended=', old)
            new_writes = re.findall(r'TRACE=SET (.*?) suspended=', new)
            self.assertEqual(old_writes, new_writes)
            self.assertEqual(len(new_writes), 6)
            old_access = [re.sub(r' suspended=.*$', '', x) for x in re.findall(r'TRACE=(?:GET|SET) [^\r\n]*', old)]
            new_access = [re.sub(r' suspended=.*$', '', x) for x in re.findall(r'TRACE=(?:GET|SET) [^\r\n]*', new)]
            self.assertEqual(old_access, new_access)
            self.assertEqual(re.findall(r'RESULT=.*', old), re.findall(r'RESULT=.*', new))
            self.assertLess(new.index('TRACE=SUSPEND'), new.index('TRACE=SET'))
            self.assertGreater(old.index('TRACE=SUSPEND'), old.index('TRACE=SET'))
            self.assertNotIn('key=Cont', new)

    def test_original_read_failure_turns_into_zero_but_num_preserves_setter_description(self):
        code, out = self.invoke(self.original, mode='both_fail', label='old_both_fail')
        self.assertEqual(code, 12)
        self.assertIn('TRACE=SET idx=5 key=Volume value=0.000000', out)
        self.assertRegex(out, r'ERROR=DEMAND_INTERVAL_SET_FAILED no=1097 time_int=1-5 target=0\.000000 err=WRITE_SENTINEL\s*$')
        self.assertNotIn('BEFORE_SENTINEL', out)

    def test_immediate_write_error_is_preserved_and_stops(self):
        code, out = self.invoke(self.current, mode='write_fail', label='current_write_fail')
        self.assertEqual(code, 12)
        self.assertIn('target=112.000000 error_number=514 err=WRITE_SENTINEL', out)
        self.assertNotIn('TRACE=SET idx=6', out)

    def test_before_read_failure_never_writes_zero(self):
        code, out = self.invoke(self.current, mode='before_fail', label='current_before_fail')
        self.assertEqual(code, 12)
        self.assertIn('stage=before attribute=Volume error_number=513 err=BEFORE_SENTINEL', out)
        self.assertNotIn('TRACE=SET idx=5', out)

    def test_after_read_failure_preserves_original_error(self):
        code, out = self.invoke(self.current, mode='after_fail', label='current_after_fail')
        self.assertEqual(code, 12)
        self.assertIn('stage=after attribute=Volume error_number=515 err=AFTER_SENTINEL', out)
        self.assertNotIn('TRACE=SET idx=6', out)

    def test_empty_or_nonnumeric_read_is_not_a_zero_demand(self):
        for mode, error in (('empty', 'DEMAND_ATTRIBUTE_READ_EMPTY'), ('text', 'DEMAND_VOLUME_NOT_NUMERIC')):
            code, out = self.invoke(self.current, mode=mode, label='current_' + mode)
            self.assertEqual(code, 12)
            self.assertIn(error, out)
            self.assertNotIn('TRACE=SET idx=5', out)

    @classmethod
    def tearDownClass(cls):
        after_sha = hashlib.sha256(RUNNER.read_bytes()).hexdigest()
        result = {'schema': 'startup-demand-gui-fake/v1', 'current_sha256': CURRENT_SHA,
                  'original_sha256': ORIGINAL_SHA, 'source_changes': [] if after_sha == CURRENT_SHA else [str(RUNNER)],
                  'cases': cls.evidence, 'actual_vissim_instances': 0, 'simulation_steps': 0,
                  'scope': 'Actual extracted VBS routines and GUI block against in-script fake objects. Setter side effects inside VISSIM are not modeled or certified.'}
        (cls.dest / 'evidence.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print('EVIDENCE=' + str(cls.dest))
        if after_sha != CURRENT_SHA:
            raise AssertionError('Production VBS changed during fake regression')


if __name__ == '__main__':
    unittest.main()
