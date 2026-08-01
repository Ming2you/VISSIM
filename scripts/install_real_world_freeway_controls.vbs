Option Explicit

' Add a real-world freeway control layer to the Gaepo modi network.
' The source network is not modified. The target network receives:
'   * 8 VSL segment-start desired-speed decisions per freeway direction and lane
'   * 8 physical ramp-meter signal controllers on on-ramp connectors
'
' 2026-08-01: the freeway mainline is a LINK CHAIN, not a single link.
' The chain (which links, in which order) is read from the canonical CSV
'   evaluation\real_world_modi_control\freeway_mainline_chain.csv
' and every length is read back from the loaded VISSIM network, so a user edit
' to the .inpx geometry propagates without touching this script.
' The 8 VSL segments are an equal split of the WHOLE chain length; each segment
' start is converted from a chain offset back to (link, pos on link).
'
' 2026-08-01 (b): a segment start that lands too close to the point where
' vehicles leave its chain member is SNAPPED forward to the next member that can
' host it (see DSD_EDGE_CLEARANCE_M). The segment boundaries themselves never
' move - only the physical decision point does - so the few tens of metres
' between the boundary and the snapped decision point keep the upstream
' segment's VSL. Every snap is echoed as SNAP= and recorded in the manifest
' purpose column (chain_placed_m / snap_m).
'
' 2026-08-01 (c): two fixes measured by the VSL channel live-execution run
' (outputs\vsl_channel_live_execution_20260801.md).
'   1) The segment-0 exception that forced the decision point back to pos 1.0 is
'      removed, so S0 obeys the same entry clearance as every other segment.
'   2) Vehicle class 70 (TAXI) is added to the VSL target set on every RW DSD.
'
' Ramp meter targets intentionally exclude connector 10699 (link 74 -> 2),
' because it is a mainline chain member rather than an isolated ramp merge.

If WScript.Arguments.Count < 5 Then
    WScript.Echo "Usage: cscript install_real_world_freeway_controls.vbs <source.inpx> <source.layx> <target.inpx> <target.layx> <manifest.csv> [freeway_mainline_chain.csv]"
    WScript.Quit 2
End If

Const SEGMENTS_PER_MODEL_LINK = 8

' 2026-08-01: clearance a desired-speed decision needs from the point where
' vehicles ENTER a chain member and from the point where they LEAVE it.
' Within one simulation step a vehicle jumps a whole step length and crosses the
' member boundary, so a decision point inside that band is not guaranteed to be
' seen as passed (FW_E S2 used to sit 1.701 m before the point where connector
' 10699 leaves link 74, i.e. 1/16 of the VSL channels could die silently).
' Sizing: SimRes = 1 -> dt = 1.0 s. SimRes is hard-set to 1 both by
' prepare_real_world_modi_eval_copy.py and by run_real_world_stackelberg_controller.vbs,
' so one step is a full second, not 0.1 s. Free-flow desired speed is 120 km/h
' and the upper tail of that distribution reaches about 130 km/h = 36.1 m/s.
' One step at the upper tail is 36.1 m; rounded up with margin -> 40 m.
' VSL only lowers speeds, so 40 m is an upper bound on the per-step jump.
Const DSD_EDGE_CLEARANCE_M = 40.0
' A chain member must hold the clearance on BOTH sides to host a decision point
' (= 2 * DSD_EDGE_CLEARANCE_M). A segment start landing on a member that cannot
' is snapped forward to the next member that can.
Const MIN_DSD_HOST_LENGTH_M = 80.0

Dim sourceNet, sourceLayout, targetNet, targetLayout, manifestPath, chainCsvPath
sourceNet = WScript.Arguments(0)
sourceLayout = WScript.Arguments(1)
targetNet = WScript.Arguments(2)
targetLayout = WScript.Arguments(3)
manifestPath = WScript.Arguments(4)

Dim fso, manifest, Vissim, chainModels, chainLinks, chainDirections
Set fso = CreateObject("Scripting.FileSystemObject")

If WScript.Arguments.Count >= 6 Then
    chainCsvPath = WScript.Arguments(5)
Else
    chainCsvPath = DefaultChainCsvPath()
End If
LoadChainCsv chainCsvPath

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

