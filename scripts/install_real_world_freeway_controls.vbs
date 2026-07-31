Option Explicit

' Add a real-world freeway control layer to the Gaepo modi network.
' The source network is not modified. The target network receives:
'   * 8 VSL segment-start desired-speed decisions per freeway direction and lane
'   * 8 physical ramp-meter signal controllers on on-ramp connectors
'
' Freeway links follow the user-provided geometry hint:
'   link 2  -> model FW_E
'   link 26 -> model FW_W
'
' Ramp meter targets intentionally exclude connector 10699 (link 74 -> 2),
' because it behaves like a freeway feeder/mainline entry rather than an
' isolated ramp merge.

If WScript.Arguments.Count < 5 Then
    WScript.Echo "Usage: cscript install_real_world_freeway_controls.vbs <source.inpx> <source.layx> <target.inpx> <target.layx> <manifest.csv>"
    WScript.Quit 2
End If

Dim sourceNet, sourceLayout, targetNet, targetLayout, manifestPath
sourceNet = WScript.Arguments(0)
sourceLayout = WScript.Arguments(1)
targetNet = WScript.Arguments(2)
targetLayout = WScript.Arguments(3)
manifestPath = WScript.Arguments(4)

Dim fso, manifest, Vissim
Set fso = CreateObject("Scripting.FileSystemObject")
EnsureParentFolder manifestPath
Set manifest = fso.CreateTextFile(manifestPath, True)
manifest.WriteLine "object_type,category,control_id,segment_id,model_link,model_segment_index,direction,name,no,link,lane,pos,segment_start_m,segment_end_m,default_speed_kph,veh_classes,sc_no,sg_no,connector,from_link,from_pos,to_link,to_pos,default_green_sec,capacity_vph,model_ramp_key,purpose"

Set Vissim = CreateVissimCom()
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

WScript.Echo "COUNTS_BEFORE DSD=" & Vissim.Net.DesSpeedDecisions.Count & " SC=" & Vissim.Net.SignalControllers.Count & " SH=" & Vissim.Net.SignalHeads.Count

InstallVslSegments "FW_E", "E", 2
InstallVslSegments "FW_W", "W", 26
InstallRampMeters

WScript.Echo "COUNTS_AFTER_IN_MEMORY DSD=" & Vissim.Net.DesSpeedDecisions.Count & " SC=" & Vissim.Net.SignalControllers.Count & " SH=" & Vissim.Net.SignalHeads.Count

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

Sub InstallVslSegments(modelLink, direction, linkNo)
    Dim link, length, i, startPos, endPos, dsdPos, segId, purpose
    Set link = Vissim.Net.Links.ItemByKey(CLng(linkNo))
    length = CDbl(link.AttValue("Length2D"))
    For i = 0 To 7
        startPos = length * CDbl(i) / 8.0
        endPos = length * CDbl(i + 1) / 8.0
        dsdPos = VslDecisionPos(modelLink, i, startPos)
        If i = 0 Then dsdPos = 1.0
        segId = "RW_" & modelLink & "_S" & CStr(i)
        purpose = "Real-world freeway VSL segment " & modelLink & " S" & CStr(i)
        AddVslDsds segId, modelLink, i, direction, link, dsdPos, startPos, endPos, purpose
    Next
End Sub

