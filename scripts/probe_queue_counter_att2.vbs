Option Explicit
Dim Vissim, qc, i, v, args, n, cands, c, okList, simEnd
Set args = WScript.Arguments
Set Vissim = CreateObject("Vissim.Vissim")
Vissim.LoadNet args(0), False
WScript.Echo "LOADED counters=" & Vissim.Net.QueueCounters.Count

On Error Resume Next
Vissim.Evaluation.AttValue("QueuesCollectData") = True
Vissim.Evaluation.AttValue("QueuesFromTime") = 0
Vissim.Evaluation.AttValue("QueuesToTime") = 900
Vissim.Evaluation.AttValue("QueuesInterval") = 150
If Err.Number<>0 Then WScript.Echo "EVAL_SET_ERR " & Err.Description
Err.Clear
Vissim.Simulation.SetAttValue "SimPeriod", 620
If Err.Number<>0 Then
  WScript.Echo "SETATT_ERR " & Err.Description : Err.Clear
  Vissim.Simulation.AttValue("SimPeriod") = 620
  If Err.Number<>0 Then WScript.Echo "ATT_ERR " & Err.Description : Err.Clear
End If
Vissim.Simulation.SetAttValue "SimRes", 1
Err.Clear
Vissim.Simulation.SetAttValue "RandSeed", 13
Err.Clear
On Error GoTo 0
WScript.Echo "SIMPERIOD=" & Vissim.Simulation.AttValue("SimPeriod")

' 단일스텝으로 확실히 진행시킨다
Dim t
For i = 1 To 620
  On Error Resume Next
  Vissim.Simulation.RunSingleStep
  If Err.Number<>0 Then WScript.Echo "STEP_ERR at " & i & " " & Err.Description : Err.Clear : Exit For
  On Error GoTo 0
Next
t = Vissim.Simulation.AttValue("SimSec")
WScript.Echo "SIM_DONE t=" & t

' 카운터 하나를 잡고 후보 속성을 전수 시도
Set qc = Nothing
For Each c In Vissim.Net.QueueCounters
  Set qc = c
  Exit For
Next
If qc Is Nothing Then WScript.Echo "NO_COUNTER" : WScript.Quit 1
WScript.Echo "PROBE_COUNTER no=" & qc.AttValue("No") & " name=" & qc.AttValue("Name")

cands = Array( _
  "QLen(Current,Last)", "QLenMax(Current,Last)", "QStops(Current,Last)", _
  "QStops(Current,Last,All)", "QStopsAvg(Current,Last)", "NumVeh(Current,Last)", _
  "NumVehs(Current,Last)", "VehCount(Current,Last)", "QVehs(Current,Last)", _
  "QLenVeh(Current,Last)", "QueueLengthVeh(Current,Last)", "Vehs(Current,Last)", _
  "QStops", "No", "Name", "Link", "Pos", "Lane" )

For i = 0 To UBound(cands)
  On Error Resume Next
  v = qc.AttValue(cands(i))
  If Err.Number = 0 Then
    WScript.Echo "OK   " & cands(i) & " = " & CStr(v)
  Else
    WScript.Echo "FAIL " & cands(i) & " : " & Err.Description
  End If
  Err.Clear
  On Error GoTo 0
Next

' 비영 판독이 몇 개나 나오는지
Dim nz, tot
nz = 0 : tot = 0
On Error Resume Next
For Each c In Vissim.Net.QueueCounters
  tot = tot + 1
  v = c.AttValue("QLen(Current,Last)")
  If Err.Number = 0 Then
    If CDbl(v) > 0 Then nz = nz + 1
  End If
  Err.Clear
Next
On Error GoTo 0
WScript.Echo "NONZERO_QLEN=" & nz & "/" & tot
Vissim.Exit
