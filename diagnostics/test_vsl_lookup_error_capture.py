"""Execute the actual VBS lookup with controlled failures; no live VISSIM."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VslLookupCapture(unittest.TestCase):
    def test_success_stale_error_missing_busy_and_null(self):
        source = (ROOT/'scripts/run_real_world_stackelberg_controller.vbs').read_text(encoding='utf-8')
        lookup = re.search(r'(?ms)^Function LookupVslDecision\(.*?^End Function', source).group()
        script = r'''
Option Explicit
Dim Vissim, mode, item, ok
Class Collection
    Public Function ItemByKey(key)
        If mode = "missing" Then Err.Raise 513, "lookup-test", "missing key"
        If mode = "busy" Then Err.Raise -2147418111, "lookup-test", "call rejected"
        If mode = "blank" Then Err.Raise -2147418111, "lookup-test", ""
        If mode = "null" Then
            Set ItemByKey = Nothing
        Else
            Set ItemByKey = CreateObject("Scripting.Dictionary")
        End If
    End Function
End Class
Class Network
    Public DesSpeedDecisions
    Private Sub Class_Initialize()
        Set DesSpeedDecisions = New Collection
    End Sub
End Class
Class Application
    Public Net
    Private Sub Class_Initialize()
        Set Net = New Network
    End Sub
End Class
Function OneLine(value)
    OneLine = CStr(value)
End Function
Set Vissim = New Application
mode = "ok"
If Not LookupVslDecision(1350, 39, item) Then WScript.Quit 2
On Error Resume Next
Err.Raise 513, "earlier-operation", "unrelated"
ok = LookupVslDecision(1350, 39, item)
On Error GoTo 0
If Not ok Then WScript.Quit 3
For Each mode In Array("missing", "busy", "blank", "null")
    Set item = CreateObject("Scripting.Dictionary")
    ok = LookupVslDecision(1350, 39, item)
    If ok Then WScript.Quit 4
    If Not (item Is Nothing) Then WScript.Quit 5
Next
WScript.Echo "PASS"
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'lookup.vbs'
            path.write_text(script+'\n'+lookup, encoding='utf-16')
            result = subprocess.run(['cscript.exe', '//nologo', str(path)], capture_output=True,
                                    text=True, encoding='mbcs', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('err_no=513 err_hex=201 source=lookup-test err=missing key', result.stdout)
        self.assertIn('err_no=-2147418111 err_hex=80010001 source=lookup-test err=call rejected', result.stdout)
        self.assertIn('ERROR=VSL_DSD_NULL_OBJECT sim_sec=1350 dsd=39', result.stdout)
        self.assertIn('PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
