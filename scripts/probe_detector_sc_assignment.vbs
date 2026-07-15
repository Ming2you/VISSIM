Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_detector_sc_assignment.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim Vissim, netPath
netPath = WScript.Arguments(0)
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"

Dim sc1, sc2, link, lane, det
Set sc1 = Vissim.Net.SignalControllers.AddSignalController(1)
sc1.AttValue("Name") = "PROBE_SC_1"
Set sc2 = Vissim.Net.SignalControllers.AddSignalController(2)
sc2.AttValue("Name") = "PROBE_SC_2"
WScript.Echo "SC1=" & SafeAtt(sc1, "No") & " SC2=" & SafeAtt(sc2, "No")

Set link = Vissim.Net.Links.ItemByKey(1)
Set lane = link.Lanes.ItemByKey(1)
Set det = Vissim.Net.Detectors.AddDetector(0, lane, 20)
det.AttValue("Name") = "PROBE_DET_SC"
WScript.Echo "DET_INITIAL SC=" & SafeAtt(det, "SC")

TrySetAtt det, "SC", 2
WScript.Echo "DET_AFTER_SC_NUM SC=" & SafeAtt(det, "SC")

TrySetAtt det, "SC", sc1
WScript.Echo "DET_AFTER_SC_OBJ SC=" & SafeAtt(det, "SC")

WScript.Echo "NOTE=Network was not saved."
Set Vissim = Nothing
WScript.Quit 0

Sub TrySetAtt(obj, att, value)
    On Error Resume Next
    obj.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "TRY_SET " & att & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
    Else
        WScript.Echo "TRY_SET " & att & " RESULT=OK"
    End If
    On Error GoTo 0
End Sub

Function SafeAtt(obj, att)
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(att))
    If Err.Number <> 0 Then
        SafeAtt = "ERR:" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Function
