Option Explicit

' Build the 8-segment-per-direction eval network from the 5-segment one.
'
' Design (2026-07-14, user-approved):
'   * Links 33 (FW_E) / 34 (FW_W) are NOT modified: all ramp connectors,
'     routing decisions and positions keep their coordinates.
'   * Mainline is extended with new entry/exit links + 4 m gap connectors:
'       EB entry 500 m (west), EB exit 200 m (east)
'       WB entry 350 m (east), WB exit 250 m (west)
'   * Freeway vehicle inputs VI_FW_E / VI_FW_W move onto the entry links.
'   * Old EVAL_VSL_SEG_* DSDs (5-seg layout) are deleted; 32 new DSDs are
'     installed, one per lane at each of 8 segment starts per direction.
'   * One ramp junction per segment: off-ramps in S2/S4, on-ramp merges in
'     S3/S5 (matches Numerical-Sim 8-seg default.yaml: off 2/4, merge 3/5).
'
' Segment boundaries in main-link coordinates (link length 2900.003):
'   EB S1..S7 start at: 0, 350, 800, 1300, 1800, 2300, 2600
'      (ramps: OR_D 499.03 in S2, R_D 812.39 in S3, OR_F 1735.61 in S4,
'       R_F 2029.15 in S5)
'   WB S1..S7 start at: 0, 350, 850, 1350, 1900, 2450, 2750
'      (ramps: OR_F 537.74 in S2, R_F 1155.25 in S3, OR_D 1743.46 in S4,
'       R_D 2398.24 in S5)
'   S0 = the new entry link; S7 extends over the new exit link.

If WScript.Arguments.Count < 5 Then
    WScript.Echo "Usage: cscript install_eval_vsl_8seg.vbs <source.inpx> <source.layx> <target.inpx> <target.layx> <manifest.csv>"
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
manifest.WriteLine "object_type,category,segment_id,direction,name,no,link,lane,pos,segment_start_m,segment_end_m,default_speed_kph,veh_classes,purpose"

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

WScript.Echo "COUNTS_BEFORE DSD=" & Vissim.Net.DesSpeedDecisions.Count & " LINKS=" & Vissim.Net.Links.Count & " VI=" & Vissim.Net.VehicleInputs.Count

' --- Stage 1: delete old 5-seg DSDs -------------------------------------
DeleteOldSegDsds

' --- Stage 2: extension links + connectors ------------------------------
' Main link endpoints (from inventory): EB 33 (-1450,-512)->(1450,-512),
' WB 34 (1450,-488)->(-1450,-488). 4 m gap before/after each main link.
Dim ebEntry, ebExit, wbEntry, wbExit
Set ebEntry = AddExtensionLink("FW_E entry extension", -1954, -1454, -512)
Set ebExit = AddExtensionLink("FW_E exit extension", 1454, 1654, -512)
Set wbEntry = AddExtensionLink("FW_W entry extension", 1804, 1454, -488)
Set wbExit = AddExtensionLink("FW_W exit extension", -1454, -1704, -488)

Dim mainEB, mainWB
Set mainEB = Vissim.Net.Links.ItemByKey(33)
Set mainWB = Vissim.Net.Links.ItemByKey(34)

CopyLinkStyle mainEB, ebEntry
CopyLinkStyle mainEB, ebExit
CopyLinkStyle mainWB, wbEntry
CopyLinkStyle mainWB, wbExit

Dim connEbIn, connEbOut, connWbIn, connWbOut
Set connEbIn = AddGapConnector("FW_E entry->main", ebEntry, mainEB, -1454, -1450, -512)
Set connEbOut = AddGapConnector("FW_E main->exit", mainEB, ebExit, 1450, 1454, -512)
Set connWbIn = AddGapConnector("FW_W entry->main", wbEntry, mainWB, 1454, 1450, -488)
Set connWbOut = AddGapConnector("FW_W main->exit", mainWB, wbExit, -1450, -1454, -488)