Dim modelIdx
For modelIdx = 0 To UBound(chainModels)
    InstallVslSegments CStr(chainModels(modelIdx))
Next
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

Sub InstallVslSegments(modelLink)
    Dim members, offsets, total, direction, i, chainStart, chainEnd, memberIdx, link
    Dim dsdPos, minPos, placedChain, snapOffset, snapped, segId, purpose, entryHeld
    direction = CStr(chainDirections(modelLink))
    BuildChainGeometry modelLink, members, offsets, total
    WScript.Echo "CHAIN=" & modelLink & " dir=" & direction & " links=" & Join(members, "+") & _
        " offsets_m=" & JoinRound3(offsets) & " total_m=" & Round3(total) & _
        " segment_m=" & Round3(total / CDbl(SEGMENTS_PER_MODEL_LINK)) & _
        " edge_clearance_m=" & Round3(DSD_EDGE_CLEARANCE_M)
    EchoChainMembers modelLink, members, offsets, total
    For i = 0 To SEGMENTS_PER_MODEL_LINK - 1
        chainStart = total * CDbl(i) / CDbl(SEGMENTS_PER_MODEL_LINK)
        chainEnd = total * CDbl(i + 1) / CDbl(SEGMENTS_PER_MODEL_LINK)
        memberIdx = ResolveChainMember(members, offsets, total, chainStart, snapped)
        Set link = Vissim.Net.Links.ItemByKey(CLng(members(memberIdx)))
        dsdPos = chainStart - CDbl(offsets(memberIdx))
        ' Never place a decision point before the position where vehicles appear
        ' on the host member (a connector lands mid-link, not at pos 0), and keep
        ' one step of clearance after it.
        ' 2026-08-01 (c): segment 0 used to be exempted from this rule and forced
        ' back to pos 1.0. That put the S0 decision point UPSTREAM of the original
        ' network's entry DSDs (no 36-42, pos 1.5-11.9, distribution 100), which
        ' overwrote our VSL a few metres later and killed the channel
        ' (measured FW_E S0 self-fingerprint 1.3%, FW_W S0 21.8%). The exemption
        ' is gone: segment 0 now gets the same entry clearance as every other
        ' segment, so its DSD lands at entry + 40 m, downstream of the legacy DSDs.
        entryHeld = False
        minPos = MemberEntryPos(members, memberIdx) + DSD_EDGE_CLEARANCE_M
        If dsdPos < minPos Then
            dsdPos = minPos
            entryHeld = True
        End If
        dsdPos = ClampPos(dsdPos, link)
        placedChain = CDbl(offsets(memberIdx)) + dsdPos
        snapOffset = placedChain - chainStart
        segId = "RW_" & modelLink & "_S" & CStr(i)
        purpose = "Real-world freeway VSL segment " & modelLink & " S" & CStr(i) & _
            " chain_start_m=" & Round3(chainStart) & " on link " & CStr(members(memberIdx)) & "@" & Round3(dsdPos) & _
            " chain_placed_m=" & Round3(placedChain) & " snap_m=" & Round3(snapOffset)
        If snapped Then
            ' The measurement grid is untouched; only the physical decision point
            ' moved, so vehicles in [chain_start, chain_placed) keep the previous
            ' segment's VSL. That is the accepted approximation - a dead channel
            ' would be worse and the action CSV readback cannot detect it.
            purpose = purpose & " snap=PAST_MEMBER_END grid_unchanged upstream_vsl_applies_over_snap_m"
            WScript.Echo "SNAP=" & segId & " reason=MEMBER_END_CLEARANCE" & _
                " chain_start_m=" & Round3(chainStart) & _
                " host_link=" & CStr(members(memberIdx)) & " host_pos_m=" & Round3(dsdPos) & _
                " chain_placed_m=" & Round3(placedChain) & " snap_m=" & Round3(snapOffset) & _
                " edge_clearance_m=" & Round3(DSD_EDGE_CLEARANCE_M)
        End If
        If entryHeld Then
            ' Same accepted approximation as the snap case: the measurement grid is
            ' untouched, only the physical decision point moved forward, so vehicles
            ' in [chain_start, chain_placed) keep the upstream distribution. For
            ' segment 0 there is no upstream VSL at all, so that band keeps the
            ' network's own entry distribution.
            purpose = purpose & " hold=MEMBER_ENTRY_CLEARANCE"
            ' Do not repeat the shared suffix when the snap branch already wrote it.
            If Not snapped Then
                If i = 0 Then
                    ' Segment 0 has no upstream segment, so the band before the
                    ' decision point keeps the network's own inflow distribution.
                    purpose = purpose & " grid_unchanged no_vsl_before_chain_placed_m"
                Else
                    purpose = purpose & " grid_unchanged upstream_vsl_applies_over_snap_m"
                End If
            End If
            WScript.Echo "ENTRY_HOLD=" & segId & " reason=MEMBER_ENTRY_CLEARANCE" & _
                " chain_start_m=" & Round3(chainStart) & _
                " host_link=" & CStr(members(memberIdx)) & " host_pos_m=" & Round3(dsdPos) & _
                " member_entry_pos_m=" & Round3(MemberEntryPos(members, memberIdx)) & _
                " chain_placed_m=" & Round3(placedChain) & " snap_m=" & Round3(snapOffset) & _
                " edge_clearance_m=" & Round3(DSD_EDGE_CLEARANCE_M)
        End If
        AddVslDsds segId, modelLink, i, direction, link, dsdPos, chainStart, chainEnd, purpose
    Next
