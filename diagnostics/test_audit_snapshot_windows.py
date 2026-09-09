"""Validate the unapplied VBS patch and execute its real reset block in cscript.

The harness replaces COM capture/output with calls to the extracted reset block;
ResetQueueWindow and ResetFarMeasurement are copied from the actual VBS source.
No simulator or production file is modified.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'scripts/run_real_world_stackelberg_controller.vbs'
PATCH=ROOT/'diagnostics/audit_snapshot_readonly.patch'


def patched_source():
    original=SOURCE.read_text(encoding='utf-8-sig').splitlines(keepends=True)
    if 'Sub WriteStateJson(simSec, path, resetWindows)\n' in original:
        return ''.join(original)
    patch=PATCH.read_text(encoding='utf-8').splitlines(keepends=True)
    out=[]; cursor=0; i=0
    while i<len(patch):
        match=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',patch[i])
        if not match:i+=1;continue
        start=int(match[1])-1
        out.extend(original[cursor:start]);cursor=start;i+=1
        while i<len(patch) and not patch[i].startswith('@@'):
            line=patch[i];prefix=line[:1]
            if prefix in (' ','-'):
                if original[cursor]!=line[1:]:raise AssertionError('Patch context differs from frozen VBS')
                cursor+=1
            if prefix in (' ','+'):out.append(line[1:])
            i+=1
    out.extend(original[cursor:])
    return ''.join(out)


def subroutine(source,name):
    return re.search(r'^Sub '+name+r'\([^\n]*\).*?^End Sub',source,re.M|re.S).group()


class ReadonlySnapshotTests(unittest.TestCase):
    def test_all_writer_calls_declare_consumption(self):
        source=patched_source()
        calls=re.findall(r'^\s*WriteStateJson\s+([^\n]+)',source,re.M)
        self.assertEqual(calls,['simSec, stateJsonPath, True','CLng(simSec), anchorPath, False'])
        body=subroutine(source,'WriteStateJson')
        self.assertIn('Sub WriteStateJson(simSec, path, resetWindows)',body)
        self.assertEqual(body.count('ResetQueueWindow'),1)
        self.assertEqual(body.count('ResetFarMeasurement'),1)
        self.assertLess(body.index('FarMeasurementJson()'),body.index('If resetWindows Then'))

    def test_actual_reset_helpers_preserve_audits_and_consume_decisions(self):
        source=patched_source()
        body=subroutine(source,'WriteStateJson')
        block=re.search(r'    If resetWindows Then\n.*?    End If',body,re.S).group()
        reset_queue=subroutine(source,'ResetQueueWindow')
        reset_far=subroutine(source,'ResetFarMeasurement')
        harness='''Option Explicit
Dim winDepart, winStoppedSum, winStoppedMax, winCountSum, winSamples, farFwExit, enabled
Set winDepart=CreateObject("Scripting.Dictionary")
Set winStoppedSum=CreateObject("Scripting.Dictionary")
Set winStoppedMax=CreateObject("Scripting.Dictionary")
Set winCountSum=CreateObject("Scripting.Dictionary")
enabled=True
winDepart("a")=5
winStoppedSum("a")=8
winStoppedMax("a")=4
winCountSum("a")=11
winSamples=3
farFwExit=7
Capture False
Assert winDepart("a")=5 And winStoppedSum("a")=8 And winStoppedMax("a")=4 And winCountSum("a")=11 And winSamples=3 And farFwExit=7, "audit mutated measurements"
winDepart("a")=winDepart("a")+2
winSamples=winSamples+1
farFwExit=farFwExit+3
Capture False
Assert winDepart("a")=7 And winSamples=4 And farFwExit=10, "repeated audit erased intervening samples"
Capture True
Assert winDepart.Count=0 And winStoppedSum.Count=0 And winStoppedMax.Count=0 And winCountSum.Count=0 And winSamples=0 And farFwExit=0, "decision failed to consume measurements"
enabled=False
winDepart("a")=2
winSamples=1
farFwExit=6
Capture True
Assert winDepart("a")=2 And winSamples=1 And farFwExit=0, "disabled queue behavior changed"
WScript.Echo "PASS readonly audit and consuming decision windows"
Sub Assert(condition,message)
    If Not condition Then
        WScript.Echo message
        WScript.Quit 1
    End If
End Sub
Function QueueWindowEnabled()
    QueueWindowEnabled=enabled
End Function
Sub Capture(resetWindows)
'''+block+'\nEnd Sub\n'+reset_queue+'\n'+reset_far+'\n'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'audit_window_test.vbs'
            path.write_text(harness,encoding='ascii')
            result=subprocess.run(['cscript.exe','//nologo',str(path)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('PASS readonly audit',result.stdout)


if __name__=='__main__':unittest.main()