WScript.Echo "NEW_LINK EB_ENTRY=" & ebEntry.AttValue("No") & " len=" & ebEntry.AttValue("Length2D")
WScript.Echo "NEW_LINK EB_EXIT=" & ebExit.AttValue("No") & " len=" & ebExit.AttValue("Length2D")
WScript.Echo "NEW_LINK WB_ENTRY=" & wbEntry.AttValue("No") & " len=" & wbEntry.AttValue("Length2D")
WScript.Echo "NEW_LINK WB_EXIT=" & wbExit.AttValue("No") & " len=" & wbExit.AttValue("Length2D")
WScript.Echo "NEW_CONN EB_IN=" & connEbIn.AttValue("No") & " EB_OUT=" & connEbOut.AttValue("No") & " WB_IN=" & connWbIn.AttValue("No") & " WB_OUT=" & connWbOut.AttValue("No")

WriteManifest "link", "mainline_extension", "EB_S0_W_EXT_ENTRY", "EB", "FW_E entry extension", ebEntry.AttValue("No"), ebEntry.AttValue("No"), "", 0, 0, CDbl(ebEntry.AttValue("Length2D")), "", "", "new EB upstream entry link"
WriteManifest "link", "mainline_extension", "EB_S7_E_EXIT", "EB", "FW_E exit extension", ebExit.AttValue("No"), ebExit.AttValue("No"), "", 0, 0, CDbl(ebExit.AttValue("Length2D")), "", "", "new EB downstream exit link"
WriteManifest "link", "mainline_extension", "WB_S0_E_EXT_ENTRY", "WB", "FW_W entry extension", wbEntry.AttValue("No"), wbEntry.AttValue("No"), "", 0, 0, CDbl(wbEntry.AttValue("Length2D")), "", "", "new WB upstream entry link"
WriteManifest "link", "mainline_extension", "WB_S7_W_EXIT", "WB", "FW_W exit extension", wbExit.AttValue("No"), wbExit.AttValue("No"), "", 0, 0, CDbl(wbExit.AttValue("Length2D")), "", "", "new WB downstream exit link"
WriteManifest "connector", "mainline_extension", "EB_S0_W_EXT_ENTRY", "EB", "FW_E entry->main", connEbIn.AttValue("No"), 33, "", 0, 0, 0, "", "", "gap connector entry->main"
WriteManifest "connector", "mainline_extension", "EB_S7_E_EXIT", "EB", "FW_E main->exit", connEbOut.AttValue("No"), 33, "", 0, 0, 0, "", "", "gap connector main->exit"
WriteManifest "connector", "mainline_extension", "WB_S0_E_EXT_ENTRY", "WB", "FW_W entry->main", connWbIn.AttValue("No"), 34, "", 0, 0, 0, "", "", "gap connector entry->main"
WriteManifest "connector", "mainline_extension", "WB_S7_W_EXIT", "WB", "FW_W main->exit", connWbOut.AttValue("No"), 34, "", 0, 0, 0, "", "", "gap connector main->exit"

' --- Stage 3: move freeway vehicle inputs to the entry links -------------
MoveVehicleInput "VI_FW_E", 33, ebEntry
MoveVehicleInput "VI_FW_W", 34, wbEntry

' --- Stage 4: install 32 DSDs (8 segments x 2 lanes x 2 directions) ------
' S0 sits on the entry link; S1..S7 on the main link. Segment start/end in
' the manifest are per-corridor coordinates (0 = entry link start).
Dim ebEntryLen, wbEntryLen, ebExitLen, wbExitLen
ebEntryLen = CDbl(ebEntry.AttValue("Length2D"))
ebExitLen = CDbl(ebExit.AttValue("Length2D"))
wbEntryLen = CDbl(wbEntry.AttValue("Length2D"))
wbExitLen = CDbl(wbExit.AttValue("Length2D"))

