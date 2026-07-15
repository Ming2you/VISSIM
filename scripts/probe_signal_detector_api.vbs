Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_signal_detector_api.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim netPath
netPath = WScript.Arguments(0)

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"

Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "SIGNAL_CONTROLLERS_BEFORE=" & SafeCount(Vissim.Net.SignalControllers)
WScript.Echo "DETECTORS_BEFORE=" & SafeCount(Vissim.Net.Detectors)

Dim sc, link, lane, det
Set sc = Nothing

TryAddSignalController "sc_sig1_no", 1
TryAddSignalController "sc_sig2_zero", 0
TryAddSignalControllerNoArgs "sc_sig3_noargs"

If Not sc Is Nothing Then
    On Error Resume Next
    sc.AttValue("Name") = "PROBE_SC"
    Err.Clear
    On Error GoTo 0
End If

Set link = Vissim.Net.Links.ItemByKey(1)
Set lane = link.Lanes.ItemByKey(1)

If Not sc Is Nothing Then
    TryAddDetector "det_sig_no_lane_pos", 0, lane, 20
    TrySetDetectorAttrs
End If

WScript.Echo "SIGNAL_CONTROLLERS_AFTER_IN_MEMORY=" & SafeCount(Vissim.Net.SignalControllers)
WScript.Echo "DETECTORS_AFTER_IN_MEMORY=" & SafeCount(Vissim.Net.Detectors)
WScript.Echo "NOTE=Network was not saved."

Set Vissim = Nothing
WScript.Quit 0

Sub TryAddSignalController(label, no)
    If Not sc Is Nothing Then Exit Sub
    On Error Resume Next
    Set sc = Vissim.Net.SignalControllers.AddSignalController(no)
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
        Set sc = Nothing
    ElseIf sc Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK NO=" & SafeAtt(sc, "No") & " NAME=" & SafeAtt(sc, "Name")
    End If
    On Error GoTo 0
End Sub

Sub TryAddSignalControllerNoArgs(label)
    If Not sc Is Nothing Then Exit Sub
    On Error Resume Next
    Set sc = Vissim.Net.SignalControllers.AddSignalController()
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
        Set sc = Nothing
    ElseIf sc Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK NO=" & SafeAtt(sc, "No") & " NAME=" & SafeAtt(sc, "Name")
    End If
    On Error GoTo 0
End Sub

Sub TryAddDetector(label, no, laneObj, pos)
    On Error Resume Next
    Set det = Vissim.Net.Detectors.AddDetector(no, laneObj, pos)
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
        Set det = Nothing
    ElseIf det Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK NO=" & SafeAtt(det, "No") & " SC=" & SafeAtt(det, "SC") & " LINK=" & SafeAtt(det, "Link") & " LANE=" & SafeAtt(det, "Lane") & " POS=" & SafeAtt(det, "Pos") & " LENGTH=" & SafeAtt(det, "Length") & " TYPE=" & SafeAtt(det, "Type")
    End If
    On Error GoTo 0
End Sub

Sub TrySetDetectorAttrs()
    If det Is Nothing Then Exit Sub
    TrySetAtt det, "Name", "PROBE_DET"
    TrySetAtt det, "Length", 6
    TrySetAtt det, "Type", 0
    TrySetAtt det, "PortNo", 901
    WScript.Echo "DETECTOR_AFTER_ATTRS NO=" & SafeAtt(det, "No") & " NAME=" & SafeAtt(det, "Name") & " SC=" & SafeAtt(det, "SC") & " POS=" & SafeAtt(det, "Pos") & " LENGTH=" & SafeAtt(det, "Length") & " TYPE=" & SafeAtt(det, "Type") & " PORT=" & SafeAtt(det, "PortNo")
End Sub

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

Function SafeCount(collection)
    On Error Resume Next
    SafeCount = collection.Count
    If Err.Number <> 0 Then
        SafeCount = "ERR:" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Function

Function SafeAtt(obj, att)
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(att))
    If Err.Number <> 0 Then
        SafeAtt = "ERR:" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Function
