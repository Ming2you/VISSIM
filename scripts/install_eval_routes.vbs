Option Explicit

If WScript.Arguments.Count < 5 Then
    WScript.Echo "Usage: cscript install_eval_routes.vbs <source.inpx> <source.layx> <target.inpx> <target.layx> <manifest.csv>"
    WScript.Quit 2
End If

Dim sourceNet, sourceLayout, targetNet, targetLayout, manifestPath
sourceNet = WScript.Arguments(0)
sourceLayout = WScript.Arguments(1)
targetNet = WScript.Arguments(2)
targetLayout = WScript.Arguments(3)
manifestPath = WScript.Arguments(4)

Dim fso, manifest, Vissim, currentRd, currentOrigin, successRoutes, failedRoutes
Set fso = CreateObject("Scripting.FileSystemObject")
EnsureParentFolder manifestPath
Set manifest = fso.CreateTextFile(manifestPath, True)
manifest.WriteLine "object_type,status,origin,decision_name,decision_no,start_link,start_pos,route_name,route_no,dest_label,dest_link,dest_pos,rel_flow,link_seq,error"
successRoutes = 0
failedRoutes = 0

Set Vissim = CreateObject("Vissim.Vissim")
WScript.Echo "STAGE=COM_CREATED"
Vissim.LoadNet sourceNet, False
WScript.Echo "STAGE=SOURCE_NET_LOADED"

On Error Resume Next
Vissim.LoadLayout sourceLayout
If Err.Number <> 0 Then
    WScript.Echo "WARN=SOURCE_LAYOUT_LOAD_FAILED err=" & Err.Description
    Err.Clear
Else
    WScript.Echo "STAGE=SOURCE_LAYOUT_LOADED"
End If
On Error GoTo 0

On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.SuspendUpdateGUI
Err.Clear
On Error GoTo 0

WScript.Echo "COUNTS_BEFORE RD=" & Vissim.Net.VehicleRoutingDecisionsStatic.Count

AddOriginRoutes

WScript.Echo "COUNTS_AFTER_IN_MEMORY RD=" & Vissim.Net.VehicleRoutingDecisionsStatic.Count & " ROUTES_OK=" & successRoutes & " ROUTES_FAIL=" & failedRoutes

EnsureParentFolder targetNet
EnsureParentFolder targetLayout
Vissim.SaveNetAs targetNet
Vissim.SaveLayout targetLayout
manifest.Close

On Error Resume Next
Vissim.ResumeUpdateGUI True
Err.Clear
On Error GoTo 0

WScript.Echo "STAGE=SAVED"
WScript.Echo "TARGET_NET=" & targetNet
WScript.Echo "TARGET_LAYOUT=" & targetLayout
WScript.Echo "MANIFEST=" & manifestPath

Set Vissim = Nothing
WScript.Quit 0