' EB corridor
AddVsl8 "EB_S0_W_EXT_ENTRY", "EB", ebEntry, 1.0, 0.0, ebEntryLen, "EB entry extension segment (upstream warmup)"
AddVsl8 "EB_S1_W_APPROACH", "EB", mainEB, 1.0, ebEntryLen + 0.0, ebEntryLen + 350.0, "EB approach segment before D diverge"
AddVsl8 "EB_S2_D_DIVERGE", "EB", mainEB, 350.0, ebEntryLen + 350.0, ebEntryLen + 800.0, "EB segment containing OR_D off-ramp diverge (499.03)"
AddVsl8 "EB_S3_D_MERGE", "EB", mainEB, 800.0, ebEntryLen + 800.0, ebEntryLen + 1300.0, "EB segment containing R_D on-ramp merge (812.39, metering)"
AddVsl8 "EB_S4_F_DIVERGE", "EB", mainEB, 1300.0, ebEntryLen + 1300.0, ebEntryLen + 1800.0, "EB segment containing OR_F off-ramp diverge (1735.61)"
AddVsl8 "EB_S5_F_MERGE", "EB", mainEB, 1800.0, ebEntryLen + 1800.0, ebEntryLen + 2300.0, "EB segment containing R_F on-ramp merge (2029.15, metering)"
AddVsl8 "EB_S6_POST_F", "EB", mainEB, 2300.0, ebEntryLen + 2300.0, ebEntryLen + 2600.0, "EB post-F mainline segment"
AddVsl8 "EB_S7_E_EXIT", "EB", mainEB, 2600.0, ebEntryLen + 2600.0, ebEntryLen + 2900.003 + ebExitLen, "EB exit segment (tail of main link + exit extension)"

' WB corridor
AddVsl8 "WB_S0_E_EXT_ENTRY", "WB", wbEntry, 1.0, 0.0, wbEntryLen, "WB entry extension segment (upstream warmup)"
AddVsl8 "WB_S1_E_APPROACH", "WB", mainWB, 1.0, wbEntryLen + 0.0, wbEntryLen + 350.0, "WB approach segment before F diverge"
AddVsl8 "WB_S2_F_DIVERGE", "WB", mainWB, 350.0, wbEntryLen + 350.0, wbEntryLen + 850.0, "WB segment containing OR_F off-ramp diverge (537.74)"
AddVsl8 "WB_S3_F_MERGE", "WB", mainWB, 850.0, wbEntryLen + 850.0, wbEntryLen + 1350.0, "WB segment containing R_F on-ramp merge (1155.25, metering)"
AddVsl8 "WB_S4_D_DIVERGE", "WB", mainWB, 1350.0, wbEntryLen + 1350.0, wbEntryLen + 1900.0, "WB segment containing OR_D off-ramp diverge (1743.46)"
AddVsl8 "WB_S5_D_MERGE", "WB", mainWB, 1900.0, wbEntryLen + 1900.0, wbEntryLen + 2450.0, "WB segment containing R_D on-ramp merge (2398.24, metering)"
AddVsl8 "WB_S6_POST_D", "WB", mainWB, 2450.0, wbEntryLen + 2450.0, wbEntryLen + 2750.0, "WB post-D mainline segment"
AddVsl8 "WB_S7_W_EXIT", "WB", mainWB, 2750.0, wbEntryLen + 2750.0, wbEntryLen + 2900.003 + wbExitLen, "WB exit segment (tail of main link + exit extension)"

WScript.Echo "COUNTS_AFTER_IN_MEMORY DSD=" & Vissim.Net.DesSpeedDecisions.Count & " LINKS=" & Vissim.Net.Links.Count & " VI=" & Vissim.Net.VehicleInputs.Count

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

' =========================================================================

Sub DeleteOldSegDsds()
    Dim all, dsd, name, toRemove(), n, i
    all = Vissim.Net.DesSpeedDecisions.GetAll
    n = 0
    ReDim toRemove(UBound(all) + 1)
    For Each dsd In all
        name = SafeAtt(dsd, "Name")
        If InStr(1, name, "EVAL_VSL_SEG_", vbTextCompare) = 1 Then
            Set toRemove(n) = dsd
            n = n + 1
        End If
    Next
    For i = 0 To n - 1
        On Error Resume Next
        Vissim.Net.DesSpeedDecisions.RemoveDesSpeedDecision toRemove(i)
        If Err.Number <> 0 Then
            WScript.Echo "WARN=FAILED_REMOVE_DSD err=" & Err.Description
            Err.Clear
        End If
        On Error GoTo 0
    Next
    WScript.Echo "STAGE=OLD_DSDS_REMOVED count=" & n
End Sub

Function AddExtensionLink(name, x0, x1, y)
    Dim wkt, widths(1), link
    widths(0) = 3.65
    widths(1) = 3.65
    wkt = "LINESTRING(" & Num(x0) & " " & Num(y) & " 0," & Num(x1) & " " & Num(y) & " 0)"
    Set link = Vissim.Net.Links.AddLink(0, wkt, widths)
    SetName link, name
    Set AddExtensionLink = link
