Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_signal_head_api.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim Vissim, netPath
netPath = WScript.Arguments(0)
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "SC_COUNT=" & Vissim.Net.SignalControllers.Count
WScript.Echo "SIGNAL_HEADS_BEFORE=" & Vissim.Net.SignalHeads.Count

Dim sc, sg, sh, link, lane
Set sg = Nothing
Set sh = Nothing
Set sc = Vissim.Net.SignalControllers.ItemByKey(1)
WScript.Echo "SC1 NO=" & SafeAtt(sc, "No") & " NAME=" & SafeAtt(sc, "Name") & " TYPE=" & SafeAtt(sc, "Type") & " ACTIVE=" & SafeAtt(sc, "Active") & " SGCOUNT=" & SafeCount(sc.SGs)

TryAddSignalGroup "sg_sig1_no", sc, 1
TryAddSignalGroup "sg_sig2_zero", sc, 0
TryAddSignalGroupNoArgs "sg_sig3_noargs", sc

If Not sg Is Nothing Then
    SetName sg, "PROBE_SG_1"
    WScript.Echo "SG_AFTER_NAME NO=" & SafeAtt(sg, "No") & " NAME=" & SafeAtt(sg, "Name") & " SIGSTATE=" & SafeAtt(sg, "SigState")
    TrySetAtt sg, "SigState", "GREEN"
    TrySetAtt sg, "SigState", "RED"
    TrySetAtt sg, "State", "GREEN"
End If

Set link = Vissim.Net.Links.ItemByKey(1)
Set lane = link.Lanes.ItemByKey(1)

If Not sg Is Nothing Then
    TryAddSignalHead "sh_sig1_no_lane_pos", 0, lane, 470, Null, Null
    TryAddSignalHead "sh_sig2_no_lane_pos_sc_sg_nums", 0, lane, 465, 1, 1
    If Not sh Is Nothing Then
        SetName sh, "PROBE_SH"
        TrySetAtt sh, "SC", 1
        TrySetAtt sh, "SG", 1
        TrySetAtt sh, "Type", "CIRCULAR"
        WScript.Echo "SH_AFTER_ATTRS NO=" & SafeAtt(sh, "No") & " NAME=" & SafeAtt(sh, "Name") & " LANE=" & SafeAtt(sh, "Lane") & " POS=" & SafeAtt(sh, "Pos") & " SC=" & SafeAtt(sh, "SC") & " SG=" & SafeAtt(sh, "SG") & " SIGSTATE=" & SafeAtt(sh, "SigState")
    End If
End If

WScript.Echo "SIGNAL_HEADS_AFTER_IN_MEMORY=" & Vissim.Net.SignalHeads.Count
WScript.Echo "NOTE=Network was not saved."
Set Vissim = Nothing
WScript.Quit 0

Sub TryAddSignalGroup(label, scObj, no)
    If Not sg Is Nothing Then Exit Sub
    On Error Resume Next
    Set sg = scObj.SGs.AddSignalGroup(no)
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
        Set sg = Nothing
    ElseIf sg Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK NO=" & SafeAtt(sg, "No") & " NAME=" & SafeAtt(sg, "Name") & " SIGSTATE=" & SafeAtt(sg, "SigState")
    End If
    On Error GoTo 0
End Sub

Sub TryAddSignalGroupNoArgs(label, scObj)
    If Not sg Is Nothing Then Exit Sub
    On Error Resume Next
    Set sg = scObj.SGs.AddSignalGroup()
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
        Set sg = Nothing
    ElseIf sg Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK NO=" & SafeAtt(sg, "No") & " NAME=" & SafeAtt(sg, "Name") & " SIGSTATE=" & SafeAtt(sg, "SigState")
    End If
    On Error GoTo 0
End Sub

Sub TryAddSignalHead(label, no, laneObj, pos, scNo, sgNo)
    If Not sh Is Nothing Then Exit Sub
    On Error Resume Next
    If IsNull(scNo) Then
        Set sh = Vissim.Net.SignalHeads.AddSignalHead(no, laneObj, CDbl(pos))
    Else
        Set sh = Vissim.Net.SignalHeads.AddSignalHead(no, laneObj, CDbl(pos), CLng(scNo), CLng(sgNo))
    End If
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
        Set sh = Nothing
    ElseIf sh Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK NO=" & SafeAtt(sh, "No") & " LANE=" & SafeAtt(sh, "Lane") & " POS=" & SafeAtt(sh, "Pos") & " SC=" & SafeAtt(sh, "SC") & " SG=" & SafeAtt(sh, "SG")
    End If
    On Error GoTo 0
End Sub

Sub SetName(obj, name)
    On Error Resume Next
    obj.AttValue("Name") = name
    Err.Clear
    On Error GoTo 0
End Sub

Sub TrySetAtt(obj, att, value)
    On Error Resume Next
    obj.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "TRY_SET " & att & "=" & CStr(value) & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
    Else
        WScript.Echo "TRY_SET " & att & "=" & CStr(value) & " RESULT=OK"
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