Sub AddVslDsds(segmentId, modelLink, segmentIndex, direction, link, pos, segmentStart, segmentEnd, purpose)
    Dim laneNo, lane, dsd, name, defaultSpeed
    defaultSpeed = 120
    pos = ClampPos(CDbl(pos), link)
    For laneNo = 1 To link.Lanes.Count
        Set lane = link.Lanes.ItemByKey(CLng(laneNo))
        On Error Resume Next
        Set dsd = Vissim.Net.DesSpeedDecisions.AddDesSpeedDecision(0, lane, CDbl(pos))
        If Err.Number <> 0 Then
            WScript.Echo "WARN=FAILED_ADD_DSD segment=" & segmentId & " link=" & link.AttValue("No") & " lane=" & laneNo & " pos=" & pos & " err=" & Err.Description
            Err.Clear
            On Error GoTo 0
        Else
            On Error GoTo 0
            name = "RW_VSL_" & segmentId & "_L" & CStr(link.AttValue("No")) & "_LN" & CStr(laneNo)
            SetName dsd, name
            SetClassSpeed dsd, 10, defaultSpeed
            SetClassSpeed dsd, 20, defaultSpeed
            SetClassSpeed dsd, 30, defaultSpeed
            WriteManifest "desSpeedDecision", "segment_start_vsl", segmentId, segmentId, modelLink, segmentIndex, direction, name, SafeAtt(dsd, "No"), link.AttValue("No"), laneNo, Round3(pos), Round3(segmentStart), Round3(segmentEnd), defaultSpeed, "10;20;30", "", "", "", "", "", "", "", "", "", "", purpose
        End If
    Next
End Sub

Sub InstallRampMeters()
    AddRampMeter "RM_C10480", 9101, 10480, 31, 734.931, 26, 3525.124, "R_D_W", 10, 900, "Ramp meter on connector 10480 link 31 to freeway link 26"
    AddRampMeter "RM_C10482", 9102, 10482, 32, 1028.621, 26, 3829.779, "R_D_W", 10, 900, "Ramp meter on connector 10482 link 32 to freeway link 26"
    AddRampMeter "RM_C10646", 9103, 10646, 68, 352.004, 26, 6072.550, "R_F_W", 10, 900, "Ramp meter on connector 10646 link 68 to freeway link 26"
    AddRampMeter "RM_C10644", 9104, 10644, 69, 1740.482, 26, 6774.308, "R_F_W", 10, 900, "Ramp meter on connector 10644 link 69 to freeway link 26"
    AddRampMeter "RM_C10639", 9105, 10639, 70, 180.143, 2, 1876.292, "R_F_E", 10, 900, "Ramp meter on connector 10639 link 70 to freeway link 2"
    AddRampMeter "RM_C10681", 9106, 10681, 68, 76.589, 2, 2165.429, "R_F_E", 10, 900, "Ramp meter on connector 10681 link 68 to freeway link 2"
    AddRampMeter "RM_C10490", 9107, 10490, 32, 1330.644, 2, 4413.602, "R_D_E", 10, 900, "Ramp meter on connector 10490 link 32 to freeway link 2"
    AddRampMeter "RM_C10484", 9108, 10484, 31, 412.087, 2, 4702.918, "R_D_E", 10, 900, "Ramp meter on connector 10484 link 31 to freeway link 2"
End Sub