End Sub

' Per-member entry/exit geometry, echoed so the placement can be audited without
' re-running COM.
Sub EchoChainMembers(modelLink, members, offsets, total)
    Dim i
    For i = 0 To UBound(members)
        WScript.Echo "CHAIN_MEMBER=" & modelLink & " idx=" & CStr(i) & " link=" & CStr(members(i)) & _
            " chain_offset_m=" & Round3(offsets(i)) & _
            " length_m=" & Round3(MemberLength(members(i))) & _
            " entry_pos_m=" & Round3(MemberEntryPos(members, i)) & _
            " exit_pos_m=" & Round3(MemberExitPos(members, i)) & _
            " can_host=" & CStr(IsValidDsdHost(members, i))
    Next
End Sub

' Cumulative chain geometry, measured from the loaded network. offsets(i) is the
' chain coordinate of the start of chain member i; total is the chain length.
Sub BuildChainGeometry(modelLink, ByRef members, ByRef offsets, ByRef total)
    Dim i, link, acc()
    members = Split(CStr(chainLinks(modelLink)), ",")
    ReDim acc(UBound(members))
    total = 0.0
    For i = 0 To UBound(members)
        On Error Resume Next
        Set link = Vissim.Net.Links.ItemByKey(CLng(members(i)))
        If Err.Number <> 0 Then
            WScript.Echo "ERROR=CHAIN_LINK_NOT_FOUND model=" & modelLink & " link=" & CStr(members(i)) & " err=" & Err.Description
            WScript.Quit 5
        End If
        On Error GoTo 0
        acc(i) = total
        total = total + CDbl(link.AttValue("Length2D"))
    Next
    offsets = acc
End Sub

' Chain offset -> index of the chain member that should host the decision point.
' A member can host only if it keeps DSD_EDGE_CLEARANCE_M after the point where
' vehicles enter it and before the point where they leave it. When the wanted
' position lands inside the exit clearance band of its own member, the decision
' point is snapped forward to the next member that can host it; members too
' short to hold a decision point are skipped the same way. snapped reports it.
' NOTE: only the physical decision point moves. Segment boundaries (the
' measurement grid) are pure chain arithmetic and are never touched here.
Function ResolveChainMember(members, offsets, total, chainPos, snapped)
    Dim i, memberEnd, wanted, found
    snapped = False
    found = -1
    For i = 0 To UBound(members)
        memberEnd = MemberChainEnd(offsets, total, i)
        If memberEnd > CDbl(chainPos) Then
            wanted = CDbl(chainPos) - CDbl(offsets(i))
            If IsValidDsdHost(members, i) Then
                If wanted <= (MemberExitPos(members, i) - DSD_EDGE_CLEARANCE_M) Then
                    found = i
                    Exit For
                End If
            End If
            snapped = True
        End If
    Next
    If found < 0 Then
        snapped = True
        For i = UBound(members) To 0 Step -1
            If IsValidDsdHost(members, i) Then
                found = i
                Exit For
            End If
        Next
    End If
    If found < 0 Then found = 0
    ResolveChainMember = found
