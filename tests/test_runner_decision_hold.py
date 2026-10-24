"""Inject pre-write failures into the actual VBS decision subroutine (no COM)."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Windows Script Host')
class RunnerDecisionHoldTests(unittest.TestCase):
    def run_case(self, *, enabled=True, prior=True, apply_ok=True, hold_ok=True):
        source=(ROOT/'scripts/run_real_world_stackelberg_controller.vbs').read_text(encoding='utf-8-sig')
        block=re.search(r'(?ms)^Sub RunControllerDecision\(.*?^End Sub\s*$',source)[0]
        with tempfile.TemporaryDirectory(prefix='decision hold ') as tmp:
            folder=Path(tmp)
            script=folder/'test.vbs'
            text='''Option Explicit
Dim fso, decisionDir, obs150Mode, controllerName, controlStartSec, warmupControllerName
Dim pythonExe,adapterPath,mappingPath,detectorMappingPath,calibrationPath,tuningPath
Dim lastActionJson,adapterMode,RW_COMMAND_REPLAY_DIR,RW_OFFSET_WRITER,RW_ALLOWED_VSL_SPEEDS
Dim decisionsFailed,decisionsOk,decisionsHeld,calls,applies,Vissim,stateFile,actionFile
Dim bottleneckLinkFile,bottleneckSegmentFile,signalTraceFile,vslTraceFile,vslTraceOutPath
Set fso=CreateObject("Scripting.FileSystemObject")
decisionDir="TMP"
obs150Mode=False: controllerName="wu-link":controlStartSec=900:warmupControllerName="no-control"
pythonExe="python":adapterPath="adapter":mappingPath="map":detectorMappingPath=""
calibrationPath="":tuningPath="":RW_COMMAND_REPLAY_DIR="":RW_OFFSET_WRITER="experiment"
lastActionJson="PRIOR":decisionsFailed=0:decisionsOk=0:decisionsHeld=0:calls=0:applies=0
RunControllerDecision 900
RunControllerDecision 1050
WScript.Echo "CHECK=" & decisionsFailed & "," & decisionsHeld & "," & decisionsOk & "," & applies & "," & lastActionJson
Function EnvText(k)
 EnvText=""
 If k="RW_DECISION_HOLD_PREVIOUS" Then EnvText="ENABLED"
 If k="RW_DECISION_TIMEOUT_SEC" Then EnvText="1800"
 If k="RW_DECISION_FAIL_FAST" Then EnvText="1"
End Function
Function RunCapture3Timeout(cmd, limit, ByRef o, ByRef e)
 Dim f,t
 o="":e="injected controller failure"
 calls=calls+1
 If calls=1 Then
  RunCapture3Timeout=7:Exit Function
 End If
 If InStr(cmd,"--hold-previous-action")>0 And Not HOLDOK Then
  RunCapture3Timeout=8:Exit Function
 End If
 For Each t In Array(900,1050)
  Set f=fso.CreateTextFile(fso.BuildPath(decisionDir,"action_" & Pad6(t) & ".json"),True):f.Close
  Set f=fso.CreateTextFile(fso.BuildPath(decisionDir,"action_" & Pad6(t) & ".csv"),True):f.Close
 Next
 If calls=2 Then o="HOLD_NATIVE_SIGNALS=1"
 RunCapture3Timeout=0
End Function
Function RunCapture3(cmd, ByRef o, ByRef e)
 RunCapture3=RunCapture3Timeout(cmd,0,o,e)
End Function
Function ApplyActionCsv(t,p,c)
 applies=applies+1
 If applies=1 And c<>"no-control" Then Err.Raise 513,,"Warmup ownership was lost"
 ApplyActionCsv=APPLYOK
End Function
Sub WriteStateJson(t,p,r)
End Sub
Sub PerfAdd(k,t)
End Sub
Function PerfNow():PerfNow=0:End Function
Function ElapsedSec(t):ElapsedSec=0:End Function
Function OneLine(t):OneLine=t:End Function
Function Pad6(t):Pad6=Right("000000" & t,6):End Function
Function Q(t):Q=Chr(34) & t & Chr(34):End Function
'''.replace('TMP',str(folder)).replace('PRIOR','prior.json' if prior else '').replace('ENABLED','1' if enabled else '0').replace('HOLDOK',str(hold_ok)).replace('APPLYOK',str(apply_ok))
            script.write_text(text+'\n'+block,encoding='utf-16')
            return subprocess.run(['cscript.exe','//nologo',str(script)],capture_output=True,text=True,encoding='mbcs',timeout=10)

    def test_recovery_then_next_decision_resumes(self):
        r=self.run_case()
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('CHECK=1,1,1,2,',r.stdout)
        self.assertIn('action_001050.json',r.stdout)

    def test_partial_application_failure_still_stops(self):
        r=self.run_case(apply_ok=False)
        self.assertEqual(r.returncode,3,r.stdout+r.stderr)
        self.assertNotIn('CHECK=',r.stdout)

    def test_missing_prior_failed_hold_and_disabled_policy_stop(self):
        for args in (dict(prior=False),dict(hold_ok=False),dict(enabled=False)):
            r=self.run_case(**args)
            self.assertEqual(r.returncode,3,r.stdout+r.stderr)


if __name__=='__main__':unittest.main()