Sub AddRampMeter(controlId, scNo, connectorNo, fromLink, fromPos, toLink, toPos, modelRampKey, defaultGreen, capacity, purpose)
    Dim sc, sg, link, pos, laneNo, lane, sh, name
    Set sc = EnsureSignalController(scNo, "RW_SC_" & controlId)
    Set sg = EnsureSignalGroup(sc, 1, "RW_SG_" & controlId)
    TrySetAtt sc, "Active", False

    Set link = Vissim.Net.Links.ItemByKey(CLng(connectorNo))
    pos = ClampPos(5.0, link)
    WriteManifest "rampMeter", "ramp_meter_connector", controlId, "", "", "", "", "RW_RM_" & controlId, "", "", "", "", "", "", "", "", scNo, 1, connectorNo, fromLink, Round3(fromPos), toLink, Round3(toPos), defaultGreen, capacity, modelRampKey, purpose
    WriteManifest "signalController", "ramp_meter_controller", controlId, "", "", "", "", SafeAtt(sc, "Name"), SafeAtt(sc, "No"), "", "", "", "", "", "", "", scNo, "", connectorNo, fromLink, Round3(fromPos), toLink, Round3(toPos), defaultGreen, capacity, modelRampKey, purpose
    WriteManifest "signalGroup", "ramp_meter_signal_group", controlId, "", "", "", "", SafeAtt(sg, "Name"), SafeAtt(sg, "No"), "", "", "", "", "", "", "", scNo, 1, connectorNo, fromLink, Round3(fromPos), toLink, Round3(toPos), defaultGreen, capacity, modelRampKey, purpose

    For laneNo = 1 To link.Lanes.Count
        Set lane = link.Lanes.ItemByKey(CLng(laneNo))
        On Error Resume Next
        Set sh = Vissim.Net.SignalHeads.AddSignalHead(0, lane, CDbl(pos))
        If Err.Number <> 0 Then
            WScript.Echo "WARN=FAILED_ADD_SIGNAL_HEAD meter=" & controlId & " connector=" & connectorNo & " lane=" & laneNo & " err=" & Err.Description
            Err.Clear
            On Error GoTo 0
        Else
            On Error GoTo 0
            name = "RW_SH_" & controlId & "_C" & CStr(connectorNo) & "_LN" & CStr(laneNo)
            SetName sh, name
            TrySetAtt sh, "SG", CStr(scNo) & "-" & "1"
            TrySetAtt sh, "Type", "CIRCULAR"
            WriteManifest "signalHead", "ramp_meter_signal_head", controlId, "", "", "", "", name, SafeAtt(sh, "No"), connectorNo, laneNo, Round3(pos), "", "", "", "", scNo, 1, connectorNo, fromLink, Round3(fromPos), toLink, Round3(toPos), defaultGreen, capacity, modelRampKey, purpose
        End If
    Next
End Sub

Function EnsureSignalController(scNo, name)
    Dim sc
    On Error Resume Next
    Set sc = Vissim.Net.SignalControllers.ItemByKey(CLng(scNo))
    If Err.Number <> 0 Then
        Err.Clear
        Set sc = Vissim.Net.SignalControllers.AddSignalController(CLng(scNo))
    End If
    If Err.Number <> 0 Then
        WScript.Echo "ERROR=FAILED_ADD_SIGNAL_CONTROLLER sc=" & scNo & " err=" & Err.Description
        WScript.Quit 3
    End If
    On Error GoTo 0
    SetName sc, name
    Set EnsureSignalController = sc
End Function

Function EnsureSignalGroup(sc, sgNo, name)
    Dim sg
    On Error Resume Next
    Set sg = sc.SGs.ItemByKey(CLng(sgNo))
    If Err.Number <> 0 Then
        Err.Clear
        Set sg = sc.SGs.AddSignalGroup(CLng(sgNo))
    End If
    If Err.Number <> 0 Then
        WScript.Echo "ERROR=FAILED_ADD_SIGNAL_GROUP sc=" & SafeAtt(sc, "No") & " sg=" & sgNo & " err=" & Err.Description
        WScript.Quit 4
    End If
    On Error GoTo 0
    SetName sg, name
    Set EnsureSignalGroup = sg
End Function

Function VslDecisionPos(modelLink, segmentIndex, startPos)
    VslDecisionPos = CDbl(startPos)
    If modelLink = "FW_E" And CLng(segmentIndex) = 2 Then
        ' The exact S2 boundary sits just upstream of a connector; keep the DSD inside S2 with clearance.
        VslDecisionPos = CDbl(startPos) + 10.0
    End If
End Function

Sub SetClassSpeed(dsd, vehClassNo, speedKph)
    TrySetAtt dsd, "DesSpeedDistr(" & CStr(vehClassNo) & ")", CLng(speedKph)
End Sub

Function ClampPos(pos, link)
    Dim length
    length = CDbl(link.AttValue("Length2D"))
    If CDbl(pos) < 1 Then
        ClampPos = 1
    ElseIf CDbl(pos) > length - 1 Then
        ClampPos = length - 1
    Else
        ClampPos = CDbl(pos)
    End If
