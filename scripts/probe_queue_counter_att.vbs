Option Explicit
Dim Vissim, net, qc, i, cand, v, ok, args, simTo
Set args = WScript.Arguments
Set Vissim = CreateObject("Vissim.Vissim")
Vissim.LoadNet args(0), False
WScript.Echo "LOADED counters=" & Vissim.Net.QueueCounters.Count
' 평가 켜기 — ReadOnlyDuringSim 이라 시뮬 전에
On Error Resume Next
Vissim.Evaluation.AttValue("QueuesCollectData") = True
If Err.Number<>0 Then WScript.Echo "SET_FAIL QueuesCollectData " & Err.Description
Err.Clear
Vissim.Evaluation.AttValue("QueuesFromTime") = 0
Vissim.Evaluation.AttValue("QueuesToTime") = 600
Vissim.Evaluation.AttValue("QueuesInterval") = 150
If Err.Number<>0 Then WScript.Echo "SET_FAIL Queues* " & Err.Description
Err.Clear
On Error GoTo 0
Vissim.Simulation.AttValue("SimPeriod") = 400
Vissim.Simulation.AttValue("SimRes") = 1
Vissim.Simulation.AttValue("RandSeed") = 13
Vissim.Simulation.RunContinuous
WScript.Echo "SIM_DONE t=" & Vissim.Simulation.AttValue("SimSec")
' 속성 목록 덤프
On Error Resume Next
Dim atts, a
Set atts = Vissim.Net.QueueCounters.Attributes.GetAll
If Err.Number = 0 Then
    For i = 0 To UBound(atts)
        WScript.Echo "ATT " & atts(i)(0) & " | " & atts(i)(1)
    Next
Else
    WScript.Echo "ATTLIST_FAIL " & Err.Description
End If
Err.Clear
On Error GoTo 0
' 후보 표기 시험
Set qc = Vissim.Net.QueueCounters.ItemByKey(1)
cand = Array("QLen(Current,Last,All)", "QLen(Current, Last, All)", "QLen(Current,Last)", "QLen", _
             "QLenMax(Current,Last,All)", "QLenMax(Current,Last)", "QLenMax", _
             "QLen(1,Last,All)", "QLen(Current,1,All)", "QLen(Avg,Last,All)")
For i = 0 To UBound(cand)
    On Error Resume Next
    v = qc.AttValue(cand(i))
    If Err.Number = 0 Then
        WScript.Echo "OK   " & cand(i) & " = " & CStr(v)
    Else
        WScript.Echo "FAIL " & cand(i) & " : " & Err.Description
    End If
    Err.Clear
    On Error GoTo 0
Next
Vissim.Exit
