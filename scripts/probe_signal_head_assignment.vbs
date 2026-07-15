Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_signal_head_assignment.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim Vissim, netPath
netPath = WScript.Arguments(0)
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"

Dim sc, sg1, sg2, link, lane, sh
Set sc = Vissim.Net.SignalControllers.ItemByKey(1)
Set sg1 = sc.SGs.AddSignalGroup(1)
sg1.AttValue("Name") = "PROBE_SG_1"
Set sg2 = sc.SGs.AddSignalGroup(2)
sg2.AttValue("Name") = "PROBE_SG_2"
WScript.Echo "SG1=" & SafeAtt(sg1, "No") & " SG2=" & SafeAtt(sg2, "No")

Set link = Vissim.Net.Links.ItemByKey(1)
Set lane = link.Lanes.ItemByKey(1)

Set sh = Vissim.Net.SignalHeads.AddSignalHead(0, lane, 470)
sh.AttValue("Name") = "PROBE_SH_ASSIGN"
WScript.Echo "SH_INITIAL SG=" & SafeAtt(sh, "SG")

TrySetAtt sh, "SG", "1-2"
WScript.Echo "SH_AFTER_SG_STRING SG=" & SafeAtt(sh, "SG")

TrySetAtt sh, "SG", sg2
WScript.Echo "SH_AFTER_SG_OBJECT SG=" & SafeAtt(sh, "SG")

Set sh = Nothing
TryAddSignalHeadWithSg "sh_sig2_no_lane_pos_sgobj", 0, lane, 465, sg2
TryAddSignalHeadWithScSg "sh_sig3_no_lane_pos_sc_sgobj", 0, lane, 460, sc, sg2

WScript.Echo "SIGNAL_HEADS_AFTER_IN_MEMORY=" & Vissim.Net.SignalHeads.Count
WScript.Echo "NOTE=Network was not saved."
Set Vissim = Nothing
WScript.Quit 0

Sub TryAddSignalHeadWithSg(label, no, laneObj, pos, sgObj)
    On Error Resume Next
    Dim head
    Set head = Vissim.Net.SignalHeads.AddSignalHead(no, laneObj, CDbl(pos), sgObj)
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
    ElseIf head Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK SG=" & SafeAtt(head, "SG")
    End If
    On Error GoTo 0
End Sub

Sub TryAddSignalHeadWithScSg(label, no, laneObj, pos, scObj, sgObj)
    On Error Resume Next
    Dim head
    Set head = Vissim.Net.SignalHeads.AddSignalHead(no, laneObj, CDbl(pos), scObj, sgObj)
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
    ElseIf head Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK SG=" & SafeAtt(head, "SG")
    End If
    On Error GoTo 0
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

Function SafeAtt(obj, att)
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(att))
    If Err.Number <> 0 Then
        SafeAtt = "ERR:" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Function