Sub AddOriginRoutes()
    ' Urban/boundary origins. Destination set mixes boundary exits and freeway/ramp access.
    BeginDecision "AW", "EVAL_RD_AW_IN", 1, 30
    AddRoute "AN", 4, 400, 1
    AddRoute "BN", 10, 400, 1
    AddRoute "CN", 16, 400, 1
    AddRoute "CE", 17, 450, 1.2
    AddRoute "DW", 22, 450, 0.8
    AddRoute "FE", 29, 450, 1.2
    AddRoute "FW_EB", 33, 2600, 0.8
    AddRoute "FW_WB", 34, 2600, 0.8

    BeginDecision "AN", "EVAL_RD_AN_IN", 3, 30
    AddRoute "AW", 2, 450, 1
    AddRoute "BN", 10, 400, 1
    AddRoute "CN", 16, 400, 1
    AddRoute "CE", 17, 450, 1.2
    AddRoute "DW", 22, 450, 0.8
    AddRoute "FE", 29, 450, 1
    AddRoute "FW_EB", 33, 2600, 0.7
    AddRoute "FW_WB", 34, 2600, 0.7

    BeginDecision "BN", "EVAL_RD_BN_IN", 9, 30
    AddRoute "AW", 2, 450, 1
    AddRoute "AN", 4, 400, 1
    AddRoute "CN", 16, 400, 1
    AddRoute "CE", 17, 450, 1.1
    AddRoute "DW", 22, 450, 0.9
    AddRoute "FE", 29, 450, 1.1
    AddRoute "FW_EB", 33, 2600, 0.8
    AddRoute "FW_WB", 34, 2600, 0.8

    BeginDecision "CN", "EVAL_RD_CN_IN", 15, 30
    AddRoute "AW", 2, 450, 1.1
    AddRoute "AN", 4, 400, 1
    AddRoute "BN", 10, 400, 1
    AddRoute "CE", 17, 450, 0.8
    AddRoute "DW", 22, 450, 1
    AddRoute "FE", 29, 450, 1.1
    AddRoute "FW_EB", 33, 2600, 0.7
    AddRoute "FW_WB", 34, 2600, 0.7

    BeginDecision "CE", "EVAL_RD_CE_IN", 18, 30
    AddRoute "AW", 2, 450, 1.2
    AddRoute "AN", 4, 400, 1
    AddRoute "BN", 10, 400, 1
    AddRoute "CN", 16, 400, 0.8
    AddRoute "DW", 22, 450, 1
    AddRoute "FE", 29, 450, 1
    AddRoute "FW_EB", 33, 2600, 0.7
    AddRoute "FW_WB", 34, 2600, 0.7

    BeginDecision "DW", "EVAL_RD_DW_IN", 21, 30
    AddRoute "AW", 2, 450, 0.8
    AddRoute "AN", 4, 400, 1
    AddRoute "BN", 10, 400, 1
    AddRoute "CN", 16, 400, 1
    AddRoute "CE", 17, 450, 1.1
    AddRoute "FE", 29, 450, 1.2
    AddRoute "FW_EB", 33, 2600, 1
    AddRoute "FW_WB", 34, 2600, 1

    BeginDecision "FE", "EVAL_RD_FE_IN", 30, 30
    AddRoute "AW", 2, 450, 1.2
    AddRoute "AN", 4, 400, 1
    AddRoute "BN", 10, 400, 1
    AddRoute "CN", 16, 400, 1
    AddRoute "CE", 17, 450, 0.8
    AddRoute "DW", 22, 450, 1.1
    AddRoute "FW_EB", 33, 2600, 1
    AddRoute "FW_WB", 34, 2600, 1

    ' Freeway origins. Same-link destination is the through movement.
    BeginDecision "FW_EB", "EVAL_RD_FW_EB_IN", 33, 80
    AddRoute "FW_EB_THROUGH", 33, 2800, 3
    AddRoute "D_OFF_TO_DW", 22, 450, 0.7
    AddRoute "D_OFF_TO_AN", 4, 400, 0.5
    AddRoute "F_OFF_TO_FE", 29, 450, 0.7
    AddRoute "F_OFF_TO_CE", 17, 450, 0.5
    AddRoute "URBAN_TO_CN", 16, 400, 0.4

    BeginDecision "FW_WB", "EVAL_RD_FW_WB_IN", 34, 80
    AddRoute "FW_WB_THROUGH", 34, 2800, 3
    AddRoute "F_OFF_TO_FE", 29, 450, 0.7
    AddRoute "F_OFF_TO_CN", 16, 400, 0.5
    AddRoute "D_OFF_TO_DW", 22, 450, 0.7
    AddRoute "D_OFF_TO_AW", 2, 450, 0.5
    AddRoute "URBAN_TO_AN", 4, 400, 0.4
End Sub