End Function

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

Sub WriteManifest(objectType, category, controlId, segmentId, modelLink, modelSegmentIndex, direction, name, no, linkNo, laneNo, pos, segmentStart, segmentEnd, defaultSpeed, vehClasses, scNo, sgNo, connector, fromLink, fromPos, toLink, toPos, defaultGreen, capacity, modelRampKey, purpose)
    manifest.WriteLine Csv(objectType) & "," & Csv(category) & "," & Csv(controlId) & "," & Csv(segmentId) & "," & Csv(modelLink) & "," & Csv(modelSegmentIndex) & "," & Csv(direction) & "," & Csv(name) & "," & Csv(no) & "," & Csv(linkNo) & "," & Csv(laneNo) & "," & Csv(pos) & "," & Csv(segmentStart) & "," & Csv(segmentEnd) & "," & Csv(defaultSpeed) & "," & Csv(vehClasses) & "," & Csv(scNo) & "," & Csv(sgNo) & "," & Csv(connector) & "," & Csv(fromLink) & "," & Csv(fromPos) & "," & Csv(toLink) & "," & Csv(toPos) & "," & Csv(defaultGreen) & "," & Csv(capacity) & "," & Csv(modelRampKey) & "," & Csv(purpose)
End Sub

Function Csv(value)
    Dim text
    text = CStr(value)
    text = Replace(text, """", """""")
    Csv = """" & text & """"
End Function

Function Round3(value)
    Round3 = Replace(FormatNumber(CDbl(value), 3, -1, 0, 0), ",", "")
End Function

Sub EnsureParentFolder(path)
    Dim parent
    parent = fso.GetParentFolderName(path)
    If parent <> "" And Not fso.FolderExists(parent) Then
        EnsureParentFolder parent
        fso.CreateFolder parent
    End If
End Sub

' 2026-08-01: create the VISSIM COM object with a ProgID fallback chain.
' NOTE: this file stays pure ASCII on purpose. cscript reads .vbs as the system
' ANSI codepage (CP949 here), so non-ASCII bytes corrupt string literals.
'
' Why the fallback: the generic ProgID "Vissim.Vissim" points at whichever VISSIM
' version registered last. On a machine where 2026 was installed and then removed,
' it still resolves to a missing Vissim260.exe and every script dies with
' "ActiveX component can't create object" even though 2020 is installed and fine.
' The proper repair is re-registering the wanted build as admin:
'     "C:\Program Files\PTV Vision\PTV Vissim 2020\exe\Vissim200.exe" /regserver
' That is a system-level change, so the repo also falls back to version-specific
' ProgIDs. Set VISSIM_PROGID to pin a specific one.
Function CreateVissimCom()
    Dim candidates, i, obj, forced, shell
    Set shell = CreateObject("WScript.Shell")
    forced = shell.ExpandEnvironmentStrings("%VISSIM_PROGID%")
    If forced <> "%VISSIM_PROGID%" And forced <> "" Then
        Set CreateVissimCom = CreateObject(forced)
        WScript.Echo "STAGE=COM_PROGID " & forced & " (VISSIM_PROGID)"
        Exit Function
    End If
    candidates = Array("Vissim.Vissim", "Vissim.Vissim.2020", "Vissim.Vissim-64.20", "Vissim.Vissim.200")
    For i = 0 To UBound(candidates)
        On Error Resume Next
        Set obj = CreateObject(candidates(i))
        If Err.Number = 0 Then
            Err.Clear
            On Error GoTo 0
            WScript.Echo "STAGE=COM_PROGID " & candidates(i)
            Set CreateVissimCom = obj
            Exit Function
        End If
        Err.Clear
        On Error GoTo 0
    Next
    WScript.Echo "ERROR=NO_VISSIM_COM no registered VISSIM COM ProgID could be created"
    WScript.Quit 3
End Function
