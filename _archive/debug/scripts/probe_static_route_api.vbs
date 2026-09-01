Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript probe_static_route_api.vbs <network.inpx>"
    WScript.Quit 2
End If

Dim Vissim, netPath
netPath = WScript.Arguments(0)
Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet netPath, False
WScript.Echo "STAGE=NET_LOADED"
WScript.Echo "ROUTE_DECISIONS_BEFORE=" & Vissim.Net.VehicleRoutingDecisionsStatic.Count

Dim startLink, destLink, rd, route
Set startLink = Vissim.Net.Links.ItemByKey(1)
Set destLink = Vissim.Net.Links.ItemByKey(17)

TryAddDecision "rd_sig1_no_link_pos", 0, startLink, 30
If Not rd Is Nothing Then
    SetName rd, "PROBE_RD_AW_TO_CE"
    TrySetAtt rd, "CombineStaRoutDec", True
    TryAddRoute "route_sig1_no_dest_pos", rd, 0, destLink, 400
    TryAddRoute "route_sig2_no_dest", rd, 0, destLink, Null
End If

WScript.Echo "ROUTE_DECISIONS_AFTER_IN_MEMORY=" & Vissim.Net.VehicleRoutingDecisionsStatic.Count
WScript.Echo "NOTE=Network was not saved."
Set Vissim = Nothing
WScript.Quit 0

Sub TryAddDecision(label, no, linkObj, pos)
    On Error Resume Next
    Set rd = Vissim.Net.VehicleRoutingDecisionsStatic.AddVehicleRoutingDecisionStatic(no, linkObj, CDbl(pos))
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
        Set rd = Nothing
    ElseIf rd Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        WScript.Echo "TRY=" & label & " RESULT=OK NO=" & SafeAtt(rd, "No") & " LINK=" & SafeAtt(rd, "Link") & " POS=" & SafeAtt(rd, "Pos")
    End If
    On Error GoTo 0
End Sub

Sub TryAddRoute(label, rdObj, no, destLinkObj, destPos)
    On Error Resume Next
    Set route = Nothing
    If IsNull(destPos) Then
        Set route = rdObj.VehRoutSta.AddVehicleRouteStatic(no, destLinkObj)
    Else
        Set route = rdObj.VehRoutSta.AddVehicleRouteStatic(no, destLinkObj, CDbl(destPos))
    End If
    If Err.Number <> 0 Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL ERR=" & Err.Description
        Err.Clear
        Set route = Nothing
    ElseIf route Is Nothing Then
        WScript.Echo "TRY=" & label & " RESULT=FAIL_NULL"
    Else
        SetName route, "PROBE_ROUTE"
        TrySetAtt route, "RelFlow(1)", 1
        WScript.Echo "TRY=" & label & " RESULT=OK NO=" & SafeAtt(route, "No") & " DEST=" & SafeAtt(route, "DestLink") & " DESTPOS=" & SafeAtt(route, "DestPos") & " RELFLOW=" & SafeAtt(route, "RelFlow(1)") & " LINKSEQ=" & SafeAtt(route, "LinkSeq")
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