End Function

' Chain coordinate where chain member idx ends (pure geometry, matches the grid).
Function MemberChainEnd(offsets, total, idx)
    If idx < UBound(offsets) Then
        MemberChainEnd = CDbl(offsets(idx + 1))
    Else
        MemberChainEnd = CDbl(total)
    End If
End Function

Function IsValidDsdHost(members, idx)
    IsValidDsdHost = ((MemberExitPos(members, idx) - MemberEntryPos(members, idx)) >= MIN_DSD_HOST_LENGTH_M)
End Function

' Position ON chain member idx where vehicles coming from member idx-1 appear.
' A connector lands on its target link at toLinkEndPt, which is not pos 0, so a
' decision point placed before it would never be crossed at all.
Function MemberEntryPos(members, idx)
    Dim v
    MemberEntryPos = 0.0
    If idx <= 0 Then Exit Function
    v = ConnectorEndPos(members(idx - 1), "ToPos")
    If v >= 0 Then
        If v < MemberLength(members(idx)) Then MemberEntryPos = v
    End If
End Function

' Position ON chain member idx where vehicles leave towards member idx+1.
' This is the connector's fromLinkEndPt, which can be well before the geometric
' end of the link (link 74 ends at 2701.577 but hands over at 2694.978).
Function MemberExitPos(members, idx)
    Dim v, length
    length = MemberLength(members(idx))
    MemberExitPos = length
    If idx >= UBound(members) Then Exit Function
    v = ConnectorEndPos(members(idx + 1), "FromPos")
    If v > 0 Then
        If v <= length Then MemberExitPos = v
    End If
End Function

Function MemberLength(linkNo)
    MemberLength = CDbl(Vissim.Net.Links.ItemByKey(CLng(linkNo)).AttValue("Length2D"))
End Function

' FromPos / ToPos of a connector link. Returns -1 when the link is not a
' connector or the attribute cannot be read, so callers fall back to plain
' chain geometry instead of dying.
Function ConnectorEndPos(linkNo, att)
    Dim raw
    ConnectorEndPos = -1
    raw = SafeAtt(Vissim.Net.Links.ItemByKey(CLng(linkNo)), att)
    If raw = "" Then Exit Function
    If Not IsNumeric(raw) Then Exit Function
    ConnectorEndPos = CDbl(raw)
End Function

' Read the canonical mainline chain CSV into chainModels / chainLinks / chainDirections.
' Columns: model_link,direction,chain_order,link_no,role . Lines starting with # are comments.
Sub LoadChainCsv(path)
    Dim ts, line, parts, model, models, orders, seen
    If Not fso.FileExists(path) Then
        WScript.Echo "ERROR=CHAIN_CSV_NOT_FOUND path=" & path
        WScript.Quit 6
    End If
    Set chainLinks = CreateObject("Scripting.Dictionary")
    Set chainDirections = CreateObject("Scripting.Dictionary")
    Set orders = CreateObject("Scripting.Dictionary")
    models = ""
    Set ts = fso.OpenTextFile(path, 1, False)
    Do Until ts.AtEndOfStream
        line = Trim(ts.ReadLine)
        If line <> "" And Left(line, 1) <> "#" Then
            parts = Split(line, ",")
            If UBound(parts) >= 3 Then
                model = Trim(parts(0))
                If model <> "model_link" Then
                    If Not chainLinks.Exists(model) Then
                        chainLinks(model) = Trim(parts(3))
                        chainDirections(model) = Trim(parts(1))
                        orders(model) = CLng(Trim(parts(2)))
                        If models <> "" Then models = models & ","
                        models = models & model
                    Else
                        If CLng(Trim(parts(2))) <> CLng(orders(model)) + 1 Then
                            WScript.Echo "ERROR=CHAIN_ORDER_NOT_CONSECUTIVE model=" & model & " chain_order=" & Trim(parts(2))
                            WScript.Quit 6
                        End If
                        orders(model) = CLng(Trim(parts(2)))
                        chainLinks(model) = CStr(chainLinks(model)) & "," & Trim(parts(3))
                    End If
                End If
            End If
        End If
    Loop
    ts.Close
    If models = "" Then
        WScript.Echo "ERROR=CHAIN_CSV_EMPTY path=" & path
        WScript.Quit 6
    End If
    chainModels = Split(models, ",")
    WScript.Echo "CHAIN_CSV=" & path