End Function

Sub CopyLinkStyle(src, dst)
    TrySetAtt dst, "LinkBehavType", src.AttValue("LinkBehavType")
    TrySetAtt dst, "DisplayType", src.AttValue("DisplayType")
End Sub

Function AddGapConnector(name, fromLink, toLink, xFrom, xTo, y)
    ' Straight gap connector, intermediate points only (Vissim adds ends).
    Dim wkt, conn, xm1, xm2
    xm1 = xFrom + (xTo - xFrom) / 3.0
    xm2 = xFrom + 2.0 * (xTo - xFrom) / 3.0
    wkt = "LINESTRING(" & Num(xm1) & " " & Num(y) & " 0," & Num(xm2) & " " & Num(y) & " 0)"
    Set conn = Vissim.Net.Links.AddConnector(0, fromLink.Lanes.ItemByKey(1), CDbl(fromLink.AttValue("Length2D")), toLink.Lanes.ItemByKey(1), 0, 2, wkt)
    SetName conn, name
    Set AddGapConnector = conn
End Function

Sub MoveVehicleInput(viName, oldLinkNo, newLink)
    Dim all, vi, name, volume, found
    found = False
    all = Vissim.Net.VehicleInputs.GetAll
    For Each vi In all
        name = SafeAtt(vi, "Name")
        If StrComp(name, viName, vbTextCompare) = 0 Then
            volume = CDbl(vi.AttValue("Volume(1)"))
            On Error Resume Next
            Vissim.Net.VehicleInputs.RemoveVehicleInput vi
            If Err.Number <> 0 Then
                WScript.Echo "WARN=FAILED_REMOVE_VI name=" & viName & " err=" & Err.Description
                Err.Clear
                On Error GoTo 0
                Exit Sub
            End If
            On Error GoTo 0
            Dim nvi
            Set nvi = Vissim.Net.VehicleInputs.AddVehicleInput(0, newLink)
            nvi.AttValue("Volume(1)") = volume
            SetName nvi, viName
            WScript.Echo "VI_MOVED name=" & viName & " old_link=" & oldLinkNo & " new_link=" & newLink.AttValue("No") & " volume=" & volume
            WriteManifest "vehicleInput", "mainline_extension", "", "", viName, nvi.AttValue("No"), newLink.AttValue("No"), "", 0, 0, 0, "", "", "freeway input moved to entry extension link"
            found = True
            Exit For
        End If
    Next
    If Not found Then
        WScript.Echo "WARN=VI_NOT_FOUND name=" & viName
    End If
End Sub

Sub AddVsl8(segmentId, direction, link, startPosOnLink, corridorStart, corridorEnd, purpose)
    Dim laneNo, lane, dsd, name, dsdNo, defaultSpeed, pos
    defaultSpeed = 120
    pos = ClampPos(CDbl(startPosOnLink), link)

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
            name = "EVAL_VSL_SEG_" & segmentId & "_L" & CStr(link.AttValue("No")) & "_LN" & CStr(laneNo)
            SetName dsd, name
            SetClassSpeed dsd, 10, defaultSpeed
            SetClassSpeed dsd, 20, defaultSpeed
            SetClassSpeed dsd, 30, defaultSpeed
            dsdNo = SafeAtt(dsd, "No")
            WriteManifest "desSpeedDecision", "segment_start_vsl", segmentId, direction, name, dsdNo, link.AttValue("No"), laneNo, Round3(pos), Round3(corridorStart), Round3(corridorEnd), defaultSpeed, "10;20;30", purpose
        End If
    Next
End Sub

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

Function Num(value)
    Num = Replace(CStr(CDbl(value)), ",", ".")
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

Sub WriteManifest(objectType, category, segmentId, direction, name, no, linkNo, laneNo, pos, startPos, endPos, defaultSpeed, vehClasses, purpose)
    manifest.WriteLine Csv(objectType) & "," & Csv(category) & "," & Csv(segmentId) & "," & Csv(direction) & "," & Csv(name) & "," & Csv(no) & "," & Csv(linkNo) & "," & Csv(laneNo) & "," & Csv(pos) & "," & Csv(startPos) & "," & Csv(endPos) & "," & Csv(defaultSpeed) & "," & Csv(vehClasses) & "," & Csv(purpose)
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