Sub BeginDecision(origin, name, startLinkNo, startPos)
    Dim link
    currentOrigin = origin
    Set link = Vissim.Net.Links.ItemByKey(CLng(startLinkNo))
    Set currentRd = Vissim.Net.VehicleRoutingDecisionsStatic.AddVehicleRoutingDecisionStatic(0, link, CDbl(startPos))
    SetName currentRd, name
    TrySetAtt currentRd, "CombineStaRoutDec", True
    TrySetAtt currentRd, "AllVehTypes", True
    WriteDecisionManifest "vehicleRoutingDecisionStatic", "OK", origin, name, SafeAtt(currentRd, "No"), startLinkNo, startPos, "", "", "", "", "", "", "", ""
End Sub

Sub AddRoute(destLabel, destLinkNo, destPos, relFlow)
    Dim destLink, route, routeName, errText
    If currentRd Is Nothing Then Exit Sub
    Set destLink = Vissim.Net.Links.ItemByKey(CLng(destLinkNo))
    routeName = "EVAL_ROUTE_" & currentOrigin & "_TO_" & destLabel
    On Error Resume Next
    Set route = currentRd.VehRoutSta.AddVehicleRouteStatic(0, destLink, CDbl(destPos))
    If Err.Number <> 0 Then
        errText = Err.Description
        Err.Clear
        failedRoutes = failedRoutes + 1
        WriteDecisionManifest "vehicleRouteStatic", "FAIL", currentOrigin, SafeAtt(currentRd, "Name"), SafeAtt(currentRd, "No"), SafeAtt(currentRd, "Link"), SafeAtt(currentRd, "Pos"), routeName, "", destLabel, destLinkNo, destPos, relFlow, "", errText
        On Error GoTo 0
        Exit Sub
    End If
    On Error GoTo 0

    SetName route, routeName
    TrySetAtt route, "RelFlow(1)", CDbl(relFlow)
    successRoutes = successRoutes + 1
    WriteDecisionManifest "vehicleRouteStatic", "OK", currentOrigin, SafeAtt(currentRd, "Name"), SafeAtt(currentRd, "No"), SafeAtt(currentRd, "Link"), SafeAtt(currentRd, "Pos"), routeName, SafeAtt(route, "No"), destLabel, destLinkNo, destPos, relFlow, SafeAtt(route, "LinkSeq"), ""
End Sub

Sub SetName(obj, name)
    On Error Resume Next
    obj.AttValue("Name") = name
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_NAME name=" & name & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Sub TrySetAtt(obj, att, value)
    On Error Resume Next
    obj.AttValue(att) = value
    If Err.Number <> 0 Then
        WScript.Echo "WARN=FAILED_SET_ATT att=" & att & " value=" & CStr(value) & " err=" & Err.Description
        Err.Clear
    End If
    On Error GoTo 0
End Sub

Function SafeAtt(obj, att)
    On Error Resume Next
    SafeAtt = CStr(obj.AttValue(att))
    If Err.Number <> 0 Then
        SafeAtt = ""
        Err.Clear
    End If
    On Error GoTo 0
End Function

Sub WriteDecisionManifest(objectType, status, origin, decisionName, decisionNo, startLink, startPos, routeName, routeNo, destLabel, destLink, destPos, relFlow, linkSeq, errorText)
    manifest.WriteLine Csv(objectType) & "," & Csv(status) & "," & Csv(origin) & "," & Csv(decisionName) & "," & Csv(decisionNo) & "," & Csv(startLink) & "," & Csv(startPos) & "," & Csv(routeName) & "," & Csv(routeNo) & "," & Csv(destLabel) & "," & Csv(destLink) & "," & Csv(destPos) & "," & Csv(relFlow) & "," & Csv(linkSeq) & "," & Csv(errorText)
End Sub

Function Csv(value)
    Dim text
    text = CStr(value)
    text = Replace(text, """", """""")
    Csv = """" & text & """"
End Function

Sub EnsureParentFolder(path)
    Dim parent
    parent = fso.GetParentFolderName(path)
    If parent <> "" And Not fso.FolderExists(parent) Then
        EnsureParentFolder parent
        fso.CreateFolder parent
    End If
End Sub