End Sub

Function DefaultChainCsvPath()
    Dim scriptsFolder, root
    scriptsFolder = fso.GetParentFolderName(WScript.ScriptFullName)
    root = fso.GetParentFolderName(scriptsFolder)
    DefaultChainCsvPath = fso.BuildPath(root, "evaluation\real_world_modi_control\freeway_mainline_chain.csv")
End Function

Function JoinRound3(values)
    Dim i, s
    s = ""
    For i = 0 To UBound(values)
        If i > 0 Then s = s & "+"
        s = s & Round3(values(i))
    Next
    JoinRound3 = s
End Function

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
            ' 2026-08-01 (c): class 70 (TAXI, vehType 150) joins the VSL target set.
            ' It is 10% of the mainline vehicle composition (14.45% of measured
            ' mainline samples) and used to keep the inflow distribution 40
            ' (40-45 km/h) across the whole corridor because no DSD - ours or the
            ' network's own - ever assigned it a distribution. Leaving it out caps
            ' the theoretical VSL coverage at about 85%. See control_mapping
            ' known_approximations id=vsl_taxi_class70_included: this RAISES taxi
            ' free-flow desired speed on the mainline, so the plant differs from
            ' every VISSIM run made before this change.
            SetClassSpeed dsd, 70, defaultSpeed
            WriteManifest "desSpeedDecision", "segment_start_vsl", segmentId, segmentId, modelLink, segmentIndex, direction, name, SafeAtt(dsd, "No"), link.AttValue("No"), laneNo, Round3(pos), Round3(segmentStart), Round3(segmentEnd), defaultSpeed, "10;20;30;70", "", "", "", "", "", "", "", "", "", "", purpose
        End If
    Next
End Sub

' Ramp meter placement is unchanged: the signal head still sits at pos 5 on the
' on-ramp connector. The from/to link+pos literals below are manifest metadata
' only; generate_real_world_control_mapping.py re-reads them from the connector
' end points in the .inpx, so the network stays authoritative if they drift.
Sub InstallRampMeters()
    AddRampMeter "RM_C10480", 9101, 10480, 31, 734.931, 26, 3525.124, "R_D_W", 10, 900, "Ramp meter on connector 10480 link 31 to freeway link 26"
    AddRampMeter "RM_C10482", 9102, 10482, 32, 1028.621, 26, 3829.779, "R_D_W", 10, 900, "Ramp meter on connector 10482 link 32 to freeway link 26"
    AddRampMeter "RM_C10646", 9103, 10646, 68, 352.004, 26, 6072.550, "R_F_W", 10, 900, "Ramp meter on connector 10646 link 68 to freeway link 26"
    AddRampMeter "RM_C10644", 9104, 10644, 69, 1740.482, 26, 6774.308, "R_F_W", 10, 900, "Ramp meter on connector 10644 link 69 to freeway link 26"
    AddRampMeter "RM_C10639", 9105, 10639, 70, 180.143, 2, 1876.292, "R_F_E", 10, 900, "Ramp meter on connector 10639 link 70 to freeway link 2"
    AddRampMeter "RM_C10681", 9106, 10681, 68, 76.589, 2, 2165.429, "R_F_E", 10, 900, "Ramp meter on connector 10681 link 68 to freeway link 2"
    AddRampMeter "RM_C10490", 9107, 10490, 32, 1330.644, 2, 4413.602, "R_D_E", 10, 900, "Ramp meter on connector 10490 link 32 to freeway link 2"
    AddRampMeter "RM_C10484", 9108, 10484, 31, 412.087, 24, 10.319, "R_D_E", 10, 900, "Ramp meter on connector 10484 link 31 to freeway link 24"
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

Sub SetClassSpeed(dsd, vehClassNo, speedKph)
    TrySetAtt dsd, "DesSpeedDistr(" & CStr(vehClassNo) & ")", CLng(speedKph)
End Sub

Function ClampPos(pos, link)
    Dim length
    length = CDbl(link.AttValue("Length2D"))
    If length <= 2 Then
        ClampPos = length / 2.0
    ElseIf CDbl(pos) < 1 Then
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
