Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_detector_api.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim netPath
netPath = WScript.Arguments(0)

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"

Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "DETECTORS_BEFORE=" & SafeCount(Vissim.Net.Detectors)

Dim link, lane, det
Set link = Vissim.Net.Links.ItemByKey(1)
Set lane = link.Lanes.ItemByKey(1)

TryAddDetector "sig1_no_lane_pos_len", Array(0, lane, 20, 6)
TryAddDetector "sig2_no_lane_pos", Array(0, lane, 25)
TryAddDetector "sig3_no_link_lane_pos_len", Array(0, link, 1, 30, 6)
TryAddDetector "sig4_no_lane_pos_len_sc", Array(0, lane, 35, 6, Nothing)

WScript.Echo "DETECTORS_AFTER_IN_MEMORY=" & SafeCount(Vissim.Net.Detectors)
WScript.Echo "NOTE=Network was not saved."

Set Vissim = Nothing
WScript.Quit 0

Sub TryAddDetector(label, args)
    On Error Resume Next
    Dim d
    Set d = Nothing
    If label = "sig1_no_lane_pos_len" Then
        Set d = Vissim.Net.Detectors.AddDetector(args(0), args(1), args(2), args(3))
    ElseIf label = "sig2_no_lane_pos" Then
        Set d = Vissim.Net.Detectors.AddDetector(args(0), args(1), args(2))
    ElseIf label = "sig3_no_link_lane_pos_len" Then
        Set d = Vissim.Net.Detectors.AddDetector(args(0), args(1), args(2), args(3), args(4))
    ElseIf label = "sig4_no_lane_pos_len_sc" Then
        Set d = Vissim.Net.Detectors.AddDetector(args(0), args(1), args(2), args(3), args(4))
    End If

    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
    ElseIf d Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK NO=" & SafeAtt(d, "No") & " LINK=" & SafeAtt(d, "Link") & " LANE=" & SafeAtt(d, "Lane") & " POS=" & SafeAtt(d, "Pos") & " LENGTH=" & SafeAtt(d, "Length")
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
