' 재작성한 .sig 가 VISSIM 안에서 실제로 몇 초 주기로 도는지 SG 상태를 초당 받아 잰다
Option Explicit
Dim inpx, outCsv, secs, i, t, v, sc, sg, no, buf, fso, ts, targets, scDict, key, simSec
inpx   = WScript.Arguments(0)
outCsv = WScript.Arguments(1)
secs   = CLng(WScript.Arguments(2))

targets = Array("1","5","6","11","12","101","105","107","108","109","1001","1002","1003","1004","1005")

Set v = CreateObject("Vissim.Vissim")
v.LoadNet inpx, False
WScript.Echo "LOAD_OK"

v.Simulation.AttValue("SimPeriod") = CDbl(secs) + 5
v.Simulation.AttValue("SimRes") = 1
On Error Resume Next
v.Simulation.AttValue("UseMaxSimSpeed") = True
v.SuspendUpdateGUI
On Error GoTo 0

Set scDict = CreateObject("Scripting.Dictionary")
For Each sc In v.Net.SignalControllers
    no = CStr(sc.AttValue("No"))
    For i = 0 To UBound(targets)
        If targets(i) = no Then scDict.Add no, sc
    Next
Next
WScript.Echo "SC_FOUND=" & scDict.Count

Set fso = CreateObject("Scripting.FileSystemObject")
Set ts = fso.CreateTextFile(outCsv, True)
ts.WriteLine "simsec,sc,states"

For t = 1 To secs
    v.Simulation.RunSingleStep
    simSec = v.Simulation.AttValue("SimSec")
    For i = 0 To UBound(targets)
        key = targets(i)
        If scDict.Exists(key) Then
            buf = ""
            For Each sg In scDict.Item(key).SGs
                buf = buf & Left(CStr(sg.AttValue("SigState")), 1)
            Next
            ts.WriteLine simSec & "," & key & "," & buf
        End If
    Next
    If (t Mod 100) = 0 Then WScript.Echo "PROGRESS t=" & t & " simsec=" & simSec
Next
ts.Close
WScript.Echo "WROTE=" & outCsv
On Error Resume Next
v.Exit
On Error GoTo 0
WScript.Echo "DONE"
